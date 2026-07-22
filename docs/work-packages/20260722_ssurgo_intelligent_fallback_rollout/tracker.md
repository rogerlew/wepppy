# Tracker - SSURGO Intelligent Fallback M4 Rollout

> Living record for implementation, RQ evidence, and review disposition.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-22 UTC
**Current phase**: M3 generated-output/adversarial validation in progress
**Last updated**: 2026-07-22 UTC
**Next milestone**: Complete M3 generated-output/adversarial evidence, then
perform the local RQ acceptance sequence before considering M4 release lift.
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `artifacts/2026-07-22_security_review.md`

## Task Board

### Ready / Backlog

- [x] M1: Implement conditional padded-raster/candidate-build preparation and
  deterministic all-valid no-op coverage.
- [x] M2: Implement vector selection, global escape hatch, selected-donor
  materialization, and additive provenance.
- [ ] M3: Validate compatibility, generated outputs, and RQ contracts.
- [x] M4 runtime: Run `plastic-bundling` / `disturbed9002` through RQ and
  capture all-valid no-op evidence.
- [ ] M5: Complete remaining M3 evidence, reviews, and disposition.

### In Progress

- [ ] M3: Add generated-output, adversarial artifact, and propagation evidence.
**Contract checkpoint**: `2026-07-22_contract_decision.md` (commit `bf5f2e62c`)

### Blocked

- [ ] Package/M4 acceptance is held until every accepted-pending review finding
  has an implementation commit and reviewer-visible verification result.

### Done

- [x] ADR-0025 and fallback specification ratified before implementation
  package creation (2026-07-22 UTC).

## Decisions Log

### 2026-07-22 UTC: Separate M4 rollout package

**Decision**: Keep the empirical study as evidence/governance history and use
this package for implementation, RQ evidence, and review closure.

### 2026-07-22 UTC: RQ evidence is mandatory

**Decision**: Rebuild `plastic-bundling` using authenticated RQ `build_soils`
with config `disturbed9002`; direct `Soils.build()` is not acceptance evidence.

### 2026-07-22 UTC: Candidate preparation is conditional

**Decision**: Retrieve the padded map and build added MUKEYs only after the
primary build identifies a residual-invalid dominant hillslope.

### 2026-07-22 UTC: Review disposition holds implementation

**Decision**: Accept all independent scaffold-review findings as required work;
do not begin M1 code changes until the high-severity findings have concrete
contracts and tests in the active ExecPlan.

**Rationale**: Reviews exposed ambiguity in primary versus added candidate
eligibility, global-baseline stability, artifact safety, and the actual RQ API
contract. The evidence gate would otherwise be unable to prove the policy.

## Risks and Issues

| Risk | Severity | Mitigation | Status |
| --- | --- | --- | --- |
| Candidate artifacts are stale, partial, or escape run scope | High | Fixed paths, resolved-root checks, atomic publish, checksum/provenance tests | Open |
| Candidate source is untrusted or unavailable | High | Canonical root resolver, identity validation, explicit global fallback | Open |
| RQ run escapes scope or races | High | Root lock, security review, run-tree checks, config binding test | Open |
| Local stack is stale | Medium | Preflight active jobs/queue; prefer targeted recreation; health check after restart | Open |
| `plastic-bundling` is all-valid | Low | Required no-op RQ proof; hermetic fixture covers selection | Open |

## Verification Checklist

- [ ] Additive NoDb/Parquet schema compatibility recorded before code edits.
- [ ] ADR field/radius/normalization/tie contract matches implementation.
- [ ] Legacy hydration and existing consumers pass.
- [ ] `plastic-bundling` RQ job completes and artifacts are inspected.
- [ ] Code review: `artifacts/2026-07-22_code_review.md` complete.
- [ ] QA review: `artifacts/2026-07-22_qa_review.md` complete.
- [ ] Security review: `artifacts/2026-07-22_security_review.md` complete.
- [ ] All findings dispositioned in
  `artifacts/2026-07-22_review_disposition.md`.

## Progress Notes

### 2026-07-22 UTC: Package initialization

**Agent/Contributor**: Codex

