# Publish large-watershed interchange and daily totals

Completed locally 2026-11-23 02:36 UTC. Both repositories have paired task branches. Production rollout and original-run recovery are pending.

## Purpose and milestones

The run needs a readable H.pass.parquet and subsequent daily totals even when the number of source files exceeds 32,767. In the adjacent wepppyo3 checkout, inventory wepp_interchange/src/parquet.rs and every caller. Reproduce the old boundary and count physical groups from the footer. Change the sink and affected consumers, then test actual rows, source order and daily aggregation on mixed and split groups. Build the py312 extension and validate its public integration. Keep production recovery separate from local acceptance.

## Progress

- [x] 2026-11-22 UTC. Traced PASS, six bulk families, shared stream writers, AgFields validation and totalwatsed3.
- [x] 2026-11-22 23:25 UTC. Implemented and verified the paired native release, identity validation and daily aggregation.
- [x] 2026-11-22 23:25 UTC. Reviewed final binary, documented evidence and production recovery state.
- [x] 2026-11-23 02:36 UTC. Final standalone repository-wide sanity passed 14,901 tests with clean source and runtime fingerprints.

## Surprises & Discoveries

AgFields completion equates identity count with physical group count. Roads accounting writes at least one chunk per represented target. Baseline WAT, SOIL and ELEMENT aggregation previously revisited a physical group for each selected identity in it. The live native source tree included an unreleased MOFE module, so the paired binary must be built from the released crate with only the interchange changes.

## Decision Log

Preserve source order and validate identity independently of storage boundaries. Limit the number of neighboring sources per group to keep per-hill aggregation affordable. Keep single-file artifacts and atomic publication.

## Validation and recovery

Run the native crate tests, generate a file through a bulk writer at the incident boundary and compare daily outputs from packed and ordinary input. Exercise AgFields manifest handling, rollback and invalid identities. Run canonical WEPPpy tests. A failed staged write can be retried from retained model outputs after the updated extension is installed.

## Outcomes & Retrospective

The prior release reproduced the incident on a synthetic full-count fixture. The candidate completed PASS and WAT, the daily aggregation, and AgFields LOSS at that source count. Four hillslopes from the original project independently exercised the complete 45-year calendar. The final release preserves the incumbent MOFE slope artifact. Independent correctness and QA reviews passed. The full WEPPpy gate passed in one serialized run. Production installation and requeue are outside the local completion claim.
