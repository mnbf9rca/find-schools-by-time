# National Rail timetable to GTFS: issue #8 design

Date: September 14, 2026

## Goal

Give MOTIS a National Rail timetable, so a journey that needs a train returns a real itinerary instead of a bus-only one. The BODS feed has no heavy rail, which is why the milestone 1 spike put Colfe's School at 76 minutes against Transport for London's 44 minutes.

## Scope

In scope: one conversion script, one rail GTFS zip, its registration in the MOTIS config, and the validation that proves it worked. Out of scope: any change to the web app, the schools data, or the sweep scripts. Neither the CIF bundle nor the zip is committed.

## The conversion script

`fixtures/rail_cif_to_gtfs.R`, run as `Rscript fixtures/rail_cif_to_gtfs.R <cif-directory> <output-zip>`. Both paths are arguments, because the builder works in a git worktree while the input and output live in the main tree. The script fails with a clear message if either argument is missing, if the directory holds no `*MCA.txt`, or if the output path already exists.

`atoc2gtfs()` reads a zip, so the script zips the nine CIF files into a temporary file first and deletes it afterwards. It then calls `atoc2gtfs()` with `public_only = TRUE` and `working_timetable = FALSE`, which together keep the public timetable and its pickup and set-down rules rather than the operational one; `transfers = TRUE`, which produces the interchange times; `missing_tiplocs = TRUE` and `locations = "tiplocs"`, which supply the station coordinates; `agency = "atoc_agency"`; `shapes = FALSE`, because the MOTIS config sets `with_shapes: false`; and `ncores = 4`. Short-term plan overlays and cancellations are handled inside `atoc2gtfs()`, so the script must not filter any record itself. The result goes through `gtfs_validate_internal()`, whose problems are printed but are not fatal, then `gtfs_write()` with the output path split into its folder and stem.

The calendar is left as the bundle supplies it. Trimming it in R buys nothing, because MOTIS imports only the seven days from `first_day: 2026-09-14`. The script does assert that `calendar.txt` brackets 2026-09-16 and that at least one trip runs that Wednesday, and exits non-zero if not.

## Registering the feed

The rail zip is written to `motis-spike/feeds/rail.zip` by absolute path. `motis-spike/data/config.yml` gains a `rail` entry beside `bods` under `timetable.datasets`, with `path: feeds/rail.zip` and the same five per-dataset flags that `bods` carries. `merge_dupes_inter_src` stays `false`.

The milestone 1 graph must survive, so the existing `motis-spike/data` is renamed to `data.bods-only` and a fresh `data` is created holding a copy of the edited `config.yml` before `./motis import` runs. Disk is not a constraint.

## Validation

1. Compare the `agency_id` and `stop_id` sets of the two zips and record the size of each intersection. MOTIS namespaces identifiers by source, so an overlap is not fatal, but it is recorded.
2. Check every rail stop has a latitude between 49.8 and 61.0 and a longitude between -8.7 and 1.9, and count any stop missing coordinates.
3. Spot check three services on Wednesday 2026-09-16 against the published timetable, matching calling pattern and every time to the minute: a London King's Cross to Cambridge service, a Manchester to Leeds service, and a Brighton to London Victoria service.
4. Confirm the import exits zero and that `data/timetable_metrics.json` shows more locations and trips than the milestone 1 figures.

## Done when

A plan request through `GET /api/v1/plan`, from London King's Cross to Cambridge, arriving by 08:30 on Wednesday 2026-09-16, returns an itinerary containing a leg on a rail mode. The request shape comes from the MOTIS 2.11.3 OpenAPI document. The server runs under a harness task and is stopped before the agent replies.

## Housekeeping

The same pull request removes the "Pending: not yet used." wording from the UK2GTFS row in `LICENSES/README.md`. The National Rail timetable row still needs the agreement text from registration, which only the user can supply, so it stays pending.

A "Rail GTFS (issue #8)" section is appended to `motis-spike/NOTES.md`, recording the R and UK2GTFS versions, the command run, the conversion wall clock and zip size, the row counts of each GTFS table, the two collision counts, the coordinate check result, the three spot checks, the import timing, the new timetable metrics, and the plan response.
