# Schools by Travel Time Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local web page that takes a UK postcode, a time limit, and a transport mode, and lists every post-16 establishment in England reachable within that time, sorted by journey minutes.

**Architecture:** A one-off build script turns the Get Information About Schools CSV into a committed `schools.json`. A standard-library HTTP server loads that file into memory, validates search requests, and forwards one TravelTime "Time Filter" request per search. A single static page does postcode geocoding in the browser and renders the results table.

**Tech Stack:** Python 3.11+ standard library, `pyproj` (only in the build script, via `uv run` inline script metadata), plain HTML with inline JavaScript, GNU Make, 1Password `op run` for secrets.

**Spec:** `docs/superpowers/specs/2026-09-13-schools-by-travel-time-design.md`

## Global Constraints

- The whole application is six committed files plus `schools.json` and two test files. Do not add directories, packages, frameworks, or dependencies beyond `pyproj` in the build script.
- `app.py` uses the Python standard library only.
- `.env.tpl`, `.envrc`, and `.gitignore` already exist and are committed. Do not modify them.
- All files live at the repository root: `/Users/rob/git/find-schools-by-time`.
- Tests are standard-library `unittest`, run with `uv run --with pyproj python -m unittest`. No network access in tests.
- The source CSV is `data/extract/edubasealldata20260913.csv`, encoded Windows-1252 (`cp1252`). `data/` is gitignored; never commit it.
- TravelTime endpoint: `POST https://api.traveltimeapp.com/v4/time-filter`, headers `X-Application-Id` and `X-Api-Key`, at most 2,000 arrival location ids, `travel_time` at most 14,400 seconds.
- Never log or return the outgoing TravelTime request headers or body; they carry the API credentials.
- Commit after every task.

---

### Task 1: `build_schools.py` and the generated `schools.json`

**Files:**
- Create: `build_schools.py`
- Create: `test_build.py`
- Create: `schools.json` (generated, committed)

**Interfaces:**
- Consumes: nothing.
- Produces: `schools.json`, a JSON array of objects with keys `urn` (string), `name` (string), `type` (string), `postcode` (string), `website` (string, empty when unusable), `sixth_form` (string), `lat` (float), `lng` (float). Tasks 2 to 4 read this file. Functions `keep(row) -> bool`, `website(value) -> str`, `to_latlng(easting, northing) -> (float, float)`.

- [ ] **Step 1: Write the failing test**

Create `test_build.py`:

```python
import unittest

from build_schools import keep, to_latlng, website


def row(**overrides):
    base = {
        "EstablishmentStatus (name)": "Open",
        "GOR (code)": "H",
        "Easting": "530000",
        "Northing": "180000",
        "StatutoryLowAge": "11",
        "StatutoryHighAge": "18",
        "OfficialSixthForm (name)": "Has a sixth form",
    }
    return base | overrides


class TestKeep(unittest.TestCase):
    def test_keeps_open_english_school_with_sixth_form(self):
        self.assertTrue(keep(row()))

    def test_drops_closed(self):
        self.assertFalse(keep(row(**{"EstablishmentStatus (name)": "Closed"})))

    def test_drops_non_english_region(self):
        self.assertFalse(keep(row(**{"GOR (code)": "W"})))

    def test_drops_zero_coordinates(self):
        self.assertFalse(keep(row(Easting="0", Northing="0")))

    def test_drops_blank_coordinates(self):
        self.assertFalse(keep(row(Easting="", Northing="")))

    def test_keeps_age_range_without_sixth_form(self):
        self.assertTrue(
            keep(row(StatutoryLowAge="16", StatutoryHighAge="19",
                     **{"OfficialSixthForm (name)": "Not applicable"}))
        )

    def test_keeps_blank_ages_when_sixth_form_present(self):
        self.assertTrue(keep(row(StatutoryLowAge="", StatutoryHighAge="")))

    def test_drops_primary_school(self):
        self.assertFalse(
            keep(row(StatutoryLowAge="4", StatutoryHighAge="11",
                     **{"OfficialSixthForm (name)": "Does not have a sixth form"}))
        )


class TestWebsite(unittest.TestCase):
    def test_adds_https_when_scheme_missing(self):
        self.assertEqual(website("  www.example.sch.uk "), "https://www.example.sch.uk")

    def test_keeps_existing_http_scheme(self):
        self.assertEqual(website("http://example.sch.uk"), "http://example.sch.uk")

    def test_drops_blank(self):
        self.assertEqual(website(""), "")

    def test_drops_non_web_scheme(self):
        self.assertEqual(website("mailto:head@example.sch.uk"), "")


class TestToLatLng(unittest.TestCase):
    def test_converts_british_national_grid(self):
        lat, lng = to_latlng("530000", "180000")
        self.assertAlmostEqual(lat, 51.503991, places=4)
        self.assertAlmostEqual(lng, -0.128354, places=4)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --with pyproj python -m unittest test_build -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'build_schools'`

