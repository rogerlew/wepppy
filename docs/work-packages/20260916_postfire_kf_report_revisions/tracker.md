# Kf and rainfall-response revisions tracker

Started/updated: 2026-09-16 UTC. Status: execution started; source research and
contract checkpoint `9395f4722` accepted; runtime implementation underway.
Starting revision: `5f98c577a`. Security: high; dedicated review required.

## Progress

- [x] Capture owner direction, exclusions, compatibility and complexity budget.
- [x] Draft parameterization ADR and self-contained implementation ExecPlan.
- [x] M1: establish Kf scientific source/aggregation proposal and authentic source comparisons.
- [x] M2: canonical amendments passed independent correctness/security reviews;
  disposition and standalone ancestor checkpoint `9395f4722` recorded.
- [x] M3: implement and wire module-owned Kf; remove RUSLE coupling.
- [x] M4: implement response curve and rainfall provenance labels/exports.
- [x] M5: regression, real workflow evidence, correctness/security/UX review.
- [x] M5 live gate: restart forest stack, confirm health and updated web/worker
  code, then complete nervous-mesquite M1 UI/RQ → Kf results → report/export/reload.
- [ ] M6: promote final docs and close implementation package.

## Decisions

2026-09-16 UTC / owner: execute this package. This supersedes original scaffold-only
limits, retaining named live acceptance and all pre-implementation gates.

2026-09-16 UTC / root: propose USGS KFFACT COG, original all-layer/component
aggregation, customary units and nearest alignment after independent source
comparison. Prepare source within each attempt; no shared cache/pointer. Exact
policy is in `docs/kf_source.md` under the module and ADR-0068. Report sampling
and provenance are in the report contract's 2026-09-16 amendment. Independent
review delegation was requested and is pending; no review approval or ancestor
commit is claimed.

2026-09-16 UTC / owner: new M1 should replace RUSLE K with stricter USGS-compatible
Kf; gridded RUSLE ceases to be a post-fire dependency. This is a new direction,
not an amendment to the closed verification audit. "Strict" concerns Kf identity
and evidence, not revival of rejected M3 material/thickness restrictions.

2026-09-16 UTC / owner: response curve is useful; existing delineation stays.
Carry forward the accepted labeling clarification: NOAA is design rainfall,
whereas the audited dated event peaks are modeled GridMetPRISM/CLIGEN rainfall.

2026-09-16 UTC / root: scaffold only. Source hierarchy, aggregation and exact
payload/curve sampling policy remain checkpoint work, not invented defaults.
No live mutation, source acquisition, implementation, commit or push this turn.

2026-09-16 UTC / owner follow-up: include restarting the forest stack and
verifying an end-to-end run on `nervous-mesquite` during package execution.
This explicitly authorizes that named acceptance rerun, not immediate operations
in this documentation turn. Preserve the previous attempt and protected inputs;
other existing runs still require their own authority. Retain restart/job/report
evidence, not only service-health or unit-test results.

## Evidence and risks

Execution artifacts: [source policy](artifacts/kf_source_policy.md),
[contract checkpoint](artifacts/20260916_contract_decision.md),
`artifacts/source-probe/results.json` and retained original sources/ranges.
All 301,379 compared native cells exactly match original polygon KFFACT.
The COG metadata incorrectly labels conductivity; original field lineage and
numerical comparison support customary erodibility units. This interpretation
awaits independent review and does not claim publisher confirmation.
At the initial scientific checkpoint no runtime/project writes had occurred;
implementation and live acceptance are recorded below.

Thomas audit: `../20260916_thomas_fire_verification/artifacts/findings.md`.
At I15=24 mm/hour: run 85.63%, USGS 69.35%; K 0.337162 versus Kf 0.139364.
Different basin conventions prevent exact output equality as a success oracle.
Source availability, historical aggregation ambiguity and old-manifest currentness
are explicit risks. The source checkpoint must close them without broadening M3.

## Required review artifacts

Retain scientific source evidence, compatibility/state matrix, contract decision,
two independent contract reviews and dispositions, correctness review, security
review, dedicated UX review, and generated-output validation under `artifacts/`.
Do not create empty approval artifacts or report scaffold completion as wiring.

## Scaffold validation

Package, ADR, specification, roadmap and project tracker doc lint passed;
`git diff --check` passed. No executable code changed or model tests run.
Existing audit artifacts and unrelated code-quality changes were preserved.

## Execution checkpoint validation

Source parity passed for 301,379 native cells in two regions; bounded transport
used 12 requests and 655,360 bytes. All 20 proposal/package Markdown files passed
lint and `git diff --check` passed. See
[validation](artifacts/checkpoint_validation.md). No runtime regression tests,
restart or rerun occurred because implementation has not begun. Resume M2 with
independent reviews, disposition and authorized standalone ancestor commit.

## Completion authorization

2026-09-16 UTC: owner explicitly reiterated complete-package delivery including
stack restart and end-to-end run after the request for independent reviews and
checkpoint commit. These required steps are authorized; no further permission
stop is needed. Two independent contract reviews are running. The latest user
rerun remains legacy code and will be preserved as the before-state.

## Implementation progress

Kf/schema-3, source decoupling, preflight dispatch and response curve are wired.
633 module tests, 250 routes/render checks, canonical archive regression, Go
preflight, 112 frontend suites/899 tests and facade stubtest pass. Independent
review defects are fixed and covered. Full repository sanity passed: 8,693 passed, 103 skipped, 1,109.71s.

Forest restart and both actual UI/RQ/browser acceptances passed. Named new
attempt `0ea9c1f5b0964b22ba7f1b457c1a6c9f` has Kf 0.139396 and I15=24 probability
72.19%. Fixture `pfdf-kf-e5c25f5b` ran without RUSLE/POLARIS and retained its
post-fire control/current results immediately after RUSLE removal and after two
reloads. Actual generated files round-trip through canonical archive/restore.

Evidence: [restart](artifacts/forest_restart_validation.md),
[named run](artifacts/nervous_mesquite_e2e.md),
[generic/M3](artifacts/generic_e2e.md). All final independent reviews PASS; final documentation/commit closeout remains; no push or production deployment.
