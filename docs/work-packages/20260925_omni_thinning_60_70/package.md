# Omni thinning 60% and 70%

Status: completed code delivery/local validation 2026-09-25 UTC.
Owner: requesting operator; implementer: Codex.

## Scope and complexity budget

Add 60% and 70% remaining canopy cover, each with 75/85/90/93% ground cover.
Offer 30, 40, 50, 60, 65, 70% in ascending order. Keep 40% default and retain
65% availability, assets, IDs and saved selections for old-project compatibility.
Follow the static additive recipe of the closed 20260920_omni_thinning_30_50
package without modifying that historical package. Eight new assets, five
catalogs, CSV mirror, existing selector and bounded regression extensions only.
No migration, dependency, queue, service, template refactor, deployment or live
project mutation. Preserve all other parameters and precedence rules.

## Compatibility and regression plan

Allocate unused IDs 151–158 in disturbed/au/eu/revegetation and 451–458 in c3s;
verify collision freedom before implementation. Copy corresponding 40% files,
changing only cancov. Compare every existing catalog entry and management file
against starting revision. Preserve payload percent strings and scenario names.
Read new values through parser/writer, single-OFE and multiple-OFE synthesis,
prepared inputs, and canonical archive/restore. Extend soil artifact coverage
for the new prefixes under the existing thinning soil contract.

## Governance and acceptance

Canonical authority: [thinning contract](../../ui-docs/contracts/omni-thinning-contract.md)
and [ADR-0074](../../adrs/ADR-0074-omni-thinning-60-70.md).
Security impact: none; no attack-surface, auth, persistence or path changes.
Two independent contract reviews and standalone ancestor checkpoint precede
implementation; independent final correctness and QA reviews close findings.
Run focused Python, controller lint/tests and bundle build, then required broad
Python suite. Existing unrelated timeout-test failure must be reported honestly
if it recurs, without changing unrelated timeout behavior in this package.

## Artifact and state boundaries

Reuse ordinary landuse and wepp/runs management files, soils and diagnostics;
no new paths, exclusions or lifecycle. Cover never-used/empty lists, populated
new choices and supported legacy 65% hydration. Malformed inputs retain existing
errors. Working/failed/completed state and retry behavior are unchanged; archive
snapshots preserve new and legacy files. Run existing browse/download tests.
Highest delivery claim is locally validated generated inputs. Live browser,
production-equivalent execution, deployment and fresh model reports remain
operator-owned release gates, not claims of this code-delivery package.

## Execution

[ExecPlan](prompts/completed/omni_thinning_execplan.md); [tracker](tracker.md).

## Outcome

Delivered eight 60/70 assets, eight additive records in each of five catalogs,
CSV mirror and six-choice selector in `2d0891398`, after reviewed contract
ancestor `9ed739875`. Retained all 16 prior assets, 322 catalog records, every
existing CSV byte, 65% support and 40% default. Durable compatibility decision is
in the canonical thinning contract, Compatibility, states and errors / Choice
and parameter contract, and ADR-0074 (including safe rollback after saved use).

Validation: 308 focused Python tests plus 12 subtests, 913 frontend tests, 230 real
soil artifact cases, lint, bundle build and documentation checks pass. Independent
correctness and QA reviews report no package findings. The required broad run
stopped with 5,326 passed, 54 skipped and one confirmed preexisting timeout-test
failure (60 expected, 120 implemented per unchanged ADR-0072); later tests were
not run. Full-suite success is not claimed. See
[validation summary](artifacts/validation-summary.md) for evidence and limits.

No deployment, live browser acceptance or fresh model reports. Operator owns
those release gates. Repository maintainers own the unrelated timeout expectation
follow-up. Closed historical packages were not modified.
