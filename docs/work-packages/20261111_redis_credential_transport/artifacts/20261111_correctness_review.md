# Correctness review - Redis credential transport hardening

**Status**: Pending implementation and independent review
**Reviewer**: Unassigned
**Date opened**: 2026-11-11 UTC

## Required Valid States

Review each established logical DB and consumer: Redis lock/default, status DB
2, RQ DB 9, sessions/stream sessions DB 11, NoDb cache DB 13, README DB 14 and
log-level DB 15 where affected. Preserve credential-free local test fixtures only
where their explicit contract permits them.

## Review Checks

- [ ] Endpoint parsing preserves host, port, IPv6, TLS/query options and DB.
- [ ] Mounted-file precedence and legacy conflicts match the ratified matrix.
- [ ] Sync, async, session, RQ, status, preflight and streamauth use the intended
      DB and preserve timeouts/retries.
- [ ] Missing/wrong credentials fail explicitly without unauthenticated fallback.
- [ ] RQ queue names, counts, worker class, startup delay and registration remain
      unchanged.
- [ ] Redis restart, health and rollback do not flush or corrupt data.
- [ ] Focused tests exercise real AUTH rather than only mocks/miniredis.
- [ ] No full-suite success is required or claimed.

## Findings and Verdict

Populate findings with severity, exact evidence and disposition. **Gate status:
PENDING/FAIL** until direct scoped runtime evidence and review are complete.
