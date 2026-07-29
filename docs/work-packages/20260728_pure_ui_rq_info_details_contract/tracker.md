# Tracker - SURF-17 Pure UI RQ Info Details Contract

## Status

Verified 2026-07-28 UTC.

## Progress

- [x] Registered SURF-17 after verified SURF-09.
- [x] Recorded the operator-approved active-job queue-separation delta.
- [x] Complete two independent read-only contract reviews.
- [x] Commit the standalone checkpoint ancestor.
- [x] Add direct render and route evidence.
- [x] Apply only the ratified queue-separation change and confirmed conformance
  repairs.
- [x] Complete security review, focused and broad validation, parent
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

The standalone contract checkpoint revision is `cf20ef0b0`.

## Outcomes

- Active jobs render in ordered, isolated panels for the requested queues;
  `default` precedes `batch` by default.
- Recently completed and failed jobs remain combined.
- Authorization, read-only listing, lookbacks, metadata columns, and protected
  navigation are retained.
- No production repair beyond the operator-approved queue presentation was
  required.

## Validation

- Focused Python: 134 passed.
- Full frontend: 93 suites, 687 tests passed; lint passed.
- Independent correctness and security reviews passed with no unresolved
  findings.
- Broad-exception enforcement and `git diff --check` passed.
- Broad Python reached 2,462 passes and 40 skips before the known unrelated
  GridMET `_FakeUnits.degC` fixture failure.
