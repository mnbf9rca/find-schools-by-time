# Split result columns and CSV download: iteration 3 design

Date: September 13, 2026

## Goal

Let the user compare grades and point scores independently, and take the table away with them. This extends the iteration 2 design in `2026-09-13-results-columns-design.md`, which stays as written except where this document changes it. Work continues as further commits on the `results-columns` branch.

## Scope

In scope: splitting the two paired results columns into four, and a Download CSV button. Out of scope: any server change, any new data field, any change to the build, and any change to the other columns.

## Four columns in place of two

`COLUMNS` in `sort.js` replaces its two paired entries with four:

| Column | Cell contents | Sorts on |
|---|---|---|
| Average result grade | `grade` | `aps` |
| Average result points | `aps` | `aps` |
| Best 3 A levels grade | `best3_grade` | `best3_aps` |
| Best 3 A levels points | `best3_aps` | `best3_aps` |

The existing rule that a grade column orders by its point score is what keeps the two grade columns sorting sensibly, since grade letters do not sort in grade order. Two columns therefore share a sort key with their neighbour; clicking either one sorts the same way, and the `aria-sort` marker and the arrow appear on both. That is the honest consequence of the split and needs no extra code.

The `Progress` column stays paired, as does every other column. Cells whose value is `None` still render empty.

## Download CSV

A `<button id="download">Download CSV</button>` sits next to the results count, `disabled` until a search returns at least one row, and disabled again at the start of each new search. It carries no styling beyond the page default.

On click the page builds the CSV in the browser from the rows it already holds, in the order currently shown, and saves it with a `Blob` and a temporary anchor carrying a `download` attribute, revoking the object URL afterwards. The file is named `schools-<postcode with spaces removed>-<minutes>min.csv`, taking both values from the form as submitted.

The text starts with a UTF-8 byte order mark, `﻿`, so Excel reads school names with accented characters correctly rather than as mojibake. Rows are joined with `\r\n`.

Fields are the raw values, not the table's display text: grades as their letters, numbers unformatted and without a per cent sign, `null` and `undefined` as an empty field. A field is wrapped in double quotes only when it contains a comma, a double quote, or a newline, and any double quote inside it is doubled.

Columns are `URN`, already present in every search response, then one field per table column in table order, using each column's underlying value rather than its rendered cell. The one addition: `Progress` exports two fields, the score and `Progress description` carrying the banding, because it is the only column still pairing two values and dropping the banding would lose data the table shows. `Website` exports the URL.

## Where the code lives

`sort.js` gains three exports, so `check_sort.mjs` can run them under `node` with no browser:

- Each `COLUMNS` entry gains a `value(row)` function returning its raw CSV value, alongside the `cell(row)` it already has.
- `csvField(value)` returns the quoted-when-necessary text for one value.
- `csvRows(rows)` returns the array of CSV lines, header first, ready for the page to join.

`index.html` keeps only the click handler: build the text, make the Blob, click the anchor. No server change, so `app.py` and `build_schools.py` are untouched.

## Testing

`check_sort.mjs` gains cases:

- `csvField` leaves a plain value alone, quotes a name containing a comma, quotes and doubles the quote in a name containing one, quotes a value containing a newline, and returns an empty field for `null`.
- `csvRows` on a row with a null cell emits an empty field in that position and keeps the row's field count equal to the header's.
- The header row names `URN` first and then the table columns in table order, checked against `COLUMNS` rather than a hand-written list, so a reordered column cannot pass silently.

The four-way split needs no new check: the existing column mapping cases in `check_sort.mjs` already assert each column's key and cell text, and gain one case per new column in the same form.
