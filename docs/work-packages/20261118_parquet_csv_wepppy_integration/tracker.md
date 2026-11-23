# Parquet CSV integration tracker

**Updated**: 2026-11-18 UTC

**Phase**: Closed locally; production deployment pending

**Branch**: `codex/parquet-csv-cli-package`

**Security impact**: high; independent correctness/security reviews passed

**Plan**: [implementation_execplan.md](prompts/completed/implementation_execplan.md)

## Milestones

- [x] M0: Ratified compatibility, strict IPC, errors, fixed limits and retention.
- [x] M0: Independent checkpoint ancestor `a1f40de48`; bounded dictionary amendment
  `3fefd089d` and column amendment `9a4642a01` committed before threshold edits.
- [x] M1: Required native CLI/provenance, production supervisor and compatibility.
- [x] M2: Immediate cutover across run/culvert/batch/directory CSV; no Python fallback
  or environment-facing CSV controls; full lifetime ownership and cleanup.
- [x] M3: 213 focused, 152 adjacent, 104 file-route and 13 Rust checks passed;
  46 real files match oracle bytes. Final exact-image HTTP/identity/resource gates pass.
- [x] M3: Broad pytest passed after integration (wrapper source-change disposition
  and clean targeted follow-up retained in validation): 14535 passed, 506 skipped, 99 deselected, 5906 warnings in 3657.80s (1:00:57).
- [x] M4: Independent reviews, durable contracts, operator/developer/user docs and
  canonical release/whole-release rollback handoff retained.

## Decisions and evidence

The operator approved transient conversion storage because retained CSV could
become stale and imply automatic model generation. Invalid UTF-8 metadata is
explicitly rejected; authorized raw Parquet remains available. Normative scope and
rationale are in the integration contract's temporary-retention and approved-metadata
sections. No project artifact/cache was introduced.

[Validation](artifacts/validation.md), [correctness review](artifacts/20261118_final_correctness_review.md),
[security review](artifacts/20261118_final_security_review.md), and
[release handoff](artifacts/release-handoff.md) bind source/binary/image/HTTP evidence.

Implemented, wired, focused/broad validated and locally image-validated: complete.
Merged to shared master, remotely integrated or production deployed: not performed.
Target-host configuration/auth/secrets/proxy validation remains a deployment gate.
