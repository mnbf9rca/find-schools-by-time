# Publishing a version to R2: issue #19 design

Date: September 14, 2026

## Goal

`fixtures/publish.py` puts one finished run into R2: `uv run fixtures/publish.py <out-dir>/<version>`. Standard library only. The shard layout and its reasons are in `docs/decisions/2026-09-14-publish-sharded-objects.md`.

## Validate

Run the runner's `fixtures/check_dataset_manifest.py` against `<out-dir>/<version>/manifest.json` and stop on any error. Nothing uploads from a run whose manifest does not validate.

Read `records_per_shard`, `count` and `record_bytes` from the manifest's `shards` object and the key templates from its `keys` object. The script restates none of those numbers; it asserts its packing against them.

## Pack

`pack(origins_csv, out_dir, records_per_shard)` takes its inputs as arguments so the tests can run it offline against a small fake directory.

Read the origins CSV in file order. For each origin, assert `<out-dir>/<version>/<origin-id>.bin` exists and is exactly `record_bytes`; a missing or short file is a hard error naming the origin. Write it into `<out-dir>/<version>/shards/shard-<nn>.bin`, opening each shard for writing on its first record and never appending, so a rerun after a crash cannot double a shard's content. Close a shard every `records_per_shard` records.

Assert that each closed shard's length equals its record count times `record_bytes`, that the number of shards equals the manifest's `count`, and that a full shard is under 315,000,000 bytes, which is wrangler's single-object limit. Name `records_per_shard` in that message as the knob to lower: a full shard is 279,872,000 bytes today, about 12 percent under the limit, and 4,922 schools would cross it.

Write `<out-dir>/<version>/origins.txt`: the same identifiers in the same order, one per line.

Packing needs 3.26 GB of local disk for `shards/` beside the per-origin files. Delete `shards/` once `current.json` has uploaded successfully.

## Upload

The bucket is `schooltraveltime-cynexia-com`. If `npx --yes wrangler@4.131.1 r2 bucket list` does not name it, create it once with `r2 bucket create <bucket> --location weur`. The site is UK-facing and the location hint cannot be changed afterwards.

Each object goes up as

    npx --yes wrangler@4.131.1 r2 object put <bucket>/<key> --file <path> --content-type <type> -y

`-y` is not optional: `r2 object put` and `r2 object delete` prompt without it. The content type is `application/octet-stream` for the shards, `text/plain` for `origins.txt`, and `application/json` for `manifest.json` and `current.json`. The order is records first, meaning the twelve shards and then `origins.txt`, the manifest second, and `current.json` last, so no version is named before it is complete.

After each success, touch an empty marker under `<out-dir>/<version>/.uploaded/`, named for the key with slashes replaced by underscores. A rerun skips any key whose marker exists. Comparing `wrangler r2 object get --pipe | wc -c` against the local size would download 267 MiB per shard to learn one number, so the marker is the cheaper check. Delete a marker to force that object up again.

Print the uploaded total in bytes at the end, against R2's 10 GB included storage.

## Verify

The bucket stays private and wrangler 4.131.1 cannot ask for a byte range, so the check downloads one shard once and slices it locally:

    npx --yes wrangler@4.131.1 r2 object get <bucket>/<version>/shard-07.bin --pipe | tail -c +276163697 | head -c 34984 > whitby.bin

Origin `489_510` near Whitby is index 63,894: shard 7 at offset 276,163,696, which is `tail -c +276163697` in the 1-based counting that flag uses. The download is 267 MiB and one Class B operation, with no egress charge. Decode `whitby.bin` with `decode` from `fixtures/record.py` at mode index 0 and school index 907, Whitby School, assert 957 seconds, and exit non-zero otherwise.

Do not enable the r2.dev public URL. It would make every shard anonymously downloadable, which is the bulk download of the travel-time table that `docs/decisions/2026-09-14-odbl-position-for-the-travel-time-table.md` rules out. The production Worker reads the bucket through its binding.

Issue #19's done condition asks for a curl against a signed or Worker-proxied key. Neither exists: there is no S3 API token to sign with, and no Worker until milestone 4. The slice above is the round-trip check, and the curl clause moves to the milestone 4 Worker issue.

## Size and deletion

A version is 12 shards totalling 3,261,103,528 bytes, 3.26 GB, plus about 1 MB of indexes. Two versions coexist across a flip, 6.52 GB against the 10 GB allowance.

`--delete-version <version>` removes an old version, never automatically, so a flip that turns out wrong can be undone by pointing `current.json` back. It deletes fourteen objects, the twelve shards plus `origins.txt` and `manifest.json`, one `r2 object delete <bucket>/<key> -y` at a time, because wrangler 4.131.1 offers neither a prefix delete nor an object list. It never touches `current.json`. It also removes that version's local `.uploaded/` markers, so a later rerun cannot skip shards that are no longer in the bucket. `r2 bucket info --json` can be printed afterwards as a sanity line; it does not gate the flip.

## Tests

Written first, offline:

1. Packing: `pack()` over a two-origin fake directory with `records_per_shard` lowered puts each origin's bytes at the shard and offset the formula gives, `origins.txt` matches the origin order, a second run over the existing `shards/` leaves the lengths unchanged rather than doubled, and an origin file that is missing or the wrong length fails the run.
2. Upload: with the wrangler command replaced by a recording stub, each command line carries the right key, content type and `-y`, the order is the shards, `origins.txt`, the manifest and `current.json`, and a rerun with some markers present skips exactly those keys and uploads the rest.
