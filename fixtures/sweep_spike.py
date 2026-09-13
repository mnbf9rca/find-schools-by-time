"""Issue #3: arrive-by-08:30 sweeps for the 100 spike schools in four modes. Throwaway.

Run from the repo root with the MOTIS graph built in motis-spike/ (see motis-spike/NOTES.md):

    uv run --with pyproj fixtures/sweep_spike.py            # full sweep, starts and stops ./motis server itself
    uv run --with pyproj fixtures/sweep_spike.py --schools 2  # smoke run on the first two schools
    uv run --with pyproj fixtures/sweep_spike.py --check      # self-test, no server needed
    uv run --with pyproj fixtures/sweep_spike.py --workers 8 --cap 90 --out w8-cap90   # issue #5 timing runs

Candidate origins: centres of the EPSG:27700 1 km grid cells within RADIUS_KM of the school
(one of the two options in section 6 of the hosting research note; no download, no licence, and
the denser option, so its count is an upper bound for issue #5). No land mask: sea cells come
back unreachable. Query day: Wednesday 2026-09-16, a term-time weekday inside the imported window.

Output (gitignored): motis-spike/sweep/results.csv, one row per reachable (school, mode, origin),
motis-spike/sweep/requests.csv, one row per MOTIS request with its elapsed time, and summary.json
with wall time and the server's peak resident memory. --out NAME puts them in motis-spike/sweep/NAME/.
--workers N runs N school-mode sweeps at once; --cap MINUTES limits every mode (default 240).
"""
import csv, json, math, os, signal, socket, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPIKE = os.path.join(ROOT, 'motis-spike')
SAMPLE = os.path.join(ROOT, 'fixtures', 'spike-sample.csv')
OUT = os.path.join(SPIKE, 'sweep')
BASE = 'http://127.0.0.1:8080'
ARRIVE = '2026-09-16T08:30:00+01:00'
RADIUS_KM = 30
MAX_SECONDS = 4 * 3600  # overridden by --cap
STREET_BATCH = 250  # ponytail: GET URL must stay under the 8 KB header limit; ~20 bytes per coordinate
MODES = ['TRANSIT', 'WALK', 'BIKE', 'CAR']


