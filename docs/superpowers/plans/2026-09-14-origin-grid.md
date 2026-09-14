# Origin grid implementation plan

**Goal:** Commit the England postcode mask and verify school postcode coverage.

**Architecture:** Read Code-Point Open directly from its zip, deduplicate integer kilometre cells, and convert centres with the specified pipeline. Fetch school postcode coordinates separately so routine tests remain offline.

**Tools:** Python standard library, pyproj, and the existing unittest suite.

**Contract:** `origin/issue-12-origin-grid-spec:docs/superpowers/specs/2026-09-14-origin-grid-design.md`, amended by the accepted findings in `/Users/rob/.claude/jobs/362f546b/tmp/brief-design-4.md`.

## One build task

1. Add `test_origins.py`. Check known identifiers, England and quality filtering, numeric sorting, centre coordinates, school coverage, and regeneration when the zip exists. Run the tests and confirm failure before implementation.
2. Add `fixtures/make_origins.py` with `origin_id(easting, northing)`, direct zip reading, the pinned transformation, and `make origins`.
3. Add `fixtures/fetch_school_postcodes.py`. Fetch distinct school postcodes in batches of 100, then use the terminated endpoint for missing results. Reject unresolved coordinates before replacing the fixture.
4. Register the Code-Point Open licence before downloading. Record the downloaded zip's size and checksum in `fixtures/feed-manifest.json`.
5. Generate both CSVs. Run `uv run fixtures/check_manifest.py .`, `uv run --with pyproj python -m unittest`, and `node check_sort.mjs`. Verify the generator test skips when the zip is absent.
6. Record measured counts and neighbour exceptions in the local spike notes. Review once, commit the build, and push the branch without a pull request.
