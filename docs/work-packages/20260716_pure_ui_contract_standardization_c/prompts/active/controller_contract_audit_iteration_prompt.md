# Test and repair one Pure UI controller contract

> **Purpose**: Reusable protocol for one bounded controller iteration.
> **Target**: Primary Codex agent.
> **Status**: Active.

## Boundary

Select exactly one controller or one inseparable controller facet from
`artifacts/controller_audit_register.md`. The controller inventory is a backlog,
not a dependency graph and not a reason to combine work.

One iteration must:

1. establish intended behavior;
2. test actual rendered and downstream seams;
3. identify mismatches;
4. patch only confirmed mismatches;
5. run existing applicable gates; and
6. retain the regression tests before moving on.

Do not build initiative-wide registries, manifests, change classifiers,
dependency engines, attestations, or CI workflows during a controller
iteration.

## Package Setup

Use the standard work-package layout:

- `package.md` for the exact controller boundary and exclusions;
- `tracker.md` for fields, mismatches, tests, patches, runtime, and decisions;
- one active ExecPlan; and
- a concise contract or field matrix.

Add security or independent-review artifacts only when an actual production
patch triggers them. Test/documentation-only work begins with security impact
`none`.

## Before Production Edits

Read the nearest subsystem and test instructions, then inspect:

- the actual controller source and generated/runtime relationship;
- the actual Jinja template and relevant macro calls;
- the route parser and normalization;
- the persistence owner and reload/bootstrap path;
- RQ code only for values or lifecycle behavior that reach it;
- current focused tests; and
- current canonical intent.

A field or action is risk-bearing when its rendered value or use can change a
submitted payload, persisted or reloaded state, queued work, or visible
workflow state. Record any reviewed field/action excluded from that set and the
reason in the controller package or field matrix. For each included field or
action, record only:

| Contract value | Required evidence |
| --- | --- |
| DOM id and submitted name | Actual rendered HTML |
| Type, option token, default, selected/disabled/hidden state | Actual render plus focused browser behavior |
| Serialized key/value | Focused JavaScript test |
| Parser key/type/default/alias | Focused route test |
| Persisted attribute and reload value | Focused NoDb/save/reload test |
| RQ input or lifecycle | Focused worker/RQ test when applicable |

If intent is missing or conflicting, stop for a bounded decision. Do not infer
desired behavior from code.

## Tests First

Write the cheapest test that crosses the suspected mismatch. Prefer:

- actual-template render assertions over hand-authored DOM;
- direct assertions over generic helpers;
- focused JavaScript tests over browser orchestration when both prove the same
  seam;
- focused route/persistence tests over full job execution when RQ is not
  involved; and
- existing test commands over new runners or workflows.

For a confirmed mismatch, demonstrate the regression fails before the patch
when practical. If behavior already conforms, retain the new test and continue.

## Minimal Repair

Make one small compatible repair at a time. Preserve public payload keys,
aliases, persisted state, defaults, parameterization, authorization, upload
handling, queue wiring, and unrelated behavior by default.

Do not combine:

- refactoring or cleanup;
- visual redesign;
- new features;
- new defaults or compatibility policy;
- broad shared-helper modernization; or
- unrelated documentation rewrites.

Change a shared macro/helper only when a controller-local repair would be
incorrect. First add regression coverage for the affected controller and the
direct consumers identified by repository search. If that coverage is not
practical, narrow or defer the shared change.

## Tooling Rule

Tooling must make existing tests easier and more accurate.

- Start with direct assertions.
- Extract a helper only after at least two tests repeat the same logic.
- Keep helpers stateless, test-only, and smaller than the tests using them.
- A helper must expose the field mapping in failure messages.
- Do not create a separate tooling package.
- Do not add a schema, generator, registry, manifest, planner, diff engine, or
  workflow without a measured missed defect or repeated burden and explicit
  operator approval.

## Validation

Run focused tests while iterating. After controller JavaScript changes:

    wctl run-npm lint
    wctl run-npm test
    python wepppy/weppcloud/controllers_js/build_controllers_js.py

After Python changes, run the exact affected pytest modules and the appropriate
broader suite. Run `wctl check-rq-graph` only if enqueue sites or dependencies
change. Run documentation lint for changed docs and `git diff --check`.

Do not run expensive RQ or full-repository gates before cheap render, syntax,
lint, and focused contract tests.

## Review and Security

- Test/documentation-only iterations need normal package review, not a
  hypothetical high-security artifact.
- A production patch receives one independent correctness review.
- A dedicated security review is required only when the actual patch changes an
  attack surface such as auth/session/CSRF, upload/path handling, protected
  output, queue authorization, subprocess behavior, secrets, or egress.
- A second independent review is reserved for high-risk behavior changes,
  shared-producer patches with material fan-out, or explicit operator request.

Unresolved high/medium findings block the production patch. Review artifacts
must remain proportional to the change.

## Closure

Close the controller iteration when:

- intended and observed behavior are distinguished;
- actual-render tests cover risk-bearing field identities and state;
- applicable serialization, parser, persistence/reload, and RQ seams are tested;
- confirmed mismatches have minimal patches and retained regression tests;
- focused and existing applicable broad gates pass;
- generated assets are current when source changed;
- required review/security gates for the actual patch are complete; and
- runtime, mismatches, helper value, remaining gaps, and the next controller are
  recorded.

Do not require a machine registry or maintenance gate for closure.

## Stop-Loss

Stop and simplify if test tooling fails twice, metadata maintenance exceeds test
work, a controller repair creates more governance files than product/test files,
or a cheap deterministic failure appears after a broad test run. Continuing
past a stop-loss requires an explicit operator decision.
