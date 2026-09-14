# /// script
# requires-python = ">=3.11"
# dependencies = ["pyproj"]
# ///
"""Turn the Get Information About Schools CSV into schools.json.

Usage: uv run build_schools.py data/extract/edubasealldata20260913.csv data/a-level-and-other-16-to-18-results_2024-25/data/institution_performance_202225_API.csv > schools.json
"""

import csv
import hashlib
from pathlib import Path
import json
import math
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
        if not 0 < float(row["Easting"]) < math.inf or not 0 < float(row["Northing"]) < math.inf:
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


FILTERS = {"time_period": "202425", "exam_cohort": "A level", "disadvantage_status": "Total"}

RESULT_COLUMNS = {
    "students": "aps_per_entry_student_count",
    "progress": "value_added",
    "progress_banding": "progress_banding",
    "grade": "aps_per_entry_grade",
    "aps": "aps_per_entry",
    "retained_percent": "retained_percent",
    "aab_percent": "aab_percent",
    "best3_grade": "best_three_alevels_grade",
    "best3_aps": "best_three_alevels_aps",
}


def measure(value):
    """A float for a number, None for a blank or a suppression code, the string otherwise."""
    value = (value or "").strip()
    if value in ("", "z", "c", "x"):
        return None
    try:
        return float(value)
    except ValueError:
        return value


def load_results(path):
    """Map URN to the nine A level measures, for 2024/25 total-cohort rows only."""
    with open(path, encoding="utf-8", newline="") as f:
        return {
            row["school_urn"]: {k: measure(row[c]) for k, c in RESULT_COLUMNS.items()}
            for row in csv.DictReader(f)
            if all(row[k] == v for k, v in FILTERS.items())
        }


def write_school_index(schools, path):
    urns = sorted(school["urn"] for school in schools)
    digest = hashlib.sha256('\n'.join(urns).encode('utf-8')).hexdigest()
    Path(path).write_text(f'export const SCHOOL_COUNT = {len(urns)};\n'
                          f'export const SCHOOL_INDEX_SHA256 = "{digest}";\n')


def main(path, results_path, index_path=None):
    results = load_results(results_path)
    empty = dict.fromkeys(RESULT_COLUMNS, None)
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
                "gender": None if row["Gender (name)"] in ("", "Not applicable") else row["Gender (name)"],
                "religious_character": None if row["ReligiousCharacter (name)"] in ("", "None", "Does not apply") else row["ReligiousCharacter (name)"],
                "lat": lat,
                "lng": lng,
            } | results.get(row["URN"], empty))
    schools.sort(key=lambda school: school["urn"])
    json.dump(schools, sys.stdout)
    if index_path is not None:
        write_school_index(schools, index_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], index_path="school-index.js")
