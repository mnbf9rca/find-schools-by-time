# 16 to 18 Results Columns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show each school's 2024/25 A level results beside its travel time, and let the user sort the results table by any column.

**Architecture:** The existing build script gains a second input, the Department for Education performance CSV, and merges nine result fields into every record in the committed `schools.json`. The server change is one widened tuple plus a route that serves a new static file. The page gains six columns and a client-side sort, with the comparator and the header-toggle rule in their own ES module so they can be checked under `node` with no browser and no test framework.

**Tech Stack:** Python 3.11+ standard library, `pyproj` (build script only, via `uv run` inline script metadata), plain HTML with an inline ES module, one ES module file loaded by both the browser and `node`, GNU Make.

**Spec:** `docs/superpowers/specs/2026-09-13-results-columns-design.md` (iteration 2). It extends `docs/superpowers/specs/2026-09-13-schools-by-travel-time-design.md` (iteration 1), which stays as written.

## Global Constraints

- All files live at the repository root: `/Users/rob/git/find-schools-by-time`. This change adds exactly two committed files, `sort.js` and `check_sort.mjs`, and modifies `build_schools.py`, `app.py`, `index.html`, `Makefile`, `test_build.py`, and `test_app.py`. Do not add directories, packages, frameworks, or dependencies.
- `app.py` uses the Python standard library only. The build script's only dependency stays `pyproj`.
- Python tests are standard-library `unittest`, run with `uv run --with pyproj python -m unittest`. No network access in tests.
- The sort check is `node check_sort.mjs`, asserting with `node:assert`. No test framework, no browser, no npm install, no `package.json`.
- Source CSV for results: `data/a-level-and-other-16-to-18-results_2024-25/data/institution_performance_202225_API.csv`, UTF-8, no byte order mark. `data/` is gitignored; never commit it.
- The three filter values, exact strings: `time_period` is `202425`, `exam_cohort` is `A level`, `disadvantage_status` is `Total`.
- The nine `schools.json` keys, exact spelling and order: `students`, `progress`, `progress_banding`, `grade`, `aps`, `retained_percent`, `aab_percent`, `best3_grade`, `best3_aps`.
- Suppression codes to treat as missing: `z` (not applicable), `c` (confidential), `x` (unavailable), plus the empty string.
- Every school record carries all nine keys. A school with no matching performance row gets nine `None` values, so the record shape never varies.
- All cell text on the page is written with `textContent`, never `innerHTML`.
- The visible results heading is exactly `A level results, 2024/25`.
- Commit after every task.

### Two notes on reconciling the spec

The spec's "Page" section says `sort.js` exports one function taking a key and a direction. Its "Testing" section also asks `check_sort.mjs` to cover the direction toggle on a repeated key, the reset to travel time ascending after a fresh search, and the grade columns ordering by their point scores rather than their grade letters. None of those three is runnable under `node` unless the behaviour lives in `sort.js`, so `sort.js` holds the comparator, the current sort state with its toggle and reset, and the column list that maps each column to the key it sorts on. All of it is plain data and pure functions with no DOM, and `index.html` keeps only the wiring. This is the smallest way to make the spec's own checks executable, and it is not a design change.

The spec says `index.html` loads the comparator with a plain `<script src="sort.js">` tag. A file using `export` has to be loaded as a module, so the page's existing inline `<script>` becomes `<script type="module">` and imports from `./sort.js` directly. That replaces the separate tag rather than adding one. This is a mechanical consequence of using an ES module, not a design change.

---

### Task 1: `measure` and `load_results` in `build_schools.py`

Two pure functions that read the performance CSV. Nothing else changes yet: `main` is untouched and `schools.json` is not rebuilt in this task.

