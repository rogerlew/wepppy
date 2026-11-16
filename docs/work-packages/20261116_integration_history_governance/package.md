# Integration and history preservation governance

**Status**: Open — implemented and enforced; final validation and observation pending
**Started**: 2026-11-16 20:48 UTC
**Timezone**: UTC

## Overview

Prevent accepted work from disappearing between local review, integration, and
release. A November 15 rebase omitted 20 reviewed Rust-parser commits while
producing a valid fast-forward push from an older remote master. Local acceptance
and issue closure had not established remote integration. This package connects
those states with verifiable evidence and preserves unrelated work during Git
operations.

The operator requested execution on 2026-11-16. Recommended D1–D5 defaults are
adopted in `docs/standards/integration-history-governance.md`; implementation,
canary and remote configuration are authorized.
No production deployment is part of this package.

## Objectives

- Prove remote integration before claiming work is integrated or closing its
  integration obligation; distinguish local acceptance from remote integration.
- Prevent routine rewriting of shared master and loss of unrelated local work.
- Isolate concurrent tasks without silently overriding the current branch policy.
- Enforce reviewed integration and required checks at the remote boundary.
- Detect removal of accepted security behavior even when commit ancestry survives.

## Scope

Included: canonical integration policy, acceptance receipts, local Git safeguards,
concurrency/worktree conventions, GitHub rule configuration proposal and rollout,
security baseline CI/release wiring, failure-injection tests, and operator recovery.
Initial baseline enrollment is shape-converter; inventory other consumers without
claiming a repository-wide security certification.

Excluded: redesigning the parser, replaying historical reviews, rewriting old
work packages, changing production runtime permissions, deploying images,
creating new hosted services, and automatically closing or messaging GitHub issues.

## Complexity Budget

Reuse Git, Python standard library, existing wctl tests, GitHub Actions and repository
rules available to this account. Permit small verifier commands, test fixtures,
a versioned receipt format, and existing-workflow changes. Start with remote
receipt verification and a shared-master preservation policy. No new daemon,
database, queue, bot credential, dependency, or service is budgeted. Before
escalation retain a real failing acceptance test and the smallest required change.
Hooks are defense in depth; they are not a server-enforced security boundary.

## Implemented Deliverables

1. `docs/standards/integration-history-governance.md`: durable state definitions,
   Git mutation rules, receipt requirements, exception and recovery procedures.
2. A small verifier under `tools/` with real Git tests under `tests/tools/`:
   remote observation, accepted revision, integration result, and explicit failures.
3. Work-package closure template and root agent guidance referencing the standard.
4. An exact GitHub protection/rules proposal, baseline export, capability check,
   canary evidence, and applied-settings readback under the execution authorization.
5. An always-reported security-baseline check in canonical workflow sources,
   generated workflow validation, and release/publication consumer coverage.

## Adopted Control Decisions

| ID | Decision | Proposed default | Tradeoff to resolve |
|---|---|---|---|
| D1 | Integration and merge method | Preserve accepted commits through merge commits; no routine shared-master rebase/reset | Squash/rebase requires a separately reviewed mapping from accepted source to integrated tree; ancestry alone cannot validate it |
| D2 | Concurrent task isolation | Separate worktrees/task branches, one integrator, serialized validation on the existing stack | Root instructions now authorize scoped task branches for authorized work; shared refs and stack validation still require one integrator |
| D3 | Remote protection and approval | Required checks; prevent force-push/deletion; defined exceptional bypass | PR association and both exact-head checks enforced for administrators; zero human approvals until an independent reviewer is assigned |
| D4 | Security baseline trust | Required baseline validation on every candidate, owned policy changes explicitly reviewed | Candidate-controlled checks can weaken themselves; determine trusted policy source and minimum workable ownership protection |
| D5 | Closure and publication | Local acceptance, remote integration, and deployment are distinct states; durable remote receipt before integrated closure | Store receipts after their subject commit; avoid self-referential hashes; define retention/issue authority and publication eligibility |

