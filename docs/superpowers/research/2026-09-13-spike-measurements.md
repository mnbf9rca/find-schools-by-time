# Spike measurements and England extrapolation

2026-09-13 · [Issue #5](https://github.com/mnbf9rca/find-schools-by-time/issues/5). **The 18-core, 48 GB Mac is enough for the measured 30 km approach: 4,373 schools project to 1.75–36.24 hours, with 9.98–18.45 GB peak server RSS.** These are sample extrapolations, not nationwide measurements.

## Measurements

Sources: `motis-spike/sweep/{run}/{summary.json,requests.csv,results.csv}` and the top-level CSVs from [#3](https://github.com/mnbf9rca/find-schools-by-time/issues/3). Every run covers the same 100 schools, four modes and 282,716 origins per mode (2,827.16/school): EPSG:27700 1 km centres within 30 km, without a land mask. All requests returned HTTP 200. [Workers](../../../fixtures/sweep_spike.py) parallelise school-mode tasks; the cap affects every mode. Wall time includes grid generation, output and shutdown, excluding import/server startup. MB/GB are decimal; RSS KiB ×1,024 gives bytes. Peak server RSS was sampled from `ps` every 2 s, so short spikes may be missed; client/system memory was not measured.

| Run | Workers | Cap (min) | Wall (s) | Peak server RSS (GB) | Requests | Results CSV (MB) |
|---|---:|---:|---:|---:|---:|---:|
| #3 original | 1 | 240 | ≈3,000 | — | 3,700 | 20.118 |
| w1-cap240 | 1 | 240 | 2,983.4 | 18.045 | 3,700 | 20.118 |
| w4-cap240 | 4 | 240 | 1,074.0 | 18.404 | 3,700 | 20.118 |
| w8-cap240 | 8 | 240 | 674.2 | 18.449 | 3,700 | 20.118 |
| w8-cap90 | 8 | 90 | 143.7 | 9.978 | 3,700 | 11.360 |

The original's approximate wall time comes from #3; it has no summary or RSS measurement. Below, `elapsed_s` sums overlap under concurrency: neither wall nor CPU time. Each run has 100 transit requests and 1,200 per street mode.

| Run | Transit (s) | Walk (s) | Bike (s) | Car (s) |
|---|---:|---:|---:|---:|
| #3 original | 25.669 | 13.135 | 72.976 | 2,875.006 |
| w1-cap240 | 22.947 | 13.073 | 72.862 | 2,872.448 |
| w4-cap240 | 25.701 | 17.989 | 94.797 | 4,101.236 |
| w8-cap240 | 29.872 | 20.781 | 107.193 | 5,048.077 |
| w8-cap90 | 25.450 | 10.954 | 21.910 | 1,010.030 |

[Issue #4 validation](https://github.com/mnbf9rca/find-schools-by-time/issues/4) found that transit sweep seconds mean 08:30 minus latest departure, including early-arrival slack, rather than journey duration; that caveat does not change compute cost.

## Output and 30 km projection

Means divide CSV bytes and `gzip -9 -c results.csv` bytes by 100. Medians compress each school's rows separately, in original order with the CSV header, through `gzip -9 -c` on stdin.

| Run | CSV bytes | Gzip bytes | CSV bytes/school | Gzip bytes/school | Median separate-school gzip bytes |
|---|---:|---:|---:|---:|---:|
| w8-cap240 | 20,117,517 | 5,242,057 | 201,175.17 | 52,420.57 | 56,961.5 |
| w8-cap90 | 11,359,526 | 2,930,262 | 113,595.26 | 29,302.62 | 32,721.0 |

Multiply wall time and output by **4,373 / 100 = 43.73**, using the four summarised runs. At fixed concurrency the graph is reused, so server RSS stays at the measured envelope rather than scaling by school count. This assumes representative costs/reachability. Client memory grows: the script retains all origins and completed task results.

| Quantity | Minimum | Maximum |
|---|---:|---:|
| Elapsed hours | 1.75 | 36.24 |
| CSV GB | 0.497 | 0.880 |
| Whole-file gzip GB | 0.128 | 0.229 |
| Peak server RSS GB | 9.98 | 18.45 |

Elapsed endpoints are w8-cap90 and w1-cap240; maximum RSS is w8-cap240. At 240 minutes, eight workers project to 8.19 hours, four to 13.05 hours. The [commute research](2026-09-13-post-16-commute-statistics.md) supports testing 60–90 minutes around the cited 75-minute benchmark; 90 is generous, and 60 is unmeasured. It supplies no post-16 time distribution or guarantee of 30 km coverage.

## Removing the radius

The [hosting note, section 5](2026-09-13-public-deployment-hosting.md), assumes 130,000 cells/school: **568,490,000 pairs per mode**, 45.98 times the sample origins. Driving needs `ceil(130,000 / 250) = 520` requests/school versus 12: **2,273,960 requests**, a 43.33-fold increase. Each batch repeats the bounded street search: per-request overhead. At one worker/240 minutes, 250-origin batches average 2.395 s; final batches averaging only 77.16 origins still take 2.383 s. Origin matching, response handling and export scale with origins.

The table projects driving as `(car seconds / 1,200) × 520 × 4,373 / workers`. Transit uses `(transit seconds / 282,716) × 568,490,000 / workers`. Hours divide by 3,600. These use each configuration's observed request latency, including contention, and assume sustained worker occupancy; they exclude import and client overhead.

| Run | Car s/request | Transit ms/origin | Full-grid car hours | Full-grid transit hours |
|---|---:|---:|---:|---:|
| w1-cap240 | 2.394 | 0.0812 | 1,512.00 | 12.82 |
| w4-cap240 | 3.418 | 0.0909 | 539.70 | 3.59 |
| w8-cap240 | 4.207 | 0.1057 | 332.15 | 2.09 |
| w8-cap90 | 0.842 | 0.0900 | 66.46 | 1.78 |

Transit shares a timetable search per request, with access-path work/results per origin. Its 0.229–0.299 s/request includes both; similarly sized origin sets cannot isolate fixed overhead. Linear scaling is a sensitivity estimate, not a measured marginal cost or bound. A 130,000-origin POST needs a higher limit than the current 4,096; retaining that limit needs 32 POSTs/school, repeating the search. Wider geography and memory remain unmeasured: the 30 km output/RSS estimates do not apply, and retaining 568 million origin tuples makes client memory a separate constraint.

Compared with the earlier **1–10 days** for an unoptimised full grid, the measured 30 km workload is much cheaper, but it is a different workload. Applying the street batch multiplier to walking and cycling too, and the origin multiplier to transit, gives about **2.9 days at eight workers/90 minutes, 14.3 days at eight/240, and 65.4 days at one/240**, before client overhead. The old assumed 1–10 ms per transit origin was much higher than the observed 0.081–0.106 ms amortised cost; repeated driving searches dominate instead. Thus 1–10 days remains plausible with a shorter cap and parallelism, but understates the unchanged four-hour full-grid sweep.

**Use the Mac; Hetzner is unnecessary for the 30 km, 90-minute approach.** Eight workers project to 1.75 hours with 9.98 GB server RSS, leaving substantial room within 48 GB for client/OS; the worst measured server footprint is below 19 GB. This does not guarantee total memory or cover added rail. Use the two deferred optimisations—parallelism and a shorter cap; no-radius work also needs bounded client retention and remeasurement. The hosting note quotes Hetzner CCX43 at €0.4423/hour (64 GB, excluding VAT/IPv4) and Fly London performance-8x at $0.7692/hour (64 GB, plus storage), without measured speedups.
