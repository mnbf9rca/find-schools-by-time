# 16 to 18 results data: source, measures, coverage

## Replacement service

Compare school and college performance (`compare-school-performance.service.gov.uk`) is closing, with a new service due autumn 2026. The statistics themselves already live on Explore education statistics (EES), publication [A level and other 16 to 18 results](https://explore-education-statistics.service.gov.uk/find-statistics/a-level-and-other-16-to-18-results). Latest release: academic year 2024/25, published 23 April 2026, last updated 24 July 2026. Licence: Open Government Licence v3.

## Recommended file

Use the data set **Schools and colleges - performance** (`institution_performance_202225_API.csv`), 56 MB uncompressed, 201,024 rows, covering 2021/22 to 2024/25 at School geographic level. It carries `school_urn`, which joins directly to the URN key in `schools.json`.

Download without the 749 MB release ZIP:

`https://api.education.gov.uk/statistics/v1/data-sets/019c2960-81e3-70c2-8d65-72c3718ae4fd/csv`

That returns 2.7 MB gzipped and is byte-identical to the file in the release ZIP. Filter to `time_period=202425`, `disadvantage_status=Total`, and the `exam_cohort` you want. The six cohorts are Academic, A level, Applied general, Tech level, Technical certificate, and E/M measures.

## Measures to sort by

Three columns cover the sixth-form choice, each read at cohort `A level` for A level results and `Applied general` or `Tech level` for vocational routes:

- `aps_per_entry_grade` — average result per entry as a grade, for example `A` or `B+`. Present for 2,536 institutions.
- `aps_per_entry` — the same measure in points, out of a 60-point A level scale. Sort on this, display the grade.
- `value_added` — progress against students' key stage 4 starting point, with `value_added_lower_ci` and `value_added_upper_ci` for the confidence interval and `progress_banding` for the published label such as `Above average`. Present for 2,553 institutions.

Two useful extras: `aab_percent` (share achieving AAB or better in at least two facilitating subjects, 2,437 institutions) and `retained_percent` (2-year programme retention, 1,988 institutions, the thinnest of the set).

Suppression codes appear in place of numbers: `z` means not applicable, `c` means suppressed as confidential, `x` means unavailable. Treat all three as missing and sort them last.

## Coverage against schools.json

2,715 of the 4,373 establishments in `schools.json` appear in the 2024/25 data, and 77 institutions in the data are absent from `schools.json`. Coverage is near-complete for mainstream types: academy converters 1,094 of 1,136, further education 199 of 204, community schools 113 of 114, university technical colleges 44 of 44.

Independent schools are included and reported on the same measures: 556 of 648 appear, 491 with a points score and 495 with a value added score.

Nothing is reported for special schools, pupil referral units, alternative provision, or special post-16 institutions. The data guidance states these are excluded by design, so roughly 1,300 of the missing 1,658 rows are permanent gaps rather than gaps to fill later.

A companion file, `institution_information_202225_API.csv` (1.1 MB, 2,792 rows), gives each institution's `establishment_type`, admissions policy, sex policy, and age range, if the table needs those as filters.
