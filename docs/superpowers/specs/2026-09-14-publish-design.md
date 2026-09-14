# Publishing a version to R2: issue #19 design

Date: September 14, 2026

## Goal

`fixtures/publish.py` puts one finished run into R2: `uv run fixtures/publish.py <out-dir>/<version>`. Standard library only. The shard layout and its reasons are in `docs/decisions/2026-09-14-publish-sharded-objects.md`.

## Validate

Run the runner's `fixtures/check_dataset_manifest.py` against `<out-dir>/<version>/manifest.json` and stop on any error. Nothing uploads from a run whose manifest does not validate.

## Pack

Read `fixtures/origins.csv` in file order. For each origin, assert `<out-dir>/<version>/<origin-id>.bin` exists and is exactly 34,984 bytes; a missing or short file is a hard error naming the origin. Append it to `<out-dir>/<version>/shards/shard-<nn>.bin`, closing a shard every 8,000 records. Assert that each closed shard's length equals its record count times 34,984: 279,872,000 bytes for shards 0 to 10, and 182,511,528 for shard 11 with the last 5,217 origins.

Write `<out-dir>/<version>/origins.txt`: the same identifiers in the same order, one per line.

## Upload

The bucket is `schooltraveltime-cynexia-com`. If `npx --yes wrangler@4.131.1 r2 bucket list` does not name it, create it once with `r2 bucket create`.

Each object goes up as

    npx --yes wrangler@4.131.1 r2 object put <bucket>/<key> --file <path> --content-type <type>

with `application/octet-stream` for the shards, `text/plain` for `origins.txt`, and `application/json` for `manifest.json` and `current.json`. The order is records first, meaning the twelve shards and then `origins.txt`, the manifest second, and `current.json` last, so no version is named before it is complete.

After each success, touch an empty marker under `<out-dir>/<version>/.uploaded/`, named for the key with slashes replaced by underscores. A rerun skips any key whose marker exists. Comparing `wrangler r2 object get --pipe | wc -c` against the local size would download 267 MiB per shard to learn one number, so the marker is the cheaper check. Delete a marker to force that object up again.

## Verify

Enable the bucket's public URL once with `wrangler r2 bucket dev-url enable`, then range-read one record:

    curl -r 276163696-276198679 <r2.dev-url>/<version>/shard-07.bin -o whitby.bin

Origin `489_510` near Whitby is index 63,894: shard 7, offset 276,163,696. Decode those bytes with `decode` from `fixtures/record.py` at mode index 0 and school index 907, Whitby School, and print the seconds.

A public bucket is acceptable: the school and results sources carry the Open Government Licence, and the travel times are a produced work under `docs/decisions/2026-09-14-odbl-position-for-the-travel-time-table.md`. Disable the public URL with `wrangler r2 bucket dev-url disable` once the check passes, because that decision also settles that the whole table is not offered as a download. The production Worker reads the bucket through its binding, never through r2.dev.

## Size and deletion

A version is 12 shards totalling 3,261,103,528 bytes, 3.26 GB, plus about 1 MB of indexes. Two versions coexist across a flip, 6.52 GB against R2's 10 GB included storage.

Deleting the old version is a separate `--delete-version <version>` run, never automatic, so a wrong flip can be undone by pointing `current.json` back.

## Self-test

`--check` packs a fake two-origin dataset into one shard in a temporary directory, asserts the two records land at offsets 0 and 34,984, and asserts the shard is 69,968 bytes. It touches no network.

## Tests

Written first, offline:

1. Packing: over a fake run directory with the records per shard lowered, each origin's 34,984 bytes land in the shard and at the offset the formula gives, `origins.txt` matches the origin order, and an origin file that is missing or not 34,984 bytes fails the run.
2. Upload: with the wrangler command replaced by a recording stub, each command line carries the right key and content type, the order is shards, `origins.txt`, manifest, `current.json`, and a rerun with some markers present skips exactly those keys and uploads the rest.
