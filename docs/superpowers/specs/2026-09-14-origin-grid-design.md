# Origin grid: issue #12 design

Date: September 14, 2026

## Goal

Fix the set of origins the precompute runs against, give each one an identifier the browser computes from a postcode without a round trip, and commit the list so a later run has something to compare against.

## The geography

Origins stay the centres of EPSG:27700 1 kilometre grid cells, as already decided. The change is a mask. A cell is an origin exactly when it contains at least one live England postcode centroid in Ordnance Survey Code-Point Open, whose country code column identifies England as E92000001.

The mask is exact rather than approximate. The only thing a user can enter is a postcode, so a cell holding no postcode can never be asked about. A land or population mask has to guess where people are; this one does not.

## The cell identifier

The identifier is the easting and northing of the cell's south-west corner in whole kilometres, joined by an underscore. The cell holding the Whitby probe origin is `489_510`. It is stable, it sorts, and one pure function computes it by integer division of OSGB36 National Grid metres:

    origin_id(easting, northing) = f"{easting // 1000}_{northing // 1000}"

Code-Point Open publishes eastings and northings directly, and so does postcodes.io, which the page already calls to geocode the postcode. The browser therefore needs no coordinate transform in milestone 4, and there is no pair of Python and JavaScript transforms that can drift apart.

## The committed output

`fixtures/origins.csv` has the columns `id`, `lat` and `lng`, one row per origin, sorted by id. The coordinates are the cell centre, easting plus 500 and northing plus 500, converted to WGS84 and written to six decimal places, because MOTIS takes latitude and longitude.

`fixtures/make_origins.py` generates that file from the Code-Point Open download using pyproj, which the test suite already depends on. pyproj appears only in the conversion of cell centres to latitude and longitude. The identifier never touches it.

Pin the transform instead of letting pyproj choose one. As installed, pyproj 3.7.2 with PROJ 9.5.1 has no OSTN15 grid and falls back to the Helmert transform named "OSGB36 to WGS 84 (6)", which EPSG rates at 2 metres. Installing the grid later would switch pyproj to OSTN15 and move every cell centre by about that much. Build the transformer with `Transformer.from_pipeline` and the Helmert parameters so every run produces the same file.

## The download

Download the Code-Point Open zip by hand into `data/`, which is gitignored. Add an entry for it in `fixtures/feed-manifest.json` with a null validity window, and a row in `LICENSES/README.md`. It is a free download under the Open Government Licence v3.0 and carries the Ordnance Survey and Royal Mail acknowledgements the page shows for postcodes.io.

## The test

For every postcode in `schools.json`, look it up in Code-Point Open, compute `origin_id` from its published easting and northing, and assert that exactly one row of `fixtures/origins.csv` carries that id. A postcode absent from Code-Point Open fails the test and is reported by name, because that is a coverage gap rather than a rounding question.

## Expected count

Between 90,000 and 120,000 origins. Replace this with the measured count. The planning figure for England's land grid is about 130,000 cells, and England holds roughly 1.5 million of Code-Point Open's Great Britain postcodes, an average of about 11 per cell. Rural England is thoroughly postcoded, so the empty cells are mainly upland moor and fell, large forests, military ranges, and the mostly-sea half of coastal cells. That is plausibly 10 to 30 percent of the grid.
