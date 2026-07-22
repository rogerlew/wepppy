# Tracker - SSURGO Intelligent Fallback M4 Rollout

> Living record for implementation, RQ evidence, and review disposition.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-22 UTC
**Current phase**: Scaffold review dispositioned; M1 implementation ready
**Last updated**: 2026-07-22 UTC
**Next milestone**: Resolve all M1 review requirements before implementation:
canonical source/artifact contract, exact eligibility/baseline rule, schema
compatibility, and RQ validation procedure.
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `artifacts/2026-07-22_security_review.md`

## Task Board

### Ready / Backlog

- [ ] M1: Implement conditional padded-raster/candidate-build preparation and
  deterministic all-valid no-op coverage.
- [ ] M2: Implement vector selection, global escape hatch, selected-donor
  materialization, and additive provenance.
- [ ] M3: Validate compatibility, generated outputs, and RQ contracts.
- [ ] M4: Run `plastic-bundling` / `disturbed9002` through RQ, then complete
  reviews and disposition.

### In Progress

- [ ] M1: Implement the accepted-pending source/artifact, no-op, schema, and
config-binding requirements.
**Contract checkpoint**: `2026-07-22_contract_decision.md` (commit pending)

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
