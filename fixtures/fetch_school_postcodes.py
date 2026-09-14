"""Refresh the offline school postcode fixture: uv run fixtures/fetch_school_postcodes.py.

Source: postcodes.io bulk lookup, then terminated lookup for missing live units.
https://postcodes.io/docs/api/bulk-postcode-lookup/
https://postcodes.io/docs/api/lookup-terminated-postcode/
Both responses supply integer eastings and northings; no transform is needed.
Input postcode spelling is preserved so the fixture covers schools.json exactly.
Output is replaced only after every distinct school postcode has coordinates.
"""
import csv
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def get_json(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    request = Request('https://api.postcodes.io' + path, data=data,
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result['status'] != 200:
        raise ValueError(f'{path}: {result}')
    return result


def fetch(postcodes):
    rows = []
    postcodes = sorted(set(postcodes))
    for offset in range(0, len(postcodes), 100):
        batch = postcodes[offset:offset + 100]
        data = get_json('/postcodes', {'postcodes': batch})['result']
        results = {item['query']: item['result'] for item in data}
        if len(data) != len(batch) or set(results) != set(batch):
            raise ValueError('Bulk lookup did not return every requested postcode')
        for postcode in batch:
            result, source = results[postcode], 'postcodes'
            if result is None:
                result = get_json('/terminated_postcodes/' + quote(postcode, safe=''))['result']
                source = 'terminated_postcodes'
            e, n = result['eastings'], result['northings']
            if type(e) is not int or type(n) is not int or e <= 0 or n <= 0:
                raise ValueError(f'{postcode}: unusable coordinates {e}, {n}')
            rows.append((postcode, e, n, source))
        print(f'Fetched {len(rows)} of {len(postcodes)} school postcodes.', flush=True)
    return rows


def main():
    schools = json.loads((ROOT / 'schools.json').read_text())
    rows = fetch(school['postcode'] for school in schools)
    output = ROOT / 'fixtures/school-postcodes.csv'
    temporary = output.with_suffix('.csv.tmp')
    with temporary.open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['postcode', 'eastings', 'northings', 'source'])
        writer.writerows(rows)
    temporary.replace(output)
    terminated = sum(row[3] == 'terminated_postcodes' for row in rows)
    print(f'Wrote {len(rows)} school postcodes, including {terminated} terminated postcodes.')


if __name__ == '__main__':
    main()
