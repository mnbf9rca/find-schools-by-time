# BODS gap audit and supplements: issue #9 design

Date: September 14, 2026

## Goal

Establish which services the timetable is missing, then add only those. The milestone 1 spike found 115 ferry, 99 tram, 29 metro and 2 rail routes in the BODS snapshot, but a count is not proof that a particular crossing or line is present. Without the Isle of Wight sailings, no Island sixth form is reachable at all.

## Scope

In scope: an audit of the feeds, a gap list, supplements for what is genuinely missing, and two routing checks. Out of scope: replacing BODS, importing the Traveline National Dataset, and anything about rail, which issue #8 covers.

## The audit script

`fixtures/audit_feeds.py`, run as `uv run fixtures/audit_feeds.py <zip> [<zip> ...]`. It uses only `zipfile` and `csv` from the standard library and streams the tables rather than loading them, because `stop_times.txt` in the BODS zip is 5.1 GB uncompressed. For each zip it prints route and trip counts by `route_type`, the same counts by agency, and every route whose type is not bus or coach with its agency, short name and long name. Zip paths are arguments so the script runs from a worktree against the main tree's files.

Run it on `motis-spike/feeds/bods.zip` and, once issue #8 has produced it, on `motis-spike/feeds/rail.zip`.

## What the audit is compared against

Every London Underground line; the Docklands Light Railway; London Trams; the Elizabeth line; London Overground and its named lines; the Thames Clippers river bus; the London cable car. Every ferry crossing that a student might use to reach an English sixth form: Wightlink's Portsmouth to Fishbourne, Portsmouth Harbour to Ryde Pier and Lymington to Yarmouth; Hovertravel's Southsea to Ryde; Red Funnel's Southampton to East Cowes and its Red Jet to West Cowes; and the Mersey ferry. The audit's full list of ferry routes is read for any other crossing that a sixth form depends on, and each one found is added to the gap list whether or not it was expected.

The Elizabeth line and London Overground are National Rail services and appear in the CIF bundle, so they may arrive through issue #8 rather than BODS. The gap list records which feed supplied each one, and a service present in either feed is not a gap.

## The gap list

`docs/superpowers/research/2026-09-14-timetable-gaps.md`, one row per expected service with these columns: service, operator, present in BODS, present in the rail feed, resolution. The resolution is one of "no action, already present", "supplement from the TfL Journey Planner feed", or "supplement by hand from the operator's published timetable". Every row has a resolution before any supplement is built.

## Supplements

Add nothing that is already present. For a missing London service, take the registered TfL Journey Planner TransXChange feed and convert only the missing services with `transxchange2gtfs()`, writing the result to `motis-spike/feeds/tfl.zip`. For a missing ferry, type the operator's published weekday timetable by hand into a small GTFS zip under `motis-spike/feeds/`, holding one agency, its piers, one route and one calendar per crossing, and enough morning sailings in each direction to support an arrival by 08:30. Do not import the Traveline National Dataset, because BODS already includes it.

Before any new source is downloaded, it gets a row in `LICENSES/README.md` and its verbatim licence text in `LICENSES/`. Each new zip is registered as its own dataset under `timetable.datasets` in a copy of the existing configuration. Import with `-c` for that configuration and `-d` for a new data directory, preserving every existing graph.

## Done when

The gap list exists with a resolution on every row, and two plan requests through `GET /api/v6/plan`, both arriving by 08:30 on Wednesday 2026-09-16, return itineraries of the right shape.

1. Portsmouth to a sixth form on the Isle of Wight, returning an itinerary that contains a ferry leg.
2. A journey between two central London points whose only sensible route is the Underground, returning an itinerary whose transit legs are all London Underground.

The server runs under a harness task and is stopped before the agent replies. The audit output, the supplements built, and both plan responses are appended to `motis-spike/NOTES.md` under a "Gap audit (issue #9)" heading.
