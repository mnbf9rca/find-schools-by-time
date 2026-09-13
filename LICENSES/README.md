# Licences

Verbatim licence texts live in this folder, one file per licence, named by SPDX identifier. This table maps each thing the project uses to its licence and to the attribution that must appear on the page. Add a row here before using a new data source, API or tool.

| Item | Licence | Attribution shown on the page | Conditions |
|---|---|---|---|
| This project's code | [MIT](MIT.txt) | none | |
| Get Information About Schools (establishment data in `schools.json`) | [OGL-UK-3.0](OGL-UK-3.0.txt) | Contains public sector information licensed under the Open Government Licence v3.0. | GIAS acceptable use policy: do not combine with other data to create or infer personal data. Never add head teacher or contact columns. |
| A level and other 16 to 18 results, 2024/25 (Explore Education Statistics) | [OGL-UK-3.0](OGL-UK-3.0.txt) | Source: Department for Education, A level and other 16 to 18 results, 2024/25. | Show suppressed values as not published, not as zero. |
| postcodes.io geocoding (ONS Postcode Directory, OS Open Names, Royal Mail) | OS OpenData terms, OGL | Contains OS data © Crown copyright and database right 2025. Contains Royal Mail data © Royal Mail copyright and database right 2025. Contains National Statistics data © Crown copyright and database right 2025. | Northern Ireland postcodes need a separate commercial licence; restrict to Great Britain. |
| Bus Open Data Service national GTFS, supplemented by Traveline National Dataset | [OGL-UK-3.0](OGL-UK-3.0.txt) | Timetable data from the Bus Open Data Service and Traveline National Dataset, licensed under the Open Government Licence v3.0. | Pending: not yet used. |
| National Rail timetable (Rail Delivery Group, Rail Data Marketplace, "Timetable - Full Refresh - Weekly", RSPS5046 CIF) | [Rail Data Marketplace Data Sharing Agreement](RDM-Data-Sharing-Agreement-Timetable-Full-Refresh-Weekly.txt), Open licence fee type, free. | Rail timetable data from Rail Delivery Group via the Rail Data Marketplace. Rail Delivery Group does not endorse this site. | Schedule 1 permits use "for research & analysis purposes only". On 2026-09-13, the user accepted this project's precomputed travel-time table as analysis; that decision is settled. Clause 3.3.2 requires an accuracy notice on onward distribution; clause 3.3.3 requires reporting defects to the publisher. The one-year term renews automatically with one month's notice. Data may be retained after the term. Territory: UK and Europe. |
| OpenStreetMap England extract (street network for routing) | [ODbL-1.0](ODbL-1.0.txt) | © OpenStreetMap contributors. | Share-alike: a precomputed travel-time table derived from OSM may itself have to be offered under ODbL. Pending: not yet used. |
| MOTIS 2 (routing engine, run offline) | MIT | none | No obligation on output. Pending: not yet used. |
| UK2GTFS (rail timetable conversion, run offline) | [GPL-3.0-only](GPL-3.0-only.txt) | none | Run as a tool; output is not a derived work. Pending: not yet used. |
| pyproj (coordinate conversion in the build) | MIT | none | Build-time only. |
| TravelTime API (current local version only) | TravelTime terms of service | Travel times by TravelTime | Free plan is evaluation only and forbids end users; not usable for the public site. |
