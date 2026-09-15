"""Validate local origin records: uv run --with pyproj fixtures/validate_dataset.py VERSION.

--partial skips uncomputed sample schools and pending planner comparisons; all
other thresholds remain unchanged. Exceptions require committed, reviewed reasons.
"""
import argparse
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct

from pyproj import Transformer
from pyproj.enums import TransformDirection

if __package__:
    from . import make_origins, record
    from .check_dataset_manifest import validate as check_manifest
else:
    import make_origins
    import record
    from check_dataset_manifest import validate as check_manifest

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('Completeness and value range', 'Manifest', 'Empty origins', 'Mode sanity',
         'Reach distance', 'Walk coverage', 'Reachable counts', 'Spike journeys', 'New samples')


def rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def validate(directory, *, root=ROOT, partial=False, emit=print):
    directory, root = Path(directory), Path(root)
    fixtures = root / 'fixtures'
    checks = {i: {'status': 'PASS', 'failures': 0, 'skipped': 0, 'pending': 0}
              for i in range(1, 10)}

    def fail(check, message):
        checks[check]['status'] = 'FAIL'
        checks[check]['failures'] += 1
        emit(f'FAIL {check}: {message}')

    manifest = json.loads((directory / 'manifest.json').read_text())
    run = manifest.get('run') if isinstance(manifest, dict) else None
    counter = run.get('walk_missing_pairs', 'absent') if isinstance(run, dict) else 'invalid run object'
    emit(f'Check 6: manifest walk_missing_pairs={counter}')
    for error in check_manifest(manifest):
        fail(2, error)
    if not isinstance(manifest, dict):
        manifest = {}
    origins = rows(fixtures / 'origins.csv')
    schools = sorted(json.loads((root / 'schools.json').read_text()), key=lambda s: s['urn'])
    school_indices = {s['urn']: i for i, s in enumerate(schools)}
    count = record.SCHOOL_COUNT
    if manifest.get('school_count') != count or len(schools) != count:
        fail(2, 'school_count differs from the full school index')
        count = len(schools)
    if manifest.get('origins_sha256') != hashlib.sha256((fixtures / 'origins.csv').read_bytes()).hexdigest():
        fail(2, 'origins_sha256 differs from fixtures/origins.csv')
    if manifest.get('school_index_sha256') != record.school_index_hash(school_indices):
        fail(2, 'school_index_sha256 differs from schools.json')

    def exceptions(name, key, check):
        result = set()
        for row in rows(fixtures / name):
            if not row['reason'].strip():
                fail(check, f'{name}: {row[key]} has no reason')
            else:
                result.add(row[key])
        return result

    unreachable = exceptions('unreachable-origins.csv', 'origin_id', 3)
    unmatched = exceptions('unmatched-schools.csv', 'urn', 6)
    origin_ids = {o['id'] for o in origins}
    files = {p.stem for p in directory.glob('*.bin')}
    if len(files) != manifest.get('origin_count') or len(origins) != manifest.get('origin_count'):
        fail(1, f'object count {len(files)}, grid count {len(origins)}, manifest origin_count {manifest.get("origin_count")}')
    for oid in sorted(files - origin_ids):
        fail(1, f'unexpected origin record {oid}')
    if len(origin_ids) != len(origins):
        fail(1, 'duplicate origin identifiers in fixtures/origins.csv')

    transformer = Transformer.from_pipeline(make_origins.PIPELINE)
    school_xy = [transformer.transform(s['lng'], s['lat'], direction=TransformDirection.INVERSE,
                                       errcheck=True) for s in schools]
    completed = {p.stem for p in (directory.parent / 'schools').glob('*.bin')}
    if partial and not completed:
        fail(6, '--partial requires completed school files in the sibling schools directory')
    active = completed if partial else set(school_indices)
    nearby = {}
    excluded_schools = 0
    for i, (school, (e, n)) in enumerate(zip(schools, school_xy)):
        if school['urn'] not in active or school['urn'] in unmatched:
            excluded_schools += 1
            continue
        for x in range(math.floor((e - 2500) / 1000), math.floor((e + 1500) / 1000) + 1):
            for y in range(math.floor((n - 2500) / 1000), math.floor((n + 1500) / 1000) + 1):
                oid = f'{x}_{y}'
                if oid in origin_ids and oid not in unreachable and math.hypot(x * 1000 + 500 - e, y * 1000 + 500 - n) <= 2000:
                    nearby.setdefault(oid, []).append(i)
    checks[6]['excluded_schools'] = excluded_schools
    checks[6]['pairs_checked'] = sum(map(len, nearby.values()))
    checks[6]['missing_pairs'] = 0
    counts = [[] for _ in record.MODES]
    greatest = [0.0] * 4
    comparable, slower = [0] * 4, [0] * 4
    size = 8 * count
    for number, origin in enumerate(origins, 1):
        oid = origin['id']
        path = directory / f'{oid}.bin'
        if not path.exists():
            fail(1, f'missing origin record {oid}')
            continue
        if path.stat().st_size != size:
            fail(1, f'{oid}: record length {path.stat().st_size}, expected {size}')
            continue
        data = path.read_bytes()
        values = struct.unpack(f'<{4 * count}H', data)
        planes = [values[m * count:(m + 1) * count] for m in range(4)]
        totals = [0] * 4
        empty = True
        e, n = (int(k) * 1000 + 500 for k in oid.split('_'))
        for i, pair in enumerate(zip(*planes)):
            if pair == (record.SENTINEL,) * 4:
                continue
            empty = False
            valid = tuple(v <= record.CAP for v in pair)
            for mode, v in enumerate(pair):
                if record.CAP < v < record.SENTINEL:
                    fail(1, f'{oid} {schools[i]["urn"]} {record.MODES[mode]}: invalid value {v}')
            if not any(valid):
                continue
            distance = math.hypot(e - school_xy[i][0], n - school_xy[i][1]) / 1000
            for mode in range(4):
                if valid[mode]:
                    totals[mode] += 1
                    greatest[mode] = max(greatest[mode], distance)
            pt, walk, cycle, drive = pair
            if valid[1]:
                if pt > walk:
                    fail(4, f'{oid} {schools[i]["urn"]}: public transport {pt} exceeds walking {walk}')
                if distance > 7.5:
                    fail(5, f'{oid} {schools[i]["urn"]}: walking reaches {distance:.3f} km, above 7.5 km')
                for mode in (2, 3):
                    if valid[mode]:
                        comparable[mode] += 1
                        slower[mode] += pair[mode] > walk
        for mode, total in enumerate(totals):
            counts[mode].append(total)
        if empty and oid not in unreachable:
            fail(3, f'{oid}: all four planes are empty')
        for i in nearby.get(oid, []):
            if planes[1][i] == record.SENTINEL:
                checks[6]['missing_pairs'] += 1
                emit(f'Check 6 evidence: {oid} {schools[i]["urn"]}: no walking value within 2 km')
        del data, values, planes
        if number % 10000 == 0:
            emit(f'Read {number}/{len(origins)} records')

    for mode in (2, 3):
        emit(f'Check 4: {record.MODES[mode]} slower than walking in {slower[mode]}/{comparable[mode]} comparable pairs')
        if slower[mode] * 50 > comparable[mode]:
            fail(4, f'{record.MODES[mode]} exceeds walking in more than 2 percent of comparable pairs')
    missing, near = checks[6]['missing_pairs'], checks[6]['pairs_checked']
    emit(f'Check 6: {missing}/{near} nearby pairs have no walking value')
    if missing * 20 > near:
        fail(6, 'missing walks exceed 5 percent of nearby pairs')
    checks[5]['maximum_km'] = dict(zip(record.MODES, greatest))
    emit(f'Check 5: maximum distances km {checks[5]["maximum_km"]}')
    if greatest[2] >= 27:
        fail(5, f'cycling reaches {greatest[2]:.3f} km, at or beyond the 27 km physical bound')
    checks[7]['counts'] = {mode: {'min': min(c) if c else 0, 'median': statistics.median(c) if c else 0,
                                 'max': max(c) if c else 0} for mode, c in zip(record.MODES, counts)}
    emit(f'Check 7: reachable schools {checks[7]["counts"]}')
    if checks[7]['counts']['driving']['median'] < 50:
        fail(7, 'driving median is below 50 reachable schools')

    def stored(check, oid, urn, mode):
        if urn not in school_indices or oid not in origin_ids or mode not in record.MODES:
            fail(check, f'unknown origin, school or mode: {oid} {urn} {mode}')
            return None
        if partial and urn not in completed:
            if check == 8:
                checks[check]['skipped'] += 1
                emit(f'SKIPPED {check}: {oid} {urn} {mode}: school not computed in this sample')
            else:
                fail(check, f'{oid} {urn} {mode}: school not computed in this sample')
            return None
        try:
            return record.decode((directory / f'{oid}.bin').read_bytes(), record.MODES.index(mode), school_indices[urn])
        except (OSError, ValueError) as error:
            fail(check, f'{oid} {urn}: {error}')
            return None

    disagreements = []

    def compare(check, label, value, seconds, note=''):
        if value is None:
            return
        if not math.isfinite(seconds) or seconds < 0:
            fail(check, f'{label}: invalid planner time')
        elif value == record.SENTINEL or abs(value // 600 - int(seconds // 600)) > 1:
            message = f'{label}: stored {value} seconds, planner {seconds:g} seconds differ by more than one band'
            if check == 9:
                disagreements.append((message, note))
            else:
                fail(check, message)
        else:
            emit(f'PASS {check}: {label}: stored {value} seconds, planner {seconds:g} seconds')

    for row in rows(fixtures / 'validation-spike.csv'):
        e, n = transformer.transform(float(row['lng']), float(row['lat']), direction=TransformDirection.INVERSE, errcheck=True)
        oid = make_origins.origin_id(round(e), round(n))
        label = f'{oid} {row["urn"]} {row["mode"]}'
        value = stored(8, oid, row['urn'], row['mode'])
        compare(8, label, value, float(row['planner_leave_by_minutes']) * 60)

    for row in rows(fixtures / 'validation-samples.csv'):
        label = f'{row["origin_id"]} {row["urn"]} {row["mode"]}'
        pt = row['mode'] == 'public_transport'
        planner = row['planner_departure'].strip() if pt else row['planner_minutes'].strip()
        if not planner:
            checks[9]['pending'] += 1
            emit(f'PENDING 9: {label}: planner comparison unfilled')
            if not partial:
                fail(9, f'{label}: planner comparison is pending')
            continue
        value = stored(9, row['origin_id'], row['urn'], row['mode'])
        try:
            if planner == 'beyond cap':
                seconds = record.CAP + 1
            elif pt:
                departure = datetime.strptime(planner, '%H:%M')
                seconds = (8 * 60 + 30 - departure.hour * 60 - departure.minute) * 60
            else:
                seconds = float(planner) * 60
        except ValueError:
            fail(9, f'{label}: invalid planner value {planner!r}')
            continue
        if not math.isfinite(seconds) or seconds < 0:
            fail(9, f'{label}: invalid planner time')
            continue
        note = (row.get('note') or '').strip()
        beyond_cap = (planner == 'beyond cap' or row['planner_minutes'].strip() == 'beyond cap'
                      or (not pt and math.isfinite(seconds) and seconds > record.CAP))
        if pt and value == record.SENTINEL and math.isfinite(seconds) and seconds >= record.CAP - 600:
            emit(f'PASS 9: {label}: stored sentinel, planner {seconds:g} seconds is within one band of the cap or beyond')
        elif (row['mode'] == 'driving' and value is not None and value <= record.CAP
              and math.isfinite(seconds) and 0 <= value <= seconds):
            emit(f'PASS 9: {label}: stored {value} seconds is below planner {seconds:g} seconds')
        elif value is not None and beyond_cap:
            if value != record.SENTINEL or seconds <= record.CAP:
                disagreements.append((f'{label}: beyond-cap claim disagrees with stored value or planner departure', note))
            else:
                emit(f'PASS 9: {label}: both beyond cap')
        else:
            compare(9, label, value, seconds, note)

    for message, note in disagreements:
        if len(disagreements) == 1 and note:
            emit(f'DOCUMENTED 9: {message}; {note}')
        else:
            fail(9, message)

    if partial:
        emit(f'Partial mode: {len(completed & set(school_indices))} of {len(schools)} schools covered')
    for i, check in checks.items():
        if check['status'] != 'FAIL':
            if check['pending']:
                check['status'] = 'PENDING'
            elif check['skipped']:
                check['status'] = 'SKIPPED'
        emit(f'Check {i} {NAMES[i-1]}: {check["status"]}; failures={check["failures"]}, skipped={check["skipped"]}, pending={check["pending"]}')
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--partial', action='store_true')
    args = parser.parse_args()
    try:
        result = validate(args.directory, partial=args.partial)
    except (OSError, ValueError, KeyError) as error:
        print(f'Validation failed: {error}')
        return 1
    return int(any(c['status'] == 'FAIL' for c in result.values()))


if __name__ == '__main__':
    raise SystemExit(main())
