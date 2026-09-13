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

The spec's "Page" section says `sort.js` exports one function taking a key and a direction. Its "Testing" section also asks `check_sort.mjs` to cover the direction toggle on a repeated key and the reset to travel time ascending after a fresh search. Those two behaviours are only runnable under `node` if they live in `sort.js` too, so `sort.js` exports three things: `comparator`, `nextSort`, and `DEFAULT_SORT`. This is the smallest way to make the spec's own checks executable; it is not a design change, and the page keeps only the wiring.

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

Then run this check, which asserts the record count, the join count, and one known school's values against the published figures:

```bash
python3 -c "
import json
s = json.load(open('schools.json'))
by = {x['urn']: x for x in s}
joined = sum(1 for x in s if x['aps'] is not None or x['progress'] is not None or x['students'] is not None)
print(len(s), 'schools,', joined, 'with results')
assert len(s) == 4373, len(s)
assert joined == 2715, joined
city = by['100003']
assert city['aps'] == 50.44 and city['grade'] == 'A', city
assert city['progress'] == 0.18 and city['progress_banding'] == 'Above average', city
assert city['retained_percent'] is None, city
assert all(len(x) == 17 for x in s), 'every record must carry 17 keys'
print('ok')
"
```

Expected: `4373 schools, 2715 with results` followed by `ok`. The file grows from roughly 1.0 MB to roughly 1.5 MB.

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
- Produces, all from `sort.js`: `comparator(key, direction)` returning a comparison function for `Array.prototype.sort`, where `direction` is the string `'asc'` or `'desc'`; `nextSort(current, key)` taking and returning an object of the shape `{ key, direction }`; and `DEFAULT_SORT`, the constant `{ key: 'minutes', direction: 'asc' }`. Task 5 imports all three. `app.py` serves `sort.js` at `GET /sort.js` with content type `application/javascript`.

- [ ] **Step 1: Write the failing check**

Create `check_sort.mjs`. It runs the comparator against rows shaped like `/search` responses.

```js
import assert from 'node:assert/strict';
import { comparator, nextSort, DEFAULT_SORT } from './sort.js';

const rows = [
  { name: 'Beta', minutes: 30, progress: 0.18, aps: 50.44, best3_aps: 50.58 },
  { name: 'alpha', minutes: 10, progress: -0.42, aps: 30.1, best3_aps: 29.0 },
  { name: 'Gamma', minutes: 20, progress: null, aps: null, best3_aps: null },
];

const order = (key, direction) =>
  [...rows].sort(comparator(key, direction)).map((r) => r.name);

// Numbers compare numerically, in both directions.
assert.deepEqual(order('minutes', 'asc'), ['alpha', 'Gamma', 'Beta']);
assert.deepEqual(order('minutes', 'desc'), ['Beta', 'Gamma', 'alpha']);

// A negative progress score sorts below a positive one.
assert.deepEqual(order('progress', 'asc'), ['alpha', 'Beta', 'Gamma']);

// Text compares with localeCompare, so case does not split the order.
assert.deepEqual(order('name', 'asc'), ['alpha', 'Beta', 'Gamma']);

// The grade columns sort on their point scores, not their grade letters.
assert.deepEqual(order('aps', 'asc'), ['alpha', 'Beta', 'Gamma']);
assert.deepEqual(order('best3_aps', 'desc'), ['Beta', 'alpha', 'Gamma']);

// Null sorts last whichever direction is asked for.
assert.equal(order('aps', 'asc').at(-1), 'Gamma');
assert.equal(order('aps', 'desc').at(-1), 'Gamma');

// The same header toggles to descending; a different header starts ascending again.
assert.deepEqual(nextSort({ key: 'aps', direction: 'asc' }, 'aps'),
  { key: 'aps', direction: 'desc' });
assert.deepEqual(nextSort({ key: 'aps', direction: 'desc' }, 'aps'),
  { key: 'aps', direction: 'asc' });
assert.deepEqual(nextSort({ key: 'aps', direction: 'desc' }, 'name'),
  { key: 'name', direction: 'asc' });

// A fresh search resets to travel time ascending.
assert.deepEqual(DEFAULT_SORT, { key: 'minutes', direction: 'asc' });
assert.deepEqual(
  [...rows].sort(comparator(DEFAULT_SORT.key, DEFAULT_SORT.direction)).map((r) => r.minutes),
  [10, 20, 30]);

console.log('sort.js ok');
```

- [ ] **Step 2: Run the check to verify it fails**

Run: `node check_sort.mjs`
Expected: FAIL with `ERR_MODULE_NOT_FOUND`, naming `sort.js`.

- [ ] **Step 3: Write `sort.js`**

Create `sort.js`. The null handling is the part worth reading closely: null is pushed last by returning a fixed sign before the direction is applied, so it stays last when the direction reverses.

```js
export const DEFAULT_SORT = { key: 'minutes', direction: 'asc' };

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

export function nextSort(current, key) {
  const ascending = current.key !== key || current.direction === 'desc';
  return { key, direction: ascending ? 'asc' : 'desc' };
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
- Consumes: `comparator`, `nextSort`, and `DEFAULT_SORT` from `sort.js` (Task 4), and the widened `/search` response from Task 3.
- Produces: nothing later tasks depend on. This is the last task.

- [ ] **Step 1: Turn the inline script into a module and hold the rows**

At the top of the existing `<script>` block in `index.html`, change the opening tag to `<script type="module">` and add the import:

```js
import { comparator, nextSort, DEFAULT_SORT } from './sort.js';
```

Below the existing element lookups, add the two pieces of state the page now keeps:

```js
let rows = [];
let sort = { ...DEFAULT_SORT };
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

- [ ] **Step 3: Describe the columns in one table**

Replace the body of `render` with a column list, so each column's heading, its sort key, and its cell text stay in one place. Order matters: the six new columns sit after Minutes and before Website.

```js
const text = (value) => (value == null ? '' : String(value));
const pair = (main, extra) =>
  main == null ? '' : extra == null ? String(main) : `${main} (${extra})`;
const percent = (value) => (value == null ? '' : `${value}%`);

const COLUMNS = [
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
```

- [ ] **Step 4: Render the sortable header and the sorted rows**

Rewrite `render` so it takes no arguments, reads the module-level `rows` and `sort`, and redraws the whole table. Every heading holds a native `<button>`, so the control is reachable and operable by keyboard; the active heading carries `aria-sort` and shows the direction as a visible arrow.

```js
function render() {
  table.textContent = '';
  const header = table.insertRow();
  for (const column of COLUMNS) {
    const th = cell(header, '', 'th');
    th.scope = 'col';
    const active = sort.key === column.key;
    th.setAttribute('aria-sort', active ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none');
    const button = document.createElement('button');
    button.textContent = column.label + (active ? (sort.direction === 'asc' ? ' ▲' : ' ▼') : '');
    button.addEventListener('click', () => {
      sort = nextSort(sort, column.key);
      render();
    });
    th.appendChild(button);
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
    sort = { ...DEFAULT_SORT };
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
- A second search resets the order to travel time ascending.

- [ ] **Step 7: Run everything one last time**

Run: `uv run --with pyproj python -m unittest -v && node check_sort.mjs`
Expected: PASS for the Python suite, then `sort.js ok`.

- [ ] **Step 8: Commit**

```bash
git add index.html
git commit -m "Show A level results columns and sort the table by any column"
```
