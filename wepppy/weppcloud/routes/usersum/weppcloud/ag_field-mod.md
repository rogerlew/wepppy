# `AgFields` mod

Model fields within a watershed with crop schedule (observed climates over a period of time)

Resources stored in weppcloud `ag_fields` directory

## Additional Model Inputs

### GeoJSON of field boundaries within the watershed

- `field_id` of some sort
- filename saved as `ag_fields\field_boundaries_geojson` property of AgFields
- rasterize to `ag_fields.field_boundaries`

### Rotation schedule (`rotation_schedule.tsv`)

- table with `field_id`, `year`, and `crop_id`

### Crop managements (`ag_fields\crop_kv_lookup.tsv`)

- database of crop management files saved in `ag_fields\plant_files`
- table with `crop_id` keys and `management_file` values

## Running fields as sub-fields

1. Generate WEPPcloud watershed containing the field boundaries with whitebox-tools delineation backend
   - Make sure climate observed `start_year` and `end_year` match the `rotation_schedule.tsv`
2. Rasterize `ag_fields.field_boundaries_geojson` to `ag_fields.field_boundaries`
3. Intersect `ag_fields.field_boundaries` with `watershed.subwta` to yield `ag_fields.sub_field_boundaries`
   - These "sub" fields will be treated sa hydrologically disconnected
   - filter out `sub_fields` smaller than some pre-determined area threshold `ag_fields.sub_field_area_threshold_m2`
4. Abstract the `sub_fields` to hillslopes
5. For each sub field hillslope
   - 5.1 Build multi-year management files
   - 5.2 use soil, climate from sub_fields `topaz` hillslope
   - 5.3 run hillslope in `wepp\ag_fields\runs` and generate outputs in `wepp\ag_fields\output`
6. Compile spatio-temporal outputs

## Watershed model - Running subfields as OFEs
1. Calculate area of sub fields
   - if the area of the sub field is less than 1/8 the subcatchment's area disregard
   - determine if the sub field area is closest to 1/4, 1/3, 1/2, of 1/1 of the subcatchment
   - use the inverse to determine how many OFEs (1/4 -> 4, 1/3 -> 3, 1/2 -> 2, 1/1 -> 1)
   - use the distance to channel map to detemine which OFE the sub field should be assigned to (e.g. bottom 1/2, middle 1/3, ...)
2. Hillslope prep fro sub-fields
   - MOFE slope file
   - MOFE soil file
   - MOFE management with the rotation schedule for the field
3. Run WEPP hillslopes and watershed as normal


### Hangman notes

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

