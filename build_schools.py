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
