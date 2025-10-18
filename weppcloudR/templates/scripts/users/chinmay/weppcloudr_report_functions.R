## --------------------------------------------------------------------------------------##
##
## Script name: weppcloudr_report_functions.R
##
## Purpose of the script: meta functions used in the rmarkdown report.
##
## Author: Chinmay Deval
##
## Updated On: 2023-04-19
##
## Copyright (c) Chinmay Deval, 2022
## Email: chinmay.deval91@gmail.com
##
## --------------------------------------------------------------------------------------##
##  Notes: This file along with the styles.css should be in the same folder as the
##  rmarkdown file.
##   
##
## --------------------------------------------------------------------------------------##


## ----------------------------------Load packages---------------------------------------##



## --------------------------------------------------------------------------------------##

PRIMARY_RUN_ROOT <- Sys.getenv("PRIMARY_RUN_ROOT", "/geodata/weppcloud_runs")
PARTITIONED_RUN_ROOT <- Sys.getenv("PARTITIONED_RUN_ROOT", "/wc1/runs")
BATCH_ROOT <- Sys.getenv("BATCH_ROOT", "/wc1/batch")

.run_root_cache <- new.env(parent = emptyenv())

first_present <- function(name_vector, candidates) {
  for (candidate in candidates) {
    if (candidate %in% name_vector) {
      return(candidate)
    }
  }
  NULL
}

mutate_from_candidates <- function(tbl, target, candidates, transform = identity, default = NA_real_, warn = TRUE) {
  source_name <- first_present(names(tbl), candidates)
  if (is.null(source_name)) {
    if (warn) {
      warning(
        sprintf(
          "Columns [%s] not found when populating '%s'",
          paste(candidates, collapse = ", "),
          target
        ),
        call. = FALSE
      )
    }
    tbl[[target]] <- default
  } else {
    tbl[[target]] <- transform(tbl[[source_name]])
  }
  tbl
}

safe_depth_mm <- function(volume_m3, area_m2) {
  volume <- as.numeric(volume_m3)
  area <- as.numeric(area_m2)
  result <- rep(0, length(volume))
  valid <- !is.na(volume) & !is.na(area) & area > 0
  result[valid] <- (volume[valid] * 1000) / area[valid]
  result
}

safe_density_kg_ha <- function(mass_kg, area_ha) {
  mass <- as.numeric(mass_kg)
  area <- as.numeric(area_ha)
  result <- rep(0, length(mass))
  valid <- !is.na(mass) & !is.na(area) & area > 0
  result[valid] <- mass[valid] / area[valid]
  result
}

coerce_numeric_columns <- function(tbl, columns) {
  existing <- intersect(columns, names(tbl))
  for (column in existing) {
    tbl[[column]] <- as.numeric(tbl[[column]])
  }
  tbl
}

resolve_run_root <- function(runid) {
  cached <- .run_root_cache[[runid]]
  if (!is.null(cached) && dir.exists(cached)) {
    return(cached)
  }

  root <- NULL

  if (grepl(";;", runid, fixed = TRUE)) {
    tokens <- strsplit(runid, ";;", fixed = TRUE)[[1]]
    if (length(tokens) == 3 && identical(tokens[1], "batch")) {
      batch_dir <- file.path(BATCH_ROOT, tokens[2])
      if (dir.exists(batch_dir)) {
        if (identical(tokens[3], "_base")) {
          root <- file.path(batch_dir, "_base")
        } else {
          root <- file.path(batch_dir, "runs", tokens[3])
        }
      }
    }
  } else {
    primary <- file.path(PRIMARY_RUN_ROOT, runid)
    if (dir.exists(primary)) {
      root <- primary
    } else {
      prefix <- substr(runid, 1, min(2, nchar(runid)))
      partitioned <- file.path(PARTITIONED_RUN_ROOT, prefix, runid)
      if (dir.exists(partitioned)) {
        root <- partitioned
      }
    }
  }

  if (is.null(root) || !dir.exists(root)) {
    stop(sprintf("Run directory not found for '%s'", runid))
  }

  .run_root_cache[[runid]] <- root
  root
}

resolve_active_root <- function(runid, pup = NULL) {
  base_root <- resolve_run_root(runid)
  if (is.null(pup) || !nzchar(pup)) {
    return(base_root)
  }
  pups_dir <- file.path(base_root, "_pups")
  if (!dir.exists(pups_dir)) {
    stop(sprintf("PUP directory not available for '%s'", runid))
  }
  candidate <- normalizePath(file.path(pups_dir, pup), winslash = "/", mustWork = FALSE)
  if (is.na(candidate) || !dir.exists(candidate)) {
    stop(sprintf("PUP path '%s' not found for '%s'", pup, runid))
  }
  pups_dir_norm <- normalizePath(pups_dir, winslash = "/", mustWork = TRUE)
  if (!(identical(candidate, pups_dir_norm) || startsWith(candidate, paste0(pups_dir_norm, "/")))) {
    stop("PUP path escapes run directory")
  }
  candidate
}

run_path <- function(runid, ..., pup = NULL) {
  file.path(resolve_active_root(runid, pup), ...)
}

run_title_anchor <- function(runid, config = NULL) {
  if (is.null(runid) || !nzchar(runid)) {
    runid <- "unknown-run"
  }
  path <- if (!is.null(config) && nzchar(config)) {
    sprintf("/weppcloud/runs/%s/%s", runid, config)
  } else {
    sprintf("/weppcloud/runs/%s", runid)
  }
  sprintf("<a href=\"%s\" style=\"color: #6a4c93; text-decoration: none;\">%s</a>", path, runid)
}

gethillwatfiles<- function(runid){
  link <- run_path(runid, "wepp", "output")
  if (!dir.exists(link)) {
    stop(sprintf("WEPP output directory not found for run '%s'", runid))
  }
  list.files(link, "*\\.wat.dat$", full.names = TRUE)
}



## --------------------------------------------------------------------------------------##

calc_watbal <- function(link){
  a <- read.table(link, skip = 23,
                  col.names = c("OFE",	"J",	"Y",	"P",	"RM",	"Q",	"Ep",	"Es",
                                "Er",	"Dp",	"UpStrmQ",	"SubRIn",	"latqcc",
                                "Total_Soil_Water",	"frozwt",	"Snow_Water",	"QOFE",
                                "Tile",	"Irr",	"Area")) %>%
    dplyr::mutate_if(is.character,as.numeric)
  
  
  a <- a %>%  dplyr::mutate(wb = P-Q-Ep - Es- Er - Dp - latqcc +
                              dplyr::lag(Total_Soil_Water) - Total_Soil_Water +
                              dplyr::lag(frozwt) - frozwt+ dplyr::lag(Snow_Water) - Snow_Water) %>%
    dplyr::mutate(dplyr::across(where(is.numeric), round, 3)) %>% dplyr::select(wb) %>%
    dplyr::summarise(dplyr::across(where(is.numeric), ~sum(.x, na.rm = TRUE))) %>%
    dplyr::mutate(WeppID =readr::parse_number(gsub("^.*/", "", link)))
  
  return(as.data.frame(a))
}


