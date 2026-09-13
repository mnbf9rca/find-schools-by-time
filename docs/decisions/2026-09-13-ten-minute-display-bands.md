# Store travel times as unrounded seconds and display them in 10 minute bands

Date: September 13, 2026

## Decision

The dataset stores travel times as unrounded seconds. The site displays them in 10 minute bands.

## Why

Seconds are stored because they cost nothing to keep. A 90 minute cap is 5,400 seconds, which fits in an unsigned 16-bit integer, the width the dataset already plans to use. Rounding before storage would save no space and would fix the band width permanently.

The display band is 10 minutes because that is roughly the precision the origin geography can support. Origins are the centres of 1 km grid cells, so a home can sit up to about 700 metres from the centre used to compute its times, which is roughly 8 minutes of walking. Displaying 5 minute bands would claim a precision the grid cannot deliver, because the band would be narrower than the error introduced by snapping the home to a cell centre. Going the other way, 15 minute bands leave only four steps below the default 60 minute limit, which is too coarse to help anyone compare schools.

Because the stored value is seconds, the band width is a display choice rather than a property of the data. Issue #23 can change it without rerunning the precompute.

This particular choice was made in the user's absence, weighing the 700 metre cell error against the number of usable steps. It is the cheapest kind of decision to reverse: changing the band is a change to the display code alone, so treat it as a starting point rather than a settled question.
