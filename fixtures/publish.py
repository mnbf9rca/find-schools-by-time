"""Pack and publish a version: uv run fixtures/publish.py OUT/VERSION [--dry-run].

--dry-run packs locally and prints commands without calling Wrangler.
Object operations use --remote because Wrangler defaults to local storage.
--delete-version VERSION deletes that sibling version, leaving current.json alone.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile

if __package__:
    from . import record
    from .check_dataset_manifest import validate
else:
    import record
    from check_dataset_manifest import validate

ROOT = Path(__file__).resolve().parents[1]
BUCKET = 'schooltraveltime-cynexia-com'
WRANGLER = ['npx', '--yes', 'wrangler@4.131.1']


def load_manifest(directory):
    manifest = json.loads((directory / 'manifest.json').read_text())
    errors = validate(manifest)
    if errors:
        raise ValueError('; '.join(errors))
    version = manifest['version']
    if not re.fullmatch(r'\d{8}T\d{6}Z', version) or directory.name != version:
        raise ValueError('Manifest version must match the version directory')
    shards = manifest['shards']
    if min(shards.values()) <= 0 or manifest['origin_count'] <= 0:
        raise ValueError('Shard dimensions and origin_count must be positive')
    if manifest['keys'] != {'shard': version + '/shard-{nn}.bin',
                            'origins': version + '/origins.txt',
                            'manifest': version + '/manifest.json', 'current': 'current.json'}:
        raise ValueError('Manifest keys must name this version and current.json')
    return manifest


def pack(origins_csv, out_dir, records_per_shard):
    directory, origins_csv = Path(out_dir), Path(origins_csv)
    manifest = load_manifest(directory)
    dimensions = manifest['shards']
    size = dimensions['record_bytes']
    if size != 8 * record.SCHOOL_COUNT:
        raise ValueError('record_bytes differs from the full school index')
    if records_per_shard != dimensions['records_per_shard']:
        raise ValueError('records_per_shard differs from the manifest')
    if records_per_shard * size >= 315000000:
        raise ValueError('A full shard must be under 315000000 bytes; lower records_per_shard')
    if hashlib.sha256(origins_csv.read_bytes()).hexdigest() != manifest['origins_sha256']:
        raise ValueError('Origins CSV checksum differs from the manifest')
    with origins_csv.open(newline='') as f:
        origins = [row['id'] for row in csv.DictReader(f)]
    if len(origins) != manifest['origin_count'] or len(origins) != len(set(origins)):
        raise ValueError('Origin count differs from the manifest or identifiers repeat')
    if any(not re.fullmatch(r'\d+_\d+', oid) for oid in origins):
        raise ValueError('Invalid origin identifier')
    count = (len(origins) + records_per_shard - 1) // records_per_shard
    if count != dimensions['count']:
        raise ValueError('Shard count differs from the manifest')
    shard_dir = directory / 'shards'
    shard_dir.mkdir(exist_ok=True)
    paths = []
    for number, start in enumerate(range(0, len(origins), records_per_shard)):
        path = shard_dir / f'shard-{number:02d}.bin'
        group = origins[start:start + records_per_shard]
        with path.open('wb') as shard:
            for oid in group:
                try:
                    data = (directory / f'{oid}.bin').read_bytes()
                except FileNotFoundError as error:
                    raise ValueError(f'{oid}: missing origin record') from error
                if len(data) != size:
                    raise ValueError(f'{oid}: record length {len(data)}, expected {size}')
                shard.write(data)
        if path.stat().st_size != len(group) * size:
            raise ValueError(f'{path.name}: packed length differs from record count')
        paths.append(path)
    for stale in set(shard_dir.glob('shard-*.bin')) - set(paths):
        stale.unlink()
    (directory / 'origins.txt').write_text(''.join(oid + '\n' for oid in origins))
    return paths


def objects(directory, manifest):
    keys = manifest['keys']
    return [(keys['shard'].replace('{nn}', f'{i:02d}'),
             directory / 'shards' / f'shard-{i:02d}.bin', 'application/octet-stream')
            for i in range(manifest['shards']['count'])] + [
        (keys['origins'], directory / 'origins.txt', 'text/plain'),
        (keys['manifest'], directory / 'manifest.json', 'application/json'),
        (keys['current'], directory.parent / 'current.json', 'application/json')]


def publish(directory, origins_csv=ROOT / 'fixtures/origins.csv', *, dry_run=False,
            command=subprocess.run, emit=print):
    directory = Path(directory)
    manifest = load_manifest(directory)
    dimensions = manifest['shards']
    paths = pack(origins_csv, directory, dimensions['records_per_shard'])
    for path in paths:
        emit(f'{path.name}: {path.stat().st_size} bytes')
    origins = (directory / 'origins.txt').read_text().splitlines()
    try:
        index = origins.index('489_510')
    except ValueError as error:
        raise ValueError('Whitby origin 489_510 is missing') from error
    shard_number, within = divmod(index, dimensions['records_per_shard'])
    offset, size = within * dimensions['record_bytes'], dimensions['record_bytes']
    emit(f'Whitby: origin index {index}, shard {shard_number}, offset {offset}, record bytes {size}')
    (directory.parent / 'current.json').write_text(json.dumps({'version': manifest['version']}) + '\n')
    uploads = objects(directory, manifest)
    list_command = WRANGLER + ['r2', 'bucket', 'list']
    create_command = WRANGLER + ['r2', 'bucket', 'create', BUCKET, '--location', 'weur']
    emit(shlex.join(list_command))
    if dry_run:
        emit('If the bucket is absent: ' + shlex.join(create_command))
    else:
        result = command(list_command, check=True, stdout=subprocess.PIPE)
        if not re.search(r'^name:\s*' + re.escape(BUCKET) + r'\s*$', result.stdout.decode(), re.MULTILINE):
            emit(shlex.join(create_command))
            command(create_command, check=True)
    markers = directory / '.uploaded'
    if not dry_run:
        markers.mkdir(exist_ok=True)
    uploaded = 0
    for key, path, content_type in uploads:
        marker = markers / key.replace('/', '_')
        if marker.exists():
            emit(f'Skip uploaded {key}')
            continue
        argv = WRANGLER + ['r2', 'object', 'put', f'{BUCKET}/{key}', '--file', str(path),
                           '--content-type', content_type, '--remote', '-y']
        emit(shlex.join(argv))
        if not dry_run:
            command(argv, check=True)
            marker.touch()
        uploaded += path.stat().st_size
    total = sum(path.stat().st_size for key, path, kind in uploads)
    key = manifest['keys']['shard'].replace('{nn}', f'{shard_number:02d}')
    get_command = WRANGLER + ['r2', 'object', 'get', f'{BUCKET}/{key}', '--remote', '--pipe']
    emit(shlex.join(get_command))
    if not dry_run:
        with tempfile.TemporaryFile() as downloaded:
            command(get_command, check=True, stdout=downloaded)
            downloaded.seek(offset)
            value = record.decode(downloaded.read(size), 0, 907)
        if value != 957:
            raise ValueError(f'Whitby verification: expected 957 seconds, got {value}')
        emit('Whitby verification: 957 seconds')
        shutil.rmtree(directory / 'shards')
    emit(f'{"Would upload" if dry_run else "Uploaded"} {uploaded} bytes this invocation; '
         f'version objects total {total} bytes against 10000000000 bytes included storage')


def delete_version(directory, *, dry_run=False, command=subprocess.run, emit=print):
    directory = Path(directory)
    manifest = load_manifest(directory)
    markers = directory / '.uploaded'
    for key, path, content_type in objects(directory, manifest)[:-1]:
        argv = WRANGLER + ['r2', 'object', 'delete', f'{BUCKET}/{key}', '--remote', '-y']
        emit(shlex.join(argv))
        if not dry_run:
            command(argv, check=True)
            (markers / key.replace('/', '_')).unlink(missing_ok=True)
    if not dry_run and markers.exists():
        shutil.rmtree(markers)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--origins', type=Path, default=ROOT / 'fixtures/origins.csv')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--delete-version')
    args = parser.parse_args()
    try:
        if args.delete_version:
            if not re.fullmatch(r'\d{8}T\d{6}Z', args.delete_version):
                raise ValueError('Invalid version to delete')
            delete_version(args.directory.parent / args.delete_version, dry_run=args.dry_run)
        else:
            publish(args.directory, args.origins, dry_run=args.dry_run)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'Publish failed: {error}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
