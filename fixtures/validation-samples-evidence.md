# Planner evidence for the twelve validation samples

Google's arrive-by result set under-reports the latest departure, so each transit row includes a confirming depart-at probe.

Row 621_333 has a leave-by time of 91 minutes, one minute over the cap. It reads `beyond cap` and must be re-checked by hand if it fails.

All twelve journeys target Wednesday, September 16, 2026, arriving by 08:30 British Summer Time. Google Maps is the planner for every row. No row lies in Greater London, so the TfL Journey Planner cross-check does not apply: the four public transport origins are Walsall, Ryde, north Northumberland and north Norfolk.

## Method

Each query uses a Google Maps directions URL of the form `https://www.google.com/maps/dir/<origin>/<destination>/data=!4m6!4m5!2m3!<when>!7e2!8j<timestamp>!<mode>?hl=en&gl=uk`, with `6e1` for arrive by, `6e0` for depart at, and `3e0`, `3e1`, `3e2`, `3e3` for driving, cycling, walking and public transport. Google encodes the wall-clock time as if it were UTC, so 08:30 on September 16, 2026 is timestamp `1789547400`. Every page below was confirmed to show "Arrive by" or "Depart at", "Wed 16 Sept" and the time "08:30" in the controls.

Google's arrive-by result set does not always contain the latest feasible departure. On row 1 the arrive-by query offered 06:48 as the latest departure, but a depart-at probe found a 07:01 departure arriving at 08:30 exactly. Every public transport row therefore carries two queries: the arrive-by query for the candidate, and a depart-at probe one minute later that confirms nothing later arrives by 08:30.

Google reports driving as a traffic range rather than a single figure. For the three driving rows, `planner_minutes` is 08:30 minus the "Leave at about" time that Google gives for the arrival, which matches the upper end of its range. The full range appears in each row below.

## Public transport rows

### Row 1: 405_301 to URN 103584, King Edward's School, Birmingham

- Planner: Google Maps.
- Endpoints as snapped: Phoenix Hinges, Northgate, Walsall WS9 8TL, to Ruddock Performing Arts Centre, King Edward's School, Edgbaston Park Road, Birmingham B15 2UA.
- Route: walk to Greenfields, bus 937, then bus 61, 1 hr 29 min.
- Departs 07:01, arrives 08:30. Leave-by is 89 minutes, inside the 90 minute cap.
- Confirmation: a depart-at 07:02 probe returns 08:46 as the earliest arrival.
- Arrive-by URL: https://www.google.com/maps/dir/52.611250,-1.920209/52.450585,-1.923530/data=!4m6!4m5!2m3!6e1!7e2!8j1789547400!3e3?hl=en&gl=uk
- Depart-at URL: https://www.google.com/maps/dir/52.611250,-1.920209/52.450585,-1.923530/data=!4m6!4m5!2m3!6e0!7e2!8j1789542000!3e3?hl=en&gl=uk

### Row 2: 459_90 to URN 150099, Medina College, Isle of Wight

- Planner: Google Maps.
- Endpoints as snapped: Smallbrook Stadium, Ashey Road, Ryde PO33 4BH, to Medina College, Fairlee Road, Newport PO30 2DX.
- Route: walk, then bus 9, 1 hr 7 min.
- Departs 07:20, arrives 08:27. Leave-by is 70 minutes.
- Confirmation: a depart-at 07:21 probe returns 08:47 as the earliest arrival.
- Arrive-by URL: https://www.google.com/maps/dir/50.711097,-1.158660/50.711574,-1.282553/data=!4m6!4m5!2m3!6e1!7e2!8j1789547400!3e3?hl=en&gl=uk
- Depart-at URL: https://www.google.com/maps/dir/50.711097,-1.158660/50.711574,-1.282553/data=!4m6!4m5!2m3!6e0!7e2!8j1789543260!3e3?hl=en&gl=uk

### Row 3: 415_635 to URN 137598, Berwick Academy

