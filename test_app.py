import io
import json
import unittest
import urllib.error
from unittest.mock import Mock, patch

from datetime import datetime
from zoneinfo import ZoneInfo

from app import Handler, build_request, departure_time, nearest, results, time_filter, validate

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


class TestResults(unittest.TestCase):
    def test_sorts_by_seconds_before_rounding(self):
        schools = [school("1", 51.51, -0.12), school("2", 51.52, -0.13)]
        response = {"results": [{"locations": [
            {"id": "2", "properties": [{"travel_time": 119}]},
            {"id": "1", "properties": [{"travel_time": 61}]},
        ]}]}
        self.assertEqual([r["urn"] for r in results(schools, response)], ["1", "2"])

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


class TestHTTP(unittest.TestCase):
    def test_upstream_request_identifies_app_and_uses_timeout(self):
        def respond(request, timeout):
            self.assertEqual(request.get_header("User-agent"), "schools-by-travel-time/1.0")
            self.assertEqual(timeout, 30)
            self.assertEqual(json.loads(request.data), {"locations": []})
            return io.BytesIO(b'{"results": []}')

        with patch.dict("os.environ", TRAVELTIME_APP_ID="test", TRAVELTIME_API_KEY="test"), \
                patch("app.urllib.request.urlopen", side_effect=respond):
            self.assertEqual(time_filter({"locations": []}), {"results": []})

    def handler(self, raw, length=None):
        handler = Handler.__new__(Handler)
        handler.path = "/search"
        handler.headers = {"Content-Length": str(len(raw)) if length is None else length}
        handler.rfile = io.BytesIO(raw)
        handler._json = Mock()
        return handler

    def test_invalid_requests_return_400_without_upstream_call(self):
        for raw, length in ((b"{", None), (b"[]", None), (b"{}", None),
                            (b"\xff", None), (b" " * 4097, None),
                            (b"{}", "-1"), (b"{}", "bad")):
            with self.subTest(raw=raw[:20], length=length), patch("app.time_filter") as upstream:
                handler = self.handler(raw, length)
                handler.do_POST()
                self.assertEqual(handler._json.call_args.args[0], 400)
                upstream.assert_not_called()

    def test_upstream_failure_returns_502(self):
        handler = self.handler(json.dumps(body()).encode())
        with patch("app.time_filter", side_effect=RuntimeError("upstream unavailable")):
            handler.do_POST()
        handler._json.assert_called_once_with(502, {"error": "upstream unavailable"})

    def test_malformed_upstream_results_return_502(self):
        for response in ({"results": []}, {"results": [{"locations": [
                {"id": "unknown", "properties": [{"travel_time": 60}]}]}]}):
            with self.subTest(response=response), patch("app.time_filter", return_value=response):
                handler = self.handler(json.dumps(body()).encode())
                handler.do_POST()
                status, payload = handler._json.call_args.args
                self.assertEqual(status, 502)
                self.assertTrue(payload["error"])

    def test_http_connection_and_timeout_errors_are_readable(self):
        errors = [urllib.error.HTTPError("https://example.org", 401, "Unauthorized", {},
                                        io.BytesIO(b'{"description":"invalid credentials","error_code":1}')),
                  urllib.error.URLError("connection failed"), TimeoutError("timed out")]
        with patch.dict("os.environ", TRAVELTIME_APP_ID="test", TRAVELTIME_API_KEY="test"):
            for error in errors:
                with self.subTest(error=type(error)), patch("app.urllib.request.urlopen", side_effect=error):
                    with self.assertRaises(RuntimeError) as caught:
                        time_filter({})
                    expected = ("invalid credentials" if isinstance(error, urllib.error.HTTPError)
                                else str(error))
                    self.assertEqual(str(caught.exception), expected)

    def test_unstructured_upstream_errors_use_http_reason(self):
        with patch.dict("os.environ", TRAVELTIME_APP_ID="test", TRAVELTIME_API_KEY="test"):
            for raw in (b"<html>Forbidden</html>", b"{}"):
                error = urllib.error.HTTPError("https://example.org", 403, "Forbidden", {}, io.BytesIO(raw))
                with patch("app.urllib.request.urlopen", side_effect=error):
                    with self.assertRaisesRegex(RuntimeError, "^Forbidden$"):
                        time_filter({})


if __name__ == "__main__":
    unittest.main()
