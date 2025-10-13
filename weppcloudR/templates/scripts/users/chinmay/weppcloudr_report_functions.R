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

gethillwatfiles<- function(runid){
  link <- paste0("/geodata/weppcloud_runs/", runid,"/wepp/output/")
  if (file.exists(link)) {
    wat_dat <- list.files(link, "*\\.wat.dat$", full.names=TRUE)
    
  }else{
    link = paste0("https://wepp.cloud/weppcloud/runs/", runid,"/cfg/browse/wepp/output/")
    pg <- rvest::read_html(link)
    wat_dat <- rvest::html_attr(rvest::html_nodes(pg, "a"), "href") %>%
      stringr::str_subset(".wat.dat", negate = FALSE)
    wat_dat <- paste0(link, wat_dat)
    
  }
  
  
  return(wat_dat)
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
  
  link <- paste0("/geodata/weppcloud_runs/", runid, "/export/arcmap/subcatchments.json")
  
    
  if (file.exists(link)) {
    geometry <- sf::st_read(link,quiet = TRUE)%>%
      dplyr::select(WeppID, geometry) %>%
      sf::st_transform(4326) %>%
      dplyr::group_by(WeppID)%>%
      dplyr::summarize(geometry = sf::st_union(geometry))
  }else{
  
  link <- paste0("https://wepp.cloud/weppcloud/runs/",
                 runid,
                 "/cfg/browse/export/arcmap/subcatchments.json")
  geometry <- sf::st_read(link,quiet = TRUE)%>%
    dplyr::select(WeppID, geometry) %>%
    sf::st_transform(4326) %>%
    dplyr::group_by(WeppID)%>%
    dplyr::summarize(geometry = sf::st_union(geometry))
  
  }
  return(geometry)
  
}

## --------------------------------------------------------------------------------------##

get_WatershedArea_m2 <- function(runid){
  #
  fn = paste0(
    "/geodata/weppcloud_runs/",
    runid,
    "/wepp/output/",
    "loss_pw0.txt"
  )
  
  if (file.exists(fn)) {
    getstring<- grep("Total contributing area to outlet ",
                     readLines(fn), value = TRUE)
    getstring <- getstring[[1]]
    num <- readr::parse_number(getstring)
    num <- as.numeric(num) * 10000 ##convert ha to m2
  }
  else{
    fn = paste0("https://wepp.cloud/weppcloud/runs/", runid,"/cfg/browse/wepp/output/loss_pw0.txt")
    getstring<- grep("Total contributing area to outlet ",
                     readLines(fn), value = TRUE)
    getstring <- getstring[[1]]
    num <- readr::parse_number(getstring)
    num <- as.numeric(num) * 10000 ##convert ha to m2
    }
  
return(num)
  
}

## --------------------------------------------------------------------------------------##

# Function to extract numbers from a character vector
extract_numbers <- function(strings) {
  numbers <- as.numeric(regmatches(strings, regexpr("[0-9]+", strings)))
  return(numbers)
}

