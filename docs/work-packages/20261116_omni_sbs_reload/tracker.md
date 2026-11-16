# Omni SBS reload tracker

## Status

Complete: implementation, scoped tests, native watershed/report acceptance, and
queued browser resubmission passed. Updated 2026-11-16 UTC. No production rollout.

## Task board

- [x] Trace hydration, serialization, persistence, admission, and canonical display.
- [x] Record consumed-source mismatch and row-association risks.
- [x] Capture user requirement for contract-first implementation and scoped tests.
- [x] Retain source/regression reproduction and real saved-response/browser evidence; no pre-fix browser recording was captured.
- [x] Record user-directed two-location resolution and simple existing-project policy.
- [x] Include independent user-file staging contract in package scope.
- [x] Draft shared staging contract and Omni-specific contract delta.
- [x] Complete independent contract reviews and accepted ancestor checkpoint.
- [x] Add failing scoped regressions, implement bounded fix, rebuild controller bundle.
- [x] Run scoped tests, authenticated browser submission/reload, and native input/reset validation.
- [x] Repair disposable baseline and complete final watershed/report acceptance.
- [x] Complete correctness/UX and security code reviews; update affected documentation.

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
Contract ancestor revision: `67468cf86` (reviewed contracts only, before code edits).

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

## Implementation — 2026-11-16 UTC

Saved SBS references now hydrate/serialize and feed shared scenario identity
readers, including accepted-map deletion with a pending replacement. Numeric type
8 hydrates correctly. Backend matches persisted associations and resolves staged
or corresponding child maps; new uploads stage separately, restored bytes are
checked before publication, and accepted inputs are rechecked at commit.

Scoped validation: 116 Python tests, 26 controller tests, targeted ESLint pass.
Independent correctness and security code gates pass with findings closed.
Generated bundle rebuilt through `wctl run-python` because host Python lacks
Jinja2. Native acceptance is running on independent copy
`qa-omni-reload-20261116`; 4,165 source files copied with identity/readback evidence.
Browser and native completion evidence remain pending. No production deployment.

## Final implementation handoff — 2026-11-16 UTC

Scoped checks: 116 Python tests plus 2 real NoDb commit/drift tests, 26 controller
tests, targeted ESLint, bundle build, broad-exception check, and documentation
lint passed. No full suites run. Contract ancestor is `67468cf86`; implementation
revision is the subsequent task-scoped commit (see git history).

Authenticated dev browser submitted through the actual Run Omni button with zero
selected files, received HTTP 202, and retained the filename/reference on reload.
`artifacts/browser_acceptance.json` and screenshot retain evidence. The dev
rq-engine API was restarted to load the candidate; workers/production were not
restarted. Native input restoration passed through actual admission/persistence,
reset, verified copied raster, regenerated model inputs and 217 fresh hillslope
outputs. Full watershed and final report acceptance are blocked: channel climate
starts 2007 while hillslope passes start 1980. See `artifacts/validation.md`.

Both independent code reviews pass with findings closed. Package remains open
only for the environment gate; no speculative climate fix or production rollout
was attempted. Disposable run `qa-omni-reload-20261116` is retained for inspection.

## Fixture repair authorization and plan — 2026-11-16 UTC

User requested fixing the fixture. Diagnosis: copied Climate state and current
`climate/*.cli` use 2007–2024, but prepared parent `wepp/runs/p*.cli` still use
1980. Omni deliberately inherits those prepared hillslope inputs while preparing
channel climate from current Climate state. Repair only the disposable project:
retain failed-input hashes/backups, rematerialize prepared climate via the existing
Wepp preparation method, regenerate baseline outputs, and rerun consumed-map
admission plus scenario execution/report. Preserve climate data/configuration,
model parameters, public schemas, and the original source project. No ADR needed:
this regenerates stale derived artifacts without a parameterization decision.

Regression plan: compare every prepared hillslope climate to its selected source,
validate actual daily-year sets against 2007–2024, verify baseline and scenario
pass/output year sets and final report, and repeat the authenticated no-upload
submission through completion. Update the reusable fixture preparation path so
future copies cannot silently reuse stale prepared climates.

## Fixture repair outcome — 2026-11-16 UTC

Canonical baseline preparation replaced stale 1980/45-year derived inputs with
current 2007–2024 climate inputs. All 217 prepared climate digests match their
selected source; previous prepared inputs remain in `fixture_repair_before/`.
Source project NoDb and climate/prepared-climate hashes stayed unchanged.
Baseline and restored-child watershed execution succeeded, output year sets agree,
and 22-row reports are retained. Browser submission with zero selected Files
returned 202, reload retained the filename/reference, and all three reuse/compile/
finalization jobs finished. See `artifacts/validation.md` for final receipts.
No production code or model parameter changes were needed for this fixture repair.
