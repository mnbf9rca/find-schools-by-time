import tempfile
import unittest
from pathlib import Path

from build_schools import keep, load_results, measure, to_latlng, website


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


PERF_HEADER = ("time_period,exam_cohort,disadvantage_status,school_urn,"
               "aps_per_entry_student_count,value_added,progress_banding,aps_per_entry_grade,"
               "aps_per_entry,retained_percent,aab_percent,best_three_alevels_grade,"
               "best_three_alevels_aps")
PERF_ROW = "202425,A level,Total,100003,167,0.18,Above average,A,50.44,z,65.7,A,50.58"


def perf_csv(test, *rows):
    """Write a performance CSV to a temporary file and return its path."""
    directory = tempfile.TemporaryDirectory()
    test.addCleanup(directory.cleanup)
    path = Path(directory.name) / "perf.csv"
    path.write_text("\n".join((PERF_HEADER,) + rows) + "\n", encoding="utf-8")
    return path


class TestMeasure(unittest.TestCase):
    def test_missing_and_suppressed_values_become_none(self):
        for value in ("", "z", "c", "x"):
            with self.subTest(value=value):
                self.assertIsNone(measure(value))

    def test_numeric_values_become_floats(self):
        self.assertEqual(measure("50.44"), 50.44)
        self.assertEqual(measure("167"), 167.0)

    def test_grades_and_bandings_pass_through_as_strings(self):
        self.assertEqual(measure("A+"), "A+")
        self.assertEqual(measure("Above average"), "Above average")


class TestLoadResults(unittest.TestCase):
    def test_keeps_a_matching_row_with_all_nine_keys(self):
        loaded = load_results(perf_csv(self, PERF_ROW))
        self.assertEqual(loaded, {"100003": {
            "students": 167.0, "progress": 0.18, "progress_banding": "Above average",
            "grade": "A", "aps": 50.44, "retained_percent": None, "aab_percent": 65.7,
            "best3_grade": "A", "best3_aps": 50.58,
        }})

    def test_suppressed_column_is_none_while_the_rest_survive(self):
        loaded = load_results(perf_csv(self, PERF_ROW))
        self.assertIsNone(loaded["100003"]["retained_percent"])
        self.assertEqual(loaded["100003"]["aps"], 50.44)

    def test_drops_rows_that_differ_on_any_filter_value(self):
        for field, wrong in (("time_period", "202324"),
                             ("exam_cohort", "Applied general"),
                             ("disadvantage_status", "Disadvantaged")):
            with self.subTest(field=field):
                columns = PERF_HEADER.split(",")
                values = PERF_ROW.split(",")
                values[columns.index(field)] = wrong
                self.assertEqual(load_results(perf_csv(self, ",".join(values))), {})

if __name__ == "__main__":
    unittest.main()
