# Precompute runner: issues #14, #15 and #16 design

Date: September 14, 2026

## Goal

`fixtures/precompute.py` turns the school list and the origin grid into the published dataset: `uv run --with pyproj fixtures/precompute.py <out-dir>`, with `--workers N` default 8, `--base-url` default `http://127.0.0.1:8080`, and `--schools PATH` default `schools.json`, also taking a CSV of `urn`, `lat` and `lng` so the runbook can use `fixtures/spike-sample.csv`. Standard library plus pyproj, used only to project the school coordinates to EPSG:27700 at startup, because an origin identifier already carries its easting and northing.

The script is self-contained. It imports neither `sweep_spike.py`, unreachable by a bare `import` under the `from fixtures import ...` convention, nor `measure_reach.py`, which returns index sets rather than seconds. It carries its own grid, payload and request code.

## Requests

Three request groups per school, each holding the origins within its mode's radius from `docs/decisions/2026-09-14-per-mode-pruning-radii.md`, split into batches of at most 20,000 in origin order.

Measure distance from the cell centre: easting is 1,000 times the identifier's kilometre easting plus 500, northing likewise. The rounded radii leave margins of 669, 644 and 915 metres, two of them under the 707 metre corner-to-centre displacement, so measuring from anywhere else drops reachable origins.

- Public transport: `POST /api/experimental/one-to-many-intermodal`, `transitModes: ["TRANSIT"]`, `directMode: "WALK"`, `lat,lng`.
- Cycling: same endpoint, `transitModes: []`, `directMode: "BIKE"`, `cyclingSpeed: 5.0`, `lat,lng`.
- Driving: `POST /api/v1/one-to-many`, `mode: "CAR"`, `lat;lng`, and no `time`, because driving does not depend on time of day.

The caps carry three units: `maxTravelTime: 90` minutes on the transit leg, `maxDirectTime: 5400` seconds on the direct leg, `max: 5400` seconds for driving. All three set `arriveBy: true` and `maxMatchingDistance: 250` metres; the intermodal pair also set `time: "2026-09-16T08:30:00+01:00"`.

Three requests fill four planes: the public transport response's `street_durations` entry per origin is the direct walk, so the walking plane needs no fourth request and inherits the 90 kilometre transit radius. That leg is the intermodal endpoint's, not the street endpoint the spike used, and `motis-spike/NOTES.md` records empty `street_durations` for four nearby schools with no follow-up. Hence the explicit `maxMatchingDistance`, the runbook's sample run checking walk coverage against straight-line distance, and the same check in the issue #18 validator: an origin within 2 km of a school with no walk value is a defect to chase.

Apply `docs/decisions/2026-09-14-store-leave-by-minutes.md`: public transport takes the smaller of the `transit_durations` Pareto minimum and the `street_durations` entry, the other three their street durations alone; discard anything over 5,400 seconds. On a non-200 or a dropped connection, halve the batch and retry each half down to a single origin, which is a hard error.

## Per-school output

A worker takes one school, issues its three request groups, and writes `<out-dir>/schools/<urn>.bin` through a `.tmp` file and a rename. It holds four unsigned 32-bit counts, one per mode in plane order, then four sections of `(uint32 origin_index, uint16 seconds)` pairs ascending by index. The index is the zero-based row number in `fixtures/origins.csv`, 32 bits because there are over 65,535 origins. The sections exist because tagging each pair with its mode would cost seven bytes instead of six. Expect 120 KB per school, 500 MB in total. Keep `<out-dir>/schools/` until the version is published; then it can be deleted.

## Resume

`<out-dir>/run.json` is written on the first start and read on every later one. It holds the version, every run parameter (the three radii, batch size, cap, cycling speed, worker count and MOTIS version), the SHA-256 of `fixtures/origins.csv`, the school index hash and the graph directory. A resume refuses to continue if any differs, because the version is the run's start time and must not be minted twice. The file also accumulates wall seconds, requests and peak server resident set size across invocations, so the issue #17 figures cover the whole run.

Resume validates each school file rather than trusting it exists: its length must equal 16 bytes plus six times the sum of its four counts. The rename is atomic on APFS, the temporary file sitting in the same directory and so the same filesystem, but nothing calls `fsync` first, so a power loss can leave a short file under a complete name. Delete and redo any that fails.

## Transpose

One pass over the school files builds the whole matrix in memory, then writes one record per origin in the format of `docs/superpowers/specs/2026-09-14-per-origin-record-format.md` to `<out-dir>/<version>/<origin-id>.bin`. The matrix is 93,217 origins times 34,984 bytes, 3.26 GB, against 48 GB on the Mac and 8.8 GB for the server. Allocate the buffer once, with a `ponytail:` comment naming the ceiling: about 3.5 GB of process memory, slice by origin range on a smaller machine. Do not memory-map the 93,217 output files; macOS's open-file limit makes that worse than writing them in turn. Two phases is what issue #14 means by transposing as it goes: memory stays bounded by one matrix rather than every response, and the per-school files are what make resume possible.

