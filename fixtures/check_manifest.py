"""Verify the committed feed manifest against a directory of local inputs.

Run: uv run fixtures/check_manifest.py <base-directory>
Self-test: uv run fixtures/check_manifest.py --check
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile

ROUTING_DATE = date(2026, 9, 16)


def verify(entries, base, licence_file):
    if not isinstance(entries, list) or not entries:
        return ['Manifest must be a non-empty JSON array.']
    licences = {line.split('|')[1].strip() for line in licence_file.read_text().splitlines()
                if line.startswith('| ') and line.split('|')[1].strip() != 'Item'}
    required = {'path', 'source', 'downloaded', 'bytes', 'sha256', 'valid_from', 'valid_to', 'licence'}
    errors = []
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or not required <= entry.keys():
            errors.append(f'Entry {index}: missing required manifest fields.')
            continue
        name = entry['path']
        try:
            path = Path(name)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('path must be relative to the base directory')
            path = base / path
            size = path.stat().st_size
            if size != entry['bytes']:
                errors.append(f'{name}: size is {size}, expected {entry["bytes"]}.')
            with path.open('rb') as source:
                checksum = hashlib.file_digest(source, 'sha256').hexdigest()
            if checksum != entry['sha256']:
                errors.append(f'{name}: SHA-256 is {checksum}, expected {entry["sha256"]}.')
        except (OSError, TypeError, ValueError) as error:
            errors.append(f'{name}: cannot read file: {error}')
        start, end = entry['valid_from'], entry['valid_to']
        if start is not None or end is not None:
            try:
                if not date.fromisoformat(start) <= ROUTING_DATE <= date.fromisoformat(end):
                    errors.append(f'{name}: validity window does not cover {ROUTING_DATE}.')
            except (TypeError, ValueError):
                errors.append(f'{name}: invalid validity window; use two ISO dates or two nulls.')
        if not isinstance(entry['licence'], str) or entry['licence'] not in licences:
            errors.append(f'{name}: unknown licence item {entry["licence"]!r}.')
    return errors


def check():
    """Catch altered files, stale windows, bad licence names and early exits."""
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        (base / 'feed.txt').write_bytes(b'abc')
        licence_file = base / 'LICENSES.md'
        licence_file.write_text('| Item | Licence |\n|---|---|\n| Test feed | Test licence |\n')
        entry = dict(path='feed.txt', source='test', downloaded='2026-09-13', bytes=3,
                     sha256='ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
                     valid_from='2026-09-16', valid_to='2026-09-16', licence='Test feed')
        manifest = base / 'manifest.json'
        manifest.write_text(json.dumps([entry]))
        assert verify(json.loads(manifest.read_text()), base, licence_file) == []
        cases = [
            ({'bytes': 4}, 'size'),
            ({'sha256': '0' * 64}, 'SHA-256'),
            ({'path': 'missing.txt'}, 'cannot read'),
            ({'valid_to': '2026-09-15'}, 'validity'),
            ({'valid_from': '2026-09-17'}, 'validity'),
            ({'valid_from': None}, 'validity'),
            ({'valid_to': 'invalid'}, 'validity'),
            ({'licence': 'Unknown'}, 'licence'),
            ({'licence': 'Item'}, 'licence'),
            ({'path': '../feed.txt'}, 'relative'),
        ]
        for changes, expected in cases:
            errors = verify([entry | changes], base, licence_file)
            assert any(expected in error for error in errors), (changes, errors)
        assert verify([entry | dict(valid_from=None, valid_to=None)], base, licence_file) == []
        errors = verify([entry | dict(bytes=4, sha256='0' * 64, licence='Unknown'),
                         entry | dict(path='missing.txt', valid_to='2026-09-15')], base, licence_file)
        assert len(errors) == 5, errors
        assert verify([], base, licence_file), 'An empty manifest must fail'
    print('ok')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', nargs='?', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        check()
        return 0
    if args.base is None:
        parser.error('provide a base directory or --check')
    root = Path(__file__).resolve().parents[1]
    try:
        entries = json.loads((root / 'fixtures/feed-manifest.json').read_text())
        errors = verify(entries, args.base, root / 'LICENSES/README.md')
    except (OSError, ValueError) as error:
        print(f'Cannot check manifest: {error}')
        return 1
    for error in errors:
        print(error)
    if errors:
        print(f'Failed: {len(errors)} errors.')
        return 1
    print(f'Passed: {len(entries)} files match their sizes and SHA-256 checksums; '
          f'all validity windows cover {ROUTING_DATE}; all licence names match.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
