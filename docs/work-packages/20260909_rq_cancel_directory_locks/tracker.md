# RQ cancellation directory-lock cleanup tracker

## Status

2026-09-10 UTC: Investigated cancellation and RQ worker shutdown.
Active plan: prompts/active/rq_cancel_directory_locks_execplan.md.
Starting revision: 028413e5ce2e33a6bceb6785f8f365db8410a223.

## Progress

- [x] Record operator authorization of cancellation cleanup.
- [x] Inspect cancellation, lock payloads, and installed RQ supervisor.
- [x] Prepare canonical amendments and contract decision.
- [x] Complete two independent contract reviews and disposition; all findings closed.
- [ ] Obtain authority for standalone checkpoint commit; record revision here.
- [ ] Implement and verify real Redis/process-boundary regression.
- [ ] Complete correctness/security/QA reviews and required gates.

## Decisions

Cleanup must follow writer termination and match execution ownership plus lock
token. Sending a stop command alone is not termination evidence. Queued
cancellation must not clear another job's run locks. Keep legacy recovery explicit.

## Handoff

No implementation edits or production mutations. The repository's contract-first
standard requires a standalone ancestor commit before implementation; commit
authority was granted by the operator ("yes") on 2026-09-10 UTC.