## Manifest and publishing

`<out-dir>/<version>/manifest.json`, with `<out-dir>/current.json` holding `{"version": "..."}` alone. Locally `current.json` also goes through a temporary file and a rename.

The runner's local output layout is unchanged: one file per origin at `<out-dir>/<version>/<origin-id>.bin`. Uploading is `fixtures/publish.py`'s job, specified in `docs/superpowers/specs/2026-09-14-publish-design.md`. It packs those files into shards of 8,000 records and publishes `<version>/shard-<nn>.bin`, `<version>/origins.txt` and `<version>/manifest.json`, records first, the manifest second and `current.json` at the bucket root last, so no version is named before it is complete. `current.json` is unchanged. See `docs/decisions/2026-09-14-publish-sharded-objects.md` for why the objects are shards.

```json
{
  "version": "20260914T093000Z",
  "routing_date": "2026-09-16",
  "routing_time": "08:30",
  "timezone": "Europe/London",
  "motis_version": "2.11.3",
  "modes": ["public_transport", "walking", "cycling", "driving"],
  "cap_seconds": 5400,
  "display_band_minutes": 10,
  "unreachable": 65535,
  "compression": "none",
  "rounding": "half up to whole seconds, then compared with 5400",
  "cycling_speed_mps": 5.0,
  "pruning_radii_km": [90, 90, 25, 136],
  "shards": {"records_per_shard": 8000, "count": 12, "record_bytes": 34984},
  "origin_count": 93217,
  "origins_sha256": "2f1c...",
  "school_count": 4373,
  "school_index_sha256": "43760fe2449c63cdb1ff7a4a03fc310da08c85990199b51868d7b87edbf120d9",
  "feeds": [{"path": "motis-spike/feeds/bods.zip", "sha256": "d69d71ec..."},
            {"path": "motis-spike/feeds/rail.zip", "sha256": "..."}],
  "run": {"started": "2026-09-14T09:30:00Z", "wall_seconds": 4412, "workers": 8,
          "requests": 26238, "peak_server_rss_bytes": 9448928051, "output_bytes": 3761103528}
}
```

The version is the run's start time in UTC. MOTIS returns durations as floats, hence `rounding`. `pruning_radii_km` is in plane order. `shards` describes the published objects: `count` is the origin count divided by `records_per_shard` and rounded up, and `record_bytes` is twice four times the school count. The runner computes them; `fixtures/publish.py` checks its packing against them. `origins_sha256` hashes the committed `fixtures/origins.csv` bytes. `output_bytes` is measured at the end, covering the records, 3.26 GB, plus the school files. The `bods.zip` checksum comes from `fixtures/feed-manifest.json`; `rail.zip` is a converted output, so the feed manifest holds the nine CIF files behind it and the runner hashes the zip itself.

`fixtures/manifest.schema.json` is the contract; `fixtures/check_dataset_manifest.py` validates against it before the run exits, in about thirty lines of standard library with a `--check` self-test like `fixtures/check_manifest.py`. It walks the schema recursively, honouring `required`, `properties`, `type`, `enum`, `items` and `minItems` at every level, so a `feeds` entry missing its checksum fails, the `run` object is checked and `pruning_radii_km` must hold four numbers. `enum` applies to each array element, not the array.

## The server

The operator starts and stops the server, not the script, so a stopped run resumes without reloading the graph. At the default base URL the script asserts that `pgrep -x motis` returns exactly one process and reads that identifier to sample memory. Against any other it skips both, which lets the stub-server tests run inside the unit suite.

## Progress and summary

One flushed line per completed school:

    1841/4373 137353 12.4s requests=6 pairs=25746 rss=8.2GiB

The summary gives schools completed, requests issued and retried, wall seconds, peak server resident set size sampled every second with `ps -o rss=`, and output bytes for school files and records separately, which issue #17 records against the prediction.

## Tests

Written first, all under `uv run --with pyproj python -m unittest`, none needing a live server.

1. Request shape: the three bodies, their caps and units, the absent `time` on driving, `maxMatchingDistance: 250` on all three, and batching at 20,000 covering every origin once.
2. Leave-by rule, on a synthetic response, including the discard above 5,400 seconds.
3. Candidate origins: each mode's set is exactly the origins whose cell centre lies within its radius.
4. Transpose: known pairs give a record matching the record format spec's fixture byte for byte, and every origin gets exactly one object, all-sentinel ones included.
5. Manifest: a correct one validates; a missing key, a wrong type, an unexpected key, a `feeds` entry without its checksum and `pruning_radii_km` holding three numbers each fail.
6. Resume: against a stub HTTP server on another port through `--base-url`, stop halfway, rerun, and `<out-dir>/schools/` plus the record bytes match an uninterrupted run. The manifest is outside that claim, carrying the run's own timings.

The run itself is in `docs/precompute-runbook.md`.
