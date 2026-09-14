# Soil research and scaffold evidence

Reviewed 2026-09-14 UTC. Source inspection only; no project or soil-builder changes.
Durable findings and citations are in the module's
[SSURGO assessment](../../../../wepppy/nodb/mods/postfire_debris_flow/docs/ssurgo_validity_assessment.md#production-research-2026-09-14).

## Paper and source inspection

Read the retained accepted manuscript with `pdftotext -layout`:
`wepppy/nodb/mods/postfire_debris_flow/docs/pdfs/staley_2017.pdf`.
Section 3.2 names the STATSGO source; section 5.1 discusses thickness as a
possible sediment-availability measure; Table 4 specifies thickness/100 for M3.
The paper does not prescribe an SSURGO horizon-processing policy. Read the
existing source metadata assessment for inch units and cumulative-layer meaning.
Do not commit the ignored publisher PDF or copy GPL pfdf implementation.

NRCS Fundamental Query v1.1 and Tables and Columns v2.3.2 were accessible.
The live USGS THICK catalog was accessible. ScienceBase item fetches and old
USGS DS270 metadata URLs failed in this session (internal fetch error/403);
their historical SAS interpretation is retained repository evidence, not a new
successful retrieval. The Soil Survey Manual chapter URL also failed; NRCS's
accessible Soil Profile page supports basic O/C/R distinctions, not a complete
weathered-rock policy. Resolve that limitation in milestone 1.

## Frozen fixture inventory

Read all `*_component.csv` and `*_chorizon.csv` under
`tests/nodb/mods/fixtures/postfire_debris_flow_soils/` with Python's CSV reader.
Group component weights by `mukey`; group horizon ranges by
`(cokey, hzdept_r, hzdepb_r)`. This audit did not derive production thickness.

| Site | Map units | Components | Horizons | Weight totals below 100 | Above 100 | Repeated depth groups |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Moscow Mountain | 44 | 91 | 514 | 42 | 0 | 0 |
| Topanga | 13 | 64 | 97 | 0 | 0 | 0 |
| `az_ponderosa` | 54 | 235 | 895 | 0 | 0 | 0 |

These fixtures cover missing component weights but do not test the documented
paired-depth or above-100 cases. Add source-shaped analytical cases before
implementation acceptance; do not claim three-site coverage is exhaustive.
The `az_ponderosa` label is historical: its source lineage is New Mexico.

## Reviewed code boundaries

`wepppy/soils/ssurgo/ssurgo.py::Horizon.valid` checks WEPP parameter readiness;
`WeppSoil.build` selects a usable component after `_get_horizons` filters it.
These routines are protected. `soil_thickness.py::derive_component` rejects
all overlap, and `derive_mapunits` rejects total percentages above 100; both
are offline study choices. Extend through an explicit policy without changing
their default behavior. `read_cache` already uses read-only SQLite.

`production.py::sources` currently fingerprints M3's built `.sol` inventory and
basic mapping/source selections. Actual raw thickness sources, original MUKEY
lineage and their freshness need to be added. `execute_m3` is the explicit
pending-integration boundary. Do not derive thickness from those `.sol` files.

Next: inspect real cached schemas and original-versus-substituted raster keys,
inventory prepared THICK delivery, quantify candidate soil rules, and publish
the finite decision matrix. No live-data availability is assumed from fixtures.