## --------------------------------------------------------------------------------------##
 

get_geometry <- function(runid){
  preferred <- run_path(runid, "watershed", "subcatchments.WGS.json")
  fallback <- run_path(runid, "watershed", "subcatchments.json")

  src <- if (file.exists(preferred)) preferred else if (file.exists(fallback)) fallback else NULL
  if (is.null(src)) {
    stop(sprintf("Subcatchments JSON not found for run '%s'", runid))
  }

  geometry <- sf::st_read(src, quiet = TRUE) %>%
    dplyr::select(WeppID, geometry) %>%
    sf::st_transform(4326) %>%
    dplyr::group_by(WeppID) %>%
    dplyr::summarise(geometry = sf::st_union(geometry), .groups = "drop")

  geometry
}

## --------------------------------------------------------------------------------------##

get_WatershedArea_m2 <- function(runid){
  hills_path <- run_path(runid, "watershed", "hillslopes.parquet")
  if (file.exists(hills_path)) {
    hills <- arrow::read_parquet(hills_path)
    area_cols <- c("area", "area_m2", "area_ha")
    existing <- area_cols[area_cols %in% names(hills)]
    if (length(existing) > 0) {
      area_m2 <- NULL
      if ("area" %in% existing) {
        area_m2 <- as.numeric(hills$area)
      } else if ("area_m2" %in% existing) {
        area_m2 <- as.numeric(hills$area_m2)
      } else {
        area_m2 <- as.numeric(hills$area_ha) * 10000
      }
      area_m2 <- area_m2[!is.na(area_m2)]
      if (length(area_m2)) {
        return(sum(area_m2))
      }
    }
  }

  parquet_path <- run_path(runid, "wepp", "output", "interchange", "totalwatsed3.parquet")
  if (file.exists(parquet_path)) {
    tbl <- arrow::read_parquet(parquet_path, as_data_frame = TRUE)
    if ("Area" %in% names(tbl)) {
      candidates <- tbl$Area[which(!is.na(tbl$Area) & tbl$Area > 0)]
      if (length(candidates) > 0) {
        return(as.numeric(candidates[1]))
      }
    }
  }

  stop(sprintf("Unable to determine watershed area for run '%s'", runid))
}

## --------------------------------------------------------------------------------------##

# Function to extract numbers from a character vector
extract_numbers <- function(strings) {
  numbers <- as.numeric(regmatches(strings, regexpr("[0-9]+", strings)))
  return(numbers)
}

get_cli_summary <- function(runid){
  totals <- load_totalwatsed(runid)
  storms <- tryCatch(
    load_ebe(runid),
    error = function(err) {
      current_warning <- sprintf("EBE data unavailable for run '%s': %s", runid, err$message)
      warning(current_warning, call. = FALSE)
      dplyr::tibble()
    }
  )

  wy_span <- range(totals$WY, na.rm = TRUE)
  wy_count <- length(unique(totals$WY))

  wy_summary <- totals %>%
    dplyr::group_by(WY) %>%
    dplyr::summarise(
      precip_mm = sum(precipitation_mm, na.rm = TRUE),
      streamflow_mm = sum(streamflow_mm, na.rm = TRUE),
      .groups = "drop"
    ) %>%
    dplyr::mutate(
      precip_mm = as.numeric(precip_mm),
      streamflow_mm = as.numeric(streamflow_mm)
    )

  list(
    water_year_start = wy_span[1],
    water_year_end = wy_span[2],
    water_year_count = wy_count,
    storm_count = nrow(storms),
    total_precip_mm = sum(wy_summary$precip_mm, na.rm = TRUE),
    mean_annual_precip_mm = mean(wy_summary$precip_mm, na.rm = TRUE),
    total_streamflow_mm = sum(wy_summary$streamflow_mm, na.rm = TRUE),
    mean_annual_streamflow_mm = mean(wy_summary$streamflow_mm, na.rm = TRUE)
  )
}



## --------------------------------------------------------------------------------------##
 
get_WY <- function(x, numeric=TRUE) {
  x <- as.POSIXlt(x)
  yr <- x$year + 1900L
  mn <- x$mon + 1L
  ## adjust for water year
  yr <- yr + ifelse(mn < 10L, 0L, 1L)
  if(numeric)
    return(yr)
  ordered(yr)
}


## --------------------------------------------------------------------------------------##

process_chanwb <- function(runid, Wshed_Area_m2){
  parquet_path <- run_path(runid, "wepp", "output", "interchange", "chanwb.parquet")
  if (!file.exists(parquet_path)) {
    stop(sprintf("chanwb.parquet not found for run '%s'", runid))
  }

  chanwb <- arrow::read_parquet(parquet_path) %>%
    dplyr::as_tibble() %>%
    dplyr::mutate(
      Date = lubridate::make_date(year, month, day_of_month),
      WY = water_year,
      Q_outlet_mm = (`Outflow (m^3)` / Wshed_Area_m2) * 1000
    ) %>%
    dplyr::rename(
      Year_chan = year,
      Day_chan = day_of_month,
      Elmt_ID_chan = Elmt_ID,
      Chan_ID_chan = Chan_ID,
      Inflow_chan_m3 = `Inflow (m^3)`,
      Outflow_chan_m3 = `Outflow (m^3)`,
      Storage_chan_m3 = `Storage (m^3)`,
      Baseflow_chan_m3 = `Baseflow (m^3)`,
      Loss_chan_m3 = `Loss (m^3)`,
      Balance_chan_m3 = `Balance (m^3)`
    ) %>%
    dplyr::select(
      Year_chan,
      Day_chan,
      Date,
      WY,
      Elmt_ID_chan,
      Chan_ID_chan,
      Inflow_chan_m3,
      Outflow_chan_m3,
      Storage_chan_m3,
      Baseflow_chan_m3,
      Loss_chan_m3,
      Balance_chan_m3,
      Q_outlet_mm
    )

  chanwb <- coerce_numeric_columns(
    chanwb,
    c(
      "Year_chan",
      "Day_chan",
      "WY",
      "Elmt_ID_chan",
      "Chan_ID_chan",
      "Inflow_chan_m3",
      "Outflow_chan_m3",
      "Storage_chan_m3",
      "Baseflow_chan_m3",
      "Loss_chan_m3",
      "Balance_chan_m3",
      "Q_outlet_mm"
    )
  )

  chanwb
}

