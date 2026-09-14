# Dataset validation: issue #18 design

Date: September 14, 2026

## The script

`fixtures/validate_dataset.py`, standard library plus pyproj, runs as `uv run --with pyproj fixtures/validate_dataset.py <out-dir>/<version>`. It reads the manifest, `fixtures/origins.csv`, `schools.json` and every record, prints every failure rather than the first, and exits non-zero on any. It streams one record at a time: every check is per origin or per pair, check 7 holding four counts per origin and check 8 nine records.

A script run inside `fixtures/` puts that directory on the path, so the validator imports `make_origins` and `record` bare; `from fixtures import make_origins` fails there. From `record.py` it takes `SENTINEL`, `CAP`, `MODES`, `SCHOOL_COUNT`, `school_index_hash` and `decode`.

pyproj converts the issue #4 coordinates to EPSG:27700 through `make_origins.PIPELINE` inverted. Round the projected metres to whole metres before calling `make_origins.origin_id`: the inverse returns floats, on which its floor division gives `502.0_196.0`.

A band is `seconds // 600`, so band 6 covers 3,600 up to but not including 4,200 seconds; checks 8 and 9 both use it. Checks 1 to 8 run unattended; check 9 needs a person once the dataset exists.

## The checks

1. **Completeness and value range.** The object count equals the manifest's `origin_count`, every identifier in `fixtures/origins.csv` having one record of `4 * 2 * school_count` bytes. In the same pass, fail on any value from 5,401 to 65,534: neither under the cap nor the sentinel.

2. **Manifest.** It passes `fixtures/check_dataset_manifest.py`, `origins_sha256` matches `fixtures/origins.csv` and `school_index_sha256` matches `schools.json`.

3. **Empty origins.** No origin is sentinel in all four planes, except those in `fixtures/unreachable-origins.csv`, a committed file of identifier and reason. The builder fills it from one run of this check, confirming each failure by hand; the Isles of Scilly are the expected case. Each reason lands in the same commit, so the list is reviewed, not grown to silence failures.

4. **Mode sanity.** Public transport never exceeds walking for the same pair, sentinel as infinity. That holds by construction, so the threshold is zero and any failure is a writer bug. Driving or cycling exceeding walking is legitimate through one-way systems and footpaths, so that threshold is 1 percent of the pairs where both exist.

5. **Reach distance.** Measuring from the cell centre, the one speed bound worth asserting is walking: 7.5 km in 90 minutes, because MOTIS walks at about 4.15 km/h in issue #4 journey 8 and the runner does not pin the walk speed. The cycling, driving and transit bounds are dropped, having no figure behind them.

    Asserting the radius cannot fail, so report instead the greatest distance per mode at which a value was stored, and fail if it reaches the pre-margin measurement in `docs/decisions/2026-09-14-per-mode-pruning-radii.md`: 81.2 km public transport, 22.1 km cycling, 122.8 km driving. A value out at the measured edge is what radius truncation looks like.

6. **Walk coverage.** Read `walk_missing_pairs` from the manifest first: the runner counts the same gap, so a non-zero figure says where to look before any record is opened. Every origin whose centre is within 2 km straight line of a school has a walking value. Milestone 1 left four nearby schools with empty street durations; this check would have caught it. Two exclusions prevent failures on correct data.

    A school in `fixtures/unmatched-schools.csv`, a committed allow-list of URN and reason, is skipped: its coordinate is off the routable network, a defect for issue #9 rather than a validator failure. Lord Wandsworth College (116521), with 10 origin centres within 2 km, and The Grammar School At Leeds (108113), with 13, are in it already from issues #4 and #9. The builder adds further rows by hand from the first run, with reasons, in the same commit.

    Origins in `fixtures/unreachable-origins.csv` are skipped too: straight line is not walking distance, 2 km across an estuary being over 6 km on foot, so a cell centre such as 320_388 on the Dee sands is legitimately sentinel.

7. **Reachable counts.** Report the minimum, median and maximum reachable schools per origin, per mode. Fail if the driving median is below 50: the median origin has 259 schools within 60 km, so 50 is a smoke alarm, not a tuning knob. No maximum is worth asserting, the most within 136 km of any origin being 2,804.

8. **The nine spike journeys.** `fixtures/validation-spike.csv` holds the nine comparable journeys of the issue #4 comment as `lat`, `lng`, `urn`, `mode`, `planner_leave_by_minutes` and `source`. Ryde, the tenth, is not comparable: the planner snapped it 4.6 miles away. The column is explicit because the issue's table records a latest departure for Chorleywood alone. Journeys 2, 3, 4 and 7 use the returned itinerary's departure as a proxy, each saying so in `source`; Whitby compares against the planner's 11 minute walk. Convert each row's coordinates to its cell, read the stored value for that school and mode, and assert it falls within one band of the planner figure.

9. **Twelve new samples.** `fixtures/validation-samples.csv` holds `origin_id`, `urn`, `mode`, `planner_minutes`, `planner_departure` and `character`; the script derives the stored value and the verdict. Its twelve rows are committed with the planner columns blank, three per mode, spread across urban, island, border, rural and coastal origins, which `character` records. Fill it from TfL Journey Planner or Google Maps for Wednesday September 16, 2026 arriving by 08:30; each row must agree within one band. A `public_transport` row compares on 08:30 minus `planner_departure`, the stored value being leave-by, so `planner_minutes` is informational. Where the stored value is the sentinel, write `beyond cap` in `planner_minutes`: the row agrees if the planner's leave-by also exceeds 90 minutes and fails otherwise.
