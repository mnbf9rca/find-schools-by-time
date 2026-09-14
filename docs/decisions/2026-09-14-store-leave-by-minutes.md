# Store how long before 08:30 you must leave, not the journey duration

Date: September 14, 2026

## Decision

For every origin, school and mode, the dataset stores the number of seconds before 08:30 at which you must leave home to arrive by 08:30. For the public transport mode that is the smaller of the transit figure and the direct walk. For walking, cycling and driving it is the street journey duration, because those searches run with the transit modes switched off.

## Why

This is the metric the site already uses. The decision to use a computed departure time put it plainly: a school appears exactly when you can leave home at that time and be there by 08:30. Storing leave-by seconds keeps that promise rather than changing what the site means.

It is also what MOTIS returns natively. Under `arriveBy`, `POST /api/experimental/one-to-many-intermodal` reports 08:30 minus the departure time of the latest feasible journey, so the wait before 08:30 is already folded in. The `street_durations` entry for the direct leg is a plain journey time, which under this metric is the same number, because a street journey involves no waiting.

True journey duration is not available from the one-to-many endpoints at all. Getting it would need one plan request per origin and school pair, which is hundreds of millions of requests against the 17,492 one-to-many sweeps that searching outward from each school costs.

Taking the smaller of the two settles the check in issue #39. From the origin at 54.481966, -0.620123 to Whitby School, URN 121667, MOTIS 2.11.3 on the combined graph returns 4,200 seconds of transit and 957 seconds of direct walking for Wednesday September 16, 2026. The stored value is 957 seconds, or 16 minutes, which is the sensible answer for a school 300 metres away.

## Consequences

The site must say "leave by" or "minutes before 08:30", never "journey time". A school served by one early bus shows a long figure even when the bus ride itself is short, and that figure is correct: you do have to leave that early.