read_subcatchments = function(runid) {
  wbt_wgs <- run_path(runid, "dem", "wbt", "subcatchments.WGS.geojson")
  wbt_utm <- run_path(runid, "dem", "wbt", "subcatchments.geojson")
  topaz_wgs <- run_path(runid, "dem", "topaz", "SUBCATCHMENTS.WGS.JSON")
  topaz_utm <- run_path(runid, "dem", "topaz", "SUBCATCHMENTS.JSON")

  candidate_paths <- c(wbt_wgs, wbt_utm, topaz_wgs, topaz_utm)
  existing_path <- candidate_paths[file.exists(candidate_paths)][1]
  if (is.na(existing_path)) {
    stop(sprintf("Subcatchments GeoJSON not found for run '%s'", runid))
  }

  subcatchments <- sf::st_read(existing_path, quiet = TRUE)

  subcatchments <- sf::st_transform(subcatchments, 4326)
  if (!("TopazID" %in% names(subcatchments))) {
    stop("TopazID column missing from subcatchments geometry")
  }
  subcatchments$TopazID <- as.integer(subcatchments$TopazID)
  if (!("WeppID" %in% names(subcatchments))) {
    subcatchments$WeppID <- NA_integer_
  } else {
    subcatchments$WeppID <- as.integer(subcatchments$WeppID)
  }

  hills_path <- run_path(runid, "watershed", "hillslopes.parquet")
  landuse_path <- run_path(runid, "landuse", "landuse.parquet")
  soils_path <- run_path(runid, "soils", "soils.parquet")

  hills <- arrow::read_parquet(hills_path) %>%
    dplyr::as_tibble()
  if (!"TopazID" %in% names(hills)) {
    if ("topaz_id" %in% names(hills)) {
      hills$TopazID <- hills$topaz_id
    } else {
      stop("TopazID column missing from hillslopes parquet")
    }
  }
  if (!"wepp_id" %in% names(hills) && "WeppID" %in% names(hills)) {
    hills$wepp_id <- hills$WeppID
  }
  area_col <- first_present(names(hills), c("area", "area_m2", "Area"))
  area_m2 <- NULL
  if (!is.null(area_col)) {
    area_m2 <- as.numeric(hills[[area_col]])
  }
  if (is.null(area_m2) && "area_ha" %in% names(hills)) {
    area_m2 <- as.numeric(hills$area_ha) * 10000
  }
  if (is.null(area_m2)) {
    warning("Unable to resolve area for hillslopes.parquet; defaulting to NA", call. = FALSE)
    area_m2 <- rep(NA_real_, nrow(hills))
  }
  area_ha_existing <- if ("area_ha" %in% names(hills)) as.numeric(hills$area_ha) else NULL
  if (!is.null(area_ha_existing) && any(!is.na(area_ha_existing))) {
    area_ha <- area_ha_existing
  } else {
    area_ha <- area_m2 / 10000
  }

  slope_percent <- NULL
  if ("slope_scalar" %in% names(hills)) {
    slope_percent <- as.numeric(hills$slope_scalar) * 100
  } else if ("slope_percent" %in% names(hills)) {
    slope_percent <- as.numeric(hills$slope_percent)
  } else if ("slope" %in% names(hills)) {
    slope_percent <- as.numeric(hills$slope)
  } else {
    warning("Unable to resolve slope information for hillslopes.parquet; defaulting to NA", call. = FALSE)
    slope_percent <- rep(NA_real_, nrow(hills))
  }

  hills <- hills %>%
    dplyr::mutate(
      TopazID = as.integer(TopazID),
      wepp_id = as.integer(wepp_id),
      area_ha = area_ha,
      slope_percent = slope_percent,
      slope = slope_percent
    ) %>%
    dplyr::select(TopazID, wepp_id, area_ha, slope_percent, slope)

  landuse <- arrow::read_parquet(landuse_path)
  if (!"TopazID" %in% names(landuse) && "topaz_id" %in% names(landuse)) {
    landuse$TopazID <- landuse$topaz_id
  }
  landuse <- landuse %>%
    dplyr::mutate(
      TopazID = as.integer(TopazID),
      landuse = dplyr::coalesce(desc, disturbed_class, as.character(key))
    ) %>%
    dplyr::select(TopazID, landuse)

  soils <- arrow::read_parquet(soils_path)
  if (!"TopazID" %in% names(soils) && "topaz_id" %in% names(soils)) {
    soils$TopazID <- soils$topaz_id
  }
  soils <- soils %>%
    dplyr::mutate(
      TopazID = as.integer(TopazID),
      soil = dplyr::coalesce(desc, mukey),
      Texture = dplyr::coalesce(simple_texture, "Refer to the soil file for details")
    ) %>%
    dplyr::select(TopazID, soil, Texture)

  loss_path <- run_path(runid, "wepp", "output", "interchange", "loss_pw0.hill.parquet")

  empty_loss_summary <- dplyr::tibble(
    wepp_id = integer(),
    runoff_mm = numeric(),
    lateral_flow_mm = numeric(),
    baseflow_mm = numeric(),
    Sediment_Yield_kg = numeric(),
    sd_yd_kg_ha = numeric(),
    soil_loss_kg = numeric(),
    so_ls_kg_ha = numeric(),
    Total_Phosphorus_kg = numeric(),
    tp_kg_ha = numeric(),
    SRP_kg = numeric(),
    srp_kg_ha = numeric(),
    PP_kg = numeric(),
    pp_kg_ha = numeric()
  )

  if (file.exists(loss_path)) {
    loss_raw <- arrow::read_parquet(loss_path) %>%
      dplyr::as_tibble()

    wepp_col <- first_present(names(loss_raw), c("wepp_id", "WeppID"))
    area_col <- first_present(names(loss_raw), c("Hillslope Area", "area_ha", "Area_ha"))
    runoff_col <- first_present(names(loss_raw), c("Runoff Volume", "runoff_volume"))
    lateral_col <- first_present(names(loss_raw), c("Subrunoff Volume", "subrunoff_volume"))
    baseflow_col <- first_present(names(loss_raw), c("Baseflow Volume", "baseflow_volume"))
    soil_loss_col <- first_present(names(loss_raw), c("Soil Loss", "soil_loss_kg"))
    sed_yield_col <- first_present(names(loss_raw), c("Sediment Yield", "sediment_yield_kg"))
    total_p_col <- first_present(names(loss_raw), c("Total Pollutant", "total_p_kg"))
    srp_col <- first_present(names(loss_raw), c("Solub. React. Pollutant", "srp_kg"))
    pp_col <- first_present(names(loss_raw), c("Particulate Pollutant", "pp_kg"))

    if (is.null(wepp_col) || is.null(area_col)) {
      warning("loss_pw0.hill.parquet is missing required identifiers; skipping hillslope metrics", call. = FALSE)
      loss_summary <- empty_loss_summary
    } else {
      loss_summary <- loss_raw %>%
        dplyr::mutate(
          wepp_id = as.integer(.data[[wepp_col]]),
          area_ha_raw = as.numeric(.data[[area_col]]),
          runoff_m3 = if (!is.null(runoff_col)) as.numeric(.data[[runoff_col]]) else 0,
          lateral_m3 = if (!is.null(lateral_col)) as.numeric(.data[[lateral_col]]) else 0,
          baseflow_m3 = if (!is.null(baseflow_col)) as.numeric(.data[[baseflow_col]]) else 0,
          soil_loss_kg = if (!is.null(soil_loss_col)) as.numeric(.data[[soil_loss_col]]) else 0,
          Sediment_Yield_kg = if (!is.null(sed_yield_col)) as.numeric(.data[[sed_yield_col]]) else 0,
          Total_Phosphorus_kg = if (!is.null(total_p_col)) as.numeric(.data[[total_p_col]]) else 0,
          SRP_kg = if (!is.null(srp_col)) as.numeric(.data[[srp_col]]) else 0,
          PP_kg = if (!is.null(pp_col)) as.numeric(.data[[pp_col]]) else 0
        ) %>%
        dplyr::group_by(wepp_id) %>%
        dplyr::summarise(
          area_ha = {
            valid <- area_ha_raw[!is.na(area_ha_raw)]
            if (length(valid)) valid[1] else NA_real_
          },
          runoff_volume_m3 = sum(runoff_m3, na.rm = TRUE),
          lateral_volume_m3 = sum(lateral_m3, na.rm = TRUE),
          baseflow_volume_m3 = sum(baseflow_m3, na.rm = TRUE),
          Sediment_Yield_kg = sum(Sediment_Yield_kg, na.rm = TRUE),
          soil_loss_kg = sum(soil_loss_kg, na.rm = TRUE),
          Total_Phosphorus_kg = sum(Total_Phosphorus_kg, na.rm = TRUE),
          SRP_kg = sum(SRP_kg, na.rm = TRUE),
          PP_kg = sum(PP_kg, na.rm = TRUE),
          .groups = "drop"
        ) %>%
        dplyr::mutate(
          area_m2 = area_ha * 10000,
          runoff_mm = safe_depth_mm(runoff_volume_m3, area_m2),
          lateral_flow_mm = safe_depth_mm(lateral_volume_m3, area_m2),
          baseflow_mm = safe_depth_mm(baseflow_volume_m3, area_m2),
          so_ls_kg_ha = safe_density_kg_ha(soil_loss_kg, area_ha),
          sd_yd_kg_ha = safe_density_kg_ha(Sediment_Yield_kg, area_ha),
          tp_kg_ha = safe_density_kg_ha(Total_Phosphorus_kg, area_ha),
          srp_kg_ha = safe_density_kg_ha(SRP_kg, area_ha),
          pp_kg_ha = safe_density_kg_ha(PP_kg, area_ha)
        ) %>%
        dplyr::select(
          wepp_id,
          runoff_mm,
          lateral_flow_mm,
          baseflow_mm,
          Sediment_Yield_kg,
          sd_yd_kg_ha,
          soil_loss_kg,
          so_ls_kg_ha,
          Total_Phosphorus_kg,
          tp_kg_ha,
          SRP_kg,
          srp_kg_ha,
          PP_kg,
          pp_kg_ha
        )

      loss_summary <- dplyr::bind_rows(empty_loss_summary[0, ], loss_summary)
    }
  } else {
    warning(sprintf("loss_pw0.hill.parquet not found for run '%s'; runoff and sediment metrics set to zero", runid), call. = FALSE)
    loss_summary <- empty_loss_summary
  }

  subcatchments <- subcatchments %>%
    dplyr::left_join(hills, by = "TopazID") %>%
    dplyr::left_join(landuse, by = "TopazID") %>%
    dplyr::left_join(soils, by = "TopazID")

  sub_wepp_source <- first_present(names(subcatchments), c("WeppID", "wepp_id", "wepp_id.x", "wepp_id.y"))
  hills_wepp_source <- first_present(names(hills), c("wepp_id"))

  subcatchments <- subcatchments %>%
    dplyr::mutate(
      sub_wepp_id = if (!is.null(sub_wepp_source)) as.integer(.data[[sub_wepp_source]]) else NA_integer_,
      hill_wepp_id = if (!is.null(hills_wepp_source)) as.integer(.data[[hills_wepp_source]]) else NA_integer_
    )

  resolved_wepp <- dplyr::coalesce(subcatchments$hill_wepp_id, subcatchments$sub_wepp_id)
  if (any(is.na(resolved_wepp))) {
    stop("Unable to resolve wepp_id for subcatchments; ensure loss and geometry IDs align")
  }

  subcatchments <- subcatchments %>%
    dplyr::mutate(
      wepp_id = resolved_wepp,
      area_ha = dplyr::coalesce(area_ha, as.numeric(sf::st_area(geometry)) / 10000),
      landuse = dplyr::coalesce(landuse, "Unknown"),
      soil = dplyr::coalesce(soil, "Refer to the soil file for details"),
      Texture = dplyr::coalesce(Texture, "Refer to the soil file for details"),
      gradient = dplyr::case_when(
        is.na(slope_percent) ~ "Refer to the soil file for details",
        slope_percent < 10 ~ "0-10% slopes",
        slope_percent < 20 ~ "10-20% slopes",
        slope_percent < 30 ~ "20-30% slopes",
        slope_percent < 40 ~ "30-40% slopes",
        TRUE ~ "40%+ slopes"
      ),
      Watershed = runid
    ) %>%
    dplyr::left_join(loss_summary, by = "wepp_id")

  subcatchments <- subcatchments %>%
    {
      drop_cols <- intersect(names(.), c("wepp_id.x", "wepp_id.y", "sub_wepp_id", "hill_wepp_id"))
      if (length(drop_cols)) dplyr::select(., -dplyr::all_of(drop_cols)) else .
    }

  numeric_metrics <- c(
    "runoff_mm",
    "lateral_flow_mm",
    "baseflow_mm",
    "Sediment_Yield_kg",
    "sd_yd_kg_ha",
    "soil_loss_kg",
    "so_ls_kg_ha",
    "Total_Phosphorus_kg",
    "tp_kg_ha",
    "SRP_kg",
    "srp_kg_ha",
    "PP_kg",
    "pp_kg_ha"
  )

  subcatchments <- subcatchments %>%
    dplyr::mutate(
      area_ha = as.numeric(area_ha),
      slope_percent = as.numeric(slope_percent),
      slope = as.numeric(slope)
    ) %>%
    dplyr::mutate(
      dplyr::across(
        dplyr::any_of(numeric_metrics),
        ~as.numeric(dplyr::coalesce(., 0))
      )
    )

  subcatchments
}


