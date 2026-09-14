# Per-origin record format: issue #13 design

Date: September 14, 2026

## Goal

Define the bytes the precompute writes for one origin, precisely enough that a Python writer and a JavaScript Worker reader can be built independently and agree. The Worker, the validator and the refresh all depend on this, so it is written down before the writer.

## What a value means

Every stored value is leave-by seconds: how long before 08:30 you must leave that origin to reach that school by 08:30. See `docs/decisions/2026-09-14-store-leave-by-minutes.md`.

## Dense, not sparse

Each record is a dense fixed-width array covering all 4,373 schools in all four modes: 34,984 bytes, always.

A sparse record holding a two-byte index and a two-byte value per reachable pair is smaller before compression. It wins while a record holds fewer than 8,744 reachable pairs out of a possible 17,492, which is most origins. It stops winning once both formats are compressed. The dense record's unreachable slots are runs of `ff` bytes that gzip reduces to almost nothing, leaving roughly two bytes of real entropy per reachable pair. The sparse record still carries four, and its ascending indexes do not compress well. Compressed, dense is the smaller of the two and simpler to read: one fixed offset, no scan, no index table.

## Stored resolution

Unsigned 16-bit seconds, unrounded, little-endian. This keeps the existing decision in `docs/decisions/2026-09-13-ten-minute-display-bands.md` and resolves its conflict with issue #13, which asks for 5, 10 or 15 minute buckets in the bytes. The bucket stays a display choice, recorded in the manifest under issue #16 and changeable without a rerun. Banding to a single byte would halve the record to 17,492 bytes, but the uncompressed dataset already fits inside R2's allowance, so the saving buys nothing and costs the ability to sort within a band.

## Layout

Four planes, one per mode, in this order: public transport, walking, cycling, driving. Each plane is 4,373 values of two bytes, 8,746 bytes. A value sits at

    offset = mode_index * 8746 + school_index * 2

The sentinel `ffff`, 65,535, means unreachable. Real values run from 0 to 5,400 inclusive, the 90 minute cap. Anything between 5,401 and 65,534 is corrupt.

There is no header. The dataset version is in the object key, `version/cell-id.bin`, and everything else is in the manifest, so a header would repeat the manifest in every record.

## Walking is stored separately

The site already offers walking as one of its four modes, so dropping it is a product change rather than a format simplification. A 90 minute walk covers about seven kilometres, so most origins reach no school on foot and the walking plane is almost all sentinel. The public transport plane already takes the smaller of the transit figure and the direct walk, so the public transport value is never larger than the walking value. The validator checks that.

## School index

The index is the position of the school's URN in the URNs from `schools.json` sorted ascending, 0 to 4,372. All URNs are six-digit strings, so text and numeric order agree.

The manifest records `school_index_sha256`, the SHA-256 of those sorted URNs joined by single newlines with no trailing newline, encoded as UTF-8 in lowercase hex. Today it is `43760fe2449c63cdb1ff7a4a03fc310da08c85990199b51868d7b87edbf120d9`. A record decodes only against the school list carrying its hash.

## Worked example

Origin `489_510`, the cell holding 54.481966 and -0.620123 near Whitby. Whitby School, URN 121667, is at index 907, so its four slots are at byte offsets 1,814, 10,560, 19,306 and 28,052. MOTIS returns 4,200 seconds of transit and 957 seconds of direct walking for that pair, so both the public transport value and the walking value are 957, which is `03bd` and goes to disk as `bd 03`. City of London School for Girls, URN 100001, is at index 0 and is 350 kilometres away, so every one of its slots is the sentinel.

    offset      bytes    meaning
         0      ff ff    public transport, index 0, unreachable
     1,814      bd 03    public transport, index 907, 957 seconds
     8,746      ff ff    walking, index 0, unreachable
    10,560      bd 03    walking, index 907, 957 seconds

## Encoding and decoding

To encode, fill 34,984 bytes with `ff`, then for every pair whose leave-by seconds are 5,400 or fewer write `struct.pack("<H", seconds)` at its offset. Leave everything else at the sentinel. Assert that no value written falls between 5,401 and 65,534.

To decode, reject any object whose length is not exactly 34,984 bytes, then read it as a `Uint16Array` and take element `mode_index * 4373 + school_index`. Every platform that runs a browser is little-endian, so no `DataView` is needed. Treat 65,535 as unreachable and anything from 5,401 to 65,534 as corrupt.

## Size

34,984 bytes per origin. For the 90,000 to 120,000 origins the origin grid spec expects, that is 3.15 GB to 4.20 GB uncompressed, inside R2's 10 GB included storage, and 120,000 objects against its million included monthly writes. Store the objects gzipped and measure the compressed total before publishing.

## The round-trip test

A Python test builds a record containing 0 seconds, 5,400 seconds, a sentinel, index 0 and index 4,372, encodes it, decodes it, and asserts the values come back unchanged and the length is 34,984. It writes that record to `fixtures/example-origin.bin`. `check_sort.mjs` reads the same file and asserts the same values, so the writer and the reader are checked against each other rather than each against itself.
