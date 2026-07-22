# Tracker - SSURGO Intelligent Fallback M4 Rollout

> Living record for implementation, RQ evidence, and review disposition.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-22 UTC
**Current phase**: M5 independent review and disposition in progress
**Last updated**: 2026-07-22 UTC
**Next milestone**: Complete M5 review disposition and release gates before
considering the release lift.
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `artifacts/2026-07-22_security_review.md`

## Task Board

### Ready / Backlog

- [x] M1: Implement conditional padded-raster/candidate-build preparation and
  deterministic all-valid no-op coverage.
- [x] M2: Implement vector selection, global escape hatch, selected-donor
  materialization, and additive provenance.
- [x] M3: Validate compatibility, generated outputs, and RQ contracts.
- [x] M4 runtime: Run `plastic-bundling` / `disturbed9002` through RQ and
  capture all-valid no-op evidence.
- [x] M4 runtime: Run a true-current-invalid watershed through RQ and capture
  local-vector donor-selection evidence.
- [ ] M5: Complete independent reviews, disposition, and release gates
  (in progress 2026-07-22 UTC).

### In Progress

- [x] M3: Generated-output, adversarial artifact, and propagation evidence.
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
| Candidate artifacts are stale, partial, or escape run scope | High | Fixed paths, resolved-root checks, atomic publish, checksum/provenance tests; record metadata from persisted raster | Mitigated; adversarial closure remains |
| Candidate source is untrusted or unavailable | High | Canonical root resolver, identity validation, explicit global fallback | Open |
| RQ run escapes scope or races | High | Root lock, security review, run-tree checks, config binding test | Open |
| Local stack is stale | Medium | Preflight active jobs/queue; prefer targeted recreation; health check after restart | Open |
| `plastic-bundling` is all-valid | Low | Required no-op RQ proof; hermetic fixture covers selection | Open |

## Verification Checklist

- [ ] Additive NoDb/Parquet schema compatibility recorded before code edits.
- [ ] ADR field/radius/normalization/tie contract matches implementation.
- [ ] Legacy hydration and existing consumers pass.
- [x] `plastic-bundling` RQ job completes and artifacts are inspected.
- [x] Current-invalid RQ job completes with conditional candidate preparation,
  local selection, and coherent generated output.
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

### 2026-07-22 UTC: Historical-invalid watershed recheck

**Agent/Contributor**: Codex

**Work completed**: Used the operator-supplied scoped JWT to submit and poll
`build-soils` for `improvident-dyslexia` / `disturbed9002_wbt`.

**Result**: PASS for current recovery/no-op behavior. The 3,597 raw/final
assignments agree; no current substitutions or local selections occurred;
candidate preparation was not attempted. This historical-invalid watershed
therefore cannot furnish true-current-invalid local-selection acceptance.
Evidence is appended to `artifacts/2026-07-22_rq_acceptance.md`.

### 2026-07-22 UTC: Current-invalid local donor RQ acceptance

**Agent/Contributor**: Codex

**Work completed**: Used the operator-supplied scoped JWT for
far-out-quiescence / disturbed9002_wbt to discover the live API contract,
submit the resolved build-soils request, poll its terminal result, and inspect
candidate, NoDb, Parquet, and soil artifacts.

**Result**: PASS for true-current-invalid local selection. Nine hillslopes
whose raw MUKEY 2712917 remains non-buildable selected local vector-profile
donors (eight 2712901, one 2712931) at 250 m or 500 m; none used the global
donor 2712884. Candidate preparation was prepared and every final soil
reference existed. The initial attempt exposed an exact CRS-WKT publication
drift, fixed by recording metadata from the persisted raster and covered by a
regression test. Full redacted evidence is in
`artifacts/2026-07-22_rq_acceptance.md`.

**Next steps**: Complete remaining M3 adversarial/generated-output evidence
and M5 review disposition; these remain the release-hold gates.

### 2026-07-22 UTC: Committed M3 adversarial selection corpus

**Agent/Contributor**: Codex

**Work completed**: Added a small synthetic JSON corpus and explicit runner
that call the production shallow-profile and vector-selection functions without
external SSURGO, raster, or RQ dependencies. It covers primary and padded
donor eligibility, radius escalation, deterministic ties, insufficient shared
fields, invalid source/candidate profiles, and disconnected source locations.

**Decision**: The corpus is deliberately not collected by pytest. It is a
reviewer-invoked release-evidence command; narrow pytest tests continue to
cover filesystem publication, builder failure injection, and persistence.

**Result**: Initial execution passed all 10 cases. The draft texture case
revealed that an invalid sand/clay pair does not invalidate an otherwise
three-field profile; the committed scenario instead proves that the candidate
is skipped when removal leaves fewer than three usable fields.

**Next steps**: Add/verify the remaining M3 artifact, materialization,
legacy-hydration, and generated-output evidence.

### 2026-07-22 UTC: M3 adversarial and propagation closure

**Agent/Contributor**: Codex

**Work completed**: Closed the remaining M3 fault and compatibility boundaries.
Tests cover failed candidate-crop publication preserving the prior manifest,
canonical-source and native-support errors, non-dominant invalid-MUKEY no-op,
nonbuildable padded candidate exclusion, candidate-build/support/donor-write
global degradation, selected-donor rollback/retry, and nullable legacy JSON
provenance. The source resolver now reports missing configured roots using its
canonical error contract; legacy JSON evidence no longer becomes a literal
`"null"` string.

**Evidence**: Focused SSURGO/NoDb tests, the ten-case explicit corpus,
test-stub validation, and changed-file broad-exception enforcement. The
required full sweep reached 310 passed and 17 skipped before an unrelated
order-sensitive browse-auth route test failed; that exact test passes in
isolation.

**Result**: M3 complete. The M4 all-valid and current-invalid RQ acceptances
remain valid. M5 independent review/disposition is now the only release-hold
phase.

### 2026-07-22 UTC: M5 review and disposition start

**Agent/Contributor**: Codex

**Work started**: Reconciled the active ExecPlan, tracker, M3 committed corpus
and generated-output evidence, M4 RQ acceptance artifact, and ancestor
checkpoint `bf5f2e62c`. The implementation commits remain descendants of the
accepted contract checkpoint.

**Next steps**: Complete fresh code, QA, and security review records; update
the append-only ledger with reviewer-visible verification; then run the M5
release gates and issue a GO or HOLD recommendation.

### 2026-07-22 UTC: M5 concurrent candidate-publication evidence

**Agent/Contributor**: Codex

**Evidence**: Added `test_candidate_preparation_concurrent_retry_leaves_valid_active_artifact`.
It synchronizes three publishers, injects one crop failure, retries publication,
and verifies that the active manifest remains loadable, immutable artifacts are
complete, and temporary files are absent. `wctl run-pytest
tests/soils/test_ssurgo_fallback.py --maxfail=1` passed 15 tests.

**Disposition impact**: Resolves the security review's missing concurrent
candidate-publication/retry evidence gap, pending its independent re-check and
final append-only review disposition.
