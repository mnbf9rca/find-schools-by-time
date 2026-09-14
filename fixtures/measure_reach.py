"""Issue 15 measurements, using an already running combined MOTIS graph.

Run: uv run --with pyproj fixtures/measure_reach.py
Check without a server: uv run --with pyproj fixtures/measure_reach.py --check
Set data.rail/config.yml limits to 200000 origins and 600 seconds first.
The caller owns server startup and shutdown. Outputs one CSV row per request.
Distances are straight lines in EPSG:27700. RSS is server KiB, sampled each
second plus request boundaries; subsecond peaks can be missed. Request wall
time excludes JSON encoding/decoding; group wall time includes client work.
"""
import csv
import http.client
import json
import math
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from pyproj import Transformer
import sweep_spike as sweep

ROOT = Path(__file__).resolve().parents[1]
URNS = ('137353', '131065', '110533', '150099')
MODES = ('TRANSIT', 'BIKE', 'CAR')
CAP = 5400
FIELDS = ('phase', 'workers', 'urn', 'mode', 'origin_set', 'part', 'radius_km',
          'n_origins', 'elapsed_s', 'http_status', 'outcome', 'n_reachable',
          'max_distance_km', 'n_walk_reachable', 'max_walk_distance_km',
          'peak_rss_kib', 'group_wall_s', 'missing_from_full', 'error')
FWD = Transformer.from_crs(4326, 27700, always_xy=True)
BACK = Transformer.from_crs(27700, 4326, always_xy=True)


def reachable_indices(mode, data, count):
    if mode == 'CAR':
        entries = data
    else:
        entries = data['street_durations']
        assert len(entries) == count, (len(entries), count)
        if mode == 'TRANSIT':
            transit = data['transit_durations']
            assert len(transit) == count, (len(transit), count)
            entries = [[walk, *trips] for walk, trips in zip(entries, transit)]
    assert len(entries) == count, (len(entries), count)
    return {i for i, entry in enumerate(entries)
            if (seconds := sweep.best_seconds(entry)) is not None and 0 <= seconds <= CAP}


def england_grid():
    # Same cell centers, ordering and coordinate rounding as sweep.grid_origins.
    return [(round(lat, 6), round(lng, 6))
            for e in range(80500, 660000, 1000)
            for n in range(500, 660000, 1000)
            for lng, lat in [BACK.transform(e, n)]]


def distances(school, origins):
    e, n = FWD.transform(float(school['lng']), float(school['lat']))
    xs, ys = FWD.transform([o[1] for o in origins], [o[0] for o in origins])
    return [math.hypot(x - e, y - n) / 1000 for x, y in zip(xs, ys)]


def payload(school, mode, origins):
    sep = ';' if mode == 'CAR' else ','
    body = {'one': f'{school["lat"]}{sep}{school["lng"]}',
            'many': [f'{lat}{sep}{lng}' for lat, lng in origins], 'arriveBy': True}
    if mode == 'CAR':
        body.update(mode='CAR', max=CAP, maxMatchingDistance=250)
        endpoint = '/api/v1/one-to-many'
    else:
        body.update(time=sweep.ARRIVE, maxTravelTime=90,
                    transitModes=['TRANSIT'] if mode == 'TRANSIT' else [],
                    preTransitModes=['WALK'], postTransitModes=['WALK'],
                    maxPreTransitTime=900, maxPostTransitTime=900,
                    directMode='WALK' if mode == 'TRANSIT' else 'BIKE',
                    maxDirectTime=CAP, useRoutedTransfers=True)
        if mode == 'BIKE':
            body['cyclingSpeed'] = 5.0
        endpoint = '/api/experimental/one-to-many-intermodal'
    return endpoint, json.dumps(body).encode()


