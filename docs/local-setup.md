# Local setup for the precompute

What is installed on the user's Mac and where the large inputs and graphs live. None of this is in the repository. Read this before rerunning the rail conversion, an import, or the precompute.

## Rail conversion tooling (issue #8)

Installed with Homebrew: the `r` formula (4.6.1, not the CRAN cask, which needs an administrator password), plus `udunits`, `gdal`, `geos`, `proj`, `abseil` and `cmake`, which the `sf`, `s2`, `units` and `RcppParallel` R packages need. UK2GTFS came from GitHub master with `remotes::install_github("ITSleeds/UK2GTFS", upgrade = "never")`; the installed commit is recorded in `LICENSES/README.md`. The first install attempt failed on the missing libraries above; the second succeeded.

Rerunning the conversion needs only `Rscript fixtures/rail_cif_to_gtfs.R data/timetable_full motis-spike/feeds/rail.zip` from the repository root, after deleting any existing `rail.zip`.

## Inputs and graphs on disk

The raw inputs (MOTIS 2.11.3 binary, the BODS zip, the OpenStreetMap England extract and the nine National Rail CIF files) are listed with sizes and checksums in `fixtures/feed-manifest.json`; `uv run fixtures/check_manifest.py .` verifies them. They live under `motis-spike/` and `data/`, both gitignored.

Graphs under `motis-spike/`: `data/` (BODS only, milestone 1), `data.run1/` (the first milestone 1 import) and `data.rail/` (BODS plus rail, built with `./motis import -c config.rail.yml -d data.rail`). Nothing was renamed. No supplement feed was needed, so the feed set for the precompute is `bods.zip` plus `rail.zip`.

Serve the combined graph from `motis-spike/` with `./motis server -d data.rail`. The server reads `data.rail/config.yml`, not the `config.rail.yml` used for the import. The three limits the precompute raises in that file are `onetomany_max_many`, `routing_max_timeout_seconds` and `max_max_matching_distance`.

## Cloudflare

Wrangler runs as `npx --yes wrangler@4.131.1` and is logged in to the user's account. The OAuth login covers R2; there is no separate R2 scope. The site's hostname is schooltraveltime.cynexia.com and the R2 bucket and anything else created for it is named for that hostname.

## Scratch notes

`motis-spike/NOTES.md` is the gitignored running record of every measurement and command from the spike onwards. Anything not committed elsewhere is there.