**Files:**
- Modify: `build_schools.py`
- Test: `test_build.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `measure(value) -> float | str | None`; `load_results(path) -> dict[str, dict]`, mapping a URN string to a dictionary with exactly the nine keys named in the Global Constraints; `RESULT_COLUMNS`, a module-level dictionary mapping each of those nine keys to its source CSV column name. Task 2 uses `load_results` and `RESULT_COLUMNS`.

- [ ] **Step 1: Write the failing tests**

Add to `test_build.py`. Change the existing import line to `from build_schools import keep, load_results, measure, to_latlng, website` and add `import tempfile` and `from pathlib import Path` at the top.

```python
PERF_HEADER = ("time_period,exam_cohort,disadvantage_status,school_urn,"
               "aps_per_entry_student_count,value_added,progress_banding,aps_per_entry_grade,"
               "aps_per_entry,retained_percent,aab_percent,best_three_alevels_grade,"
               "best_three_alevels_aps")
PERF_ROW = "202425,A level,Total,100003,167,0.18,Above average,A,50.44,z,65.7,A,50.58"


def perf_csv(*rows):
    """Write a performance CSV to a temporary file and return its path."""
    path = Path(tempfile.mkdtemp()) / "perf.csv"
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
        loaded = load_results(perf_csv(PERF_ROW))
        self.assertEqual(loaded, {"100003": {
            "students": 167.0, "progress": 0.18, "progress_banding": "Above average",
            "grade": "A", "aps": 50.44, "retained_percent": None, "aab_percent": 65.7,
            "best3_grade": "A", "best3_aps": 50.58,
        }})

    def test_suppressed_column_is_none_while_the_rest_survive(self):
        loaded = load_results(perf_csv(PERF_ROW))
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
                self.assertEqual(load_results(perf_csv(",".join(values))), {})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --with pyproj python -m unittest test_build -v`
Expected: FAIL with `ImportError: cannot import name 'load_results' from 'build_schools'`.

- [ ] **Step 3: Write the implementation**

Add to `build_schools.py`, above `main`. The dictionary is the join contract: its keys are the nine `schools.json` names and its values are the source CSV column names.

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --with pyproj python -m unittest test_build -v`
Expected: PASS, all cases.

- [ ] **Step 5: Commit**

```bash
git add build_schools.py test_build.py
git commit -m "Read A level measures from the performance CSV"
```

---

### Task 2: Merge results into every school record, and rebuild `schools.json`

**Files:**
- Modify: `build_schools.py` (the `main` function and the `__main__` block)
- Modify: `Makefile`
- Modify: `schools.json` (regenerated, committed)
- Test: `test_build.py`

**Interfaces:**
- Consumes: `load_results(path)` and `RESULT_COLUMNS` from Task 1.
- Produces: `main(path, results_path)`, and a `schools.json` in which every object carries the iteration 1 keys (`urn`, `name`, `type`, `postcode`, `website`, `sixth_form`, `lat`, `lng`) plus the nine result keys. Task 3 reads that file through `app.py`.

- [ ] **Step 1: Write the failing tests**

Add to `test_build.py`. These call `main` with a temporary establishments CSV and the temporary performance CSV from Task 1's helper, capturing standard output. Reuse `perf_csv`, `PERF_HEADER`, and `PERF_ROW` from Task 1; add `import io`, `import json`, and `from contextlib import redirect_stdout` at the top, and import `main` alongside the other names.

