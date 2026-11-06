# Production cutover tracker

Status: executing. Last updated: 2026-11-06 UTC.

## Progress

- [x] Operator authorized package and production deployment, including `2111d0eb2`.
- [x] Published candidate/native hashes and current fleet baseline inspected.
- [x] wepp1 cleanup completed: 215 GB free, tagged rollback images preserved.
- [x] Package/checkpoint and independent preflight review.
- [ ] Scheduler queue correction, regressions and published candidate.
- [ ] Production state backup/rehearsal and coordinated migration/deployment.
- [ ] Notification activation and actual scheduled/browser acceptance.
- [ ] Default-worker pilot and monitored general catalog activation.
- [ ] Final reviews, cleanup and closure.

## Decisions

Keep all earlier safeguards and GC pause. The user's last config-default commit
is release authority, not an invitation to rewrite existing project selections.
Keep notification population on batch and catalog maintenance on default. Use
wctl merged environment files; no new Compose mapping is necessary. Preserve old
catalog ledger/pause/history during queue migration. No Redis flush or image/volume
prune during deployment. No 1.x workers may attach after 2.x writes.

## Current findings

Scheduler YAML corrected to default; actual-config integration failed before
and passed after the correction. Focused tests: 186 passed; deployment tests:
72 passed; RQ graph current. Broad suite running. wepp2
batch workers retired; only stalled pool processes remain. Canonical recreation
must restore real registrations. Independent review requires all old producers
and five worker containers stopped before first 2.x writes; normal traffic may
reopen on exclusively-2.x wepp1 while remote deployments continue.
Production schema is e7a1c9d204bf, pending additive f6b8d27a901c. Production pins
also change FastAPI/narwhals/pkginfo/dateutil relative to actual installed baseline.
The old dashboard 502 and legacy archive read-only placement are retained existing
limitations, not authority for new services or mount changes.

## Evidence and next action

Readiness assessment is under notes/. Original production inspection and cleanup
logs are retained under /tmp on forest; copy sanitized summaries to artifacts and
private operational backups to mode-0700 host directories. Complete independent
review and exact rollback/control commands before irreversible cutover.
