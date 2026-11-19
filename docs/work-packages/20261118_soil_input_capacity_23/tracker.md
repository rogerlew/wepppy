# Soil input capacity 23 tracker

Status: Closed 2026-11-19 UTC; implementation and local release preparation complete.

## Progress

- [x] Native evaluation and national inventory; capacity decision recorded.
- [x] Dedicated worktrees, package, ADR-0150 and canonical contracts.
- [x] Native input capacity 23, calculation capacity ten, fixtures and metadata.
- [x] Native acceptance and legacy parity; matched Linux pair locally vendored.
- [x] Python raw/prepared/Disturbed/MOFE/channel/derivative propagation and launch guard.
- [x] Focused tests, native Disturbed matrix, stub checks and independent reviews.
- [x] Disposable original-project workflow and full-calendar/report readback.
- [x] Opt-in release/rollback preparation and user/operator documentation.
- [x] Reconciled segmented broad gate and final source/evidence handoff.

## Decisions

Use `mxhzin=23`, retain `mxnsl=10`, no merging or conductivity policy change.
Keep historical/default selections. User authorized nearest CLIGEN station on
only the disposable clone and independent read-only review agents.
Production deployment and original-project recovery are separate actions.
Normative decision: [ADR-0150](../../adrs/ADR-0150-native-soil-input-capacity.md).

## Evidence

- [Release identity](artifacts/release-identity.md): native full suite 1824, reader 72,
  metadata 14, watchlist 31, 80/80 exact reader states and 20 watershed executions.
- [Disturbed parity](artifacts/disturbed-parity.json): 186 checks passed;
  768 native outputs match previous reviewed results byte for byte.
- [Project replay](artifacts/project-replay.md): 355 hillslopes, 144 channels,
  100 years, all 5,259,456 daily channel rows finite and calendar-complete;
  canonical post-jobs and report readers passed.
- [Correctness review](artifacts/20261119_correctness_review.md): three omitted
  derivative-consumer findings closed; 42 focused regression checks passed.
- [Security review](artifacts/20261119_security_review.md): pass, no findings.
- [Consumer matrix](artifacts/consumer-matrix.md) and [rollout](artifacts/rollout.md).

## Final validation disposition

[Validation manifest](artifacts/validation.json) reconciles 14,554 passes and 505
runtime skips across all 15,059 selected ordinary tests; one collection skip and
99 opt-in deselections are reported separately. The repaired final modules pass
with stable source. See the independent [broad gate assessment](artifacts/20261119_broad_gate_assessment.md).
This is segmented broad coverage; failed prior receipts remain retained, and
cross-segment ordering was not re-exercised. Six-module stubtest, test-stub
completeness, broad-exception checks and documentation lint passed.

The Roads benchmark retains its existing stale full-project-routing warning;
its updated source review does not reapprove historical routing results.
The import smoke fixture now excludes only confirmed executable management
utility directories and restores cwd/sys.path. The tracked example JSON was
restored exactly. Production code still matches independent review hashes.

No production deployment, remote integration or original-run mutation occurred.
