# Security Review - SSURGO Intelligent Fallback M4 Rollout

## Metadata

- **Package**: `docs/work-packages/20260722_ssurgo_intelligent_fallback_rollout/`
- **Reviewer**: Mendel, independent security/operations review agent
- **Date**: 2026-07-22 UTC
- **Review turn**: independent read-only scaffold review
- **Reviewed base**: `def1d3243` plus uncommitted M4 scaffold
- **Scope reviewed**: candidate raster/build paths, NoDb/Parquet writes,
  `build_soils_rq` propagation, and local RQ validation.

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: RQ-worker execution mutates run files and adds a
  configured geodata read; path, lock, source, and failure boundaries require
  independent review.

## Required Surface Checks

- [ ] Candidate and temporary paths stay under the resolved run soils root;
  symlink escape, stale artifact, partial output, and concurrent retry are
  tested.
- [ ] Candidate source is canonical gNATSGO, not a user-controlled path or
  silent fallback source; root containment and source identity are tested.
- [ ] Existing RQ authorization, run access, config binding, locks, and
  response/error contracts remain unchanged or have explicit tested contracts.
- [ ] Queue dependency metadata and graph are checked if wiring changes.
- [ ] No tokens, raw source data, or sensitive run contents enter committed
  artifacts or logs.
- [ ] Local restart preflight/recovery protects unrelated jobs and does not
  flush Redis DB9.

## Findings

| ID | Severity | Surface | Required action | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | High | Candidate artifacts | Define fixed names, resolved-root containment, symlink policy, same-filesystem temporary files, fsync/`os.replace`, post-rename checksum, map/metadata validation before provenance, stale-artifact rejection, and full existing-lock coverage. Test traversal/symlink/stale/write-failure/concurrent retry cases. | accepted-pending |
| SEC-02 | High | Canonical source | Define one configured-root canonical resolver; prohibit caller/NoDb source paths; require resolved regular readable file, approved-root containment, source identity/version, and documented mount-symlink policy. Test traversal/outside-root/request isolation/source unavailable. | accepted-pending |
| OPS-01 | High | RQ proof | Replace wrong endpoint discovery with pipeline/readiness plus `rq_engine_build_soils` schema/defaults/errors. POST current resolved JSON defaults with `rq:enqueue`, capture correlation/job ID, poll terminal `finished`, and record redacted transcript. | accepted-pending |
| SEC-03 | Medium | Config binding | Add normalized config-match precondition before mutable build-soils state, with canonical non-mutating error. Test wrong config unchanged and `disturbed9002` success. | accepted-pending |
| OPS-02 | Medium | Local restart | Record `wctl ps`, active local jobs, and `wctl rq-info`; do not restart during unrelated mutations without approval; prefer targeted recreation; health-check worker/engine after restart; never flush DB9. | accepted-pending |
| GOV-01 | Medium | Review closure | Require append-only finding IDs, reviewer/turn/base SHA, owner/rationale/evidence/implementation commit/result, and zero unresolved high/medium findings at closure. | accepted-pending |

## Verdict

- **Gate status**: HOLD
- **Release recommendation**: resolve and verify SEC-01, SEC-02, and OPS-01
  before M1 implementation; no M4 RQ proof until the corrected procedure and
  config-binding disposition are complete.
