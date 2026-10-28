# Default-worker routing security review, 2026-10-28

Reviewer: independent `queue_contract_security` agent (`security_reviewer` role).
Contract checkpoint: `0e6302905`; runtime edits followed that ancestor.
Disposition: **PASS, no blocking findings** for contract and implementation.

The review examined default admission/execution routing, queue-bound worker
capability, retained ledger and pause keys, dual-queue bootstrap, legacy manifest
readback, resume/receipt rejection and manifest-selected historical observation.
No new authentication, privilege, filesystem or public API authority was found.
Old outstanding/uncertain jobs retain capacity; queue migration does not reset
budgets or erase evidence. Default ordinary backlog still defers new maintenance.

Nonblocking recommendation: execute a retained legacy job through a default
worker and prove rejection before publication or receipt acknowledgment without
claiming old authority. Disposition: added the parameterized
`test_default_worker_rejects_legacy_execution_authority` for old configuration
and wrong origin. Both passed in the parent's real-Redis 129-test run.

The reviewer's independent selected invocation skipped 12 tests because its
container lacked redis-server and no socket was supplied. It is not runtime
passing evidence. Parent-run tests used a disposable Unix-socket Redis instance;
[validation](20261028_default_queue_validation.md) records that evidence and
separate normal-forking-worker artifact/job-tree acceptance.

Production deployment, live fleet/mount parity and ordinary-job delay acceptance
remain outside this local review. The seven-job cap does not establish latency
or fleet capacity. General production enablement is not authorized here.