def request(school, mode, origins, pid):
    endpoint, body = payload(school, mode, origins)
    conn = http.client.HTTPConnection('127.0.0.1', 8080, timeout=600)
    stop = threading.Event()
    timed_out = threading.Event()
    peak = [0]

    def sample():
        rss = subprocess.run(['ps', '-o', 'rss=', '-p', str(pid)],
                             capture_output=True, text=True).stdout.strip()
        if rss.isdigit():
            peak[0] = max(peak[0], int(rss))

    def monitor():
        while not stop.wait(1):
            sample()

    def expire():
        timed_out.set()
        if conn.sock:
            try:
                conn.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    sample()
    sampler = threading.Thread(target=monitor)
    sampler.start()
    timer = threading.Timer(600, expire)
    status, raw, error = '', b'', ''
    t0 = time.monotonic()
    timer.start()
    try:
        conn.request('POST', endpoint, body, {'Content-Type': 'application/json'})
        response = conn.getresponse()
        status, raw = response.status, response.read()
    except (OSError, http.client.HTTPException) as exc:
        error = str(exc)
    finally:
        elapsed = time.monotonic() - t0
        timer.cancel()
        conn.close()
        stop.set()
        sampler.join()
        sample()
    outcome = 'timeout' if timed_out.is_set() or elapsed > 600 else 'ok'
    if outcome == 'ok' and (status != 200 or error):
        outcome = 'failed'
    row = dict(n_origins=len(origins), elapsed_s=round(elapsed, 6), http_status=status,
               outcome=outcome, peak_rss_kib=peak[0], error=error or (raw[:200].decode(errors='replace') if outcome != 'ok' else ''))
    reached, walked = set(), set()
    if outcome == 'ok':
        try:
            data = json.loads(raw)
            reached = reachable_indices(mode, data, len(origins))
            if mode == 'TRANSIT':
                walked = reachable_indices('BIKE', data, len(origins))
        except (ValueError, KeyError, TypeError, AssertionError) as exc:
            row.update(outcome='failed', error=f'Invalid response: {exc}')
    return row, reached, walked


def measure(school, mode, origins, pid, emit, *, phase, workers, label, radius='', part='all'):
    """Record every failure; split both halves so the whole set is still measured."""
    row, reached, walked = request(school, mode, origins, pid)
    ds = distances(school, origins)
    row.update(phase=phase, workers=workers, urn=school['urn'], mode=mode,
               origin_set=label, radius_km=radius, part=part)
    if row['outcome'] == 'ok':
        row.update(n_reachable=len(reached), max_distance_km=max((ds[i] for i in reached), default=0),
                   n_walk_reachable=len(walked) if mode == 'TRANSIT' else '',
                   max_walk_distance_km=max((ds[i] for i in walked), default=0) if mode == 'TRANSIT' else '')
    emit(row)
    print(f'{phase} w{workers} {school["urn"]} {mode} {label} {part}: '
          f'{len(origins)} origins, {row["outcome"]} HTTP {row["http_status"]}, '
          f'{row["elapsed_s"]:.3f}s, reachable {row.get("n_reachable", "unknown")}, '
          f'max {row.get("max_distance_km", 0):.3f} km, RSS {row["peak_rss_kib"]} KiB', flush=True)
    if row['outcome'] == 'ok':
        return {origins[i] for i in reached}
    if len(origins) == 1:
        raise RuntimeError(f'Single-origin request failed: {row}')
    midpoint = len(origins) // 2
    result = set()
    for suffix, subset in [('a', origins[:midpoint]), ('b', origins[midpoint:])]:
        result.update(measure(school, mode, subset, pid, emit, phase=phase,
                              workers=workers, label=label, radius=radius, part=part + suffix))
    return result


