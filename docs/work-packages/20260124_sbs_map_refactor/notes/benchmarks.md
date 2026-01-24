# SBS Map Benchmarks

Generated: 2026-01-24 03:16:10

## Summary

### prediction_wgs84_merged.tif

| Step | Seconds | Notes |
| --- | --- | --- |
| sbs_map_sanity_check | 236.573 | [0, 'Map has valid classes'] |
| get_sbs_color_table | 195.130 |  |
| SoilBurnSeverityMap.__init__ | 202.156 | ok |
| SoilBurnSeverityMap.class_map | 0.000 |  |
| SoilBurnSeverityMap.class_pixel_map | 0.000 |  |
| SoilBurnSeverityMap.data | 883.160 |  |
| SoilBurnSeverityMap.export_4class_map | 933.545 |  |
| export_size_bytes | 11092361 | /tmp/sbs-bench-kkjg8zgk/prediction_wgs84_merged.4class.tif |

### Rattlesnake.tif

| Step | Seconds | Notes |
| --- | --- | --- |
| sbs_map_sanity_check | 0.408 | [0, 'Map has valid color table'] |
| get_sbs_color_table | 0.185 |  |
| SoilBurnSeverityMap.__init__ | 0.178 | ok |
| SoilBurnSeverityMap.class_map | 0.017 |  |
| SoilBurnSeverityMap.class_pixel_map | 0.004 |  |
| SoilBurnSeverityMap.data | 7.523 |  |
| SoilBurnSeverityMap.export_4class_map | 7.743 |  |
| export_size_bytes | 43542 | /tmp/sbs-bench-zb6ys3t5/Rattlesnake.4class.tif |

## Rust-Accelerated (2026-01-24 06:39:32)

### prediction_wgs84_merged.tif

| Step | Seconds | Notes |
| --- | --- | --- |
| sbs_map_sanity_check | 4.772 | [0, 'Map has valid classes'] |
| get_sbs_color_table | 0.032 |  |
| SoilBurnSeverityMap.__init__ | 0.003 | ok |
| SoilBurnSeverityMap.class_map | 0.000 |  |
| SoilBurnSeverityMap.class_pixel_map | 0.000 |  |
| SoilBurnSeverityMap.data | 12.445 |  |
| SoilBurnSeverityMap.export_4class_map | 14.229 |  |
| export_size_bytes | 11092361 | /tmp/sbs-bench-03luoa9a/prediction_wgs84_merged.4class.tif |

### Rattlesnake.tif

| Step | Seconds | Notes |
| --- | --- | --- |
| sbs_map_sanity_check | 0.020 | [0, 'Map has valid color table'] |
| get_sbs_color_table | 0.001 |  |
| SoilBurnSeverityMap.__init__ | 0.003 | ok |
| SoilBurnSeverityMap.class_map | 0.016 |  |
| SoilBurnSeverityMap.class_pixel_map | 0.002 |  |
| SoilBurnSeverityMap.data | 0.021 |  |
| SoilBurnSeverityMap.export_4class_map | 0.048 |  |
| export_size_bytes | 43542 | /tmp/sbs-bench-vxbvyyeq/Rattlesnake.4class.tif |