## --------------------------------------------------------------------------------------##

read_subcatchments_map = function(runid){
  read_subcatchments(runid) %>%
    dplyr::mutate(scenario = NA_character_)
}

## --------------------------------------------------------------------------------------##

summarize_subcatch_by_var = function(subcatch, var_to_summarize_by){
  
  subcatchdf = subcatch %>% 
    as.data.frame() %>%
    dplyr::select(-geometry)%>%
    dplyr::group_by(.data[[var_to_summarize_by]]) %>%
    dplyr::summarise_at(vars(area_ha), list(sum_area = sum))%>%
    dplyr::mutate(percent_area = sum_area/sum(sum_area)*100)%>%
    dplyr::select(-sum_area)%>%
    dplyr::mutate(dplyr::across(where(is.numeric), round, 0)) %>%
    dplyr::rename("Area" = "percent_area")%>%
    dplyr::arrange(-Area)
  
  if(var_to_summarize_by == "landuse"){
    subcatchdf = subcatchdf %>%
      dplyr::rename("Landuse" = "landuse")
    }else
        if(var_to_summarize_by == "soil"){
          subcatchdf = subcatchdf %>%
            dplyr::rename("Soil" = "soil")
          }else
              if(var_to_summarize_by == "gradient"){
                subcatchdf = subcatchdf %>%
                  dplyr::rename("Gradient" = "gradient")
                }else
                    if(var_to_summarize_by == "Texture"){
                      subcatchdf = subcatchdf}
  return(subcatchdf)
} 

