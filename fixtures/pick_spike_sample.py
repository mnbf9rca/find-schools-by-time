"""Pick the 100-school MOTIS spike sample (issue #2). Run from the repo root: python3 fixtures/pick_spike_sample.py"""
import csv, json, math
rows = json.load(open('schools.json'))
by = {r['urn']: r for r in rows}

# Hand-picked awkward cases: islands, ferries, borders, remote and thinly served areas.
SPECIAL = {
    '150099': 'island', '136753': 'ferry', '140845': 'ferry', '150935': 'island', '145119': 'island',
    '137598': 'border', '136979': 'border', '137382': 'border', '111424': 'border',
    '137107': 'remote', '112451': 'remote', '122328': 'remote', '144496': 'remote', '143981': 'remote',
    '121667': 'coast', '136217': 'coast', '112045': 'coast', '139553': 'coast', '118082': 'coast',
    '135290': 'marsh', '137282': 'fen', '136791': 'moor', '149645': 'moor', '148602': 'moor',
    '136902': 'lakes', '121689': 'dales', '142262': 'wolds', '150196': 'rural', '148737': 'rural',
}
assert len(SPECIAL) == 29 and all(u in by for u in SPECIAL)

def km(a, b):
    return math.hypot((a['lat'] - b['lat']) * 111.2, (a['lng'] - b['lng']) * 111.2 * math.cos(math.radians(52.5)))

# Density proxy: other schools with an A level cohort within 10 km.
pool = [r for r in rows if r['students'] is not None]
for r in pool:
    r['n10'] = sum(1 for s in pool if km(r, s) <= 10) - 1

# Biased towards sparse places: rural gets the most picks, dense urban the fewest.
BINS = [('rural', lambda n: n <= 3, 25), ('town', lambda n: 4 <= n <= 12, 22),
        ('suburban', lambda n: 13 <= n <= 40, 14), ('urban', lambda n: n > 20, 10)]

chosen = [dict(by[u], reason=w) for u, w in SPECIAL.items()]
for reason, test, count in BINS:
    cands = [r for r in pool if test(r['n10']) and r['urn'] not in {c['urn'] for c in chosen}]
    for _ in range(count):  # farthest-point sampling spreads each bin across the map
        if reason == 'urban':  # densest school at least 30 km from other urban picks: one city centre each
            urban = [c for c in chosen if c['reason'] == 'urban']
            best = max((r for r in cands if all(km(r, c) >= 30 for c in urban)), key=lambda r: r['n10'])
        else:
            best = max(cands, key=lambda r: min(km(r, c) for c in chosen))
        cands.remove(best)
        chosen.append(dict(best, reason=reason))
assert len(chosen) == 100 and len({c['urn'] for c in chosen}) == 100

with open('fixtures/spike-sample.csv', 'w', newline='') as f:
    w = csv.writer(f, lineterminator='\n')
    w.writerow(['urn', 'name', 'lat', 'lng', 'reason'])
    for c in chosen:
        w.writerow([c['urn'], c['name'], c['lat'], c['lng'], c['reason']])

# Scatter plot: every school in grey, the sample coloured by reason.
W, H = 600, 780
def xy(r):
    return (r['lng'] + 6.5) / 8.5 * W, H - (r['lat'] - 49.8) / 6.1 * H
COL = {'rural': '#1b9e77', 'town': '#d95f02', 'suburban': '#7570b3', 'urban': '#e7298a'}
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" style="background:#fff">']
for r in rows:
    x, y = xy(r); out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="1" fill="#ccc"/>')
for c in chosen:
    x, y = xy(c); out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="4" fill="{COL.get(c["reason"], "#1f78b4")}" stroke="#000" stroke-width="0.5"><title>{c["urn"]} {c["name"].replace("&", "&amp;")} ({c["reason"]})</title></circle>')
for i, (k, v) in enumerate([*COL.items(), ('other awkward case', '#1f78b4')]):
    out.append(f'<circle cx="20" cy="{20 + i * 18}" r="5" fill="{v}"/><text x="32" y="{25 + i * 18}" font-family="sans-serif" font-size="13">{k}</text>')
out.append('</svg>')
open('fixtures/spike-sample.svg', 'w').write('\n'.join(out))
from collections import Counter
print(Counter(c['reason'] for c in chosen))
