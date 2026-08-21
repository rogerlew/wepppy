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
CULVERTS_ROOT <- Sys.getenv("CULVERTS_ROOT", "/wc1/culverts")
PROFILE_PLAYBACK_BASE <- Sys.getenv("PROFILE_PLAYBACK_BASE", "/workdir/wepppy-test-engine-data/playback")
PROFILE_PLAYBACK_RUN_ROOT <- Sys.getenv("PROFILE_PLAYBACK_RUN_ROOT", file.path(PROFILE_PLAYBACK_BASE, "runs"))
PROFILE_PLAYBACK_FORK_ROOT <- Sys.getenv("PROFILE_PLAYBACK_FORK_ROOT", file.path(PROFILE_PLAYBACK_BASE, "fork"))
PROFILE_PLAYBACK_ARCHIVE_ROOT <- Sys.getenv("PROFILE_PLAYBACK_ARCHIVE_ROOT", file.path(PROFILE_PLAYBACK_BASE, "archive"))
TEMPLATE_ROOT <- Sys.getenv("TEMPLATE_ROOT", "/srv/weppcloudr/templates")
DEFAULT_TEMPLATE <- Sys.getenv("DEVAL_TEMPLATE", file.path(TEMPLATE_ROOT, "new_report.Rmd"))
FONTAWESOME_JS <- Sys.getenv(
  "FONTAWESOME_JS",
  "/srv/weppcloudr/vendor/fontawesome/5.3.1/all.js"
)
FONTAWESOME_SHA256 <- "8cb270b4d9485a93b31df98113fda8723ffc067fa7bfa90cedd47b76f7b10be1"

fontawesome_header <- function() {
  if (!file.exists(FONTAWESOME_JS) || file.info(FONTAWESOME_JS)$isdir) {
    stop("vendored Font Awesome asset is unavailable")
  }
  link_target <- Sys.readlink(FONTAWESOME_JS)
  if (!is.na(link_target) && nzchar(link_target)) {
    stop("vendored Font Awesome asset must not be a symlink")
  }
  digest_output <- system2(
    "sha256sum",
    shQuote(FONTAWESOME_JS),
    stdout = TRUE,
    stderr = TRUE
  )
  if (!is.null(attr(digest_output, "status")) && attr(digest_output, "status") != 0L) {
    stop("could not verify vendored Font Awesome asset")
  }
  digest <- strsplit(digest_output[[1L]], "[[:space:]]+")[[1L]][[1L]]
  if (!identical(digest, FONTAWESOME_SHA256)) {
    stop("vendored Font Awesome asset checksum mismatch")
  }
  header <- tempfile(pattern = "fontawesome-5.3.1-", fileext = ".html")
  writeLines(
    c("<script>", readLines(FONTAWESOME_JS, warn = FALSE), "</script>"),
    header,
    useBytes = TRUE
  )
  header
}

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

