# F5 prerequisite checkpoint

**Status: PASS — F5 implementation may begin.**
**Date:** 2026-11-11 UTC.
**Accepted implementation:** `db7ef7cb7e1d05400b6acca333526dfe80c7b417`.
**Standalone contract ancestor:** `ca1034a2b2a46ed91984220f2596ec9687ca93fc`.

Correctness, QA, security and operations independently approved the candidate.
All medium/high review findings are closed. Final exact-image and client
receipts are retained in `20261111_final-candidate.json`; negative startup,
dashboard and nonsecret Redis configuration receipts accompany it. See
`20261111_scoped_validation.md` for commands, identity/mount parity, test results,
failed attempts and limits. Later closeout changes contain documentation and
validation artifacts only; the accepted production source remains the candidate.

255 focused Python tests passed; one Docker-in-container render case was skipped
and covered by seven host renders. Go integration and real AUTH tests passed.
The isolated canonical Compose workflow authenticated all expected DBs, round-
tripped/expired Flask sessions, registered six workers and executed a harmless
job returning 42, served Go/dashboard health, rejected wrong/missing credentials,
and passed credential-free argv/config/log scans. Redis restart and baseline
rollback/candidate restore retained data; recovery explicitly restarted affected
consumers. No full pytest or npm gate was run, per the operator's scoped waiver.
F5 retains its own full Python/frontend gates.

This is a code-delivery and isolated-environment checkpoint, not production
rollout approval. The Go test wrapper incidentally recreated shared dev Redis;
current AUTH, 11 worker TTLs and Go health pass, but prior job continuity cannot
be established. That event is documented in `20261111_operations_review.md`.
Dormant standalone dashboard and remote production/TLS acceptance limits remain
explicit in the consumer matrix and validation receipt. No password was rotated,
no existing Redis volume was deleted, and no live DB was flushed.

Durable behavior and rationale are in
[Redis credential transport contract](../../../schemas/redis-credential-transport-contract.md),
especially Resolution and compatibility, Native clients and diagnostics,
Workers and dashboard, Server and CLI, and Acceptance and recovery.
