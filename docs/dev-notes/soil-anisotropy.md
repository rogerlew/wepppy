# Soil anisotropy preparation

[SA-01](../schemas/soil-anisotropy-contract.md) and [ADR-0088](../adrs/ADR-0088-soil-anisotropy-overrides.md) govern the optional WEPP Advanced Options fields. Python persists omitted/cleared values and enforces MOFE/hourly eligibility. Disabled settings remain saved but inactive; preparation-time hourly overrides are authoritative for that preparation.

`WeppSoilUtil` reads a soil source into one text snapshot. Uploaded native validation and parsing share that snapshot. Symbolic parameter recomputation reparses the same snapshot with the historical formula flags, preserving rounding and restrictive-layer derivation. Existing saturation, kslast, minimum-depth and maximum-depth operations run in their original order. The Rust `wepppyo3.wepp_interchange.soil_anisotropy_values` function then computes optional overrides in memory; the existing writer writes the prepared destination once. Archive materialization and independent consumers are separate from this advanced-option pass.

The Python preparation integration admits per-horizon formats 7778/9001/9002/9003/9005. The Rust kernel preserves unset ratios and accepts existing nondecreasing clipped depths. Uploaded 7777/2006 layouts never migrate to accept an override. A missing native function fails explicitly. No source soil is rewritten; repeated preparation starts from the selected source, so clearing an override restores source values.

Deploy the paired WEPPpy and rebuilt wepppyo3 revisions. Update `docker/wepppyo3-interchange-preflight.py` to the paired artifact SHA-256; a mismatch intentionally blocks startup. Production uses the installed `wctl` preset and `scripts/deploy-production.sh` with its existing build, static-asset and health checks. The native repository release must be available to that build; restart all importing web/worker processes as part of deployment. The canonical production deployment boundary is unchanged. Retain the native module hash and source revision; a Python-only update cannot enable this feature. Rollback must restore both matching revisions. Do not run a model or change existing runs merely to deploy these controls.

Validation reads `wepp/runs/p*.sol` through the real writer/native path and counts source opens and destination writes. Tests cover multiple OFEs, exact 500 mm boundary, crossing horizons, clipped duplicate depths, original zero values, inactive state, blank clearing and canonical native-format errors. The [work package](../work-packages/20261012_soil_anisotropy/package.md) retains current evidence and deployment limits.

The validated runtime pair is WEPPpy `e6004b118` (or its reviewed descendants) with wepppyo3 `822b6fe`. The native artifact SHA-256 is `103f209676425ae2bcf7fbde0c31b6d7bbe9ca0a5779d766297a4af9cd92c633`. The [build receipt](../work-packages/20261012_soil_anisotropy/artifacts/native-build.json) records source hashes. Forest's actual default RQ worker produced byte-identical prepared output under UID 1000/GID 993, mode 0644; the [validation record](../work-packages/20261012_soil_anisotropy/artifacts/validation.md) distinguishes completed checks from baseline gate limitations. No production deployment or full WEPP simulation was performed for this acceptance.

## Project developer mode (DM-01)

[DM-01](../schemas/project-developer-mode-contract.md) adds `Ron.developer_mode`,
missing-false for legacy projects. Exact Dev membership is checked only by the
activation action; ordinary authorized anisotropy submissions and preparation
resolve Ron policy. Developer mode removes both maxima while keeping finite
values >=1, MOFE/hourly eligibility and normal source/depth semantics.

Activation holds the existing catalog lifecycle guard before the Ron lock and
fresh disk hydration. Fork/archive capture already uses that guard, avoiding
inconsistent Ron/Wepp snapshots without queue or copy changes. Archive restore
and existing failed-fork recovery intentionally use incoming mode, even normal
mode. There is no off setter or sticky history.

The native function takes a keyword-only `developer_mode=False`; WEPPpy passes
an explicit snapshot through preparation. Pair the caller with wepppyo3
`4d4c075` or a compatible descendant and the corresponding startup artifact pin.
An old native library fails explicitly rather than silently ignoring policy.
See the [implementation evidence](../work-packages/20261028_project_developer_mode/tracker.md)
for current validation and deployment status.
