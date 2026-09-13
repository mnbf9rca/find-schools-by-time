# Feed manifest and verification: issue #10 design

Date: September 14, 2026

## Goal

Make a precompute run reproducible, and give a later refresh something to diff against. The feeds are too large to commit, so the manifest stands in for them.

## The manifest

`fixtures/feed-manifest.json`, a JSON array of objects, one per input file. JSON rather than CSV because the standard library reads it without quoting rules, and it sits beside the script that verifies it. Each entry has: `path`, relative to the repository root; `source`, the download URL or, where there is no public URL, the account and product that supplied it; `downloaded`, an ISO date; `bytes`; `sha256`; `valid_from` and `valid_to`, the feed's validity window as ISO dates or both null where the input is not a timetable; and `licence`, matching an item name in `LICENSES/README.md` exactly.

Entries cover the MOTIS binary tarball, the Bus Open Data Service zip, the OpenStreetMap England extract, the nine National Rail CIF files, and every supplement issue #9 adds. The milestone 1 figures come from `motis-spike/NOTES.md` and `motis-spike/checksums.txt`, and the rail figures from the "Rail timetable (issue #7)" section of the same note. The rail bundle's validity window is 2026-05-17 to 2027-05-15, taken from the schedule records rather than the stale file header, and every one of the nine files carries it. The MOTIS tarball and the OpenStreetMap extract have a null window, because neither is a timetable.

## The verification script

`fixtures/check_manifest.py`, run as `uv run fixtures/check_manifest.py <base-directory>`, standard library only. The base directory is an argument so the script runs from a worktree against the main tree's files. For each entry it resolves `path` against that directory, then checks the file exists, its size matches `bytes`, and its SHA-256 matches `sha256`, hashing in chunks because one CIF file is 715 MB. It then checks that every entry with a validity window covers 2026-09-16, the routing date, and that every `licence` names a row in `LICENSES/README.md`. Every failure is printed, not just the first, and the script exits non-zero if there was any.

`--check` runs a self-test instead: it builds a small manifest and matching files in a temporary directory and asserts that a correct set passes, and that a wrong size, a wrong checksum, a missing file, and a validity window ending before 2026-09-16 each fail. It touches no real feed and exits non-zero on any failed assertion.
