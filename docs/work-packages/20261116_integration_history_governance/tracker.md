# Tracker — Integration and history preservation governance

## Quick Status

**Timezone**: UTC
**Started**: 2026-11-16 20:48 UTC
**Phase**: Implemented and enforced; operational observation open
**Security impact**: high
**Remote implementation**: bootstrap PR #657; protected follow-up PR #661
**Next milestone**: Observe five real protected integrations; retain baseline regression failures

## Task Board

- [x] Capture incident evidence, scaffold, and independent design reviews.
- [x] Adopt D1–D5 defaults and promote the canonical governance standard.
- [x] Implement fresh remote receipts and a durable protected-ref hook; 37 real-Git cases pass.
- [x] Implement live checkout identity, including sparse trees; 66 initial and 16 final focused wctl cases pass.
- [x] Implement base-owned policy evaluation, exact-source behavior checks, and release gates.
- [x] Validate rejection of green-but-weakened policy and no-PR changes on disposable canaries.
- [x] Validate eligible PR-associated integration and read back protected master.
- [x] Merge the sparse correction through protected master and retain a fresh integration receipt.
- [x] Complete independent implementation reviews and close identified medium/high findings.
- [x] Clean up disposable canary rules, remote refs and clean worktrees, retaining evidence/local refs.
- [x] Record failed full/remainder attempts, baseline attribution and final changed-path validation.
- [x] Complete disposable recovery drill, including tracked/untracked WIP recovery and fresh receipt.
- [ ] Observe five real subsequent protected integrations; do not manufacture empty changes.
- [ ] Complete operational observation and package closure.

## Decisions Log

2026-11-16: the operator requested execution of the reviewed scaffold. Adopted
commit-preserving integration, task branches and one integrator, externally approved
policy transitions, two required checks, administrator enforcement, and zero required
human approvals until an independent human reviewer is assigned. No production
deployment is authorized.

Live GitHub behavior refines the enforcement description: a green PR head can be
fast-forwarded and is recorded as that PR's merge. A commit with no PR association
was separately rejected. The contract is PR-associated/check-gated integration,
not a guarantee that only the merge button/API can update a branch.

## Evidence and Remaining Risks

See [execution receipt](artifacts/20261116_execution.md),
[implementation correctness review](artifacts/20261116_implementation_correctness_review.md),
[implementation history review](artifacts/20261116_implementation_history_review.md),
and [implementation security review](artifacts/20261116_implementation_security_review.md).

Local hooks prevent accidents; they do not contain an actor who controls hooks.
GitHub owners can change protections, and same-app deliberate check forgery remains
outside the stated threat model. PR association with zero human approvals is not
independent human review. Other local installations must adopt the hook and updated
wctl shim; no production-host installation is claimed.

## Verification

- [x] Package and canonical Markdown lint, link readback, spelling preview and whitespace checks.
- [x] Generated workflow validation and relevant focused suites.
- [x] Real Rust valid-output, quota and malformed-input checks locally and on GitHub.
- [x] Real remote rejection/acceptance canaries and master settings readback.
- [x] Exact-source publication eligibility rejects stale approval before registry writes.
- [x] Full application attempts and final audit record; four preexisting RQ fixture failures remain.

## Hardening Signal Log

Baseline: 20 accepted local commits omitted while a remote fast-forward remained
valid. Recovery preceded this package. Current controls reject the reproduced
false-closure scenario and tested integration violations. First protected master
integration: PR #661. Bootstrap PR #657 and disposable canaries are not counted
as five real subsequent integrations.

The canary setup error that produced an empty-tree candidate was isolated and closed
without merging; trusted policy rejected it. It is retained as a setup failure, not
positive evidence. See the execution receipt for exact identity and recovery.

## Handoff

The implementation is wired and remotely enforced. Keep the package open for
operational observation; do not label future evidence complete or the failed broad
suites green. Coupled YAML/governance/web validation: 559 passed; deployment
plan/execution: 77 passed; history boundary: 37 passed.
Durable policy lives in `docs/standards/integration-history-governance.md`.
