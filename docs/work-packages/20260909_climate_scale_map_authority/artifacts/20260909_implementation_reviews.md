# Climate scale-map implementation reviews

## Independent correctness review

Reviewer: `climate_map_contract_correctness` (`reviewer`), 2026-09-09.
Production property/parser/template changes approved without material findings.
Repair P2: repeated repair rewrote correct records. Resolved with fresh hydration
under an explicit lock, equality check, and dump only when changed; the `finally`
block releases the lock. Reviewer rechecked and approved the revised script.
Confirmed production RQ 1.16.2 uses plain started-registry IDs; the repair asserts
that version and reads raw IDs without invoking registry cleanup.

## Independent QA review

Reviewer: `climate_map_qa` (`qa_reviewer`), 2026-09-09.
Both P2 findings resolved and rechecked: add `fork-archive` to repair job guards;
remove undeclared Node/jsdom dependency from pytest. Python tests verify rendered
HTML and Jest tests exercise actual WCForms serialization. Added catalog test
markers and repair no-op. No remaining blocking implementation findings.
The real raster-to-climate-to-WEPP propagation acceptance evidence is recorded
separately in `20260909_live_evidence.md`; reviewers did not run production writes.

## Worker replay follow-up

Correctness review identified a missing real-parser replay regression. Added
`test_rq_payload_replay_cannot_replace_configured_scale_map`: actual
`build_climate_rq`, serialized poisoned job metadata, real Climate/config/parser,
NoDb persistence/cache clearing and reload; only generation and external RQ/run
lookup plumbing are stubbed. It verifies both configured and stored maps at
build entry and afterward while leaving the poison in job metadata. The focused
test passed, and the reviewer rechecked and approved coverage closure. Matching
worker activation remains necessary; a web-only refresh is insufficient.