## --------------------------------------------------------------------------------------##

gen_cumulative_plt_df <- function(subcatch, var_to_use){

  var_to_use = dplyr::enquo(var_to_use)
  value_col <- rlang::as_name(var_to_use)
  value_sym <- rlang::sym(value_col)

  c_plt_df = subcatch %>%
      # as.data.frame()%>%
      dplyr::select(wepp_id,!!var_to_use,area_ha,geometry,landuse,soil,Texture,slope)%>%
      dplyr::mutate(
        area_ha = suppressWarnings(as.numeric(area_ha)),
        area_ha = dplyr::coalesce(area_ha, 0),
        !!value_sym := suppressWarnings(as.numeric(.data[[value_col]])),
        !!value_sym := dplyr::coalesce(!!value_sym, 0)
      ) %>%
      dplyr::mutate(
        total_area = sum(area_ha, na.rm = TRUE),
        total_value = sum(!!value_sym, na.rm = TRUE)
      ) %>%
      dplyr::arrange(desc(!!var_to_use)) %>%
      dplyr::mutate(
        cumPercArea = ifelse(total_area > 0,
          cumsum(area_ha) / total_area * 100,
          0
        ),
        new_col = ifelse(total_value > 0,
          cumsum(!!value_sym) / total_value * 100,
          0
        )
      )%>%
    dplyr::select(-total_area, -total_value) %>%
    dplyr::mutate(
      cumPercArea = replace(cumPercArea, is.na(cumPercArea), 0),
      new_col = replace(new_col, is.na(new_col), 0),
      cumPercArea = round(cumPercArea, 1),
      new_col = round(new_col, 1),
      !!value_sym := round(!!value_sym, 1),
      area_ha = round(area_ha, 1)
    )%>%
    dplyr::select(wepp_id,!!var_to_use,area_ha,geometry,cumPercArea,new_col,landuse,
                  soil,Texture,slope)

  colnames(c_plt_df)[6] = paste0("cum_",colnames(c_plt_df)[2])
  cum_col <- colnames(c_plt_df)[6]

  c_plt_df <- c_plt_df %>%
    dplyr::mutate(
      dplyr::across(
        dplyr::all_of(c(value_col, cum_col)),
        ~ suppressWarnings(as.numeric(.))
      )
    )
  
  return(c_plt_df)

}

## --------------------------------------------------------------------------------------##
gen_cumulative_plt_df_map <- function(subcatch, var_to_use){
  
  var_to_use = dplyr::enquo(var_to_use)
  value_col <- rlang::as_name(var_to_use)
  value_sym <- rlang::sym(value_col)
  
  c_plt_df = subcatch %>%
    dplyr::group_by(Watershed, scenario)%>%
    # dplyr::select(wepp_id,!!var_to_use,area_ha,geometry,landuse,soil,Texture,slope)%>%
    dplyr::mutate(
      area_ha = suppressWarnings(as.numeric(area_ha)),
      area_ha = dplyr::coalesce(area_ha, 0),
      !!value_sym := suppressWarnings(as.numeric(.data[[value_col]])),
      !!value_sym := dplyr::coalesce(!!value_sym, 0)
    ) %>%
    dplyr::mutate(
      total_area = sum(area_ha, na.rm = TRUE),
      total_value = sum(!!value_sym, na.rm = TRUE)
    ) %>%
    dplyr::arrange(desc(!!var_to_use)) %>%
    dplyr::mutate(
      cumPercArea = ifelse(total_area > 0,
        cumsum(area_ha) / total_area * 100,
        0
      ),
      new_col = ifelse(total_value > 0,
        cumsum(!!value_sym) / total_value * 100,
        0
      )
    )%>%
    dplyr::select(-total_area, -total_value) %>%
    dplyr::mutate(
      cumPercArea = replace(cumPercArea, is.na(cumPercArea), 0),
      new_col = replace(new_col, is.na(new_col), 0),
      cumPercArea = round(cumPercArea, 1),
      new_col = round(new_col, 1),
      !!value_sym := round(!!value_sym, 1),
      area_ha = round(area_ha, 1)
    )%>%
    dplyr::select(wepp_id,!!var_to_use,area_ha,geometry,cumPercArea,new_col,landuse,
    soil,Texture,slope,Watershed,scenario,sd_yd_kg_ha,tp_kg_ha)%>%
    ungroup()
  
  colnames(c_plt_df)[6] = paste0("cum_",colnames(c_plt_df)[2])
  cum_col <- colnames(c_plt_df)[6]
  
  c_plt_df <- c_plt_df %>%
    dplyr::mutate(
      dplyr::across(
        dplyr::all_of(c(value_col, cum_col)),
        ~ suppressWarnings(as.numeric(.))
      )
    )
  
  return(c_plt_df)
  
}


## --------------------------------------------------------------------------------------##
# Event by event file

