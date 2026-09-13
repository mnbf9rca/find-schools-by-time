# Search outward from each school with an 08:30 arrival, not outward from each origin

Date: September 13, 2026

## Decision

The precompute runs one search per school per mode, with `arriveBy` set to 08:30 on a term-time weekday and the origins as the destination list. It does not run a search per origin. The results are inverted afterwards into one record per origin.

## Why

The question the app answers is "which schools can I reach by 08:30", so the fixed point of every search is the arrival at the school, not the departure from home. Running searches school-outward expresses that directly and keeps the count small: 4,373 schools times four modes is about 17,500 one-to-many searches, against hundreds of thousands of searches if every origin cell were its own search.

The saving is real rather than bookkeeping, because MOTIS runs one transit search per request and then calculates access paths for each destination. Adding destinations to an existing request therefore costs access-path work only, while adding requests repeats the whole transit search. The issue #3 sweep measured this: 100 transit sweeps, each covering about 2,824 origins, took 26 seconds of request time in total, because each school needed only one shared transit search.

The direction has a trap the hosting research note flags explicitly: a reverse search must arrive at the school, not depart from it. Getting this backwards produces plausible-looking times that answer the wrong question, because morning services run towards schools and the return journey is not symmetric.

See `docs/superpowers/research/2026-09-13-public-deployment-hosting.md`, section 5, for the sweep arithmetic and the reverse-search warning.
