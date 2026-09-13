"""Issue #3: arrive-by-08:30 sweeps for the 100 spike schools in four modes. Throwaway.

Run from the repo root with the MOTIS graph built in motis-spike/ (see motis-spike/NOTES.md):

    uv run --with pyproj fixtures/sweep_spike.py            # full sweep, starts and stops ./motis server itself
    uv run --with pyproj fixtures/sweep_spike.py --schools 2  # smoke run on the first two schools
    uv run --with pyproj fixtures/sweep_spike.py --check      # self-test, no server needed

Candidate origins: centres of the EPSG:27700 1 km grid cells within RADIUS_KM of the school
(one of the two options in section 6 of the hosting research note; no download, no licence, and
the denser option, so its count is an upper bound for issue #5). No land mask: sea cells come
back unreachable. Query day: Wednesday 2026-09-16, a term-time weekday inside the imported window.

Output (gitignored): motis-spike/sweep/results.csv, one row per reachable (school, mode, origin),
and motis-spike/sweep/requests.csv, one row per MOTIS request with its elapsed time.
"""
import csv, json, math, os, signal, socket, subprocess, sys, time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPIKE = os.path.join(ROOT, 'motis-spike')
SAMPLE = os.path.join(ROOT, 'fixtures', 'spike-sample.csv')
OUT = os.path.join(SPIKE, 'sweep')
BASE = 'http://127.0.0.1:8080'
ARRIVE = '2026-09-16T08:30:00+01:00'
RADIUS_KM = 30
MAX_SECONDS = 4 * 3600
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


def check():
    o = grid_origins(51.508, -0.128)
    assert 2780 <= len(o) <= 2860, len(o)  # pi * 30^2 = 2827 cells, give or take the rim
    assert min(math.hypot((a - 51.508) * 111.2, (b + 0.128) * 68) for a, b in o) < 0.72, 'nearest cell centre too far'
    assert best_seconds([{'duration': 900, 'transfers': 1}, {'duration': 600, 'transfers': 2}]) == 600
    assert best_seconds([]) is None and best_seconds({}) is None and best_seconds({'duration': 5}) == 5
    print('ok')


def main():
    if '--check' in sys.argv:
        return check()
    limit = int(sys.argv[sys.argv.index('--schools') + 1]) if '--schools' in sys.argv else None
    schools = list(csv.DictReader(open(SAMPLE)))[:limit]
    os.makedirs(OUT, exist_ok=True)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    proc = start_server()
    try:
        with open(os.path.join(OUT, 'results.csv'), 'w', newline='') as rf, \
             open(os.path.join(OUT, 'requests.csv'), 'w', newline='') as qf:
            results, requests = csv.writer(rf, lineterminator='\n'), csv.writer(qf, lineterminator='\n')
            results.writerow(['urn', 'mode', 'origin_lat', 'origin_lng', 'seconds'])
            requests.writerow(['urn', 'mode', 'n_origins', 'n_reachable', 'elapsed_s', 'status'])
            for i, s in enumerate(schools, 1):
                origins = grid_origins(float(s['lat']), float(s['lng']))
                for mode in MODES:
                    n_reach = n_req = 0
                    t0 = time.monotonic()
                    for n, elapsed, status, rows in sweep(s, mode, origins):
                        requests.writerow([s['urn'], mode, n, len(rows), f'{elapsed:.3f}', status])
                        results.writerows([s['urn'], mode, a, b, sec] for a, b, sec in rows)
                        n_reach += len(rows); n_req += 1
                    rf.flush(); qf.flush()
                    print(f'{i:3}/{len(schools)} {s["urn"]} {mode:7} {len(origins)} origins '
                          f'{n_reach} reachable {n_req} req {time.monotonic() - t0:.1f}s', flush=True)
    finally:
        stop_server(proc)


if __name__ == '__main__':
    main()
