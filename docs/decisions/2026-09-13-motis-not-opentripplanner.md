# Use a self-hosted MOTIS 2 as the precompute engine, not OpenTripPlanner

Date: September 13, 2026

## Decision

The precompute runs on MOTIS 2.11.3, self-hosted, using the native macOS arm64 binary on the user's own Mac. OpenTripPlanner 2 is not used. Neither is the public Transitous instance, which runs MOTIS but forbids commercial use, so the engine is one we host ourselves.

## Why

The spike in issue #1 measured MOTIS on the full England inputs (the 1.69 GB Geofabrik England extract and the 1.34 GB national Bus Open Data Service GTFS feed) and it was far cheaper than the hosting research note budgeted. Two independent runs imported everything in 63 and 68 seconds of wall clock, with a maximum resident set size of 12.56 GB and 11.27 GB, well under 13 GB. The resulting graph is 4.8 GB on disk. The server starts in about a second and sits at roughly 2 GB resident. A `one-to-many-intermodal` request for eight destinations returned in 0.185 seconds, and in the issue #3 sweep, 100 transit searches each covering about 2,824 origins cost 26 seconds of request time in total. The research note had budgeted 1 to 6 hours and 64 GB of RAM for the import alone.

OpenTripPlanner is heavier and less suited to this shape of work. It needs a JVM with a very large heap: the hosting note's provisioning estimate is 128 GB of RAM against MOTIS's 64 GB, and OpenTripPlanner's own build instructions use `-Xmx100G`. OpenTripPlanner 2 also dropped the analysis and isochrone features of version 1 and points users at R5 for batch analytics, so its ordinary journey requests are the wrong foundation for a batch of this size. MOTIS gives a one-to-many transit matrix directly, at a memory cost the existing Mac already meets, so no rented compute is needed.

See `docs/superpowers/research/2026-09-13-public-deployment-hosting.md` for the engine comparison and the provisioning estimates this measurement replaced.
