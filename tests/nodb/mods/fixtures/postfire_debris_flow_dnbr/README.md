# Public Arizona dNBR fixtures

Two unmodified GeoTIFFs from Villarreal and Conrad (2020), USGS Sky Island
2011-2017 dNBR release, DOI [10.5066/P99S0I9W](https://doi.org/10.5066/P99S0I9W).
The [USGS landing page](https://www.usgs.gov/data/differenced-normalized-burn-ratio-dnbr-data-wildfires-sky-island-mountains-southwestern-us-and)
marks this work CC0 1.0 Universal. See `manifest.json` for archive URL, members,
sizes and hashes, and `source_metadata.xml` for original methodology.

Selected Arizona event identifiers: AZ3133311041620120508 and
AZ3134011074320110214. These are 30 m Float32, UTM 12N rasters. Use explicit
scale 0.001, offset 0: embedded source processing code multiplies dNBR by 1000.
Metadata prose says 8-bit but does not match actual TIFF dtype. Values include
negative greening, NaN, and an extreme negative declared NoData sentinel.
Do not infer scale from Float32. Acquisition dates are not supplied per fire
in this bundle; filename dates identify events, not pre/post image dates.

Files are small ordinary Git fixtures. Tests are offline and generate temporary
targets/masks; they do not claim these images overlap the earlier soil panel.
MTBS fire bundles are another development source; continuous `dnbr.tif` must
not be confused with categorical `dnbr6.tif` or relativized `rdnbr.tif`.

## Preferred real severity fixtures

Use the [Wallow final-severity collection](../postfire_debris_flow_wallow/README.md)
for real SBS/BARC examples. It includes the distributed final four-class map,
BARC256 and continuous dNBR from the user-selected USGS archive. The pseudo
products below are retained as labeled historical derivatives, not the preferred
severity examples. These collections cover different fires and are not co-located.

## Pseudo-BARC256 derivatives

Two derived byte rasters are available in [pseudo_barc256/](pseudo_barc256/README.md),
with original grid/support, an internal missing-data mask and source/output hashes.
They are labeled pseudo products, not field-validated SBS or independent burn
severity observations. Original dNBR files and this source manifest are unchanged.
