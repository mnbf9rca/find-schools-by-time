# BODS repository and the national GTFS feed

Cloned `https://github.com/department-for-transport-BODS/bods` (69 MB, shallow) to `scratchpad/bods`, and downloaded the national GTFS file to `scratchpad/gtfs-all.zip`. Headline: the repo is the publishing portal, not the converter. The GTFS file is built by a separate ITO World pipeline and simply served from an S3 bucket. The feed is Great Britain wide, bus-dominated, and contains no National Rail.

## 1. TransXChange parsing and GTFS export

1. **TransXChange parsing lives in `transit_odp/timetables/transxchange.py`** (635 lines). It defines `TransXChangeDocument`, a thin lxml wrapper with accessors such as `get_mode`, `get_services`, `get_journey_pattern_sections`, `get_all_vehicle_journeys`, `get_operating_period_start_date`, and `TransXChangeZip` for multi-file archives. The typed view of the same data is `transit_odp/timetables/dataclasses/transxchange.py`.
2. **The ETL that loads TransXChange into the database is `transit_odp/pipelines/pipelines/dataset_etl/`**, writing into the `transit_odp/transmodel/` models (services, journey patterns, stop activity). Validation against the TransXChange 2.4 schema and the DfT profile lives in `transit_odp/data_quality/pti/` (`validators.py`, `functions.py`, `constants.py`) with the schema zip at `transit_odp/pipelines/tests/data/TransXChange_schema_2.4.zip`.
3. **There is no TransXChange to GTFS converter in this repo.** Nothing reads Transmodel models and writes `routes.txt` or `stop_times.txt`. The only GTFS code is delivery: `transit_odp/browse/views/timetable_views.py` (lines 1204 to 1320) either calls an external service at `settings.GTFS_API_BASE_URL` (`/gtfs/regions` and `/gtfs?regionName=`) behind the `is_new_gtfs_api_active` flag, or falls back to `GTFSFileDownloader` in `transit_odp/common/downloaders.py`, which pulls `itm_<region>_gtfs.zip` objects from S3.
4. **The bucket is ITO World's.** `transit_odp/common/services.py` builds the client from `ITO_GTFS_AWS_ACCESS_KEY_ID`, `ITO_GTFS_AWS_SECRET_ACCESS_KEY`, `ITO_GTFS_AWS_STORAGE_BUCKET_NAME` (`config/settings/base.py` lines 535 to 542), and the `itm_` filename prefix is ITO's. The CHANGELOG issue tracker is `itoworld.atlassian.net`. So the conversion pipeline is ITO World's proprietary product, outside this repository. URL route: `transit_odp/browse/urls/timetables.py:110`, `download/gtfs-file/<str:id>/`.
5. **Consequence for us:** no reusable open-source converter here. To build our own GTFS we would use an external tool such as UK2GTFS, or feed TransXChange straight into a router.

## 2. Modes in the national GTFS download

6. Downloaded `https://data.bus-data.dft.gov.uk/timetable/download/gtfs-file/all/` on 13 September 2026: HTTP 200, **1,344,428,986 bytes (1.3 GB) zipped, 7.8 GB uncompressed**, ten files. `stop_times.txt` alone is 5.1 GB and `shapes.txt` 2.5 GB.
7. `feed_info.txt`: publisher "Bus Open Data Service (BODS)", **feed_start_date 20260913, feed_end_date 20271207**, version `20260913_022858`. The `calendar.txt` range matches, 2026-09-13 to 2027-12-07.
8. **635 agencies** in `agency.txt`, carrying a non-standard `agency_noc` column (National Operator Code). Agency URLs are mostly `https://www.traveline.info`.
9. **13,627 routes**, by `route_type`: **3 (bus) 13,135; 200 (coach, extended type) 246; 4 (ferry) 115; 0 (tram/light rail) 99; 1 (metro/subway) 29; 2 (rail) 2; 6 (aerial lift) 1.**
10. Inspecting the non-bus routes: type 1 is London Underground lines plus the Glasgow Subway (GRN and YEL); type 2 is the Docklands Light Railway only; type 6 is the London Cable Car. **There is no National Rail heavy rail in this feed.** Any rail journey outside London and the light-rail networks has to come from a separate source such as the Rail Data Marketplace.
11. So the answer to the mode question: **bus, coach, tram, metro and ferry yes; rail effectively no** (DLR and Underground only).
12. `stops.txt` has 311,735 stops keyed by ATCO code, with coordinates, wheelchair_boarding and parent_station.

