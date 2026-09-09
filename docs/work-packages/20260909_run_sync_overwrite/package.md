# Run sync overwrite

Status: implemented locally and tested; live workflow validation pending.

Scope: worker cleanup and fresh replacement of manifest-listed files, with real
filesystem and downloader regression coverage. Source service, queue wiring,
UI and authentication are excluded. Security impact: low; filesystem deletions
require explicit containment checks and hostile/valid-state tests.

Trigger: stale `climate.log.aria2` length mismatch in sync job
`13783040-6204-4ad7-a699-1be9ea698923` on Forest. Prior diagnostic work is recorded
in [the diagnostic note](../../dev-notes/run-sync-failure-diagnostics.md).

Authority: [run sync contract](../../schemas/run-sync-contract.md).
Health signal: a repeat pull refreshes changed listed files without stale-resume
failure. Danger signals: unlisted deletions, escaped paths, false success, or
repeat length mismatch. Observation is recurrence-triggered; any such incident
requires reassessment in a new package. No temporary mitigation is introduced.
Rollback before rollout is reverting the worker patch; deleted partial progress
is not recoverable. Owner: implementing operator. Close only after focused,
full-suite, independent correctness/QA and real workflow evidence is recorded.
