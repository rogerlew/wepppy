# Implemented freshness waves: independent QA review

Reviewer: `freshness_qa`, 2026-09-17 UTC. Review scope: current uncommitted
post-fire production/cache/source-currentness and RQ download changes, NoDb
descriptor-bound hydration, and their changed tests. Accepted checkpoints:
`43317704f`, `0fe02dc0f`, `4e000950a`.

## Disposition

The implementation is cohesive and appropriately bounded. No new production
correctness defect or medium/high maintainability defect was identified.
**Scoped implementation QA passes; QA-01, QA-02, and QA-03 are resolved.**
The revised real-read replacement and both-loader stale-write regressions are
covered by `nodb_review_regressions.log` (76 passed). The changed-download-receipt
and handle-cleanup regression is covered by `download_review_regressions.log`
(35 passed).

This review follows the retained first-wave correctness review/follow-up and
security review. The subsequent NoDb implementation correctness/security
reviews also pass their bounded scope with the revised regressions.
This is not approval of the full inventory, deployment, or runtime acceptance.

## Findings and smallest corrective actions

| ID | Severity | Evidence and impact | Action / disposition |
| --- | --- | --- | --- |
| QA-01 | Medium, valid-state test coverage; resolved | Originally, `tests/nodb/test_hydration_snapshot.py:56` replaced the pathname before returning its stream, so both descriptor stats happened after unlink. That failed to exercise the harmless during-read ctime change identified as NODB-S01. | Verified correction: `ReplacingReader.read` performs real `os.replace` between the helper's descriptor stats. Assertions retain the complete old Unicode bytes, old inode/size/mtime, and new pathname contents. No filesystem stat mocking. Covered by the 76-test follow-up run. |
| QA-02 | Low, incomplete checkpoint evidence; resolved | The original replacement regression proved old payload/old mtime and cache mismatch but did not exercise the checkpoint-required stale-write rejection. Its `READONLY` marker also prevented demonstrating the writable path directly. | Verified companion regression `tests/nodb/test_base_boundary_characterization.py::test_decode_time_replacement_rejects_subsequent_stale_dump`: both loaders return A after real replacement by B; mutation under the usual lock raises `NoDbStaleWriteError`, and B's exact bytes remain intact. Covered by the 76-test follow-up run. |
| QA-03 | Low, regression coverage; resolved | `wepppy/microservices/rq_engine/postfire_debris_flow_routes.py` newly rejects changed accepted state after hashing; the original tests returned the same receipt from both state reads and did not exercise rejection cleanup. | Verified `test_download_changed_acceptance_closes_verified_handle`: the second state read removes acceptance, the route returns 409, and its sole actual `open_local` handle is closed. The 35-test download follow-up passes. |

## Maintainability and observability assessment

- NoDb changes reuse the existing narrow read/retry boundary and remove both
  post-decode pathname-stat blocks. The same helper serves both loaders without
  expanding NoDb identity, writer protocol, retry scope, or persisted fields.
- Post-fire content equivalence is separate from strict publication checks.
  Explicit `strict=True` at finalizers and `content=False` source capture preserve
  that distinction. Legacy snapshots are handled conservatively; validation
  rejects malformed new hash maps rather than inventing historical identity.
- The two bounded cache tables have different purposes. The observation token
  in the digest key prevents a surviving old digest from becoming eligible after
  observation eviction. Comments and the ADR explain the otherwise non-obvious
  unused key parameter. Strong verification deliberately bypasses caching.
- Read loops bound growth and validate final sizes; descriptor checks and access
  admission remain explicit. Errors retain domain/errno contracts rather than
  broad silent recovery. The download preserves the admitted handle through
  verification and response cleanup.
- Failed probes and intermediate test logs are retained alongside revised
  evidence. This makes the timestamp-collision correction and the coherent
  earlier-read limitation auditable instead of hiding failed assumptions.

Residual non-blocking debt: `production.py` was already compact and large; new
multi-part expressions in `_current_authority` and `get_state` require careful
reading to distinguish content and metadata comparison. At the next focused
maintenance pass, named local comparison values would make these decisions
clearer without introducing another abstraction or changing policy. Do not
combine digest and download loops merely to remove duplication: they currently
have different admission, error, and handle-lifetime responsibilities.

## Valid-state and test-quality assessment

The tests use actual bytes, hard links, atomic replacement, raster/model output,
and NoDb persistence at the changed boundaries. Narrow monkeypatches schedule
race interleavings or isolate external systems. The source-currentness helper
test includes missing/extra/null/malformed hashes and selection changes. Artifact
tests distinguish empty from absent, content-equivalent metadata churn from
changed bytes, legacy metadata behavior from new hashes, and strict publication
from accepted-result currentness.

The M3 regression invokes actual `copy_input_file` on an accepted project and
checks state before and after link removal. The M1 run test accepts pre-admission
metadata churn and rejects during-build drift while preserving the prior
accepted result. Its stubbed `sources` fixture means that test alone is not
proof of full owner/source integration; the separate M3 and production source
coverage is necessary.

The real-clock rapid-rewrite test does not force the original defect away with
sleeps. The controlled admission clock is appropriate for deterministic cache
age/eviction behavior. The single-block concurrent-read characterization accepts
an explicit error or the complete earlier digest, requires no cache admission,
and checks that the subsequent call sees the new bytes. It does not claim
arbitrary-writer snapshot isolation. The retained multi-chunk probe supplies
additional bounded evidence rather than a universal guarantee.

Access-loss coverage in `test_warm_digest_reads_no_content_and_rechecks_access`
is conditional on non-root execution. Retain actual UID/GID evidence in runtime
acceptance; a test run as root does not exercise that permission assertion.
Synthetic permission-error coverage still verifies NoDb error propagation.

## Evidence inspected and remaining acceptance

This QA pass inspected source and retained author/reviewer evidence; it did not
rerun production test suites. Observed completed logs:

- `first_wave_focused_revision4.log`: 144 passed.
- `postfire_affected_suite.log`: 712 passed, including freshness, report, route,
  real production artifact, and M3 runtime modules.
- `nodb_focused_revision2.log`: 155 passed across snapshot, initial retry, base,
  and boundary suites. Existing empty/malformed payload, optional absence,
  Redis/singleton retry and stale-write tests supplement the new snapshot suite.
- `nodb_review_regressions.log`: 76 passed after QA-01/QA-02 corrections, covering
  the revised snapshot module and the complete boundary-characterization module.
- `download_review_regressions.log`: 35 passed, including changed-acceptance
  rejection and actual admitted-handle cleanup for QA-03.
- `security_admission_tests.log` and `security_growth_after_bound.log`: retained
  independent cache-admission and bounded-growth evidence.
- `state_performance_admission.json`: 100 settled state reads add 21,400 cache
  hits and zero misses; warm state time is about 0.695 seconds. This demonstrates
  settled reuse for the measured project, not performance for all projects.

Any new test corrections need their own successful scoped run. Required full
`wctl run-pytest tests --maxfail=1`, current final correctness/security reviews,
remaining consumer inventory dispositions/checkpoints, restarted UI/RQ/WEPP
acceptance under actual identities/mounts, representative NFS evidence, and
archive/restore acceptance remain separate open gates. The package cannot close
on these implemented waves or the passing scoped counts alone.
