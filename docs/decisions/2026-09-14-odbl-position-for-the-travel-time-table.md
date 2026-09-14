# The ODbL position for the precomputed travel-time table

Date: September 14, 2026

## Decision

The precomputed travel-time table is a produced work under the Open Database Licence, not a derivative database. The user decided this on September 14, 2026. The website and the per-search CSV carry the OpenStreetMap credit required for a produced work, and the whole table is not published as a downloadable database. Publishing it later would be a fresh decision taken with the rail agreement in view.

## The facts

The precomputed table holds travel times in seconds from origin grid cells to schools. MOTIS produces each number by routing over the OpenStreetMap England street network together with the bus, rail and ferry timetables. The table carries no OpenStreetMap geometry and no OpenStreetMap identifiers: an origin is an EPSG:27700 grid cell centre generated arithmetically, a destination is a school URN, and the value between them is a duration.

The website shows the results for one postcode at a time and offers a CSV of exactly those results. Whether the whole table is also published as a downloadable dataset is open.

Two parts of the Open Database Licence decide this. Clause 4.5 b says that using the database to create a produced work does not create a derivative database, so the share-alike duty in clause 4.4 does not reach a produced work. Clause 4.6 says that publicly using a derivative database, or a produced work made from one, obliges you to offer recipients the derivative database or the alterations. The Open Street Map Foundation's produced work guideline draws the line by intent: a published result meant for extracting the original data is a database, and anything else is a produced work. Its geocoding guideline is the closest published analogy: individual results are insubstantial extracts that do not trigger share-alike, while a systematic aggregation reconstructing a substantial part of OpenStreetMap does become a derivative database.

## The options

**Publish the whole table under the Open Database Licence as a derivative database.** This is the safest reading if the table is judged a substantial extraction. It settles the question and lets anyone reuse the data. The cost is that the table then has to stay available under those terms, and the reuse it invites has to be compatible with the timetable licences that also sit in the numbers.

**Treat the page and the per-search CSV as produced works, attribute OpenStreetMap, and never publish the whole table as a downloadable database.** This rests on clause 4.5 b and on the geocoding guideline's treatment of individual results. It keeps the obligation to a credit line. The cost is the constraint itself: no bulk download can ever be offered without revisiting this, and the judgement that the table is not a substantial extract has not been tested.

**Publish the whole table under the Open Database Licence, and record how that meets the Rail Delivery Group agreement.** The agreement's Schedule 1 permits the raw data for research and analysis only, and clause 3.3.2 requires an accuracy notice on onward distribution. A public dataset of derived times would need that notice, and the user's settled position that this project's table counts as analysis would have to extend to redistributing it.

## Why

This is the second option. It was chosen because the table holds no OpenStreetMap geometry or identifiers, so it is a weak candidate for a substantial extract, and the produced work reading matches how the numbers are actually used: a visitor asks about one postcode and gets an answer. It is also the only option that adds no lasting obligation, and it is reversible, because publishing the table later stays available while the reverse does not. The rail agreement points the same way, since not distributing the table avoids the accuracy notice question entirely.

See `LICENSES/README.md` for the OpenStreetMap and rail rows, and `LICENSES/ODbL-1.0.txt` for the licence text.
