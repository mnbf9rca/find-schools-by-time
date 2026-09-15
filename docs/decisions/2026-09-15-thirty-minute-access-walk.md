# Allow a 30 minute walk to the first stop

Date: September 15, 2026

## Decision

The public transport request sets `maxPreTransitTime` to 1,800 seconds, up from 900. `maxPostTransitTime` stays at 900, because schools sit in towns with stops nearby and raising it alone recovers nothing.

## Why

Medina College, URN 150099, from cell `459_90` has a real journey that the 900 second limit hides: leave at 07:09, arrive at 08:29, a 76 minute leave-by with a 27 minute walk to the first stop. At 900 seconds MOTIS returns nothing for that pair, and widening the matching distance to 1,000 metres does not recover it. Only the longer access walk does.

That is the rural pattern, not one origin. In the full dataset the median origin reaches one school by public transport, which is what a 15 minute limit on the walk to the first stop produces in a country where rural stops are further apart than that.

## Cost

About 1 hour 35 minutes of wall time on the full grid. Run 3, version 20260915T011918Z, took 4 hours 8 minutes at eight workers against run 2's 2 hours 33 minutes, with everything else equal apart from the fallback pass over 887 origins, which issued 2,661 requests and took a few minutes. Peak server resident set rose from 9.95 GB to 11.77 GB.

The longer access walk also does the work it was meant to do: the count of origins reaching nothing at all fell from 1,120 to 887 before the fallback ran.

## What it changes

The public transport plane now allows up to 30 minutes of walking at the home end, so some stored values describe a journey a visitor would call a long walk to the bus. The 90 minute cap still bounds the whole journey, and widening the set of journeys can only add a pair or lower an existing value, never raise one.
