# Origin grid: issue #12 design

Date: September 14, 2026

## Goal

Fix the set of origins the precompute runs against, give each one an identifier the browser computes from a postcode without a round trip, and commit the list.

## The geography

Origins are the centres of EPSG:27700 1 kilometre grid cells, masked to those holding at least one England postcode in Ordnance Survey Code-Point Open, whose country code column marks England as E92000001. The mask is exact: the only thing a user can enter is a postcode, so a cell holding none can never be asked about.

Drop the 849 England rows whose positional quality indicator is 90: their easting and northing are zero, which would put an origin at cell `0_0` in the Atlantic. Keep quality 50 and 60, 3,853 and 241 rows. Those positions are estimated rather than surveyed, but the postcodes are real and an estimated position is worth more than no origin.

The result is 93,217 cells holding 1,495,007 England postcodes. Great Britain would be 123,416. A Welsh or Scottish postcode gets no origin by design, so the page must say that the site covers England only.

## The cell identifier

The identifier is the easting and northing of the cell's south-west corner in whole kilometres, joined by an underscore, for example `489_510`. One pure function computes it from OSGB36 National Grid metres:

    origin_id(easting, northing) = f"{easting // 1000}_{northing // 1000}"

Code-Point Open publishes eastings and northings directly, and so does postcodes.io, which the page already calls, so the browser needs no coordinate transform, only its own copy of this function with `Math.floor(e / 1000)` for the floor division.

`fixtures/origins.csv` sorts numerically by easting then northing, not lexicographically, because the identifiers run from `87_` to `655_`.

## The Worker must try the neighbours

postcodes.io and Code-Point Open disagree about position for 99 of the 4,227 school postcodes present in both, 10 of them by a whole cell. GL16 7EJ maps through postcodes.io to cell `362_211`, which the mask does not contain. Any two releases drift like this, so the answer is a fallback, not a different source.

The milestone 4 Worker looks up the requested identifier and, on a miss, tries the eight neighbours in a fixed order: east, west, north, south, then the four diagonals. It serves the first present and tells the page it used a neighbour.

## The committed output

`fixtures/origins.csv` has the columns `id`, `lat` and `lng`, one row per origin. The coordinates are the cell centre, easting and northing plus 500, converted to WGS84 to six decimal places, because MOTIS takes latitude and longitude.

`fixtures/make_origins.py` generates it from the Code-Point Open download, behind a `make origins` target. It uses pyproj, already a test dependency, only for that conversion. The identifier never touches it.

Pin the transform rather than letting pyproj choose:

    +proj=pipeline +step +inv +proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +step +proj=push +v_3 +step +proj=cart +ellps=airy +step +proj=helmert +x=446.448 +y=-125.157 +z=542.06 +rx=0.15 +ry=0.247 +rz=0.842 +s=-20.489 +convention=position_vector +step +inv +proj=cart +ellps=WGS84 +step +proj=pop +v_3 +step +proj=unitconvert +xy_in=rad +xy_out=deg

The pin is for reproducibility, not accuracy: this Helmert transform differs from OSTN15 by 1.3 to 3.5 metres at sample cell centres, nothing against MOTIS's 250 metre matching distance. What matters is that the file does not change under the generator, and `PROJ_NETWORK=ON` alone makes pyproj fetch the OSTN15 grid, so it must not depend on the environment.

## The download

`https://api.os.uk/downloads/v1/products/CodePointOpen/downloads?area=GB&format=CSV&redirect` returns a 14,461,176 byte zip and needs no account. The API publishes its MD5, which goes in the `fixtures/feed-manifest.json` entry alongside a null validity window. Download it by hand into `data/`, which is gitignored.

Inside, `Data/CSV/` holds 129 headerless CSV files, one per postcode area, with column names in `Doc/Code-Point_Open_Column_Headers.csv`.

The `LICENSES/README.md` row is Open Government Licence v3.0: the Ordnance Survey licence URL redirects to the National Archives text already in `LICENSES/`. Three acknowledgements go on the page, all at 2026 because `Doc/metadata.txt` gives the copyright date 20260720: Ordnance Survey, Royal Mail and National Statistics.

## The tests

`fixtures/school-postcodes.csv` is a committed fixture of `postcode`, `eastings`, `northings` and `source`, built once by `fixtures/fetch_school_postcodes.py` from postcodes.io's bulk lookup and its terminated-postcodes endpoint for the 4,263 distinct postcodes in `schools.json`.

The unit test runs always. For every postcode in that fixture it computes the cell the way the browser will and asserts that it is in `fixtures/origins.csv`, or that one of its eight neighbours is.

Absence from Code-Point Open is not a failure. 36 school postcodes are missing: 34 terminated, since Code-Point Open holds current units only, and two live ones, M7 4LJ and TA19 9DT.

`make_origins.py` also has a self-check that regenerates a sample from the zip. That needs `data/`, which is gitignored, so it runs only when the zip is present and otherwise skips with a message.
