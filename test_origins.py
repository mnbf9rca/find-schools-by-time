import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from pyproj import Transformer
from fixtures import make_origins, fetch_school_postcodes

ROOT = Path(__file__).resolve().parent


class TestOriginGrid(unittest.TestCase):
    def test_origin_id_floors_metres_at_cell_boundaries(self):
        for e, n, expected in [(489123, 510987, '489_510'), (999, 999, '0_0'),
                               (1000, 2000, '1_2'), (87000, 0, '87_0'),
                               (655999, 100999, '655_100'), (-1, -1, '-1_-1')]:
            with self.subTest(e=e, n=n):
                self.assertEqual(make_origins.origin_id(e, n), expected)

    def test_zip_filter_keeps_estimates_deduplicates_cells_and_sorts_numerically(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'codepo.zip'
            with ZipFile(archive, 'w') as z:
                z.writestr('Data/CSV/a.csv',
                           '"A1 1AA",10,100200,1200,E92000001,,,,,\n'
                           '"A1 1AB",50,87200,2400,E92000001,,,,,\n'
                           '"A1 1AC",60,87900,2800,E92000001,,,,,\n'
                           '"A1 1AD",10,87100,1100,E92000001,,,,,\n'
                           '"A1 1AE",90,0,0,E92000001,,,,,\n'
                           '"A1 1AF",10,200000,300000,W92000004,,,,,\n'
                           '"A1 1AG",10,300000,400000,S92000003,,,,,\n')
                z.writestr('Doc/ignored.csv', 'not postcode data\n')
            rows, count = make_origins.generate(archive)
        self.assertEqual(count, 4)
        self.assertEqual([r[0] for r in rows], ['87_1', '87_2', '100_1'])

    def test_committed_grid_has_unique_sorted_ids_and_correct_centres(self):
        with (ROOT / 'fixtures/origins.csv').open() as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, ['id', 'lat', 'lng'])
            rows = list(reader)
        cells = [tuple(map(int, r['id'].split('_'))) for r in rows]
        self.assertTrue(cells)
        self.assertEqual(len(cells), len(set(cells)))
        self.assertEqual(cells, sorted(cells))
        self.assertNotIn((0, 0), cells)
        transformer = Transformer.from_pipeline(make_origins.PIPELINE)
        eastings, northings = transformer.transform(
            [float(r['lng']) for r in rows], [float(r['lat']) for r in rows], direction='INVERSE')
        for row, (e, n), x, y in zip(rows, cells, eastings, northings):
            self.assertRegex(row['lat'], r'^-?\d+\.\d{6}$')
            self.assertRegex(row['lng'], r'^-?\d+\.\d{6}$')
            self.assertLess(abs(x - (e * 1000 + 500)), 0.1, row['id'])
            self.assertLess(abs(y - (n * 1000 + 500)), 0.1, row['id'])
            self.assertTrue(e * 1000 <= x < (e + 1) * 1000, row['id'])
            self.assertTrue(n * 1000 <= y < (n + 1) * 1000, row['id'])

    def test_school_postcodes_have_a_cell_or_one_of_eight_neighbours(self):
        with (ROOT / 'fixtures/origins.csv').open() as f:
            cells = {r['id'] for r in csv.DictReader(f)}
        with (ROOT / 'fixtures/school-postcodes.csv').open() as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, ['postcode', 'eastings', 'northings', 'source'])
            postcodes = list(reader)
        schools = json.loads((ROOT / 'schools.json').read_text())
        self.assertEqual({r['postcode'] for r in postcodes}, {s['postcode'] for s in schools})
        self.assertEqual(len(postcodes), len({r['postcode'] for r in postcodes}))
        fallback = []
        # The future Worker tries east, west, north, south, then NE, NW, SE, SW.
        neighbours = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)]
        for postcode in postcodes:
            self.assertIn(postcode['source'], ['postcodes', 'terminated_postcodes'])
            cell = make_origins.origin_id(int(postcode['eastings']), int(postcode['northings']))
            if cell not in cells:
                e, n = map(int, cell.split('_'))
                self.assertTrue(any(f'{e + de}_{n + dn}' in cells for de, dn in neighbours), postcode)
                fallback.append(postcode['postcode'])
        self.assertEqual(fallback, ['GL16 7EJ', 'OX18 2PY'])

    @unittest.skipUnless((ROOT / 'data/codepo_gb.zip').is_file(), 'Code-Point Open zip absent; skipping generator self-check')
    def test_generator_reproduces_committed_csv(self):
        rows, count = make_origins.generate(ROOT / 'data/codepo_gb.zip')
        out = io.StringIO(newline='')
        make_origins.write_csv(rows, out)
        self.assertEqual(out.getvalue(), (ROOT / 'fixtures/origins.csv').read_text())
        self.assertGreater(count, len(rows))


class TestSchoolPostcodeFetch(unittest.TestCase):
    def test_bulk_results_and_terminated_results_keep_input_postcodes(self):
        from unittest.mock import patch
        from urllib.parse import unquote
        postcodes = ['Tf6 6pn'] + [f'TEST {i:03}' for i in range(100)]
        def response(path, body=None):
            if path == '/postcodes':
                self.assertLessEqual(len(body['postcodes']), 100)
                return {'status': 200, 'result': [
                    {'query': p, 'result': None if p == 'TEST 099' else
                     {'postcode': p.upper(), 'eastings': 123456, 'northings': 234567}}
                    for p in reversed(body['postcodes'])]}
            self.assertEqual(unquote(path), '/terminated_postcodes/TEST 099')
            return {'status': 200, 'result': {'postcode': 'TEST 099', 'eastings': 345678,
                                            'northings': 456789, 'year_terminated': 2013,
                                            'month_terminated': 10, 'longitude': -2.5, 'latitude': 53.7}}
        with patch.object(fetch_school_postcodes, 'get_json', side_effect=response):
            rows = fetch_school_postcodes.fetch(postcodes)
        self.assertEqual(len(rows), 101)
        self.assertIn(('Tf6 6pn', 123456, 234567, 'postcodes'), rows)
        self.assertIn(('TEST 099', 345678, 456789, 'terminated_postcodes'), rows)
        self.assertEqual([r[0] for r in rows], sorted(postcodes))

    def test_missing_coordinates_fail_instead_of_creating_a_false_cell(self):
        from unittest.mock import patch
        for e in (None, 0, -1):
            data = {'status': 200, 'result': [{'query': 'TEST', 'result':
                    {'postcode': 'TEST', 'eastings': e, 'northings': 123456}}]}
            with patch.object(fetch_school_postcodes, 'get_json', return_value=data):
                with self.assertRaises(ValueError):
                    fetch_school_postcodes.fetch(['TEST'])


if __name__ == '__main__':
    unittest.main()
