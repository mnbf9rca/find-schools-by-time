"""Local server for the schools-by-travel-time search.

Start with: make run
"""

import json
import math
from datetime import timedelta
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