get_cli_summary <- function(runid){
  #
  fn = paste0(
    "/geodata/weppcloud_runs/",
    runid,
    "/wepp/output/",
    "loss_pw0.txt"
  )
  
  
  if (file.exists(fn)) {
    
    linenumber = grep("AVERAGE ANNUAL basis",readLines(fn))[1]
    getstring<- readLines(con = fn)
  }else{
    fn = paste0("https://wepp.cloud/weppcloud/runs/", runid,"/cfg/browse/wepp/output/loss_pw0.txt")
    linenumber = grep("AVERAGE ANNUAL basis",readLines(fn))[1]
    getstring<- readLines(con = fn)
    
  }
  
  return(head(tail(getstring, n = -(linenumber - 1)), n = 6))
  
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
  
  chanwb_path = paste0("/geodata/weppcloud_runs/",
                       runid,
                       "/wepp/output/chanwb.out"
  )
  
  if (file.exists(chanwb_path)) {
    ## read channel and watershed water and sediment data
    
    chanwb <- data.table::fread(chanwb_path, skip = 11, header = F)
    
    ### set names of the dataframes
    
    colnames(chanwb) <- c("Year_chan", "Day_chan", "Elmt_ID_chan",
                          "Chan_ID_chan", "Inflow_chan", "Outflow_chan",
                          "Storage_chan", "Baseflow_chan", "Loss_chan",
                          "Balance_chan")
    
    
    
    chanwb <- chanwb %>% dplyr::mutate(Q_outlet_mm = (Outflow_chan/ Wshed_Area_m2 *1000),
                                       originDate = as.Date(paste0(Year_chan, "-01-01"),tz = "UTC") - lubridate::days(1),
                                       Date = as.Date(Day_chan, origin = originDate, tz = "UTC"),
                                       WY = get_WY(Date)) %>% dplyr::select(-originDate) %>%
      dplyr::select(Year_chan, Day_chan, Date, WY, everything())
  }else{
  
  chanwb_path= paste0("https://wepp.cloud/weppcloud/runs/",
                      runid,
         "/cfg/browse/wepp/output/chanwb.out"
  )
  
  ## read channel and watershed water and sediment data
  
  chanwb <- data.table::fread(chanwb_path, skip = 11, header = F)
  
  ### set names of the dataframes
  
  colnames(chanwb) <- c("Year_chan", "Day_chan", "Elmt_ID_chan",
                        "Chan_ID_chan", "Inflow_chan", "Outflow_chan",
                        "Storage_chan", "Baseflow_chan", "Loss_chan",
                        "Balance_chan")
  
  
  
  chanwb <- chanwb %>% dplyr::mutate(Q_outlet_mm = (Outflow_chan/ Wshed_Area_m2 *1000),
                                     originDate = as.Date(paste0(Year_chan, "-01-01"),tz = "UTC") - lubridate::days(1),
                                     Date = as.Date(Day_chan, origin = originDate, tz = "UTC"),
                                     WY = get_WY(Date)) %>% dplyr::select(-originDate) %>%
    dplyr::select(Year_chan, Day_chan, Date, WY, everything())
  
  }
  
  return(as.data.frame(chanwb))
  
} 

