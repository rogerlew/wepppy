# Independent forest contract reviews

2026-11-18 UTC. Read-only reviewer and security_reviewer independently examined
canonical contract, ADR-0145 and checkpoint before executable client/NoDb edits.

- Correctness: classify all network deadline exhaustion, including headers/body and
  aggregate budget, as availability. Accepted in canonical contract.
- Correctness: translate selection-persistence faults to SoilDataSourceError so
  candidate fallback cannot swallow OSError/ValueError. Accepted with fault tests.
- Correctness: freeze event version/outcome/reason enums. Accepted.
- Security: actual_supplier is cache/transport binding, not proof of unknown legacy
  row origin. Accepted: historical_rows_unknown is retained in selection evidence.
- Security: validate selection schema/events and invalidate latest evidence before
  attempts; require both persistence boundaries before returning a collection.
  Accepted with SQLite/filesystem fault coverage.
- Security implementation checks: TLS failures before OSError, distinct DNS-child
  failure classification, UTF-16 DTD/entity rejection, and multiple primaries sharing
  a valid SDA cache without misbinding. Included in implementation/tests.

No high findings or objection to operator-approved geographic/live parity deferral.
Final implementation review will verify closure against executable evidence.

## Implementation closure

Independent read-only correctness and security reviewers examined the executable
client, NoDb, importer, credentials/readiness and dev Compose changes.

- Reject unexpected XML envelopes while allowing legitimate empty NewDataSet.
  Real TLS Error-envelope regression passes and writes no fetch/negative evidence.
- Resolve explicit configuration before deployment defaults when hydrating older
  projects without saved identity. Real Redis XML/JSON reload regressions pass.
- Read cache evidence before assigning success. Injected SQLite read failure now
  records structured failure and closes the connection.
- Remove serving credentials from psql command arguments; initializer uses environment
  import. File secrets are readable only by owner and the named container UID.
- Compare selection history's unknown-origin flag against its immutable binding.
- Distinguish new persisted defaults from existing unconfigured resolved defaults
  in the operator guide. Include latest selection evidence in selected-cache clearing.

Reviewers independently reproduced XML/evidence-read closure and found no remaining
blocking correctness or medium/high security findings. Qualification uses isolated
Redis/queue, actual UID/GID and /wc1 mounts; no shared client activation is implied.
