# National Rail timetable to GTFS: issue #8 design

Date: September 14, 2026

## Goal

Give MOTIS the National Rail timetable the BODS feed lacks. Neither the bundle nor the zip is committed.

## The conversion script

Run as `Rscript fixtures/rail_cif_to_gtfs.R <cif-directory> <output-zip>`; both paths are arguments, so it runs from a worktree. It fails unless the directory holds the MCA, MSN and FLF files UK2GTFS needs.

`atoc2gtfs()` identifies files in the zip by extension, requiring `.mca`, `.msn` and `.flf`, but the nine RSPS5046 files all end in `.txt`. The script stages renamed copies of those three in a temporary zip, deleted afterwards; the other six are unused, the originals untouched.

Before `library(UK2GTFS)` it sets `options(UK2GTFS_opt_updateCachedDataOnLibaryLoad = FALSE)` in the main process and worker startup profile, so a load cannot swap the cached data. The script prints `packageDescription("UK2GTFS")$RemoteSha` and checksums of the cached tiploc and agency tables. The notes record the UK2GTFS-data release commit verified by matching those checksums to the release archive; UK2GTFS-data is a data repository, not an R package. A version will not do: UK2GTFS has no tag matching the reported 0.4.0 (tags run 0.001 to 0.003). Both SHAs go in `NOTES.md` and the licence rows.

The call passes `public_only = TRUE` and `working_timetable = FALSE`, keeping the public timetable with its pickup and set-down rules, plus `transfers = TRUE` for interchange times, `missing_tiplocs = TRUE` with `locations = "tiplocs"` for coordinates, `agency = "atoc_agency"`, `shapes = FALSE` and `ncores = 4`. Six of the seven are package defaults, written out so the call documents itself. Only `ncores` changes anything, and not the MCA parse, which UK2GTFS runs at one core regardless; it speeds the schedule-to-routes step. Overlays and cancellations are handled inside `atoc2gtfs()`, with missing-location records removed only by the post-processing described below.

`transfers = TRUE` builds `transfers.txt` from the FLF fixed links and MSN minimum change times alone; the ALF file is never read, because `importALF` is commented out in the package's `atoc.R`. Cross-station walks such as King's Cross to St Pancras therefore rely on MOTIS's footpath routing (`osr_footpath: true`, `link_stop_distance: 100`), not the feed.

Before `gtfs_write()`, post-processing drops stops without coordinates, stop times referring to absent stops and transfers with absent endpoints, and raises departures earlier than arrival to the arrival time; it prints every changed or dropped row count, which is recorded in `NOTES.md`. `gtfs_validate_internal()` reports all remaining errors, warnings and notes without blocking the export; the MOTIS import and dated plan request are the final gate.

The calendar is left as supplied, because MOTIS imports a narrow window anyway, though not seven days from `first_day`: `import.cc` starts a day earlier and spans `num_days` plus one, so 2026-09-14 with `num_days: 7` covers 2026-09-13 to 2026-09-20. Milestone 1's metrics recorded firstDay 2026-09-12, lastDay 2026-09-20. The script checks trips run on Wednesday 2026-09-16 from the `calendar.txt` bounds and Wednesday flag plus the `calendar_dates.txt` exceptions, and exits non-zero if none do.

## Licensing

The tiploc locations and ATOC agency table come from the separate ITSleeds/UK2GTFS-data repository under its own licence, reported as AGPL-3.0. Before use, add a UK2GTFS-data row to `LICENSES/README.md` with its licence, attribution and conditions, plus its verbatim text in `LICENSES/` unless it is MIT or GPL-3.

The National Rail row is complete (pull request #44); this one only removes the UK2GTFS row's pending wording and adds the UK2GTFS-data row.

## Importing

The zip is written to `motis-spike/feeds/rail.zip`. `motis import` takes `-c <config>` and `-d <data-dir>`; `motis server` takes only `-d <data-dir>` and reads the imported configuration there, so nothing is renamed. Copy `config.yml` to `motis-spike/config.rail.yml`, adding a `rail` entry beside `bods` under `timetable.datasets` with `path: feeds/rail.zip` and the same five per-dataset flags. Run `./motis import -c config.rail.yml -d data.rail` from `motis-spike/` so relative paths resolve, and serve with `./motis server -d data.rail`. Milestone 1's `data/` and `config.yml` are untouched. `merge_dupes_inter_src` stays `false`.

## Validation

1. Record the `agency_id` and `stop_id` overlap between the two zips. The issue's no-collision condition is met by per-source namespacing, not disjoint id sets: `docs/setup.md` says the dataset tag prefixes stop and trip ids and agencies register per source; an overlap is recorded, not a defect.
2. Check every rail stop sits between latitude 49.8 and 61.0 and longitude -8.7 and 1.9, and count stops with no coordinates. Check the six spot-check stations land within 500 m of their known positions, and list tiplocs whose coordinates came from the MSN fallback.
3. Spot check three services on Wednesday 2026-09-16 against the published timetable, each named by headcode or departure time: London King's Cross to Cambridge, Manchester Piccadilly to Leeds, and Brighton to London Victoria. Compare each stop against its published passenger time, allowing the CIF working time where the public field is blank, since `working_timetable = FALSE` falls back to it when that field is `0000`; working times carry half minutes.
4. Check each harder feature against its CIF record and GTFS counterpart: an overlay (short-term plan indicator O), a cancellation (indicator C), a restricted pickup or set-down, and an interchange time in `transfers.txt`.
5. Confirm the import exits zero and record `data.rail/timetable_metrics.json` against milestone 1; higher counts are evidence, not proof.

## Done when

This request returns an itinerary from King's Cross to Cambridge arriving by 08:30 on Wednesday 2026-09-16, with a leg traced to the rail dataset:

```
GET /api/v6/plan?fromPlace=51.5320,-0.1233&toPlace=52.1943,0.1372&time=2026-09-16T08:30:00%2B01%3A00&arriveBy=true&timetableView=false
```

The timestamp carries the +01:00 British Summer Time offset, and there is no date parameter. Matching a rail mode is not enough: the v6 rail modes are HIGHSPEED_RAIL, LONG_DISTANCE, NIGHT_RAIL, REGIONAL_RAIL, SUBURBAN and SUBWAY, and SUBWAY matches an Underground leg. Trace it to the rail dataset through the dataset tag prefixing its stop and trip ids.

## Notes

A "Rail GTFS (issue #8)" section in `motis-spike/NOTES.md` records the R version, both commit SHAs, every timing and size, the validator counts, each table's rows, every check's result, and the plan response.
