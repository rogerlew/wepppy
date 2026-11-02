# Surface support implementation validation

The production change adds cosurffrags missingness and known-area support to the
existing RUSLE source reports. It preserves numeric selection, precedence,
clipping, manual overrides, fallback behavior and C raster values. Malformed
values consumed by the old aggregation retain its error outcome. Old manifests
remain readable; rebuilding may add the support object. No model parameter,
default, deployment or existing run was changed.

Contract ancestor: acfadc938. Independent implementation and generated-artifact
reviews pass. Real parquet/raster RAP and SBS fixtures produce four distinct
retained roots; all45files were independently verified, including exact automatic
versus manual C raster identity. This is actual production-function artifact
execution, not a claim of a deployed full project or native armor validation.

Validation: `wctl run-pytest tests/nodb/mods/test_rusle_c_integration.py` passes48
focused tests. `wctl run-pytest tests --maxfail=1` passes12,642, skips423 and reports
5,830 warnings in3,587.85seconds. The broad suite started before the final three
focused test cases were added; production code was unchanged throughout. The
final focused run covers all48cases. No broad rerun is needed for collection-only
coverage growth after the unchanged production source was tested.

Raw roots remain active within the larger rock-water program; archival is pending
completion of its native studies. This surface checkpoint does not close that
program. Native mechanical armor remains unadmitted: area accounting and survey
proxies do not establish engineered-road shielding/friction coefficients.

| Bound artifact | SHA256 |
| --- | --- |
| wepppy/nodb/mods/rusle/c_integration.py | 631ed7aa7663790dfdc1515c508a602ad4672b92e7b0abc25739db5bf3078159 |
| tests/nodb/mods/test_rusle_c_integration.py | d2cd9e4a323bce3e05ab3dbb5fc2a1c55226e64d3274f2ad05248ebfb9bb39f9 |
| out/rock-water-development-20261101/surface-broad-v1.log | a4397de044ffe96511f833c71bc3e16f35de40abf02cb9d17695143bccfbec0c |
| out/rock-water-development-20261101/surface-artifacts-v1/receipt.json | 729829f4e58fb1b68d47f27dd1e957bb484fc27c3463d72e508205f533438516 |
