# Timetable gaps: issue #9

Audited on 14 September 2026 using fixtures/audit_feeds.py against /Users/rob/git/find-schools-by-time/motis-spike/feeds/bods.zip, downloaded on 13 September 2026. The feed version is 20260913_022858. Its recorded SHA256 checksum is d69d71ecf6d1cc85ff8a62d6f72b83fdb4f23cd2c6978e7306a2f12c5353f5ec. The complete output is saved locally in motis-spike/bods-gap-audit.txt, including counts for all 635 agencies and 99 tram, 29 metro, 2 rail, 115 ferry and 1 aerial lift routes.

BODS contains all 11 Underground lines, the Docklands Light Railway, London Trams, the cable car and all seven ferry services named in the spec. The Thames Clippers entries are RB1, RB4 and RB6. The rail feed supplies the Elizabeth line and all six named Overground lines, which are absent from BODS. No expected service is missing from both feeds.

Presence means that a matching route has trip records in the snapshot. It does not establish every branch or pier. The dated morning checks below establish a complete qualifying trip for each of the eleven Underground lines and seven named crossings; the additional ferry rows remain presence checks. A resolution of "no action, already present" means no additional feed for that observed service; it does not close the routing checks. The rail column records the second audit, using the repaired feed from issue #8. A named corridor establishes presence, not coverage of every branch or date.

## Method and counts

Run uv run fixtures/audit_feeds.py /Users/rob/git/find-schools-by-time/motis-spike/feeds/bods.zip from the issue-9-bods-gaps worktree. Run uv run fixtures/audit_feeds.py --check for the in-memory self-test. More zip paths can follow the first path when the rail feed arrives.

The script streams the agency, route and trip tables, keeping the route lookup and counters in memory. It does not open stop_times.txt or shapes.txt. In addition to the spec's route names, it prints route identifiers, trip counts and distinct trip destinations. All tram, metro, rail, ferry and aerial lift route long names are blank, so destinations help identify crossings. The extra imports are standard library text handling, counters and command-line parsing; there are no new dependencies. Bus and coach filtering follows the [extended route types](https://developers.google.com/transit/gtfs/reference/extended-route-types).

These are counts of route and trip records across the snapshot, not unique public lines or departures on a particular day. They match milestone 1's 13,627 routes and 1,541,556 trips.

| Route type | Meaning | Routes | Trips |
|---|---|---|---|
| 0 | Tram and light rail | 99 | 28,355 |
| 1 | Metro | 29 | 61,989 |
| 2 | Rail | 2 | 5,539 |
| 3 | Bus | 13,135 | 1,403,614 |
| 4 | Ferry | 115 | 21,865 |
| 6 | Aerial lift | 1 | 1,016 |
| 200 | Coach | 246 | 19,178 |

The type 2 records are both Docklands Light Railway, not National Rail. London Underground accounts for 24 route records and 60,550 trips across 11 named lines. The other five type 1 records belong to Tyne and Wear Metro. Contrary to the earlier BODS research note, Glasgow Subway is type 0 in this snapshot. Type 0 also includes heritage railways, airport shuttles and Metrolink replacement buses, so mode totals alone do not establish coverage.

## Expected services

