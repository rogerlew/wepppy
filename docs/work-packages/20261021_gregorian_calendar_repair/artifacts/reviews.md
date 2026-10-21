# Review evidence

Primary correctness (`calendar_correctness`): source approved after null/slash
record guards, distinct compatibility digest, shared exact ASCII header format,
and non-leap day-366 cursor-preservation test. Independently ran 61 tests.

Secondary QA (`calendar_qa`), after primary approval: no remaining blocker. Legacy
fixture tests explicitly reject runtime use then exercise offline hydration;
compiled leap tests replace the removed legacy source-string assertion. Independent
61-reader-test and replacement leap-test passes. Nonblocking debt: invalid-date
messages could include offending tuple/ordinal; existing fixed `/tmp` fixture
naming can collide across concurrent suites; obsolete leap-warning FORMAT labels
remain. Generated-output acceptance and broad-gate disposition remain the parent
plan's responsibility. These reviews do not establish deployment readiness.

Downstream extension self-review: explicit new-policy filtering occurs only after
full payload/schema/CRC validation; legacy rows and leap-day records remain.
Corrupted-padding regression verifies no validation bypass. All 109 Rust tests,
163 Python API tests and the 400-year generated Parquet audit pass. This extension
changes no Fortran after the independent source reviews.