load_ebe <- function(runid) {
  parquet_path <- run_path(runid, "wepp", "output", "interchange", "ebe_pw0.parquet")
  if (!file.exists(parquet_path)) {
    stop(sprintf("ebe_pw0.parquet not found for run '%s'", runid))
  }
  area_m2 <- get_WatershedArea_m2(runid)

  arrow::read_parquet(parquet_path) %>%
    dplyr::as_tibble() %>%
    dplyr::mutate(
      Day_ebe = day_of_month,
      Month_ebe = month,
      Year_ebe = year,
      Date = lubridate::make_date(year, month, day_of_month),
      WY = water_year,
      P_ebe = precip,
      Runoff_ebe = (runoff_volume / area_m2) * 1000,
      peak_ebe = peak_runoff,
      Sediment_ebe = sediment_yield,
      SRP_ebe = soluble_pollutant,
      PP_ebe = particulate_pollutant,
      TP_ebe = total_pollutant,
      Sediment_tonnes_ebe = Sediment_ebe / 1000,
      SRP_tonnes_ebe = SRP_ebe / 1000,
      PP_tonnes_ebe = PP_ebe / 1000,
      TP_tonnes_ebe = TP_ebe / 1000
    ) %>%
    dplyr::select(
      Day_ebe,
      Month_ebe,
      Year_ebe,
      Date,
      WY,
      P_ebe,
      Runoff_ebe,
      peak_ebe,
      Sediment_ebe,
      SRP_ebe,
      PP_ebe,
      TP_ebe,
      Sediment_tonnes_ebe,
      SRP_tonnes_ebe,
      PP_tonnes_ebe,
      TP_tonnes_ebe
    ) %>%
    coerce_numeric_columns(
      c(
        "Day_ebe",
        "Month_ebe",
        "Year_ebe",
        "WY",
        "P_ebe",
        "Runoff_ebe",
        "peak_ebe",
        "Sediment_ebe",
        "SRP_ebe",
        "PP_ebe",
        "TP_ebe",
        "Sediment_tonnes_ebe",
        "SRP_tonnes_ebe",
        "PP_tonnes_ebe",
        "TP_tonnes_ebe"
      )
    )
}

process_ebe <- function(runid, yr_start, yr_end){
  load_ebe(runid)
}
## --------------------------------------------------------------------------------------##
load_totalwatsed <- function(runid) {
  parquet_path <- run_path(runid, "wepp", "output", "interchange", "totalwatsed3.parquet")
  if (!file.exists(parquet_path)) {
    stop(sprintf("totalwatsed3.parquet not found for run '%s'", runid))
  }
  totals <- arrow::read_parquet(parquet_path) %>%
    dplyr::as_tibble()

  year_col <- first_present(names(totals), c("year", "Year"))
  month_col <- first_present(names(totals), c("month", "Month"))
  day_col <- first_present(names(totals), c("day_of_month", "day", "Day"))

  if (!is.null(year_col) && !is.null(month_col) && !is.null(day_col)) {
    totals$Date <- lubridate::make_date(
      year = as.integer(totals[[year_col]]),
      month = as.integer(totals[[month_col]]),
      day = as.integer(totals[[day_col]])
    )
  } else {
    warning("Unable to determine Date column from totalwatsed3 parquet metadata", call. = FALSE)
    totals$Date <- as.Date(NA)
  }

  wy_col <- first_present(names(totals), c("water_year", "WaterYear", "WY", "wy"))
  if (!is.null(wy_col)) {
    totals$WY <- suppressWarnings(as.integer(totals[[wy_col]]))
    if (anyNA(totals$WY)) {
      totals$WY <- get_WY(totals$Date, numeric = TRUE)
    }
  } else {
    totals$WY <- get_WY(totals$Date, numeric = TRUE)
  }

  totals <- mutate_from_candidates(
    totals,
    "precipitation_mm",
    c("Precipitation", "precipitation_mm", "precipitation"),
    transform = as.numeric
  )
  totals <- mutate_from_candidates(
    totals,
    "rain_melt_mm",
    c("Rain+Melt", "rain_melt_mm", "rain_melt"),
    transform = as.numeric
  )
  totals <- mutate_from_candidates(
    totals,
    "transpiration_mm",
    c("Transpiration", "transpiration_mm", "transpiration"),
    transform = as.numeric
  )
  totals <- mutate_from_candidates(
    totals,
    "evaporation_mm",
    c("Evaporation", "evaporation_mm", "evaporation"),
    transform = as.numeric
  )
  totals <- mutate_from_candidates(
    totals,
    "percolation_mm",
    c("Percolation", "percolation_mm", "percolation"),
    transform = as.numeric
  )
  totals <- mutate_from_candidates(
    totals,
    "runoff_mm",
    c("Runoff", "runoff_mm", "runoff"),
    transform = as.numeric
  )
  totals <- mutate_from_candidates(
    totals,
    "lateral_flow_mm",
    c("Lateral Flow", "lateral_flow_mm", "lateral_flow"),
    transform = as.numeric
  )
  totals <- mutate_from_candidates(
    totals,
    "baseflow_mm",
    c("Baseflow", "baseflow_mm", "baseflow"),
    transform = as.numeric
  )
  totals <- mutate_from_candidates(
    totals,
    "streamflow_mm",
    c("Streamflow", "streamflow_mm", "streamflow"),
    transform = as.numeric
  )

  totals <- coerce_numeric_columns(
    totals,
    c(
      "precipitation_mm",
      "rain_melt_mm",
      "transpiration_mm",
      "evaporation_mm",
      "percolation_mm",
      "runoff_mm",
      "lateral_flow_mm",
      "baseflow_mm",
      "streamflow_mm"
    )
  )

  if ("day_of_month" %in% names(totals)) {
    if (!"day" %in% names(totals)) {
      totals <- totals %>% dplyr::rename(day = day_of_month)
    } else {
      totals <- totals %>% dplyr::select(-day_of_month)
    }
  }

  totals
}

process_totalwatsed <- function(runid){
  load_totalwatsed(runid)
}

process_totalwatsed_map_df <- function(runid){
  load_totalwatsed(runid) %>%
    dplyr::mutate(runid = runid)
}

## --------------------------------------------------------------------------------------##

