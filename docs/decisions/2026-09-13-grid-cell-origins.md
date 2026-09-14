# Use EPSG:27700 1 km grid cell centres as the origin geography

Date: September 13, 2026

## Decision

Origins are the centres of EPSG:27700 1 km grid cells, pruned to a radius around each school. The spike in issue #3 used a 30 km radius, giving about 2,824 origins per school. Measurement has since replaced that with one radius per mode; see `docs/decisions/2026-09-14-per-mode-pruning-radii.md`. There is no land mask or population mask yet.

## Why

The grid needs no download and no licence row in `LICENSES/README.md`, because the cell centres are generated arithmetically with pyproj, which the test suite already depends on. That made it the cheapest of the two options in section 6 of the hosting research note to get working for the spike.

It is also the denser of the two options: roughly 130,000 cells over England against 33,755 Census 2021 Lower Layer Super Output Areas. Denser origins mean the reachable-origin counts the spike produced are upper bounds, so any extrapolation from them overstates rather than understates the full run's cost. That is the safe direction for a measurement whose purpose is to decide whether the full run is affordable.

Population-weighted Lower Layer Super Output Area centroids and a land or population mask are not rejected. They were deferred until the full run's cost was known. That cost is now measured at 1.2 hours on eight workers, so neither is needed to make the run affordable. Issue #12 keeps the 1 km grid and masks it to the cells holding a postcode.

See `docs/superpowers/research/2026-09-13-public-deployment-hosting.md`, section 6, for the two geographies and the cell counts.
