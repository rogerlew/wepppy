#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(plumber)
  library(logger)
})

log_threshold(INFO)

host <- Sys.getenv("HOST", "0.0.0.0")
port <- as.integer(Sys.getenv("PORT", "8000"))

log_info("Starting WEPPcloudR service on {host}:{port}")

pr <- plumb(file = "plumber.R")
pr$run(host = host, port = port)