```python
GIAS_HEADER = ("URN,EstablishmentName,TypeOfEstablishment (name),Postcode,SchoolWebsite,"
               "OfficialSixthForm (name),EstablishmentStatus (name),GOR (code),"
               "Easting,Northing,StatutoryLowAge,StatutoryHighAge")
GIAS_ROW = ("{urn},School {urn},Academy,N1 1AA,,Has a sixth form,Open,H,"
            "530000,180000,11,18")


def gias_csv(*urns):
    path = Path(tempfile.mkdtemp()) / "gias.csv"
    rows = [GIAS_ROW.format(urn=urn) for urn in urns]
    path.write_text("\n".join([GIAS_HEADER] + rows) + "\n", encoding="cp1252")
    return path


def build(urns, *perf_rows):
    out = io.StringIO()
    with redirect_stdout(out):
        main(gias_csv(*urns), perf_csv(*perf_rows))
    return {s["urn"]: s for s in json.loads(out.getvalue())}


class TestMerge(unittest.TestCase):
    def test_school_with_a_performance_row_carries_the_nine_values(self):
        school = build(["100003"], PERF_ROW)["100003"]
        self.assertEqual(school["aps"], 50.44)
        self.assertEqual(school["grade"], "A")
        self.assertEqual(school["progress"], 0.18)
        self.assertEqual(school["progress_banding"], "Above average")
        self.assertEqual(school["students"], 167.0)
        self.assertEqual(school["aab_percent"], 65.7)
        self.assertEqual(school["best3_grade"], "A")
        self.assertEqual(school["best3_aps"], 50.58)
        self.assertIsNone(school["retained_percent"])
        self.assertEqual(school["name"], "School 100003")

    def test_school_without_a_performance_row_carries_nine_nones(self):
        school = build(["999999"], PERF_ROW)["999999"]
        for key in ("students", "progress", "progress_banding", "grade", "aps",
                    "retained_percent", "aab_percent", "best3_grade", "best3_aps"):
            with self.subTest(key=key):
                self.assertIsNone(school[key])

    def test_every_record_has_the_same_keys(self):
        schools = build(["100003", "999999"], PERF_ROW)
        self.assertEqual(set(schools["100003"]), set(schools["999999"]))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --with pyproj python -m unittest test_build -v`
Expected: FAIL. `main` takes one argument, so the new cases raise `TypeError: main() takes 1 positional argument but 2 were given`.

- [ ] **Step 3: Write the implementation**

In `build_schools.py`, give `main` a second parameter, load the results once before the loop, and merge with the dictionary union operator. The union builds a new dictionary every time, so the shared `EMPTY` default is never stored in a record and cannot be mutated through one.

```python
def main(path, results_path):
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
                "lat": lat,
                "lng": lng,
            } | results.get(row["URN"], empty))
    json.dump(schools, sys.stdout)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
```

Update the module docstring's usage line to `uv run build_schools.py data/extract/edubasealldata20260913.csv data/a-level-and-other-16-to-18-results_2024-25/data/institution_performance_202225_API.csv > schools.json`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --with pyproj python -m unittest test_build -v`
Expected: PASS, all cases.

- [ ] **Step 5: Add the second wildcard to the `Makefile`**

Replace the `CSV` line and the `build` recipe. Keep the existing temporary-file and `trap` behaviour exactly as it is.

```make
CSV = $(lastword $(sort $(wildcard data/extract/edubasealldata*.csv)))
RESULTS_CSV = $(lastword $(sort $(wildcard data/a-level-and-other-16-to-18-results_2024-25/data/institution_performance_*_API.csv)))

build:
	@trap 'rm -f schools.json.tmp' EXIT; uv run build_schools.py $(CSV) $(RESULTS_CSV) > schools.json.tmp && mv schools.json.tmp schools.json
```

- [ ] **Step 6: Rebuild `schools.json` and check the real join**

Run: `make build`

Then run this check, which asserts the record count, the number of records carrying at least one measure, and one known school's values against the published figures:

```bash
python3 -c "
import json
RESULTS = ('students', 'progress', 'progress_banding', 'grade', 'aps',
           'retained_percent', 'aab_percent', 'best3_grade', 'best3_aps')
s = json.load(open('schools.json'))
by = {x['urn']: x for x in s}
populated = sum(1 for x in s if any(x[k] is not None for k in RESULTS))
print(len(s), 'schools,', populated, 'with at least one measure')
assert len(s) == 4373, len(s)
assert populated == 2578, populated
city = by['100003']
assert city['aps'] == 50.44 and city['grade'] == 'A', city
assert city['progress'] == 0.18 and city['progress_banding'] == 'Above average', city
assert city['retained_percent'] is None, city
assert all(len(x) == 17 for x in s), 'every record must carry 17 keys'
print('ok')
"
```

Expected: `4373 schools, 2578 with at least one measure` followed by `ok`. The file grows from roughly 1.0 MB to roughly 1.5 MB.

The 2,578 figure is not the same as the 2,715 URNs the spec's Build section mentions. 2,715 schools have a matching 2024/25 A level row, but 137 of those rows carry a suppression code in all nine columns, so they come out of the merge indistinguishable from a school with no row at all. `schools.json` cannot tell the two apart, so the check counts populated records. To confirm the 2,715 figure as well, count matching URNs in the source CSV instead:

