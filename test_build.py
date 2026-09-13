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

    def test_drops_unusable_coordinates(self):
        for field in ("Easting", "Northing"):
            for value in ("-1", "nan", "inf", "not a number"):
                with self.subTest(field=field, value=value):
                    self.assertFalse(keep(row(**{field: value})))

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
