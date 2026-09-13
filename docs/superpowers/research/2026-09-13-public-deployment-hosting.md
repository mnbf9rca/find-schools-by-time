1. **Pick MOTIS 2, with a benchmark before committing to nationwide generation.** Assessed 13 September 2026; pin [MOTIS 2.11.3](https://github.com/motis-project/motis/releases/tag/v2.11.3). It has a usable experimental transit matrix API. OTP 2 explicitly omits OTP 1’s analysis/isochrone features and recommends R5 for analytics; ordinary OTP journey requests are the wrong foundation for this batch. [OTP’s position](https://docs.opentripplanner.org/en/latest/Analysis/).

   No reproducible, current England/all-timetables benchmark was found. These are **provisioning estimates, not measured requirements**, assuming 16–32 cores, local NVMe, no map tiles/geocoder/elevation:

   | Engine | RAM to provision | Scratch disk | Graph/index allowance | Initial import allowance |
   |---|---:|---:|---:|---:|
   | MOTIS 2 | 64 GB; investigate 32 GB after measuring | 200 GB | 10–40 GB | 1–6 hours |
   | OTP 2 | 128 GB; investigate 64 GB after measuring | 300 GB | 20–60 GB | 2–12 hours |

   Sizing anchors: [OTP documents](https://docs.opentripplanner.org/en/latest/System-Requirements/) just over 10 GB for Finland and 95 GB for Germany. MOTIS’s [OSR street component](https://github.com/motis-project/osr) advertises ≤10 GB RAM for planet import, but that excludes timetable import, transfers and concurrent queries. England’s [OSM PBF](https://download.geofabrik.de/europe/united-kingdom/england.html) is currently **1,693,160,170 bytes**. Border journeys may require the larger Great Britain extract.

2. **Acquire and validate feeds before renting compute.**

   **BODS:** operators publish TransXChange 2.4 XML; use the ready-made **GTFS Schedule ZIP**, not GTFS-Realtime. The [national URL](https://data.bus-data.dft.gov.uk/timetable/download/gtfs-file/all/) returned HTTP 200, `application/zip`, filename `itm_all_gtfs.zip`. Independently inspected the downloaded 13 September snapshot: **1,344,428,986 bytes compressed; 7,814,544,886 uncompressed**, including 5.07 GB `stop_times.txt` and 2.52 GB `shapes.txt`. Its 13,627 routes include 115 ferry, 99 tram/light-rail and 29 metro routes; its only two type-2 rail routes are DLR. **National Rail still needs adding.** BODS timetables are [OGL data](https://findtransportdata.dft.gov.uk/dataset/bus-open-data---published-bus-timetables-1833b69a181).

   The supplied [bods repository’s download code](https://github.com/department-for-transport-BODS/bods/blob/main/transit_odp/browse/views/timetable_views.py) serves an external API/S3 export; it is not a standalone converter. However, DfT’s separate **[bods-integrated-data](https://github.com/department-for-transport-BODS/bods-integrated-data#readme)** explicitly documents open-source TransXChange→GTFS mapping, BODS/TNDS ingestion and national `all_gtfs.zip` generation. It needs NOC, NaPTAN, NPTG, PostgreSQL/Aurora and AWS; GTFS export is documented as unavailable locally. **Download the result; do not recreate this platform.**

   **Traveline National Dataset:** registered FTP access, regional ZIPs containing TXC **2.1 and 2.5**, normally rebuilt Monday–Thursday nights; GB bus, tram, light rail and ferry coverage. [Feed](https://www.travelinedata.org.uk/traveline-open-data/traveline-national-dataset/), [OGL attribution](https://tfl.gov.uk/corporate/data-sources). BODS’s [download-page source](https://github.com/department-for-transport-BODS/bods/blob/main/transit_odp/browse/templates/browse/timetables/download_timetables.html) confirms TNDS supplementation and GB-wide coverage. Do not import TNDS wholesale again.

   **Rail:** obtain the passenger timetable/CIF package described by [RDG](https://www.raildeliverygroup.com/our-services/essential-services/rail-data/timetable-data.html), through its current data-product access process. The historical `data.atoc.org` host did not resolve during this check. [Rail Data Marketplace](https://www.raildeliverygroup.com/our-services/essential-services/rail-data-marketplace.html) has product-specific agreements: do not assume every product is OGL. Alternatively use [Network Rail SCHEDULE](https://www.networkrail.co.uk/who-we-are/transparency-and-ethics/transparency/open-data-feeds/) under its [Data Feeds Licence/OGL](https://www.networkrail.co.uk/who-we-are/transparency-and-ethics/transparency/). Convert CIF with R package **UK2GTFS**: [`atoc2gtfs()`](https://itsleeds.github.io/UK2GTFS/reference/atoc2gtfs.html) for RDG packages, [`nr2gtfs()`](https://itsleeds.github.io/UK2GTFS/reference/nr2gtfs.html) for Network Rail CIF. These supply improved TIPLOC coordinates. Preserve public pickup/set-down rules, overlays, cancellations and interchange times. Darwin XML is a different feed, not CIF.

   **TfL/ferries:** audit the BODS snapshot first. Supplement missing London services using the registered [Journey Planner timetable feed](https://tfl.gov.uk/info-for/open-data-users/our-open-data): Underground, buses, DLR, tram, cable car and river; standard schedules exclude engineering works. TXC supplements use [`transxchange2gtfs()`](https://itsleeds.github.io/UK2GTFS/reference/transxchange2gtfs.html). TfL’s [Transport Data Service terms](https://tfl.gov.uk/corporate/transparency/) and attribution apply. Its “station topology GTFS” is not a timetable. TNDS ferry coverage is not proof every operator/sailing is present: check Isle of Wight and other required crossings, obtaining missing licensed operator schedules. OSM ferry ways alone supply no sailing calendar. MOTIS [accepts GTFS/NeTEx, not native TransXChange](https://github.com/motis-project/motis/blob/v2.11.3/README.md). Retain [OSM attribution/ODbL obligations](https://www.openstreetmap.org/copyright).

3. **Build once, query locally, retain reproducible inputs.** Following the [MOTIS quick start](https://github.com/motis-project/motis/blob/v2.11.3/README.md), on Linux x86-64:

   ```sh
   mkdir -p england-batch/feeds
   cd england-batch
   curl -fL -o motis.tar.bz2 https://github.com/motis-project/motis/releases/download/v2.11.3/motis-linux-amd64.tar.bz2
   tar xf motis.tar.bz2
   curl -fL -o england.osm.pbf https://download.geofabrik.de/europe/united-kingdom/england-latest.osm.pbf
   curl -fL -o feeds/bods.zip https://data.bus-data.dft.gov.uk/timetable/download/gtfs-file/all/
   # Put converted rail and genuinely missing supplements in feeds/.
   ./motis config england.osm.pbf feeds/*.zip
   ```

   Before import, edit generated `config.yml`: `server.host: 127.0.0.1`, `street_routing: true`, `osr_footpath: true`, `geocoding: false`; omit `tiles`. Under `timetable`, set `railviz: false`, `with_shapes: false`, explicit `first_day` and `num_days` spanning the chosen date. Under `limits`, set `onetoall_max_travel_minutes: 240`; tune `onetomany_max_many` upward from **128** only after benchmarking. [Configuration](https://github.com/motis-project/motis/blob/v2.11.3/docs/setup.md).

   ```sh
   /usr/bin/time -v ./motis import
   ./motis server
   ```

   Example transit matrix, school=`one`, origins=`many`; POST coordinates use commas:

   ```sh
   curl -f http://localhost:8080/api/experimental/one-to-many-intermodal \
     -H 'Content-Type: application/json' --data-binary '{
     "one":"51.51,-0.12","many":["51.50,-0.10","51.52,-0.11"],
     "time":"2026-09-16T08:30:00+01:00","arriveBy":true,
     "maxTravelTime":240,"transitModes":["TRANSIT"],
     "preTransitModes":["WALK"],"postTransitModes":["WALK"],
     "maxPreTransitTime":900,"maxPostTransitTime":900,
     "directMode":"WALK","maxDirectTime":14400,"useRoutedTransfers":true}'
   ```

   Take minimum `duration` from each `transit_durations` Pareto set; values are seconds, transit resolution minutes. Walking is separately in `street_durations`. Street-only GET `/api/v1/one-to-many` uses `one=lat;lon`, `many=lat;lon,lat;lon`, `mode=WALK|BIKE|CAR`, `max=14400`, `maxMatchingDistance=250`, `arriveBy=true`. Stop-only GET `/api/v6/one-to-all` uses `one=lat,lon`, `time`, `arriveBy=true`, `maxTravelTime=240`; it does not return a grid. [Pinned API](https://github.com/motis-project/motis/blob/v2.11.3/openapi.yaml).

   OTP alternative: place PBF/GTFS files in `otp-data`; with the release JAR and recommended Java 25:

   ```sh
   java -Xmx100G -jar otp-shaded-2.10.0.jar --build --save otp-data
   java -Xmx100G -jar otp-shaded-2.10.0.jar --load otp-data
   ```

   [Build instructions](https://docs.opentripplanner.org/en/latest/Basic-Tutorial/). POST JSON `{"query":"…"}` to [`/otp/gtfs/v1`](https://docs.opentripplanner.org/en/latest/apis/GTFS-GraphQL-API/); GraphQL [`planConnection`](https://docs.opentripplanner.org/api/dev-2.x/graphql-gtfs/queries/planConnection) takes `origin`/`destination` → `location.coordinate.latitude/longitude`, and `dateTime:{latestArrival:"2026-09-16T08:30:00+01:00"}`. It remains point-to-point.

4. **Use a temporary Hetzner VM, or an already-owned large Mac.**

   | Option | Practical cost and limitation |
   |---|---|
   | Hetzner CCX43 | 16 dedicated vCPU, 64 GB, 360 GB NVMe; **€0.4423/hour**, €2.65/6 hours, €10.62/24 hours, excluding VAT/IPv4. CCX53: 32 vCPU/128 GB, €0.855/hour. |
   | Home Mac | Native `macos-arm64` MOTIS binary; prefer 64 GB RAM and 200 GB free SSD. Existing hardware costs electricity only: illustrative 100 W × 8 hours × £0.25/kWh = **£0.20**. Prevent sleep; avoid Docker’s extra VM memory constraint. |
   | Fly.io London | `performance-8x`, 64 GB: **$0.7692/hour**; six hours $4.62 plus a 200 GB volume ≈$0.25 for six hours. Volume retention costs $30/month; delete after export. |
   | Cloudflare Containers | Standard maximum **4 vCPU/12 GiB/20 GB**: insufficient provisioning headroom. Fully busy standard-4 is ≈$0.401/hour before allowances/other charges; cheap CPU does not solve memory limits. |
   | GitHub Actions | Public Linux: 4 vCPU/16 GB/14 GB disk; private: 2 vCPU/8 GB/14 GB. All hosted jobs stop at **6 hours**. Paid larger runners exist, but standard runners are unsuitable. |

   Sources: [Hetzner specs](https://www.hetzner.com/cloud/general-purpose/), [June 2026 prices](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/), [Fly pricing](https://fly.io/docs/about/pricing/), [Containers limits](https://developers.cloudflare.com/containers/platform/limits/)/[pricing](https://developers.cloudflare.com/containers/platform/pricing/), [GitHub specifications](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)/[job limits](https://docs.github.com/en/actions/reference/limits). Upload outputs, then delete rented compute; stopping Hetzner instances does not end billing.

5. **Runtime: allow days initially; “a few hours” needs measurement.** There are **17,492 school/mode sweeps**, but ≈130,000 cells produce **568,490,000 school–cell pairs per mode**. At the default 128 destinations, four modes require **17,771,872 batch requests** without pruning. Increasing batches avoids repeated transit sweeps, but MOTIS’s [implementation](https://github.com/motis-project/motis/blob/v2.11.3/src/endpoints/one_to_many.cc) still calculates access paths for every destination after one shared transit search.

   Sensitivity estimates, **not benchmarks**: 17,492 complete sweeps at 1–10 seconds each, with eight effective parallel workers, take **0.6–6.1 hours**, plus import/export. However, 568 million uncached grid-to-stop calculations at an assumed 1–10 ms each already take **20–197 hours** on eight workers. Budget roughly **1–10 days for an unoptimised full-grid run**; do not promise termly six-hour jobs. Cache reusable grid-to-stop access only if profiling warrants engine integration; first try conservative geographic pruning and larger batches.

   Benchmark 100 geographically varied schools, all modes and realistic candidate cells; measure peak RAM and elapsed time at 1/4/8 concurrent requests. Scale by 43.73. Select an actual school-term weekday, preserve calendars, test transfers/ferries and compare sampled journeys. Reverse searches must **arrive at school**, not depart it. Static driving lacks rush-hour traffic; termly snapshots miss subsequent timetable changes.

6. **Serve versioned per-origin records from R2.** Use EPSG:27700 1 km cells, or England’s **33,755 Census-2021 LSOAs** with population-weighted centroids. [ONS geography](https://www.ons.gov.uk/methodology/geography/ukgeographies/statisticalgeographies). The ≈130,000-cell count is a planning assumption; generate an actual land/population mask.

   Keep a shared school-index dictionary. Dense unsigned-16-bit seconds, four modes, sentinel 65535: **34,984 bytes/cell**; **4.548 GB** for 130,000 cells or **1.181 GB** for LSOAs, before compression. Sparse records `(uint16 schoolIndex, four uint16 durations)` use 10 bytes/reachable-school entry: 100–500 entries imply **1–5 KB/cell**, illustrative until measured. Gzipped JSON is easier to inspect but larger; stream-transpose school results into cell files rather than retaining the whole matrix in RAM.

   Keys: `version/cell-id.bin`; manifest records date, timezone, feeds/checksums, modes, thresholds and unreachable convention. R2 Standard includes **10 GB storage, 1 million writes and 10 million reads/month**, with free egress; one dense version fits. [R2 pricing](https://developers.cloudflare.com/r2/pricing/). KV’s included storage is only **1 GB**, then $0.50/GB-month: use R2, optionally KV for the current manifest. [KV pricing](https://developers.cloudflare.com/kv/platform/pricing/). Publish a version only after validating counts and samples. Clearly label centroid travel times as approximate: barriers and rural LSOAs can cause substantial postcode-level error.
