# Timetable gaps: first audit for issue #9

Audited on 14 September 2026 using fixtures/audit_feeds.py against /Users/rob/git/find-schools-by-time/motis-spike/feeds/bods.zip, downloaded on 13 September 2026. The feed version is 20260913_022858. Its recorded SHA256 checksum is d69d71ecf6d1cc85ff8a62d6f72b83fdb4f23cd2c6978e7306a2f12c5353f5ec. The complete output is saved locally in motis-spike/bods-gap-audit.txt, including counts for all 635 agencies and all 246 routes whose type is neither bus nor coach.

BODS contains all 11 Underground lines, the Docklands Light Railway, London Trams, the cable car and all seven ferry services named in the spec. The Thames Clippers entries are RB1, RB4 and RB6. Elizabeth line and all six named Overground lines are absent from BODS and await the rail feed from issue #8. No supplement is justified by this first audit alone.

Presence means that a matching route has trip records in the snapshot. It does not establish a sailing before 08:30, service on 16 September 2026, every branch or pier, or a successful journey to a school. Those checks remain for the second half of issue #9. A resolution of "no action, already present" means no additional feed for that observed service; it does not close the routing checks. The rail column stays "pending #8" throughout because no rail zip was available, including for services already settled by BODS.

## Method and counts

Run uv run fixtures/audit_feeds.py /Users/rob/git/find-schools-by-time/motis-spike/feeds/bods.zip from the issue-9-bods-gaps worktree. Run uv run fixtures/audit_feeds.py --check for the in-memory self-test. More zip paths can follow the first path when the rail feed arrives.

The script streams the agency, route and trip tables, keeping the route lookup and counters in memory. It does not open stop_times.txt or shapes.txt. In addition to the spec's route names, it prints route identifiers, trip counts and distinct trip destinations. All 246 non-bus route long names are blank, so destinations help identify crossings. The extra imports are standard library text handling, counters and command-line parsing; there are no new dependencies. Bus and coach filtering follows the [extended route types](https://developers.google.com/transit/gtfs/reference/extended-route-types).

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

