# Tracker

## Progress

- Production read-only assessment confirmed hillslope/OFE mismatch on wepp1.
- Drafted selected-hillslope contract; operator's requested outcome recorded.
- Two independent contract reviews approved after state/failure-policy clarification.
- Contract and package documentation lint passed.
- Standalone contract ancestor commit requires commit authority; no implementation edits.
- Implementation, tests, generated-artifact validation, and correctness review pending.

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
