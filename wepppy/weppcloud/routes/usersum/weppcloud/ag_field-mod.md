# `AgFields` mod

Model agricultural fields in WEPP within a watershed with crop schedule (observed climates over a period of time)

Resources stored in weppcloud `ag_fields` directory

## Additional Model Inputs

### GeoJSON of field boundaries within the watershed

- filename saved as `ag_fields\field_boundaries_geojson` property of AgFields
- rasterize to `ag_fields.field_boundaries`

### Rotation schedule (`rotation_schedule.tsv`)

- with field id and rotation by year info

### Crop managements (`ag_fields\crop_kv_lookup.tsv`)

- database of crop management files saved in `ag_fields\plant_files`
  - no spaces in filenames (`rename 's/ /-/g' *`)
- table with `crop_id` keys and `management_file` values

## Running fields as sub-fields

1. Generate WEPPcloud watershed containing the field boundaries with whitebox-tools delineation backend
   - Make sure climate observed `start_year` and `end_year` match the `rotation_schedule.tsv`
2. Rasterize `ag_fields.field_boundaries_geojson` to `ag_fields.field_boundaries`
3. Intersect `ag_fields.field_boundaries` with `watershed.subwta` to yield `ag_fields.sub_field_boundaries`
   - These "sub" fields will be treated sa hydrologically disconnected
   - filter out `sub_fields` smaller than some pre-determined area threshold `ag_fields.sub_field_min_area_threshold_m2`
4. Abstract the `sub_fields` to hillslopes generating slope files in `ag_fields\slope_files`
5. For each sub field hillslope
   - 5.1 Build multi-year management files
   - 5.2 use soil, climate from sub_fields `topaz` hillslope
   - 5.3 run hillslope in `wepp\ag_fields\runs` and generate outputs in `wepp\ag_fields\output`
6. Compile spatio-temporal outputs

## Data files `/wc1/runs/co/copacetic-note`

### `ag_fields/<field_boundaries_geojson>.geojson`
- `ag_fields/rotation_schedule.parquet`
- `ag_fields/field_boundaries.tif`

#### `ag_fields/rotation_schedule.parquet`
- the rotation schedule has rotations over several years as separate columns
- each field is a separate row and has a unique field id
e.g.
```
 #   Column      Non-Null Count  Dtype  
---  ------      --------------  -----  
 30  field_ID    2177 non-null   float64
 31  Crop2008    2177 non-null   object 
 32  Crop2009    2177 non-null   object 
 33  Crop2010    2177 non-null   object 
 34  Crop2011    2177 non-null   object 
 35  <rotation>    2177 non-null   object 
 ...
```

- Field ID is configurable as `AgFields.field_id_key`
- Crop<year> is accessed by `AgFields.crop_year_accessor.format(year)`
  - e.g 'Crop{}' and is set using `AgFields.set_crop_year_accessor`
  - the `rotation` columns have `crop_name`s

###

#### `ag_fields/field_boundaries.tif`
- raster with the field id burned in
- aligned with weppcloud project rasters

### Each field is divided into hydrologiccal sub fields `ag_fields/sub_fields` by PERIDOT

#### `ag_fields/sub_fields/sub_field_id_map.tif`
- intersection of subwta and field boundaries has sub field id keys

#### `fields.parquet` similiar to `watershed/hillslopes.parquet` but for fields

schema
```
 #   Column        Non-Null Count  Dtype  
---  ------        --------------  -----  
 0   field_id      8109 non-null   int64  
 1   topaz_id      8109 non-null   object 
 2   sub_field_id  8109 non-null   int64  
 3   slope_scalar  8109 non-null   float64
 4   length        8109 non-null   float64
 5   width         8109 non-null   float64
 6   direction     8109 non-null   float64
 7   aspect        8109 non-null   float64
 8   area          8109 non-null   float64
 9   elevation     8109 non-null   float64
 10  centroid_px   8109 non-null   int64  
 11  centroid_py   8109 non-null   int64  
 12  centroid_lon  8109 non-null   float64
 13  centroid_lat  8109 non-null   float64
 14  wepp_id       8109 non-null   int64  
 15  TopazID       8109 non-null   int64  
```

#### slope files from PERIDOT
- `ag_fields/sub_fields/slope_files`
- names convention is `field_{field_id}_{topaz_id}.slp`

(flowpaths and flowpaths table are also produced by PERIDOT but not used)

### plant_files (`.man`) user supplied plant database
- user uploads a zip archive
- the .zip files are extracted and converted to 98.4 format with normalized file names
- `ag_fields/plant_files` contains the 98.4 format managements
- `ag_fields/plant_files/2017.1` contains the 2017.1 format managements if they were supplied



## Weppcloud Controls

Upload GeoJSON

define field_id column
define crop lookup template
upload plants.zip
- extracts and converts to 98.4

build rotation table lookup



## Watershed model - Running subfields as OFEs
1. Calculate area of sub fields (there could be multiple)
   - order the sub fields by area in ascending order
   - if the area of the sub field is less than 1/8 the subcatchment's area disregard
   - determine if the sub field area is closest to 1/4, 1/3, 1/2, of 1/1 of the subcatchment
   - this become the division factor for breaking the hillslope into OFEs
   - use the inverse to determine how many OFEs (1/4 -> 4, 1/3 -> 3, 1/2 -> 2, 1/1 -> 1)
   - use the distance to channel map to detemine which OFE the sub field should be assigned to (e.g. bottom 1/2, middle 1/3, ...)
2. Hillslope prep fro sub-fields
   - MOFE slope file
   - MOFE soil file
   - MOFE management with the rotation schedule for the field
3. Run WEPP hillslopes and watershed as normal


### Hangman notes

Hangman is the weppcloud alpha project for developing AgFields

runid: dumbfounded-patentee

wd: /wc1/runs/du/dumbfounded-patentee/

## remaining for hangman

- [x] 1. Setup a new NoBbBase subclass AgFields to model and rasterize the geojson 
- [x] 2. Intersect the fields raster with the subwta to identify sub fields
- [ ] 3. write a program in peridot to abstract representative hillslopes (e.g. wepp slope file) for each subfield and a fields_hillslope.csv metadata. 
- [ ] 4. setup a routine in AgFields to prep the sub field hillslopes 
      - using the slope file from rust
      - the stacked managements from the rotation_schedule.tsv
      - the soil and the climate from the associated hillslope
- [ ] 4. setup routine in AgFields to run wepp


# all management files are 2017.1
(wepppy310-env) roger@forest.local:/wc1/runs/du/dumbfounded-patentee/ag_fields/plant_files$ head -n 1 *.man
==> alfalfa,spr-seeded,NT,-cm8-wepp.man <==
2017.1

==> barley,spr,MT,-cm8,-fchisel-wepp.man <==
2017.1

==> beans,spr,CONV,-cm8-wepp.man <==
2017.1

==> canola,spr,MT,-cm8-wepp.man <==
2017.1

==> chickpeas,spr,NT,-cm8-wepp.man <==
2017.1

==> lentils,spr,NT,-cm8-wepp.man <==
2017.1

==> oats,spr,-CONV,-cm8-wepp.man <==
2017.1

==> peas,spr,NT,-cm8-wepp.man <==
2017.1

==> wheat,spr,MT,-cm8,-fchisel-wepp.man <==
2017.1

==> wheat,winter,MT,-cm8-wepp.man <==
2017.1