```bash
python3 -c "
import csv, json
urns = {x['urn'] for x in json.load(open('schools.json'))}
path = 'data/a-level-and-other-16-to-18-results_2024-25/data/institution_performance_202225_API.csv'
with open(path, newline='') as f:
    matching = {r['school_urn'] for r in csv.DictReader(f)
                if r['time_period'] == '202425' and r['exam_cohort'] == 'A level'
                and r['disadvantage_status'] == 'Total'}
joined = len(urns & matching)
print(joined, 'matching URNs')
assert joined == 2715, joined
"
```

Expected: `2715 matching URNs`.

- [ ] **Step 7: Commit**

```bash
git add build_schools.py test_build.py Makefile schools.json
git commit -m "Merge A level results into schools.json"
```

---

### Task 3: Widen `RESULT_KEYS` in `app.py`

The whitelist that keeps `lat` and `lng` out of the search response has to name every field the page needs. Widening it breaks `test_app.py` in two places, so both are fixed in this task.

**Files:**
- Modify: `app.py:91`
- Test: `test_app.py`

**Interfaces:**
- Consumes: the rebuilt `schools.json` from Task 2.
- Produces: a `/search` response where each row carries `urn`, `name`, `type`, `postcode`, `website`, `sixth_form`, `minutes`, and the nine result keys. Task 5 renders those rows.

- [ ] **Step 1: Update the `school()` helper and write the failing tests**

In `test_app.py`, replace the `school()` helper so it supplies the nine new keys, defaulting to populated values, and accepts overrides. Existing cases then keep working unchanged.

```python
RESULTS = {"students": 167.0, "progress": 0.18, "progress_banding": "Above average",
           "grade": "A", "aps": 50.44, "retained_percent": 90.1, "aab_percent": 65.7,
           "best3_grade": "A", "best3_aps": 50.58}


def school(urn, lat, lng, **results):
    return {"urn": urn, "name": f"School {urn}", "type": "Academy", "postcode": "N1 1AA",
            "website": "", "sixth_form": "Has a sixth form", "lat": lat, "lng": lng
            } | RESULTS | results
```

In `TestResults.test_joins_sorts_and_rounds_up`, replace the response-key assertion with the full widened set:

```python
        self.assertEqual(set(rows[0]), {
            "urn", "name", "type", "postcode", "website", "sixth_form", "minutes",
            "students", "progress", "progress_banding", "grade", "aps",
            "retained_percent", "aab_percent", "best3_grade", "best3_aps"})
```

Add one case to `TestResults`, covering a populated school and an entirely unpopulated one in the same response:

```python
    def test_carries_results_and_missing_results_through_the_join(self):
        schools = [school("1", 51.51, -0.12),
                   school("2", 51.52, -0.13, **dict.fromkeys(RESULTS, None))]
        response = {"results": [{"locations": [
            {"id": "1", "properties": [{"travel_time": 600}]},
            {"id": "2", "properties": [{"travel_time": 1200}]},
        ]}]}
        populated, missing = results(schools, response)
        self.assertEqual(populated["aps"], 50.44)
        self.assertEqual(populated["grade"], "A")
        self.assertEqual(populated["progress_banding"], "Above average")
        self.assertEqual(populated["best3_aps"], 50.58)
        self.assertTrue(all(missing[k] is None for k in RESULTS))
        self.assertEqual(missing["name"], "School 2")
        self.assertEqual(set(populated), set(missing))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --with pyproj python -m unittest test_app -v`
Expected: FAIL. The widened-key assertions fail because `RESULT_KEYS` still names the six iteration 1 fields.

- [ ] **Step 3: Widen the tuple**

Replace line 91 of `app.py`:

```python
RESULT_KEYS = ("urn", "name", "type", "postcode", "website", "sixth_form",
               "students", "progress", "progress_banding", "grade", "aps",
               "retained_percent", "aab_percent", "best3_grade", "best3_aps")
```

Nothing else in `app.py` changes in this task. There is no new join, no new request handling, and no new validation.

