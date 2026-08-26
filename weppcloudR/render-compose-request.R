#!/usr/bin/env Rscript

# Fixed stdin-driven adapter for Docker Compose. Caller values are data and are
# never interpolated into R source.
suppressPackageStartupMessages(library(jsonlite))

fail <- function(message) {
  write(message, stderr())
  quit(save = "no", status = 2L, runLast = FALSE)
}

main <- function() {
payload_text <- paste(readLines(file("stdin"), warn = FALSE), collapse = "\n")
if (nchar(payload_text, type = "bytes") > 16384L) {
  fail("Compose render request exceeds 16 KiB")
}
payload <- tryCatch(
  fromJSON(payload_text, simplifyVector = FALSE),
  error = function(error) fail("Compose render request is invalid JSON")
)
required <- c("run_path", "runid", "config", "skip_cache", "fencing_generation")
if (!identical(sort(names(payload)), sort(required))) {
  fail("Compose render request fields are invalid")
}
if (!is.character(payload$run_path) || length(payload$run_path) != 1L ||
    !startsWith(payload$run_path, "/")) {
  fail("Compose run path is invalid")
}
if (!is.character(payload$runid) || length(payload$runid) != 1L ||
    payload$runid %in% c("", ".", "..") || grepl("[/\\]", payload$runid)) {
  fail("Compose run ID is invalid")
}
if (!is.character(payload$config) || length(payload$config) != 1L ||
    !nzchar(payload$config) || !grepl("^[A-Za-z0-9_.-]+$", payload$config)) {
  fail("Compose config is invalid")
}
if (!is.logical(payload$skip_cache) || length(payload$skip_cache) != 1L) {
  fail("Compose skip_cache is invalid")
}
fencing_generation <- suppressWarnings(as.integer(payload$fencing_generation))
if (is.na(fencing_generation) || fencing_generation < 1L) {
  fail("Compose fencing generation is invalid")
}
if (identical(Sys.getenv("WEPPCLOUDR_CONTRACT_PROBE"), "1")) {
  write(toJSON(list(protocol = 1L, accepted = TRUE), auto_unbox = TRUE), stdout())
  quit(save = "no", status = 0L, runLast = FALSE)
}

run_path <- normalizePath(payload$run_path, winslash = "/", mustWork = TRUE)
approved_roots <- strsplit(
  Sys.getenv(
    "WEPPCLOUDR_RUN_ROOTS",
    "/wc1/runs:/geodata/weppcloud_runs:/wc1/batch:/wc1/culverts"
  ),
  ":",
  fixed = TRUE
)[[1L]]
approved_roots <- vapply(
  approved_roots,
  normalizePath,
  character(1L),
  winslash = "/",
  mustWork = FALSE
)
within <- function(path, parent) identical(path, parent) || startsWith(path, paste0(parent, "/"))
if (!any(vapply(approved_roots, function(root) within(run_path, root), logical(1L)))) {
  fail("Compose run path is outside approved roots")
}

output_dir <- file.path(run_path, "export", "WEPPcloudR")
if (Sys.readlink(file.path(run_path, "export")) != "" || Sys.readlink(output_dir) != "") {
  fail("Compose output path contains a symlink")
}
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
final_output <- file.path(output_dir, paste0("deval_", payload$runid, ".htm"))
fence_file <- file.path(
  run_path,
  "_locks",
  "weppcloudr",
  paste0("deval_", payload$runid, ".fence")
)
if (!file.exists(fence_file) || Sys.readlink(fence_file) != "") {
  fail("Compose fencing record is unavailable")
}
if (!payload$skip_cache && file.exists(final_output) && Sys.readlink(final_output) == "") {
  quit(save = "no", status = 0L, runLast = FALSE)
}
temporary_output <- tempfile(
  pattern = paste0(".deval_", payload$runid, "."),
  tmpdir = "/tmp",
  fileext = ".tmp.htm"
)
on.exit(unlink(temporary_output, force = TRUE), add = TRUE)

source("/srv/weppcloudr/plumber.R")
invisible(render_deval(
  run_path,
  payload$runid,
  payload$config,
  skip_cache = TRUE,
  output_file_override = temporary_output
))
publication_status <- system2(
  "python3",
  args = c(
    "/srv/weppcloudr/publish_fenced.py",
    shQuote(run_path),
    shQuote(payload$runid),
    as.character(fencing_generation),
    shQuote(basename(temporary_output))
  ),
  stdout = TRUE,
  stderr = TRUE
)
status_code <- attr(publication_status, "status")
if (!is.null(status_code) && status_code != 0L) {
  fail("atomic fenced Compose report publication failed")
}
invisible(NULL)
}

main()