resolve_primary_run_root <- function(runid) {
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

resolve_profile_run_root <- function(profile_type, runid) {
  candidate <- switch(
    profile_type,
    "tmp" = file.path(PROFILE_PLAYBACK_RUN_ROOT, runid),
    "fork" = file.path(PROFILE_PLAYBACK_FORK_ROOT, runid),
    "archive" = file.path(PROFILE_PLAYBACK_ARCHIVE_ROOT, runid),
    NULL
  )
  if (is.null(candidate)) {
    return(NULL)
  }
  if (dir.exists(candidate)) {
    return(candidate)
  }
  NULL
}

resolve_run_root <- function(runid) {
  if (is.null(runid) || !nzchar(runid)) {
    return(NULL)
  }
  if (grepl(";;", runid, fixed = TRUE)) {
    tokens <- strsplit(runid, ";;", fixed = TRUE)[[1]]
    if (length(tokens) >= 3) {
      suffix_group <- tokens[length(tokens) - 1]
      suffix_id <- tokens[length(tokens)]
      if (suffix_group %in% c("omni", "omni-contrast")) {
        parent_runid <- paste(tokens[1:(length(tokens) - 2)], collapse = ";;")
        parent_root <- resolve_run_root(parent_runid)
        if (is.null(parent_root)) {
          return(NULL)
        }
        child_dir <- if (identical(suffix_group, "omni")) "scenarios" else "contrasts"
        candidate <- file.path(parent_root, "_pups", "omni", child_dir, suffix_id)
        if (dir.exists(candidate)) {
          return(candidate)
        }
        return(NULL)
      }
    }
    if (length(tokens) == 3 && identical(tokens[1], "batch")) {
      return(resolve_batch_run_root(tokens[2], tokens[3]))
    }
    if (length(tokens) == 3 && identical(tokens[1], "culvert")) {
      culvert_path <- file.path(CULVERTS_ROOT, tokens[2], "runs", tokens[3])
      if (dir.exists(culvert_path)) {
        return(culvert_path)
      }
      return(NULL)
    }
    if (length(tokens) == 3 && identical(tokens[1], "profile")) {
      return(resolve_profile_run_root(tokens[2], tokens[3]))
    }
    return(NULL)
  }
  resolve_primary_run_root(runid)
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

extract_source_location <- function(trace) {
  calls <- trace$calls
  if (is.null(calls) || !length(calls)) {
    return(NULL)
  }
  for (idx in rev(seq_along(calls))) {
    call <- calls[[idx]]
    sr <- attr(call, "srcref")
    if (is.null(sr)) {
      next
    }
    srcfile <- attr(sr, "srcfile")
    filename <- tryCatch(srcfile$filename, error = function(e) NULL)
    if (is.null(filename) || !nzchar(filename)) {
      next
    }
    line <- tryCatch(as.integer(sr[[1]]), error = function(e) NA_integer_)
    column <- tryCatch({
      if (length(sr) >= 5) {
        as.integer(sr[[5]])
      } else {
        NA_integer_
      }
    }, error = function(e) NA_integer_)
    context <- tryCatch({
      if (!is.null(srcfile$lines) && !is.na(line) && line >= 1 && line <= length(srcfile$lines)) {
        srcfile$lines[[line]]
      } else {
        NULL
      }
    }, error = function(e) NULL)
    return(list(
      filename = filename,
      line = line,
      column = column,
      context = context
    ))
  }
  NULL
}

build_error_diagnostics <- function(err) {
  call_repr <- tryCatch({
    call <- conditionCall(err)
    if (is.null(call)) {
      NULL
    } else {
      paste(deparse(call), collapse = " ")
    }
  }, error = function(e) NULL)
  if (!requireNamespace("rlang", quietly = TRUE)) {
    return(list(
      error = err,
      call = call_repr,
      note = "rlang package not available; install to capture annotated backtraces"
    ))
  }
  tryCatch({
    err <- rlang::cnd_entrace(err)
    trace_formals <- tryCatch(names(formals(rlang::trace_back)), error = function(e) character())
    trace_notes <- character()
    trace <- tryCatch({
      if ("simplify" %in% trace_formals) {
        rlang::trace_back(err, simplify = "none")
      } else {
        trace_notes <- c(trace_notes, "rlang::trace_back() does not support 'simplify'; using default output")
        rlang::trace_back(err)
      }
    }, error = function(e) {
      trace_notes <<- c(
        trace_notes,
        sprintf("failed to request unsimplified trace: %s", conditionMessage(e))
      )
      rlang::trace_back(err)
    })
    trace_text <- paste(capture.output(trace), collapse = "\n")
    origin <- extract_source_location(trace)
    if (is.null(origin)) {
      trace_notes <- c(trace_notes, "origin not available; template chunk may lack srcref information")
    }
    note_text <- if (length(trace_notes)) paste(trace_notes, collapse = "; ") else NULL
    list(
      error = err,
      trace_text = trace_text,
      origin = origin,
      call = call_repr,
      note = note_text
    )
  }, error = function(e) list(
    error = err,
    call = call_repr,
    note = sprintf("failed to enrich diagnostics: %s", conditionMessage(e))
  ))
}

render_deval <- function(run_path, runid, config = NULL, skip_cache = FALSE, parquet_overrides = NULL, output_file_override = NULL) {
  template_path <- DEFAULT_TEMPLATE
  if (!file.exists(template_path)) {
    stop(glue("DEVAL report template not found: {template_path}"))
  }
  previous_overrides <- getOption("weppcloudr_parquet_overrides", NULL)
  options(weppcloudr_parquet_overrides = parquet_overrides)
  on.exit(options(weppcloudr_parquet_overrides = previous_overrides), add = TRUE)
  output_dir <- file.path(run_path, "export", "WEPPcloudR")
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  output_file <- if (is.null(output_file_override)) {
    file.path(output_dir, glue("deval_{runid}.htm"))
  } else {
    output_file_override
  }
  anchor_runid <- if (!is.null(runid) && nzchar(runid)) runid else "unknown-run"
  anchor_path <- if (!is.null(config) && nzchar(config)) {
    glue("/weppcloud/runs/{anchor_runid}/{config}")
  } else {
    glue("/weppcloud/runs/{anchor_runid}")
  }
  params <- list(
    proj_runid = runid,
    proj_config = config,
    proj_run_label = anchor_runid
  )
  log_info("Rendering DEVAL report", runid = runid, config = config, template = template_path, output = output_file)
  append_log <- function(level, message) {
    if (identical(level, "ERROR")) {
      log_error(message, runid = runid, config = config)
    } else {
      log_info(message, runid = runid, config = config)
    }
  }
  append_log("INFO", glue("Checking render cache for run {runid}"))
  if (!skip_cache && file.exists(output_file)) {
    append_log("INFO", glue("Serving cached render for run {runid}"))
    return(readChar(output_file, file.info(output_file)$size, useBytes = TRUE))
  }
  if (skip_cache) {
    append_log("INFO", glue("Cache bypass requested for run {runid}; regenerating report"))
  }
  append_log("INFO", glue("Starting render for run {runid}"))
  local_fontawesome_header <- fontawesome_header()
  on.exit(unlink(local_fontawesome_header, force = TRUE), add = TRUE)
  render_target <- output_file
  publish_after_render <- is.null(output_file_override)
  if (publish_after_render) {
    render_target <- tempfile(
      pattern = paste0(".deval_", runid, "."),
      tmpdir = output_dir,
      fileext = ".tmp.htm"
    )
    on.exit(unlink(render_target, force = TRUE), add = TRUE)
  }
  tryCatch(
    {
      rmarkdown::render(
        input = template_path,
        params = params,
        output_file = render_target,
        output_dir = dirname(render_target),
        output_options = list(
          use_fontawesome = FALSE,
          includes = list(in_header = local_fontawesome_header)
        ),
        # The production image has a read-only root filesystem. Keep all knit
        # intermediates in the pod-local writable tmpfs; only the fenced final
        # artifact is published to the run directory.
        intermediates_dir = tempdir(),
        envir = new.env(parent = globalenv())
      )
      if (publish_after_render && !file.rename(render_target, output_file)) {
        stop("atomic DEVAL report publication failed")
      }
      append_log("INFO", glue("Render succeeded for run {runid}"))
      readChar(output_file, file.info(output_file)$size, useBytes = TRUE)
    },
    error = function(err) {
      msg <- conditionMessage(err)
      if (is.null(msg) || identical(msg, "")) {
        msg <- paste(capture.output(print(err)), collapse = "\n")
      }
      diagnostics <- build_error_diagnostics(err)
      err <- diagnostics$error
      origin <- diagnostics$origin
      tb <- diagnostics$trace_text
      if (is.null(tb) || !nzchar(tb)) {
        tb <- tryCatch(
          {
            calls <- sys.calls()
            paste(sapply(calls, function(call) paste(deparse(call), collapse = " ")), collapse = "\n -> ")
          },
          error = function(e) "Failed to capture call stack"
        )
      }
      origin_lines <- character()
      if (!is.null(origin)) {
        line_part <- if (!is.null(origin$line) && !is.na(origin$line)) {
          as.character(origin$line)
        } else {
          "?"
        }
        location <- glue("{origin$filename}:{line_part}")
        if (!is.null(origin$column) && !is.na(origin$column)) {
          location <- glue("{location}:{origin$column}")
        }
        origin_lines <- c(
          glue("Probable source: {location}"),
          if (!is.null(origin$context) && nzchar(trimws(origin$context))) {
            glue("Context: {trimws(origin$context)}")
          } else {
            NULL
          }
        )
      }
      call_line <- if (!is.null(diagnostics$call) && nzchar(diagnostics$call)) {
        glue("Call: {diagnostics$call}")
      } else {
        NULL
      }
      note_line <- if (!is.null(diagnostics$note) && nzchar(diagnostics$note)) {
        glue("Diagnostics: {diagnostics$note}")
      } else {
        NULL
      }
      detail <- paste(
        c(
          glue("Render failed for run {runid}: {msg}"),
          call_line,
          note_line,
          origin_lines,
          "Traceback:",
          tb
        ),
        collapse = "\n"
      )
      append_log("ERROR", detail)
      stop(err)
    }
  )
}

#* Health probe
#* @serializer json
#* @get /healthz
function() {
  list(status = "ok", timestamp = format(Sys.time(), tz = "UTC"))
}

#* Render Deval-In-The-Details report
#* @serializer html
#* @get /runs/<runid>/<config>/report/deval_details
function(runid, config, res, req, pup = NULL) {
  run_path <- resolve_run_dir(runid, config, pup)
  if (is.null(run_path)) {
    res$status <- 404
    return(glue("<html><body><h3>Run not found: {runid}/{config}</h3></body></html>"))
  }
  args <- req$args
  skip_cache <- FALSE
  if (!is.null(args) && any(names(args) == "no-cache")) {
    skip_cache <- TRUE
  }
  tryCatch(
    render_deval(run_path, runid, config, skip_cache = skip_cache),
    error = function(err) {
      log_error("Render failed: {err$message}", runid = runid, config = config)
      res$status <- 500
      glue("<html><body><h3>Render error</h3><pre>{err$message}</pre></body></html>")
    }
  )
}