The Overground rows use the six names listed by [Transport for London](https://tfl.gov.uk/modes/london-overground/the-new-look-london-overground?intcmp=75267). Operators for present services use the agency names in the snapshot. Transport for London identifies the absent networks without guessing the rail feed's eventual agency labels. Searches covered agency names and all route names, including bus and coach entries; Elizabeth Yule Transport is a bus operator, not evidence of the Elizabeth line.

| Service | Operator | Present in BODS | Present in the rail feed | Resolution |
|---|---|---|---|---|
| London Underground Bakerloo line | London Underground (TfL) | Yes. 1,691 trips on route 10245790. | pending #8 | no action, already present |
| London Underground Central line | London Underground (TfL) | Yes. 7,934 trips on routes 12364313, 12838358. | pending #8 | no action, already present |
| London Underground Circle line | London Underground (TfL) | Yes. 2,449 trips on routes 10245795, 13031477, 13276222. | pending #8 | no action, already present |
| London Underground District line | London Underground (TfL) | Yes. 8,902 trips on routes 12364306, 13031489, 13276236. | pending #8 | no action, already present |
| London Underground Hammersmith & City line | London Underground (TfL) | Yes. 2,256 trips on routes 10245799, 13031462, 13276224. | pending #8 | no action, already present |
| London Underground Jubilee line | London Underground (TfL) | Yes. 3,485 trips on route 10245834. | pending #8 | no action, already present |
| London Underground Metropolitan line | London Underground (TfL) | Yes. 6,639 trips on routes 10245827, 13031473, 13276229. | pending #8 | no action, already present |
| London Underground Northern line | London Underground (TfL) | Yes. 6,135 trips on route 10423673. | pending #8 | no action, already present |
| London Underground Piccadilly line | London Underground (TfL) | Yes. 12,206 trips on routes 10245837, 13031500, 13276263, 13276268. | pending #8 | no action, already present |
| London Underground Victoria line | London Underground (TfL) | Yes. 8,322 trips on routes 10245820, 12838352. | pending #8 | no action, already present |
| London Underground Waterloo & City line | London Underground (TfL) | Yes. 531 trips on route 137823. | pending #8 | no action, already present |
| Docklands Light Railway | London Docklands Light Railway - TfL | Yes. 5,539 trips on routes 10884596, 13031618. | pending #8 | no action, already present |
| London Trams | London Tramlink | Yes. 2,670 trips on routes 13276884, 4069348. | pending #8 | no action, already present |
| Elizabeth line | Transport for London Elizabeth line | No matching agency or route. The only type 2 routes belong to the Docklands Light Railway. | pending #8 | pending #8 |
| London Overground Liberty line | Transport for London London Overground | No matching agency or route. The only type 2 routes belong to the Docklands Light Railway. | pending #8 | pending #8 |
| London Overground Lioness line | Transport for London London Overground | No matching agency or route. The only type 2 routes belong to the Docklands Light Railway. | pending #8 | pending #8 |
| London Overground Mildmay line | Transport for London London Overground | No matching agency or route. The only type 2 routes belong to the Docklands Light Railway. | pending #8 | pending #8 |
| London Overground Suffragette line | Transport for London London Overground | No matching agency or route. The only type 2 routes belong to the Docklands Light Railway. | pending #8 | pending #8 |
| London Overground Weaver line | Transport for London London Overground | No matching agency or route. The only type 2 routes belong to the Docklands Light Railway. | pending #8 | pending #8 |
| London Overground Windrush line | Transport for London London Overground | No matching agency or route. The only type 2 routes belong to the Docklands Light Railway. | pending #8 | pending #8 |
| Thames Clippers river bus | Thames Clippers | Yes. 517 trips on routes 11478119, 11478121, 11478117. | pending #8 | no action, already present |
| London cable car | IFS Cloud Cable Car | Yes. 1,016 trips on route 723057. | pending #8 | no action, already present |
| Portsmouth to Fishbourne | WightLink | Yes. 151 trips on route 222677. | pending #8 | no action, already present |
| Portsmouth Harbour to Ryde Pier | WightLink | Yes. 100 trips on route 92706. | pending #8 | no action, already present |
| Lymington to Yarmouth | WightLink | Yes. 80 trips on route 222679. | pending #8 | no action, already present |
| Southsea to Ryde hovercraft | Hovertravel | Yes. 86 trips on route 141118. | pending #8 | no action, already present |
| Southampton to East Cowes | Red Funnel | Yes. 114 trips on route 222675. | pending #8 | no action, already present |
| Southampton to West Cowes Red Jet | Red Funnel | Yes. 146 trips on route 222676. | pending #8 | no action, already present |
| Mersey ferry between Liverpool Pier Head and Seacombe | Mersey Ferries | Yes. 72 trips on routes 12459557, 12459558. | pending #8 | no action, already present |

## Additional ferry services found

All 115 ferry route records were inspected. The additional rows below retain every identified English ferry service from that list, including local crossings that could form part of a journey to a sixth form. Repeated route records for the same service are grouped in one row. Scottish island and loch services were excluded because they do not provide a local crossing to an English sixth form.

These are candidates based on their location and route descriptions, not claims that each operates early enough for school. Where the feed supplies only a service name, that name is retained rather than inventing its piers. The Plymouth Barbican Ferry remains a separate entry because this audit does not establish that it duplicates another crossing.

| Service | Operator | Present in BODS | Present in the rail feed | Resolution |
|---|---|---|---|---|
| Mount Batten to Plymouth Barbican | Mountbatten Water Taxis | Yes. 228 trips on route 10148609. | pending #8 | no action, already present |
| Bosham Hoe to West Itchenor | Itchenor Ferry | Yes. 72 trips on route 12736258. | pending #8 | no action, already present |
| Shepperton to Weybridge | Nauticalia Ferry | Yes. 207 trips on route 12736259. | pending #8 | no action, already present |
| Bristol Cross Harbour Ferry | Number Seven Boat Trips | Yes. 246 trips on route 1316912. | pending #8 | no action, already present |
| Woolwich Ferry | Woolwich Free Ferry | Yes. 128 trips on route 137948. | pending #8 | no action, already present |
| Flushing to Falmouth | Flushing Ferry | Yes. 158 trips on routes 141084, 141088. | pending #8 | no action, already present |
| St Mawes Ferry | St Mawes Ferry | Yes. 106 trips on routes 141090, 141094. | pending #8 | no action, already present |
| Fowey to Polruan | Polruan Ferry Co Ltd | Yes. 261 trips on route 141093. | pending #8 | no action, already present |
| Cremyll to Plymouth | Plymouth Boat Trips | Yes. 348 trips on routes 141095, 405325. | pending #8 | no action, already present |
| Fowey to Bodinnick | Polruan Passenger Ferry, Bodinnick Vehicle Ferry | Yes. 480 trips on route 222656. | pending #8 | no action, already present |
| Mudeford Ferry | Mudeford Ferry | Yes. 108 trips on route 222667. | pending #8 | no action, already present |
| Tuckton Ferry | Bournemouth Boating Ser | Yes. 54 trips on route 222668. | pending #8 | no action, already present |
| St Mawes to Place | St Mawes Ferry | Yes. 96 trips on route 3080. | pending #8 | no action, already present |
| Torpoint to Plymouth | Tamar Bridge & Torpoint Ferry Joint Committee | Yes. 779 trips on route 3084. | pending #8 | no action, already present |
| Plymouth Barbican to Cawsand | Plymouth Boat Trips | Yes. 36 trips on route 3091. | pending #8 | no action, already present |
| Plymouth Barbican Ferry | Plymouth Boat Trips | Yes. 39 trips on route 3092. | pending #8 | no action, already present |
| Dartmouth Higher Ferry to Kingswear | Dartmouth Higher Ferry | Yes. 378 trips on route 3094. | pending #8 | no action, already present |
| Dartmouth Lower Ferry to Kingswear | River Link | Yes. 464 trips on route 3095. | pending #8 | no action, already present |
| Salcombe to East Portlemouth | Salcombe Ferry | Yes. 138 trips on route 3111. | pending #8 | no action, already present |
| Sandbanks Ferry | Sandbanks Ferry | Yes. 392 trips on route 3171. | pending #8 | no action, already present |
| Cowes Floating Bridge | Cowes Ferry | Yes. 900 trips on route 3213. | pending #8 | no action, already present |
| Gosport to Portsmouth | Gosport-Portsmouth Ferry | Yes. 592 trips on route 3214. | pending #8 | no action, already present |
| Hayling Ferry | Hayling Ferry Limited | Yes. 116 trips on route 3215. | pending #8 | no action, already present |
| Brightlingsea to East Mersea | Brightlingsea Ferry Services | Yes. 30 trips on route 3345290. | pending #8 | no action, already present |
| Harwich Harbour ferry serving Harwich, Felixstowe and Shotley | Harwich Harbour Ferry | Yes. 58 trips on routes 3345291, 9475106. | pending #8 | no action, already present |
| Plymouth to Saltash | Plymouth Boat Trips | Yes. 36 trips on route 3916898. | pending #8 | no action, already present |
| Feock to Philleigh | Fal River Links | Yes. 254 trips on route 405317. | pending #8 | no action, already present |
| Padstow to Rock | Padstow Harbour Commissioners | Yes. 198 trips on route 405331. | pending #8 | no action, already present |
| Shields Ferry between North Shields and South Shields | Nexus Ferry | Yes. 210 trips on route 66999. | pending #8 | no action, already present |
| Bristol Ferry Boats | Bristol Ferry Boat Company | Yes. 36 trips on route 8726042. | pending #8 | no action, already present |
| Felixstowe Foot Ferry | Felixstowe Ferry Boat Yard | Yes. 140 trips on routes 9286766, 9286767. | pending #8 | no action, already present |
| Burnham on Crouch to Wallasea Island | Burnham Ferry | Yes. 60 trips on route 9619885. | pending #8 | no action, already present |
| Mevagissey to Fowey | Mevagissey Ferry | Yes. 24 trips on route 96401. | pending #8 | no action, already present |

## Gaps and remaining checks

The only missing expected services in BODS are the Elizabeth line and the Liberty, Lioness, Mildmay, Suffragette, Weaver and Windrush Overground lines. Each resolution remains "pending #8" until the rail feed is audited. There are no confirmed missing Underground lines or missing ferry services among the comparison rows.

Milestone 1 already found London journeys close to the user's TfL comparison, while rail-dependent journeys were slower. Its seven schools with no transit reach are a separate routing question, not evidence of a missing ferry or Underground line. The Grammar School At Leeds and Lord Wandsworth College remain candidates for coordinate or stop-matching checks recorded on issue #9. No supplement, timetable conversion, graph import or server run was performed for this half.
