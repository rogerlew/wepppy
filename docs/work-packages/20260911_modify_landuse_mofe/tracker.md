# Tracker

## Progress

- Production read-only assessment confirmed hillslope/OFE mismatch on wepp1.
- Drafted selected-hillslope contract; operator's requested outcome recorded.
- Two independent contract reviews approved after state/failure-policy clarification.
- Contract and package documentation lint passed.
- Standalone contract ancestor committed as `134a3a9af`.
- Implementation and focused regression tests complete. A disposable synced run was exercised with real NoDb locking, process-pool MOFE synthesis, parquet summary persistence, reload, and restoration of the original selection. Archive/browser/downstream checks remain pending before deployment.

Runtime evidence: on 2026-09-11 22:50 UTC, Topaz 1433 changed 90 -> 424;
`domlc_mofe_d` changed to `{'1': '424'}`, the regenerated file was written, and
summary class 424 reported 0.3125 area / 0.0172867% coverage. At 22:51 UTC the
selection was restored 424 -> 90; final counts returned to 434 hillslopes class
424, 21 class 90, 1,052 OFE segments class 90, and 13 class 70.

## Decisions and compatibility plan

Preserve schemas and OFE geometry. Apply selected classes to existing OFEs using
the existing builder's explicit-assignment override, preserving configured buffer
behavior. Verify summary area and actual management contents, then propagation
into disposable WEPP preparation. Do not mutate or deploy to production.

## Findings

`Landuse.modify` updates only `domlc_d`. `build_managements` computes MOFE area
from `domlc_mofe_d` and does not synthesize MOFE files. `_build_multiple_ofe`
already accepts `domlc_mofe_override`; inspect its buffer and disturbance behavior
before reuse. The supplied RQ job changed 71 to 90 and was not the thinning edit.
