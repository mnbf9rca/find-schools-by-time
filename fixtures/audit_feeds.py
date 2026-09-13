"""Audit GTFS zip files without reading stop times or shapes.

Run: uv run fixtures/audit_feeds.py <zip> [<zip> ...]
Self-test: uv run fixtures/audit_feeds.py --check
"""
import argparse
import csv
import io
import sys
import zipfile
from collections import Counter, defaultdict


def rows(archive, name):
    with archive.open(name) as raw, io.TextIOWrapper(raw, encoding='utf-8-sig', newline='') as text:
        yield from csv.DictReader(text)


def audit(source, output):
    with zipfile.ZipFile(source) as archive:
        agencies = {row.get('agency_id', ''): row['agency_name'] for row in rows(archive, 'agency.txt')}
        routes = {row['route_id']: row for row in rows(archive, 'routes.txt')}
        non_bus = {key for key, row in routes.items()
                   if int(row['route_type']) != 3 and not 200 <= int(row['route_type']) < 300
                   and not 700 <= int(row['route_type']) < 800}
        trips, destinations = Counter(), defaultdict(set)
        for row in rows(archive, 'trips.txt'):
            route = row['route_id']
            if route not in routes:
                raise ValueError(f'Trip references unknown route {route}')
            trips[route] += 1
            if route in non_bus and row.get('trip_headsign'):
                destinations[route].add(row['trip_headsign'])
    by_type, by_agency = defaultdict(Counter), defaultdict(Counter)
    for key, row in routes.items():
        agency = row.get('agency_id') or (next(iter(agencies)) if len(agencies) == 1 else '')
        row['agency_id'] = agency
        row['agency_name'] = agencies[agency]
        for counts in (by_type[int(row['route_type'])], by_agency[agency]):
            counts['routes'] += 1
            counts['trips'] += trips[key]
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(['Routes and trips by route_type'])
    writer.writerow(['route_type', 'routes', 'trips'])
    for kind, counts in sorted(by_type.items()):
        writer.writerow([kind, counts['routes'], counts['trips']])
    writer.writerow(['Routes and trips by agency'])
    writer.writerow(['agency_id', 'agency_name', 'routes', 'trips'])
    for agency, counts in sorted(by_agency.items()):
        writer.writerow([agency, agencies[agency], counts['routes'], counts['trips']])
    writer.writerow(['Routes other than bus or coach'])
    writer.writerow(['route_id', 'route_type', 'agency_id', 'agency_name', 'route_short_name',
                     'route_long_name', 'trips', 'trip_destinations'])
    for key in sorted(non_bus):
        row = routes[key]
        writer.writerow([key, row['route_type'], row['agency_id'], row['agency_name'],
                         row.get('route_short_name', ''), row.get('route_long_name', ''),
                         trips[key], '; '.join(sorted(destinations[key]))])


def check():
    """Catch wrong trip joins, missing empty routes, and bus or coach leakage."""
    source = io.BytesIO()
    with zipfile.ZipFile(source, 'w') as archive:
        archive.writestr('agency.txt', '\ufeffagency_id,agency_name\na,"Ferries, Ltd"\nb,Metro\n')
        archive.writestr('routes.txt', 'route_id,agency_id,route_type,route_short_name,route_long_name\n'
                         'f,a,4,F,"Harbour, Island"\ne,a,4,E,Empty crossing\n'
                         'b,a,3,B,Bus\nc,a,200,C,Coach\nx,a,700,X,Extended bus\nm,b,1,M,Metro line\n')
        archive.writestr('trips.txt', 'route_id,trip_id,trip_headsign\n'
                         'f,1,"Island, pier"\nm,2,City\nf,3,Harbour\nf,4,Harbour\n'
                         'b,5,Town\nc,6,Airport\nx,7,Station\n')
    output = io.StringIO()
    audit(source, output)
    rows = list(csv.reader(io.StringIO(output.getvalue())))
    assert ['4', '2', '3'] in rows, rows
    assert ['1', '1', '1'] in rows, rows
    assert ['a', 'Ferries, Ltd', '5', '6'] in rows, rows
    assert ['b', 'Metro', '1', '1'] in rows, rows
    assert ['f', '4', 'a', 'Ferries, Ltd', 'F', 'Harbour, Island', '3', 'Harbour; Island, pier'] in rows, rows
    assert ['e', '4', 'a', 'Ferries, Ltd', 'E', 'Empty crossing', '0', ''] in rows, rows
    assert not any(len(row) == 8 and row[0] in {'b', 'c', 'x'} for row in rows), rows
    print('ok')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zips', nargs='*')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        return check()
    if not args.zips:
        parser.error('provide at least one zip or --check')
    for source in args.zips:
        print(f'Feed: {source}')
        audit(source, sys.stdout)


if __name__ == '__main__':
    main()
