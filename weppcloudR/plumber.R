#* @apiTitle WEPPcloudR Renderer
#* @apiDescription Minimal Plumber service that renders WEPPcloud reports.

suppressPackageStartupMessages({
  library(jsonlite)
  library(glue)
  library(logger)
})

PRIMARY_RUN_ROOT <- Sys.getenv("PRIMARY_RUN_ROOT", "/geodata/weppcloud_runs")
PARTITIONED_RUN_ROOT <- Sys.getenv("PARTITIONED_RUN_ROOT", "/wc1/runs")
BATCH_ROOT <- Sys.getenv("BATCH_ROOT", "/wc1/batch")
TEMPLATE_ROOT <- Sys.getenv("TEMPLATE_ROOT", "/srv/weppcloudr/templates")
DEFAULT_TEMPLATE <- Sys.getenv("DEVAL_TEMPLATE", file.path(TEMPLATE_ROOT, "new_report.Rmd"))

resolve_batch_run_root <- function(batch_name, runid) {
  batch_dir <- file.path(BATCH_ROOT, batch_name)
  if (!dir.exists(batch_dir)) {
    return(NULL)
  }
  if (identical(runid, "_base")) {
    return(file.path(batch_dir, "_base"))
  }
  file.path(batch_dir, "runs", runid)
}

resolve_run_root <- function(runid) {
  if (grepl(";;", runid, fixed = TRUE)) {
    tokens <- strsplit(runid, ";;", fixed = TRUE)[[1]]
    if (length(tokens) == 3 && identical(tokens[1], "batch")) {
      return(resolve_batch_run_root(tokens[2], tokens[3]))
    }
    return(NULL)
  }
  primary_path <- file.path(PRIMARY_RUN_ROOT, runid)
  if (dir.exists(primary_path)) {
    return(primary_path)
  }
  prefix <- substr(runid, 1, min(2, nchar(runid)))
  partitioned_path <- file.path(PARTITIONED_RUN_ROOT, prefix, runid)
  if (dir.exists(partitioned_path)) {
    return(partitioned_path)
  }
  NULL
}

resolve_run_dir <- function(runid, config, pup = NULL) {
  root <- resolve_run_root(runid)
  if (is.null(root)) {
    return(NULL)
  }
  if (!is.null(pup) && nzchar(pup)) {
    pups_root <- file.path(root, "_pups")
    if (!dir.exists(pups_root)) {
      return(NULL)
    }
    candidate <- normalizePath(file.path(pups_root, pup), winslash = "/", mustWork = FALSE)
    if (is.na(candidate) || !dir.exists(candidate)) {
      return(NULL)
    }
    pups_root_norm <- normalizePath(pups_root, winslash = "/", mustWork = TRUE)
    if (!(identical(candidate, pups_root_norm) || startsWith(candidate, paste0(pups_root_norm, "/")))) {
      return(NULL)
    }
    return(candidate)
  }
  candidate <- file.path(root, config)
  if (dir.exists(candidate)) {
    return(candidate)
  }
  if (dir.exists(root)) {
    return(root)
  }
  NULL
}

render_deval <- function(run_path, runid) {
  template_path <- DEFAULT_TEMPLATE
  if (!file.exists(template_path)) {
    log_warn("Template {template_path} not found; returning placeholder HTML")
    return("<html><body><h3>DEVAL report template missing</h3></body></html>")
  }
  output_dir <- file.path(run_path, "export", "WEPPcloudR")
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  output_file <- file.path(output_dir, glue("deval_{runid}.htm"))
  params <- list(proj_runid = runid)
  log_info("Rendering DEVAL report", runid = runid, template = template_path, output = output_file)
  rmarkdown::render(
    input = template_path,
    params = params,
    output_file = output_file,
    output_dir = output_dir,
    envir = new.env(parent = globalenv())
  )
  readChar(output_file, file.info(output_file)$size, useBytes = TRUE)
}

#* Health probe
#* @serializer json
#* @get /healthz
function() {
  list(status = "ok", timestamp = format(Sys.time(), tz = "UTC"))
}

#* Render DEVAL Details report
#* Render DEVAL Details report
#* @serializer html
#* @get /runs/<runid>/<config>/report/deval_details
function(runid, config, res, pup = NULL) {
  run_path <- resolve_run_dir(runid, config, pup)
  if (is.null(run_path)) {
    res$status <- 404
    return(glue("<html><body><h3>Run not found: {runid}/{config}</h3></body></html>"))
  }
  tryCatch(
    render_deval(run_path, runid),
    error = function(err) {
      log_error("Render failed: {err$message}", runid = runid, config = config)
      res$status <- 500
      glue("<html><body><h3>Render error</h3><pre>{err$message}</pre></body></html>")
    }
  )
}