## --------------------------------------------------------------------------------------##
## older function that read subcatchments file
# read_subcatchments = function(runid) {
#   link = paste0("/geodata/weppcloud_runs/", runid, "/export/arcmap/subcatchments.WGS.json")
#   link_utm = paste0("/geodata/weppcloud_runs/", runid, "/export/arcmap/subcatchments.json")
#   
#   
#   ## location to parse from if running locally
#   link_l = paste0("https://wepp.cloud/weppcloud/runs/",runid, "/cfg/browse/export/arcmap/subcatchments.WGS.json")
#   link_utm_l = paste0("https://wepp.cloud/weppcloud/runs/",runid, "/cfg/browse/export/arcmap/subcatchments.json")
#   
#   
#   subcatchments <- NULL
#   if (file.exists(link)) {
#     subcatchments <- sf::st_read(link,quiet = TRUE)
#     phosporus_flag = paste0("/geodata/weppcloud_runs/",runid, "/wepp/runs/phosphorus.txt")
#     ermit_texture_csv = paste0("/geodata/weppcloud_runs/", runid,"/export/", 
#                                paste0("ERMiT_input_", runid,".csv"))
#   } else if (file.exists(link_utm)) {
#     subcatchments <- sf::st_read(link_utm,quiet = TRUE)
#     phosporus_flag = paste0("/geodata/weppcloud_runs/",runid, "/wepp/runs/phosphorus.txt")
#     ermit_texture_csv = paste0("/geodata/weppcloud_runs/", runid,"/export/", 
#                                paste0("ERMiT_input_", runid,".csv"))
#   } else if(file.exists(link_l)){
#     subcatchments <- sf::st_read(link_l,quiet = TRUE)
#     phosporus_flag = paste0("https://wepp.cloud/weppcloud/runs/",runid, "/cfg/browse/wepp/runs/phosphorus.txt")
#     ermit_texture_csv = paste0("https://wepp.cloud/weppcloud/runs/", runid,"/cfg/browse/export/",paste0("ERMiT_input_", runid,".csv/?raw"))
#   }else{
#     subcatchments <- sf::st_read(link_utm_l,quiet = TRUE)
#     phosporus_flag = paste0("https://wepp.cloud/weppcloud/runs/",runid, "/cfg/browse/wepp/runs/phosphorus.txt")
#     ermit_texture_csv = paste0("https://wepp.cloud/weppcloud/runs/", runid,"/cfg/browse/export/",paste0("ERMiT_input_", runid,".csv/?raw"))
#   }
#   
#   subcatchments <- st_transform(subcatchments, 4326)
#   
#   geom_sum <- subcatchments %>%
#     group_by(WeppID) %>%
#     summarize(geometry = st_union(geometry)) 
#   
#   geom_sum <- geom_sum %>%
#     left_join(subcatchments %>%
#                 as.data.frame() %>%
#                 select(-geometry) %>%
#                 distinct(), by = "WeppID")
#   
#   geom_sum <- geom_sum %>%
#     separate(soil, c("x1", "x2", "x3", "x4"), sep = ",", fill = "right") %>%
#     mutate(Soil = ifelse(grepl("slopes", x2), x1, paste(x1, x2, sep = ",")),
#            Gradient = ifelse(grepl("slopes", x2), x2,
#                              ifelse(grepl("slopes", x3), x3, "Refer to the soil file for details")),
#            Texture = ifelse(grepl("slopes", x2), x3, x4),
#            Texture = replace_na(Texture, "Refer to the soil file for details"),
#            Gradient = replace_na(Gradient, "Refer to the soil file for details"),
#            Soil = str_remove(Soil, ",NA")) %>%
#     select(-c(wepp_id, x1, x2, x3, x4)) %>%
#     clean_names() %>%
#     mutate(soil = str_replace(soil, "-", " ")) %>%
#     mutate(across(contains('_kg_ha'), list(kg = ~ .*area_ha)))
#   # print(phosporus_flag)
#   if (file.exists(phosporus_flag)) {
# 
# 
#     geom_sum = geom_sum %>% dplyr::rename("Particulate_Phosphorus_kg" ="pp_kg_ha_kg",
#                                           "Soluble_Reactive_Phosohorus_kg"= "srp_kg_ha_kg",
#                                           "Sediment_Deposition_kg" = "sd_dp_kg_ha_kg",
#                                           "Sediment_Yield_kg"= "sd_yd_kg_ha_kg",
#                                           "Soil_Loss_kg" = "so_ls_kg_ha_kg",
#                                           "Total_Phosphorus_kg" = "tp_kg_ha_kg")
# 
#   }else{
#     geom_sum = geom_sum %>% dplyr::rename("Sediment_Deposition_kg" = "sd_dp_kg_ha_kg",
#                                           "Sediment_Yield_kg"= "sd_yd_kg_ha_kg",
#                                           "Soil_Loss_kg" = "so_ls_kg_ha_kg")
#   }
# 
#   if (file.exists(ermit_texture_csv)) {
# 
#     ermit_texture = data.table::fread(ermit_texture_csv, sep = ",")
# 
#     ermit_texture = ermit_texture %>%
#       dplyr::select(HS_ID,SOIL_TYPE)%>%
#       dplyr::rename("Texture" = "SOIL_TYPE",
#                     "wepp_id" = "HS_ID")
# 
#     geom_sum = dplyr::left_join(geom_sum, ermit_texture, by ="wepp_id")%>%
#       dplyr::rename("Texture_string" = "Texture.x",
#                     "Texture" = "Texture.y")
# 
#   }else{
#     geom_sum = geom_sum
#   }
#   
#   return(geom_sum)
#   
# }

## updated function to read subcatchments file with updated variable names (10/11/2023)