totwatsed_to_wbal = function(daily_totwatsed_df){

  numeric_cols <- c(
    "precipitation_mm",
    "rain_melt_mm",
    "transpiration_mm",
    "evaporation_mm",
    "percolation_mm",
    "runoff_mm",
    "lateral_flow_mm",
    "baseflow_mm",
    "streamflow_mm"
  )

  daily_totwatsed_df <- coerce_numeric_columns(daily_totwatsed_df, numeric_cols)
  
  totwatsed2wbal = daily_totwatsed_df %>% dplyr::select(
    "WY",
    "Date",
    "precipitation_mm",
    "rain_melt_mm",
    "transpiration_mm",
    "evaporation_mm",
    "percolation_mm",
    "runoff_mm",
    "lateral_flow_mm"
  )%>% dplyr::filter(Date >= paste0(lubridate::year(Date[1]),"-10-01"))
  
  wys = as.numeric(length(unique(totwatsed2wbal$WY)))
  
  totwatsed2wbal = totwatsed2wbal %>%
    dplyr::select(- c(Date,WY))%>%
    dplyr::summarise(dplyr::across(where(is.numeric), ~sum(.x, na.rm = TRUE))) %>%
    dplyr::mutate(
      precipitation_mm = precipitation_mm / wys,
      rain_melt_mm = rain_melt_mm / wys,
      transpiration_mm = transpiration_mm / wys,
      evaporation_mm = evaporation_mm / wys,
      percolation_mm = percolation_mm / wys,
      runoff_mm = runoff_mm / wys,
      lateral_flow_mm = lateral_flow_mm / wys) %>%
    dplyr::mutate(
      rain_melt_mm = rain_melt_mm / precipitation_mm * 100,
      transpiration_mm = transpiration_mm / precipitation_mm *
        100,
      evaporation_mm = evaporation_mm / precipitation_mm *
        100,
      percolation_mm = percolation_mm / precipitation_mm *
        100,
      runoff_mm = runoff_mm / precipitation_mm * 100,
      lateral_flow_mm = lateral_flow_mm / precipitation_mm *
        100,
      WbalErr_mm = rain_melt_mm - (
        transpiration_mm + evaporation_mm + percolation_mm + runoff_mm + lateral_flow_mm
      )
    ) %>%
    dplyr::rename(
      "Precipitation (mm)" = "precipitation_mm",
      "Rain+Melt (%)" = "rain_melt_mm",
      "Transpiration (%)" = "transpiration_mm",
      "Evaporation (%)" = "evaporation_mm",
      "Percolation (%)" = "percolation_mm",
      "Runoff (%)" = "runoff_mm",
      "Lateral flow (%)" = "lateral_flow_mm",
      "Change in storage (%)" = "WbalErr_mm"
    ) %>%
    tidyr::gather(key = "variable") %>% 
    dplyr::mutate(dplyr::across(where(is.numeric), round, 2))
  
  return(totwatsed2wbal)
} 
## --------------------------------------------------------------------------------------##

totwatsed_to_wbal_map_dfs = function(daily_totwatsed_df){

  numeric_cols <- c(
    "precipitation_mm",
    "rain_melt_mm",
    "transpiration_mm",
    "evaporation_mm",
    "percolation_mm",
    "runoff_mm",
    "lateral_flow_mm",
    "baseflow_mm",
    "streamflow_mm"
  )

  daily_totwatsed_df <- coerce_numeric_columns(daily_totwatsed_df, numeric_cols)
  
  totwatsed2wbal = daily_totwatsed_df %>% dplyr::select("runid",
                                                        "WY",
                                                        "Date",
                                                        "precipitation_mm",
                                                        "rain_melt_mm",
                                                        "transpiration_mm",
                                                        "evaporation_mm",
                                                        "percolation_mm",
                                                        "runoff_mm",
                                                        "lateral_flow_mm"
  )%>% dplyr::group_by(runid)%>% dplyr::filter(Date >= paste0(lubridate::year(Date[1]),"-10-01"))
  
  n_wys = totwatsed2wbal %>%
    dplyr::select(runid,WY) %>%
    dplyr::group_by(runid) %>% 
    dplyr::summarise(wys=n_distinct(WY))
  
  totwatsed2wbal = totwatsed2wbal %>%
    dplyr::select(- c(Date,WY))%>%
    dplyr::group_by(runid)%>%
    dplyr::summarise(dplyr::across(where(is.numeric), ~sum(.x, na.rm = TRUE))) 
  
  totwatsed2wbal = dplyr::left_join(totwatsed2wbal, n_wys, by = "runid")  %>%
    dplyr::mutate(
      precipitation_mm = precipitation_mm / wys,
      rain_melt_mm = rain_melt_mm / wys,
      transpiration_mm = transpiration_mm / wys,
      evaporation_mm = evaporation_mm / wys,
      percolation_mm = percolation_mm / wys,
      runoff_mm = runoff_mm / wys,
      lateral_flow_mm = lateral_flow_mm / wys) %>%
    dplyr::mutate(
      rain_melt_mm = rain_melt_mm / precipitation_mm * 100,
      transpiration_mm = transpiration_mm / precipitation_mm *
        100,
      evaporation_mm = evaporation_mm / precipitation_mm *
        100,
      percolation_mm = percolation_mm / precipitation_mm *
        100,
      runoff_mm = runoff_mm / precipitation_mm * 100,
      lateral_flow_mm = lateral_flow_mm / precipitation_mm *
        100,
      WbalErr_mm = rain_melt_mm - (
        transpiration_mm + evaporation_mm + percolation_mm + runoff_mm + lateral_flow_mm
      )
    ) %>%
    dplyr::rename(
      "Precipitation (mm)" = "precipitation_mm",
      "Rain+Melt (%)" = "rain_melt_mm",
      "Transpiration (%)" = "transpiration_mm",
      "Evaporation (%)" = "evaporation_mm",
      "Percolation (%)" = "percolation_mm",
      "Runoff(%)" = "runoff_mm",
      "Lateral flow(%)" = "lateral_flow_mm",
      "Change in storage (%)" = "WbalErr_mm"
    ) %>% dplyr::select(-wys)%>%
    # tidyr::gather(key = "variable",value = "value", -runid) %>% 
    dplyr::mutate(dplyr::across(where(is.numeric), round, 2))
  
  return(totwatsed2wbal)
} 

## --------------------------------------------------------------------------------------##
 
merge_daily_Vars <- function(totalwatsed_df, chanwb_df, ebe_df){
  daily<- dplyr::left_join(as.data.frame(totalwatsed_df), as.data.frame(chanwb_df), by = c("Date", "WY")) %>%
    dplyr::left_join(as.data.frame(ebe_df),  by = c("Date", "WY")) 
  daily <- coerce_numeric_columns(
    daily,
    c(
      "precipitation_mm",
      "rain_melt_mm",
      "transpiration_mm",
      "evaporation_mm",
      "percolation_mm",
      "runoff_mm",
      "lateral_flow_mm",
      "baseflow_mm",
      "streamflow_mm",
      "Inflow_chan_m3",
      "Outflow_chan_m3",
      "Storage_chan_m3",
      "Baseflow_chan_m3",
      "Loss_chan_m3",
      "Balance_chan_m3",
      "Q_outlet_mm",
      "P_ebe",
      "Runoff_ebe",
      "peak_ebe",
      "Sediment_ebe",
      "SRP_ebe",
      "PP_ebe",
      "TP_ebe",
      "Sediment_tonnes_ebe",
      "SRP_tonnes_ebe",
      "PP_tonnes_ebe",
      "TP_tonnes_ebe"
    )
  )
  # %>%
  #   dplyr::mutate_at(c("area_m_2",	"precip_vol_m_3",	"rain_melt_vol_m_3",	"transpiration_vol_m_3",
  #                      "evaporation_vol_m_3",	"percolation_vol_m_3",	"runoff_vol_m_3",	"lateral_flow_vol_m_3",
  #                      "storage_vol_m_3",	"sed_det_kg",	"sed_dep_kg",	"sed_del_kg",
  #                      "class_1",	"class_2",	"class_3",	"class_4",	"class_5",
  #                      "area_ha",	"cumulative_sed_del_tonnes",	"sed_del_density_tonne_ha",
  #                      "precipitation_mm",	"rain_melt_mm",	"transpiration_mm",	"evaporation_mm",	"et_mm",
  #                      "percolation_mm",	"runoff_mm",	"lateral_flow_mm",	"storage_mm",
  #                      "reservoir_volume_mm",	"baseflow_mm",	"aquifer_losses_mm",
  #                      "streamflow_mm",	"swe_mm",	"sed_del_tonne",	"p_load_mg",
  #                      "p_runoff_mg",	"p_lateral_mg",	"p_baseflow_mg",	"total_p_kg",
  #                      "particulate_p_kg",	"soluble_reactive_p_kg",	"p_total_kg_ha",	"particulate_p_kg_ha",
  #                      "soluble_reactive_p_kg_ha",	"Elmt_ID_chan",	"Chan_ID_chan",	"Inflow_chan",	"Outflow_chan",
  #                      "Storage_chan",	"Baseflow_chan",	"Loss_chan",	"Balance_chan",
  #                      "Q_outlet_mm",	"Day_ebe",	"P_ebe",	"Runoff_ebe",	"peak_ebe",
  #                      "Sediment_ebe",	"SRP_ebe",	"PP_ebe",	"TP_ebe",
  #                      "Sediment_tonnes_ebe",	"SRP_tonnes_ebe",	"PP_tonnes_ebe",
  #                      "TP_tonnes_ebe"),as.numeric)
  return(daily)
} 

