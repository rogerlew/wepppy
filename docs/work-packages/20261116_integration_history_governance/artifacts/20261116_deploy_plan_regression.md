# Deployment plan continuation regression repair

## Diagnosis

The continuation suite reported seven failures in
`tests/scripts/test_deploy_production_plan.py`. Their common error was
`unexpected wctl call: show-compose-files`. The plan fixture did not model the
read-only installed-preset query restored with the Rust-parser release contract.
Those failures occurred before the governance gate; the gate already follows the
successful `--print-plan` exit and did not need to move or gain a bypass.

The fixture now returns the appropriate production, worker, or wepp3 preset and
permits only preset/configuration reads plus the real Compose contract parser.
Unexpected Git, Docker, GitHub, HTTP, other Python, or non-query wctl invocations
set a forbidden-action sentinel. Every plan test checks that sentinel, including
negative configuration tests, so an unrelated side effect cannot masquerade as
an expected validation failure.

## Confirmed production correction

Extending valid-state coverage to the dedicated wepp3 plan found a real boundary
error: `validate_deploy_topology` launched its secret-readability probe through
`docker compose run` even for `--print-plan`. The new test failed with that exact
command recorded; the other ten plan cases passed after fixture repair. Evidence:
`/tmp/governance-plan-red.log` (1 failed, 10 passed).

The one-condition production change runs that probe only when `PRINT_PLAN=false`.
Actual wepp3 deployment still requires the existing secret-readability check.
Execution coverage verifies governance success precedes the secret probe, which
precedes build, suspension, stop, and activation. Injected governance failure is
covered for full-stack and wepp3 modes and must reach none of those operations.
No production operation or external mutation was executed during these tests;
service commands use the existing disposable fake-executable harness.

## Validation and review

Scoped plan/execution validation passed: **77 passed** in 105.37 seconds,
recorded in `/tmp/governance-deploy-plan-execution-tests.log`. After adding the
explicit secret-probe absence assertion, the final failure-boundary rerun passed:
**2 passed** in 9.47 seconds, recorded in
`/tmp/governance-deploy-governance-boundary-tests.log`.
Shell syntax and Git whitespace checks pass. This repair does not claim to fix
other continuation failures or replace the package-wide validation record.

Implementation author: delegated `ci_security` agent. Independent static review:
`history_controls` agent accepted the minimal production condition and requested
an explicit assertion that governance failure cannot reach the secret probe;
that assertion was added. Root integrator owns commit, exact-source policy
approval, and integration. No deployment authorization is implied.
