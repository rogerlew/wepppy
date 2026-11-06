# ESDAC missing-data tracker

## Status

Started 2026-11-06 UTC. Phase: closed local implementation and study. Completed plan: [implementation_execplan.md](prompts/completed/implementation_execplan.md). Security impact: none; independent correctness review required.

## Progress

- [x] Production diagnosis and original report retained.
- [x] Package scaffold and 1,000-location study scope established.
- [x] Contract/ADR, metadata repair and regression matrix.
- [x] Incident and availability generated-artifact evidence.
- [x] Focused/broad validation and independent review.

## Decisions

2026-11-06 UTC: Operator authorizes robust building when physical information suffices; metadata absence must not cause rejection. Preserve physical gates and existing numerical formulas. Retain geographic study failures rather than filtering them out.

## Risks and remaining work

Production is unchanged. Deployment and affected-run recovery require separate operational execution. Study can reveal additional physical insufficiencies; classify evidence before any escalation.

## Progress — 2026-11-06 UTC

Incident replay revealed a second confirmed defect: legacy soil keys collide and timestamp bytes rejected identical soils. Added content disambiguation and equivalent-file retry; all 35 incident soils now build, with two unique base artifacts and 35 accepted disturbed conversions. Independent review also required preserving partial forest metadata and historical comment order. Final targeted checks and paired baseline/candidate 1,000-location builds are running. Preliminary study v1 is excluded from release evidence because files changed during execution; final study binds consumed source hashes.

## Final evidence checkpoint — 2026-11-06 18:24 UTC

Final paired study: 733/1,000 accepted (136 valid, 597 degraded), 267 rejected,
287 recovered, zero regressions and exact physical parity for all 446 previous
successes. All 76 single-material successes preserve the mapped soil boundary
and the 200 mm material split. Final source hashes stayed unchanged throughout.
Incident replay: 35/35 accepted, two unique base soils, 35 downstream readbacks,
and byte-identical retries. Focused tests: 122 passed plus one final real-writer
collision regression. Native disturbed matrix: 99 passed. Remaining broad-suite
partition was still running at this checkpoint; its final disposition is recorded below. Independent review passes with no medium/high finding.

## Closure — 2026-11-06 UTC

All package milestones are complete. Broad partitions: 13,289 distinct passed,
424 skipped, one pre-existing Runs-template mismatch; isolated reproduction and
unchanged-HEAD evidence retained. Remaining 66 tests pass; 123 focused tests pass.
See `artifacts/validation.md` for exact commands/disposition. No production deploy
or original-run mutation occurred. The completed plan is archived; durable field,
identity and consumed-horizon policy is in `docs/schemas/esdac-soil-source-contract.md`.
