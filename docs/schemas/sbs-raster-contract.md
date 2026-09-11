# SBS native raster contract

Implementation pending. Soil Burn Severity raster processing in
`wepppy/nodb/mods/baer/sbs_map.py` requires the existing `wepppyo3.sbs_map`
implementations for raster summary, default color-table reading/summary, raster
reclassification and four-class export. Missing native modules/functions and
native execution errors MUST fail explicitly through the existing route error
contract. Do not log-and-continue, silently switch algorithms, or keep a second
Python raster implementation. A failed computation MUST NOT be cached as success.

Preserve classification, palette, orientation, projection, resolution and
NoData semantics. Four-class export MUST mask the union of original source
NoData and current display NoData; WGS display export must not erase original
source masking. Native output must match the previously correct Python output
pixel-for-pixel on the actual Wallow raster and representative NoData/color-table
cases. No numerical formula or class threshold changes are authorized.

Scalar class-label helpers used for class summaries and explicit user color-map
interpretation remain supported; they are not alternative raster engines. The
existing GDAL display reprojection/color-relief pipeline remains. Optional import
may defer a missing dependency error until an SBS operation, but an operation
must never succeed by using a Python raster fallback.

Compatibility: public operations and route payloads remain stable. Missing or
broken native dependencies become explicit failures by owner decision, documented
in ADR-0065. Unit tests may inject native failures but may not make a fallback
path appear successful.

Rationale: Wallow's source NoData disabled native export and selected a 6.2-million
pixel Python loop, taking 55.55 seconds versus 0.35 seconds natively. Silent
fallback hides deployment defects and requires duplicate maintenance.

## Caller failure boundaries

Existing run upload, HUC upload, batch upload and Flask SBS operations must not
report success after a required native failure. In particular, batch upload must
return the canonical error response when sanity checking or required burn-class
summary fails, rather than logging and publishing incomplete success metadata.
No native failure may authorize a model run or accepted summary. Preserve existing
authentication, run ownership, upload limits and cleanup containment.