read_subcatchments = function(runid) {
  link = paste0("/geodata/weppcloud_runs/", runid, "/export/arcmap/subcatchments.WGS.json")
  link_utm = paste0("/geodata/weppcloud_runs/", runid, "/export/arcmap/subcatchments.json")
  
  
  ## location to parse from if running locally
  link_l = paste0("https://wepp.cloud/weppcloud/runs/",runid, "/cfg/browse/export/arcmap/subcatchments.WGS.json")
  link_utm_l = paste0("https://wepp.cloud/weppcloud/runs/",runid, "/cfg/browse/export/arcmap/subcatchments.json")
  
  
  subcatchments <- NULL
  if (file.exists(link)) {
    subcatchments <- sf::st_read(link,quiet = TRUE)
    phosporus_flag = paste0("/geodata/weppcloud_runs/",runid, "/wepp/runs/phosphorus.txt")
    ermit_texture_csv = paste0("/geodata/weppcloud_runs/", runid,"/export/", 
                               paste0("ERMiT_input_", runid,".csv"))
  } else if (file.exists(link_utm)) {
    subcatchments <- sf::st_read(link_utm,quiet = TRUE)
    phosporus_flag = paste0("/geodata/weppcloud_runs/",runid, "/wepp/runs/phosphorus.txt")
    ermit_texture_csv = paste0("/geodata/weppcloud_runs/", runid,"/export/", 
                               paste0("ERMiT_input_", runid,".csv"))
  } else if(file.exists(link_l)){
    subcatchments <- sf::st_read(link_l,quiet = TRUE)
    phosporus_flag = paste0("https://wepp.cloud/weppcloud/runs/",runid, "/cfg/browse/wepp/runs/phosphorus.txt")
    ermit_texture_csv = paste0("https://wepp.cloud/weppcloud/runs/", runid,"/cfg/browse/export/",paste0("ERMiT_input_", runid,".csv/?raw"))
  }else{
    subcatchments <- sf::st_read(link_utm_l,quiet = TRUE)
    phosporus_flag = paste0("https://wepp.cloud/weppcloud/runs/",runid, "/cfg/browse/wepp/runs/phosphorus.txt")
    ermit_texture_csv = paste0("https://wepp.cloud/weppcloud/runs/", runid,"/cfg/browse/export/",paste0("ERMiT_input_", runid,".csv/?raw"))
  }
  
  subcatchments <- st_transform(subcatchments, 4326)
  
  geom_sum <- subcatchments %>%
    group_by(WeppID) %>%
    summarize(geometry = st_union(geometry)) 
  
  geom_sum <- geom_sum %>%
    left_join(subcatchments %>%
                as.data.frame() %>%
                select(-geometry) %>%
                distinct(), by = "WeppID")
  
  geom_sum <- geom_sum %>%
    separate(soil, c("x1", "x2", "x3", "x4"), sep = ",", fill = "right") %>%
    mutate(Soil = ifelse(grepl("slopes", x2), x1, paste(x1, x2, sep = ",")),
           Gradient = ifelse(grepl("slopes", x2), x2,
                             ifelse(grepl("slopes", x3), x3, "Refer to the soil file for details")),
           Texture = ifelse(grepl("slopes", x2), x3, x4),
           Texture = replace_na(Texture, "Refer to the soil file for details"),
           Gradient = replace_na(Gradient, "Refer to the soil file for details"),
           Soil = str_remove(Soil, ",NA")) %>%
    select(-c(wepp_id, x1, x2, x3, x4)) %>%
    clean_names() %>%
    mutate(soil = str_replace(soil, "-", " ")) %>%
    mutate(across(contains('_kg_ha'), list(kg = ~ .*area_ha)))
  print(phosporus_flag)
  if (file.exists(phosporus_flag)) {
    list_to_lookup = c(Particulate_Phosphorus_kg ="pp_kg_ha_kg",
                       Particulate_Phosphorus_kg ="particulate_p_kg_ha_kg",
                       Soluble_Reactive_Phosohorus_kg= "srp_kg_ha_kg",
                       Soluble_Reactive_Phosohorus_kg= "solub_react_p_kg_ha_kg",
                       Sediment_Yield_kg= "sd_yd_kg_ha_kg",
                       Sediment_Yield_kg= "sediment_yield_kg_ha_kg",
                       Soil_Loss_kg = "so_ls_kg_ha_kg",
                       Soil_Loss_kg = "soil_loss_kg_ha_kg",
                       Sediment_Deposition_kg = "sd_dp_kg_ha_kg",
                       Sediment_Deposition_kg = "sediment_deposition_kg_ha_kg",
                       Total_Phosphorus_kg = "tp_kg_ha_kg",
                       Total_Phosphorus_kg = "total_p_kg_ha_kg")
    geom_sum = geom_sum %>% dplyr::rename(dplyr::any_of(list_to_lookup))
    
  }else{
    list_to_lookup = c(Sediment_Deposition_kg = "sd_dp_kg_ha_kg",
                       Sediment_Deposition_kg = "sediment_deposition_kg_ha_kg",
                       Sediment_Yield_kg= "sd_yd_kg_ha_kg",
                       Sediment_Yield_kg= "sediment_yield_kg_ha_kg",
                       Soil_Loss_kg = "so_ls_kg_ha_kg",
                       Soil_Loss_kg = "soil_loss_kg_ha_kg")
    geom_sum = geom_sum %>% dplyr::rename(dplyr::any_of(list_to_lookup))
  }
  
  if (file.exists(ermit_texture_csv)) {
    
    ermit_texture = data.table::fread(ermit_texture_csv, sep = ",")
    
    ermit_texture = ermit_texture %>%
      dplyr::select(HS_ID,SOIL_TYPE)%>%
      dplyr::rename("Texture" = "SOIL_TYPE",
                    "wepp_id" = "HS_ID")
    
    geom_sum = dplyr::left_join(geom_sum, ermit_texture, by ="wepp_id")%>%
      dplyr::rename("Texture_string" = "Texture.x",
                    "Texture" = "Texture.y")
    
  }else{
    geom_sum = geom_sum
  }
  
  return(geom_sum)
  
}


