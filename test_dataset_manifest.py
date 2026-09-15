import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from fixtures.check_dataset_manifest import validate


MANIFEST = {
    'version': '20260914T093000Z', 'routing_date': '2026-09-16',
    'routing_time': '08:30', 'timezone': 'Europe/London', 'motis_version': '2.11.3',
    'modes': ['public_transport', 'walking', 'cycling', 'driving'],
    'cap_seconds': 5400, 'display_band_minutes': 10, 'unreachable': 65535,
    'compression': 'none', 'rounding': 'half up to whole seconds, then compared with 5400',
    'max_pre_transit_seconds': 1800, 'max_post_transit_seconds': 900,
    'cycling_speed_mps': 5.0, 'pruning_radii_km': [90, 90, 25, 136],
    'origin_count': 93217, 'origins_sha256': 'a' * 64, 'school_count': 4373,
    'school_index_sha256': 'b' * 64,
    'shards': {'records_per_shard': 8000, 'count': 12, 'record_bytes': 34984},
    'keys': {'shard': '20260914T093000Z/shard-{nn}.bin',
             'origins': '20260914T093000Z/origins.txt',
             'manifest': '20260914T093000Z/manifest.json', 'current': 'current.json'},
    'feeds': [{'path': 'motis-spike/feeds/bods.zip', 'sha256': 'c' * 64}],
    'run': {'started': '2026-09-14T09:30:00Z', 'wall_seconds': 4412, 'workers': 8,
            'requests': 26238, 'peak_server_rss_bytes': 9448928051,
            'fallback_origins': 1120, 'fallback_requests': 3360,
            'output_bytes': 3761103528},
}


class DatasetManifestTests(unittest.TestCase):
    def test_valid_manifest(self):
        self.assertEqual(validate(MANIFEST), [])
        manifest = copy.deepcopy(MANIFEST)
        manifest['pruning_radii_km'] = [None, None, 30, None]
        self.assertEqual(validate(manifest), [])
        manifest['run'].update(requests_retried=1, transpose_seconds=0.25,
                               schools_completed=4373, school_bytes=100,
                               record_bytes=200, fallback_bytes=10, walk_missing_pairs=0,
                               walk_nearby_pairs=10)
        self.assertEqual(validate(manifest), [])

    def test_rejects_invalid_fields_at_every_level(self):
        cases = [
            ((), 'version', None, '$.version'),
            ((), 'max_pre_transit_seconds', None, '$.max_pre_transit_seconds'),
            ((), 'max_post_transit_seconds', None, '$.max_post_transit_seconds'),
            ((), 'max_pre_transit_seconds', '1800', '$.max_pre_transit_seconds'),
            ((), 'shards', None, '$.shards'),
            ((), 'keys', None, '$.keys'),
            (('shards',), 'count', '12', '$.shards.count'),
            (('keys',), 'shard', 1, '$.keys.shard'),
            ((), 'school_count', '4373', '$.school_count'),
            ((), 'school_count', True, '$.school_count'),
            ((), 'cycling_speed_mps', True, '$.cycling_speed_mps'),
            ((), 'unexpected', 1, '$.unexpected'),
            (('feeds', 0), 'sha256', None, '$.feeds[0].sha256'),
            (('feeds', 0), 'unexpected', 1, '$.feeds[0].unexpected'),
            (('run',), 'requests', None, '$.run.requests'),
            (('run',), 'fallback_origins', None, '$.run.fallback_origins'),
            (('run',), 'fallback_requests', None, '$.run.fallback_requests'),
            (('run',), 'fallback_requests', '3', '$.run.fallback_requests'),
            (('run',), 'fallback_bytes', '10', '$.run.fallback_bytes'),
            (('run',), 'wall_seconds', '4412', '$.run.wall_seconds'),
            (('run',), 'unexpected', 1, '$.run.unexpected'),
            ((), 'pruning_radii_km', [90, 90, 25], '$.pruning_radii_km'),
            ((), 'pruning_radii_km', [90, 90, 25, 136, 1], '$.pruning_radii_km'),
            (('pruning_radii_km',), 0, '90', '$.pruning_radii_km[0]'),
            (('pruning_radii_km',), 0, True, '$.pruning_radii_km[0]'),
            (('modes',), 0, 'flying', '$.modes[0]'),
            ((), 'feeds', [], '$.feeds'),
            ((), 'feeds', ['invalid'], '$.feeds[0]'),
            ((), 'run', [], '$.run'),
        ]
        for path, key, value, expected in cases:
            with self.subTest(path=path, key=key, value=value):
                manifest = copy.deepcopy(MANIFEST)
                target = manifest
                for part in path:
                    target = target[part]
                if value is None:
                    del target[key]
                else:
                    target[key] = value
                errors = validate(manifest)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_cli_validates_files_and_runs_self_check(self):
        script = Path(__file__).parent / 'fixtures/check_dataset_manifest.py'
        result = subprocess.run([sys.executable, str(script), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'manifest.json'
            for value, status in ((MANIFEST, 0), ({}, 1)):
                manifest.write_text(json.dumps(value))
                result = subprocess.run([sys.executable, str(script), str(manifest)], capture_output=True, text=True)
                self.assertEqual(result.returncode, status, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
