# Schools by travel time: MVP design

Date: September 13, 2026

## Goal

Enter a UK postcode, a time limit in minutes, and a transport mode. Get back every post-16 establishment in England reachable within that time, sorted by journey minutes. The typical question is "which sixth forms and colleges are within an hour of home by public transport?"

This is a personal tool run on your own machine. It is deliberately minimal.

## Scope

In scope:

- Open establishments in England that either have a statutory age range covering 16 to 18 or are recorded as having a sixth form, of any type: schools with sixth forms, sixth-form colleges, further education colleges, independents, special schools, pupil referral units, and 16 to 19 free schools. Establishments without usable coordinates are dropped.
- Transport modes: public transport (default), driving, cycling, walking.
- A single web page served locally.

Out of scope for the MVP: a map, accounts, saved searches, Ofsted ratings, admissions data, deployment anywhere other than your machine, and any UI beyond a form and a table.

Travel times are measured to each establishment's single registered location in the Get Information About Schools dataset, so a college with several campuses appears only at its registered site.

## Data sources

- Establishment data: the "All establishment data" CSV from https://get-information-schools.service.gov.uk/Downloads. The file is named `edubasealldataYYYYMMDD.csv`, is about 65 MB, and is encoded as Windows-1252. Coordinates are British National Grid eastings and northings. A copy lives in `data/extract/` and is not committed.
- Postcode geocoding: https://api.postcodes.io. No key, allows cross-origin browser requests, returns latitude and longitude.
- Travel times: TravelTime "Time Filter" endpoint, `POST https://api.traveltimeapp.com/v4/time-filter`. The request carries a `locations` array, where each entry has an `id` and a `coords` object, and a `departure_searches` array. A departure search takes `id`, `departure_location_id`, `arrival_location_ids`, `transportation`, `departure_time`, `travel_time`, and `properties`, and returns travel seconds for each reachable arrival location. A search may name at most 2,000 arrival location ids, and the maximum `travel_time` is 14,400 seconds (4 hours). Authenticated with the `X-Application-Id` and `X-Api-Key` headers. The free plan allows 60 searches a minute during the trial and 5 a minute afterwards, and is licensed for evaluation use only.

## Components

The whole application is six committed files — `build_schools.py`, `app.py`, `index.html`, `Makefile`, `.env.tpl`, and `.envrc` — plus the generated `schools.json`, which is also committed. Two test files sit alongside them.

### `build_schools.py` (run once, or whenever you refresh the CSV)

Usage: `uv run build_schools.py data/extract/edubasealldata20260913.csv > schools.json`. It must be run through `uv run`, because `pyproj` is declared as inline script metadata and plain `python3` cannot resolve it.

It reads the CSV and keeps a row only when all of the following hold:

- `EstablishmentStatus (name)` is `Open`.
- `GOR (code)` is one of A, B, D, E, F, G, H, J, or K, which are the nine English regions. This drops the 17 non-English rows that would otherwise survive.
- `Easting` and `Northing` are both numeric and greater than zero. This drops the 22 rows recorded at (0, 0).
- Either the statutory age range covers 16 to 18 (`StatutoryLowAge` is 16 or less and `StatutoryHighAge` is 18 or more) or `OfficialSixthForm (name)` is "Has a sixth form". The second branch keeps 47 sixth forms whose age columns are blank.

It converts eastings and northings to WGS84 latitude and longitude using `pyproj`. It writes a JSON array of objects with these keys: `urn`, `name`, `type` (from `TypeOfEstablishment (name)`), `postcode`, `website`, `sixth_form` (from `OfficialSixthForm (name)`), `lat`, and `lng`.

`sixth_form` is carried through for display only and is never filtered on beyond the rule above. It matters because 63 age-eligible schools say "Does not have a sixth form" and colleges say "Not applicable".

Websites are normalised: trim the `SchoolWebsite` value, prepend `https://` when it has no scheme (1,776 rows lack one), keep the value only if the resulting scheme is `http` or `https`, and otherwise drop it.

Expected output is about 4,300 rows and 800 KB. `schools.json` is committed so the server has no build step.

### `app.py` (the server)

Python 3 standard library only. Started with `make run`, which wraps it in `op run --env-file=.env.tpl`. It binds explicitly to 127.0.0.1, so it is not reachable from other machines. On startup it reads `TRAVELTIME_APP_ID` and `TRAVELTIME_API_KEY` from the environment and exits with a one-line error if either is missing. It loads `schools.json` into memory once.

Routes:

- `GET /` serves `index.html`.
- `POST /search` with a JSON body `{"lat": number, "lng": number, "minutes": integer, "mode": string}`.

Request validation, all failures returning 400:

