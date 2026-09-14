"""Resumable MOTIS sweeps and per-origin records; see docs/precompute-runbook.md.

uv run --with pyproj fixtures/precompute.py OUT --schools fixtures/spike-sample.csv
The operator owns MOTIS. --origins and --graph-dir also support isolated checks.
The school index always uses the whole committed schools.json, even for samples.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import http.client
import json
import math
from pathlib import Path
import signal
import struct
import subprocess
import threading
import time
import urllib.error
import urllib.request

from pyproj import Transformer

if __package__:
    from . import record
    from .check_dataset_manifest import validate
else:
    import record
    from check_dataset_manifest import validate

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = 'http://127.0.0.1:8080'
ARRIVE = '2026-09-16T08:30:00+01:00'
RADII = (None, None, 30, None)
BATCH_SIZE = 20000
CAP = 5400
MOTIS_VERSION = '2.11.3'
FULL_SCHOOLS = json.loads((ROOT / 'schools.json').read_text())
SCHOOL_INDEX = {s['urn']: i for i, s in enumerate(sorted(FULL_SCHOOLS, key=lambda s: s['urn']))}


def atomic_bytes(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_bytes(data)
    temporary.replace(path)


def atomic_json(path, value):
    atomic_bytes(path, (json.dumps(value, indent=2) + '\n').encode())


def sha256(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def batches(values):
    for offset in range(0, len(values), BATCH_SIZE):
        yield values[offset:offset + BATCH_SIZE]


def candidate_indices(origins, easting, northing, radius_km):
    if radius_km is None:
        return list(range(len(origins)))
    limit = (radius_km * 1000) ** 2
    return [i for i, origin in enumerate(origins)
            for e, n in [origin.get('centre') or tuple(int(k) * 1000 + 500 for k in origin['id'].split('_'))]
            if (e - easting) ** 2 + (n - northing) ** 2 <= limit]


def payload(school, mode, origins):
    separator = ';' if mode == 3 else ','
    body = {'one': f'{school["lat"]}{separator}{school["lng"]}',
            'many': [f'{o["lat"]}{separator}{o["lng"]}' for o in origins],
            'arriveBy': True, 'maxMatchingDistance': 250}
    if mode == 3:
        body.update(mode='CAR', max=CAP)
        return '/api/v1/one-to-many', body
    body.update(time=ARRIVE, maxTravelTime=90, maxDirectTime=CAP,
                transitModes=['TRANSIT'] if mode == 0 else [],
                directMode='WALK' if mode == 0 else 'BIKE',
                preTransitModes=['WALK'], postTransitModes=['WALK'],
                maxPreTransitTime=900, maxPostTransitTime=900, useRoutedTransfers=True)
    if mode == 2:
        body['cyclingSpeed'] = 5.0
    return '/api/experimental/one-to-many-intermodal', body


def seconds(entry):
    entries = entry if isinstance(entry, list) else [entry]
    values = []
    for item in entries:
        if 'duration' not in item:
            continue
        value = item['duration']
        if not math.isfinite(value) or value < 0:
            raise ValueError('MOTIS seconds must be finite and nonnegative')
        whole = math.floor(value)
        value = whole + (value - whole >= .5)
        values.append(value if value <= CAP else record.SENTINEL)
    return min(values, default=record.SENTINEL)


def response_values(mode, data, count):
    street = data if mode == 3 else data['street_durations']
    if len(street) != count:
        raise ValueError('Street response length differs from request')
    direct = [seconds(entry) for entry in street]
    if mode != 0:
        return {mode: direct}
    transit = data['transit_durations']
    if len(transit) != count:
        raise ValueError('Transit response length differs from request')
    return {0: [min(seconds(t), w) for t, w in zip(transit, direct)], 1: direct}


def halving(batch, request, stop):
    if stop.is_set():
        raise InterruptedError('Run stopped')
    try:
        response = request(batch)
    except (OSError, urllib.error.URLError, http.client.HTTPException) as error:
        if stop.is_set():
            raise InterruptedError('Run stopped') from error
        if len(batch) == 1:
            raise RuntimeError('A single-origin request failed') from error
        midpoint = len(batch) // 2
        yield from halving(batch[:midpoint], request, stop)
        yield from halving(batch[midpoint:], request, stop)
    else:
        yield batch, response


def write_school(path, planes):
    sections = [sorted(plane) for plane in planes]
    data = struct.pack('<4I', *(len(plane) for plane in sections))
    data += b''.join(struct.pack('<IH', i, seconds) for plane in sections for i, seconds in plane)
    atomic_bytes(path, data)


def read_school(path, origin_count):
    data = path.read_bytes()
    if len(data) < 16:
        raise ValueError('Short school header')
    counts = struct.unpack_from('<4I', data)
    if len(data) != 16 + 6 * sum(counts):
        raise ValueError('School file length does not match counts')
    planes, offset = [], 16
    for count in counts:
        pairs = list(struct.iter_unpack('<IH', data[offset:offset + 6 * count]))
        if any(i >= origin_count or value > CAP for i, value in pairs):
            raise ValueError('Invalid school pair')
        if any(a[0] >= b[0] for a, b in zip(pairs, pairs[1:])):
            raise ValueError('School pairs are not unique and ordered')
        planes.append(pairs)
        offset += 6 * count
    return planes


def transpose(out, version, origins, urns, stop):
    size = 8 * record.SCHOOL_COUNT
    # ponytail: one matrix uses about 3.5 GB; slice origin ranges on a smaller machine.
    matrix = bytearray(b'\xff') * (len(origins) * size)
    for urn in urns:
        if stop.is_set():
            raise InterruptedError('Transpose stopped')
        planes = read_school(out / 'schools' / f'{urn}.bin', len(origins))
        for mode, pairs in enumerate(planes):
            slot = 2 * (mode * record.SCHOOL_COUNT + SCHOOL_INDEX[urn])
            for origin, value in pairs:
                struct.pack_into('<H', matrix, origin * size + slot, value)
    directory = out / version
    directory.mkdir(exist_ok=True)
    view = memoryview(matrix)
    for i, origin in enumerate(origins):
        if stop.is_set():
            raise InterruptedError('Transpose stopped')
        atomic_bytes(directory / f'{origin["id"]}.bin', view[i * size:(i + 1) * size])
    if {p.stem for p in directory.glob('*.bin')} != {o['id'] for o in origins}:
        raise ValueError('Version must contain exactly one record per origin')
    return len(matrix)


def load_origins(path):
    with path.open() as f:
        origins = list(csv.DictReader(f))
    seen = set()
    for origin in origins:
        e, n = map(int, origin['id'].split('_'))
        if origin['id'] in seen or origin['id'] != f'{e}_{n}':
            raise ValueError('Origin identifiers must be unique and canonical')
        seen.add(origin['id'])
        origin['centre'] = (e * 1000 + 500, n * 1000 + 500)
        for key in ('lat', 'lng'):
            if not math.isfinite(float(origin[key])):
                raise ValueError('Origin coordinates must be finite')
    if not origins:
        raise ValueError('Origin grid is empty')
    return origins


def load_schools(path):
    with path.open() as f:
        schools = list(csv.DictReader(f)) if path.suffix == '.csv' else json.load(f)
    transformer = Transformer.from_crs(4326, 27700, always_xy=True)
    seen = set()
    for school in schools:
        urn = school['urn']
        if urn not in SCHOOL_INDEX or urn in seen:
            raise ValueError(f'Unknown or duplicate school URN {urn}')
        seen.add(urn)
        school['lat'], school['lng'] = float(school['lat']), float(school['lng'])
        school['e'], school['n'] = transformer.transform(school['lng'], school['lat'], errcheck=True)
        if not math.isfinite(school['e']) or not math.isfinite(school['n']):
            raise ValueError(f'Invalid coordinates for {urn}')
    if not schools:
        raise ValueError('School selection is empty')
    return sorted(schools, key=lambda s: s['urn'])


def walk_coverage(out, schools, origins):
    missing, nearby = [], 0
    for school in schools:
        walking = {i for i, value in read_school(out / 'schools' / f'{school["urn"]}.bin', len(origins))[1]}
        for i in candidate_indices(origins, school['e'], school['n'], 2):
            nearby += 1
            if i not in walking:
                e, n = origins[i]['centre']
                missing.append((school['urn'], origins[i]['id'],
                                round(math.hypot(e - school['e'], n - school['n']), 1)))
    temporary = out / 'walk-coverage.csv.tmp'
    with temporary.open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['urn', 'origin_id', 'distance_metres'])
        writer.writerows(missing)
    temporary.replace(out / 'walk-coverage.csv')
    return len(missing), nearby


def run(args):
    started_clock = time.monotonic()
    origins, schools = load_origins(args.origins), load_schools(args.schools)
    graph = args.graph_dir.resolve()
    with (ROOT / 'fixtures/feed-manifest.json').open() as f:
        feeds = json.load(f)
    bods = next(feed for feed in feeds if feed['path'] == 'motis-spike/feeds/bods.zip')
    feeds = [{'path': bods['path'], 'sha256': bods['sha256']},
             {'path': 'motis-spike/feeds/rail.zip', 'sha256': sha256(graph.parent / 'feeds/rail.zip')}]
    parameters = {'pruning_radii_km': list(RADII), 'batch_size': BATCH_SIZE, 'cap_seconds': CAP,
                  'cycling_speed_mps': 5.0, 'workers': args.workers, 'motis_version': MOTIS_VERSION,
                  'origins_sha256': sha256(args.origins), 'school_index_sha256': record.school_index_hash(SCHOOL_INDEX),
                  'schools_sha256': sha256(args.schools), 'graph_directory': str(graph),
                  'arrival': ARRIVE, 'feeds': feeds}
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    state_path = out / 'run.json'
    if state_path.exists():
        state = json.loads(state_path.read_text())
        state['parameters'].pop('base_url', None)
        if state['parameters'] != parameters:
            raise ValueError('Resume parameters differ from run.json')
    else:
        now = datetime.now(timezone.utc)
        state = {'version': now.strftime('%Y%m%dT%H%M%SZ'), 'started': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                 'parameters': parameters, 'wall_seconds': 0, 'requests': 0, 'requests_retried': 0,
                 'peak_server_rss_bytes': 0, 'transpose_seconds': 0}
        atomic_json(state_path, state)
    prior_wall = state['wall_seconds']
    lock, stop, sampler_stop = threading.RLock(), threading.Event(), threading.Event()

    def save():
        with lock:
            state['wall_seconds'] = prior_wall + time.monotonic() - started_clock
            atomic_json(state_path, state)

    def stopping(signum, frame):
        stop.set()

    old_handlers = {s: signal.signal(s, stopping) for s in (signal.SIGTERM, signal.SIGINT)}
    pid = None
    if args.base_url == DEFAULT_URL:
        pids = subprocess.run(['pgrep', '-x', 'motis'], capture_output=True, text=True).stdout.split()
        if len(pids) != 1:
            for s, handler in old_handlers.items():
                signal.signal(s, handler)
            raise ValueError(f'Expected exactly one MOTIS process, found {len(pids)}')
        pid = pids[0]

    def sample():
        if pid:
            value = subprocess.run(['ps', '-o', 'rss=', '-p', pid], capture_output=True, text=True).stdout.strip()
            if value.isdigit():
                with lock:
                    state['peak_server_rss_bytes'] = max(state['peak_server_rss_bytes'], int(value) * 1024)

    def monitor():
        while not sampler_stop.wait(1):
            sample()
            save()

    sample()
    sampler = threading.Thread(target=monitor)
    sampler.start()
    (out / 'schools').mkdir(exist_ok=True)

    def school_task(school):
        if stop.is_set():
            raise InterruptedError('Run stopped')
        t0, requests, planes = time.monotonic(), 0, [[], [], [], []]
        for mode in (0, 2, 3):
            indices = candidate_indices(origins, school['e'], school['n'], RADII[mode])
            for batch in batches(indices):
                attempts = 0
                def request(subset):
                    nonlocal requests, attempts
                    if stop.is_set():
                        raise InterruptedError('Run stopped')
                    endpoint, body = payload(school, mode, [origins[i] for i in subset])
                    with lock:
                        state['requests'] += 1
                        state['requests_retried'] += int(attempts > 0)
                        save()
                    attempts += 1
                    requests += 1
                    req = urllib.request.Request(args.base_url + endpoint, data=json.dumps(body).encode(),
                                                 headers={'Content-Type': 'application/json'})
                    with urllib.request.urlopen(req, timeout=600) as response:
                        if response.status != 200:
                            raise OSError(f'HTTP {response.status}')
                        return json.load(response)
                for subset, response in halving(batch, request, stop):
                    for plane, values in response_values(mode, response, len(subset)).items():
                        planes[plane].extend((i, value) for i, value in zip(subset, values) if value != record.SENTINEL)
        if stop.is_set():
            raise InterruptedError('Run stopped')
        write_school(out / 'schools' / f'{school["urn"]}.bin', planes)
        return school['urn'], time.monotonic() - t0, requests, sum(map(len, planes))

    pool = ThreadPoolExecutor(max_workers=args.workers)
    try:
        remaining, complete = [], 0
        for school in schools:
            path = out / 'schools' / f'{school["urn"]}.bin'
            try:
                read_school(path, len(origins))
            except (FileNotFoundError, ValueError):
                path.unlink(missing_ok=True)
                remaining.append(school)
            else:
                complete += 1
        print(f'Resume: {complete}/{len(schools)} valid school files; version={state["version"]}', flush=True)
        futures = [pool.submit(school_task, school) for school in remaining]
        for future in as_completed(futures):
            urn, elapsed, requests, pairs = future.result()
            complete += 1
            print(f'{complete}/{len(schools)} {urn} {elapsed:.1f}s requests={requests} pairs={pairs} '
                  f'rss={state["peak_server_rss_bytes"] / 1024**3:.2f}GiB', flush=True)
        if stop.is_set():
            raise InterruptedError('Run stopped')
        missing, nearby = walk_coverage(out, schools, origins)
        print(f'Walk coverage: {missing}/{nearby} pairs within 2 km have no walking value; see walk-coverage.csv', flush=True)
        print('Transposing all origins using the full school index.', flush=True)
        t0 = time.monotonic()
        try:
            record_bytes = transpose(out, state['version'], origins, [s['urn'] for s in schools], stop)
        finally:
            state['transpose_seconds'] += time.monotonic() - t0
        school_bytes = sum((out / 'schools' / f'{s["urn"]}.bin').stat().st_size for s in schools)
        save()
        run_stats = {key: state[key] for key in ('started', 'wall_seconds', 'requests', 'requests_retried',
                                               'peak_server_rss_bytes', 'transpose_seconds')}
        run_stats.update(workers=args.workers, output_bytes=school_bytes + record_bytes,
                         school_bytes=school_bytes, record_bytes=record_bytes, schools_completed=complete,
                         walk_missing_pairs=missing, walk_nearby_pairs=nearby)
        manifest = {'version': state['version'], 'routing_date': '2026-09-16', 'routing_time': '08:30',
                    'timezone': 'Europe/London', 'motis_version': MOTIS_VERSION, 'modes': list(record.MODES),
                    'cap_seconds': CAP, 'display_band_minutes': 10, 'unreachable': record.SENTINEL,
                    'compression': 'none', 'rounding': 'half up to whole seconds, then compared with 5400',
                    'cycling_speed_mps': 5.0, 'pruning_radii_km': list(RADII), 'origin_count': len(origins),
                    'origins_sha256': parameters['origins_sha256'], 'school_count': record.SCHOOL_COUNT,
                    'school_index_sha256': parameters['school_index_sha256'], 'feeds': feeds, 'run': run_stats,
                    'shards': {'records_per_shard': 8000, 'count': (len(origins) + 7999) // 8000,
                               'record_bytes': 8 * record.SCHOOL_COUNT},
                    'keys': {'shard': state['version'] + '/shard-{nn}.bin',
                             'origins': state['version'] + '/origins.txt',
                             'manifest': state['version'] + '/manifest.json', 'current': 'current.json'}}
        errors = validate(manifest)
        if errors:
            raise ValueError('; '.join(errors))
        atomic_json(out / state['version'] / 'manifest.json', manifest)
        atomic_json(out / 'current.json', {'version': state['version']})
        print(json.dumps(run_stats, sort_keys=True), flush=True)
        return 0
    except BaseException:
        stop.set()
        raise
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
        sampler_stop.set()
        sampler.join()
        sample()
        save()
        for s, handler in old_handlers.items():
            signal.signal(s, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--base-url', default=DEFAULT_URL)
    parser.add_argument('--schools', type=Path, default=ROOT / 'schools.json')
    parser.add_argument('--origins', type=Path, default=ROOT / 'fixtures/origins.csv')
    parser.add_argument('--graph-dir', type=Path, default=ROOT / 'motis-spike/data.rail')
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('--workers must be positive')
    args.base_url = args.base_url.rstrip('/')
    try:
        return run(args)
    except InterruptedError:
        print('Interrupted; rerun the same command to resume.', flush=True)
        return 143
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f'Precompute failed: {error}', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
