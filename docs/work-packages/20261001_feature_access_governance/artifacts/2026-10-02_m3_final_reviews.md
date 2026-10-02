# Milestone 3 final independent reviews

Date: 2026-10-02 UTC. Runtime candidate: `23c2f27fe`.

Two independent reviewers inspected the final M3 identity, deployment and
private-resource boundaries. Neither reviewer edited production code.

## Correctness review

The reviewer found that the first explicit Browse and Query Engine
`depends_on` maps replaced the shared service anchor's Redis dependency. This
was a release-blocking startup-order finding because both services use Redis
for current-token revocation. Development, HPC and production Compose now list
Redis `service_started` and Postgres `service_healthy` for Browse, D-Tale and
Query Engine. A regression test parses all three definitions and asserts the
secrets, environment paths and both dependency conditions. Independent focused
verification passed 61 tests.

The reviewer required exact-candidate environment evidence rather than the
initial dirty-tree run. The implementation was checkpointed as `03fc3eae6`, the
services were recreated, and acceptance was repeated. That clean-process run
found the private D-Tale proxy redirect defect corrected in `23c2f27fe`.
Independent inspection confirmed the correction matches D-Tale's route quoting,
occurs after ticket and live-capability verification, and introduces no open
redirect. The independent redirect suite passed 10 tests.

The canonical Docker operator documentation now names Browse, D-Tale and Query
Engine as live account-database consumers and distinguishes Query Engine's WEPP
verification secret from its MCP secret. The retained harness restores the
audited membership and removes disposable fixtures even when browser execution
fails. No correctness finding remains open.

## Security review

The reviewer passed the numeric JWT subject binding, live account/group reads,
Redis revocation, private D-Tale capability and cookie checks, public-table
continuity, Query Engine registered-source boundary and external-access denial.
The Redis dependency replacement was also reported as a Low availability and
hardening finding, then independently confirmed closed.

Independent security regression passed 152 tests. Additional DuckDB probes
blocked `read_csv`, `read_json`, `ST_Read`, `glob`, and `ATTACH` while the
registered admitted relation remained readable. The post-review proxy redirect
change preserved signed-ticket, scope membership and current-capability checks;
the reviewer found no path injection, open redirect or authorization bypass and
independently passed the launch/cookie/location regression.

No High, Medium or Low security finding remains open. The reviewer recommends
M3 security acceptance. Existing symmetric JWT and account-database credential
blast radius remains an architectural property of services that must verify
tokens and current membership; this change added no new credential or trust
class.

## Closeout regression

After review, the complete repository suite exposed and then closed a
test-isolation defect: the signed-token test now replaces the Redis constructor
captured by `rq_engine.auth` at import time. This changes test wiring only. The
all-collection reproduction passed, followed by **10,246 tests passed, 126
skipped and 12 subtests passed** in 2,668.41 seconds (44:28).
