# Final transport and Forest1 review addendum

## Scope

Four independent reviewers reassessed revision `e11985f02` after the real
Forest `wctl` boundary exposed shell stripping of single quotes inside the
transported Python/Lua payload. The review also considered the completed
Forest1 forward, rollback, targeted-isolation, and DEVAL evidence.

## Disposition

| Discipline | Result | Critical | High |
|---|---:|---:|---:|
| Correctness | PASS | 0 | 0 |
| Operations | PASS | 0 | 0 |
| QA | PASS | 0 | 0 |
| Security | PASS | 0 | 0 |

Correctness verified that Lua long-bracket literals survive Bash, `wctl`, the
Python `-c` boundary, and Redis Lua 5.1 without changing KEYS/ARGV mappings or
atomic semantics. Security confirmed the literals are static and add no
interpolation or injection path. QA confirmed the updated regression assertions
fail against the old quoted source and pass against the repair; the real
Forest acquisition/resume supplies the integration evidence a mock cannot.

Operations initially held the gate for exact-final-revision rescue evidence.
That High was closed by the contained CAP candidate failure at `e11985f02`:
nonzero deploy result, no success footer, known-good rescue restoration,
functional and public health, unchanged non-selected identities, clean RQ
state, and an immediate successful retry. Operations then returned PASS.

Validation available to reviewers included 36 passing script tests, shell
syntax and diff checks, two exact full Forest deployments, two token-bound
Redis resume receipts, targeted identity isolation, stale-renderer rejection,
and the successful RQ-driven DEVAL publication.

The remaining production hold is the explicit operator-controlled browser UX
gate, not a Critical/High implementation or recovery finding.