- [ ] **Step 3: Write the implementation**

Create `build_schools.py`:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyproj"]
# ///
"""Turn the Get Information About Schools CSV into schools.json.

Usage: uv run build_schools.py data/extract/edubasealldata20260913.csv > schools.json
"""

import csv
import json
import sys
from urllib.parse import urlparse

from pyproj import Transformer

ENGLISH_REGIONS = {"A", "B", "D", "E", "F", "G", "H", "J", "K"}

_to_wgs84 = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)


def keep(row):
    """True when the row is an open English establishment serving 16 to 18 year olds."""
    if row["EstablishmentStatus (name)"] != "Open":
        return False
    if row["GOR (code)"] not in ENGLISH_REGIONS:
        return False
    try:
        if float(row["Easting"]) <= 0 or float(row["Northing"]) <= 0:
            return False
    except ValueError:
        return False
    if row["OfficialSixthForm (name)"] == "Has a sixth form":
        return True
    try:
        return int(row["StatutoryLowAge"]) <= 16 and int(row["StatutoryHighAge"]) >= 18
    except ValueError:
        return False


def website(value):
    """Normalise a SchoolWebsite value, or return "" when it is unusable."""
    url = (value or "").strip()
    if not url:
        return ""
    if not urlparse(url).scheme:
        url = "https://" + url
    return url if urlparse(url).scheme in ("http", "https") else ""


def to_latlng(easting, northing):
    lng, lat = _to_wgs84.transform(float(easting), float(northing))
    return round(lat, 6), round(lng, 6)


def main(path):
    schools = []
    with open(path, encoding="cp1252", newline="") as f:
        for row in csv.DictReader(f):
            if not keep(row):
                continue
            lat, lng = to_latlng(row["Easting"], row["Northing"])
            schools.append({
                "urn": row["URN"],
                "name": row["EstablishmentName"],
                "type": row["TypeOfEstablishment (name)"],
                "postcode": row["Postcode"],
                "website": website(row["SchoolWebsite"]),
                "sixth_form": row["OfficialSixthForm (name)"],
                "lat": lat,
                "lng": lng,
            })
    json.dump(schools, sys.stdout)


if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run --with pyproj python -m unittest test_build -v`
Expected: PASS, 13 tests.

- [ ] **Step 5: Generate `schools.json` and sanity-check it**

Run:

```bash
uv run build_schools.py data/extract/edubasealldata20260913.csv > schools.json
python3 -c "import json;d=json.load(open('schools.json'));print(len(d));print(d[0])"
```

Expected: roughly 4,300 records (anything between 4,000 and 4,600 is fine), a file around 800 KB, and a first record carrying all eight keys with a plausible English latitude and longitude.

- [ ] **Step 6: Commit**

```bash
git add build_schools.py test_build.py schools.json
git commit -m "Build schools.json from the establishment CSV"
```

---

### Task 2: `app.py` request validation

**Files:**
- Create: `app.py`
- Create: `test_app.py`

**Interfaces:**
- Consumes: `schools.json` from Task 1.
- Produces: `validate(body) -> (lat, lng, minutes, mode)`, raising `ValueError` with a human-readable message. `MODES`, the set of the four allowed transport modes. Tasks 3 and 4 add functions to the same file.

- [ ] **Step 1: Write the failing test**

Create `test_app.py`:

```python
import unittest

