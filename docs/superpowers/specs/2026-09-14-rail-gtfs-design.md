# National Rail timetable to GTFS: issue #8 design

Date: September 14, 2026

## Goal

Give MOTIS a National Rail timetable, which the BODS feed lacks. In scope: a conversion script, a rail GTFS zip, its MOTIS registration, and the validation. Neither the CIF bundle nor the zip is committed.

## The conversion script

Run as `Rscript fixtures/rail_cif_to_gtfs.R <cif-directory> <output-zip>`. Both paths are arguments, so it runs from a worktree against the main tree.

`atoc2gtfs()` reads a zip and identifies the files inside by extension, requiring `.mca`, `.msn` and `.flf`. The nine RSPS5046 files all end in `.txt`, so the script stages renamed copies of those three into a temporary zip, deleted afterwards. The originals are untouched; the other six are unused.

Before `library(UK2GTFS)` it sets `options(UK2GTFS_opt_updateCachedDataOnLibaryLoad = FALSE)`, so a load cannot swap the cached data under a run, and records the version or checksums of the cached UK2GTFS-data files used: the tiploc locations and the ATOC agency table.

It calls `atoc2gtfs()` with `public_only = TRUE` and `working_timetable = FALSE`, keeping the public timetable and its pickup and set-down rules; `transfers = TRUE` for interchange times; `missing_tiplocs = TRUE` and `locations = "tiplocs"` for coordinates; `agency = "atoc_agency"`; `shapes = FALSE`; and `ncores = 4`. Overlays and cancellations are handled inside `atoc2gtfs()`, so the script filters nothing itself.

The result goes through `gtfs_validate_internal()`. Any Error severity is fatal and exits non-zero; Warning and Note rows are printed for the record. `gtfs_write()` writes the zip, taking the output path split into folder and stem.

The calendar is left as supplied; MOTIS imports only seven days from `first_day: 2026-09-14`. The script checks trips run on Wednesday 2026-09-16, reading the `calendar.txt` start and end dates with the Wednesday flag, then applying the `calendar_dates.txt` exceptions, and exits non-zero if none do.

## Licensing

The tiploc locations and the ATOC agency table come from the separate ITSleeds/UK2GTFS-data repository, not from the timetable or the converter code, under its own licence, reported as AGPL-3.0. Before use, add a UK2GTFS-data row to `LICENSES/README.md` with its licence, attribution and conditions, and its verbatim text in `LICENSES/` unless it is MIT or GPL-3, already there.

The National Rail row is complete, recorded on main by pull request #44. This pull request only removes the pending wording from the UK2GTFS row and adds the UK2GTFS-data row.

## Importing

The zip is written to `motis-spike/feeds/rail.zip` by absolute path. Import reads `motis-spike/config.yml`, not `motis-spike/data/config.yml`, which is a copy it overwrites. So: rename `motis-spike/data` to `data.bods-only`, keeping the milestone 1 measurements reproducible; add a `rail` entry to `motis-spike/config.yml` beside `bods` under `timetable.datasets`, with `path: feeds/rail.zip` and the same five per-dataset flags `bods` carries; then run `./motis import` from `motis-spike/` so relative paths resolve. `merge_dupes_inter_src` stays `false`.

## Validation

1. Record the `agency_id` and `stop_id` overlap between the two zips. MOTIS namespaces identifiers by source, so an overlap is recorded, not fatal.
2. Check every rail stop's latitude falls between 49.8 and 61.0 and longitude between -8.7 and 1.9, and count stops missing coordinates. Check London King's Cross, Cambridge, Manchester Piccadilly, Leeds, Brighton and London Victoria each land within 500 m of their known coordinates. Count and list tiplocs whose coordinates came from the MSN fallback.
3. Spot check three services on Wednesday 2026-09-16 against the published timetable, each named by headcode or departure time so the check repeats: London King's Cross to Cambridge, Manchester Piccadilly to Leeds, and Brighton to London Victoria. Compare each stop against its published passenger time, allowing the CIF working time where the public field is blank, because `working_timetable = FALSE` falls back to it when the public field is `0000`, and working times carry half minutes.
4. Ordinary services do not show the harder features survived, so check one of each by finding the CIF record and its GTFS counterpart: an overlay with short-term plan indicator O, a cancellation with indicator C, a restricted pickup or set-down, and an interchange time in `transfers.txt`.
5. Confirm the import exits zero. Record `data/timetable_metrics.json` against the milestone 1 figures; higher counts are evidence, not proof.

## Done when

A plan request returns an itinerary from London King's Cross to Cambridge arriving by 08:30 on Wednesday 2026-09-16 with a leg whose route comes from the rail dataset. A rail mode alone is not enough: an Underground leg would match. Use `GET /api/v6/plan`, the current endpoint on MOTIS 2.11.3, with `fromPlace` and `toPlace` as latitude and longitude, `time` as an ISO timestamp for 08:30 London time that day, `arriveBy=true` and `timetableView=false`.

## Notes

A "Rail GTFS (issue #8)" section is appended to `motis-spike/NOTES.md`: the R, UK2GTFS and UK2GTFS-data versions, the conversion time and zip size, the validator's counts by severity, each GTFS table's row count, every check above with its result, the import timing and metrics, and the plan response.
