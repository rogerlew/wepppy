# Tracker - Project Config Preset Snapshot (WP04)

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-26 20:00 UTC
**Current phase**: Complete
**Last updated**: 2026-08-26 21:12 UTC
**Next milestone**: WP05 stable capability population and enforcement
**Security impact**: `high`
**Dedicated security review**: required
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master`
**Promotion policy**: merge only at the roadmap promotion gate
**Starting revision**: `95a8c4394`
**Implementation revision**: `140354fde`
**Upstream**: `origin/feature/project-owned-config`
**Upstream state at start**: ahead 2; WP03 not yet pushed

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Verified branch and prerequisite WP00A/WP00B/WP02/WP03 artifacts (2026-08-26 20:00 UTC).
- [x] Imported all 18 WP04-owned checklist tasks and five downstream contributions (2026-08-26 20:00 UTC).
- [x] Wrote the generated-data compatibility/regression plan before implementation edits (2026-08-26 20:00 UTC).
- [x] Added explicit policies for all 128 shipped presets and canonical safe resolution (2026-08-26 20:32 UTC).
- [x] Wired atomic pre-Ron materialization and 24-hour creation idempotency behind a strict default-off flag (2026-08-26 20:45 UTC).
- [x] Passed focused, subsystem, stub, broad-exception, correctness, and security gates (2026-08-26 21:12 UTC).

## Requirement Ledger

| Contract area | Tasks | Planned evidence | Status |
| --- | --- | --- | --- |
| PC-09 | N-023 through N-027; R-011 through R-014; R-031; R-035 | token, all-preset, override, determinism, chain, Interfaces tests | complete |
| PC-10 | N-055 through N-057; N-081 through N-083; R-046; R-052 | TTL/fingerprint/replay/conflict/concurrency/failure/readiness tests | complete |
| PC-01/04/05/06/08 contributions | real snapshot, sanitizer, bytes, provenance, manifest | generated temporary-run pair and WP02 reopen fixture | complete |

## Decisions Log

### 2026-08-26 20:00 UTC: Preserve the existing synchronous creation boundary

**Decision**: Integrate the default-off preset writer into rq-engine's existing
`/create/` blocking section rather than add a new route, database, or RQ job.

**Rationale**: This retains authorization, CAPTCHA, ownership, redirect, and
cleanup behavior while satisfying the contract's explicit synchronous boundary.

### 2026-08-26 20:00 UTC: Resolve before allocation and materialize before Ron

**Decision**: Validate policy/overrides and produce candidate bytes before run
allocation; after allocation, atomically write both artifacts before Ron.

**Rationale**: Invalid input cannot leave a run directory, and no controller can
observe a recognized flattened config without its manifest.

### 2026-08-26 20:00 UTC: Preserve legacy behavior outside the writer flag

**Decision**: `WEPPPY_PROJECT_CONFIG_PRESET_WRITER_ENABLED` is strict boolean,
absent/false by default, and only its true path narrows override acceptance.

**Rationale**: Section 7.1 prohibits silently changing legacy creation behavior
before the flattened writer is enabled.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Secret/host-bound value enters snapshot | Critical | Low | WP00A assertion on candidate config and manifest before write | Mitigated |
| Partial pair becomes visible to Ron | High | Low | complete resolution first; temp+fsync+replace before Ron | Mitigated |
| Replay creates duplicate owned run | High | Low | actor-scoped fingerprinted 24-hour reservation/result record | Mitigated |
| Unknown query transport value becomes durable | High | Medium | explicit policy keys; validate before reservation/allocation | Mitigated |
| Existing Interfaces behavior changes while off | High | Low | split flag paths and preserve existing tests | Mitigated |

## Verification Checklist

- [x] Generated pair passes WP00A and WP02 boundaries.
- [x] Every preset and override policy validates.
- [x] Focused/microservice/NoDb/exact full-suite gates pass.
- [x] Stub/API, broad-exception, docs, and diff checks pass.
- [x] Correctness and dedicated security artifacts have no unresolved medium/high findings.
- [x] Writer flag remains absent from deployment defaults.

## Progress Notes

### 2026-08-26 20:00 UTC: Scaffold and ingress

**Agent/Contributor**: Codex

**Work completed**:

- Verified WP03 at `95a8c4394` and preserved unrelated dirty files.
- Mapped WP04 to the existing rq-engine synchronous creation path.
- Recorded compatibility, generated-output, security, failure, and rollback plans.

**Blockers encountered**: None.

**Next steps**: Finish preset/override inventory, implement core writer, then
wire the flagged path and idempotency.

**Baseline**: WP03 exact full suite was 6,864 passed and 63 skipped.

## Watch List

- WP10 owns real fork/archive/restore pair preservation; WP04 tests only copied
  parent-chain semantics at the writer API boundary.
- WP11 owns Forest enablement, deployed Redis behavior, mixed readers, and rollback.

## Closeout

WP04 is complete with the writer dormant by default. Evidence is retained in
`artifacts/20260826_preset_snapshot_evidence.md`, with separate correctness and
high-impact security reviews. WP05 must populate stable capability IDs without
inferring the continental-US profile for incompatible legacy presets.

Implementation was committed as `140354fde`.
