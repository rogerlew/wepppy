# PASS components v3 release compatibility

2026-10-09. Roger authorized general-release integration, including Roads and
AgFields composition. Mutation and disturbed-parameterization studies precede
deployment. No production deployment or executable-default change is authorized.

## Metadata and Backward Compatibility

Legacy PASS metadata retains its five-line layout. Version 3 prepends exactly
WEPP_PASS_COMPONENTS 3. Roads climate-token reads and rewrites must skip this
marker, preserve it and every event/component byte, and retain existing climate
identity checks. AgFields must read climate and modeled area from the five
metadata lines following the marker. Reject unsupported component versions;
do not guess offsets or drop the marker. Legacy behavior remains unchanged.

## Native Composition

The matching wepppyo3 reader and combiners are required with wepp_261010,
which replaces the undeployed wepp_261009 distribution without changing this
PASS v3 contract.
All combined inputs must use the same PASS version and be freshly generated
with the selected model build. Native composition preserves Vr, Qr, Vs and
hourly return weights per the wepppyo3 docs/pass-components-v3.md contract.
There is no Python physical-composition fallback and no Parquet column change.

## Regression and Generated Artifacts

Test version-aware metadata reads, climate rewrites with unchanged component
records, malformed/unknown markers, and legacy inputs. Run Roads and AgFields
regressions plus fresh same-build combined files through the native watershed
reader. Refresh the pinned interchange hash together with its release artifact.
Release provenance must identify the matching reader and model commits.
