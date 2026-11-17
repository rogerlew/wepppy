# M2 independent QA and operations review

## Scope and method

This review covers the M2 change from `eb6b0d3fb` through `0e58feced`, the
candidate evidence in `20261116_m2_validation.md`, the M1 resource receipt, and
the M0 QA/operations acceptance requirements. It inspected test strength,
regression coverage, exact-image identity, runtime observability, resource and
cleanup evidence, fail-closed activation, recovery and supply-chain evidence.
It did not change runtime code or approve publication/deployment.

The focused seven-test GeoParquet suite was already green. As an independent
regression check, the full shape-converter unit suite was run with a 180-second
outer deadline. It advanced through 11 tests and timed out. The isolated
`test_module_level_app_bootstraps` case also failed to finish within 30 seconds
while entering the module app's `TestClient` lifespan. This is an incomplete
gate, not evidence that a particular M2 code path caused the hang.

## Findings

| ID | Severity | Finding | Required closure | Status |
| --- | --- | --- | --- | --- |
| M2-QAOPS-01 | Medium | The exact-image evidence is a functional smoke, not the complete M2 operational qualification required by the active ExecPlan. `20261116_m2_validation.md:43-56` covers small valid/projected/hostile requests and idle resource state, but contains no peak aggregate memory/CPU/FD/tmpfs measurement under a near-ceiling request, concurrent valid/hostile admission, real timeout/cancellation/descendant drainage, or succeeding recovery control in the same image. M1's 100,000-row probe was outside this Python/container boundary and explicitly was not a full-ceiling claim. | Exercise the exact image at reviewed near-limit load and concurrent valid/hostile states; capture peak cgroup/process/descriptor/scratch measurements. Force real timeout and repeated cancellation across the API boundary, prove the process group and scratch disappear, admission ownership is reclaimed, and a valid request succeeds afterward. | Open; M2 acceptance hold |
| M2-QAOPS-02 | Medium | Candidate regression validation is incomplete. The retained evidence lists only seven new Python tests and 30 Rust tests (`20261116_m2_validation.md:38-40`). The full shape-converter unit run timed out after 180 seconds, and the isolated module-app bootstrap did not finish within 30 seconds. The exact-image receipt also lacks a Shapefile inspect/convert readback even though M2 changes shared conversion metadata and canonical readback. | Diagnose or bound the local lifespan hang, then retain a green focused/full shape-converter regression gate from the candidate checkout. At minimum, run exact-image Shapefile inspect and convert controls and verify unchanged response/artifact semantics and cleanup alongside GeoParquet. | Open; M2 acceptance hold |
| M2-QAOPS-03 | Medium | Required resolved-Compose, fail-closed activation and recovery evidence is absent. The candidate was launched directly with `docker run`; no merged candidate Compose model proves the image, identity, mounts, internal/no-egress network and aggregate limits operators will actually activate. The code reports format-specific unavailability and blocks GeoParquet requests (`app.py:114-124`, `1016-1024`), but no test corrupts/removes the parser or canary and proves 503 for binary input while existing Shapefile behavior remains available. No immutable previous-image rollback/readback receipt is retained. | Resolve the isolated candidate Compose configuration and read back its effective image, identity, mounts, networks and limits. Add fail-closed parser/provenance/canary tests, then execute the documented local disable/rollback simulation and verify Shapefile/GeoJSON recovery, health, scratch and process state. Do not deploy. | Open; M2 acceptance hold |
| M2-QAOPS-04 | Medium | The work package requires an exact-image SBOM and vulnerability dispositions, but `20261116_m2_validation.md:61-77` retains only hashes and line counts for temporary ecosystem inventories plus a Rust-only advisory result. Debian and Python packages have no vulnerability disposition, and the inventory bodies/commands are not retained in the package. Deferring a publication scanner is appropriate, but it does not make the M2 SBOM gate complete. | Retain a reproducible SPDX/CycloneDX SBOM (or the complete deterministic inventory plus generator) for the immutable image and record Rust, Debian and Python vulnerability dispositions. Keep a fresh publication-pipeline scan as an additional rollout gate. | Open; M2 acceptance hold |
| M2-QAOPS-05 | Low | The new timeout test is a useful unit control but mocks process creation, signals and group existence (`test_geoparquet_input.py:179-219`). It proves branch behavior, not descendant disappearance or repeated-cancellation ownership. Several semantic tests also replace `_run_blocking_phase` with direct synchronous execution (`test_geoparquet_input.py:53-58`), so they do not cover the production cancellation/thread-ownership path. | Keep these fast unit tests, and add separate real-process/API lifecycle tests rather than making the mocks more elaborate. | Open; covered by M2-QAOPS-01 closure |
| M2-QAOPS-06 | Low | Format-specific readiness is observable in the JSON body but remains HTTP 200 when the GeoParquet parser is unavailable (`app.py:397-410`). This preserves Shapefile availability, but generic status-only probes can silently miss loss of the new feature. | Make rollout/preflight monitoring assert `geoparquet_parser == ready`; retain HTTP 200 for the whole service unless the operator deliberately changes that compatibility contract. | Open rollout gate |

No High finding was identified. The implementation's local happy-path artifact
readback, source/canonical digests, unavailable-grid rejection, hostile 413,
empty post-request scratch and embedded parser provenance are useful and
credible. They do not close the operational scenarios above.

## Quality observations

- The implementation reuses the predecessor process-group drain and request
  cleanup ownership rather than adding a second lifecycle abstraction. That is
  cohesive and reduces behavioral divergence.
- Stable format-specific errors and the separate readiness field provide useful
  operator signals without echoing hostile metadata.
- The M2 change adds roughly 493 lines to `convert.py`; future refactoring may
  extract common parser-launch configuration and provenance helpers, but doing
  so before acceptance would add unnecessary regression risk. Treat this as
  non-blocking debt.
- Exact package inventory bodies currently live in `/tmp`; hashes alone are not
  independently inspectable after that workspace disappears.

## Verdict

**HOLD for M2 QA/operations acceptance.** Unresolved findings: High 0, Medium 4,
Low 2. The focused implementation tests and exact-image smoke pass, but the
candidate has not yet satisfied the active plan's full regression, exact-image
resource/lifecycle, resolved-Compose/recovery, or SBOM/vulnerability evidence
gates. This verdict does not authorize or require publication or deployment;
all closure work can be performed locally or in the existing isolated candidate
harness.