- The body must be valid JSON and a JSON object, and must be at most 4 KB.
- All four fields must be present.
- `lat` and `lng` must be finite numbers inside the British Isles bounding box: latitude 49 to 61, longitude -8 to 2.
- `minutes` must be an integer, not a boolean, between 1 and 240. The upper bound is the endpoint cap of 14,400 seconds.
- `mode` must be one of `public_transport`, `driving`, `cycling`, or `walking`. These are passed straight through as `transportation.type`; the standard endpoint takes these plain names, not the `+ferry` variants the fast endpoint uses.

The server then sends one Time Filter request with a single departure search. The `locations` array holds the origin plus the selected schools, each school keyed by its URN as a string. In the departure search, `departure_location_id` is the origin, `arrival_location_ids` are the selected school ids, `transportation.type` is the requested mode, `travel_time` is the requested minutes multiplied by 60, and `properties` is `["travel_time"]`.

`departure_time` is 08:30 Europe/London on the next weekday, minus the requested minutes. So "within 60 minutes" means "leave at 07:30 and arrive by 08:30" against the real published timetable, rather than against a generic morning profile.

The endpoint accepts at most 2,000 arrival location ids, so the server sends the 2,000 schools nearest the origin by straight-line distance. A realistic search returns well under 100 schools, so this discards nothing a user would have seen.

<!-- ponytail: nearest-2,000 by straight-line distance; switch to chunked requests if a search ever fills the cap. -->

It joins the returned seconds back to the school records, sorts by seconds ascending, and responds with a JSON array of `{"urn", "name", "type", "postcode", "website", "sixth_form", "minutes"}`, where `minutes` is the returned seconds rounded up to a whole minute.

The upstream call uses a 30 second timeout. HTTP errors, connection failures, and timeouts all return a readable 502. The 502 body carries the TravelTime message and nothing else; it never includes request headers. The server never logs the outgoing request headers or body, because they carry the API credentials.

### `index.html` (the page)

Plain HTML and inline JavaScript, no framework and no build. A form with three fields: postcode, minutes (default 60), and mode (select, default public transport). On submit the page:

1. Disables the submit button and clears any previous results and error text, so a failure cannot leave a stale table on screen.
2. Calls `https://api.postcodes.io/postcodes/<postcode>`. Any non-2xx response, or a 2xx response with null coordinates, shows "Postcode not found or has no coordinates".
3. Posts latitude, longitude, minutes, and mode to `/search`.
4. Renders a table with columns name, type, postcode, sixth form, minutes, and a website link where one exists, sorted by minutes ascending, with a count above it.
5. Re-enables the submit button in a `finally` block, whether the search succeeded or failed.

All text taken from the data file is written with `textContent`, never `innerHTML`, so CSV content cannot inject markup.

A small "Travel times by TravelTime" credit sits beside the results. TravelTime's terms require attribution wherever their data is displayed.

Errors from either call appear as a single line of text above the table. The page has no other state.

### `Makefile`

Two targets: `build` runs the build script under `uv run` against the newest `data/extract/edubasealldata*.csv`, matching that filename pattern specifically because the directory holds other CSVs; `run` starts the server through `op run --env-file=.env.tpl -- python3 app.py`. The Makefile is the only place `op run` appears, matching the convention documented in `.envrc`.

### Secrets

`.envrc` exports a 1Password service account token for this repository and nothing else. `.env.tpl` maps `TRAVELTIME_APP_ID` and `TRAVELTIME_API_KEY` to `op://find-schools-by-time/traveltime/...` references. Both files are committed because they contain references, not values. Secret values exist only inside the server process started by `make run`.

`.gitignore` ignores `data/` entirely, which covers both the extract directory and the 117 MB source zip beside it.

## Error handling

- Missing environment variables: the server refuses to start and names the variable.
- Bad postcode: the page shows "Postcode not found or has no coordinates".
- Invalid request body: 400 from the server, shown on the page.
- TravelTime failure, including timeouts, connection failures, and the 5 per minute rate limit after the trial: 502 with the upstream message, shown on the page.

## Testing

Two small standard-library `unittest` files, run with `uv run --with pyproj python -m unittest`:

- `test_build.py` feeds the filter and conversion functions a handful of hand-written rows and checks that the region, coordinate, and age-or-sixth-form rules keep and drop the right rows, that website normalisation adds a scheme and drops unusable values, and that a known easting and northing converts to the expected latitude and longitude within a small tolerance.
- `test_app.py` checks the request body shape sent to TravelTime, the selection of the nearest 2,000 schools by straight-line distance, the `departure_time` calculation (08:30 Europe/London on the next weekday minus the requested minutes, including the case where today is a Friday, Saturday, or Sunday), the join and sort of a stubbed TravelTime response, and the 400 and 502 cases. The TravelTime call is replaced with a stub; no network access in tests.

No browser tests. The page is short enough to check by hand.