def check():
    # Losing the direct walk or admitting an over-cap journey must fail this check.
    data = {'transit_durations': [[], [{'duration': 5401}], [{'duration': 5300}]],
            'street_durations': [{'duration': 60}, {}, {'duration': 5400}]}
    assert reachable_indices('TRANSIT', data, 3) == {0, 2}
    assert reachable_indices('BIKE', data, 3) == {0, 2}
    assert reachable_indices('CAR', [{}, {'duration': 5400}, {'duration': 5401}], 3) == {1}
    grid = england_grid()
    assert len(grid) == 382800 and len(set(grid)) == 382800
    school = {'lat': '51.52221', 'lng': '-0.15217'}
    circle = sweep.grid_origins(float(school['lat']), float(school['lng']))
    assert set(circle) <= set(grid)
    assert max(distances(school, circle)) < 30.001
    for mode in MODES:
        endpoint, raw = payload(school, mode, circle[:1])
        body = json.loads(raw)
        assert body['arriveBy'] and body.get('max', body.get('maxDirectTime')) == 5400
        if mode == 'BIKE':
            assert body['cyclingSpeed'] == 5.0 and body['transitModes'] == []
    from types import SimpleNamespace
    from unittest.mock import patch
    with patch('subprocess.run', return_value=SimpleNamespace(stdout='')), \
         patch.object(http.client.HTTPConnection, 'request', side_effect=OSError('server exited')):
        row, _, _ = request(school, 'CAR', circle[:1], 999999)
    assert row['outcome'] == 'failed' and row['error'] == 'server exited'
    assert row['peak_rss_kib'] == 0
    print('reach checks passed')


def main():
    if '--check' in sys.argv:
        return check()
    pids = subprocess.check_output(['pgrep', '-x', 'motis'], text=True).split()
    assert len(pids) == 1, f'Expected one managed MOTIS server, found {pids}'
    pid = int(pids[0])
    with (ROOT / 'fixtures/spike-sample.csv').open() as f:
        sample = {s['urn']: s for s in csv.DictReader(f)}
    schools = [sample[urn] for urn in URNS]
    full = england_grid()
    full_reach = {}
    rows = []
    with (ROOT / 'fixtures/measure_reach.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, FIELDS, lineterminator='\n')
        writer.writeheader()
        lock = threading.Lock()

        def emit(row):
            with lock:
                rows.append(row)
                writer.writerow(row)
                f.flush()

        for school in schools:
            for radius in (30, 60, 100, None):
                sweep.RADIUS_KM = radius or 30
                origins = full if radius is None else sweep.grid_origins(float(school['lat']), float(school['lng']))
                for mode in MODES:
                    reached = measure(school, mode, origins, pid, emit, phase='scaling', workers=1,
                                      label='england' if radius is None else f'{radius}km', radius=radius or '')
                    if radius is None:
                        full_reach[school['urn'], mode] = reached

        # Measure the smallest sample-wide radius with a ten percent margin.
        radii = {mode: max(r['max_distance_km'] for r in rows
                           if r['mode'] == mode and r['outcome'] == 'ok') * 1.1 for mode in MODES}
        candidates = {}
        for school in schools:
            ds = distances(school, full)
            for mode in MODES:
                origins = [o for o, d in zip(full, ds) if d <= radii[mode]]
                assert full_reach[school['urn'], mode] <= set(origins), 'Pruning dropped a reachable origin'
                candidates[school['urn'], mode] = origins
        for workers in (1, 8):
            for mode in MODES:
                tasks = schools if workers == 1 else schools * 2
                def task(school):
                    records = []
                    def record(row):
                        records.append(row)
                        emit(row)
                    reached = measure(school, mode, candidates[school['urn'], mode], pid, record,
                                      phase='margin', workers=workers, label='margin', radius=radii[mode])
                    missing = len(full_reach[school['urn'], mode] - reached)
                    for record in records:
                        record['missing_from_full'] = missing
                    return records, missing
                t0 = time.monotonic()
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    results = list(pool.map(task, tasks))
                wall = time.monotonic() - t0
                for records, missing in results:
                    for record in records:
                        record['group_wall_s'] = round(wall, 6)
                assert not any(missing for _, missing in results), 'Pruned routing lost reachable origins'
                print(f'PROJECTION {mode} workers={workers} radius={radii[mode]:.6f} '
                      f'group_wall_s={wall:.6f} schools={len(tasks)} '
                      f'full_hours={wall / len(tasks) * 4373 / 3600:.6f}', flush=True)
        # Keep the request log intact if interrupted while adding group metadata.
        output = ROOT / 'fixtures/measure_reach.csv'
        temporary = output.with_suffix('.csv.tmp')
        with temporary.open('w', newline='') as completed:
            final = csv.DictWriter(completed, FIELDS, lineterminator='\n')
            final.writeheader()
            final.writerows(rows)
        temporary.replace(output)


if __name__ == '__main__':
    main()
