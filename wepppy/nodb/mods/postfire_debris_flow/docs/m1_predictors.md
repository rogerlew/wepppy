# M1 prepared predictor integration contract

Status: proposed local backend contract, 2026-09-09 UTC. Implementation pending.
The [work package](../../../../../docs/work-packages/20260909_staley_m1_predictors/package.md)
composes existing accepted helpers. New K coverage/readiness policies remain
proposals; scaffolding does not approve them or production workflow changes.

## Scope and existing authority

Read the existing project watershed/outlet, raw DEM, prepared WEPP Soils, SBS,
normalized dNBR and named RUSLE Nomograph K. Write only a caller-selected fresh
local output directory. No live controller mutation, rebuild, acquisition,
active-result replacement, UI, queue or deployment. RUSLE owns K preparation.

Reuse the [domain mapping](../specification.md#project-watershed-assessment-scope),
[slope/SBS contract](slope_sbs.md), [dNBR contract](dnbr_upload.md),
[numerical engine](staley2017_engine.md), and ADRs 0054–0058. Initial scope is
one project watershed at its existing resolved outlet, including channel cells.
Do not shrink the domain to common coverage of the predictor rasters.

## Proposed composition

A thin `integration.py` collaborator validates explicit prepared inputs and
coordinates existing helpers. Keep manifest/schema handling in `manifest.py`
only if that separation clarifies the bounded implementation. Freeze Python
signatures, required provenance fields and error vocabulary before code.
The backend has no default rainfall or model-switching behavior.

T comes from a fresh, complete StaleySlopeSbs invocation with the accepted
Horn/raw DEM/strict-neighborhood contract. Preserve true/false/unknown counts,
input coverage, T_lower/T_upper and null T where uncertainty remains. A success
marker means processing completed, not necessarily model-ready T.

F comes from `summarize_dnbr` over the same full watershed mask. The canonical
dNBR raster contains normalized differences: its mean supplies F directly.
Require its normalization provenance and source identity. Positive partial
coverage permits the accepted observed-support estimate, with coverage warning;
no observations means unavailable F. Existing normalize_dnbr remains a separate
preparation operation; this composition does not reinterpret original encoding.

S comes from `rusle/k_polaris_nomograph.tif`, not the default K alias or EPIC.
Verify calibrated units against actual RUSLE formula/output and published Kf
before fixing the mapping to S. Record source depth/statistic, source gap fill,
optional fragment treatment and explicit unit conversion or identity. Missing K
policy remains pending; recommended behavior is no additional fill and no point
S on incomplete usable coverage. Do not impose T's support rules or dNBR's
partial mean by analogy. Existing upstream RUSLE filling must remain disclosed.

## Prepared raster boundary

Prepare independent copies for the owned WBT decoder: classic, uncompressed,
untiled, single-band grayscale GeoTIFF with explicit SampleFormat and finite
NoData. Preserve CRS, affine, dimensions, valid samples and missing masks;
verify those properties after conversion. Pick a representable sentinel that
cannot collide with valid data. Do not reuse dNBR NaN conventions for WBT inputs.
Preserve palette indices for SBS, not rendered RGB values. Canonical normalized
classes are 0–3, with declared 255 NoData; use the existing SBS owner's mapping.
Rasterio/GDAL is an existing preparation precedent; Rust still computes slopes.

The raw DEM grid never changes. Define any necessary categorical SBS alignment
explicitly with nearest sampling and retained holes. Require the K/dNBR grid
contract separately; do not silently warp continuous K or change its averaging
scale. The composed resource budget must respect WBT's 10-million-cell limit,
not the dNBR backend's larger cap. No decoder fallback or limit bypass.

Invoke a verified StaleySlopeSbs executable through an existing owned execution
pattern. Record executable hash/version, parameters, return status and outputs;
fail clearly if the tool is missing. Account for wrapper cwd behavior without
changing process-global state unsafely. FNV source fingerprints in the WBT
summary are diagnostic; preserve independent SHA-256 lineage in the bundle.

## Availability, identity and outputs

Proposed bundle includes versioned manifest, prepared-input identities, WBT
artifacts, predictor record and source/support diagnostics. Final field names
must be frozen before implementation. Successful processing and scientific
availability are distinct. Preserve a null/unavailable predictor with reasons;
do not emit a probability if any required predictor is unavailable.

Record full basin area/outlet/grid, T/F/S units, independent support, source and
prepared hashes, accepted parameterization and binary identity. Propagate the
accepted 0.2–8 km² area warning without rejecting on area alone. Machine-readable
canonical values do not depend on SI/English display settings. Example rainfall
scenarios are validation artifacts, not a climate-frequency result contract.

Hash immutable inputs before/after the build and validate referenced manifests
and completion markers. A hash proves identity, not that a stale upstream
artifact still matches its source configuration. Define the available lineage
checks and report unsupported/missing provenance explicitly. Reject source
mutation during build; do not publish a successful bundle based on mixed inputs.

Use fresh private local output with a final completion marker after validation.
Existing output preservation, partial-write cleanup/retention and retry semantics
must be specified and tested. Do not imply this local interface safely handles
hostile concurrent directory owners or publishes active NoDb results.

## Remaining decisions and validation

[Decision register](../../../../../docs/work-packages/20260909_staley_m1_predictors/artifacts/decision_register.md)
tracks K convention, coverage and artifact-only readiness. The latter is
recommended instead of full RUSLE completion but is not yet accepted workflow.
Completed WEPP Soils remains an accepted production prerequisite; fixture builds
must distinguish supplied artifact validation from a live controller check.

Acceptance requires real binary/binding outputs, analytical predictor means,
independent-support cases, valid zero/negative dNBR, missing/stale/legacy sources,
unit/encoding errors, actual file-boundary failures and source preservation.
Use representative project artifacts with verified overlap; synthetic SBS/K
must be labeled. A final real-project claim requires real prepared sources,
not synthetic replacements. If these cannot be obtained read-only, record the
missing evidence and do not claim that acceptance gate passed.