- [ ] **Step 4: Run the full Python suite to verify it passes**

Run: `uv run --with pyproj python -m unittest -v`
Expected: PASS, both `test_build` and `test_app`.

- [ ] **Step 5: Commit**

```bash
git add app.py test_app.py
git commit -m "Return the A level result fields from /search"
```

---

### Task 4: `sort.js`, its runnable check, and the route that serves it

**Files:**
- Create: `sort.js`
- Create: `check_sort.mjs`
- Modify: `app.py` (the `do_GET` method)
- Test: `check_sort.mjs` and `test_app.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces, all from `sort.js`: `COLUMNS`, the array of `{ label, key, cell }` column descriptions in display order, where `cell(row)` returns the cell's text as a string and the Website column additionally carries `link: true`; `comparator(key, direction)` returning a comparison function for `Array.prototype.sort`, where `direction` is the string `'asc'` or `'desc'`; `DEFAULT_SORT`, the constant `{ key: 'minutes', direction: 'asc' }`; the live binding `sort`, the current `{ key, direction }`; `toggle(key)`, which advances `sort` and returns it; and `reset()`, which restores `sort` to `DEFAULT_SORT` and returns it. Task 5 imports `COLUMNS`, `comparator`, `sort`, `toggle`, and `reset`. `app.py` serves `sort.js` at `GET /sort.js` with content type `application/javascript`.

- [ ] **Step 1: Write the failing check**

Create `check_sort.mjs`. It runs the comparator against rows shaped like `/search` responses.

Every fixture value here is chosen so that a wrong implementation fails. The minutes are 2, 10, 20, and 100, so a comparator that compares numbers as text puts 100 before 2 and the assertion fails. The progress scores are -1.5, -0.42, and 0.18, which text ordering also gets wrong. The grades are `E`, `A`, and `A+` against point scores 9.5, 45.0, and 50.44, so grade text order and point-score order disagree on every pair, and a column wired to sort by grade text fails. The check reads the sort key from `COLUMNS` rather than naming `aps` itself, so rewiring the Average result column to any other key is caught here.

```js
import assert from 'node:assert/strict';
import { COLUMNS, comparator, DEFAULT_SORT, reset, sort, toggle } from './sort.js';

const rows = [
  { name: 'Beta', minutes: 10, progress: -0.42, grade: 'A', aps: 45.0, best3_grade: 'A', best3_aps: 46.0 },
  { name: 'alpha', minutes: 2, progress: 0.18, grade: 'A+', aps: 50.44, best3_grade: 'A+', best3_aps: 50.58 },
  { name: 'Gamma', minutes: 20, progress: -1.5, grade: 'E', aps: 9.5, best3_grade: 'E', best3_aps: 9.0 },
  { name: 'Delta', minutes: 100, progress: null, grade: null, aps: null, best3_grade: null, best3_aps: null },
];

const order = (key, direction) =>
  [...rows].sort(comparator(key, direction)).map((r) => r.name);
const keyOf = (label) => COLUMNS.find((c) => c.label === label).key;

// Numbers compare numerically: text ordering would put 100 between 10 and 2.
assert.deepEqual(order('minutes', 'asc'), ['alpha', 'Beta', 'Gamma', 'Delta']);
assert.deepEqual(order('minutes', 'desc'), ['Delta', 'Gamma', 'Beta', 'alpha']);

// Negative progress scores sort below positive ones, and below each other correctly:
// text ordering would put -0.42 before -1.5.
assert.deepEqual(order('progress', 'asc'), ['Gamma', 'Beta', 'alpha', 'Delta']);
assert.deepEqual(order('progress', 'desc'), ['alpha', 'Beta', 'Gamma', 'Delta']);

// Text compares with localeCompare, so case does not split the order.
assert.deepEqual(order('name', 'asc'), ['alpha', 'Beta', 'Delta', 'Gamma']);

