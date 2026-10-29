# Project developer mode tracker

Updated: 2026-10-29 01:06 UTC.

## Task board

- [x] Inspect current UI, Python and Rust bounds and role conventions.
- [x] Record approved lifecycle, cloning and parameter policy in DM-01, SA-01 and ADR-0088.
- [x] Scaffold package, implementation ExecPlan and contract checkpoint.
- [x] Obtain two independent contract/package reviews and disposition every finding; reviewers confirmed C2/C3 design fixes and open lifecycle findings.
- [x] Operator approved incoming-state replacement, including true-to-normal; contract/plan amended.
- [x] Both independent reviewers confirmed all design findings closed.
- [x] Commit reviewed checkpoint as standalone ancestor `44746ff63`.
- [x] Implement runtime behavior and complete focused/native/frontend/local-worker/browser validation.
- [x] Independent correctness/security reviews closed all implementation findings.
- [ ] Finish full Python suite and package closeout.

## Decisions

- 2026-10-29 00:51 UTC — Operator approved permanent Ron-owned mode, exact Dev-role activation, project-policy-only bounds enforcement and clone inheritance. Avoid reversible/clamping semantics and user-dependent worker validation.
- 2026-10-29 00:51 UTC — Scope this session to documentation/review. No code, native build, project mutation or deployment is authorized by this scaffold.

## Risks and decision points

Native/Python compatibility, Dev-only panel reachability, clone variants and restore-over-live semantics require explicit verification. Do not infer a general authorization bypass from developer mode. See the review disposition for resolved and open decisions.

Operator decision recorded: old-archive restore and failed-fork recovery may overwrite activated mode with incoming normal state. This preserves recovery flexibility and avoids additional implementation complexity. No policy question or blocking design finding remains; both reviewers confirmed closure.

## Verification and handoff

Starting implementation revision: `cebb4b4283e408fd270126811f4dbbd1a8dfd8e2`.
Contract ancestor revision: `44746ff63`; implementation started after this standalone checkpoint.
Documentation validation: scoped `wctl doc-lint` passes; final rerun recorded in review artifacts. Spelling preview found only existing PROJECT_TRACKER text changes (including the `axe` tool name); none applied. Runtime validation: not run (documentation-only scope).

Next: prepare a standalone reviewed contract commit and future execution of the [ExecPlan](prompts/active/implementation_execplan.md). Implementation must maintain this tracker and plan and retain separate implemented/local/environment/deployed evidence claims.

## Lifecycle decision — 2026-10-29 01:06 UTC

The operator rejected preserving destination mode or blocking archive/failed-fork recovery. Incoming state wins, even when normal; no off toggle is added. Rationale: simpler implementation and maximum user recovery flexibility; blocking recovery could make projects unusable.

Implementation note: Ron activation takes the existing catalog lifecycle guard before the NoDb lock and fresh hydration. Independent correctness inspection confirms fork/archive already use this guard; no queue/copy changes are necessary to preserve capture consistency.

## Implementation evidence — 2026-10-29 UTC

See [validation](artifacts/validation.md), [runtime receipt](artifacts/runtime.json), [browser receipt](artifacts/browser.json), and final correctness/security artifacts. Actual preparation, model execution and fork succeeded. Native `4d4c075` is published and verified upstream; unrelated sibling edits are untouched. Full Python suite is in progress.
