# Per-origin record format: issue #13 design

Date: September 14, 2026

## Goal

Define the bytes the precompute writes for one origin, precisely enough that a Python writer and a JavaScript Worker reader can be built independently and agree. The Worker, the validator and the refresh all depend on this, so it is written down before the writer.

## What a value means

Every stored value is leave-by seconds: how long before 08:30 you must leave that origin to reach that school by 08:30. See `docs/decisions/2026-09-14-store-leave-by-minutes.md`.

The sentinel means only that no value was stored: the journey is over the 5,400 second cap, the origin lies outside that mode's pruning radius, or the pair was never computed. The validator must not read it as proof that a school is unreachable.

## Dense, not sparse

Each record is a dense fixed-width array covering every school in the index in all four modes. With today's 4,373 schools that is 34,984 bytes, always.

Sparse is the smaller format for most origins, and stays smaller after compression. Gzipping built records gives 1,420 bytes dense against 1,233 sparse at 330 reachable pairs, 3,148 against 3,085 at 861, and 5,217 against 5,762 at 1,623. Sparse therefore wins below about 1,000 pairs, which is where most origins sit, and the most it saves is about 190 bytes on a record of 1.4 KB.

Dense is chosen for everything else. A value is one fixed offset, with no index to read and no list to scan. The record's length is its own validity check. The whole dataset fits the storage allowance uncompressed, so the saving buys nothing worth the extra reader.

## Stored resolution

Unsigned 16-bit seconds, unrounded, little-endian. This keeps the existing decision in `docs/decisions/2026-09-13-ten-minute-display-bands.md` and resolves its conflict with issue #13, which asks for 5, 10 or 15 minute buckets in the bytes. The bucket stays a display choice, recorded in the manifest under issue #16 and changeable without a rerun. Banding to a single byte would halve the record, but the dataset already fits inside R2's allowance, so the saving buys nothing and costs the ability to sort within a band.

## Layout

The per-origin key scheme below is superseded by `docs/decisions/2026-09-14-publish-sharded-objects.md`, which publishes shards of 8,000 records instead; the record bytes are unchanged.

Four planes, one per mode. The plane index matches the mode strings `app.py` already uses: `public_transport` is 0, `walking` is 1, `cycling` is 2, `driving` is 3. The manifest's `modes` list is that array in that order.

Each plane holds one two-byte value per school, so a plane is twice the school count in bytes, 8,746 with today's 4,373 schools. A value sits at

    plane_bytes = school_count * 2
    offset = mode_index * plane_bytes + school_index * 2

The sentinel `ffff`, 65,535, means no value. Real values run from 0 to 5,400 inclusive, the 90 minute cap.

There is no header: the version is in the object key and everything else is in the manifest, so a header would repeat the manifest in every record. Keys are `<version>/<origin-id>.bin`, the version being the run's start time in UTC as the runner spec defines it, for example `20260914T093000Z/489_510.bin`. The origin identifier is the one in `docs/superpowers/specs/2026-09-14-origin-grid-design.md`.

Every origin in `fixtures/origins.csv` gets exactly one object, all sentinel where nothing is reachable, so the object count equals the origin count. The validator checks that equality. A key that is missing is an error the Worker reports, not an empty result.

## The four planes

Walking is one of the site's four modes, so dropping it is a product change rather than a format simplification. A 90 minute walk covers about seven kilometres, so most origins reach no school on foot and the walking plane is almost all sentinel.

The public transport value is the smaller of the MOTIS transit figure and the value written to the walking plane, not of the transit figure and some other walk. Written that way, the invariant that public transport never exceeds walking holds by construction. The validator checks it, treating the sentinel as infinity.

## School index

The index is the position of the school's URN in the URNs from `schools.json` sorted ascending, 0 to 4,372. All URNs are six-digit strings, so text and numeric order agree. The index is always the whole of `schools.json`, whatever the runner's `--schools` flag selects, so a sample run still writes full-size records with only the sampled schools populated.

`schools.json` is currently in that order by accident: `build_schools.py` does not sort. This build makes it sort by URN and makes `test_build.py` assert that, two lines in total.

The manifest records `school_index_sha256`, the SHA-256 of those sorted URNs joined by single newlines with no trailing newline, encoded as UTF-8 in lowercase hex. Today it is `43760fe2449c63cdb1ff7a4a03fc310da08c85990199b51868d7b87edbf120d9`. The writer computes it into the manifest. `build_schools.py` also emits `school-index.js`, a small module holding the school count and that hash, which is what `record.js` and the Worker read; importing `schools.json` would pull two megabytes into a Worker bundle to learn one integer. The Worker compares the manifest's hash with the one in that module and refuses to serve on a mismatch, because a record decoded against the wrong school list returns another school's times without failing.

## Worked example

Origin `489_510`, the cell holding 54.481966 and -0.620123 near Whitby. Whitby School, URN 121667, is at index 907, so with today's 4,373 schools its four slots are at byte offsets 1,814, 10,560, 19,306 and 28,052. MOTIS returns 4,200 seconds of transit and 957 seconds of direct walking for that pair, so both the public transport value and the walking value are 957, which is `03bd` and goes to disk as `bd 03`. City of London School for Girls, URN 100001, is at index 0 and 350 kilometres away, so all four of its slots are the sentinel.

    offset      bytes    meaning
         0      ff ff    public transport, index 0, no value
     1,814      bd 03    public transport, index 907, 957 seconds
     8,746      ff ff    walking, index 0, no value
    10,560      bd 03    walking, index 907, 957 seconds

## Encoding and decoding

To encode, round each MOTIS duration half up to a whole second, then compare it with the cap. Zero is a valid value. A negative value is a writer error and raises. Fill `4 * plane_bytes` with `ff`, then for every pair of 5,400 seconds or fewer write `struct.pack("<H", seconds)` at its offset, leaving everything else at the sentinel.

To decode, take the school count from the school list rather than hardcoding it, and reject any object whose length is not `4 * 2 * school_count`. Read the buffer through a `DataView` with `littleEndian` true and take element `mode_index * school_count + school_index`, because a byte view can start at an odd offset, where a `Uint16Array` throws. Treat 65,535 as no value and anything from 5,401 to 65,534 as corrupt. The school index hash is what guarantees the school count is the right one.

The reader lives in `record.js`, exporting `decode(buffer, modeIndex, schoolIndex)`. The Worker imports it in milestone 4; `check_sort.mjs` imports it now.

## Size

34,984 bytes per origin across the 93,217 origins the origin grid spec measures, so one version is 3.26 GB.

Objects are stored uncompressed. R2 does not compress at rest and the Workers binding does not decompress, so a gzipped object would reach the browser still gzipped. Compression would also break the exact-length check and any range read added later.

Two versions coexist during a publish: upload the new version in full, flip `current.json` to it, then delete the previous one. The budget is therefore twice one version, 6.5 GB against R2's 10 GB included storage, which leaves no room for a third. Each version is 93,217 objects against the million included monthly writes.

## The round-trip test

`fixtures/example-origin.bin` is committed. It holds 0 seconds, 5,400 seconds, sentinels, index 0 and the last index.

The Python test builds that record from its values, asserts the encoder reproduces the committed file byte for byte, then decodes it and asserts the values and length come back unchanged. `check_sort.mjs` reads the same file through `record.js` and asserts the same values. Because both read a committed fixture rather than one the other wrote, the two test commands pass in either order and the fixture guards the format against an accidental change.

`check_sort.mjs` keeps its name. Its final printed line changes to cover the record checks as well as the sorting, split-column and CSV ones.