from app import validate


def body(**overrides):
    return {"lat": 51.5, "lng": -0.12, "minutes": 60, "mode": "public_transport"} | overrides


class TestValidate(unittest.TestCase):
    def test_accepts_a_good_body(self):
        self.assertEqual(validate(body()), (51.5, -0.12, 60, "public_transport"))

    def test_rejects_non_object(self):
        with self.assertRaises(ValueError):
            validate([1, 2, 3])

    def test_rejects_missing_field(self):
        b = body()
        del b["mode"]
        with self.assertRaises(ValueError):
            validate(b)

    def test_rejects_latitude_outside_the_british_isles(self):
        with self.assertRaises(ValueError):
            validate(body(lat=12.0))

    def test_rejects_longitude_outside_the_british_isles(self):
        with self.assertRaises(ValueError):
            validate(body(lng=40.0))

    def test_rejects_non_finite_latitude(self):
        with self.assertRaises(ValueError):
            validate(body(lat=float("nan")))

    def test_rejects_boolean_minutes(self):
        with self.assertRaises(ValueError):
            validate(body(minutes=True))

    def test_rejects_fractional_minutes(self):
        with self.assertRaises(ValueError):
            validate(body(minutes=60.5))

    def test_rejects_minutes_above_the_endpoint_cap(self):
        with self.assertRaises(ValueError):
            validate(body(minutes=241))

    def test_rejects_minutes_below_one(self):
        with self.assertRaises(ValueError):
            validate(body(minutes=0))

    def test_rejects_unknown_mode(self):
        with self.assertRaises(ValueError):
            validate(body(mode="teleport"))

    def test_accepts_every_allowed_mode(self):
        for mode in ("public_transport", "driving", "cycling", "walking"):
            self.assertEqual(validate(body(mode=mode))[3], mode)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --with pyproj python -m unittest test_app -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Write the implementation**

Create `app.py`:

```python
"""Local server for the schools-by-travel-time search.

Start with: make run
"""

import json
import math
from pathlib import Path

MODES = {"public_transport", "driving", "cycling", "walking"}
MAX_ARRIVALS = 2000

HERE = Path(__file__).parent
SCHOOLS = json.loads((HERE / "schools.json").read_text())


def _number(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return value


def validate(body):
    """Return (lat, lng, minutes, mode), or raise ValueError with a readable message."""
    if not isinstance(body, dict):
        raise ValueError("body must be a JSON object")
    missing = [k for k in ("lat", "lng", "minutes", "mode") if k not in body]
    if missing:
        raise ValueError("missing fields: " + ", ".join(missing))
    lat = _number(body["lat"], 49, 61, "lat")
    lng = _number(body["lng"], -8, 2, "lng")
    minutes = body["minutes"]
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= 240:
        raise ValueError("minutes must be an integer between 1 and 240")
    if body["mode"] not in MODES:
        raise ValueError("mode must be one of " + ", ".join(sorted(MODES)))
    return lat, lng, minutes, body["mode"]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run --with pyproj python -m unittest test_app -v`
Expected: PASS, 12 tests.

- [ ] **Step 5: Commit**

```bash
git add app.py test_app.py
git commit -m "Validate search requests"
```

---

### Task 3: The TravelTime request body

**Files:**
- Modify: `app.py` (append after `validate`)
- Modify: `test_app.py` (append a new test class and the import)

