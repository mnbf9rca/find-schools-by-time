# Schools by travel time: MVP design

Date: September 13, 2026

## Goal

Enter a UK postcode, a time limit in minutes, and a transport mode. Get back every post-16 establishment in England reachable within that time, sorted by journey minutes. The typical question is "which sixth forms and colleges are within an hour of home by public transport?"

This is a personal tool run on your own machine. It is deliberately minimal.

## Scope

In scope:

- Open establishments in England whose statutory age range covers 16 to 18, of any type: schools with sixth forms, sixth-form colleges, further education colleges, independents, special schools, pupil referral units, and 16 to 19 free schools. Establishments without coordinates are dropped.
- Transport modes: public transport (default), driving, cycling, walking.
- A single web page served locally.

Out of scope for the MVP: a map, accounts, saved searches, Ofsted ratings, admissions data, deployment anywhere other than your machine, and any UI beyond a form and a table.

## Data sources

- Establishment data: the "All establishment data" CSV from https://get-information-schools.service.gov.uk/Downloads. The file is named `edubasealldataYYYYMMDD.csv`, is about 65 MB, and is encoded as Windows-1252. Coordinates are British National Grid eastings and northings. A copy lives in `data/extract/` and is not committed.
- Postcode geocoding: https://api.postcodes.io. No key, allows cross-origin browser requests, returns latitude and longitude.
- Travel times: TravelTime "Time Filter" endpoint, `POST https://api.traveltimeapp.com/v4/time-filter`. One search accepts up to 2,000 destinations and returns travel minutes for each reachable one. Authenticated with the `X-Application-Id` and `X-Api-Key` headers. The free plan allows 60 searches a minute during the trial and 5 a minute afterwards, and is licensed for evaluation use only.

## Components

The whole application is four committed files plus a generated data file.

### `build_schools.py` (run once, or whenever you refresh the CSV)

Usage: `python3 build_schools.py data/extract/edubasealldata20260913.csv > schools.json`

It reads the CSV and keeps rows where `EstablishmentStatus (name)` is `Open`, `StatutoryLowAge` is 16 or less, `StatutoryHighAge` is 18 or more, and both `Easting` and `Northing` are present. It converts eastings and northings to WGS84 latitude and longitude using `pyproj`, declared as an inline script dependency so `uv run build_schools.py` works without a project file. It writes a JSON array of objects with these keys: `urn`, `name`, `type`, `postcode`, `website`, `lat`, `lng`. Expected output is about 4,360 rows and 800 KB. `schools.json` is committed so the server has no build step.

### `app.py` (the server)

Python 3 standard library only. Started with `make run`, which wraps it in `op run --env-file=.env.tpl`. On startup it reads `TRAVELTIME_APP_ID` and `TRAVELTIME_API_KEY` from the environment and exits with a one-line error if either is missing. It loads `schools.json` into memory once.

Routes:

- `GET /` serves `index.html`.
- `POST /search` with a JSON body `{"lat": number, "lng": number, "minutes": integer, "mode": string}`. The server picks the 2,000 schools nearest the origin by straight-line distance, sends one TravelTime Time Filter request with a departure search from the origin at the next weekday 08:00 local time, and responds with a JSON array of `{"urn", "name", "type", "postcode", "website", "minutes"}` for reachable schools, sorted by minutes. Mode is passed to TravelTime as one of `public_transport`, `driving`, `cycling`, `walking`; any other value is a 400. Minutes must be between 1 and 240; anything else is a 400. If TravelTime returns an error, the server responds 502 with the TravelTime message in the body.

The nearest-2,000 cut is a deliberate simplification and is marked with a `ponytail:` comment. From any origin in England it covers a radius of well over 50 km, which is beyond any plausible daily journey.

### `index.html` (the page)

Plain HTML and inline JavaScript, no framework and no build. A form with three fields: postcode, minutes (default 60), and mode (select, default public transport). On submit the page:

1. Calls `https://api.postcodes.io/postcodes/<postcode>` and shows the error text if the lookup fails.
2. Posts latitude, longitude, minutes, and mode to `/search`.
3. Renders a table with columns name, type, postcode, minutes, and a website link where one exists, sorted by minutes ascending, with a count above it.

Errors from either call appear as a single line of text above the table. The page has no other state.

### `Makefile`

Two targets: `build` runs the build script against the newest CSV in `data/extract/`, and `run` starts the server through `op run --env-file=.env.tpl -- python3 app.py`. The Makefile is the only place `op run` appears, matching the convention documented in `.envrc`.

### Secrets

`.envrc` exports a 1Password service account token for this repository and nothing else. `.env.tpl` maps `TRAVELTIME_APP_ID` and `TRAVELTIME_API_KEY` to `op://find-schools-by-time/traveltime/...` references. Both files are committed because they contain references, not values. Secret values exist only inside the server process started by `make run`.

## Data flow

Browser form submit, then postcodes.io returns latitude and longitude, then the browser posts to `/search`, then the server selects the nearest 2,000 schools, calls TravelTime once, joins the returned minutes back to the school records, sorts, and returns JSON, then the browser renders the table.

## Error handling

- Missing environment variables: the server refuses to start and names the variable.
- Bad postcode: postcodes.io returns 404 and the page shows "Postcode not found".
- Invalid minutes or mode: 400 from the server, shown on the page.
- TravelTime failure, including the 5 per minute rate limit after the trial: 502 with the upstream message, shown on the page.

## Testing

Two small standard-library `unittest` files, run with `python3 -m unittest`:

- `test_build.py` feeds the filter and conversion functions a handful of hand-written rows and checks that only open post-16 rows with coordinates survive and that a known easting and northing converts to the expected latitude and longitude within a small tolerance.
- `test_app.py` checks the nearest-2,000 selection, the request body shape sent to TravelTime, the join and sort of a stubbed TravelTime response, and the 400 cases. The TravelTime call is replaced with a stub; no network access in tests.

No browser tests. The page is short enough to check by hand.
