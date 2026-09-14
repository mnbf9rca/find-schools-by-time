import copy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from fixtures import publish, record
from test_dataset_manifest import MANIFEST


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / '20260914T093000Z'
        self.directory.mkdir()
        self.origins = self.root / 'origins.csv'
        self.origins.write_text('id,lat,lng\n0_0,0,0\n489_510,54.48,-0.62\n')
        self.data = [b'\xff' * (8 * record.SCHOOL_COUNT),
                     (Path(__file__).parent / 'fixtures/example-origin.bin').read_bytes()]
        for oid, data in zip(('0_0', '489_510'), self.data):
            (self.directory / f'{oid}.bin').write_bytes(data)
        self.manifest = copy.deepcopy(MANIFEST)
        self.manifest.update(origin_count=2,
            origins_sha256=hashlib.sha256(self.origins.read_bytes()).hexdigest())
        self.manifest['shards'].update(records_per_shard=1, count=2)
        self.save_manifest()

    def save_manifest(self):
        (self.directory / 'manifest.json').write_text(json.dumps(self.manifest))

    def test_pack_positions_restart_and_reject_bad_input(self):
        for per_shard in (1, 2):
            self.manifest['shards'].update(records_per_shard=per_shard, count=(2 + per_shard - 1) // per_shard)
            self.save_manifest()
            for repeat in range(2):
                shards = publish.pack(self.origins, self.directory, per_shard)
                self.assertEqual(len(shards), self.manifest['shards']['count'])
                for i, data in enumerate(self.data):
                    raw = shards[i // per_shard].read_bytes()
                    offset = (i % per_shard) * len(data)
                    self.assertEqual(raw[offset:offset + len(data)], data)
                self.assertEqual(sum(p.stat().st_size for p in shards), sum(map(len, self.data)))
                self.assertEqual((self.directory / 'origins.txt').read_text(), '0_0\n489_510\n')
        target = self.directory / '489_510.bin'
        for bad in (None, b'short'):
            if bad is None:
                target.unlink()
            else:
                target.write_bytes(bad)
            with self.assertRaisesRegex(ValueError, '489_510'):
                publish.pack(self.origins, self.directory, 2)
        target.write_bytes(self.data[1])
        self.manifest['shards']['count'] = 3
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'count'):
            publish.pack(self.origins, self.directory, 2)
        self.manifest['shards'].update(records_per_shard=10000, count=1)
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'records_per_shard'):
            publish.pack(self.origins, self.directory, 10000)

    def test_upload_order_markers_dry_run_verification_and_delete(self):
        calls = []
        remote = {}
        bucket_exists = False
        def command(argv, **kwargs):
            nonlocal bucket_exists
            self.assertEqual(argv[:3], ['npx', '--yes', 'wrangler@4.131.1'])
            calls.append(argv[3:])
            cmd = argv[3:]
            if cmd[:3] == ['r2', 'bucket', 'list']:
                output = f'name: {publish.BUCKET}\n' if bucket_exists else ''
                return subprocess.CompletedProcess(argv, 0, stdout=output.encode())
            if cmd[:3] == ['r2', 'bucket', 'create']:
                self.assertEqual(cmd[3:], [publish.BUCKET, '--location', 'weur'])
                bucket_exists = True
            elif cmd[:3] == ['r2', 'object', 'put']:
                self.assertIn('--remote', cmd)
                self.assertIn('-y', cmd)
                remote[cmd[3]] = Path(cmd[cmd.index('--file') + 1]).read_bytes()
            elif cmd[:3] == ['r2', 'object', 'get']:
                self.assertIn('--remote', cmd)
                self.assertIn('--pipe', cmd)
                kwargs['stdout'].write(remote[cmd[3]])
            elif cmd[:3] == ['r2', 'object', 'delete']:
                self.assertIn('--remote', cmd)
                self.assertIn('-y', cmd)
                remote.pop(cmd[3], None)
            return subprocess.CompletedProcess(argv, 0)
        messages = []
        publish.publish(self.directory, self.origins, dry_run=True, command=command, emit=messages.append)
        self.assertEqual(calls, [])
        self.assertFalse((self.directory / '.uploaded').exists())
        self.assertTrue((self.directory / 'shards').exists())
        self.assertIn('Whitby: origin index 1, shard 1, offset 0, record bytes 34984', messages)
        self.assertTrue(any('r2 object put' in m for m in messages))
        version = self.manifest['version']
        first_key = f'{version}/shard-00.bin'
        markers = self.directory / '.uploaded'
        markers.mkdir()
        (markers / first_key.replace('/', '_')).touch()
        remote[f'{publish.BUCKET}/{first_key}'] = self.data[0]
        publish.publish(self.directory, self.origins, command=command, emit=messages.append)
        puts = [c for c in calls if c[:3] == ['r2', 'object', 'put']]
        self.assertEqual([c[3] for c in puts], [f'{publish.BUCKET}/{key}' for key in
            (f'{version}/shard-01.bin', f'{version}/origins.txt', f'{version}/manifest.json', 'current.json')])
        self.assertEqual([c[c.index('--content-type') + 1] for c in puts],
            ['application/octet-stream', 'text/plain', 'application/json', 'application/json'])
        self.assertEqual(json.loads(remote[f'{publish.BUCKET}/current.json']), {'version': version})
        self.assertFalse((self.directory / 'shards').exists())
        calls.clear()
        publish.publish(self.directory, self.origins, command=command, emit=messages.append)
        self.assertFalse(any(c[:3] in (['r2', 'bucket', 'create'], ['r2', 'object', 'put']) for c in calls))
        remote[f'{publish.BUCKET}/{version}/shard-01.bin'] = self.data[0]
        with self.assertRaisesRegex(ValueError, 'Whitby'):
            publish.publish(self.directory, self.origins, command=command, emit=messages.append)
        calls.clear()
        publish.delete_version(self.directory, dry_run=True, command=command, emit=messages.append)
        self.assertEqual(calls, [])
        self.assertTrue(markers.exists())
        # Old versions remain deletable after the school index changes.
        self.manifest['school_count'] -= 1
        self.manifest['shards']['record_bytes'] -= 8
        self.save_manifest()
        publish.delete_version(self.directory, command=command, emit=messages.append)
        deletes = [c[3] for c in calls if c[:3] == ['r2', 'object', 'delete']]
        self.assertEqual(deletes, [f'{publish.BUCKET}/{version}/{key}' for key in
            ('shard-00.bin', 'shard-01.bin', 'origins.txt', 'manifest.json')])
        self.assertEqual(set(remote), {f'{publish.BUCKET}/current.json'})
        self.assertFalse(markers.exists())
        calls.clear()
        del self.manifest['shards']
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'shards'):
            publish.publish(self.directory, self.origins, command=command, emit=messages.append)
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
