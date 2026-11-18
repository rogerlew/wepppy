# Isolated-worktree validation tracker

Status: Complete locally, 2026-11-18 UTC. No remote integration or deployment.

- [x] Trace the Roads failures to worktree/environment prerequisites.
- [x] Add canonical one-off runner and aggregated runtime preflight.
- [x] Validate negative prerequisites, source/runtime identity and positive isolated execution.
- [x] Finish durable guidance, self-reviews and retained evidence.

The new command runs on the candidate using the installed Compose preset. Existing
shared commands retain their behavior and now direct mismatched-checkout users to
the supported worktree runner. The profile fixture includes real account template
helpers; all 49 tests pass. No assertion or timing threshold was weakened.

Broad preflight correctly identifies seven absent user columns and runs no tests.
It does not migrate shared databases. The remaining integration prerequisite is
provisioning a compatible isolated database through its owning migration workflow;
load-sensitive catalog latency remains outside this tooling change.

See [validation](artifacts/validation.md), [correctness review](artifacts/correctness_review.md),
[security review](artifacts/security_review.md) and the
[ExecPlan](prompts/completed/implementation_execplan.md). The durable operator contract
is [worktree testing](../../../tools/wctl2/docs/worktree-tests.md).
