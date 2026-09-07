# Validation and execution outcome

**Date**: 2026-09-07 UTC
**Starting revision**: `aafeecc8c3bc3ba9dbf16fec66891770742b35f4`
**Outcome**: implementation and authorized local validation complete.
**Deployment/replay**: none; explicitly excluded by the operator.

## Automated checks

| Check | Result |
| --- | --- |
| First two real-file contention regressions, before production edits | Both failed at real `dump()` with the expected same-size stale signature; see writer attribution artifact. |
| Focused Climate/RAP, batch RQ, and NoDb boundary/base suites | 245 passed. |
| Expanded contention and Climate facade suites | 49 passed, including later negative/commit/logging cases. |
| `wctl run-pytest tests --maxfail=1` | **7535 passed, 63 skipped**, 3103 warnings, 792.57 seconds. |
| `wctl run-stubtest wepppy.nodb.core.climate wepppy.nodb.mods.rap.rap_ts` | No issues in either module. |
| `wctl check-test-stubs` | All stubs complete. |
| `.venv/bin/vulture` | Exit 0. |
| `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` | Pass across all seven changed production Python files; unsuppressed broad-catch delta -2. |
| Code quality observability | Completed in observe-only mode; host lacks radon and the tool did not report uncommitted changed-file deltas. No threshold gate claimed. |
| Documentation lint and spelling preview | Touched docs pass lint. Preview did not justify unrelated spelling rewrites. |
| `git diff --check` | Pass. |

An earlier full-suite process was deliberately interrupted after 168 passes
and 13 skips when review corrections made its imported code stale. The final
full run above was restarted against the corrected implementation and completed.
Counts from separate commands overlap and are not summed.

## Direct boundary evidence

Tests use actual NoDb hydration, locks, serialization, signature checks, and
atomic file replacement in temporary run trees. They do not mock the failing
NoDb boundary. Injected collection seams supply controlled same-size unrelated
or relevant writes; they do not identify a production process.

Coverage includes observed GridMET normalized string years and backend
arguments, PRISM upstream year/CLI conflicts, RAP map/multi-OFE/raster changes,
six-band single-/multi-OFE parquet, empty summaries, legacy embedded/int-key
state, malformed state, partial retrieval/analysis failure, precommit dump
failure, postcommit version failure, unknown commit readback, ownership takeover,
and managed/unmanaged Climate directories. Failed paths preserve previous
results or retain documented recovery copies and do not publish new completion
timestamps.

The generated-output test creates real GeoTIFFs with GDAL, invokes the owned
Rust raster median implementation, writes/reloads real parquet, and verifies
`wepp/runs/p1.cov`. It ran through the Compose `weppcloud` test container as
UID 1000/GID 993. This validates local propagation, not Kubernetes filesystem,
lock, mount, or deployment parity.

## Reviews and remaining operational evidence

Independent correctness, code, QA, and security reviews closed with no
unresolved high or medium findings. Their artifacts retain each finding and
resolution. No queue edge, scientific parameterization, output column, or
public facade signature changed.

The actual Kubernetes invalidating writer remains unidentified, and recurrence
after this patch has not been measured. Copied batch group identity is a
separate confirmed follow-up. Multi-file publication remains non-crash-atomic;
unknown commit/ownership loss retains recovery evidence. No deployment approval
or production acceptance is implied by the test or review results.
