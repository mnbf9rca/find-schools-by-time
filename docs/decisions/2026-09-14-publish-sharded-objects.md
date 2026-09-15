# Publish the dataset as 12 shard objects, not 93,217 per-origin objects

Date: September 14, 2026

## Decision

A published version is 12 shard objects plus two small index objects. Each shard holds 8,000 records packed in `fixtures/origins.csv` order with no padding and no separators. The keys are `<version>/shard-<nn>.bin`, two digits and zero-based, so `shard-00.bin` through `shard-11.bin`. Beside them sit `<version>/manifest.json` and `<version>/origins.txt`, which lists the origin identifiers in file order, one per line. `current.json` at the bucket root still holds the version alone and is unchanged.

The Worker fetches `origins.txt` once per isolate to map an identifier to its index. For origin index `i` it range-reads 34,984 bytes at offset `(i mod 8000) * 34984` from shard `i div 8000`. The R2 Workers binding supports `get(key, {range: {offset, length}})`.

The per-origin files the runner writes locally are unchanged, and they stay the unit the issue #18 validator reads. Packing is a publish-time step. This supersedes only the key scheme in `docs/superpowers/specs/2026-09-14-per-origin-record-format.md`; the record bytes are the same.

## Why

Uploading 93,217 objects is not practical with the credentials available. wrangler 4.131.1 has no bulk upload, only `r2 object put` one object at a time, up to 315 MB each. The Cloudflare REST API allows 1,200 requests per five minutes per user, so 93,217 objects would take at least 6.5 hours of rate-limited calls. Escaping that limit needs an S3 API token and a parallel client. The current OAuth login cannot create one, because it has no `api_tokens:write` scope; only the dashboard can, and the user is not there. `wrangler r2 bucket create` and `r2 object put --content-type` do work with the login as it stands.

## What it costs

One extra object, `origins.txt`, about 1 MB, fetched once per isolate rather than once per request. A range read instead of a plain key lookup. A version is still 3.26 GB.

## Reversibility

Per-origin keys can return if an S3 API token is ever created. Packing runs at publish time over unchanged local files, so going back means changing `fixtures/publish.py` and the Worker's lookup, not rerunning the precompute.