The Overground rows use the six names listed by [Transport for London](https://tfl.gov.uk/modes/london-overground/the-new-look-london-overground?intcmp=75267). Operators for present services use the agency names in the snapshot. The rail feed labels the Elizabeth line agency as TfL Rail and groups all six Overground lines under London Overground; the named lines are identified from their route endpoints. Searches covered agency names and all route names, including bus and coach entries; Elizabeth Yule Transport is a bus operator, not evidence of the Elizabeth line.

| Service | Operator | Present in BODS | Present in the rail feed | Resolution |
|---|---|---|---|---|
| London Underground Bakerloo line | London Underground (TfL) | Yes. 1,691 trips on route 10245790. On 16 September, 75 qualifying complete trips arrive before 08:30. | Partial. London Underground routes 2935 and 2939 have 2,346 trips between Elephant and Castle and Harrow and Wealdstone; other Bakerloo patterns are also present. | no action, already present |
| London Underground Central line | London Underground (TfL) | Yes. 7,934 trips on routes 12364313, 12838358. On 16 September, 140 qualifying complete trips arrive before 08:30. | No separately identified service. Supplied by BODS. | no action, already present |
| London Underground Circle line | London Underground (TfL) | Yes. 2,449 trips on routes 10245795, 13031477, 13276222. On 16 September, 57 qualifying complete trips arrive before 08:30. | No separately identified service. Supplied by BODS. | no action, already present |
| London Underground District line | London Underground (TfL) | Yes. 8,902 trips on routes 12364306, 13031489, 13276236. On 16 September, 166 qualifying complete trips arrive before 08:30. | Partial. London Underground routes 2950 and 2963 have 31 trips between Richmond and Upminster; other District patterns are also present. | no action, already present |
| London Underground Hammersmith & City line | London Underground (TfL) | Yes. 2,256 trips on routes 10245799, 13031462, 13276224. On 16 September, 35 qualifying complete trips arrive before 08:30. | No separately identified service. Supplied by BODS. | no action, already present |
| London Underground Jubilee line | London Underground (TfL) | Yes. 3,485 trips on route 10245834. On 16 September, 114 qualifying complete trips arrive before 08:30. | No separately identified service. Supplied by BODS. | no action, already present |
| London Underground Metropolitan line | London Underground (TfL) | Yes. 6,639 trips on routes 10245827, 13031473, 13276229. On 16 September, 136 qualifying complete trips arrive before 08:30. | No separately identified service. Supplied by BODS. | no action, already present |
| London Underground Northern line | London Underground (TfL) | Yes. 6,135 trips on route 10423673. On 16 September, 211 qualifying complete trips arrive before 08:30. | No separately identified service. Supplied by BODS. | no action, already present |
| London Underground Piccadilly line | London Underground (TfL) | Yes. 12,206 trips on routes 10245837, 13031500, 13276263, 13276268. On 16 September, 205 qualifying complete trips arrive before 08:30. | No separately identified service. Supplied by BODS. | no action, already present |
| London Underground Victoria line | London Underground (TfL) | Yes. 8,322 trips on routes 10245820, 12838352. On 16 September, 154 qualifying complete trips arrive before 08:30. | No separately identified service. Supplied by BODS. | no action, already present |
| London Underground Waterloo & City line | London Underground (TfL) | Yes. 531 trips on route 137823. On 16 September, 83 qualifying complete trips arrive before 08:30. | No separately identified service. Supplied by BODS. | no action, already present |
| Docklands Light Railway | London Docklands Light Railway - TfL | Yes. 5,539 trips on routes 10884596, 13031618. | No separately identified service. Supplied by BODS. | no action, already present |
| London Trams | London Tramlink | Yes. 2,670 trips on routes 13276884, 4069348. | No separately identified service. Supplied by BODS. | no action, already present |
| Elizabeth line | Transport for London Elizabeth line | No matching agency or route. The only type 2 routes belong to the Docklands Light Railway. | Yes. TfL Rail routes 7489 and 7530 have 1,696 trips between Abbey Wood and Reading; Heathrow and Shenfield branches are also present. | no action, already present |
| London Overground Liberty line | Transport for London London Overground | No matching agency or route. The only type 2 routes belong to the Docklands Light Railway. | Yes. Routes 2886 and 2898 have 348 trips between Romford and Upminster. | no action, already present |
| London Overground Lioness line | Transport for London London Overground | No matching agency or route. The only type 2 routes belong to the Docklands Light Railway. | Yes. Routes 2868 and 2902 have 1,981 trips between Euston and Watford Junction. | no action, already present |
| London Overground Mildmay line | Transport for London London Overground | No matching agency or route. The only type 2 routes belong to the Docklands Light Railway. | Yes. Routes 2884 and 2892 have 1,985 trips between Richmond and Stratford; Clapham Junction routes 2836 and 2890 are also present. | no action, already present |
| London Overground Suffragette line | Transport for London London Overground | No matching agency or route. The only type 2 routes belong to the Docklands Light Railway. | Yes. Routes 2818 and 2851 have 1,336 trips between Barking Riverside and Gospel Oak. | no action, already present |
| London Overground Weaver line | Transport for London London Overground | No matching agency or route. The only type 2 routes belong to the Docklands Light Railway. | Yes. Liverpool Street routes 2830, 2831, 2849, 2870, 2871 and 2872 have 6,905 trips serving Cheshunt, Chingford and Enfield Town. | no action, already present |
| London Overground Windrush line | Transport for London London Overground | No matching agency or route. The only type 2 routes belong to the Docklands Light Railway. | Yes. Routes 2861 and 2905 have 1,827 trips between Highbury and Islington and West Croydon; Clapham Junction, Crystal Palace and New Cross branches are also present. | no action, already present |
| Thames Clippers river bus | Thames Clippers | Yes. 517 trips on routes 11478119, 11478121, 11478117. | No separately identified service. Supplied by BODS. | no action, already present |
| London cable car | IFS Cloud Cable Car | Yes. 1,016 trips on route 723057. | No separately identified service. Supplied by BODS. | no action, already present |
| Portsmouth to Fishbourne | WightLink | Yes. 151 trips on route 222677. On 16 September, earliest qualifying departure 03:00 from Portsmouth IOW Car Ferry Terminal, arriving 03:45 at Fishbourne IOW Ferry Terminal. | No separately identified service. Supplied by BODS. | no action, already present |
| Portsmouth Harbour to Ryde Pier | WightLink | Yes. 100 trips on route 92706. On 16 September, earliest qualifying departure 05:15 from Portsmouth Harbour Station Pier, arriving 05:37 at Ryde Pier Head Ferry Terminal. | Yes. South Western Railway ferry routes 5874 and 5875 connect Portsmouth Harbour and Ryde Pier Head. | no action, already present |
| Lymington to Yarmouth | WightLink | Yes. 80 trips on route 222679. On 16 September, earliest qualifying departure 06:05 from Lymington Pier Ferry Terminal, arriving 06:45 at Yarmouth IOW Ferry Terminal. | Yes. South Western Railway ferry routes 5873 and 5876 connect Lymington Pier and Yarmouth. | no action, already present |
| Southsea to Ryde hovercraft | Hovertravel | Yes. 86 trips on route 141118. On 16 September, earliest qualifying departure 06:50 from Southsea Hoverport, arriving 07:00 at Ryde Hoverport. | No separately identified service. Supplied by BODS. | no action, already present |
| Southampton to East Cowes | Red Funnel | Yes. 114 trips on route 222675. On 16 September, earliest qualifying departure 03:00 from Southampton Vehicle Ferry Terminal, arriving 04:00 at East Cowes Ferry Terminal. | No separately identified service. Supplied by BODS. | no action, already present |
| Southampton to West Cowes Red Jet | Red Funnel | Yes. 146 trips on route 222676. On 16 September, earliest qualifying departure 05:30 from Southampton Passenger Ferry Terminal, arriving 05:55 at Red Jet Ferry Terminal. | No separately identified service. Supplied by BODS. | no action, already present |
| Mersey ferry between Liverpool Pier Head and Seacombe | Mersey Ferries | Yes. 72 trips on routes 12459557, 12459558. On 16 September, earliest qualifying departure 07:20 from Seacombe Ferry Terminal, arriving 07:30 at Gerry Marsden Ferry Terminal. | No separately identified service. Supplied by BODS. | no action, already present |

## Additional ferry services found

All 115 ferry route records were inspected. The additional rows below retain every identified English ferry service from that list, including local crossings that could form part of a journey to a sixth form. Repeated route records for the same service are grouped in one row. Scottish island and loch services were excluded because they do not provide a local crossing to an English sixth form.

These are candidates based on their location and route descriptions, not claims that each operates early enough for school. Where the feed supplies only a service name, that name is retained rather than inventing its piers. The Plymouth Barbican Ferry remains a separate entry because this audit does not establish that it duplicates another crossing.

| Service | Operator | Present in BODS | Present in the rail feed | Resolution |
|---|---|---|---|---|
| Mount Batten to Plymouth Barbican | Mountbatten Water Taxis | Yes. 228 trips on route 10148609. | No separately identified service. Supplied by BODS. | no action, already present |
| Bosham Hoe to West Itchenor | Itchenor Ferry | Yes. 72 trips on route 12736258. | No separately identified service. Supplied by BODS. | no action, already present |
| Shepperton to Weybridge | Nauticalia Ferry | Yes. 207 trips on route 12736259. | No separately identified service. Supplied by BODS. | no action, already present |
| Bristol Cross Harbour Ferry | Number Seven Boat Trips | Yes. 246 trips on route 1316912. | No separately identified service. Supplied by BODS. | no action, already present |
| Woolwich Ferry | Woolwich Free Ferry | Yes. 128 trips on route 137948. | No separately identified service. Supplied by BODS. | no action, already present |
| Flushing to Falmouth | Flushing Ferry | Yes. 158 trips on routes 141084, 141088. | No separately identified service. Supplied by BODS. | no action, already present |
| St Mawes Ferry | St Mawes Ferry | Yes. 106 trips on routes 141090, 141094. | No separately identified service. Supplied by BODS. | no action, already present |
| Fowey to Polruan | Polruan Ferry Co Ltd | Yes. 261 trips on route 141093. | No separately identified service. Supplied by BODS. | no action, already present |
| Cremyll to Plymouth | Plymouth Boat Trips | Yes. 348 trips on routes 141095, 405325. | No separately identified service. Supplied by BODS. | no action, already present |
| Fowey to Bodinnick | Polruan Passenger Ferry, Bodinnick Vehicle Ferry | Yes. 480 trips on route 222656. | No separately identified service. Supplied by BODS. | no action, already present |
| Mudeford Ferry | Mudeford Ferry | Yes. 108 trips on route 222667. | No separately identified service. Supplied by BODS. | no action, already present |
| Tuckton Ferry | Bournemouth Boating Ser | Yes. 54 trips on route 222668. | No separately identified service. Supplied by BODS. | no action, already present |
| St Mawes to Place | St Mawes Ferry | Yes. 96 trips on route 3080. | No separately identified service. Supplied by BODS. | no action, already present |
| Torpoint to Plymouth | Tamar Bridge & Torpoint Ferry Joint Committee | Yes. 779 trips on route 3084. | No separately identified service. Supplied by BODS. | no action, already present |
| Plymouth Barbican to Cawsand | Plymouth Boat Trips | Yes. 36 trips on route 3091. | No separately identified service. Supplied by BODS. | no action, already present |
| Plymouth Barbican Ferry | Plymouth Boat Trips | Yes. 39 trips on route 3092. | No separately identified service. Supplied by BODS. | no action, already present |
| Dartmouth Higher Ferry to Kingswear | Dartmouth Higher Ferry | Yes. 378 trips on route 3094. | No separately identified service. Supplied by BODS. | no action, already present |
| Dartmouth Lower Ferry to Kingswear | River Link | Yes. 464 trips on route 3095. | No separately identified service. Supplied by BODS. | no action, already present |
| Salcombe to East Portlemouth | Salcombe Ferry | Yes. 138 trips on route 3111. | No separately identified service. Supplied by BODS. | no action, already present |
| Sandbanks Ferry | Sandbanks Ferry | Yes. 392 trips on route 3171. | No separately identified service. Supplied by BODS. | no action, already present |
| Cowes Floating Bridge | Cowes Ferry | Yes. 900 trips on route 3213. | No separately identified service. Supplied by BODS. | no action, already present |
| Gosport to Portsmouth | Gosport-Portsmouth Ferry | Yes. 592 trips on route 3214. | No separately identified service. Supplied by BODS. | no action, already present |
| Hayling Ferry | Hayling Ferry Limited | Yes. 116 trips on route 3215. | No separately identified service. Supplied by BODS. | no action, already present |
| Brightlingsea to East Mersea | Brightlingsea Ferry Services | Yes. 30 trips on route 3345290. | No separately identified service. Supplied by BODS. | no action, already present |
| Harwich Harbour ferry serving Harwich, Felixstowe and Shotley | Harwich Harbour Ferry | Yes. 58 trips on routes 3345291, 9475106. | No separately identified service. Supplied by BODS. | no action, already present |
| Plymouth to Saltash | Plymouth Boat Trips | Yes. 36 trips on route 3916898. | No separately identified service. Supplied by BODS. | no action, already present |
| Feock to Philleigh | Fal River Links | Yes. 254 trips on route 405317. | No separately identified service. Supplied by BODS. | no action, already present |
| Padstow to Rock | Padstow Harbour Commissioners | Yes. 198 trips on route 405331. | No separately identified service. Supplied by BODS. | no action, already present |
| Shields Ferry between North Shields and South Shields | Nexus Ferry | Yes. 210 trips on route 66999. | No separately identified service. Supplied by BODS. | no action, already present |
| Bristol Ferry Boats | Bristol Ferry Boat Company | Yes. 36 trips on route 8726042. | No separately identified service. Supplied by BODS. | no action, already present |
| Felixstowe Foot Ferry | Felixstowe Ferry Boat Yard | Yes. 140 trips on routes 9286766, 9286767. | No separately identified service. Supplied by BODS. | no action, already present |
| Burnham on Crouch to Wallasea Island | Burnham Ferry | Yes. 60 trips on route 9619885. | No separately identified service. Supplied by BODS. | no action, already present |
| Mevagissey to Fowey | Mevagissey Ferry | Yes. 24 trips on route 96401. | No separately identified service. Supplied by BODS. | no action, already present |

## Gaps and remaining checks

The seven expected services absent from BODS are supplied by rail: the Elizabeth line and the Liberty, Lioness, Mildmay, Suffragette, Weaver and Windrush Overground lines. Every comparison row is present in at least one feed and resolves to no action, already present. The eleven Underground lines and seven named crossings also pass the dated morning check. No supplement is required; the two routing responses are recorded below.

Milestone 1 already found London journeys close to the user's TfL comparison, while rail-dependent journeys were slower. Its seven schools with no transit reach are a separate routing question, not evidence of a missing ferry or Underground line. The two school checks requested in the issue comments are settled for this feed audit: The Grammar School At Leeds has nearby BODS stops, while Lord Wandsworth College has none within 1 km. They remain routing, local access or coordinate questions rather than evidence of a missing feed; the measured counts are below. The second half uses the existing combined graph from issue #8 for the two routing checks below.

## Rail audit

The second audit used uv run fixtures/audit_feeds.py /Users/rob/git/find-schools-by-time/motis-spike/feeds/rail.zip. The complete output is saved locally as motis-spike/rail-gap-audit.txt. The feed has SHA256 7652de90bda13dbf80947a48e831be48796ec92fce3fa20058993566d9d2e43e and was built as recorded in the Rail GTFS section of NOTES.md. Counts cover the full calendar. The row evidence gives representative routes rather than claiming that their trip totals describe an entire public line.

| Route type | Meaning | Routes | Trips |
|---|---|---|---|
| 1 | Metro | 54 | 6,556 |
| 2 | Rail | 5,218 | 440,577 |
| 3 | Bus | 2,229 | 81,102 |
| 4 | Ferry | 45 | 919 |

All 45 rail-feed ferry routes were inspected. Of the comparison rows, the rail feed supplies Portsmouth Harbour to Ryde Pier Head and Lymington to Yarmouth. Its other ferry routes serve Scotland, Wales, Ireland, the Isle of Man, the Isles of Scilly or the Netherlands; they do not add another local crossing to an English sixth form to this comparison list. The rail feed's partial Underground records do not replace the named lines in BODS. Its London Trams and Docklands Light Railway services are not separately identified.

## Morning service on Wednesday 16 September

The check joins calendar bounds and weekday flags with calendar_dates additions and removals, then selects the requested routes through trips and streams the full stop_times table. It checks complete boardable trips whose last permitted alighting time is before 08:30, with departure at or after midnight. Tuesday service expressed with times beyond 24:00 is included when it falls on Wednesday; Wednesday service after 24:00 is excluded. The Underground rows report qualifying trip counts from bods-morning-audit.json rather than midnight departures. The earliest departure in each crossing row runs toward the Isle of Wight, except the Mersey row, which runs from Seacombe toward Liverpool. The opposite direction also has qualifying trips for all seven crossings.

Run uv run fixtures/check_morning.py --check for the calendar, cancellation, overnight and ordering checks. Run uv run fixtures/check_morning.py /Users/rob/git/find-schools-by-time/motis-spike/feeds/bods.zip followed by the Underground and seven crossing route identifiers in the comparison rows to reproduce the scan. The complete result is saved locally in motis-spike/bods-morning-audit.json. The scanner stores only selected trip endpoints, rather than the 5.1 GB stop-times table. These are timetable checks, not a guarantee of operation or school reachability from every departure.

All eleven Underground lines have at least one complete qualifying trip. All seven named crossings have sailings in both directions arriving before 08:30. The Mersey commuter service is route 12459557; the other Mersey route need not operate that morning for the crossing to be covered. No new raw input or supplement is needed, so there is no new licence row, manifest entry, dataset configuration or import.

## Routing checks

The existing combined graph from issue #8 was served from motis-spike with ./motis server -d data.rail. No graph was renamed, overwritten or reimported. Requests used GET /api/v6/plan with arriveBy=true and timetableView=false, and time=2026-09-16T08:30:00%2B01%3A00. The older spec's version 1 endpoint and graph-renaming instructions have been corrected to match the tested version 6 API and separate configuration and data directories.

Ryde School with Upper Chine is present in schools.json, establishment 118223, at latitude 50.72824 and longitude -1.167747. The island request ran from Portsmouth Harbour station, 50.7967,-1.1082, to that school. The London request ran from Oxford Circus, 51.5152,-0.1419, to Canary Wharf, 51.5054,-0.0235. Both returned HTTP 200 in about 0.03 seconds and two itineraries each, saved locally as motis-spike/gap-plan-island.json and motis-spike/gap-plan-london.json.

The first island itinerary meets the ferry check, reaching Ryde School at 08:28. The Canary Wharf itineraries are secondary observations; the Underground done-when check is the Oxford Circus to Brixton journey below. The London response also offers the Elizabeth line via a walk to Bond Street, so this example does not uniquely favour the Underground; its Underground-only alternative does not establish the required choice of destination. All legs of both returned alternatives are recorded below. Times are British Summer Time on Wednesday 16 September 2026.

### Island itinerary 1

Departure 07:29, arrival 08:28.

| Leg | Mode | Route name | Dataset | Departure | Arrival |
|---|---|---|---|---|---|
| START to The Hard Interchange | Walk | Street walk | OpenStreetMap | 07:29 | 07:35 |
| The Hard Interchange to Clarence Pier | Bus | 25 | BODS | 07:35 | 07:47 |
| Clarence Pier to Southsea Hoverport | Walk | Street walk | OpenStreetMap | 07:47 | 07:49 |
| Southsea Hoverport to Ryde Hoverport | Ferry | IOW Hovercraft | BODS | 08:00 | 08:10 |
| Ryde Hoverport to Transport Interchange | Walk | Street walk | OpenStreetMap | 08:10 | 08:12 |
| Transport Interchange to Parish Church | Bus | 9 | BODS | 08:20 | 08:26 |
| Parish Church to END | Walk | Street walk | OpenStreetMap | 08:26 | 08:28 |

### Island itinerary 2

Departure 07:31, arrival 08:28.

| Leg | Mode | Route name | Dataset | Departure | Arrival |
|---|---|---|---|---|---|
| START to The Hard Interchange | Walk | Street walk | OpenStreetMap | 07:31 | 07:37 |
| The Hard Interchange to Kings Road Junction | Bus | 3 | BODS | 07:37 | 07:41 |
| Kings Road Junction to Kings Road Junction | Walk | Street walk | OpenStreetMap | 07:41 | 07:43 |
| Kings Road Junction to Hovertravel Stop | Bus | H1 | BODS | 07:45 | 07:47 |
| Hovertravel Stop to Southsea Hoverport | Walk | Street walk | OpenStreetMap | 07:47 | 07:49 |
| Southsea Hoverport to Ryde Hoverport | Ferry | IOW Hovercraft | BODS | 08:00 | 08:10 |
| Ryde Hoverport to Transport Interchange | Walk | Street walk | OpenStreetMap | 08:10 | 08:12 |
| Transport Interchange to Parish Church | Bus | 9 | BODS | 08:20 | 08:26 |
| Parish Church to END | Walk | Street walk | OpenStreetMap | 08:26 | 08:28 |

### London itinerary 1

Departure 07:55, arrival 08:28.

| Leg | Mode | Route name | Dataset | Departure | Arrival |
|---|---|---|---|---|---|
| START to BOND STREET | Walk | Street walk | OpenStreetMap | 07:55 | 08:07 |
| BOND STREET to CANARY WHARF | Regional rail | Train from Heathrow Terminal 4 to ABBEY WOOD (CROSSRAIL) | Rail | 08:07 | 08:21 |
| CANARY WHARF to END | Walk | Street walk | OpenStreetMap | 08:21 | 08:28 |

### London itinerary 2

Departure 07:57, arrival 08:30.

| Leg | Mode | Route name | Dataset | Departure | Arrival |
|---|---|---|---|---|---|
| START to Oxford Circus Underground Station | Walk | Street walk | OpenStreetMap | 07:57 | 08:02 |
| Oxford Circus Underground Station to Waterloo Underground Station | Underground | Bakerloo | BODS | 08:02 | 08:09 |
| Waterloo Underground Station to Waterloo Underground Station | Walk | Street walk | OpenStreetMap | 08:09 | 08:11 |
| Waterloo Underground Station to Canary Wharf Underground Station | Underground | Jubilee | BODS | 08:11 | 08:22 |
| Canary Wharf Underground Station to END | Walk | Street walk | OpenStreetMap | 08:22 | 08:30 |

The ferry is the BODS Hovertravel service from Southsea Hoverport to Ryde Hoverport, 08:00 to 08:10. Its trip identifier is 20260916_08:00_bods_VJ95d556bad01ac9c3462626362b50be5630fa4205. The secondary Canary Wharf Underground-only itinerary uses Bakerloo from Oxford Circus at 08:02 to Waterloo at 08:09, then Jubilee from Waterloo at 08:11 to Canary Wharf at 08:22. Both transit legs identify London Underground as their agency and carry the BODS namespace in their trip and stop identifiers. Walking and interchange time bring the final arrival to 08:30.

No genuine gap was found among the comparison rows, so no supplement was built. The additional ferry services remain presence checks; this audit does not assert a school-morning timetable for all of them. Issue #8 separately recorded the removal of 42 calls at the Barnstaple station bus stop on the test date; that bus-stop coverage question is outside this London and ferry comparison and remains an explicit limitation.

Both script self-checks, all 58 Python unit tests and the JavaScript sorting checks pass. The controlled server was stopped after both requests. No MOTIS executable remains; the final process check is recorded in the scratch notes.

## Schools with no transit reach in milestone 1

The check streamed BODS stops and counted records within a straight-line distance of 1 km of each coordinate in schools.json, using the same spherical distance calculation as fixtures/check_rail.py. The saved result is motis-spike/gap-school-stops.json. These counts establish local stop presence, not a timetable or walking connection to the school entrance.

| School | Establishment number | Latitude | Longitude | BODS stops within 1 km | Conclusion |
|---|---|---|---|---|---|
| The Grammar School At Leeds | 108113 | 53.864173 | -1.5194 | 16 | Nearby stops are present; investigate routing, stop matching or the school coordinate. |
| Lord Wandsworth College | 116521 | 51.214423 | -0.929437 | 0 | This is the school with no stop within 1 km; investigate local access and the school coordinate. |

Both are settled as routing or coordinate questions for this audit, rather than feed gaps requiring a supplement. This does not diagnose the precise reason for the milestone 1 routing results.

## Underground done-when: Oxford Circus to Brixton

The definitive Underground check uses Oxford Circus, 51.5152,-0.1419, to Brixton, 51.4627,-0.1145. The request was GET /api/v6/plan?fromPlace=51.5152,-0.1419&toPlace=51.4627,-0.1145&time=2026-09-16T08:30:00%2B01%3A00&arriveBy=true&timetableView=false. It returned HTTP 200 in 0.03 seconds with one itinerary, saved as motis-spike/gap-plan-brixton.json. It departs at 08:10 and arrives at 08:29, with a single Victoria line transit leg. All times below are British Summer Time on 16 September 2026.

| Leg | Mode | Route name | Dataset | Departure | Arrival |
|---|---|---|---|---|---|
| Start coordinate to Oxford Circus Underground Station | Walk | Street walk | OpenStreetMap | 08:10 | 08:16 |
| Oxford Circus Underground Station to Brixton Underground Station | Underground | Victoria | BODS | 08:16 | 08:28 |
| Brixton Underground Station to destination coordinate | Walk | Street walk | OpenStreetMap | 08:28 | 08:29 |

The transit agency is London Underground (TfL), its trip identifier is 20260916_07:55_bods_VJd4e0aade9f539bbcbb21ad0865ab3e7a5259ab5c, and its stop identifiers are bods_9400ZZLUOXC6 and bods_9400ZZLUBXN1. This itinerary establishes the Underground done-when alongside the previously recorded Ryde School ferry journey. The server ran as ./motis server -d data.rail in a controlled foreground terminal and was stopped after the request; pgrep -fl motis then returned no output.
