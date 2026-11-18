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

## Initial findings

The following table records the initial review state. Every item was rechecked
against the final3 evidence and is dispositioned in the final re-review below.

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
- The final candidate now retains the machine-readable SBOM and complete
  vulnerability report in the work package; the initial temporary-inventory
  concern is superseded.

## Final3 re-review

The final candidate is source revision
`e172f9f8a23c10774f87828181048c72188ba78a` and local image
`sha256:ed4d93692add1f7cd1527ed6948353e584a213865ebcc3006b1adf84f5c62386`.
The embedded parser provenance names that same revision. The retained SPDX and
Grype report hashes were independently reproduced from the work-package files:

- SPDX JSON:
  `00fad0f0e8c143c47f78b67f6a0706f3d64e0103e4fd8217b10130445799dffa`;
- Grype JSON:
  `a359b57d30d90cdbc9e98d06eb80f47a1aeeda281583f56f0de95eb26c163345`.

| ID | Final disposition | Evidence |
| --- | --- | --- |
| M2-QAOPS-01 | Resolved | The exact HTTP image processed the reviewed 100,000-row fixture and returned 100,000 features, source-digest equality and a 10,288,931-byte canonical artifact. Sampled peaks were 293.2 MiB, about one CPU, 50 PIDs, nine PID-1 descriptors and 16,797,373 scratch bytes, all below the resolved 1.5 GiB/1.5 CPU/256 PID/384 MiB tmpfs envelope; scratch was empty afterward. Four concurrent near-limit/hostile/valid requests produced one bounded success and three `service_saturated` responses, followed by a successful digest-matching control. A real 250 ms client abort retained admission ownership until parser/output/scratch drained within the observed 26-second window; executable-path and scratch readback were clean, and the recovery request succeeded. Repeated task-cancellation/process-group behavior remains covered by focused unit tests. |
| M2-QAOPS-02 | Resolved for M2 | The focused candidate suite increased to 19 passing tests, the CLI retains 30 locked/offline tests, and the exact image now has successful GeoParquet and Shapefile inspect/convert artifact readbacks with matching semantic and digest evidence. The full local suite stall is explicitly retained as a pre-existing `TestClient`/lifespan harness defect and is not counted green; exact-image controls exercise the shared production runtime boundary. Repairing the local harness remains non-blocking tooling debt, not an unobserved M2 format regression. |
| M2-QAOPS-03 | Resolved | Development and production Compose models resolve, and production qualification binds the exact image with UID/GID 10001, read-only root, dropped capabilities, no-new-privileges, no volumes, internal sandbox network and the resource envelope above. Removing the GeoParquet parser produced body-level `unavailable`, GeoParquet HTTP 503, continued Shapefile HTTP 200 and empty scratch; restoring final3 restored readiness and digest-matching conversion without persisted converter state. Missing production `VECTOR_UPLOAD_RUN_FILESYSTEM_ID` remains a deliberate activation stop. A production-host rollback receipt remains a separately authorized M5/deployment gate. |
| M2-QAOPS-04 | Resolved | Pinned Syft 1.57.1 produced retained SPDX 2.3 JSON for a daemon-free archive of the exact image: 103 packages and 2,845 files. Pinned Grype 0.121.3 produced the retained complete 212-match report. Its 59 High, 70 Medium, 17 Low, 50 Negligible and 16 Unknown records have explicit reachability/fix dispositions in the validation receipt; no available same-branch/package remediation is omitted from this local candidate. RustSec remains clear for the exact GeoParquet lock. A fresh publication-time scan and newly available updates remain rollout gates. |
| M2-QAOPS-05 | Resolved | The real abort/drain/process and recovery receipt supplements the fast mocked lifecycle tests. Keeping both layers is appropriate. |
| M2-QAOPS-06 | Resolved for M2; rollout assertion retained | The missing-parser probe proves the compatible whole-service HTTP 200 plus body-level format unavailability and GeoParquet 503. Rollout/preflight monitoring must assert `geoparquet_parser == ready`; changing whole-service status would regress intentional Shapefile availability. |

The vulnerability disposition is accepted only for this constrained local
candidate: non-root, read-only, capability-free, offline parser execution with
a fixed minimal child environment and no invocation of the reported command,
locale, document-formatting, SQLite extension/session/FTS, TLS-PSK or similar
surfaces. Publication must repeat the scan and apply any then-available base or
Python package updates; this review does not waive that gate.

## Verdict

**PASS for local M2 QA/operations acceptance.** Unresolved implementation
findings: High 0, Medium 0. The exact final3 candidate satisfies the scoped
format-regression, near-limit resource, concurrency, lifecycle cleanup,
resolved-Compose, fail-closed recovery and supply-chain evidence gates. The
pre-existing local `TestClient` stall is retained as non-blocking test-harness
debt. Fresh publication scanning, production-host recovery proof, image
publication, remote integration and deployment remain separate gates and are
not authorized by this verdict.
