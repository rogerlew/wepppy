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
    dplyr::summarise_all(.funs = sum, na.rm = TRUE) %>%
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

  hills <- arrow::read_parquet(hills_path)
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
  hills <- hills %>%
    dplyr::mutate(
      TopazID = as.integer(TopazID),
      wepp_id = as.integer(wepp_id),
      area_ha = as.numeric(area / 10000),
      slope_percent = as.numeric(slope_scalar * 100),
    ) %>%
    dplyr::select(TopazID, wepp_id, area_ha, slope_percent)

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

  subcatchments <- subcatchments %>%
    dplyr::left_join(hills, by = "TopazID") %>%
    dplyr::left_join(landuse, by = "TopazID") %>%
    dplyr::left_join(soils, by = "TopazID") %>%
    dplyr::mutate(
      wepp_id = as.integer(dplyr::coalesce(wepp_id, WeppID)),
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

  c_plt_df = subcatch %>%
      # as.data.frame()%>%
      dplyr::select(wepp_id,!!var_to_use,area_ha,geometry,landuse,soil,Texture,slope)%>%
      dplyr::arrange(desc(!!var_to_use)) %>%
      dplyr::mutate(cumPercArea = cumsum(area_ha) / sum(area_ha) *100,
                    new_col = cumsum(!!var_to_use) / sum(!!var_to_use) *100)%>%
    dplyr::mutate_at(vars(new_col), ~replace(., is.nan(.), 0))%>%
    dplyr::mutate(dplyr::across(where(is.numeric), round, 1))%>%
    dplyr::select(wepp_id,!!var_to_use,area_ha,geometry,cumPercArea,new_col,landuse,
                  soil,Texture,slope)
  
  colnames(c_plt_df)[6] = paste0("cum_",colnames(c_plt_df)[2])
  
  return(c_plt_df)

}

## --------------------------------------------------------------------------------------##
gen_cumulative_plt_df_map <- function(subcatch, var_to_use){
  
  var_to_use = dplyr::enquo(var_to_use)
  
  c_plt_df = subcatch %>%
    dplyr::group_by(Watershed, scenario)%>%
    # dplyr::select(wepp_id,!!var_to_use,area_ha,geometry,landuse,soil,Texture,slope)%>%
    dplyr::arrange(desc(!!var_to_use)) %>%
    dplyr::mutate(cumPercArea = cumsum(area_ha) / sum(area_ha) *100,
                  new_col = cumsum(!!var_to_use) / sum(!!var_to_use) *100)%>%
    dplyr::mutate_at(vars(new_col), ~replace(., is.nan(.), 0))%>%
    dplyr::mutate(dplyr::across(where(is.numeric), round, 1))%>%
    dplyr::select(wepp_id,!!var_to_use,area_ha,geometry,cumPercArea,new_col,landuse,
    soil,Texture,slope,Watershed,scenario,sd_yd_kg_ha,tp_kg_ha)%>%
    ungroup()
  
  colnames(c_plt_df)[6] = paste0("cum_",colnames(c_plt_df)[2])
  
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
    dplyr::as_tibble() %>%
    dplyr::mutate(
      Date = lubridate::make_date(year, month, day_of_month),
      WY = water_year,
      precipitation_mm = Precipitation,
      rain_melt_mm = `Rain+Melt`,
      transpiration_mm = Transpiration,
      evaporation_mm = Evaporation,
      percolation_mm = Percolation,
      runoff_mm = Runoff,
      lateral_flow_mm = `Lateral Flow`,
      baseflow_mm = Baseflow,
      streamflow_mm = Streamflow
    )

  if ("day_of_month" %in% names(totals)) {
    totals <- totals %>% dplyr::rename(day = day_of_month)
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
    dplyr::summarise_all(.funs = sum) %>%
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
    dplyr::summarise_all(.funs = sum) 
  
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
