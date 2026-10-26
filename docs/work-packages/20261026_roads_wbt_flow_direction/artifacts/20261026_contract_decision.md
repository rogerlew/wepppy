# Contract decision: ROADS-WBT-D8

2026-10-26 UTC. Operator: Roger Lew; implementer: Codex.
Authorization: "scaffold and execute work-package to fix the flow-direction bug",
after operator confirmed Roads requires WBT. Includes local native build/release
refresh needed to wire the fix; excludes production rollout or project mutation.

Base WEPPpy: 69ddcafe9314a120c00d9cfc89f9b1476bcda67a.
Base wepppyo3: 47e51b8e73146872056b68934977db56d91c9119.
Base Peridot: 3cef07bdc93a595016d80d0619718809a1bdccc8.

Current canonical obligations: feature_registry/feature_registry.yaml Roads
requires_backend=wbt; roads-preparation-lifecycle-contract.md preserves isolation
and readiness; roads-water-accounting-contract.md governs output weights;
new roads-flow-direction-contract.md specifies the previously missing explicit
native representation boundary. Existing lifecycle/accounting intent is unchanged.

Normative delta: explicit WBT normalization in native adapter, Roads wbt=True,
native API default TOPAZ preserved. Classification: observed representation bug
plus clarification of the native contract. Rationale: invalid WBT16 and false
loops become successful traces with existing Peridot conversion. No new scientific
formula, default parameter, units or fallback; parameterization ADR not applicable.

States: absent Roads remain unused; no eligible segments retain existing behavior;
populated WBT data traces correctly; supported native TOPAZ callers are unchanged;
invalid/missing raster and seed/shape errors stay explicit. True disconnected
traces and NoData outlets remain excluded. No auto-guessing from ambiguous codes.
Security: low, loaded in-memory buffer normalization only. No authority, path,
queue, subprocess or persistence boundary change. Native and caller version skew
fails visibly; release must be paired.

Regression: all eight actual-raster neighbors, overlapping code controls, legacy
TOPAZ behavior, invalid/loop/edge/step/seed/shape controls; caller keyword; actual
site full fresh Roads pipeline, five recovered and four retained skips, expected
channels, current receipt/report rows and unchanged baseline/source hashes.
Two independent read-only reviews and dispositions precede implementation.

Review disposition: science and correctness reviews PASS with no medium/high
findings. Corrected the accounting contract filename identified by correctness
review. Existing helper compass comments are not used as the test oracle; assert
independent neighbor positions. Source fingerprinting also requires an explicit
stale notice for historical Roads full-project publication after routing changes;
retain original result/provenance hashes and acknowledge only reviewed exact
source deltas, under the existing validation-suite contract. No historical numbers
will be presented as a fresh rerun. Science review accepts this disposition.
