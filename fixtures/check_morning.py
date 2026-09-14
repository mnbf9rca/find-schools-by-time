"""Find complete trips arriving before 08:30 on 2026-09-16; stream stop_times.

Run: uv run fixtures/check_morning.py <zip> <route-id> [<route-id> ...]
Self-test: uv run fixtures/check_morning.py --check
"""
import io
import json
import sys
import zipfile
from audit_feeds import rows


def check():
    source = io.BytesIO()
    with zipfile.ZipFile(source, 'w') as z:
        z.writestr('calendar.txt', 'service_id,tuesday,wednesday,start_date,end_date\na,0,1,20260901,20260930\nc,0,1,20260901,20260930\np,1,0,20260901,20260930\n')
        z.writestr('calendar_dates.txt', 'service_id,date,exception_type\nc,20260916,2\nb,20260916,1\n')
        z.writestr('trips.txt', 'route_id,service_id,trip_id\nr,a,ok\nr,c,cancelled\nr,b,added\nr,a,late\nr,p,previous\n')
        z.writestr('stops.txt', 'stop_id,stop_name\nA,Mainland\nB,Island\n')
        z.writestr('stop_times.txt', 'trip_id,stop_id,stop_sequence,arrival_time,departure_time,pickup_type,drop_off_type\n'
                    'ok,B,2,07:00:00,07:00:00,1,0\nok,A,1,06:00:00,06:00:00,0,1\n'
                    'cancelled,A,1,01:00:00,01:00:00,0,1\ncancelled,B,2,02:00:00,02:00:00,1,0\n'
                    'added,A,1,05:00:00,05:00:00,0,1\nadded,B,2,06:00:00,06:00:00,1,0\n'
                    'late,A,1,24:00:00,24:00:00,0,1\nlate,B,2,25:00:00,25:00:00,1,0\n'
                    'previous,A,1,24:30:00,24:30:00,0,1\nprevious,B,2,25:00:00,25:00:00,1,0\n')
    result = morning(source, {'r'})
    assert len(result) == 1 and result[0]['trip'] == 'previous', result
    assert result[0]['qualifying_trips'] == 3, result
    assert result[0]['departure'] == '00:30:00' and result[0]['service_date'] == '20260915'
    print('ok')


def morning(source, wanted):
    with zipfile.ZipFile(source) as z:
        active = {'20260915': set(), '20260916': set()}
        if 'calendar.txt' in z.namelist():
            for r in rows(z, 'calendar.txt'):
                for date, weekday in [('20260915', 'tuesday'), ('20260916', 'wednesday')]:
                    if r['start_date'] <= date <= r['end_date'] and r[weekday] == '1':
                        active[date].add(r['service_id'])
        if 'calendar_dates.txt' in z.namelist():
            for r in rows(z, 'calendar_dates.txt'):
                if r['date'] in active:
                    if r['exception_type'] == '1':
                        active[r['date']].add(r['service_id'])
                    elif r['exception_type'] == '2':
                        active[r['date']].discard(r['service_id'])
        trips = {r['trip_id']: r for r in rows(z, 'trips.txt')
                 if r['route_id'] in wanted and any(r['service_id'] in services for services in active.values())}
        stops = {r['stop_id']: r['stop_name'] for r in rows(z, 'stops.txt')}
        ends = {}
        for r in rows(z, 'stop_times.txt'):
            if r['trip_id'] not in trips:
                continue
            first, last = ends.setdefault(r['trip_id'], [None, None])
            sequence = int(r['stop_sequence'])
            if r.get('pickup_type', '0') != '1' and r['departure_time'] and (first is None or sequence < int(first['stop_sequence'])):
                ends[r['trip_id']][0] = r
            if r.get('drop_off_type', '0') != '1' and r['arrival_time'] and (last is None or sequence > int(last['stop_sequence'])):
                ends[r['trip_id']][1] = r
    best, counts = {}, {}
    for trip, (first, last) in ends.items():
        if first is None or last is None or int(first['stop_sequence']) >= int(last['stop_sequence']):
            continue
        departure = sum(int(v) * scale for v, scale in zip(first['departure_time'].split(':'), (3600, 60, 1)))
        arrival = sum(int(v) * scale for v, scale in zip(last['arrival_time'].split(':'), (3600, 60, 1)))
        for date, offset in [('20260915', 86400), ('20260916', 0)]:
            if trips[trip]['service_id'] not in active[date] or not 0 <= departure - offset < arrival - offset < 30600:
                continue
            key = (trips[trip]['route_id'], first['stop_id'], last['stop_id'])
            counts[key] = counts.get(key, 0) + 1
            clock = lambda t: f'{t // 3600:02}:{t // 60 % 60:02}:{t % 60:02}'
            candidate = dict(route=key[0], trip=trip, service=trips[trip]['service_id'], service_date=date,
                             from_stop=key[1], to_stop=key[2], origin=stops[key[1]], destination=stops[key[2]],
                             departure=clock(departure - offset), arrival=clock(arrival - offset))
            if key not in best or departure - offset < best[key][0]:
                best[key] = (departure - offset, candidate)
    return [dict(best[key][1], qualifying_trips=counts[key]) for key in sorted(best)]


if __name__ == '__main__':
    if sys.argv[1:] == ['--check']:
        check()
    else:
        print(json.dumps(morning(sys.argv[1], set(sys.argv[2:])), indent=2))
