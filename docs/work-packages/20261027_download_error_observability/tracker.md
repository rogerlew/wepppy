# Tracker

2026-10-27 UTC: implementation, focused validation and independent correctness,
security and QA review complete. Broad assessment complete; source publication is authorized, with one unrelated Roads provenance case blocked.
Deployment remains separate.

Baseline: bare server 500 / client continuation to empty success. Current bounded
signal: real lazy Flask missing-secret failure reaches the bootstrap terminal
with setting, recovery instruction, code and matching log ID; real native aria
and batch transfers preserve bytes and nonzero failures.

Validation: 190 focused server passes; Linux 12 passes/two Windows-only skips;
Windows 14 passes including actual batch/aria successful and failed transfers.
See [validation](artifacts/validation.md) and
[coverage matrix](artifacts/failure_class_matrix.md).

Decisions: typed safe server configuration failures, correlated unknown failures,
shared Python diagnostics using the existing prerequisite, original transfer
concurrency/resume and CLI arguments retained. No arbitrary traceback publication,
new service, broad retry wrapper or manifest-origin restriction. Both client
stages (manifest and payload) have retained regression coverage.

Independent findings: COR-01 through COR-06, SEC-01/02 and QA-01/02 closed.
Initial full-suite attempt invalidated by implementation edits during collection;
segmented coverage is retained in validation.md. The unrelated Roads working-tree hash drift is preserved rather than waived or repaired here. No production smoke is
claimed for an uninstalled revision. Operator owns the separate deployment and
ordinary-user smoke; recurrence reopens the bounded assessment.
