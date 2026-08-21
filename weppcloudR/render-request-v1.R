#!/usr/bin/env Rscript

# One-shot entrypoint for Kubernetes Jobs. The control plane fixes both
# arguments and independently supplies the trusted digest.
suppressPackageStartupMessages(library(jsonlite))

fail <- function(message, status = 2L) {
  write(message, stderr())
  quit(save = "no", status = status, runLast = FALSE)
}

main <- function() {
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 3L) {
  fail("expected request path, trusted SHA-256 digest, and fencing generation")
}
request_path <- args[[1L]]
trusted_digest <- args[[2L]]
fencing_generation <- suppressWarnings(as.integer(args[[3L]]))
if (is.na(fencing_generation) || fencing_generation < 1L) {
  fail("invalid fencing generation")
}
if (!identical(request_path, "/run/weppcloudr/request.json")) {
  fail("unexpected request path")
}
if (!grepl("^[0-9a-f]{64}$", trusted_digest)) {
  fail("invalid trusted request digest")
}
if (!file.exists(request_path) || file.info(request_path)$isdir || Sys.readlink(request_path) != "") {
  fail("request is missing or is not a regular non-symlink file")
}
if (file.info(request_path)$size > 16384L) {
  fail("request exceeds 16 KiB")
}

digest_output <- system2(
  "sha256sum",
  args = request_path,
  stdout = TRUE,
  stderr = TRUE
)
if (!identical(attr(digest_output, "status"), NULL) && attr(digest_output, "status") != 0L) {
  fail("could not digest request")
}
actual_digest <- strsplit(digest_output[[1L]], "[[:space:]]+")[[1L]][[1L]]
if (!identical(actual_digest, trusted_digest)) {
  fail("request digest mismatch")
}

request <- tryCatch(
  fromJSON(request_path, simplifyVector = FALSE),
  error = function(error) fail("request is not valid JSON")
)
required_fields <- c(
  "schema_version", "rq_job_id", "runid", "config", "run_root",
  "active_root", "skip_cache", "correlation_id", "deployment_revision",
  "renderer_image_digest"
)
if (!identical(sort(names(request)), sort(required_fields))) {
  fail("request fields do not match schema version 1")
}
if (!is.numeric(request$schema_version) || length(request$schema_version) != 1L || request$schema_version != 1) {
  fail("unsupported request schema version")
}
if (!is.logical(request$skip_cache) || length(request$skip_cache) != 1L) {
  fail("skip_cache must be boolean")
}
if (!is.character(request$rq_job_id) || nchar(request$rq_job_id, type = "bytes") > 64L ||
    !grepl("^[A-Za-z0-9_.-]+$", request$rq_job_id)) {
  fail("invalid RQ job ID")
}
if (!is.character(request$runid) || nchar(request$runid, type = "bytes") > 245L ||
    request$runid %in% c("", ".", "..") || grepl("[/\\]", request$runid)) {
  fail("invalid run ID")
}
if (!is.character(request$config) || nchar(request$config, type = "bytes") > 255L ||
    !nzchar(request$config) || !grepl("^[A-Za-z0-9_.-]+$", request$config)) {
  fail("invalid configuration identifier")
}
if (!is.character(request$correlation_id) || !nzchar(request$correlation_id) ||
    nchar(request$correlation_id, type = "bytes") > 128L) {
  fail("invalid correlation identifier")
}
if (!is.character(request$deployment_revision) || !nzchar(request$deployment_revision) ||
    nchar(request$deployment_revision, type = "bytes") > 128L) {
  fail("invalid deployment revision")
}
if (!is.character(request$renderer_image_digest) ||
    !grepl("^sha256:[0-9a-f]{64}$", request$renderer_image_digest)) {
  fail("invalid renderer image digest")
}
if (!is.character(request$run_root) || !is.character(request$active_root) ||
    !startsWith(request$run_root, "/") || !startsWith(request$active_root, "/")) {
  fail("run paths must be absolute strings")
}

run_root <- normalizePath(request$run_root, winslash = "/", mustWork = TRUE)
active_root <- normalizePath(request$active_root, winslash = "/", mustWork = TRUE)
allowed_roots <- strsplit(
  Sys.getenv("WEPPCLOUDR_RUN_ROOTS", "/wc1/runs:/geodata/weppcloud_runs:/wc1/batch:/wc1/culverts"),
  ":",
  fixed = TRUE
)[[1L]]
allowed_roots <- vapply(
  allowed_roots,
  normalizePath,
  character(1L),
  winslash = "/",
  mustWork = FALSE
)
within <- function(path, parent) identical(path, parent) || startsWith(path, paste0(parent, "/"))
if (!any(vapply(allowed_roots, function(root) within(run_root, root), logical(1L)))) {
  fail("run working directory is outside approved roots")
}
if (!within(active_root, run_root)) {
  fail("active root escapes run working directory")
}
if (!identical(normalizePath(getwd(), winslash = "/", mustWork = TRUE), run_root)) {
  fail("process working directory does not match request run root")
}

