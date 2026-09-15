# Allow a 30 minute walk to the first stop

Date: September 15, 2026

## Decision

The public transport request sets `maxPreTransitTime` to 1,800 seconds, up from 900. `maxPostTransitTime` stays at 900, because schools sit in towns with stops nearby and raising it alone recovers nothing.

## Why

Medina College, URN 150099, from cell `459_90` has a real journey that the 900 second limit hides: leave at 07:09, arrive at 08:29, a 76 minute leave-by with a 27 minute walk to the first stop. At 900 seconds MOTIS returns nothing for that pair, and widening the matching distance to 1,000 metres does not recover it. Only the longer access walk does.

That is the rural pattern, not one origin. In the full dataset the median origin reaches one school by public transport, which is what a 15 minute limit on the walk to the first stop produces in a country where rural stops are further apart than that.

## Cost

Measured on the 100-school sample before the rerun. The coordinator records the measured figure here.

The measurement matters because the paired extrapolations from the September 15 probes put a full run somewhere between 54 and 132 hours at eight workers, with wide uncertainty, against the 2 hours 33 minutes the run with 900 seconds took.

## What it changes

The public transport plane now allows up to 30 minutes of walking at the home end, so some stored values describe a journey a visitor would call a long walk to the bus. The 90 minute cap still bounds the whole journey, and widening the set of journeys can only add a pair or lower an existing value, never raise one.