**Work completed**: Created the successor package, active ExecPlan, review
templates, and project-tracker entry. Recorded `plastic-bundling` /
`disturbed9002` RQ acceptance and local-stack restart authority.

**Next steps**: Implement the conditional candidate boundary and additive
persistence plan.

**Test results**: Documentation scaffold only; no runtime mutation performed.

### 2026-07-22 UTC: Independent scaffold review

**Agent/Contributors**: Planck (code), Newton (QA), Mendel (security/operations)

**Work completed**: Three independent read-only reviews found nine high and
twelve medium finding records. The active plan, normative specification, ADR,
and disposition ledger were updated; all findings are accepted-pending.

**Next steps**: Complete the M1 contract and fixture implementation before
beginning vector-selection wiring.

**Test results**: Documentation review only; implementation remains unstarted.

### 2026-07-22 UTC: M4 implementation contract checkpoint

**Agent/Contributor**: Codex

**Work completed**: Recorded the canonical authority, approved implementation
delta, compatibility/security impact, and regression plan. The checkpoint must
be committed as a standalone ancestor before implementation edits.

**Next steps**: Commit this checkpoint, then implement M1 with independent
verification running in parallel.

### 2026-07-22 UTC: M1/M2 implementation and independent re-review

**Agent/Contributor**: Codex

**Work completed**: Added canonical source validation, immutable candidate-map
manifest publication, native crop/WGS84 support, raw-MUKEY/hillslope-intersected
source locations, primary-only global baseline preservation, config-match RQ
guard, vector selection, selected-added-donor publication/retry, and additive
provenance wiring. Refreshed the deployable `wepppyo3` artifact in commits
`3aedb43` and `6b05234`.

**Review result**: Planck and Mendel: GO to M3; Newton: HOLD pending the final
two narrow fallback guards, which were corrected and covered before this
record. M4 remains HOLD pending M3/RQ evidence.

**Next steps**: Add full generated-output/adversarial fixtures, then run the
RQ acceptance sequence.

**Test results**: 32 focused SSURGO/NoDb/RQ-route tests passed; native crate
tests passed 7/7 with the host PyO3 link argument; test-stub, broad-exception,
and route-contract checks passed. Full M4 remains held pending generated-output,
adversarial, and RQ evidence.

### 2026-07-22 UTC: M3 Parquet evidence and M4 local preflight

**Agent/Contributor**: Codex

**Work completed**: Added a real `soils.parquet` round-trip test for a local
selection: raw/final MUKEYs, JSON provenance, catalog publication, and the
referenced selected donor `.sol` are checked together.

**M4 preflight**: `wctl ps` reported all required local services up; `wctl
rq-info` reported zero queued/executing jobs and idle workers. No restart was
needed or performed.

**Blocker**: The documented local dev-agent password login/token flow cannot
be used because `/weppcloud/login` is OAuth-only in this stack. The API
submission requires an authorized bearer or session-token path. No token was
forged and no RQ mutation was submitted.

**Next steps**: Continue M3 adversarial and broader scoring/radius evidence;
the later entry records the now-complete RQ acceptance sequence.

### 2026-07-22 UTC: M4 local RQ all-valid acceptance

**Agent/Contributor**: Codex

**Work completed**: Used the supplied scoped JWT to discover the live
`rq_engine_build_soils` contract, prove the post-restart wrong-config request
returns non-mutating `409 run_config_mismatch`, submit the resolved correct
payload, poll terminal `finished`, and inspect NoDb/Parquet/soil artifacts.

**Result**: PASS for the all-valid no-op path. Candidate preparation was
`not_attempted`, the candidate manifest was absent, mappings were unchanged,
and 63 Parquet rows/reference soil files were coherent. Redacted details are
in `artifacts/2026-07-22_rq_acceptance.md`.

**Operational note**: A stale rq-engine process accepted the first wrong-config
probe. After the idle-queue preflight, targeted service recreation loaded the
committed implementation; the re-run produced the required 409. No Redis flush
was performed.

**Next steps**: M3 local-selection/adversarial evidence and M5 zero-unresolved
review disposition remain required to lift the package release hold.
