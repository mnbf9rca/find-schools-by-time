#!/usr/bin/env Rscript

check <- function() {
  calendar <- data.frame(service_id = c("run", "cancel", "outside", "unused"),
                         start_date = c(20260901, 20260901, 20261001, 20260901),
                         end_date = 20261231, wednesday = 1)
  exceptions <- data.frame(service_id = c("cancel", "extra", "outside"),
                           date = c(20260916, 20260916, 20260917),
                           exception_type = c(2, 1, 1))
  trips <- data.frame(service_id = c("run", "cancel", "outside", "extra"))
  stopifnot(active_trips(list(calendar = calendar, calendar_dates = exceptions,
                             trips = trips)) == 2)
  calendar$wednesday <- 0
  stopifnot(active_trips(list(calendar = calendar, trips = trips)) == 0)
  broken <- list(
    trips = data.frame(trip_id = "t"),
    stops = data.frame(stop_id = c("A", "B"), stop_lat = c(51, NA), stop_lon = 0),
    stop_times = data.frame(trip_id = "t", stop_id = c("A", "A", "B", "missing"),
                            arrival_time = c("10:01:30", "25:00:00", "10:00:00", "10:00:00"),
                            departure_time = c("10:01:00", "25:01:00", "10:00:00", "10:00:00")),
    transfers = data.frame(from_stop_id = c("A", "A", "missing"), to_stop_id = c("A", "B", "A")))
  repaired <- repair(broken)
  stopifnot(nrow(repaired$stops) == 1, nrow(repaired$stop_times) == 2,
            nrow(repaired$transfers) == 1,
            identical(repaired$stop_times$departure_time, c("10:01:30", "25:01:00")))
  for (remaining in 0:1) {
    short <- broken
    short$stop_times$stop_id[seq_len(2 - remaining)] <- "B"
    failure <- tryCatch({ repair(short); NULL }, error = identity)
    stopifnot(inherits(failure, "error"), grepl("at least two stop times", conditionMessage(failure)))
  }
  cat("Rail conversion checks passed\n")
}

active_trips <- function(gtfs) {
  calendar <- gtfs$calendar
  active <- with(calendar, service_id[start_date <= 20260916 &
                                      end_date >= 20260916 & wednesday == 1])
  exceptions <- gtfs$calendar_dates
  if (!is.null(exceptions)) {
    today <- exceptions[exceptions$date == 20260916, ]
    active <- union(active, today$service_id[today$exception_type == 1])
    active <- setdiff(active, today$service_id[today$exception_type == 2])
  }
  sum(gtfs$trips$service_id %in% active)
}

repair <- function(gtfs) {
  keep <- is.finite(gtfs$stops$stop_lat) & is.finite(gtfs$stops$stop_lon)
  cat("Stops dropped without coordinates:", sum(!keep), "\n")
  gtfs$stops <- gtfs$stops[keep, ]
  keep <- gtfs$stop_times$stop_id %in% gtfs$stops$stop_id
  cat("Stop times dropped without a located stop:", sum(!keep), "\n")
  cat("Missing stop identifiers:", unique(gtfs$stop_times$stop_id[!keep]), "\n")
  gtfs$stop_times <- gtfs$stop_times[keep, ]
  if (any(table(factor(gtfs$stop_times$trip_id, levels = gtfs$trips$trip_id)) < 2L)) stop("Every trip must retain at least two stop times")
  keep <- gtfs$transfers$from_stop_id %in% gtfs$stops$stop_id &
          gtfs$transfers$to_stop_id %in% gtfs$stops$stop_id
  cat("Transfers dropped without both stops:", sum(!keep), "\n")
  gtfs$transfers <- gtfs$transfers[keep, ]
  # Public boarding times can precede the fallback working arrival at pickup-only stops.
  earlier <- gtfs$stop_times$departure_time < gtfs$stop_times$arrival_time
  cat("Departures raised to arrival:", sum(earlier), "\n")
  gtfs$stop_times$departure_time[earlier] <- gtfs$stop_times$arrival_time[earlier]
  gtfs
}

main <- function(args) {
  if (length(args) != 2 || !grepl("[.]zip$", args[2]))
    stop("Usage: Rscript fixtures/rail_cif_to_gtfs.R <cif-directory> <output-zip>")
  output <- file.path(normalizePath(dirname(args[2]), mustWork = TRUE), basename(args[2]))
  if (file.exists(output)) stop("Output already exists: ", output)
  staged <- tempfile("rail-cif-")
  dir.create(staged)
  on.exit(unlink(staged, recursive = TRUE), add = TRUE)
  for (ext in c("MCA", "MSN", "FLF")) {
    input <- list.files(args[1], pattern = paste0(ext, "[.]txt$"), full.names = TRUE)
    if (length(input) != 1) stop("Expected exactly one ", ext, ".txt file")
    if (!file.copy(input, file.path(staged, paste0("rail.", tolower(ext)))))
      stop("Could not stage ", input)
  }
  options(UK2GTFS_opt_updateCachedDataOnLibaryLoad = FALSE)
  library(UK2GTFS)
  cat(R.version.string, "\nUK2GTFS commit", packageDescription("UK2GTFS")$RemoteSha, "\n")
  for (table in c("tiplocs", "atoc_agency")) {
    path <- system.file("extdata", paste0(table, ".rda"), package = "UK2GTFS")
    cat(table, digest::digest(file = path, algo = "sha256"), "\n")
  }
  zip::zipr(file.path(staged, "input.zip"), list.files(staged, full.names = TRUE))
  # Worker R sessions must disable cache updates before loading UK2GTFS too.
  profile <- file.path(staged, "worker.R")
  writeLines("options(UK2GTFS_opt_updateCachedDataOnLibaryLoad = FALSE)", profile)
  Sys.setenv(R_PROFILE_USER = profile)
  gtfs <- atoc2gtfs(file.path(staged, "input.zip"), public_only = TRUE,
                   working_timetable = FALSE, transfers = TRUE, missing_tiplocs = TRUE,
                   locations = "tiplocs", agency = "atoc_agency", shapes = FALSE, ncores = 4)
  gtfs <- repair(gtfs)
  gtfs_validate_internal(gtfs)
  count <- active_trips(gtfs)
  cat("Trips on 2026-09-16:", count, "\n")
  if (count == 0) stop("No trips run on 2026-09-16")
  print(vapply(gtfs, nrow, integer(1)))
  cached <- new.env()
  load(system.file("extdata", "tiplocs.rda", package = "UK2GTFS"), envir = cached)
  cat("MSN fallback stops:", setdiff(gtfs$stops$stop_id, cached[[ls(cached)[1]]]$stop_id), "\n")
  gtfs_write(gtfs, folder = dirname(output), name = tools::file_path_sans_ext(basename(output)))
  cat("Output bytes:", file.info(output)$size, "\n")
}

if (identical(commandArgs(TRUE), "--check")) check() else main(commandArgs(TRUE))
