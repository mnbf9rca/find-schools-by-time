# Run the precompute on the user's Mac, not on rented compute

Date: September 13, 2026

## Decision

Both the MOTIS import and the full sweep run on the user's own Mac, an 18-core machine with 48 GB of RAM. No cloud machine is rented.

## Why

The machine has the headroom, measured rather than estimated. The import in issue #1 took 63 to 68 seconds of wall clock with a maximum resident set size under 13 GB, and produced a 4.8 GB graph. The sweep measurements in issue #5, over 100 schools and about 2,824 origins each, put the MOTIS server's peak resident memory at 18.0 GB and the run at 674 seconds on 8 workers with a 240 minute cap, or 144 seconds at the chosen 90 minute cap. Scaled by 43.73 to all 4,373 schools, that is about 8.2 hours in the worst case and under 2 hours at the cap actually chosen. The largest number in any of those measurements, 18 GB, leaves 30 GB of the machine's 48 GB unused.

The hosting research note's budget of 1 to 10 days and a rented 64 GB machine is superseded by these measurements. It rested on provisioning estimates that it labelled as estimates, and every one of them proved conservative by roughly two orders of magnitude on time.

Renting stays the fallback rather than being ruled out. If the origin set grows beyond the radius-pruned grid, for example by dropping the 30 km pruning or moving to an unpruned national grid, the run time grows with it and the hosting note's costed options apply: a Hetzner CCX43, 16 dedicated vCPU and 64 GB, at about €0.44 an hour, or Fly.io's `performance-8x` with 64 GB at about $0.77 an hour, in both cases deleted after the outputs are uploaded.

Running locally carries one constraint from AGENTS.md: an 8 hour job must not be detached. Do not start it with `nohup`, `disown`, `setsid` or a trailing `&`. It runs under a harness-controlled task that can be stopped, so nothing survives the end of a session.

See `docs/superpowers/research/2026-09-13-spike-measurements.md` for the sweep timings and memory samples, and `docs/superpowers/research/2026-09-13-public-deployment-hosting.md` for the superseded budget and the rental prices.
