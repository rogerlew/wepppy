# Independent contract security review

Review time: 2026-09-16T22:40:57Z. Reviewer: independent `security_reviewer`
agent (`contract_security`). Starting implementation revision:
`5f98c577a8cc0dfe5cb0be78f40c231a0d0c8a18`.

## Findings and verdict

No high or medium contract security findings. Contract-design gate: **pass**.
This reviews the proposed contract, not implementation conformance or release
readiness. Final dedicated security review and its executable evidence remain
required after correctness and QA review.

| ID | Severity | Evidence and consequence | Required disposition | Status |
| --- | --- | --- | --- | --- |
| CS-01 | Low | The initial checkpoint's Authority section said commit authority and delegation were pending; ADR-0068, package and active ExecPlan retained that obsolete current status. Stale authority text could cause another unnecessary stop or leave the ancestor's authorization trail contradictory. | Record the latest owner instruction and bounded authority before the ancestor commit; retain earlier statements only as historical context, without inferring push or other-host authority. The reviewer re-read the updated checkpoint, ADR, package and active ExecPlan and confirmed this disposition. | Resolved |

There is no demonstrated exploit from CS-01; it is an authority-record defect.
No risk acceptance is requested. All review findings are resolved.

The follow-up review also covers the new concrete acquisition interface,
additive accepted/Redis `soil_policy` dispatch and immediate Mods/reload
acceptance clauses. No additional blockers were found. The acquisition paths
are internal derived inputs under the unchanged confinement boundary; the
advisory projection cannot replace authoritative artifact validation. Unknown
policy does not claim completion, absent policy preserves legacy checks, and
M3 retains its existing behavior.

## Reviewed scope and triage

Reviewed the contract decision, ADR-0068, canonical `docs/kf_source.md`, report
amendment, feature-registry amendment, and the M1/M3/predictor/model-selection/
rainfall/control amendments named in the checkpoint. Also reviewed the inherited
production runtime and report security boundaries, contract-first standard and
artifact observability standard. Source inspection of the existing transport and
preparation modules established the referenced reuse boundary; it does not
substitute for testing the future implementation.

Security impact **high** is correct: the package extends external egress, local
raster/file processing, worker execution and accepted report payloads. A final
dedicated security artifact is mandatory. No new auth protocol, endpoint,
external dependency, service, cache or deployment topology is authorized.

The attacker model includes hostile or concurrently replaced local files,
malformed or inconsistent upstream responses, unauthorized report requests,
changed project authority while workers run, and hostile textual export context.
Existing project authorization remains the trust boundary; visibility is never
an access-control or completion mechanism.

## Boundary assessment

| Surface | Contract assessment | Implementation evidence required |
| --- | --- | --- |
| Egress and native decoding | `kf_source.md`, Preparation, fixes one HTTPS object and reuses bounded M3 transport with no caller-selected URLs, redirects, retries or alternate sources. Strong identity pinning, conditional ranges, final verification, aggregate bytes and supervised time/cell bounds constrain upstream inconsistency and resource exhaustion. THICK behavior must remain unchanged. | Exercise the actual changed transport with valid ranges and hostile status/header/identity/size/deadline cases. Confirm native work is terminated by its supervising process and useful partial records survive. |
| Local files and provenance | The checkpoint explicitly rejects traversal, symlinks and sidecars under inherited local confinement. Fixed inventories and hashed snapshots prevent metadata from becoming executable source/path instructions. Kf values, common support and grids are independently validated before acceptance. | Direct filesystem tests must exercise absent parents, valid regular files, symlink replacement, malformed JSON/raster/sidecars and tampered retained artifacts through the new path. Mocks of the containment boundary are insufficient. |
| Publication and concurrency | Kf belongs to fresh attempt directories; there is no mutable global source pointer. Rechecks before and inside final locking cover project inputs, attempt ownership, eligibility, read-only state, model and rainfall policy. Failed replacement preserves the previous bundle. | Exercise real publication/locking and failure paths, including concurrent project/authority changes and intact previous acceptance bytes. Verify new M1 ignores unrelated RUSLE changes while legacy freshness keeps its original dependencies. |
| Auth, report and exports | The existing authorized routes, accepted-attempt pinning, no-store, bounded descriptor downloads and sanitized errors remain binding. Curves have at most 106 points and use validated accepted values. New CSV text inherits formula-injection defenses. | Verify unauthorized access, replaced acceptance, malformed accepted records, new textual context escaping, duration/Unitizer exports and descriptor closure. Prove report reads perform no acquisition, job reconciliation or scientific writes. |
| Observability and archive | `kf_source.md`, Preparation, inventories visible request records/bodies, publisher metadata, native/aligned rasters, manifests and failed attempts under the established module layout. Archive/restore includes them; only credentials are excluded. Success is an explicit manifest, never directory visibility. | Use canonical archive/restore to assert exact member paths and bytes for working, failed and complete records. Exercise normal authenticated browse/download under the actual service identities after restart. Do not replace these checks with filesystem-only visibility or a custom route. |
| Queue, deployment and secrets | Existing process supervision and ordinary Run are retained. Catalog/graph/live-tree validation is required if dependency edges change. Scope is forest restart plus the named run and disposable fixtures; no other-host deployment or push follows. No new credentials are needed. | Inspect installed canonical restart mechanics, validate identities/mounts/configuration and normal UI/RQ execution, retain protected-input hashes and sanitize evidence so session/bearer credentials never enter artifacts. |

## Valid-state noninterference

The checkpoint separately enumerates expected absent optional state, empty and
partial attempts, verified preparation, supported legacy bundles, no accepted
report, unavailable predictors and malformed/hostile state. Expected Kf absence
must leave GET usable and Run preparable; it cannot become a containment error
because an optional directory is missing. Empty/failed attempts stay visible
and a fresh attempt is allowed. New preparation failure must preserve readable
accepted results. M3 requires no Kf and legacy M1 retains its source identity.

This is sufficient as a pre-implementation state matrix. Actual noninterference
is not yet proven: final evidence must construct these states through the real
changed boundaries, including a valid no-RUSLE run and reads without optional
NoDb state. Correctness and UX reviewers own the usable outcome checks;
security approval cannot substitute for their reviews.

## Residual risk and closeout limits

The source object remains an externally administered publication. Identity
pinning proves one coherent retrieved object, not future publisher immutability.
The contract correctly treats accepted results as recorded snapshots and uses a
fresh identity only on a new Run. The metadata interpretation has explicit
scientific evidence and limitations; this security review does not independently
certify the scientific source decision.

The full transport/filesystem/publication/archive and real browser evidence does
not exist for the proposed implementation yet. Its absence is expected at this
checkpoint and blocks final package closeout, not contract acceptance. There are
zero unresolved high/medium/low findings after follow-up review. No production
files, runtime state or other review artifacts were
modified by this reviewer.
