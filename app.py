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
