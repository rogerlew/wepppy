# Deploy execution test refactor

Deployment maintainers exercise the production shell entry point with local command doubles. Extract the doubles and subprocess harness so maintainers can inspect the shell directly and continue selecting every scenario by its existing pytest ID.

The complexity budget covers test fixtures, a Python harness, and package records. Security impact is low because the test command search path simulates deployment tools. Verify the installed doubles against their original bytes and run the existing execution scenarios. Production deployment and dependency files are outside scope.

Acceptance requires preserved test definitions and passing scoped execution tests. Integration is local to master per operator direction.

## Outcome

Closed locally on 2026-11-23 UTC. All 75 scoped cases passed before and after extraction. See the [validation tracker](tracker.md) and [completed ExecPlan](prompts/completed/implementation_execplan.md).
