"""Check the issue 8 rail export against the pinned timetable and station samples."""
import csv
import io
import math
import sys
from pathlib import Path
import zipfile


def check():
    assert distance((51, 0), (51, 0)) == 0
    assert 111000 < distance((51, 0), (52, 0)) < 112000
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("stops.txt", '\ufeffstop_id,stop_name\nA,"Station, east"\n')
    with zipfile.ZipFile(archive) as z:
        assert list(rows(z, "stops")) == [{"stop_id": "A", "stop_name": "Station, east"}]
    print("Rail validation checks passed")


def rows(archive, table):
    with archive.open(table + ".txt") as stream:
        yield from csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"))


def distance(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 12742000 * math.asin(min(1, math.sqrt(h)))


def main(bods_path, rail_path, cif_directory):
    with zipfile.ZipFile(bods_path) as bods, zipfile.ZipFile(rail_path) as rail:
        for table, key in (("agency", "agency_id"), ("stops", "stop_id")):
            overlap = {r[key] for r in rows(bods, table)} & {r[key] for r in rows(rail, table)}
            print(f"{key} overlap: {len(overlap)}")
        stops = {r["stop_id"]: r for r in rows(rail, "stops")}
        bad = []
        missing_coordinates = 0
        for key, row in stops.items():
            lat, lon = row["stop_lat"], row["stop_lon"]
            missing_coordinates += not lat or not lon
            if not lat or not lon or not (49.8 <= float(lat) <= 61 and -8.7 <= float(lon) <= 1.9):
                bad.append((key, lat, lon))
        print(f"Stops missing coordinates: {missing_coordinates}")
        print(f"Stops outside bounds or missing coordinates: {bad}")
        positions = {
            "KNGX": (51.53088842, -0.122921342), "CAMBDGE": (52.1945746, 0.137554552),
            "MNCRPIC": (53.47671998, -2.228977818), "LEEDS": (53.79489697, -1.547435079),
            "BRGHTN": (50.82895322, -0.141225193), "VICTRIC": (51.49526139, -0.144540593),
        }
        for key, position in positions.items():
            row = stops[key]
            metres = distance(position, (float(row["stop_lat"]), float(row["stop_lon"])))
            print(f"{key} position difference: {metres:.1f} metres")
            assert metres <= 500
        active = {r["service_id"] for r in rows(rail, "calendar")
                  if r["start_date"] <= "20260916" <= r["end_date"] and r["wednesday"] == "1"}
        exceptions = [r for r in rows(rail, "calendar_dates") if r["date"] == "20260916"]
        active.update(r["service_id"] for r in exceptions if r["exception_type"] == "1")
        active.difference_update(r["service_id"] for r in exceptions if r["exception_type"] == "2")
        trips = {r["trip_id"]: r for r in rows(rail, "trips") if r["service_id"] in active}
        print(f"Active trips on 2026-09-16: {len(trips)}")
        # Published weekday columns: eNRT tables 015 page 1 and 175 page 17;
        # TransPennine Express May 2026 North timetable page 3.
        expected = {
            "1C00": [("KNGX", None, "05:01"), ("FNPK", "05:06", "05:07"),
                     ("STEVNGE", None, "05:31"), ("HITCHIN", None, "05:39"),
                     ("LTCE", None, "05:44"), ("BALDOCK", None, "05:47"),
                     ("ASHWELC", None, "05:52"), ("ROYSTON", None, "05:57"),
                     ("MELDRTH", None, "06:00"), ("SHPRTH", None, "06:04"),
                     ("FOXTON", None, "06:06"), ("CAMBSTH", None, "06:13"),
                     ("CAMBDGE", "06:19", None)],
            "1P11": [("MNCRPIC", None, "05:35"), ("SBYD", None, "05:49"),
                     ("MRSN", None, "06:02"), ("SLTHWTE", None, "06:06"),
                     ("HDRSFLD", "06:12", "06:13"), ("DWBY", None, "06:23"),
                     ("LEEDS", "06:35", "06:37"), ("YORK", "07:07", "07:10"),
                     ("MALTON", None, "07:35"), ("SEAMER", None, "07:52"),
                     ("SCARBRO", "07:59", None)],
            "1W01": [("BRGHTN", None, "05:39"), ("HYWRDSH", "05:54", "05:56"),
                     ("GTWK", "06:09", None), ("VICTRIC", "06:41", None)],
        }
        selected = set()
        departures = {("KNGX", "05:01:00"), ("MNCRPIC", "05:35:00"), ("BRGHTN", "05:39:00")}
        for row in rows(rail, "stop_times"):
            if row["trip_id"] in trips and (row["stop_id"], row["departure_time"]) in departures:
                selected.add(row["trip_id"])
                print("Selected train:", trips[row["trip_id"]])
        feature_trips = {key for key, r in trips.items() if r["service_id"].split()[0] in {"C34430", "C02022"}}
        calls = {key: [] for key in selected | feature_trips}
        for row in rows(rail, "stop_times"):
            if row["trip_id"] in calls:
                calls[row["trip_id"]].append(row)
        assert len(selected) == 3
        for key in selected:
            train = trips[key]["trip_short_name"]
            actual = sorted(calls[key], key=lambda r: int(r["stop_sequence"]))
            assert [r["stop_id"] for r in actual] == [r[0] for r in expected[train]], train
            for row, (_, arrival, departure) in zip(actual, expected[train]):
                assert arrival is None or row["arrival_time"] == arrival + ":00", row
                assert departure is None or row["departure_time"] == departure + ":00", row
            print(f"Published train {train}: all {len(actual)} calls and published times match")
        raw = {}
        with next(Path(cif_directory).glob("*MCA.txt")).open() as stream:
            current = None
            for line in stream:
                if line.startswith("BS"):
                    current = None
                    if line[3:9] in {"C34430", "G66645", "C02022"} and line[9:15] <= "260916" <= line[15:21] and line[23] == "1":
                        current = (line[3:9], line[79])
                        raw[current] = []
                if current:
                    raw[current].append(line)
        overlay = [key for key in feature_trips if trips[key]["service_id"].startswith("C34430 ")]
        assert len(overlay) == 1
        assert next(r for r in calls[overlay[0]] if r["stop_id"] == "BARKING")["arrival_time"] == "20:38:00"
        assert next(r for r in raw["C34430", "O"] if r.startswith("LIBARKING"))[25:29] == "2038"
        assert next(r for r in raw["C34430", "P"] if r.startswith("LIBARKING"))[25:29] == "2039"
        assert ("G66645", "C") in raw
        assert any(r["service_id"] == "G66645" and r["exception_type"] == "2" for r in exceptions)
        assert not any(r["service_id"] == "G66645" for r in trips.values())
        restricted = [r for key in feature_trips if trips[key]["service_id"].startswith("C02022 ") for r in calls[key] if r["stop_id"] == "PBRO"]
        assert len(restricted) == 1 and (restricted[0]["pickup_type"], restricted[0]["drop_off_type"]) == ("1", "0")
        assert next(r for r in raw["C02022", "O"] if r.startswith("LIPBRO"))[42:54].strip() == "D"
        with next(Path(cif_directory).glob("*MSN.txt")).open() as stream:
            minimum = int(next(r for r in stream if r.startswith("A    LONDON KINGS CROSS "))[63:65]) * 60
        assert next(r for r in rows(rail, "transfers") if r["from_stop_id"] == r["to_stop_id"] == "KNGX")["min_transfer_time"] == str(minimum)
        print(f"CIF features: overlay C34430, cancellation G66645, set-down C02022, King's Cross transfer {minimum} seconds match")


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        check()
    else:
        main(*sys.argv[1:])
