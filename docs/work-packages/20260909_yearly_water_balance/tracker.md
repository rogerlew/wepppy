# Yearly water-balance tracker

- Contract checkpoint: `9fe98a133`; two independent reviews passed before code edits.
- Implementation: complete locally; limited to total_watbal.py and yearly_watbal.htm.
- Validation: 8 report tests, 239 route/template tests, 835 JavaScript tests,
  and production-data parity passed. Broad Python run: 7,953 passed, 72 skipped;
  excluded the unrelated 100-year disturbed-soil simulation matrix. Lint,
  test-stub checks, and independent correctness review passed.
- Production deployment: outside this task.

Decision: retain omitted-filter default and encode explicit empty selections.
Add a report column using the existing Runoff depth, not a new model calculation.

Outcome: completed locally on 2026-09-09; contract checkpoint committed,
implementation validated and independently reviewed. No deployment performed. Detailed
evidence and test-isolation friction are in the correctness review artifact.
