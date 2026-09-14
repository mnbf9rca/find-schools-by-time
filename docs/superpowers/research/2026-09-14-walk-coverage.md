# Walk coverage diagnosis for issue 14

September 14, 2026. MOTIS 2.11.3, combined BODS and rail graph. The runner remains unchanged because the separate street endpoint also fails for all five selected pairs. A fourth request would not repair these gaps.

## Reproduction

The selected pairs come from `motis-spike/runner14-resumed/walk-coverage.csv`. All requests arrive by 08:30 British Summer Time on September 16, 2026. Durations below are seconds; “missing” means no returned walking duration.

A uses the exact runner intermodal request, including its containing batch in origin order. B uses the same body with just the selected origin. Both use WALK as the direct mode, TRANSIT as the transit mode, a 5,400-second direct cap, a 90-minute transit cap, and a 250-metre matching limit.

C posts to `/api/v1/one-to-many`, with the school as `one`, the origin as the sole `many`, mode WALK, max 5400, maxMatchingDistance 250, and arriveBy true. D gets `/api/v6/plan` from origin to school, with directModes WALK, empty transitModes, maxDirectTime 5400, maxMatchingDistance 250, and the same arrival time.

| School | URN | Origin | A batch size | A | B | C | D |
|---|---|---|---:|---|---|---|---|
| St Francis of Assisi Catholic College | 104255 | 406_299 | 18,773 | missing | missing | missing | missing |
| Reddam House Berkshire | 110137 | 477_169 | 19,092 | missing | missing | missing | missing |
| Torpoint Community College | 112041 | 244_55 | 7,341 | missing | missing | missing | missing |
| Simon Balle All-Through School | 140294 | 533_212 | 19,526 | missing | missing | missing | missing |
| Medina College | 150099 | 450_89 | 9,199 | missing | missing | missing | 1,063 |
| Simon Balle passing control | 140294 | 532_212 | 19,526 | 1,024 | 1,024 | 1,024 | 1,024 |

## Findings and controlled variations

Batch size and faster transit do not explain these results. The first two failures have no transit result either. [MOTIS computes street durations independently before transit durations](https://github.com/motis-project/motis/blob/v2.11.3/src/endpoints/one_to_many.cc#L277), and both one-to-many endpoints call the same street function.

The server configuration caps requested matching distances at 250 metres. The earlier 1,000-metre requests therefore did not test a wider effective limit. Temporarily raising that ceiling to 2,000 metres let the Walsall plan find a 1,384-second walk at 500 metres. The passing control stayed at 1,024 seconds. The street endpoint still returned nothing. The original configuration was restored byte for byte afterward.

For Medina, swapping `one` and `many` and setting arriveBy false produced 1,063 seconds through the street endpoint. Swapping the passing control instead lost its walk, so reversing every request is not a reliable correction.

The source identifies an algorithm difference worth investigating upstream: [one-to-many uses Dijkstra and prunes further matching candidates when its search reaches the cost limit](https://github.com/motis-project/osr/blob/a7b2ec2728544304ef1d8397b3042abc8d10f7e7/src/route.cc#L375), while [the plan uses bidirectional A-star](https://github.com/motis-project/motis/blob/v2.11.3/src/osr/street_routing.cc#L259). The probes establish false negatives in one-to-many, but do not isolate the exact internal candidate responsible.

Reddam, Torpoint and the failing Simon Balle pair still had no plan at an effective 2,000-metre matching limit and a six-hour direct cap. Their individual causes remain unresolved. This investigation does not establish one cause for all 43 sample gaps.

Raw requests and responses remain gitignored under `motis-spike/walk14-debug`. No replacement sample was run because the condition for changing the runner was not met. Both test commands passed. The server and sleep inhibitor were stopped, and escalated process checks found no MOTIS process.
