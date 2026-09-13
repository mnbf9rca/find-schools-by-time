import unittest

from datetime import datetime
from zoneinfo import ZoneInfo

from app import build_request, departure_time, nearest, validate

LONDON = ZoneInfo("Europe/London")


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

    def test_rejects_wrong_types_and_non_finite_coordinates(self):
        for field, value in (("mode", []), ("mode", {}), ("mode", None),
                             ("lat", True), ("lng", "-0.12"),
                             ("lng", float("inf")), ("lat", 10 ** 400)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate(body(**{field: value}))


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


if __name__ == "__main__":
    unittest.main()