// The Average result and Best 3 A levels columns sort on their point scores. Sorting by
// grade text would give Beta, alpha, Gamma, the reverse of the first pair below.
assert.deepEqual(order(keyOf('Average result'), 'asc'), ['Gamma', 'Beta', 'alpha', 'Delta']);
assert.deepEqual(order(keyOf('Best 3 A levels'), 'asc'), ['Gamma', 'Beta', 'alpha', 'Delta']);
assert.deepEqual(order(keyOf('Average result'), 'desc'), ['alpha', 'Beta', 'Gamma', 'Delta']);

// Null sorts last whichever direction is asked for.
assert.equal(order('aps', 'asc').at(-1), 'Delta');
assert.equal(order('aps', 'desc').at(-1), 'Delta');

// The same header toggles to descending; a different header starts ascending again.
assert.deepEqual(reset(), { key: 'minutes', direction: 'asc' });
assert.deepEqual(toggle('aps'), { key: 'aps', direction: 'asc' });
assert.deepEqual(toggle('aps'), { key: 'aps', direction: 'desc' });
assert.deepEqual(toggle('name'), { key: 'name', direction: 'asc' });
assert.deepEqual(sort, { key: 'name', direction: 'asc' });

// A fresh search resets to travel time ascending, from wherever the user left the sort.
toggle('aps');
toggle('aps');
assert.notDeepEqual(sort, DEFAULT_SORT);
assert.deepEqual(reset(), DEFAULT_SORT);
assert.deepEqual(sort, { key: 'minutes', direction: 'asc' });
assert.deepEqual(
  [...rows].sort(comparator(sort.key, sort.direction)).map((r) => r.minutes),
  [2, 10, 20, 100]);

console.log('sort.js ok');
```

- [ ] **Step 2: Run the check to verify it fails**

Run: `node check_sort.mjs`
Expected: FAIL with `ERR_MODULE_NOT_FOUND`, naming `sort.js`.

- [ ] **Step 3: Write `sort.js`**

Create `sort.js`. Three parts, in this order: the column list, the comparator, and the sort state.

The column list lives here rather than in `index.html` so the check above can exercise the mapping from a column to the key it sorts on. Each `cell` function returns a string and touches no DOM, so the module still runs under `node` with no browser. `index.html` builds the actual elements from this list.

The null handling in the comparator is the part worth reading closely: null is pushed last by returning a fixed sign before the direction is applied, so it stays last when the direction reverses.

The sort state is an exported `let`. Reassigning it inside the module updates the live binding that `index.html` and the check both read, so there is only ever one current sort and no copy to keep in step.

```js
const text = (value) => (value == null ? '' : String(value));
const pair = (main, extra) =>
  main == null ? '' : extra == null ? String(main) : `${main} (${extra})`;
const percent = (value) => (value == null ? '' : `${value}%`);

export const COLUMNS = [
  { label: 'Name', key: 'name', cell: (r) => text(r.name) },
  { label: 'Type', key: 'type', cell: (r) => text(r.type) },
  { label: 'Postcode', key: 'postcode', cell: (r) => text(r.postcode) },
  { label: 'Sixth form', key: 'sixth_form', cell: (r) => text(r.sixth_form) },
  { label: 'Minutes', key: 'minutes', cell: (r) => text(r.minutes) },
  { label: 'Students', key: 'students', cell: (r) => text(r.students) },
  { label: 'Progress', key: 'progress', cell: (r) => pair(r.progress, r.progress_banding) },
  { label: 'Average result', key: 'aps', cell: (r) => pair(r.grade, r.aps) },
  { label: 'Completed programme', key: 'retained_percent', cell: (r) => percent(r.retained_percent) },
  { label: 'AAB or higher incl. 2 facilitating subjects', key: 'aab_percent', cell: (r) => percent(r.aab_percent) },
  { label: 'Best 3 A levels', key: 'best3_aps', cell: (r) => pair(r.best3_grade, r.best3_aps) },
  { label: 'Website', key: 'website', cell: () => '', link: true },
];

export function comparator(key, direction) {
  const sign = direction === 'desc' ? -1 : 1;
  return (a, b) => {
    const x = a[key];
    const y = b[key];
    if (x == null && y == null) return 0;
    if (x == null) return 1;
    if (y == null) return -1;
    if (typeof x === 'number' && typeof y === 'number') return sign * (x - y);
    return sign * String(x).localeCompare(String(y));
  };
}