- Planner: Google Maps.
- Endpoints as snapped: Lindisfarne National Nature Reserve, Lindisfarne, to 16 Adams Drive, Spittal, Berwick-upon-Tweed TD15 2JG. Berwick Academy is at TD15 2JF, the adjacent address.
- Route: walk to Kiln Point, bus 918, Northern rail, LNER, then bus B1, 2 hr 4 min.
- Departs 06:20, arrives 08:24. Leave-by is 130 minutes, which exceeds the 90 minute cap, so `planner_departure` reads `beyond cap`.
- Confirmation: a depart-at 06:21 probe returns 09:57 as the earliest arrival.
- Arrive-by URL: https://www.google.com/maps/dir/55.612855,-1.755496/55.755746,-2.002587/data=!4m6!4m5!2m3!6e1!7e2!8j1789547400!3e3?hl=en&gl=uk
- Depart-at URL: https://www.google.com/maps/dir/55.612855,-1.755496/55.755746,-2.002587/data=!4m6!4m5!2m3!6e0!7e2!8j1789539660!3e3?hl=en&gl=uk

### Row 4: 621_333 to URN 121241, Norwich High School for Girls

- Planner: Google Maps.
- Endpoints as snapped: Deer's Glade Caravan and Camping Park, White Post Road, Norwich NR11 7HN, to Tennis Courts, 1 Christchurch Road, Norwich NR2 2AD, which is the school's own site.
- Route: 21 minute walk to Hanworth turn, bus 44A, then bus A excel, 1 hr 29 min.
- Departs 06:59, arrives 08:28. Leave-by is 91 minutes, one minute over the 90 minute cap, so `planner_departure` reads `beyond cap`.
- This row sits on the boundary. Re-check the row by hand if the validator reports a disagreement at this boundary.
- Confirmation: a depart-at 07:00 probe returns 08:35 as the earliest arrival.
- Arrive-by URL: https://www.google.com/maps/dir/52.853404,1.288350/52.618537,1.276055/data=!4m6!4m5!2m3!6e1!7e2!8j1789547400!3e3?hl=en&gl=uk
- Depart-at URL: https://www.google.com/maps/dir/52.853404,1.288350/52.618537,1.276055/data=!4m6!4m5!2m3!6e0!7e2!8j1789542000!3e3?hl=en&gl=uk

## Walking rows

### Row 5: 433_389 to URN 107140, King Edward VII School, Sheffield

- Planner: Google Maps, walking, arrive by 08:30.
- Endpoints as snapped: Hillsborough Works, Hillsborough, Sheffield S6 2LW, to King Edward VII Upper School, 455 Glossop Road, Sheffield S10 2PW.
- Route: 53 min, 2.2 miles via Langsett Road. Alternatives are 54 min and 56 min.
- URL: https://www.google.com/maps/dir/53.401267,-1.497616/53.376217,-1.495747/data=!4m6!4m5!2m3!6e1!7e2!8j1789547400!3e2?hl=en&gl=uk

### Row 6: 352_315 to URN 123608, Shrewsbury School

- Planner: Google Maps, walking, arrive by 08:30.
- Endpoints as snapped: Dell Farm, Sundorne Castle, Uffington, Shrewsbury SY4 4RR, to Activate Camps Shrewsbury, The Schools, Shrewsbury SY3 7BA, which is the Shrewsbury School site.
- Route: 1 hr 36 min, 4.3 miles via National Cycle Route 81. This is 96 minutes, above the 90 minute cap, so expect the stored value to be the sentinel.
- URL: https://www.google.com/maps/dir/52.735036,-2.704913/52.703908,-2.762470/data=!4m6!4m5!2m3!6e1!7e2!8j1789547400!3e2?hl=en&gl=uk

## Cycling rows

### Row 7: 351_253 to URN 117036, Hereford Cathedral School

- Planner: Google Maps, cycling, arrive by 08:30.
- Endpoints as snapped: Hereford Road, Leominster HR6 0PH, to Old Herefordians Club, Hereford Cathedral School, Cathedral Close, Hereford HR1 2NG.
- Route: 55 min, 10.9 miles via the A417. Alternatives are 1 hr 7 min and 1 hr 10 min.
- URL: https://www.google.com/maps/dir/52.177611,-2.710688/52.054504,-2.714726/data=!4m6!4m5!2m3!6e1!7e2!8j1789547400!3e1?hl=en&gl=uk

### Row 8: 419_539 to URN 130657, Bishop Auckland College

- Planner: Google Maps, cycling, arrive by 08:30.
- Endpoints as snapped: West Brandon Road, Crook DL15 9AS, to Bishop Auckland College, Woodhouse Lane, Bishop Auckland DL14 6JZ.
- Route: 51 min, 9.7 miles via Wolsingham Road. Google offers no alternative.
- URL: https://www.google.com/maps/dir/54.750079,-1.698573/54.650921,-1.694936/data=!4m6!4m5!2m3!6e1!7e2!8j1789547400!3e1?hl=en&gl=uk

