# Development contract checkpoint

Starting revision:7d7d8c72e. User explicitly requested in-depth investigation and development of volumetric/surface rock for Roads and WEPP generally. This authorizes demonstrated unit/basis repairs and scientific development; no deployment or new native physics is assumed.

Canonical changes: new rock-fragment representation contract and ADR-0125; RUSLE specification's existing SoilGrids /10 meaning is unchanged. RUSLE change is conformance repair. SoilGrids generated RFG conversion is an explicit basis correction reviewed before code edits. Compatibility: same public keys, formats, prior artifacts and native cap; changes apply on explicit rebuild. Additive units provenance only. Security:none (arithmetic, no new IO/API boundary).

Valid states: absent optional cfvo retains fallback; empty/all-nodata retains fallback; populated supported raw/aligned cfvo fixed per-mille conversion; existing explicit user cover unchanged; malformed existing raster behavior unchanged. Soil generation requires valid finite volume in[0,100] and positive fine-earth density; invalid values fail explicitly before writing a soil.

Regression: actual input/output rasters/manifest for both C modes and paths, below/at/above100 units, nodata/override; volume/mass conservation and endpoints; real SoilGrids builder soil serialization and native interpretation; focused and broad tests. Independent science and correctness contract reviews precede implementation.