**Interfaces:**
- Consumes: `MAX_ARRIVALS` and `SCHOOLS` from Task 2.
- Produces: `nearest(schools, lat, lng, limit=MAX_ARRIVALS) -> list`, `departure_time(minutes, now) -> str`, `build_request(lat, lng, minutes, mode, schools, now) -> dict`. Task 4 calls `nearest` and `build_request`.

- [ ] **Step 1: Write the failing test**

In `test_app.py`, change the import line to:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from app import build_request, departure_time, nearest, validate

LONDON = ZoneInfo("Europe/London")
```

Then append these classes above the `if __name__ == "__main__":` block:

```python
def school(urn, lat, lng):
    return {"urn": urn, "name": f"School {urn}", "type": "Academy", "postcode": "N1 1AA",
            "website": "", "sixth_form": "Has a sixth form", "lat": lat, "lng": lng}


class TestNearest(unittest.TestCase):
    def test_sorts_by_straight_line_distance(self):
        schools = [school("3", 51.8, -0.12), school("1", 51.51, -0.12), school("2", 51.6, -0.12)]
        self.assertEqual([s["urn"] for s in nearest(schools, 51.5, -0.12)], ["1", "2", "3"])

    def test_caps_at_the_endpoint_limit(self):
        schools = [school(str(i), 51.5 + i / 10000, -0.12) for i in range(2500)]
        picked = nearest(schools, 51.5, -0.12)
        self.assertEqual(len(picked), 2000)
        self.assertEqual(picked[-1]["urn"], "1999")


class TestDepartureTime(unittest.TestCase):
    def test_weekday_uses_tomorrow(self):
        now = datetime(2026, 9, 16, 14, 0, tzinfo=LONDON)  # Wednesday
        self.assertEqual(departure_time(60, now), "2026-09-17T07:30:00+01:00")

    def test_friday_skips_to_monday(self):
        now = datetime(2026, 9, 18, 14, 0, tzinfo=LONDON)  # Friday
        self.assertEqual(departure_time(60, now), "2026-09-21T07:30:00+01:00")

    def test_saturday_skips_to_monday(self):
        now = datetime(2026, 9, 19, 14, 0, tzinfo=LONDON)
        self.assertEqual(departure_time(60, now), "2026-09-21T07:30:00+01:00")

    def test_sunday_uses_monday(self):
        now = datetime(2026, 9, 20, 14, 0, tzinfo=LONDON)
        self.assertEqual(departure_time(60, now), "2026-09-21T07:30:00+01:00")

    def test_subtracts_the_requested_minutes(self):
        now = datetime(2026, 9, 16, 14, 0, tzinfo=LONDON)
        self.assertEqual(departure_time(90, now), "2026-09-17T07:00:00+01:00")


class TestBuildRequest(unittest.TestCase):
    def test_shapes_the_upstream_body(self):
        schools = [school("1", 51.51, -0.12), school("2", 51.52, -0.13)]
        now = datetime(2026, 9, 16, 14, 0, tzinfo=LONDON)
        payload = build_request(51.5, -0.12, 60, "driving", schools, now)
        self.assertEqual(payload["locations"][0],
                         {"id": "origin", "coords": {"lat": 51.5, "lng": -0.12}})
        self.assertEqual(payload["locations"][1],
                         {"id": "1", "coords": {"lat": 51.51, "lng": -0.12}})
        self.assertEqual(len(payload["locations"]), 3)
        search, = payload["departure_searches"]
        self.assertEqual(search["departure_location_id"], "origin")
        self.assertEqual(search["arrival_location_ids"], ["1", "2"])
        self.assertEqual(search["transportation"], {"type": "driving"})
        self.assertEqual(search["travel_time"], 3600)
        self.assertEqual(search["properties"], ["travel_time"])
        self.assertEqual(search["departure_time"], "2026-09-17T07:30:00+01:00")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --with pyproj python -m unittest test_app -v`
Expected: FAIL with `ImportError: cannot import name 'build_request' from 'app'`

- [ ] **Step 3: Write the implementation**

Append to `app.py`, and add `from datetime import timedelta` and `from zoneinfo import ZoneInfo` to the imports plus `LONDON = ZoneInfo("Europe/London")` beside the other constants:

```python
def nearest(schools, lat, lng, limit=MAX_ARRIVALS):
    """The closest schools by straight-line distance, longitude scaled for latitude."""
    # ponytail: nearest-2,000 by straight-line distance; switch to chunked requests
    # if a search ever fills the cap.
    scale = math.cos(math.radians(lat))

    def distance_squared(s):
        return (s["lat"] - lat) ** 2 + ((s["lng"] - lng) * scale) ** 2

    return sorted(schools, key=distance_squared)[:limit]