## --------------------------------------------------------------------------------------##

read_subcatchments_map = function(runid){
  
  link = paste0("/geodata/weppcloud_runs/", runid, "/export/arcmap/subcatchments.json")
  
  phosporus_flag = paste0("/geodata/weppcloud_runs/",runid, "/wepp/runs/phosphorus.txt")
  
  ermit_texture_csv = paste0("/geodata/weppcloud_runs/", runid,"/export/", 
                             paste0("ERMiT_input_", runid,".csv"))
  
  
  if(file.exists(link)){
    
    subcatchments <- sf::st_read(link,quiet = TRUE)
    
    subcatchments = subcatchments%>%sf::st_transform(4326)
    
    geom_sum = subcatchments%>%
      dplyr::group_by(WeppID)%>%
      dplyr::summarize(geometry = sf::st_union(geometry))
    
    subcatchments = subcatchments %>% as.data.frame() %>% 
      dplyr::select(-geometry)%>% dplyr::distinct()
    
    geom_sum = dplyr::left_join(geom_sum, subcatchments, by =c("WeppID"))
    
    geom_sum = geom_sum %>% tidyr::separate(soil,
                                            c("x1", "x2", "x3", "x4"),
                                            sep = ",",
                                            fill="right" )%>% 
      dplyr::mutate(Soil= case_when(grepl("slopes", x2)==TRUE~x1,
                                    grepl("slopes", x2)==FALSE~paste(x1,x2,sep=",")),
                    Gradient = case_when((grepl("slopes", x2)==TRUE)~x2,
                                         (grepl("slopes", x2)==FALSE & grepl("slopes", x3)==TRUE)~x3),
                    Texture = case_when((grepl("slopes", x2)==TRUE)~x3,
                                        (grepl("slopes", x2)==FALSE)~x4),
                    Texture = replace_na(Texture, "Refer to the soil file for details"),
                    Gradient = replace_na(Gradient, "Refer to the soil file for details"),
                    Soil = str_remove(Soil, ",NA"))%>%
      # dplyr::rename("Texture_from_string" = "Texture") %>%
      dplyr::select(-c(wepp_id,x1,x2,x3,x4))%>%
      janitor::clean_names()%>%
      dplyr::mutate(soil = stringr::str_replace(soil,pattern = "-"," "),
                    runid = runid)%>% 
      dplyr::mutate(dplyr::across(dplyr::contains('_kg_ha'),
                                  .fns = list(kg = ~.*area_ha)))
    
    if (file.exists(phosporus_flag)) {
      
      
      geom_sum = geom_sum %>% dplyr::rename("Particulate_Phosphorus_kg" ="pp_kg_ha_kg",
                                            "Soluble_Reactive_Phosohorus_kg"= "srp_kg_ha_kg",
                                            "Sediment_Deposition_kg" = "sd_dp_kg_ha_kg",
                                            "Sediment_Yield_kg"= "sd_yd_kg_ha_kg",
                                            "Soil_Loss_kg" = "so_ls_kg_ha_kg",
                                            "Total_Phosphorus_kg" = "tp_kg_ha_kg")
      
    }else{
      geom_sum = geom_sum %>% dplyr::rename("Sediment_Deposition_kg" = "sd_dp_kg_ha_kg",
                                            "Sediment_Yield_kg"= "sd_yd_kg_ha_kg",
                                            "Soil_Loss_kg" = "so_ls_kg_ha_kg")
    }
    
    if (file.exists(ermit_texture_csv)) {
      
      ermit_texture = data.table::fread(ermit_texture_csv ,sep = ",")
      
      ermit_texture = ermit_texture %>%
        dplyr::select(HS_ID,SOIL_TYPE)%>%
        dplyr::rename("Texture" = "SOIL_TYPE",
                      "wepp_id" = "HS_ID")
      
      geom_sum = dplyr::left_join(geom_sum, ermit_texture, by ="wepp_id")%>% 
        dplyr::rename("Texture_string" = "Texture.x",
                      "Texture" = "Texture.y")
      
    }else{
      geom_sum = geom_sum 
    }
    
  }else{
    link <- paste0("https://wepp.cloud/weppcloud/runs/",runid, "/cfg/browse/export/arcmap/subcatchments.json")
    
    phosporus_flag = paste0("https://wepp.cloud/weppcloud/runs/",runid, "/cfg/browse/wepp/runs/phosphorus.txt")
    
    ermit_texture_csv = paste0("https://wepp.cloud/weppcloud/runs/", runid,"/cfg/browse/export/",paste0("ERMiT_input_", runid,".csv/?raw"))
    
    subcatchments <- sf::st_read(link,quiet = TRUE)
    
    subcatchments = subcatchments%>%sf::st_transform(4326)
    
    geom_sum = subcatchments%>%
      dplyr::group_by(WeppID)%>%
      dplyr::summarize(geometry = sf::st_union(geometry))
    
    subcatchments = subcatchments %>% as.data.frame() %>% 
      dplyr::select(-geometry)%>% dplyr::distinct()
    
    geom_sum = dplyr::left_join(geom_sum, subcatchments, by =c("WeppID"))
    
    geom_sum = geom_sum %>% tidyr::separate(soil,
                                            c("x1", "x2", "x3", "x4"),
                                            sep = ",",
                                            fill="right" )%>% 
      dplyr::mutate(Soil= case_when(grepl("slopes", x2)==TRUE~x1,
                                    grepl("slopes", x2)==FALSE~paste(x1,x2,sep=",")),
                    Gradient = case_when((grepl("slopes", x2)==TRUE)~x2,
                                         (grepl("slopes", x2)==FALSE & grepl("slopes", x3)==TRUE)~x3),
                    Texture = case_when((grepl("slopes", x2)==TRUE)~x3,
                                        (grepl("slopes", x2)==FALSE)~x4),
                    Texture = replace_na(Texture, "Refer to the soil file for details"),
                    Gradient = replace_na(Gradient, "Refer to the soil file for details"),
                    Soil = str_remove(Soil, ",NA"))%>%
      # dplyr::rename("Texture_from_string" = "Texture") %>%
      dplyr::select(-c(wepp_id,x1,x2,x3,x4))%>%
      janitor::clean_names()%>%
      dplyr::mutate(soil = stringr::str_replace(soil,pattern = "-"," "),
                    runid = runid)%>% 
      dplyr::mutate(dplyr::across(dplyr::contains('_kg_ha'),
                                  .fns = list(kg = ~.*area_ha)))
    
    if (file.exists(phosporus_flag)) {
      
      geom_sum = geom_sum %>% dplyr::rename("Particulate_Phosphorus_kg" ="pp_kg_ha_kg",
                                            "Soluble_Reactive_Phosohorus_kg"= "srp_kg_ha_kg",
                                            "Sediment_Deposition_kg" = "sd_dp_kg_ha_kg",
                                            "Sediment_Yield_kg"= "sd_yd_kg_ha_kg",
                                            "Soil_Loss_kg" = "so_ls_kg_ha_kg",
                                            "Total_Phosphorus_kg" = "tp_kg_ha_kg")
      
    }else{
      geom_sum = geom_sum %>% dplyr::rename("Sediment_Deposition_kg" = "sd_dp_kg_ha_kg",
                                            "Sediment_Yield_kg"= "sd_yd_kg_ha_kg",
                                            "Soil_Loss_kg" = "so_ls_kg_ha_kg")
    }
    
    if (file.exists(ermit_texture_csv)) {

      ermit_texture = data.table::fread(ermit_texture_csv ,sep = ",")

      ermit_texture = ermit_texture %>%
        dplyr::select(HS_ID,SOIL_TYPE)%>%
        dplyr::rename("Texture" = "SOIL_TYPE",
                      "wepp_id" = "HS_ID")

      geom_sum = dplyr::left_join(geom_sum, ermit_texture, by ="wepp_id")%>%
        dplyr::rename("Texture_string" = "Texture.x",
                      "Texture" = "Texture.y")

    }else{
      geom_sum = geom_sum
    }
    
  }
  
  return(geom_sum)
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

process_ebe <- function(runid, yr_start, yr_end){
  
  ebe_path = paste0("/geodata/weppcloud_runs/",
                    runid,
                    "/wepp/output/ebe_pw0.txt")
  
  if(file.exists(ebe_path)){
    ## read channel and watershed water and sediment data
    # , SimStartDate, SimEndDate, SimStartDate, SimEndDate
    ebe <- data.table::fread(ebe_path, skip = 9, header = F)
    
    ### set names of the dataframe
    
    if (ncol(ebe) == 11){
      colnames(ebe) <- c("Day_ebe", "Month_ebe", "Year_ebe",
                         "P_ebe", "Runoff_ebe", "peak_ebe", "Sediment_ebe",
                         "SRP_ebe", "PP_ebe", "TP_ebe", "col11")
    }else{
    colnames(ebe) <- c("Day_ebe", "Month_ebe", "Year_ebe",
                       "P_ebe", "Runoff_ebe", "peak_ebe", "Sediment_ebe",
                       "SRP_ebe", "PP_ebe", "TP_ebe")}
    
    dt_head_d = as.character(head(ebe,1)[[1]])
    dt_head_m = as.character(head(ebe,1)[[2]])
    dt_tail_d = as.character(tail(ebe,1)[[1]])
    dt_tail_m = as.character(tail(ebe,1)[[2]])
    
    # calcs
    ebe <- ebe %>% dplyr::mutate(Date = seq(from = as.Date(paste0(yr_start,"-",dt_head_m,"-",dt_head_d)), 
                                            to = as.Date(paste0(yr_end,"-",dt_tail_m,"-",dt_tail_d)), by= 1),
                                 WY = get_WY(Date),
                                 Sediment_tonnes_ebe = Sediment_ebe/1000,
                                 SRP_tonnes_ebe = SRP_ebe/1000,
                                 PP_tonnes_ebe = PP_ebe/1000,
                                 TP_tonnes_ebe = TP_ebe/1000) %>%
      dplyr::select(Day_ebe, Month_ebe, Year_ebe, Date, WY, everything())
  }else{
    ## read channel and watershed water and sediment data
    # , SimStartDate, SimEndDate, SimStartDate, SimEndDate
    ebe <- data.table::fread(paste0("https://wepp.cloud/weppcloud/runs/",runid,
                                    "/cfg/browse/wepp/output/ebe_pw0.txt"), skip = 9, header = F)
    
    ### set names of the dataframe
    
    if (ncol(ebe) == 11){
      colnames(ebe) <- c("Day_ebe", "Month_ebe", "Year_ebe",
                         "P_ebe", "Runoff_ebe", "peak_ebe", "Sediment_ebe",
                         "SRP_ebe", "PP_ebe", "TP_ebe", "col11")
    }else{
      colnames(ebe) <- c("Day_ebe", "Month_ebe", "Year_ebe",
                         "P_ebe", "Runoff_ebe", "peak_ebe", "Sediment_ebe",
                         "SRP_ebe", "PP_ebe", "TP_ebe")}
    
    dt_head_d = as.character(head(ebe,1)[[1]])
    dt_head_m = as.character(head(ebe,1)[[2]])
    dt_tail_d = as.character(tail(ebe,1)[[1]])
    dt_tail_m = as.character(tail(ebe,1)[[2]])
    
    # calcs
    ebe <- ebe %>% dplyr::mutate(Date = seq(from = as.Date(paste0(yr_start,"-",dt_head_m,"-",dt_head_d)), 
                                            to = as.Date(paste0(yr_end,"-",dt_tail_m,"-",dt_tail_d)), by= 1),
                                 WY = get_WY(Date),
                                 Sediment_tonnes_ebe = Sediment_ebe/1000,
                                 SRP_tonnes_ebe = SRP_ebe/1000,
                                 PP_tonnes_ebe = PP_ebe/1000,
                                 TP_tonnes_ebe = TP_ebe/1000) %>%
      dplyr::select(Day_ebe, Month_ebe, Year_ebe, Date, WY, everything())
  }
  
  
  
  return(as.data.frame(ebe))
  
}
## --------------------------------------------------------------------------------------##
process_totalwatsed <- function(runid){
  
  totalwatsed_fn = paste0("/geodata/weppcloud_runs/", runid, "/export/totalwatsed.csv")
  totalwatsed2_fn = paste0("/geodata/weppcloud_runs/", runid, "/export/totalwatsed2.csv")
  
  totalwatsed_fn_l = paste0("https://wepp.cloud/weppcloud/runs/", runid, "/cfg/resources/wepp/totalwatsed.csv")
  totalwatsed2_fn_l = paste0("https://wepp.cloud/weppcloud/runs/", runid, "/cfg/resources/wepp/totalwatsed2.csv")
  
  if (file.exists(totalwatsed_fn)) {
    totalwatseddf <- data.table::fread(totalwatsed_fn) %>% 
      janitor::clean_names()%>%
      dplyr::rename("WY" = "water_year")%>%
      dplyr::mutate(Date = lubridate::make_date(year,mo,da))
  } else 
    if(file.exists(totalwatsed2_fn)){
      totalwatseddf <- data.table::fread(totalwatsed2_fn) %>% 
        janitor::clean_names()%>%
        dplyr::rename("WY" = "water_year")%>%
        dplyr::mutate(Date = lubridate::make_date(year,month,day))
    }else
      if(file.exists(totalwatsed_fn_l)){
    totalwatseddf <- data.table::fread(totalwatsed_fn_l) %>% 
      janitor::clean_names()%>%
      dplyr::rename("WY" = "water_year")%>%
      dplyr::mutate(Date = lubridate::make_date(year,mo,da))
      }else{
        totalwatseddf <- data.table::fread(totalwatsed2_fn_l) %>% 
          janitor::clean_names()%>%
          dplyr::rename("WY" = "water_year") %>%
          dplyr::mutate(Date = lubridate::make_date(year,month,day))
      }
  return(totalwatseddf)
  
}

## --------------------------------------------------------------------------------------##
process_totalwatsed_map_df <- function(runid){
  
  totalwatsed_fn = paste0("/geodata/weppcloud_runs/", runid, "/export/totalwatsed.csv")
  
  if (file.exists(totalwatsed_fn)) {
    totalwatseddf <- data.table::fread(totalwatsed_fn) %>% 
      janitor::clean_names()%>%
      dplyr::rename("WY" = "water_year")%>%
      dplyr::mutate(Date = lubridate::make_date(year,mo,da),
                    runid= runid)
  } else {
    totalwatseddf <- data.table::fread(paste0("https://wepp.cloud/weppcloud/runs/", runid, "/cfg/resources/wepp/totalwatsed.csv")) %>% 
      janitor::clean_names()%>%
      dplyr::rename("WY" = "water_year")%>%
      dplyr::mutate(Date = lubridate::make_date(year,mo,da),
                    runid = runid)
  }
  return(totalwatseddf)
  
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