These defaults were adopted by the execution request; human approval count starts
at zero until an independent reviewer is assigned. Reviewer findings and final
recommendations belong in `artifacts/review_synthesis.md`.

## Success Criteria

- [x] Reproduce the dropped-local-history/valid-remote-fast-forward incident in
  disposable Git repositories and show the selected controls prevent false closure.
- [x] A locally accepted but unpushed revision cannot yield an integration receipt.
- [x] Routine updates preserve preexisting accepted commits and working changes;
  divergent/shared branches fail with actionable recovery instructions.
- [x] Verify the exact host/container checkout actually tested; a worktree shell
  location alone cannot establish validation identity.
- [x] Supported merge modes, stale refs, shallow history, offline operation,
  concurrent remote movement, missing checks, and bypass are tested explicitly.
- [x] A later revert that retains ancestry but removes the Rust parser fails the
  behavioral security baseline unless retirement is explicitly approved.
- [x] Exact remote rules and required checks are verified in the intended account;
  ordinary authorized contribution and emergency recovery remain possible.
- [x] Publication/deployment consumers use exact candidate evidence, and a
  documentation-only local success cannot authorize release.
- [x] Independent correctness, QA, and security reviews close all medium/high
  findings before package closure; retained evidence supports each status claim.

## Security Impact and Review Gate

**Security impact**: high. This package changes agent Git workflows, CI trust,
repository write restrictions, and release eligibility. Dedicated design review:
[security review](artifacts/security_review.md). Independent correctness review:
[correctness review](artifacts/correctness_review.md). Both require implementation
re-review; design findings cannot establish implemented or enforced status.
Decision owner: repository operator. Implementer: assigned agent/maintainer.

## Generated Artifact Validation Gate

Applicable: integration receipts, generated workflows, rule exports and release
attestations are consumed artifacts. Trace approved source revision through the
fresh remote object, receipt writer, receipt reader, exact CI candidate, and release
consumer. Use real local bare remotes for Git boundaries and read back GitHub
settings/check results for environmental enforcement. Retain receipt contents and
identities, not merely successful exit codes. Current claim: implemented and environment validated for integration controls;
full regression and operational observation remain open.

## Failure-Class Assessment and Hardening

See [incident and consumer inventory](artifacts/incident_and_consumers.md).
The broken assumption is that accepted local state is durable remote integration.
Related evidence: [Rust history recovery](../20261113_shape_converter_security_conformance/artifacts/20261116_history_recovery.md).
Reuse `docs/standards/hardening-lifecycle-standard.md` and
`docs/standards/generated-artifact-validation-standard.md`.

Health signals: accepted work remains reachable, false integration claims fail,
checks always report, and routine contributions complete without bypass.
Danger signals: mandatory bypass for normal work, stale receipts, mutable policy
self-approval, orphaned worktrees, and publication before checks finish.
Adopted observation window: first five real protected integrations plus one recovery
drill. PR #661 is the first real protected integration; bootstrap and disposable
canaries do not count. No temporary bypass is installed. Future temporary
mitigations require an owner and retirement test.

## Dependencies and Validation

Read root `AGENTS.md`, work-package and workflow instructions before implementation.
Resolve D1–D5, inventory account capabilities and existing publishing triggers,
and preserve all existing WIP. No scientific parameterization changes are
proposed; a parameterization ADR is not applicable.

Scaffold validation is Markdown lint and link readback. Implementation validation
must use real Git boundary tests through wctl, generated-workflow checks, applicable
regression gates, and remote enforcement readback. Follow repository-required
pre-handoff tests when code changes; a docs-only scaffold does not run application
suites. See the [ExecPlan](prompts/active/implementation_execplan.md).

## Execution Status

Bootstrap PR #657 and protected follow-up PR #661 are merged. Remote protection
and merge settings are read back; local guard and wctl shim are installed in this
checkout. See the [execution receipt](artifacts/20261116_execution.md). No production
deployment occurred. Full repository regression and the five-integration
observation window remain open; this package is not closed.
