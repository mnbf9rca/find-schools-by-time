"""Generate the England postcode mask: uv run --with pyproj fixtures/make_origins.py.

Input: data/codepo_gb.zip. Output: fixtures/origins.csv.
Code-Point Open columns are documented in Doc/Code-Point_Open_Column_Headers.csv.
Quality 50 and 60 are estimated positions but still represent live postcodes.
The explicit Helmert pipeline keeps output independent of installed OSTN15 grids
and PROJ_NETWORK. Its metre-scale difference is irrelevant to 250 m matching.
"""
import csv
import io
from pathlib import Path
from zipfile import ZipFile

from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = '+proj=pipeline +step +inv +proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +step +proj=push +v_3 +step +proj=cart +ellps=airy +step +proj=helmert +x=446.448 +y=-125.157 +z=542.06 +rx=0.15 +ry=0.247 +rz=0.842 +s=-20.489 +convention=position_vector +step +inv +proj=cart +ellps=WGS84 +step +proj=pop +v_3 +step +proj=unitconvert +xy_in=rad +xy_out=deg'


def origin_id(easting, northing):
    """Identify a kilometre cell from integer OSGB36 metres."""
    return f'{easting // 1000}_{northing // 1000}'


def generate(archive):
    cells, postcodes = set(), 0
    with ZipFile(archive) as z:
        for name in sorted(z.namelist()):
            if not (name.startswith('Data/CSV/') and name.endswith('.csv')):
                continue
            with z.open(name) as raw, io.TextIOWrapper(raw, encoding='utf-8', newline='') as source:
                for row in csv.reader(source):
                    if row[4] != 'E92000001' or row[1] == '90':
                        continue
                    e, n = int(row[2]), int(row[3])
                    if e <= 0 or n <= 0:
                        raise ValueError(f'{name}: invalid coordinates for {row[0]}')
                    cells.add((e // 1000, n // 1000))
                    postcodes += 1
    if not cells:
        raise ValueError('Archive contains no usable England postcodes')
    transformer = Transformer.from_pipeline(PIPELINE)
    rows = []
    for e, n in sorted(cells):
        lng, lat = transformer.transform(e * 1000 + 500, n * 1000 + 500, errcheck=True)
        rows.append((origin_id(e * 1000, n * 1000), f'{lat:.6f}', f'{lng:.6f}'))
    return rows, postcodes


def write_csv(rows, output):
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(['id', 'lat', 'lng'])
    writer.writerows(rows)


def main():
    rows, postcodes = generate(ROOT / 'data/codepo_gb.zip')
    output = ROOT / 'fixtures/origins.csv'
    temporary = output.with_suffix('.csv.tmp')
    with temporary.open('w', newline='') as f:
        write_csv(rows, f)
    temporary.replace(output)
    print(f'{postcodes:,} England postcodes occupy {len(rows):,} origin cells.')


if __name__ == '__main__':
    main()