source("/srv/weppcloudr/plumber.R")
output_dir <- file.path(active_root, "export", "WEPPcloudR")
if (Sys.readlink(file.path(active_root, "export")) != "" || Sys.readlink(output_dir) != "") {
  fail("output path contains a symlink")
}
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
final_output <- file.path(output_dir, paste0("deval_", request$runid, ".htm"))
fence_file <- file.path(
  active_root,
  "_locks",
  "weppcloudr",
  paste0("deval_", request$runid, ".fence")
)
read_fence <- function() {
  if (!file.exists(fence_file) || Sys.readlink(fence_file) != "") {
    fail("trusted fencing record is unavailable")
  }
  value <- suppressWarnings(as.integer(trimws(readLines(fence_file, n = 1L, warn = FALSE))))
  if (is.na(value)) fail("trusted fencing record is invalid")
  value
}
if (read_fence() != fencing_generation) {
  fail("render fencing generation is stale")
}
emit_receipt <- function(artifact_digest = NULL, artifact_size = NULL) {
  if (is.null(artifact_size)) artifact_size <- file.info(final_output)$size
  if (is.null(artifact_digest)) {
    artifact_digest <- strsplit(
      system2("sha256sum", args = shQuote(final_output), stdout = TRUE)[[1L]],
      "[[:space:]]+"
    )[[1L]][[1L]]
  }
  write(
    toJSON(
      list(
        schema_version = 1L,
        rq_job_id = request$rq_job_id,
        request_digest = trusted_digest,
        state = "terminal-success",
        artifact_path = final_output,
        artifact_sha256 = artifact_digest,
        artifact_size = artifact_size,
        fencing_generation = fencing_generation
      ),
      auto_unbox = TRUE
    ),
    stdout()
  )
}
parse_artifact_identity <- function(output) {
  result <- strsplit(output[[1L]], "[[:space:]]+")[[1L]]
  if (length(result) != 2L || !grepl("^[0-9a-f]{64}$", result[[1L]])) {
    fail("fenced artifact helper returned invalid identity")
  }
  size <- suppressWarnings(as.numeric(result[[2L]]))
  if (is.na(size) || size < 1) fail("fenced artifact helper returned invalid size")
  list(digest = result[[1L]], size = size)
}
if (!request$skip_cache && file.exists(final_output) && Sys.readlink(final_output) == "") {
  cached_status <- system2(
    "python3",
    args = c(
      "/srv/weppcloudr/publish_fenced.py",
      shQuote(active_root),
      shQuote(request$runid),
      as.character(fencing_generation),
      "-"
    ),
    stdout = TRUE,
    stderr = TRUE
  )
  if (!is.null(attr(cached_status, "status")) && attr(cached_status, "status") != 0L) {
    fail("fenced cached artifact verification failed")
  }
  cached_identity <- parse_artifact_identity(cached_status)
  emit_receipt(cached_identity$digest, cached_identity$size)
  return(invisible(NULL))
}
temporary_output <- file.path(
  "/tmp",
  paste0(".deval_", request$runid, ".", request$rq_job_id, ".tmp.htm")
)
on.exit(unlink(temporary_output, force = TRUE), add = TRUE)
invisible(render_deval(
  active_root,
  request$runid,
  request$config,
  skip_cache = TRUE,
  output_file_override = temporary_output
))
if (!file.exists(temporary_output) || Sys.readlink(temporary_output) != "") {
  fail("renderer did not produce a regular temporary artifact")
}
output_dir_now <- normalizePath(output_dir, winslash = "/", mustWork = TRUE)
if (!identical(output_dir_now, file.path(active_root, "export", "WEPPcloudR")) ||
    Sys.readlink(file.path(active_root, "export")) != "" || Sys.readlink(output_dir) != "" ||
    Sys.readlink(final_output) != "") {
  fail("output path changed before publication")
}
publication_status <- system2(
  "python3",
  args = c(
    "/srv/weppcloudr/publish_fenced.py",
    shQuote(active_root),
    shQuote(request$runid),
    as.character(fencing_generation),
    shQuote(basename(temporary_output))
  ),
  stdout = TRUE,
  stderr = TRUE
)
status_code <- attr(publication_status, "status")
if (!is.null(status_code) && status_code != 0L) {
  fail("atomic fenced report publication failed")
}
published_identity <- parse_artifact_identity(publication_status)
emit_receipt(published_identity$digest, published_identity$size)
invisible(NULL)
}

main()
