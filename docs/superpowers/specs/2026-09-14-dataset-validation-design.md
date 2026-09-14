# Dataset validation: issue #18 design

Date: September 14, 2026

## The script

`fixtures/validate_dataset.py``fixtures/validate_dataset.py`, standard library plus pyproj, runs as `uv run --with pyproj fixtures/validate_dataset.py <out-dir>/<version>`. It reads the manifest, `fixtures/origins.csv`, `schools.json` and every record, prints every failure rather than the first, and exits non-zero on any. Like the transpose it holds the whole matrix in memory, 93,217 times 34,984 bytes, 3.26 GB. pyproj converts the issue #4 coordinates to EPSG:27700 through `make_origins.PIPELINE` inverted, so validator and generator agree. Checks 1 to 8 run unattended; check 9 needs a person or browsing agent once the dataset exists.

## The checks

1. **Completeness.** The object count equals the manifest's `origin_count`, every identifier in `fixtures/origins.csv` having one record of `4 * 2 * school_count` bytes.

2. **Manifest.** It passes `fixtures/check_dataset_manifest.py`, `origins_sha256` matches `fixtures/origins.csv` and `school_index_sha256` matches `schools.json`.

3. **Empty origins.** No origin is sentinel in all four planes, except those in `fixtures/unreachable-origins.csv`, a committed file of identifier and reason. The builder fills it by running this check once and confirming each failure by hand; the Isles of Scilly, with no fixed link and no post-16 school within 90 minutes, are the expected case. Each row's reason lands in the same commit, so the list is reviewed, not grown to silence a failure.

4. **Mode sanity.** Public transport never exceeds walking for the same pair, sentinel as infinity. That holds by construction, so the threshold is zero and any failure is a writer bug. Driving or cycling exceeding walking is legitimate in small numbers, through one-way systems, pedestrianised centres and footpaths no vehicle uses, so that threshold is 1 percent of the pairs where both exist, far above genuine shortcuts, far below a swapped plane.

5. **Reach distance.** Measuring from the cell centre, no stored value lies beyond its mode's pruning radius, 90 km for public transport and walking, 25 km cycling and 136 km driving, nor beyond a plausible 90 minute speed bound: 7.5 km walking at 5 km/h, 27 km cycling at the 18 km/h nominal speed, and the radius itself for public transport and driving.

6. **Walk coverage.** Every origin whose centre is within 2 km straight line of a school has a walking value. Milestone 1 left four nearby schools with empty street durations; this check would have caught it.

7. **Reachable counts.** Report the minimum, median and maximum reachable schools per origin, per mode. Fail if the driving median is below 50: a 136 km radius over 4,373 schools should put hundreds within reach, so 50 is a smoke alarm, not a tuning knob. Fail if any mode's maximum equals the school count, which means the cap or radius did nothing.

8. **The ten spike journeys.** Nine of the ten in the issue #4 comment are comparable; Ryde is not, the planner having snapped that origin 4.6 miles away. For each, convert the origin to its cell, read the stored value for that school and mode, and assert it falls in the same ten minute display band as the planner figure, which for a transit journey is 08:30 minus the planner's latest feasible departure, not its journey duration, because the stored value is leave-by.

9. **Twelve new samples.** `fixtures/validation-samples.csv` holds `origin_id`, `urn`, `mode`, `planner_minutes`, `planner_departure`, `stored_seconds`, `agrees`. Fill it from TfL Journey Planner or Google Maps for Wednesday September 16, 2026 arriving by 08:30; the script asserts each row agrees within one band.

| Origin | URN | Mode | Character |
|---|---|---|---|
| 405_301 | 103584 | public_transport | Birmingham urban |
| 459_90 | 150099 | public_transport | Isle of Wight island |
| 415_635 | 137598 | public_transport | Berwick, Scottish border |
| 621_333 | 121241 | public_transport | Norfolk rural |
| 433_389 | 107140 | walking | Sheffield urban |
| 352_315 | 123608 | walking | Shrewsbury town |
| 351_253 | 117036 | cycling | Hereford, Welsh border |
| 419_539 | 130657 | cycling | County Durham |
| 191_53 | 112076 | cycling | Cornwall rural |
| 484_201 | 145244 | driving | Berkshire |
| 192_78 | 112076 | driving | Cornwall rural coast |
| 623_243 | 121242 | driving | Norfolk, long |