## 3. Traveline National Dataset supplement

13. The merge is **not performed in this repo**. The only TNDS references are two identical blocks of user-facing copy in `transit_odp/browse/templates/browse/timetables/download_timetables.html` (lines 95 to 121): the GTFS data set covers "the whole of GB", is created from compliant data published to BODS, and "where data is not yet published on Bus Open Data, or is published but not compliant, this data is supplemented with Traveline National Dataset (TNDS)".
14. That supplementation therefore happens inside ITO World's pipeline before the zip reaches the S3 bucket. There is no code, configuration, or precedence rule in the repo describing how conflicts between a BODS feed and a TNDS feed are resolved, and nothing in the output marks which rows came from which source.
15. Practical implication: the feed is GB-wide because TNDS is GB-wide, even though BODS itself is an England service. Confirmed by stop counts below.

## 4. Licences

16. **The repository is MIT**, declared in `pyproject.toml` line 11 (`license = "MIT"`). There is no `LICENSE` file in the tree, which is a gap worth noting if we ever vendor code from it.
17. **The GTFS output is Open Government Licence v3.0 data**, free to reuse commercially with attribution; BODS states its data requires no licence agreement. Attribution should name the Bus Open Data Service, and TNDS where supplemented. <https://www.bus-data.dft.gov.uk/>, <https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/>

## 5. Useful for validating or filtering to England

18. **Do not use `ENGLISH_TRAVELINE_REGIONS`.** It is defined in `transit_odp/organisation/constants.py:130` as `["EA", "EM", "NE", "NW", "SE", "SW", "WM", "Y"]` and **deliberately excludes London** ("L" in the `TravelineRegions` enum at line 115), because London bus registration goes through TfL rather than the traffic commissioner. Using it as a geographic filter would silently drop every London service.
19. **Filter on the ATCO code prefix instead.** GTFS `stop_id` is the ATCO code, whose first digits are the NPTG administrative area. In this feed: **6xx (Scotland) 37,976 stops, 5xx (Wales) 19,471, everything else (England, including 490 London) 254,288.** Dropping `5` and `6` prefixes gives England plus the national 9xx pseudo-areas (910 rail, 930 ferry, 940 tram/metro), which should be kept because cross-border services use them.
20. **NaPTAN gives the authoritative mapping** if we want something better than a prefix test: `transit_odp/naptan/models.py` models `AdminArea` with `atco_code` and `traveline_region_id`, `Locality`, and `StopPoint`. The loader source is `NAPTAN_IMPORT_URL` = `https://naptan.api.dft.gov.uk/v1/access-nodes?dataFormat=XML` and `NPTG_IMPORT_URL` = `https://naptan.api.dft.gov.uk/v1/nptg` (`config/settings/base.py` lines 508 to 515). Both are free and OGL, and NPTG gives admin area to region to country mapping directly.
21. **Regional GTFS files avoid the 1.3 GB download entirely.** The same route accepts a region id in place of `all`, served as `itm_<region>_gtfs.zip`. Fetching the eight English regions plus London is far cheaper to process than the national file, and sidesteps the Scotland and Wales filtering question.
22. The repo's PTI validation rules in `transit_odp/data_quality/pti/` document what DfT considers compliant TransXChange, a useful reference for judging why a service might be missing, but they run on TransXChange, not on the GTFS we download.
