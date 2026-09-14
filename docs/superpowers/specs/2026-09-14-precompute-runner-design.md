# Precompute runner: issues #14, #15 and #16 design

Date: September 14, 2026

## Goal

One plain script, `fixtures/precompute.py`, turns the school list and the origin grid into the published dataset. Run it as `uv run --with pyproj fixtures/precompute.py <out-dir>`, with `--workers N` defaulting to 8. Standard library plus pyproj.

The inputs are `schools.json` for the 4,373 schools and `fixtures/origins.csv` for the origins. pyproj projects the school coordinates to EPSG:27700 once at startup and is used nowhere else, because an origin's identifier already carries its easting and northing in kilometres.

## Requests

Three request groups per school against a MOTIS server already listening on 127.0.0.1:8080. Each is restricted to the origins within its mode's radius from `docs/decisions/2026-09-14-per-mode-pruning-radii.md` and split into batches of at most 20,000, in origin order. Build the bodies with `payload()` from `fixtures/measure_reach.py`, which sends them. Public transport uses `POST /api/experimental/one-to-many-intermodal` with `transitModes: ["TRANSIT"]`, `directMode: "WALK"` and `lat,lng` coordinates; cycling the same endpoint with `transitModes: []`, `directMode: "BIKE"` and `cyclingSpeed: 5.0`; driving `POST /api/v1/one-to-many` with `mode: "CAR"` and `lat;lng` coordinates. All set `arriveBy: true`, a 5,400 second cap and `time: "2026-09-16T08:30:00+01:00"`.

Three requests fill four planes: the public transport response carries a `street_durations` entry per origin, the direct walk, so the walking plane needs no fourth request. It inherits the 90 kilometre transit radius.

Apply `docs/decisions/2026-09-14-store-leave-by-minutes.md`: public transport takes the smaller of the `transit_durations` Pareto minimum and the `street_durations` entry, the other three their street durations alone. Discard anything above 5,400 seconds.

On a non-200 response or a dropped connection, halve the batch and retry each half, down to a single origin, which is a hard error. `fixtures/measure_reach.py` already does that.

## Per-school output

A worker takes one school, issues its three request groups, and writes `<out-dir>/schools/<urn>.bin` through a `.tmp` file and a rename, so a file exists only when complete.

That file holds four unsigned 32-bit counts, one per mode in plane order, then four sections of `(uint32 origin_index, uint16 seconds)` pairs ascending by index. The origin index is the zero-based row number in `fixtures/origins.csv`, 32 bits because there are more than 65,535 origins. Separate sections let the transpose read only the mode it needs.

Resume is that file's existence: the script skips every school that has one. No separate checkpoint is needed, because rename is atomic and a complete file is the only state worth keeping. The four measured schools reach 1,500 to 26,000 origins each, so expect about 120 KB per school and 500 MB in total.

## Transpose

A final pass turns the school files into one record per origin in the format of `docs/superpowers/specs/2026-09-14-per-origin-record-format.md`, at `<out-dir>/<version>/<origin-id>.bin`.

Holding every record at once would need 34,984 bytes per origin, 3.5 GB at 120,000 origins. Instead it works in slices of 30,000 origins: allocate the slice's four planes, about 1.05 GB, read every school file discarding pairs outside the slice, write the slice's records, move on. Three or four passes over 500 MB cost little and write no intermediate file.

## Manifest and publishing

`<out-dir>/<version>/manifest.json`, with `<out-dir>/current.json` holding `{"version": "..."}` alone, so publishing is one write. The version is the run's start time in UTC.

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
  "cycling_speed_mps": 5.0,
  "pruning_radii_km": [90, 90, 25, 136],
  "origin_count": 104312,
  "origins_sha256": "2f1c...",
  "school_count": 4373,
  "school_index_sha256": "43760fe2449c63cdb1ff7a4a03fc310da08c85990199b51868d7b87edbf120d9",
  "feeds": [{"path": "motis-spike/feeds/bods.zip", "sha256": "d69d71ec..."}],
  "run": {"started": "2026-09-14T09:30:00Z", "wall_seconds": 4412, "workers": 8,
          "requests": 26238, "peak_server_rss_bytes": 9448928051, "output_bytes": 3649253408}
}
```

`pruning_radii_km` is in plane order. The `feeds` list copies `path` and `sha256` from `fixtures/feed-manifest.json` unchanged.

`fixtures/manifest.schema.json` is the contract, a JSON Schema document. The script validates the manifest it wrote before exiting, using the standard library alone. Validating means reading the schema's `required`, `properties` and `enum` entries, then asserting that every required key is present, every value has the declared type, every enumerated value is listed, and no unexpected top-level key appears. That is not JSON Schema but the subset this file uses; the schema must stay inside it.

## The server

The operator starts and stops the server, not the script, so a stopped run resumes without reloading the graph and the script never detaches a process it cannot supervise. It asserts that `pgrep -x motis` returns exactly one process, reads that identifier to sample memory, and exits with a plain message otherwise.

## Progress and summary

One flushed line per completed school:

    1841/4373 137353 12.4s requests=6 pairs=25746 rss=8.2GiB

The summary gives schools completed, requests issued and retried, wall seconds, peak server resident set size sampled every second with `ps -o rss=`, and output bytes for the school files and the origin records. Issue #17 records these against the prediction.

## Tests

Written first.

1. Request shape. Public transport carries `directMode: "WALK"` and `maxDirectTime: 5400`, cycling carries `transitModes: []` with `directMode: "BIKE"` and `cyclingSpeed: 5.0`, driving posts to `/api/v1/one-to-many` with semicolon coordinates, and batches cap at 20,000, covering every origin once.
2. Leave-by rule. On a synthetic response, public transport takes the smaller of the transit minimum and the street duration, walking takes the street duration alone, and anything above 5,400 seconds is dropped.
3. Transpose. School files holding known pairs transpose into a record matching the round-trip fixture from the record format spec byte for byte, at 34,984 bytes.
4. Manifest. A correct manifest validates; a missing key, a wrong type and an unexpected key each fail.
5. Resume. Run the script against a stub HTTP server returning canned responses over a few schools, stop it halfway, rerun it, and assert the output directory is byte identical to an uninterrupted run.
6. Pruning. `--verify-pruning URN...` sends both the unpruned England grid and the pruned list for each named school, and asserts that the pruned result holds every origin the unpruned request reached. Reuse the assertion in `fixtures/measure_reach.py`. It needs a live server and stays out of the default suite.

Tests 1 to 5 run under `uv run --with pyproj python -m unittest`.

The run itself is in `docs/precompute-runbook.md`.
