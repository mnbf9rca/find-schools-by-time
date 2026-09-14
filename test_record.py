import hashlib
import json
from pathlib import Path
import random
import struct
import unittest

from fixtures import record

ROOT = Path(__file__).resolve().parent
SCHOOLS = json.loads((ROOT / 'schools.json').read_text())
COUNT = len(SCHOOLS)
HASH = '43760fe2449c63cdb1ff7a4a03fc310da08c85990199b51868d7b87edbf120d9'


def example_values():
    """Whitby 489_510, with synthetic boundary cases in the last school's street slots."""
    values = [[65535] * COUNT for _ in range(4)]
    values[0][907], values[1][907] = 4200, 957
    # Test values only: these are not measured cycling or driving durations.
    values[2][-1], values[3][-1] = 0, 5400
    return values


class TestRecord(unittest.TestCase):
    def test_encoder_reproduces_committed_worked_example(self):
        self.assertEqual(SCHOOLS[907]['urn'], '121667')
        data = (ROOT / 'fixtures/example-origin.bin').read_bytes()
        self.assertEqual(record.encode(example_values()), data)
        self.assertEqual(len(data), 4 * 2 * COUNT)
        self.assertEqual(data[1814:1816], b'\xbd\x03')
        self.assertEqual(data[10560:10562], b'\xbd\x03')
        for mode in range(4):
            self.assertEqual(record.decode(data, mode, 0), 65535)
        self.assertEqual(record.decode(data, 0, 907), 957)
        self.assertEqual(record.decode(data, 1, 907), 957)
        self.assertEqual(record.decode(data, 2, COUNT - 1), 0)
        self.assertEqual(record.decode(data, 3, COUNT - 1), 5400)

    def test_random_values_round_trip_and_transit_never_exceeds_walk(self):
        rng = random.Random(13)
        choices = [0, 5400, 65535]
        values = [[rng.choice(choices) if rng.random() < .5 else rng.randrange(5401)
                   for _ in range(COUNT)] for _ in range(4)]
        original = [plane[:] for plane in values]
        data = record.encode(values)
        self.assertEqual(values, original, 'Encoding must not alter the caller\'s values')
        for mode, plane in enumerate(values):
            for school, value in enumerate(plane):
                expected = min(value, values[1][school]) if mode == 0 else value
                self.assertEqual(record.decode(data, mode, school), expected)

    def test_rounds_half_up_before_applying_the_cap(self):
        cases = [(0, 0), (.49, 0), (.5, 1), (2.5, 3), (5399.5, 5400),
                 (5400.49, 5400), (5400.5, 65535), (5401, 65535), (65535, 65535)]
        values = [[65535] * COUNT for _ in range(4)]
        for i, (value, _) in enumerate(cases):
            values[2][i] = value
        # Both cap handling and the separately stored rounded walk affect transit.
        values[0][0], values[1][0] = 5400.5, 957.5
        data = record.encode(values)
        for i, (_, expected) in enumerate(cases):
            self.assertEqual(record.decode(data, 2, i), expected)
        self.assertEqual(record.decode(data, 0, 0), 958)
        self.assertEqual(record.decode(data, 1, 0), 958)

    def test_invalid_writer_values_and_plane_sizes_raise(self):
        for bad in (-.01, -1, float('nan'), float('inf'), -float('inf')):
            values = example_values()
            values[0][907] = bad
            with self.subTest(value=bad), self.assertRaises(ValueError):
                record.encode(values)
        for values in ([], [[65535] * COUNT] * 3, [[65535] * (COUNT - 1)] * 4):
            with self.assertRaises(ValueError):
                record.encode(values)

    def test_reader_rejects_wrong_lengths_indices_and_corrupt_values(self):
        data = record.encode(example_values())
        for wrong in (b'', data[:-1], data[:-8], data + b'\xff\xff'):
            with self.assertRaises(ValueError):
                record.decode(wrong, 0, 0)
        for mode, school in [(-1, 0), (4, 0), (0, -1), (0, COUNT), (.5, 0), (0, .5)]:
            with self.assertRaises(ValueError):
                record.decode(data, mode, school)
        for value in (5401, 65534):
            corrupt = bytearray(data)
            struct.pack_into('<H', corrupt, 0, value)
            with self.assertRaises(ValueError):
                record.decode(corrupt, 0, 0)

    def test_school_hash_sorts_urns_and_has_no_trailing_newline(self):
        urns = [school['urn'] for school in SCHOOLS]
        self.assertEqual(urns, sorted(urns))
        self.assertEqual(record.school_index_hash(urns), HASH)
        self.assertEqual(record.school_index_hash(reversed(urns)), HASH)
        self.assertEqual(record.school_index_hash(['121667', '100001']),
                         hashlib.sha256(b'100001\n121667').hexdigest())


if __name__ == '__main__':
    unittest.main()
