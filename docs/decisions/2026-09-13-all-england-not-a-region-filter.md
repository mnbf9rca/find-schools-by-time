# Keep every English post-16 establishment rather than filtering by region

Date: September 13, 2026

## Decision

`schools.json` holds every open establishment in England whose statutory ages span 16 to 18 or that has a sixth form, about 4,370 rows. There is no region filter.

## Why

The user first asked for London, then pointed out that Hertfordshire is commutable. Hertfordshire sits in the East of England government region, not the South East, so a region filter would have dropped it. Keeping all of England costs nothing: the file is under 1 MB, TravelTime bills per search rather than per destination, and the nearest-2,000 selection at query time handles any origin.
