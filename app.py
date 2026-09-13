"""Local server for the schools-by-travel-time search.

Start with: make run
"""

import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

MODES = {"public_transport", "driving", "cycling", "walking"}
MAX_ARRIVALS = 2000
LONDON = ZoneInfo("Europe/London")

HERE = Path(__file__).parent
SCHOOLS = json.loads((HERE / "schools.json").read_text())


def _number(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if not low <= value <= high:
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
    if not isinstance(body["mode"], str) or body["mode"] not in MODES:
        raise ValueError("mode must be one of " + ", ".join(sorted(MODES)))
    return lat, lng, minutes, body["mode"]


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


TIME_FILTER_URL = "https://api.traveltimeapp.com/v4/time-filter"
RESULT_KEYS = ("urn", "name", "type", "postcode", "website", "sixth_form",
               "students", "progress", "progress_banding", "grade", "aps",
               "retained_percent", "aab_percent", "best3_grade", "best3_aps")


def time_filter(payload):
    """POST one search to TravelTime. Raises RuntimeError carrying the upstream message."""
    request = urllib.request.Request(
        TIME_FILTER_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "schools-by-travel-time/1.0",
            "X-Application-Id": os.environ["TRAVELTIME_APP_ID"],
            "X-Api-Key": os.environ["TRAVELTIME_API_KEY"],
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        try:
            message = json.load(error)["description"]
        except (ValueError, KeyError, TypeError):
            message = error.reason
        raise RuntimeError(str(message)[:500]) from None
    except OSError as error:
        raise RuntimeError(str(error)) from None


def results(schools, response):
    """Join travel seconds back onto school records, sorted before rounding."""
    by_urn = {str(s["urn"]): s for s in schools}
    rows = []
    for location in sorted(response["results"][0]["locations"],
                           key=lambda location: location["properties"][0]["travel_time"]):
        school = by_urn[location["id"]]
        seconds = location["properties"][0]["travel_time"]
        rows.append({k: school[k] for k in RESULT_KEYS}
                    | {"minutes": math.ceil(seconds / 60)})
    return rows


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            return self._send(404, b"not found", "text/plain")
        self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")

    def do_POST(self):
        if self.path != "/search":
            return self._send(404, b"not found", "text/plain")
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if not 0 <= length <= 4096:
                raise ValueError("body must be at most 4 KB with a non-negative Content-Length")
            lat, lng, minutes, mode = validate(json.loads(self.rfile.read(length)))
        except ValueError as error:
            return self._json(400, {"error": str(error)})
        schools = nearest(SCHOOLS, lat, lng)
        payload = build_request(lat, lng, minutes, mode, schools, datetime.now(LONDON))
        try:
            response = time_filter(payload)
            rows = results(schools, response)
        except (RuntimeError, LookupError) as error:
            return self._json(502, {"error": str(error)})
        self._json(200, rows)

    def _json(self, status, data):
        self._send(status, json.dumps(data).encode(), "application/json")

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    for name in ("TRAVELTIME_APP_ID", "TRAVELTIME_API_KEY"):
        if not os.environ.get(name):
            sys.exit(f"{name} is not set; start the server with `make run`")
    print("Serving on http://127.0.0.1:8000", file=sys.stderr)
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()


if __name__ == "__main__":
    main()
