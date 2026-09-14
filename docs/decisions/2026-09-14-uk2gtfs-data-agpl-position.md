# The UK2GTFS-data AGPL position for the travel-time table

Date: September 14, 2026

## Decision

The precomputed travel-time table is not a modified version of UK2GTFS-data, so the AGPL-3.0 network clause does not reach the website or the table. The user decided this on September 14, 2026. The obligation kept is the credit line in `LICENSES/README.md`, and the verbatim licence text stays in `LICENSES/AGPL-3.0-only.txt`. If the rail GTFS zip itself, or the MOTIS graph built from it, is ever redistributed, that is a fresh decision, because both contain the coordinates.

## The facts

UK2GTFS converts the National Rail CIF timetable to GTFS. The timetable names stations by TIPLOC code but carries no coordinates, so UK2GTFS takes them from a separate dataset, UK2GTFS-data, published by the same maintainers at release v0.1.6. That dataset is licensed under the GNU Affero General Public License version 3. Its section 13 adds one rule to the ordinary GPL: anyone who modifies the licensed work and lets users interact with it over a network must offer those users the corresponding source of the modified version.

The coordinates flow into `stops.txt` of the rail GTFS zip, then into the MOTIS graph, and MOTIS uses them to compute the travel times. The travel-time table holds those times in seconds from origin grid cells to schools. It contains no station coordinates, no TIPLOC codes and nothing else copied from UK2GTFS-data. The website shows results for one postcode at a time.

## Why

The table is something computed using the dataset, not a modified version of it. Nothing from UK2GTFS-data can be read back out of the table. The AGPL is written for software that users run or interact with; the coordinates here are an input to an offline computation whose output is a different kind of thing altogether. This is the same reasoning as the OpenStreetMap decision, which treats the table as a produced work rather than a derivative database, and the two positions should stand or fall together.

The rail GTFS zip and the MOTIS graph are different. Both contain the coordinates verbatim, so redistributing either would mean redistributing part of UK2GTFS-data and the licence would apply in full. Neither is committed or published, so no obligation arises today.

See `docs/decisions/2026-09-14-odbl-position-for-the-travel-time-table.md` for the parallel OpenStreetMap position and `LICENSES/README.md` for the UK2GTFS-data row.
