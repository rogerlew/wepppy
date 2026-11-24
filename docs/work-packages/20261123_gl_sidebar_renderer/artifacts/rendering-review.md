# Sidebar rendering verification

The baseline was local master at 8cabcd96d. The implementation is 28de9f0f6.

| Check | Observable result |
| --- | --- |
| Channel selection | Both new Jest cases passed on each revision. Selecting a channel clears both competing families, waits for the family-specific refresh, then applies the layers and redraws the checked radio. |
| Sidebar and numeric legends | Chromium compared the channel sidebar markup and 70 numeric legends through createLayerRenderer. Seven categories, five modes, and absent or populated ranges produced identical markup and live input values. |
| RUSLE tolerance | For a four-cell raster with one nodata cell and values 1, 6 and 12, Chromium compared the effective range, input, stored tolerance and RGBA bytes at requested maxima 12, 6, 0 and 20. All four snapshots matched. Nodata stayed transparent and changing the maximum recolored the canvas. |
| Live project | The repository layer smoke suite loaded all four candidate layer modules in Chromium on misty-eyed-divorcee. Eleven cases passed, including switching regular and yearly channels, changing canopy cover and toggling rasters. Five cases skipped based on available project data. |

ESLint measured peak complexity of 86 in the original renderer. The highest scores in renderer.js, legends.js, layer-sections.js and rusle-tolerance.js are now 30, 36, 18 and 23 respectively.