### Row 9: 191_53 to URN 112076, Truro School

- Planner: Google Maps, cycling, arrive by 08:30.
- Endpoints as snapped: the bare coordinate 50.3444200, -4.9317760, to 7108 Trennick Lane, Truro TR1 1TH, which is the Truro School site.
- Route: 58 min, 10.0 miles via the B3275 and A390. Google offers no alternative.
- URL: https://www.google.com/maps/dir/50.344420,-4.931776/50.260812,-5.042741/data=!4m6!4m5!2m3!6e1!7e2!8j1789547400!3e1?hl=en&gl=uk

## Driving rows

### Row 10: 484_201 to URN 145244, Edgbarrow School

- Planner: Google Maps, driving, arrive by 08:30.
- Endpoints as snapped: The Hampden Arms, Great Hampden, Great Missenden HP16 9RQ, to Edgbarrow Sixth Form, Crowthorne RG45 7JL. The school record gives RG45 7HZ, the same campus.
- Route: 31.9 miles via the A404. Google shows "typically 50 min to 1 hr 20 min" and "Leave at about 7:10 AM", giving 80 minutes to an 08:30 arrival.
- A depart-at 07:10 probe gives "typically 50 min to 1 hr 15 min" and "Arrive at about 8:25 AM", so the range spans bands 5 through 8.
- Arrive-by URL: https://www.google.com/maps/dir/51.705886,-0.778540/51.362986,-0.793744/data=!4m6!4m5!2m3!6e1!7e2!8j1789547400!3e0?hl=en&gl=uk
- Depart-at URL: https://www.google.com/maps/dir/51.705886,-0.778540/51.362986,-0.793744/data=!4m6!4m5!2m3!6e0!7e2!8j1789542600!3e0?hl=en&gl=uk

### Row 11: 192_78 to URN 112076, Truro School

- Planner: Google Maps, driving, arrive by 08:30.
- Endpoints as snapped: the bare coordinate 50.5693070, -4.9315980, to 7108 Trennick Lane, Truro TR1 1TH.
- Route: 31.7 miles via the A39. Google shows "typically 50 min to 1 hr 10 min" and "Leave at about 7:20 AM", giving 70 minutes to an 08:30 arrival.
- A depart-at 07:20 probe confirms "Arrive at about 8:30 AM".
- Arrive-by URL: https://www.google.com/maps/dir/50.569307,-4.931598/50.260812,-5.042741/data=!4m6!4m5!2m3!6e1!7e2!8j1789547400!3e0?hl=en&gl=uk
- Depart-at URL: https://www.google.com/maps/dir/50.569307,-4.931598/50.260812,-5.042741/data=!4m6!4m5!2m3!6e0!7e2!8j1789543200!3e0?hl=en&gl=uk

### Row 12: 623_243 to URN 121242, Norwich School

- Planner: Google Maps, driving, arrive by 08:30.
- Endpoints as snapped: the bare coordinate 52.0448100, 1.2577920, to Leathes Prior Solicitors, 74 The Close, Norwich NR1 4DR. Norwich School is at NR1 4DD on the same close.
- Route: 55.1 miles via the A14 and A140. Google shows "typically 1 hr 20 min to 1 hr 50 min" and "Leave at about 6:40 AM", giving 110 minutes to an 08:30 arrival.
- A depart-at 06:40 probe gives "typically 1 hr 15 min to 1 hr 50 min" and "Arrive at about 8:30 AM".
- Arrive-by URL: https://www.google.com/maps/dir/52.044810,1.257792/52.630824,1.299647/data=!4m6!4m5!2m3!6e1!7e2!8j1789547400!3e0?hl=en&gl=uk
- Depart-at URL: https://www.google.com/maps/dir/52.044810,1.257792/52.630824,1.299647/data=!4m6!4m5!2m3!6e0!7e2!8j1789540800!3e0?hl=en&gl=uk

## Caveats

- Google snapped several origins to a named place near the cell centre rather than to the centre itself. Each snap is recorded above. The largest displacement is row 3, where the label reads "Lindisfarne National Nature Reserve" but the first leg boards at Kiln Point, north of Bamburgh, which matches the cell.
- Nothing was fabricated. Every figure comes from a page that was loaded and read, and no lookup failed.