export const DEFAULT_SORT = { key: 'minutes', direction: 'asc' };

export let sort = { ...DEFAULT_SORT };

export function toggle(key) {
  const ascending = sort.key !== key || sort.direction === 'desc';
  sort = { key, direction: ascending ? 'asc' : 'desc' };
  return sort;
}

export function reset() {
  sort = { ...DEFAULT_SORT };
  return sort;
}
```

- [ ] **Step 4: Run the check to verify it passes**

Run: `node check_sort.mjs`
Expected: `sort.js ok`, exit status 0.

- [ ] **Step 5: Write the failing test for the new route**

Add to `test_app.py`. `Handler` and `Mock` are already imported; nothing new is needed.

```python
class TestStaticFiles(unittest.TestCase):
    def handler(self, path):
        handler = Handler.__new__(Handler)
        handler.path = path
        handler._send = Mock()
        return handler

    def test_serves_the_page_and_the_sort_module(self):
        for path, content_type in (("/", "text/html; charset=utf-8"),
                                   ("/sort.js", "application/javascript")):
            with self.subTest(path=path):
                handler = self.handler(path)
                handler.do_GET()
                status, body, sent_type = handler._send.call_args.args
                self.assertEqual(status, 200)
                self.assertEqual(sent_type, content_type)
                self.assertTrue(body)

    def test_unknown_paths_return_404(self):
        handler = self.handler("/secrets")
        handler.do_GET()
        self.assertEqual(handler._send.call_args.args[0], 404)
```

- [ ] **Step 6: Run the test to verify it fails**

Run: `uv run --with pyproj python -m unittest test_app.TestStaticFiles -v`
Expected: FAIL on the `/sort.js` case, which currently returns 404.

- [ ] **Step 7: Add the route**

In `app.py`, add a module-level mapping beside the other constants and rewrite `do_GET` to use it. The mapping is a whitelist, so no path outside it can be read from disk.

```python
STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/sort.js": ("sort.js", "application/javascript")}
```

```python
    def do_GET(self):
        page = STATIC.get(self.path)
        if not page:
            return self._send(404, b"not found", "text/plain")
        name, content_type = page
        self._send(200, (HERE / name).read_bytes(), content_type)
```

- [ ] **Step 8: Run both suites to verify they pass**

Run: `uv run --with pyproj python -m unittest -v && node check_sort.mjs`
Expected: PASS for the Python suite, then `sort.js ok`.

- [ ] **Step 9: Commit**

```bash
git add sort.js check_sort.mjs app.py test_app.py
git commit -m "Add the sort comparator and serve it from the server"
```

---

### Task 5: Results columns and sortable headers in `index.html`

**Files:**
- Modify: `index.html`

**Interfaces:**
- Consumes: `COLUMNS`, `comparator`, `sort`, `toggle`, and `reset` from `sort.js` (Task 4), and the widened `/search` response from Task 3.
- Produces: nothing later tasks depend on. This is the last task.

- [ ] **Step 1: Turn the inline script into a module and hold the rows**

At the top of the existing `<script>` block in `index.html`, change the opening tag to `<script type="module">` and add the import:

```js
import { COLUMNS, comparator, sort, toggle, reset } from './sort.js';
```

Below the existing element lookups, add the one piece of state the page keeps for itself. The current sort lives in `sort.js` and is read through the imported `sort` binding, so the page does not hold a second copy:

```js
let rows = [];
```

- [ ] **Step 2: Add the results heading and the header-button style**

In the `<style>` block, add one rule so the header buttons read as headers rather than form controls:

```css
  th button { font: inherit; font-weight: bold; background: none; border: 0; padding: 0; cursor: pointer; }
