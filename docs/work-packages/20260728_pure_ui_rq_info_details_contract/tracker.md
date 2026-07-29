# Tracker - SURF-17 Pure UI RQ Info Details Contract

## Status

Active 2026-07-28 UTC. Contract checkpoint reviewed and ready to commit.

## Progress

- [x] Registered SURF-17 after verified SURF-09.
- [x] Recorded the operator-approved active-job queue-separation delta.
- [x] Complete two independent read-only contract reviews.
- [ ] Commit the standalone checkpoint ancestor.
- [ ] Add direct render and route evidence.
- [ ] Apply only the ratified queue-separation change and confirmed conformance
  repairs.
- [ ] Complete security review, focused and broad validation, parent
  reconciliation, package commit, and clean closeout.

## Decisions

- Preserve the existing Admin/Root authorization and static read-only snapshot.
- Group active jobs server-side and render panels in requested queue order.
- Keep recently completed and failed tables combined.
- Treat unrequested or unknown queue values as unassigned rather than placing
  them in another queue panel.

## Checkpoint

Starting implementation revision:
`bbba58359b4f45d88eab610c27cd467bb5964a3b`.

The standalone contract checkpoint revision is pending.
