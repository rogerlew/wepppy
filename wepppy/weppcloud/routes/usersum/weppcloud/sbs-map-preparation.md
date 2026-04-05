# SBS Map Preparation

Use this page to prepare a soil burn severity (SBS) raster for upload to WEPPcloud. It explains the raster styles WEPPcloud accepts, the safest preparation workflow, and the validation problems that most often block an upload.

## What This Page Helps You Do

Use this page when you are preparing a burned watershed project or any workflow that needs an SBS raster. The goal is to upload a clean thematic burn-severity map, not a continuous burn index surface.

## What WEPPcloud Expects

Before upload, the SBS raster should have all of these characteristics:

- one band,
- integer pixel values only,
- 256 or fewer unique values,
- valid projection metadata,
- a thematic burn-severity classification rather than a continuous float surface.

GeoTIFF is usually the safest export format.

## Supported Raster Styles

| Style | Best use | Notes |
| --- | --- | --- |
| Numeric classes | New exports and easy troubleshooting | Use integer thematic classes such as a simple 4-class severity map or a BARC-style classified raster |
| Color-table raster | Existing agency or GIS products | Keep one clear color per severity class, then verify after upload that each color is assigned to the correct burn-severity class in the interface |

If you are creating a new map, numeric classes are usually easier to troubleshoot than palette-only rasters.

## Color-Table Guidance

WEPPcloud can recognize several common color-table values as burn-severity classes automatically. If your raster uses other colors, the map can still be usable, but you should check the color assignments in the interface after upload and assign each color to the correct burn-severity class if needed.

Using a color table is acceptable when:

- one color maps clearly to one severity class,
- the palette uses one of the recognized color sets below, and
- the raster is still a single-band thematic map.

If your current palette does not match one of these recognized colors:

1. upload the map,
2. check how the interface assigned each color to `No burn`, `Low`, `Moderate`, or `High`, and
3. correct any wrong assignments in the interface before continuing.

Using one of the recognized or recommended palettes below usually reduces manual cleanup because the initial class mapping is more likely to be correct.

### Recognized colors by class

These RGB values are currently recognized on the color-table upload path.

| Severity class | Commonly auto-recognized RGB values |
| --- | --- |
| No burn or unburned | `0,100,0`, `0,0,0`, `0,115,74`, `0,158,115`, `0,175,166` |
| Low | `102,204,204`, `102,205,205`, `115,255,223`, `127,255,212`, `0,255,255`, `77,230,0`, `86,180,233` |
| Moderate | `255,255,0`, `255,232,32`, `240,228,66` |
| High | `204,121,167`, `255,0,0` |

If your raster uses a different green, cyan, yellow, magenta, or red than the values above, do not assume it will be assigned correctly automatically. Check the color-to-class mapping in the interface and fix it there if needed.

## Recommended Palettes

If you need to build or repair a color table, use one of these two four-class palettes.

### Recommended standard palette

This is the traditional palette and is a good default when you want a familiar burn-severity legend.

| Severity class | RGB | Hex |
| --- | --- | --- |
| No burn or unburned | `0,100,0` | `#006400` |
| Low | `127,255,212` | `#7FFFD4` |
| Moderate | `255,255,0` | `#FFFF00` |
| High | `255,0,0` | `#FF0000` |

### Recommended color-shifted palette

This palette keeps the same class meanings but uses more separated colors that are easier to distinguish in some displays and accessibility contexts.

| Severity class | RGB | Hex |
| --- | --- | --- |
| No burn or unburned | `0,158,115` | `#009E73` |
| Low | `86,180,233` | `#56B4E9` |
| Moderate | `240,228,66` | `#F0E442` |
| High | `204,121,167` | `#CC79A7` |

## Recommended Workflow

1. Start with a thematic SBS map, not a continuous dNBR, RBR, or other float index surface.
2. Reproject to a valid projected coordinate system if needed. A local UTM coordinate system is usually the safest choice.
3. Use nearest-neighbor resampling if you reproject or resample the raster.
4. Export the raster as a single-band integer file such as `Byte` or another integer type.
5. Preserve `NoData` if the original map has masked or unknown areas.
6. Save as GeoTIFF if you have a choice of formats.
7. Check that the legend still represents unburned, low, moderate, and high severity classes in a consistent way.
8. Upload the raster to WEPPcloud.
9. In the interface, check that each uploaded color is assigned to the correct burn-severity class.
10. If any color is mapped incorrectly, assign it to the correct class in the interface before proceeding.

## Common Validation Messages

| Message from upload validation | What it usually means | Quick fix |
| --- | --- | --- |
| `Map contains an invalid projection. Try reprojecting to UTM.` | CRS metadata is missing, incomplete, or invalid | Reproject to a valid projected CRS, usually local UTM, and export again |
| `Map has non-integer classes` | Pixel values include decimals or floating-point values | Reclassify to integer classes and export as an integer raster |
| `Map has more than 256 classes` | Too many unique values were detected | Reclassify to a smaller thematic class set |
| `Map has no valid color table` | A color table exists, but the palette does not clearly match the common auto-recognized burn-severity colors | If the map uploads, check and assign the colors in the interface. If that is not practical, export a numeric-class raster instead |

## Limits and Common Mistakes

- Do not upload a continuous burn index unless you have classified it first.
- Do not use bilinear or cubic resampling for a thematic SBS raster. Those methods can create invalid intermediate classes.
- Do not upload a multiband image when the workflow expects one thematic band.
- Unsupported or ambiguous color-table entries may be treated as unknown or `NoData`.
- If your map uses a custom agency palette, do not assume the auto-assigned classes are correct. Check the assignments in the interface and fix them there when needed.
- An SBS map is one input into disturbed-land parameterization. It is not a direct measurement of runoff, erosion, or soil water repellency by itself.

## Related Docs

- [Quick Start](quick-start.md)
- [(Un)Disturbed Landuse and Soil Parameterization](../../../../nodb/mods/disturbed/ENDUSER.md)
- [Disturbed Land Soil Lookup](disturbed-land-soil-lookup.md)
