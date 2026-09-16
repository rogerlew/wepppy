# Kf source policy and independent checks

Date: 2026-09-16 UTC. Status: scientific proposal supported by source comparison;
contract review and ancestor checkpoint pending. No production changes.

## Selected source and evidence

Use the USGS 2025 KFFACT COG, release DOI
[10.5066/P13WAPYV](https://doi.org/10.5066/P13WAPYV), item
`6750c172d34ed8d3858534d8`. It rasterizes the NRCS-derived 1995 USSOILS
KFFACT field. The exact object is
[statsgo-KFFACT.tif](https://prod-is-usgs-sb-prod-publish.s3.amazonaws.com/6750c172d34ed8d3858534d8/statsgo-KFFACT.tif).
Case matters: the uppercase `STATSGO` spelling used for THICK returns 403 here.
There is no fallback source hierarchy in this increment.

Primary evidence retained under `source-evidence/`:

- `ussoils-original.xml`: [original USGS metadata](https://data.usgs.gov/datacatalog/metadata/USGS.ad9c5610-aaf5-4631-9577-5917acd873b5.xml),
  including original aggregation procedures and embedded SAS/AML source.
- `kffact.xml`: [COG release metadata](https://data.usgs.gov/datacatalog/metadata/USGS.6750c172d34ed8d3858534d8.xml),
  including its field-specific reproduction recipe.
- `soils250k.html`: [independent USGS subset metadata](https://pubs.usgs.gov/ds/270/data/DVD-1/METADATA/Soils250K.htm).
- `ussoils_18shp.zip` and `ussoils_15shp.zip`: original California and lower
  Colorado region archives linked in the original metadata.
- Retrieval JSON records contain URLs, HTTP status and content hashes. Failed
  requests are retained as diagnostics, not mistaken for source data.

The [NRCS field guide](https://www.nrcs.usda.gov/sites/default/files/2022-11/from-the-surface-down.pdf)
distinguishes fine-earth Kf from whole-soil Kw. No GPL pfdf code, tests or
implementation documentation was used to implement the independent probe.
Search discovery returned pfdf snippets; these are not the source-policy oracle.

## Metadata discrepancy and resolution proposal

The 2025 abstract and attribute units incorrectly describe hydraulic conductivity
in inches/hour. The original metadata separately defines erodibility KFFACT and
permeability PERM. Its aggregation source treats them as distinct fields. The
COG reproduction recipe explicitly selects KFFACT, and the numeric probe below
matches that field exactly. Consequently use unchanged USLE customary Kf values,
multiplier 1; never convert inches/hour into millimeters/hour for this soil input.
Retain the contradictory original metadata and record this interpretation in
provenance. This is an evidence-backed interpretation, not an upstream correction
or a claim that the publisher has confirmed the discrepancy.

## Inherited upstream aggregation

All recorded layers contribute according to their thickness, with missing-Kf
layer thickness removed from the denominator. Component means are then weighted
by component percentage; components without Kf are excluded and remaining
percentages renormalized. Entirely missing map units use -0.1. The original
metadata contains the full procedure and its missing-data handling. This is
not a 0–15 cm recipe, dominant-component selection, or the M3 thickness policy.
Consume the already aggregated product; do not recompute these source values
from current SSURGO records or fabricate missing horizons.

For an arithmetic illustration, layers of 10 and 30 depth units with Kf 0.2
and 0.4 give 0.35; a further missing layer is excluded. Combining that component
at 60% with Kf 0.1 at 30%, excluding a missing component at 10%, gives
(60 × 0.35 + 30 × 0.1) / 90 = 0.2666666666666667. This illustration explains
the documented policy; it is not an authentic raw-horizon fixture.

## Independent authentic source comparison

Run `check_source.py` from the repository root with `.venv/bin/python`.
It reserves a new `source-probe/` directory; preserve an earlier probe before
repeating. It imports the existing bounded transport in an isolated research
module, redirects only that process to the fixed KFFACT endpoint, and retains
HTTP ranges and identity checks. It never edits production source or writes runs.

The independent reference rasterizes the original polygon KFFACT attribute on
the COG's native EPSG:5069, 30 m grid. Results in `source-probe/results.json`:

| Geographic window | Compared cells | Exactly equal float32 cells | Maximum error |
| --- | ---: | ---: | ---: |
| Thomas, California | 149645 | 149645 | 0 |
| Arizona | 151734 | 151734 | 0 |

These are two geographic source windows, not two completed model runs. Their
values and original map-unit records are retained. The reader's selected byte
ranges, native rasters, ETag and length make the source comparison inspectable.

A nearest-neighbor alignment onto nervous-mesquite's saved grid gives mean
0.1393960061975289 over its 77,667 saved common-support cells. This is a research
aggregate only: that old support includes POLARIS validity, so it is not the new
Kf common mask or an accepted new result. The historical Thomas value 0.139364
was not an input. The difference is consistent with distinct spatial support;
this does not establish exact historical preprocessing parity.

## Production policy proposed for the checkpoint

Preserve native KFFACT values and align once by nearest neighbor to the project
DEM grid. Exclude NaN/masked cells and -0.1; reject other negative, infinite or
out-of-contract values. Combine Kf validity with the existing M1 DEM/SBS/dNBR
support and calculate T/F/S on that same support. Use the current [0,1] M1 S
admission range. Source resolution does not confer 30 m soil survey accuracy.
No minimum coverage threshold, imputation or source substitution is introduced.

Retain product/release, original field, units interpretation, inherited
aggregation, native and target grids, source-object identity, request hashes,
prepared-raster hashes, alignment and support policy. Legacy outputs retain
POLARIS provenance and their own freshness rules. Full canonical details are
in `wepppy/nodb/mods/postfire_debris_flow/docs/kf_source.md`.

## Remaining acceptance

Independent contract reviews and committed ancestor are pending. The prototype
is not production preparation. Two real basin workflows, no-RUSLE acceptance,
forest restart, nervous-mesquite rerun, browser/export/archive evidence and
final correctness/security/UX reviews remain mandatory.
