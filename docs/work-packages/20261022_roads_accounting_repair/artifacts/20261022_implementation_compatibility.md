# Implementation compatibility and regression plan

Contract ancestor: `83f7410e8`. Native APIs are additive. The original totalwat
entry point and raw WAT remain unchanged; the new producer emits a separate
marked accounting WAT with existing field names and canonical target IDs.
A versioned Roads ledger records source-relative paths/hashes, native topology,
represented area, product-specific scales, and canonical PASS receipts. Corrected
report selection requires this lineage and never silently falls back to raw WAT.
Historical results without a ledger remain historical. No baseline files change.

Validate native zero-road parity, multiple independent outlets, literal Q versus
physical Q, optional support areas, invalid sources and atomic paired publication.
Validate orchestration reconstructs PASS before watershed execution, then inspect
actual prepared PASS, routed output and reports on isolated UM1. Validate report
cache content hashes at equal timestamps and baseline isolation. Complete focused
and full repository gates and independent correctness/security review before
claiming completion. No new dependency or queue edge is introduced.
