# Cap the precompute at 90 minutes and offer limits up to 90, defaulting to 60

Date: September 13, 2026

## Decision

The precompute stores journeys up to 90 minutes and discards anything longer. The site offers time limits up to 90 minutes, with 60 minutes as the default.

## Why

The user's judgement is that nobody travels more than 60 to 90 minutes each way to school, so a longer cap would store journeys nobody would consider. The one official figure points the same way: the Department for Education's post-16 transport guidance treats up to 75 minutes each way as a reasonable journey, which sits between the two. The commute research note found no measured travel-time distribution for post-16 students in England at all, so there is nothing more precise to defer to, and 75 minutes is a policy benchmark rather than a measurement.

The cost of a longer cap is large and was measured in issue #5. For the same 100 schools and about 2,824 origins each, dropping the cap from 240 minutes to 90 took the run from 674 seconds to 144 seconds on 8 workers, cut the MOTIS server's peak resident memory from 18.0 GB to 9.7 GB, and cut the results file from 20.1 MB to 11.4 MB. Scaled to all 4,373 schools, that is about 1.7 hours against about 8.2 hours. Driving dominates the 240 minute figure, roughly 97 percent of request time, because each 250-origin street batch repeats the whole bounded search.

Storing up to 90 while defaulting the display to 60 keeps the two choices separate. Lowering the offered limit later is a display change; raising the stored cap is a full rerun. Storing the wider range costs 11.4 MB against a smaller file and buys the ability to change the site's limits without touching the precompute.

See `docs/superpowers/research/2026-09-13-spike-measurements.md` for the timings and `docs/superpowers/research/2026-09-13-post-16-commute-statistics.md` for the guidance figure and the absence of a measured distribution.

## Cycling speed

Cycling runs at 5.0 metres per second, 18 kilometres per hour nominal, set through `cyclingSpeed` on `POST /api/experimental/one-to-many-intermodal` with `directMode: BIKE` and an empty `transitModes` list.

The figure comes from the 10.4 kilometre route from Haxby, 54.01885 and -1.06286, to Archbishop Holgate's School, URN 136617, arriving by 08:30 on Wednesday September 16, 2026. MOTIS 2.11.3 returns 2,778 seconds at its built-in 4.2 metres per second, 2,573 at 4.5, 2,467 at 4.7 and 2,293 at 5.0. Google Maps gives 35 minutes. At 5.0 the answer is 38 minutes, an effective 16.3 kilometres per hour once junction costs are counted.

The plain street endpoints cannot be used for cycling. `GET` and `POST /api/v1/one-to-many` accept `cyclingSpeed` and silently ignore it, returning 2,778 seconds whatever it is set to. Only the intermodal endpoint honours it, so the bike sweep runs there with the transit modes switched off.

## Open points

At 90 minutes the 30 km origin radius, not the cap, is what bounds the driving results and probably the cycling results too, because both cover more than 30 km in 90 minutes. The radius therefore needs revisiting alongside the cap; issue #15 holds that work.

The metric is settled. The cap is expressed in leave-by seconds, the time before 08:30 at which you must leave home, and not in journey duration; see `docs/decisions/2026-09-14-store-leave-by-minutes.md`. The transit values the sweep already stored were leave-by figures, so the only change is taking the smaller of the transit figure and the direct walk. That can only lower a value, and it lowers it for short journeys that were already well inside the cap, so the cost measurements above stand.
