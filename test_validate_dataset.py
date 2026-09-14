import copy
import csv
import json
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from pyproj import Transformer
from fixtures import make_origins, record
from fixtures.check_dataset_manifest import validate as validate_manifest
from test_dataset_manifest import MANIFEST

from fixtures import validate_dataset as vd


class DatasetValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixtures = self.root / 'fixtures'
        self.fixtures.mkdir()
        self.directory = self.root / 'output' / '20260914T093000Z'
        self.directory.mkdir(parents=True)
        self.patch = patch.object(record, 'SCHOOL_COUNT', 50)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        transformer = Transformer.from_pipeline(make_origins.PIPELINE)
        self.positions = [transformer.transform(e, 200500) for e in (500500, 501500)]
        self.ids = ['500_200', '501_200']
        self.write_csv('origins.csv', ['id', 'lat', 'lng'],
                       [(oid, lat, lng) for oid, (lng, lat) in zip(self.ids, self.positions)])
        lng, lat = self.positions[0]
        schools = [{'urn': str(100000 + i), 'lat': lat, 'lng': lng} for i in range(50)]
        (self.root / 'schools.json').write_text(json.dumps(schools))
        self.write_csv('unreachable-origins.csv', ['origin_id', 'reason'], [])
        self.write_csv('unmatched-schools.csv', ['urn', 'reason'], [])
        self.write_csv('validation-spike.csv', ['lat', 'lng', 'urn', 'mode', 'planner_leave_by_minutes', 'source'],
                       [(lat, lng, '100000', 'public_transport', 10, 'test planner')])
        self.write_csv('validation-samples.csv', ['origin_id', 'urn', 'mode', 'planner_minutes', 'planner_departure', 'character'],
                       [('500_200', '100000', 'public_transport', 1, '08:20', 'test')])
        checkpoint = self.directory.parent / 'schools'
        checkpoint.mkdir()
        for i in range(50):
            (checkpoint / f'{100000 + i}.bin').write_bytes(b'')
        self.values = [[600] * 50, [600] * 50, [500] * 50, [400] * 50]
        for oid in self.ids:
            self.write_record(oid, self.values)
        self.manifest = copy.deepcopy(MANIFEST)
        self.manifest.update(origin_count=2, school_count=50,
                             origins_sha256=hashlib.sha256((self.fixtures/'origins.csv').read_bytes()).hexdigest(),
                             school_index_sha256=record.school_index_hash(s['urn'] for s in schools))
        self.manifest['shards'] = {'records_per_shard': 8000, 'count': 1, 'record_bytes': 400}
        self.manifest['run']['walk_missing_pairs'] = 0
        self.save_manifest()

    def write_csv(self, name, header, rows):
        with (self.fixtures / name).open('w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

    def write_record(self, oid, planes):
        (self.directory / f'{oid}.bin').write_bytes(struct.pack('<200H', *(v for plane in planes for v in plane)))

    def save_manifest(self):
        (self.directory / 'manifest.json').write_text(json.dumps(self.manifest))

    def run_validation(self, partial=False):
        self.messages = []
        return vd.validate(self.directory, root=self.root, partial=partial, emit=self.messages.append)

    def test_all_checks_pass_and_inverse_coordinates_are_integer_cells(self):
        self.assertEqual(validate_manifest(self.manifest), [])
        result = self.run_validation()
        self.assertTrue(all(c['status'] == 'PASS' for c in result.values()), result)

    def test_check_1_reports_missing_extra_short_and_invalid_values(self):
        (self.directory / '501_200.bin').unlink()
        (self.directory / '999_999.bin').write_bytes(b'bad')
        values = copy.deepcopy(self.values)
        values[2][0] = 5401
        self.write_record('500_200', values)
        result = self.run_validation()
        self.assertEqual(result[1]['status'], 'FAIL')
        text = '\n'.join(self.messages)
        for word in ('501_200', '999_999', '5401'):
            self.assertIn(word, text)
        (self.directory / '500_200.bin').write_bytes(b'bad')
        self.assertEqual(self.run_validation()[1]['status'], 'FAIL')

    def test_check_2_rejects_schema_and_both_hash_mismatches(self):
        del self.manifest['shards']
        self.manifest['origins_sha256'] = 'bad'
        self.manifest['school_index_sha256'] = 'bad'
        self.save_manifest()
        self.assertEqual(self.run_validation()[2]['status'], 'FAIL')
        for key in ('shards', 'origins_sha256', 'school_index_sha256'):
            self.assertIn(key, '\n'.join(self.messages))

    def test_bad_manifest_count_does_not_hide_record_failures(self):
        self.manifest['school_count'] = 49
        self.save_manifest()
        values = copy.deepcopy(self.values)
        values[2][0] = 5401
        self.write_record('500_200', values)
        result = self.run_validation()
        self.assertEqual(result[2]['status'], 'FAIL')
        self.assertEqual(result[1]['status'], 'FAIL')
        self.assertIn('Check 9', '\n'.join(self.messages))

    def test_malformed_manifest_run_reports_schema_failure_and_continues(self):
        self.manifest['run'] = None
        self.save_manifest()
        result = self.run_validation()
        self.assertEqual(result[2]['status'], 'FAIL')
        self.assertIn('Check 9', '\n'.join(self.messages))

    def test_corrupt_origin_is_not_reported_as_all_sentinel(self):
        self.write_record('501_200', [[5401] * 50 for _ in range(4)])
        result = self.run_validation()
        self.assertEqual(result[1]['status'], 'FAIL')
        self.assertEqual(result[3]['status'], 'PASS')

    def test_partial_does_not_skip_filled_new_planner_comparisons(self):
        (self.directory.parent / 'schools/100000.bin').unlink()
        self.write_csv('validation-samples.csv',
                       ['origin_id', 'urn', 'mode', 'planner_minutes', 'planner_departure', 'character'],
                       [('500_200', '100000', 'public_transport', 10, '07:30', 'test')])
        self.assertEqual(self.run_validation(partial=True)[9]['status'], 'FAIL')

    def test_check_3_requires_reasoned_empty_origin_exception(self):
        self.write_record('501_200', [[65535] * 50 for _ in range(4)])
        self.assertEqual(self.run_validation()[3]['status'], 'FAIL')
        self.write_csv('unreachable-origins.csv', ['origin_id', 'reason'], [('501_200', 'Confirmed offshore test cell')])
        self.assertEqual(self.run_validation()[3]['status'], 'PASS')

    def test_check_4_transit_sentinel_and_two_percent_threshold(self):
        values = copy.deepcopy(self.values)
        values[0][0] = 65535
        self.write_record('500_200', values)
        self.assertEqual(self.run_validation()[4]['status'], 'FAIL')
        values[0][0] = 600
        values[2][0] = 700
        self.write_record('500_200', values)
        self.assertEqual(self.run_validation()[4]['status'], 'PASS')
        values[2][1] = 700
        self.write_record('500_200', values)
        self.assertEqual(self.run_validation()[4]['status'], 'PASS')
        values[2][2] = 700
        self.write_record('500_200', values)
        self.assertEqual(self.run_validation()[4]['status'], 'FAIL')
        values[2] = [500] * 50
        values[3][:3] = [700, 700, 700]
        self.write_record('500_200', values)
        self.assertEqual(self.run_validation()[4]['status'], 'FAIL')

    def test_check_5_walk_limit_and_measured_edges(self):
        schools = json.loads((self.root / 'schools.json').read_text())
        transformer = Transformer.from_pipeline(make_origins.PIPELINE)
        for mode, distance in [(1, 7600), (0, 81300), (2, 22200), (3, 122900)]:
            with self.subTest(mode=mode):
                lng, lat = transformer.transform(500500 + distance, 200500)
                schools[0].update(lng=lng, lat=lat)
                (self.root / 'schools.json').write_text(json.dumps(schools))
                values = copy.deepcopy(self.values)
                for plane in values: plane[0] = 65535
                values[mode][0] = 600
                self.write_record('500_200', values)
                self.write_record('501_200', values)
                self.assertEqual(self.run_validation()[5]['status'], 'FAIL')

    def test_check_6_nearby_missing_walk_and_school_or_origin_exclusions(self):
        values = copy.deepcopy(self.values)
        values[1][:5] = [65535] * 5
        self.write_record('500_200', values)
        self.assertEqual(self.run_validation()[6]['status'], 'PASS')
        self.assertIn('500_200 100000', '\n'.join(self.messages))
        values[1][5] = 65535
        self.write_record('500_200', values)
        self.manifest['run']['walk_missing_pairs'] = 6
        self.save_manifest()
        self.assertEqual(self.run_validation()[6]['status'], 'FAIL')
        self.assertIn('walk_missing_pairs=6', self.messages[0])
        self.write_csv('unmatched-schools.csv', ['urn', 'reason'], [('100000', 'Confirmed test coordinate miss'), ('100001', 'Confirmed test coordinate miss')])
        self.assertEqual(self.run_validation()[6]['status'], 'PASS')
        self.write_csv('unmatched-schools.csv', ['urn', 'reason'], [])
        self.write_csv('unreachable-origins.csv', ['origin_id', 'reason'], [('500_200', 'Confirmed offshore test cell')])
        self.assertEqual(self.run_validation()[6]['status'], 'PASS')

    def test_check_7_driving_median_below_50_fails(self):
        values = copy.deepcopy(self.values)
        values[3][0] = 65535
        for oid in self.ids: self.write_record(oid, values)
        result = self.run_validation()
        self.assertEqual(result[7]['status'], 'FAIL')
        self.assertEqual(result[7]['counts']['driving'], {'min': 49, 'median': 49.0, 'max': 49})

    def test_check_8_uses_bands_and_skips_only_uncomputed_sample_schools(self):
        lng, lat = self.positions[0]
        self.write_csv('validation-spike.csv', ['lat', 'lng', 'urn', 'mode', 'planner_leave_by_minutes', 'source'],
                       [(lat, lng, '100000', 'public_transport', 30, 'test planner')])
        self.assertEqual(self.run_validation()[8]['status'], 'FAIL')
        self.assertEqual(self.run_validation(partial=True)[8]['status'], 'FAIL')
        self.write_record('500_200', [[65535] * 50 for _ in range(4)])
        checkpoint = self.directory.parent / 'schools'
        for path in checkpoint.glob('*.bin'): path.unlink()
        (checkpoint / '100001.bin').write_bytes(b'')
        result = self.run_validation(partial=True)
        self.assertEqual(result[8]['status'], 'SKIPPED')
        self.assertIn('Partial mode: 1 of 50 schools covered', self.messages)
        self.assertEqual(self.run_validation()[8]['status'], 'FAIL')

    def test_check_9_pending_departure_leave_by_and_beyond_cap(self):
        columns = ['origin_id', 'urn', 'mode', 'planner_minutes', 'planner_departure', 'character']
        self.write_csv('validation-samples.csv', columns, [('500_200', '100000', 'public_transport', 10, '', 'test')])
        self.assertEqual(self.run_validation()[9]['status'], 'FAIL')
        self.assertEqual(self.run_validation(partial=True)[9]['status'], 'PENDING')
        self.write_csv('validation-samples.csv', columns, [('500_200', '100000', 'public_transport', 10, '07:30', 'test')])
        self.assertEqual(self.run_validation()[9]['status'], 'FAIL')
        values = copy.deepcopy(self.values)
        values[0][0] = values[1][0] = 65535
        self.write_record('500_200', values)
        self.write_csv('validation-samples.csv', columns, [('500_200', '100000', 'public_transport', 'beyond cap', '06:30', 'test')])
        self.assertEqual(self.run_validation()[9]['status'], 'PASS')
        self.write_csv('validation-samples.csv', columns, [('500_200', '100000', 'public_transport', 'beyond cap', '07:30', 'test')])
        self.assertEqual(self.run_validation()[9]['status'], 'FAIL')
        self.write_csv('validation-samples.csv', columns, [('500_200', '100000', 'public_transport', '', 'beyond cap', 'test')])
        self.assertEqual(self.run_validation()[9]['status'], 'PASS')
        values[0][0] = 600
        self.write_record('500_200', values)
        self.assertEqual(self.run_validation()[9]['status'], 'FAIL')
        self.write_csv('validation-samples.csv', columns, [('500_200', '100000', 'walking', 40, '', 'test')])
        self.assertEqual(self.run_validation()[9]['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
