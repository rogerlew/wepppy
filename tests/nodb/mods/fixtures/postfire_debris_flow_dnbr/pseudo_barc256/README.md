# Pseudo-BARC256 fixtures

Historical derivatives. The owner selected the
[Wallow final-severity collection](../../postfire_debris_flow_wallow/README.md)
as the preferred real severity fixture on 2026-09-09.

Derived from the two parent-directory CC0 USGS dNBR fixtures at the user's
request on 2026-09-09. These are synthetic BARC-like derivatives of observed
dNBR, not official BARC products or field-validated soil burn severity.

## Derivation and compatibility

The source samples already encode dNBR × 1000. For finite unmasked samples:

    pseudo_barc256 = floor(clip((source_sample + 275) / 5, 0, 255))

The [USGS BAER product description](https://burnseverity.cr.usgs.gov/baer/index.php/background-products-applications)
describes the inverse relation dNBR = BARC256 × 5 − 275. Clipping and floor
quantization are explicit fixture choices, recorded in ADR-0060. No four-class
thresholds, field adjustment, smoothing or resampling are applied.

Outputs are single-band UInt8 GeoTIFFs on the exact source CRS/grid. Internal
masks preserve source missing cells and treat nonfinite samples as missing.
There is no numeric NoData sentinel: valid 0 and 255 must remain valid. Consumers
must honor the internal mask. Masked sample storage is 0, which is not a class.

Compatibility plan: new derivative files only; parent source files/manifests,
production formulas and run artifacts remain unchanged. `manifest.json` records
hashes, support, clipping counts and conversion details. Generation verifies all
output samples, masks, grids and original source hashes by direct readback.
These files do not establish independent SBS evidence for authentic M1 validation.

## Reproduction

From repository root, run through the existing dev container:

    wctl exec weppcloud python tests/nodb/mods/fixtures/postfire_debris_flow_dnbr/create_pseudo_barc256.py

Existing outputs are checked rather than overwritten. The two outputs are
`AZ3133311041620120508_pseudo_barc256.tif` and
`AZ3134011074320110214_pseudo_barc256.tif`.