def grid_origins(lat, lng):
    """Centres of 1 km British National Grid cells within RADIUS_KM, as (lat, lng) rounded to 6 dp."""
    from pyproj import Transformer
    fwd = Transformer.from_crs('EPSG:4326', 'EPSG:27700', always_xy=True)
    back = Transformer.from_crs('EPSG:27700', 'EPSG:4326', always_xy=True)
    e, n = fwd.transform(lng, lat)
    r = RADIUS_KM * 1000
    out = []
    for ce in range(int((e - r) // 1000), int((e + r) // 1000) + 1):
        for cn in range(int((n - r) // 1000), int((n + r) // 1000) + 1):
            x, y = ce * 1000 + 500, cn * 1000 + 500
            if math.hypot(x - e, y - n) <= r:
                lo, la = back.transform(x, y)
                out.append((round(la, 6), round(lo, 6)))
    return out


def best_seconds(entry):
    """Minimum duration in an entry: a Pareto list for transit, a single object for street modes."""
    items = entry if isinstance(entry, list) else [entry]
    secs = [i['duration'] for i in items if isinstance(i, dict) and 'duration' in i]
    return min(secs) if secs else None


def http(method, url, body=None):
    req = urllib.request.Request(url, data=body, method=method, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=900) as resp:
        return resp.status, json.load(resp)


def sweep(school, mode, origins):
    """Yield (batch_size, elapsed, status, [(lat, lng, seconds) ...]) per request."""
    if mode == 'TRANSIT':
        batches = [origins]
    else:
        batches = [origins[i:i + STREET_BATCH] for i in range(0, len(origins), STREET_BATCH)]
    for batch in batches:
        t0 = time.monotonic()
        if mode == 'TRANSIT':
            body = json.dumps({
                'one': f'{school["lat"]},{school["lng"]}', 'many': [f'{a},{b}' for a, b in batch],
                'time': ARRIVE, 'arriveBy': True, 'maxTravelTime': MAX_SECONDS // 60,
                'transitModes': ['TRANSIT'], 'preTransitModes': ['WALK'], 'postTransitModes': ['WALK'],
                'maxPreTransitTime': 900, 'maxPostTransitTime': 900,
                'directMode': 'WALK', 'maxDirectTime': MAX_SECONDS, 'useRoutedTransfers': True,
            }).encode()
            status, data = http('POST', f'{BASE}/api/experimental/one-to-many-intermodal', body)
            entries = data['transit_durations']
        else:
            many = ','.join(f'{a};{b}' for a, b in batch)
            status, data = http('GET', f'{BASE}/api/v1/one-to-many?one={school["lat"]};{school["lng"]}'
                                       f'&many={many}&mode={mode}&max={MAX_SECONDS}&maxMatchingDistance=250&arriveBy=true')
            entries = data
        assert len(entries) == len(batch), (mode, len(entries), len(batch))
        rows = [(a, b, s) for (a, b), e in zip(batch, entries) if (s := best_seconds(e)) is not None]
        yield len(batch), time.monotonic() - t0, status, rows


def port_open():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', 8080)) == 0


def start_server():
    if port_open():
        print('using MOTIS already on :8080', flush=True)
        return None
    log = open(os.path.join(SPIKE, 'server-sweep.log'), 'ab')
    proc = subprocess.Popen(['./motis', 'server'], cwd=SPIKE, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(240):
        if proc.poll() is not None:
            sys.exit(f'motis server exited early with {proc.returncode}, see motis-spike/server-sweep.log')
        if port_open():
            return proc
        time.sleep(0.5)
    proc.kill()
    sys.exit('motis server did not open :8080 within 120 s')


def stop_server(proc):
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(30)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def peak_rss_sampler(stop):
    """Sample the motis server's resident set every 2 s; return a dict whose 'kb' is the peak."""
    peak = {'kb': 0}
    def run():
        while not stop.is_set():
            pid = subprocess.run(['pgrep', '-f', '^./motis server'], capture_output=True, text=True).stdout.split()
            if pid:
                out = subprocess.run(['ps', '-o', 'rss=', '-p', pid[0]], capture_output=True, text=True).stdout.strip()
                if out.isdigit():
                    peak['kb'] = max(peak['kb'], int(out))
            stop.wait(2)
    threading.Thread(target=run, daemon=True).start()
    return peak


def check():
    o = grid_origins(51.508, -0.128)
    assert 2780 <= len(o) <= 2860, len(o)  # pi * 30^2 = 2827 cells, give or take the rim
    assert min(math.hypot((a - 51.508) * 111.2, (b + 0.128) * 68) for a, b in o) < 0.72, 'nearest cell centre too far'
    assert best_seconds([{'duration': 900, 'transfers': 1}, {'duration': 600, 'transfers': 2}]) == 600
    assert best_seconds([]) is None and best_seconds({}) is None and best_seconds({'duration': 5}) == 5
    print('ok')


def arg(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def main():
    global MAX_SECONDS
    if '--check' in sys.argv:
        return check()
    schools = list(csv.DictReader(open(SAMPLE)))[:arg('--schools', 0) or None]
    workers, cap, out = arg('--workers', 1), arg('--cap', 240), os.path.join(OUT, arg('--out', ''))
    MAX_SECONDS = cap * 60
    os.makedirs(out, exist_ok=True)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    proc = start_server()
    stop = threading.Event()
    peak = peak_rss_sampler(stop)
    t_start = time.monotonic()
    n_requests = 0
    try:
        with open(os.path.join(out, 'results.csv'), 'w', newline='') as rf, \
             open(os.path.join(out, 'requests.csv'), 'w', newline='') as qf:
            results, requests = csv.writer(rf, lineterminator='\n'), csv.writer(qf, lineterminator='\n')
            results.writerow(['urn', 'mode', 'origin_lat', 'origin_lng', 'seconds'])
            requests.writerow(['urn', 'mode', 'n_origins', 'n_reachable', 'elapsed_s', 'status'])
            origins = {s['urn']: grid_origins(float(s['lat']), float(s['lng'])) for s in schools}

            def task(s, mode):
                t0 = time.monotonic()
                batches = list(sweep(s, mode, origins[s['urn']]))
                return s, mode, batches, time.monotonic() - t0

            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(task, s, mode) for s in schools for mode in MODES]
                for i, f in enumerate(futures, 1):
                    s, mode, batches, took = f.result()
                    n_reach = 0
                    for n, elapsed, status, rows in batches:
                        requests.writerow([s['urn'], mode, n, len(rows), f'{elapsed:.3f}', status])
                        results.writerows([s['urn'], mode, a, b, sec] for a, b, sec in rows)
                        n_reach += len(rows)
                    n_requests += len(batches)
                    rf.flush(); qf.flush()
                    print(f'{(i + 3) // 4:3}/{len(schools)} {s["urn"]} {mode:7} {len(origins[s["urn"]])} origins '
                          f'{n_reach} reachable {len(batches)} req {took:.1f}s', flush=True)
    finally:
        stop.set()
        stop_server(proc)
    summary = {'schools': len(schools), 'workers': workers, 'cap_minutes': cap, 'requests': n_requests,
               'wall_s': round(time.monotonic() - t_start, 1), 'peak_server_rss_kb': peak['kb'],
               'results_bytes': os.path.getsize(os.path.join(out, 'results.csv'))}
    json.dump(summary, open(os.path.join(out, 'summary.json'), 'w'), indent=1)
    print(summary, flush=True)


if __name__ == '__main__':
    main()
