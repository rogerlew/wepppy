# Single-input soil format support

Implement operator-requested 2006, 2006.2 and 9002 uploads alongside 7778.
Status: **closed, 2026-09-26 (code/local acceptance)**. Security impact: high (expanded untrusted soil parsing); dedicated
security and separate correctness reviews required.

Authority: [SUDI-01/SUDI-02](../../schemas/single-user-defined-inputs-contract.md),
[ADR-0075](../../adrs/ADR-0075-single-user-defined-inputs.md).
Execution: [completed plan](prompts/completed/soil_formats_execplan.md).

Strict admission, source-version metadata, native parameter preservation, soil
help and compatible modifiers are implemented. Native execution passes through
32 OFEs; live uploads/RQ/preparation/download and 9002 archive/restore pass.
All 667 collected regression files are covered after a test-double correction.
Both independent final reviews pass with no unresolved findings.
See the [tracker](tracker.md) and [validation summary](artifacts/20260926_validation_summary.md).
Production deployment is separate and requires coordinated web/worker updates.
