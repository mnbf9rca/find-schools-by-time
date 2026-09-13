# 16 to 18 results columns: iteration 2 design

Date: September 13, 2026

## Goal

Show each school's 16 to 18 exam results next to its travel time, and let the user sort the results table by any column. The question this answers is "of the sixth forms within an hour of home, which ones get the best results?"

This extends the iteration 1 design in `2026-09-13-schools-by-travel-time-design.md`, which stays as written.

## Scope

In scope: six result measures from the A level cohort, joined at build time; nine new columns in the results table; click-to-sort on every column.

Out of scope: vocational cohorts (Applied general, Tech level), disadvantage breakdowns, confidence intervals, national or local authority comparisons, filters on any results column, and charts.

The "open only" filter the user asked about needs no work. The iteration 1 build already drops every row whose `EstablishmentStatus (name)` is not `Open`, so `schools.json` contains open establishments only.

## Source columns

From `data/a-level-and-other-16-to-18-results_2024-25/data/institution_performance_202225_API.csv`, filtered to `time_period` 202425, `exam_cohort` "A level", and `disadvantage_status` "Total", which leaves 2,792 rows keyed by `school_urn`.

| Column on the compare service | Source column | `schools.json` key | Populated |
|---|---|---|---|
| Number of students with an A level exam entry | `aps_per_entry_student_count` | `students` | 2,644 |
| Progress score | `value_added` | `progress` | 2,553 |
| Progress description | `progress_banding` | `progress_banding` | 2,553 |
| Average result (grade) | `aps_per_entry_grade` | `grade` | 2,536 |
| Average result (point score) | `aps_per_entry` | `aps` | 2,536 |
| Students completing their main study programme | `retained_percent` | `retained_percent` | 1,988 |
| Achieving AAB or higher including at least 2 facilitating subjects | `aab_percent` | `aab_percent` | 2,437 |
| Best 3 A levels (grade) | `best_three_alevels_grade` | `best3_grade` | 2,437 |
| Best 3 A levels (point score) | `best_three_alevels_aps` | `best3_aps` | 2,437 |

Every requested measure has a column. None is missing.

One choice is worth recording. The student count is ambiguous: the data guidance offers `aps_per_entry_student_count` ("Number of students in APS measure", 2,644 rows) and `best_three_alevels_student_count` ("Number of students entered for at least one A level or applied A level", 2,569 rows, identical in every row to `aab_student_count`). This design takes `aps_per_entry_student_count`, because it is the count that belongs to the average-result measure the table leads with. Switching to the narrower cohort is a one-word change if the published figures turn out to disagree.

## Build

`build_schools.py` takes a second argument, the performance CSV, and is run as `uv run build_schools.py <establishments.csv> <performance.csv> > schools.json`.

Two new functions, both directly testable:

- `measure(value)` returns `None` for an empty string and for the suppression codes `z` (not applicable), `c` (confidential), and `x` (unavailable), a `float` for a numeric value, and the string itself otherwise. Grades such as `A+` and bandings such as `Above average` pass through as strings.
- `load_results(path)` reads the performance CSV, keeps rows matching the three filter values above, and returns a dictionary from `school_urn` to a dictionary of the nine keys, each passed through `measure`.

`main` looks up each kept school by URN and merges the nine keys in. A school with no matching row gets all nine keys set to `None`, so every record has the same shape. Roughly 2,715 of the 4,373 schools will carry results; the rest are mostly special schools, pupil referral units, and alternative provision, which the publication excludes by design.

`schools.json` grows from about 1.0 MB to about 1.5 MB and stays committed.

The `build` target in the `Makefile` gains a second wildcard for the performance CSV and passes both paths.

## Server

One line changes in `app.py`: the nine new keys are added to `RESULT_KEYS`, the tuple that decides which school fields are copied into the search response. No join, no new request handling, no new validation. The whitelist exists so that `lat` and `lng` do not leak into the response, and it has to name any field the page needs.

## Page

`index.html` gains nine values across six new columns, placed after Minutes and before Website:

| Column | Cell contents | Sorts on |
|---|---|---|
| Students | `students` | `students` |
| Progress | `progress` with `progress_banding` in brackets, for example `0.18 (Above average)` | `progress` |
| Average result | `grade` with `aps` in brackets, for example `A (50.44)` | `aps` |
| Completed programme | `retained_percent` with a per cent sign | `retained_percent` |
| AAB or higher | `aab_percent` with a per cent sign | `aab_percent` |
| Best 3 A levels | `best3_grade` with `best3_aps` in brackets | `best3_aps` |

A cell whose underlying value is `None` renders as an empty string.

Sorting is plain JavaScript, no library. The rows returned by `/search` are held in a variable. Each header cell carries the key it sorts on. Clicking a header sorts ascending; clicking the same header again reverses to descending; clicking a different header starts ascending again. The table is re-rendered from the sorted array. Numbers compare numerically, strings compare with `localeCompare`, and `null` always sorts last regardless of direction. The default order on a fresh search stays travel time ascending, as in iteration 1.

Schools with no results data still appear in the table, with empty results cells, and sink to the bottom whenever a results column is the sort key.

All cell text is still written with `textContent`.

## Testing

`test_build.py` gains cases for the two new functions and the merge. No browser tests; the sorting is short enough to check by hand.

- `measure` returns `None` for `""`, `z`, `c`, and `x`, a float for `"50.44"`, and the string for `"A+"` and `"Above average"`.
- `load_results` keeps a row matching all three filter values and drops rows that differ on `time_period`, on `exam_cohort`, or on `disadvantage_status`.
- A school whose URN appears in the performance data gets the nine values; a school whose URN does not gets nine `None` values.
- A school whose row carries a suppression code in one column gets `None` for that column and real values for the rest.