def departure_time(minutes, now):
    """ISO time to leave to arrive at 08:30 Europe/London on the next weekday."""
    day = now.astimezone(LONDON) + timedelta(days=1)
    while day.weekday() > 4:
        day += timedelta(days=1)
    arrival = day.replace(hour=8, minute=30, second=0, microsecond=0)
    return (arrival - timedelta(minutes=minutes)).isoformat()


def build_request(lat, lng, minutes, mode, schools, now):
    ids = [str(s["urn"]) for s in schools]
    return {
        "locations": [{"id": "origin", "coords": {"lat": lat, "lng": lng}}] + [
            {"id": str(s["urn"]), "coords": {"lat": s["lat"], "lng": s["lng"]}}
            for s in schools
        ],
        "departure_searches": [{
            "id": "search",
            "departure_location_id": "origin",
            "arrival_location_ids": ids,
            "transportation": {"type": mode},
            "departure_time": departure_time(minutes, now),
            "travel_time": minutes * 60,
            "properties": ["travel_time"],
        }],
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run --with pyproj python -m unittest test_app -v`
Expected: PASS, 20 tests.

- [ ] **Step 5: Commit**

```bash
git add app.py test_app.py
git commit -m "Build the TravelTime request"
```

---

### Task 4: The upstream call, the result join, and the HTTP server

**Files:**
- Modify: `app.py` (append after `build_request`)
- Modify: `test_app.py` (append a new test class and extend the import)

**Interfaces:**
- Consumes: `validate`, `nearest`, `build_request` from Tasks 2 and 3.
- Produces: `time_filter(payload) -> dict` raising `RuntimeError` carrying the upstream message, `results(schools, response) -> list`, and a runnable server on `127.0.0.1:8000` serving `GET /` and `POST /search`.

- [ ] **Step 1: Write the failing test**

In `test_app.py`, extend the app import to `from app import build_request, departure_time, nearest, results, validate` and append this class:

```python
class TestResults(unittest.TestCase):
    def test_joins_sorts_and_rounds_up(self):
        schools = [school("1", 51.51, -0.12), school("2", 51.52, -0.13), school("3", 51.9, -0.1)]
        response = {"results": [{"locations": [
            {"id": "2", "properties": [{"travel_time": 3540}]},
            {"id": "1", "properties": [{"travel_time": 61}]},
        ]}]}
        rows = results(schools, response)
        self.assertEqual([r["urn"] for r in rows], ["1", "2"])
        self.assertEqual([r["minutes"] for r in rows], [2, 59])
        self.assertEqual(set(rows[0]), {"urn", "name", "type", "postcode", "website",
                                        "sixth_form", "minutes"})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --with pyproj python -m unittest test_app -v`
Expected: FAIL with `ImportError: cannot import name 'results' from 'app'`

- [ ] **Step 3: Write the implementation**

Append to `app.py`, adding `import os`, `import sys`, `import urllib.error`, `import urllib.request`, `from datetime import datetime`, and `from http.server import BaseHTTPRequestHandler, HTTPServer` to the imports:

```python
TIME_FILTER_URL = "https://api.traveltimeapp.com/v4/time-filter"
RESULT_KEYS = ("urn", "name", "type", "postcode", "website", "sixth_form")


def time_filter(payload):
    """POST one search to TravelTime. Raises RuntimeError carrying the upstream message."""
    request = urllib.request.Request(
        TIME_FILTER_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Application-Id": os.environ["TRAVELTIME_APP_ID"],
            "X-Api-Key": os.environ["TRAVELTIME_API_KEY"],
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(error.read().decode("utf-8", "replace")[:500]) from None
    except OSError as error:
        raise RuntimeError(str(error)) from None


def results(schools, response):
    """Join travel seconds back onto school records, sorted by whole minutes."""
    by_urn = {str(s["urn"]): s for s in schools}
    rows = []
    for location in response["results"][0]["locations"]:
        school = by_urn[location["id"]]
        seconds = location["properties"][0]["travel_time"]
        rows.append({k: school[k] for k in RESULT_KEYS}
                    | {"minutes": math.ceil(seconds / 60)})
    return sorted(rows, key=lambda r: r["minutes"])


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            return self._send(404, b"not found", "text/plain")
        self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")

    def do_POST(self):
        if self.path != "/search":
            return self._send(404, b"not found", "text/plain")
        length = int(self.headers.get("Content-Length") or 0)
        if length > 4096:
            return self._json(400, {"error": "body must be at most 4 KB"})
        try:
            lat, lng, minutes, mode = validate(json.loads(self.rfile.read(length)))
        except ValueError as error:
            return self._json(400, {"error": str(error)})
        schools = nearest(SCHOOLS, lat, lng)
        payload = build_request(lat, lng, minutes, mode, schools, datetime.now(LONDON))
        try:
            response = time_filter(payload)
        except RuntimeError as error:
            return self._json(502, {"error": str(error)})
        self._json(200, results(schools, response))

    def _json(self, status, data):
        self._send(status, json.dumps(data).encode(), "application/json")

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.command} {self.path}\n")


def main():
    for name in ("TRAVELTIME_APP_ID", "TRAVELTIME_API_KEY"):
        if not os.environ.get(name):
            sys.exit(f"{name} is not set; start the server with `make run`")
    print("Serving on http://127.0.0.1:8000", file=sys.stderr)
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run --with pyproj python -m unittest test_app -v`
Expected: PASS, 21 tests.

- [ ] **Step 5: Check the 400 and 502 paths end to end against a running server**

Run this in one shell, with a deliberately wrong API key so the upstream call fails:

```bash
TRAVELTIME_APP_ID=x TRAVELTIME_API_KEY=x python3 app.py &
sleep 1
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8000/search -d '{"lat":51.5}'
curl -s -w '\n%{http_code}\n' -X POST localhost:8000/search \
  -d '{"lat":51.5,"lng":-0.12,"minutes":60,"mode":"public_transport"}'
kill %1
```

Expected: the first `curl` prints `400`; the second prints a TravelTime error message followed by `502`. Confirm the server's own log lines show only `POST /search` and never the request headers or body.

- [ ] **Step 6: Commit**

```bash
git add app.py test_app.py
git commit -m "Call TravelTime and serve the search endpoint"
```

---

### Task 5: `index.html` and the `Makefile`

**Files:**
- Create: `index.html`
- Create: `Makefile`

**Interfaces:**
- Consumes: `GET /` and `POST /search` from Task 4, and `build_schools.py` from Task 1.
- Produces: the finished application. Nothing later depends on it.

- [ ] **Step 1: Write `index.html`**

```html
<!doctype html>
<meta charset="utf-8">
<title>Schools by travel time</title>
<style>
  body { font: 16px system-ui, sans-serif; margin: 2rem; max-width: 60rem; }
  label { margin-right: 1rem; }
  table { border-collapse: collapse; margin-top: 1rem; }
  th, td { border-bottom: 1px solid #ddd; padding: 0.3rem 0.6rem; text-align: left; }
  #error { color: #b00; }
</style>
<h1>Schools by travel time</h1>
<form id="search">
  <label>Postcode <input name="postcode" required></label>
  <label>Minutes <input name="minutes" type="number" min="1" max="240" value="60" required></label>
  <label>Mode
    <select name="mode">
      <option value="public_transport">Public transport</option>
      <option value="driving">Driving</option>
      <option value="cycling">Cycling</option>
      <option value="walking">Walking</option>
    </select>
  </label>
  <button id="go">Search</button>
</form>
<p id="error"></p>
<p id="count"></p>
<table id="results"></table>
<p><small>Travel times by TravelTime</small></p>
<script>
const form = document.getElementById('search');
const errorLine = document.getElementById('error');
const countLine = document.getElementById('count');
const table = document.getElementById('results');

function cell(row, text, tag = 'td') {
  const el = document.createElement(tag);
  el.textContent = text;
  row.appendChild(el);
  return el;
}

function render(rows) {
  const header = table.insertRow();
  for (const name of ['Name', 'Type', 'Postcode', 'Sixth form', 'Minutes', 'Website']) {
    cell(header, name, 'th');
  }
  for (const r of rows) {
    const tr = table.insertRow();
    cell(tr, r.name);
    cell(tr, r.type);
    cell(tr, r.postcode);
    cell(tr, r.sixth_form);
    cell(tr, r.minutes);
    const last = cell(tr, '');
    if (r.website) {
      const a = document.createElement('a');
      a.href = r.website;
      a.textContent = 'Website';
      last.appendChild(a);
    }
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const go = document.getElementById('go');
  go.disabled = true;
  errorLine.textContent = '';
  countLine.textContent = '';
  table.textContent = '';
  try {
    const data = new FormData(form);
    const geo = await fetch(
      'https://api.postcodes.io/postcodes/' + encodeURIComponent(data.get('postcode').trim()));
    const geoBody = geo.ok ? await geo.json() : null;
    const place = geoBody && geoBody.result;
    if (!place || place.latitude == null || place.longitude == null) {
      errorLine.textContent = 'Postcode not found or has no coordinates';
      return;
    }
    const search = await fetch('/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lat: place.latitude,
        lng: place.longitude,
        minutes: Number(data.get('minutes')),
        mode: data.get('mode'),
      }),
    });
    const rows = await search.json();
    if (!search.ok) {
      errorLine.textContent = rows.error || 'Search failed';
      return;
    }
    countLine.textContent = rows.length + ' schools within ' + data.get('minutes') + ' minutes';
    render(rows);
  } catch (e) {
    errorLine.textContent = String(e);
  } finally {
    go.disabled = false;
  }
});
</script>
```

- [ ] **Step 2: Write the `Makefile`**

Use real tab characters for the recipe lines, not spaces.

```make
CSV = $(lastword $(sort $(wildcard data/extract/edubasealldata*.csv)))

build:
	uv run build_schools.py $(CSV) > schools.json

run:
	op run --env-file=.env.tpl -- python3 app.py

.PHONY: build run
```

- [ ] **Step 3: Check the Makefile picks the right CSV**

Run: `make -n build`
Expected: `uv run build_schools.py data/extract/edubasealldata20260913.csv > schools.json`

- [ ] **Step 4: Run the whole test suite**

Run: `uv run --with pyproj python -m unittest -v`
Expected: PASS, 34 tests across `test_build` and `test_app`.

- [ ] **Step 5: Check the page by hand**

Run `make run`, open `http://127.0.0.1:8000`, and search for a real postcode such as `SW1A 1AA` with 60 minutes by public transport. Confirm a sorted table appears with a count above it, that a bad postcode such as `ZZ1 1ZZ` shows "Postcode not found or has no coordinates" and leaves no stale table behind, and that the submit button is usable again after both outcomes.

- [ ] **Step 6: Commit**

```bash
git add index.html Makefile
git commit -m "Add the search page and Makefile"
```
