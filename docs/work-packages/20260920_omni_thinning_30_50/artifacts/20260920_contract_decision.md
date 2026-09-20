# Contract decision: OMNI-THIN-30-50

Recorded 2026-09-20 19:32 UTC; base b72fd53f635c7a03b3b66fcf891f796e02fe33e5.
Classification: intended bounded enhancement, not conformance repair.
Operator authorization: “okay. this is probably safer. scaffold and execute as
work-package please” after accepting eight additional variants, preservation of
legacy assets, and 40% default. Execution includes required local checkpoint
commit; no push/deployment authorized.

## Authority and exact delta

New `docs/ui-docs/contracts/omni-thinning-contract.md` and ADR-0071 own this
finite option/asset addition. Existing controller, NoDb persistence and MOFE
artifact contracts apply unchanged; no conflict or change to their behavior.
Source boundary: omni.js select/default, eight new .man assets, additive records
in the five thinning catalogs and associated CSV mirror. Existing treatments
UI may expose the added catalog entries through its current data-driven behavior.
No route, queue, worker, auth, soil or saved-state mutation. Security impact none.

## Compatibility and evidence

Preserve all legacy records and files; no schema migration. Review never-used,
empty, populated, legacy and invalid state behavior as canonical contract states.
Regression evidence: select default/hydration/serialization, map completeness and
collision checks, real parser/writer numerical parity and generated/prepared
MOFE readback. Full local gates plus independent final correctness review.
Local fixture/input claim only; deployment and live model results are separate.

## Reviews

Two independent read-only reviews approved; see 20260920_contract_reviews.md.
Medium archive-evidence finding resolved and confirmed before checkpoint.
