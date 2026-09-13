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

    def test_rejects_wrong_types_and_non_finite_coordinates(self):
        for field, value in (("mode", []), ("mode", {}), ("mode", None),
                             ("lat", True), ("lng", "-0.12"),
                             ("lng", float("inf")), ("lat", 10 ** 400)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate(body(**{field: value}))


if __name__ == "__main__":
    unittest.main()