## --------------------------------------------------------------------------------------##
## subset percent rows from dataframe head or tail
  
df_head_percent <- function(x, percent) {
  
  head(x, ceiling( nrow(x)*percent/100)) 
}

# last percent of a dataframe
df_tail_percent <- function(x, percent) {
  # need validation of input x and percent!! 
  tail(x, ceiling( nrow(x)*percent/100)) 
}

## --------------------------------------------------------------------------------------##
make_leaflet_map = function(plot_df, plot_var, col_pal_type, unit = NULL){
  v <- dplyr::enquo(plot_var)
  
  if (col_pal_type == "Factor") {
    pal <- colorFactor(palette = "inferno", dplyr::pull(plot_df, !!v))
    
  }else
    if (col_pal_type == "Numeric") {
      pal <- colorNumeric(palette = "inferno", dplyr::pull(plot_df, !!v))
      
    }else
      if (col_pal_type == "Bin") {
        pal <- colorBin(palette = "inferno", dplyr::pull(plot_df, !!v))
        
      }else
        if (col_pal_type == "Quantile") {
          pal <- colorQuantile(palette = "inferno", dplyr::pull(plot_df, !!v))
          
        }
  
  rlang::eval_tidy(rlang::quo_squash(quo({
    leaflet::leaflet(plot_df) %>% 
      # addPolygons(color = ~pal(dplyr::pull(plot_df, !!v)))%>%
      leaflet::addProviderTiles(leaflet::providers$Esri.WorldTopoMap)%>%
      leaflet::addPolygons(fillColor = ~pal(!!v),
                           weight = 2,
                           opacity =1,
                           color = "white",
                           dashArray = "3",
                           fillOpacity = 0.5,
                           group = as.character(dplyr::as_label(v)),
                           popup = ~paste("WeppID:", plot_df$wepp_id,
                                          "<br>",if(!is.null(unit)) {
                                            paste0(as_label(v)," (",unit,") ",":")
                                          }else{paste0(as_label(v),":")}, dplyr::pull(plot_df, !!v)),
                           label = ~paste("WeppID:", plot_df$wepp_id,
                                          "\n",
                                          if(!is.null(unit)) {
                                            paste0(as_label(v)," (",unit,") ",":")
                                          }else{paste0(as_label(v),":")}, dplyr::pull(plot_df, !!v)),
                           highlightOptions = leaflet::highlightOptions(weight = 3,
                                                                        color = "#000",
                                                                        dashArray = "",
                                                                        fillOpacity = 0.7,
                                                                        bringToFront = TRUE))%>%
      # addControl(as.character(dplyr::as_label(v)), position = "topright")%>%
      addLayersControl(position = "topleft",
                       overlayGroups = as.character(dplyr::as_label(v)),
                       options = layersControlOptions(collapsed = FALSE))
  })))
}

## --------------------------------------------------------------------------------------##
make_leaflet_map_multi = function(plot_df, plot_var, col_pal_type, unit = NULL){
  v <- dplyr::enquo(plot_var)

  if (col_pal_type == "Factor") {
    pal <- colorFactor(palette = "inferno", dplyr::pull(plot_df, !!v))

  }else
    if (col_pal_type == "Numeric") {
      pal <- colorNumeric(palette = "inferno", dplyr::pull(plot_df, !!v))

    }else
      if (col_pal_type == "Bin") {
        pal <- colorBin(palette = "inferno", dplyr::pull(plot_df, !!v))

      }else
        if (col_pal_type == "Quantile") {
          pal <- colorQuantile(palette = "inferno", dplyr::pull(plot_df, !!v))

        }

  rlang::eval_tidy(rlang::quo_squash(quo({
    leaflet::leaflet(plot_df) %>%
      addPolygons(color = ~pal(dplyr::pull(plot_df, !!v)))%>%
      leaflet::addProviderTiles(leaflet::providers$Esri.WorldTopoMap)%>%
      leaflet::addPolygons(fillColor = ~pal(!!v),
                           weight = 2,
                           opacity = 1,
                           color = "white",
                           dashArray = "3",
                           fillOpacity = 0.7,
                           popup = ~paste("WeppID:", plot_df$wepp_id,
                                          "<br>",
                                          "Watershed:", plot_df$Watershed,
                                          "<br>",
                                          "Scenario:", plot_df$scenario,
                                          "<br>",
                                          "runid:", plot_df$runid,
                                          "<br>",
                                          if(!is.null(unit)) {
                                            paste0(as_label(v)," (",unit,") ",":")
                                          }else{paste0(as_label(v),":")}, dplyr::pull(plot_df, !!v)),
                           label = ~paste("WeppID:", plot_df$wepp_id,
                                          "\n",
                                          if(!is.null(unit)) {
                                            paste0(as_label(v)," (",unit,") ",":")
                                          }else{paste0(as_label(v),":")}, dplyr::pull(plot_df, !!v)),
                           highlightOptions = leaflet::highlightOptions(weight = 3,
                                                                        color = "#000",
                                                                        dashArray = "",
                                                                        fillOpacity = 0.7,
                                                                        bringToFront = TRUE))%>%
      addLayersControl(position = "topleft",
                       overlayGroups = as.character(dplyr::as_label(v)),
                       options = layersControlOptions(collapsed = FALSE))
  })))
}

## --------------------------------------------------------------------------------------##
