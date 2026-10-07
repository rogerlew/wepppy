# Fix fork option availability and absent-Omni readiness

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
All paths are repository-relative. Timezone: UTC.

## Purpose / Big Picture

A completed non-Omni fork must expose its project link even if an older client
selected skip Omni. New console sessions should explain and disable options
that cannot affect the source. The proposed authority is
`docs/ui-docs/contracts/fork-console-contract.md`; no implementation starts
until its reviewed checkpoint is committed.

## Progress

- [x] (2026-10-07 23:09 UTC) Diagnose incident and prepare proposed checkpoint.
- [x] (2026-10-07 UTC) Operator approved checkpoint, reviewers, and implementation.
- [ ] Obtain exact checkpoint acceptance, two independent reviews, and commit.
- [ ] Add regressions and implement within the recorded source boundary.
- [ ] Complete local checks, production read-only replay, and final reviews.

## Surprises & Discoveries

The worker already accepts missing Omni by skipping reset, but readiness
demands reset artifacts. All three incident forks selected the same flags.
The visible timeout is a persistent predicate mismatch, not evidence that
copying needs more time. A disabled checkbox alone does not protect explicit
JavaScript payload construction or existing queued jobs.

## Decision Log

2026-10-07: retain the current API and worker contracts; add UI guidance and
correct only the readiness predicate. This keeps old submissions working and
avoids a new capability endpoint or execution mechanism. Count configured and
retained Omni children to avoid hiding useful reset behavior before execution.

## Outcomes & Retrospective

Diagnosis and checkpoint draft only. Runtime edits, validation of the candidate,
independent reviews, and deployment have not occurred.

## Milestones and concrete steps

First, ratify the exact option/readiness state matrix, obtain two independent
read-only contract reviews, disposition findings, and commit docs as an ancestor.
Record that revision in `tracker.md`. The operator has explicitly approved
the new package's checkpoint commit and two reviewer agents.

Second, add failing tests under `tests/weppcloud/routes/` using actual temporary
filesystem trees and actual Jinja rendering. Extend existing console tests for
disabled initialization and explicit boolean payload assembly. Implement small
helpers in the existing fork route; use bounded JSON metadata reads without
hydrating/migrating controllers or loading all contrast sidecars. Use existing
Pure checkbox/help conventions and preserve poll/readiness lifecycle behavior.

Third, run focused route/render tests with `wctl run-pytest`, frontend lint and
tests with `wctl run-npm lint` and `wctl run-npm test`, and required bundle rebuild
with `wctl run-python wepppy/weppcloud/controllers_js/build_controllers_js.py`.
Run `wctl run-pytest tests --maxfail=1`, changed broad-exception enforcement,
and `wctl doc-lint --path` for touched Markdown. Record unrelated blockers
without claiming a passing gate.

Finally, perform an isolated, read-only candidate readiness replay against the
three incident destinations listed in the contract-decision artifact, under
the existing wepp1 web identity and mount. Read back core controller identity
and optional-state semantics; do not requeue, recreate, or modify those projects.
Complete correctness and security reviews and update package, tracker, this
plan, and the project board with the highest supported completion claim.

## Validation and acceptance

The exact regression must fail before the patch and pass afterward. New
non-Omni/no-SBS pages show disabled unchecked controls and explanations,
including true query values. Available capabilities remain selectable and
independent. Legacy submissions with skip Omni true finish the existing
readiness/link flow. Core missing files, pending jobs, mismatched jobs, auth
failure, and hostile filesystem entries do not become ready.

## Idempotence and recovery

Capability/readiness inspection is read-only and can be repeated. Rollback is
reverting the bounded code change; no persisted migration exists. No production
deployment, worker restart, or project repair is authorized by this plan.

## Interfaces and dependencies

Reuse current source `get_wd`, plain-JSON NoDb metadata, existing Omni scenario and
contrast metadata, disturbed SBS metadata/path, Pure macros, and filesystem
descriptor checks. Do not add fields to run data or alter the readiness JSON
shape. The only new context is the two source capability booleans used to
render controls. No new dependency is permitted.

Revision note: created 2026-10-07 to cover the diagnosed readiness mismatch and
the operator's requested unavailable-option guidance.