```

Between `<p id="count"></p>` and `<table id="results"></table>`, add the heading, so the year and the cohort the results describe are on screen rather than implied:

```html
<h2>A level results, 2024/25</h2>
```

- [ ] **Step 3: Read the column list**

The column list now lives in `sort.js` (Task 4) and is imported, so nothing is declared here. Read it once before writing `render` in the next step: its order is the column order on screen, with the six new columns after Minutes and before Website, and each entry's `key` is the field that column sorts on.

- [ ] **Step 4: Render the sortable header and the sorted rows**

Rewrite `render` so it takes no arguments, reads the module-level `rows` and the imported `sort`, and redraws the whole table. Every heading holds a native `<button>`, so the control is reachable and operable by keyboard; the active heading carries `aria-sort` and shows the direction as a visible arrow.

Redrawing destroys the button that was activated, which takes keyboard focus back to the top of the document and means a second Enter or Space cannot toggle the same column without navigating to it again. So after redrawing, move focus to the replacement button in the same position. The column's index in `COLUMNS` is also its cell index in the header row, which is why the loop takes both.

```js
function render(focusIndex) {
  table.textContent = '';
  const header = table.insertRow();
  for (const [index, column] of COLUMNS.entries()) {
    const th = cell(header, '', 'th');
    th.scope = 'col';
    const active = sort.key === column.key;
    th.setAttribute('aria-sort', active ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none');
    const button = document.createElement('button');
    button.textContent = column.label + (active ? (sort.direction === 'asc' ? ' ▲' : ' ▼') : '');
    button.addEventListener('click', () => {
      toggle(column.key);
      render(index);
    });
    th.appendChild(button);
    if (index === focusIndex) button.focus();
  }
  for (const r of [...rows].sort(comparator(sort.key, sort.direction))) {
    const tr = table.insertRow();
    for (const column of COLUMNS) {
      const td = cell(tr, column.cell(r));
      if (column.link && r.website) {
        const a = document.createElement('a');
        a.href = r.website;
        a.textContent = 'Website';
        td.appendChild(a);
      }
    }
  }
}
```

A fresh search calls `render()` with no argument, so nothing is focused and the page does not steal focus from the form.

- [ ] **Step 5: Reset the sort on a fresh search**

In the submit handler, the existing local `const rows = await search.json();` would shadow the new module-level `rows`, so rename that local to `found`. The `FormData` variable is already called `data` and keeps its name. Replace the four lines from `const rows = await search.json();` to `if (rows.length) render(rows);` with:

```js
    const found = await search.json();
    if (!search.ok) {
      errorLine.textContent = found.error || 'Search failed';
      return;
    }
    countLine.textContent = found.length + ' schools within ' + data.get('minutes') + ' minutes';
    rows = found;
    reset();
    if (rows.length) render();
```

- [ ] **Step 6: Run the app and check the page by hand**

Run: `make run`, then open `http://127.0.0.1:8000` and search a postcode you know, such as `SW1A 1AA`, with 60 minutes by public transport.

Confirm all of the following:
- The heading `A level results, 2024/25` appears above the table.
- The table shows twelve columns, with Students, Progress, Average result, Completed programme, AAB or higher, and Best 3 A levels between Minutes and Website.
- Progress reads like `0.18 (Above average)` and Average result like `A (50.44)`.
- Schools with no results show empty cells in those six columns and stay in the table.
- Clicking a heading sorts ascending and shows an up arrow; clicking it again reverses to a down arrow; clicking a different heading starts ascending again.
- Sorting on Average result or Best 3 A levels orders by the point score in brackets, not by the grade letter.
- Schools with empty results cells sink to the bottom whichever direction a results column is sorted.
- Tabbing to a heading and pressing Enter or Space sorts it.
- Pressing Enter or Space a second and third time on that same heading, without touching the mouse or pressing Tab in between, keeps toggling the direction. Focus must stay on the heading you activated, and the arrow beside its label must flip each time.
- After a heading has been activated by keyboard, pressing Tab moves to the next heading rather than back to the top of the page.
- Running a second search leaves focus on the form, not on a table heading.
- A second search resets the order to travel time ascending.

- [ ] **Step 7: Run everything one last time**

Run: `uv run --with pyproj python -m unittest -v && node check_sort.mjs`
Expected: PASS for the Python suite, then `sort.js ok`.

- [ ] **Step 8: Commit**

```bash
git add index.html
git commit -m "Show A level results columns and sort the table by any column"
```
