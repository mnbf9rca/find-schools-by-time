import json
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from fixtures import precompute as pc, record

ROOT = Path(__file__).resolve().parent


class TestPrecompute(unittest.TestCase):
    def test_request_shapes_and_complete_batches(self):
        school = {'urn': '121667', 'lat': 54.481915, 'lng': -.624338}
        origins = [{'id': '489_510', 'lat': '54.48', 'lng': '-0.62'}]
        for mode in (0, 2, 3):
            endpoint, body = pc.payload(school, mode, origins)
            self.assertTrue(body['arriveBy'])
            self.assertEqual(body['maxMatchingDistance'], 250)
            if mode == 3:
                self.assertEqual(endpoint, '/api/v1/one-to-many')
                self.assertEqual(body['mode'], 'CAR')
                self.assertEqual(body['max'], 5400)
                self.assertNotIn('time', body)
                self.assertEqual(body['many'], ['54.48;-0.62'])
            else:
                self.assertEqual(endpoint, '/api/experimental/one-to-many-intermodal')
                self.assertEqual(body['preTransitModes'], ['WALK'])
                self.assertEqual(body['postTransitModes'], ['WALK'])
                self.assertEqual(body['maxPreTransitTime'], 900)
                self.assertEqual(body['maxPostTransitTime'], 900)
                self.assertTrue(body['useRoutedTransfers'])
                self.assertEqual(body['maxTravelTime'], 90)
                self.assertEqual(body['maxDirectTime'], 5400)
                self.assertEqual(body['time'], '2026-09-16T08:30:00+01:00')
                self.assertEqual(body['many'], ['54.48,-0.62'])
                self.assertEqual(body['transitModes'], ['TRANSIT'] if mode == 0 else [])
                self.assertEqual(body['directMode'], 'WALK' if mode == 0 else 'BIKE')
                if mode == 2:
                    self.assertEqual(body['cyclingSpeed'], 5.0)
        batches = list(pc.batches(list(range(45001))))
        self.assertEqual([len(b) for b in batches], [20000, 20000, 5001])
        self.assertEqual([i for b in batches for i in b], list(range(45001)))

    def test_candidates_measure_cell_centres_including_the_boundary(self):
        origins = [{'id': '0_0'}, {'id': '1_0'}, {'id': '2_0'}, {'id': '0_1'}]
        for radius, expected in [(0, [0]), (1, [0, 1, 3]), (2, [0, 1, 2, 3])]:
            self.assertEqual(pc.candidate_indices(origins, 500, 500, radius), expected)
        ring = [{'id': '29_0'}, {'id': '30_0'}, {'id': '31_0'}, {'id': '660_660'}]
        for mode, expected in [(0, [0, 1, 2, 3]), (1, [0, 1, 2, 3]),
                               (2, [0, 1]), (3, [0, 1, 2, 3])]:
            with self.subTest(mode=mode):
                self.assertEqual(pc.candidate_indices(ring, 500, 500, pc.RADII[mode]), expected)
        self.assertEqual(pc.candidate_indices(ring, 500, 500, None), [0, 1, 2, 3])

    def test_leave_by_rounding_cap_and_empty_entries(self):
        data = {'transit_durations': [[{'duration': 4200}], [], [{'duration': 5400.5}]],
                'street_durations': [{'duration': 957.5}, {}, {'duration': 5400.49}]}
        self.assertEqual(pc.response_values(0, data, 3), {0: [958, 65535, 5400], 1: [958, 65535, 5400]})
        self.assertEqual(pc.response_values(2, data, 3), {2: [958, 65535, 5400]})
        self.assertEqual(pc.response_values(3, [{'duration': 0}, {}, {'duration': 5400.5}], 3),
                         {3: [0, 65535, 65535]})
        with self.assertRaises(ValueError):
            pc.response_values(3, [{'duration': -.1}], 1)
        with self.assertRaises(ValueError):
            pc.response_values(3, [], 1)

    def test_halving_preserves_both_halves_and_single_failure_is_fatal(self):
        calls = []
        def request(batch):
            calls.append(list(batch))
            if len(batch) > 2:
                raise OSError('dropped connection')
            return list(batch)
        result = list(pc.halving(list(range(5)), request, threading.Event()))
        self.assertEqual([i for batch, response in result for i in response], list(range(5)))
        self.assertEqual(calls, [[0, 1, 2, 3, 4], [0, 1], [2, 3, 4], [2], [3, 4]])
        with self.assertRaises(RuntimeError):
            list(pc.halving([0], lambda b: (_ for _ in ()).throw(OSError('failed')), threading.Event()))

    def test_school_layout_and_transpose_include_all_sentinel_origins(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            schools_dir = out / 'schools'
            schools_dir.mkdir()
            pc.write_school(schools_dir / '121667.bin', [[(0, 957)], [(0, 957)], [], []])
            last = json.loads((ROOT / 'schools.json').read_text())[-1]['urn']
            pc.write_school(schools_dir / f'{last}.bin', [[], [], [(0, 0)], [(0, 5400)]])
            data = (schools_dir / '121667.bin').read_bytes()
            self.assertEqual(struct.unpack_from('<4I', data), (1, 1, 0, 0))
            self.assertEqual(len(data), 28)
            self.assertEqual(pc.read_school(schools_dir / '121667.bin', 2), [[(0, 957)], [(0, 957)], [], []])
            origins = [{'id': '489_510'}, {'id': '87_15'}]
            result = pc.transpose(out, 'test', origins, ['121667', last], threading.Event())
            self.assertEqual((out / 'test/489_510.bin').read_bytes(), (ROOT / 'fixtures/example-origin.bin').read_bytes())
            self.assertEqual((out / 'test/87_15.bin').read_bytes(), b'\xff' * (8 * record.SCHOOL_COUNT))
            self.assertEqual({p.name for p in (out / 'test').iterdir()}, {'489_510.bin', '87_15.bin'})
            self.assertEqual(result, 2 * 8 * record.SCHOOL_COUNT)
            (schools_dir / '121667.bin').write_bytes(data[:-1])
            with self.assertRaises(ValueError):
                pc.read_school(schools_dir / '121667.bin', 2)

    def test_subprocess_resume_uses_nondefault_url_and_full_school_index(self):
        calls = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append(body)
                time.sleep(.1)
                entries = [{'duration': 957.5} for _ in body['many']]
                result = entries if body.get('mode') == 'CAR' else {
                    'street_durations': entries,
                    'transit_durations': [[{'duration': 4200}] for _ in entries]}
                raw = json.dumps(result).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        second_server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        second_thread = threading.Thread(target=second_server.serve_forever)
        second_thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                origins = base / 'origins.csv'
                origins.write_text('id,lat,lng\n489_510,54.481966,-0.620123\n530_180,51.508,-0.128\n87_15,49.957693,-6.358553\n')
                schools = base / 'schools.csv'
                schools.write_text('urn,lat,lng\n100001,51.508,-0.128\n121667,54.481915,-0.624338\n137353,51.52221,-0.15217\n')
                graph = base / 'data.rail'
                graph.mkdir()
                (base / 'feeds').mkdir()
                (base / 'feeds/rail.zip').write_bytes(b'local test feed')
                common = [sys.executable, str(ROOT / 'fixtures/precompute.py'), '--workers', '1',
                          '--base-url', f'http://127.0.0.1:{server.server_port}', '--origins', str(origins),
                          '--schools', str(schools), '--graph-dir', str(graph)]
                resumed, baseline = base / 'resumed', base / 'baseline'
                with (base / 'run.log').open('w') as log:
                    process = subprocess.Popen(common + [str(resumed)], stdout=log, stderr=log)
                    try:
                        deadline = time.monotonic() + 15
                        while not (resumed / 'schools/100001.bin').exists():
                            if process.poll() is not None or time.monotonic() > deadline:
                                self.fail((base / 'run.log').read_text())
                            time.sleep(.01)
                        process.send_signal(signal.SIGTERM)
                        self.assertEqual(process.wait(timeout=15), 143, (base / 'run.log').read_text())
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.wait()
                first = json.loads((resumed / 'run.json').read_text())
                self.assertEqual(first['parameters']['pruning_radii_km'], [None, None, 30, None])
                self.assertGreater(first['requests'], 0)
                saved_mtime = (resumed / 'schools/100001.bin').stat().st_mtime_ns
                # Older checkpoints stored the URL; it is not part of dataset identity.
                first['parameters']['base_url'] = f'http://127.0.0.1:{server.server_port}'
                (resumed / 'run.json').write_text(json.dumps(first))
                common[common.index('--base-url') + 1] = f'http://127.0.0.1:{second_server.server_port}'
                for out in (resumed, baseline):
                    result = subprocess.run(common + [str(out)], capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual((resumed / 'schools/100001.bin').stat().st_mtime_ns, saved_mtime)
                second = json.loads((resumed / 'run.json').read_text())
                self.assertEqual(second['version'], first['version'])
                self.assertNotIn('base_url', second['parameters'])
                for key in ('schools_sha256', 'arrival', 'feeds'):
                    self.assertEqual(second['parameters'][key], first['parameters'][key])
                self.assertGreater(second['requests'], first['requests'])
                self.assertGreater(second['wall_seconds'], first['wall_seconds'])
                versions = [json.loads((out / 'current.json').read_text())['version'] for out in (resumed, baseline)]
                for folder in ('schools', None):
                    left, right = [out / (version if folder is None else folder)
                                   for out, version in zip((resumed, baseline), versions)]
                    a, b = {p.name: p.read_bytes() for p in left.glob('*.bin')}, {p.name: p.read_bytes() for p in right.glob('*.bin')}
                    self.assertEqual(a, b)
                    self.assertEqual(len(a), 3)
                manifest = json.loads((resumed / versions[0] / 'manifest.json').read_text())
                self.assertEqual(manifest['pruning_radii_km'], [None, None, 30, None])
                self.assertEqual(manifest['school_count'], record.SCHOOL_COUNT)
                self.assertEqual(manifest['shards'], {'records_per_shard': 8000, 'count': 1, 'record_bytes': 34984})
                version = versions[0]
                self.assertEqual(manifest['keys'], {'shard': version + '/shard-{nn}.bin',
                    'origins': version + '/origins.txt', 'manifest': version + '/manifest.json', 'current': 'current.json'})
                self.assertEqual(manifest['run']['peak_server_rss_bytes'], 0)
                self.assertFalse(any(body.get('mode') == 'WALK' for body in calls))
                changed = common + [str(resumed), '--workers', '2']
                result = subprocess.run(changed, capture_output=True, text=True, timeout=15)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('parameters', result.stdout + result.stderr)
                # SIGTERM can interrupt a progress write; the handler must not write again.
                interrupt_write = """
import os, signal, sys
from fixtures import precompute
class Output:
    busy = False
    fired = False
    def write(self, text):
        if self.busy:
            raise RuntimeError('reentrant stdout write')
        if text.startswith('Resume:') and not self.fired:
            self.fired = self.busy = True
            os.kill(os.getpid(), signal.SIGTERM)
            self.busy = False
        return sys.__stdout__.write(text)
    def flush(self):
        sys.__stdout__.flush()
sys.stdout = Output()
raise SystemExit(precompute.main())
"""
                result = subprocess.run([sys.executable, '-c', interrupt_write] + common[2:] + [str(base / 'early')],
                                        cwd=ROOT, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 143, result.stdout + result.stderr)
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
            second_server.shutdown()
            second_thread.join()
            second_server.server_close()


if __name__ == '__main__':
    unittest.main()
