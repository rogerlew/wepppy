# Tracker — Portland combined watershed viewer

**Started / last updated**: 2026-10-12 08:21 UTC  
**Phase**: M0 contract checkpoint preparation; forest execution authorized  
**Security**: high; reviews pending  
**Next milestone**: M0 evidence refresh and contract checkpoint preparation

## Task board

- [x] Capture operator's Portland group-access correction and reject public publication as a workaround.
- [x] Create package, active ExecPlan, decision draft, and pending review artifacts.
- [ ] M0: Refresh production evidence, identify authoritative Portland resource association, inventory all access/consumer surfaces, and prepare canonical amendments.
- [ ] M0: Obtain two independent contract reviews; record accepted ancestor revision before code edits (commit authority not supplied by scaffold request).
- [ ] M1: Implement bounded group read access and direct positive/negative tests.
- [ ] M2: Prove legacy conversion compatibility on one copied run; prepare audited artifact repair for all affected collections.
- [ ] M3: Wire Deck.gl collections, repair generator, and preserve old URLs.
- [ ] M4: Complete unit/integration/browser checks and independent correctness/security reviews.
- [ ] M5: Separately authorized deploy, affected-run repair, live verification, and observation window.

## Decisions

**2026-10-12 08:21 UTC** — Operator intent is Portland group access. Local source identifies existing `PortlandGroup`; use current membership, an authoritative resource association, and per-run checks. No PUBLIC marker changes or inferred prefix grants. Rationale and rejected alternatives: [package: Accepted intent and rationale](package.md#accepted-intent-and-rationale).

**2026-10-12 08:21 UTC** — Scaffold only. No canonical policy amendment, checkpoint approval, implementation, commit, run conversion, or deployment is claimed. The [decision draft](artifacts/2026-10-12_contract_decision.md) is not an accepted ancestor.

## Risks and open evidence

The October 10 production investigation is summarized in the ExecPlan but raw transcripts were not retained in this package. Revalidate against the deployed revision. A reliable Portland run association, actual membership records, ordinary owner/public behavior, query-engine transport, optional phosphorus availability, and converter compatibility remain to be demonstrated. Do not assume every ownerless legacy run is intended to become private.

## Verification and review

Scaffold checks (2026-10-12 UTC): `wctl doc-lint` validated all six package files and PROJECT_TRACKER.md with zero errors/warnings; `uk2us` preview found no package spelling changes; `git diff --check` passed. Runtime checks: not run; documentation-only task.

[Correctness review](artifacts/2026-10-12_correctness_review.md): pending. [Security review](artifacts/2026-10-12_security_review.md): pending. Contract reviews and accepted ancestor revision: absent. Before closeout retain focused and broad Python results, frontend lint/tests, authenticated browser evidence, exact generated-content comparisons, production-equivalent identities/mounts, rollout/rollback record, and observation results.

## Hardening signal log

Prior baseline: 403 at collection entry; 404 at legacy value endpoints; 400 at empty generator. Post-change: not measured. Temporary mitigations: none. Observe authorized rendering and unauthorized rejection together; do not count an HTTP 200 shell as restored service.

## Handoff

Execute [the active plan](prompts/active/portland_combined_viewer_execplan.md) under the operator’s forest authorization. Start with M0; preserve the distinct contract-commit gate. Maintain Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective in the plan and this tracker at every milestone. Do not mark the package complete on documentation or local tests alone.

## Execution update — 2026-10-12 16:40 UTC

Forest implementation, required local commits, restarts, and dev-agent permission adjustments are now authorized. Production writes/deploy remain excluded. Fresh read-only wepp1 inventory confirms all 63 runs exist and are ownerless/non-PUBLIC with loss text and no loss Parquet. Preserve their existing ordinary data visibility; collection admission is the bounded correction. Contract reviews are underway.
