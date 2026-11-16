# Omni SBS reload tracker

## Status

Contract-first execution active; contract drafts and reviews prepared.
Updated 2026-11-16 19:05 UTC.

## Task board

- [x] Trace hydration, serialization, persistence, admission, and canonical display.
- [x] Record consumed-source mismatch and row-association risks.
- [x] Capture user requirement for contract-first implementation and scoped tests.
- [ ] Reproduce browser failure and capture actual saved scenario response.
- [x] Record user-directed two-location resolution and simple existing-project policy.
- [x] Include independent user-file staging contract in package scope.
- [x] Draft shared staging contract and Omni-specific contract delta.
- [ ] Complete independent contract reviews and accepted ancestor checkpoint.
- [ ] Add failing scoped regressions, implement bounded fix, rebuild controller bundle.
- [ ] Run scoped validation and real artifact/browser acceptance.
- [ ] Complete correctness/UX and security artifacts; update affected documentation.

## Decisions

- **2026-11-16 19:05 UTC:** User requested a work-package scaffold, followed by
  contract-first implementation with scoped tests. This session delivers planning
  only. Broad repository/frontend suites are excluded by that explicit scope.
- **2026-11-16 19:05 UTC:** Preserve saved map state separately from the file input;
  use canonical filename presentation. Rationale and backend decisions are in
  `package.md`, section “Contract decisions and rationale”.
- **2026-11-16 19:05 UTC:** Do not treat a UI-only path field as a complete fix:
  admission expects a temporary source that execution can consume.

## Validation record

Source inspection only; no runtime tests or production actions performed.
Scaffold validation: package docs (3 files) and root project tracker passed
`wctl doc-lint` with zero errors/warnings; spelling preview showed no changes;
`git diff --check` passed. No application tests run for this documentation-only turn.
Starting implementation revision: `65fa0c0bd008b16157a82191a766a0bdb9453173`.
Contract ancestor revision: not yet created.

## Risks and next handoff

Implement the documented `_limbo`-then-associated-scenario lookup and stage input
before child reset when execution is required. Verify row identity rather than
index-based file reuse. Inspect the actual browser to explain missing filename
presentation, since source already contains a conditional help-text display.

Existing unrelated working-tree changes include root onboarding, project tracker,
shared contracts, controller-input-validation documents, a management JSON file,
a culvert artifact, and the generated usersum index. Preserve these changes.

Health signal: accepted saved scenarios reload and resubmit with the intended
raster and no re-upload. Danger signals: wrong-map reuse, stale output, lost prior
selection after failed replacement, or increased permission scope. Observe the
whole upload/run/reload/resubmit/replacement cycle during scoped acceptance.
No temporary mitigation is introduced; no sunset action is needed.

## Follow-up decision — 2026-11-16 UTC

The user clarified that the map can be in `_limbo` or the Omni scenario project
and requested avoiding legacy-policy complexity. Apply one lookup/validation
rule to old and new projects; a missing historical receipt alone is not grounds
for re-upload. Preserve existing output-freshness checks separately. No new
storage, migration, or receipt scheme. See package.md, “Contract decisions and
rationale”. Canonical amendment and implementation remain pending.

## Shared staging contract decision — 2026-11-16 UTC

User approved `docs/schemas/user-file-staging-contract.md` as a deliverable in
this package. It owns the reusable lifecycle; Omni supplies concrete locations,
association, and rerun behavior. Other uploads are not migrated or claimed
conformant. See package.md, “Shared staging contract deliverable”, and ExecPlan
Milestone 1. Contract drafting/reviews remain pending; this update changes scope
documentation only. Scoped documentation lint and spelling/diff checks passed.

## Contract execution — 2026-11-16 UTC

Operator authorized proceeding with contract-first execution, including the plan's
required ancestor checkpoint. UFS-01/OSR-01 drafts and freshness/upload amendments
are prepared. Independent contract reviews identified same-child ambiguity and
postcommit error semantics; both were clarified before implementation. The two
review artifacts retain findings and disposition. No implementation file has
been edited before the checkpoint. Only package/new or specifically amended
contracts will be committed; unrelated dirty shared contracts remain excluded.
