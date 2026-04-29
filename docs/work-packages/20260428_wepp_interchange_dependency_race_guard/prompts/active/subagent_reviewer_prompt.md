# Sub-Agent Prompt: Reviewer Pass (Correctness and Regression Risk)

Role: `reviewer`

Review the patch for WEPP interchange dependency race hardening.

## Review scope
- `wepppy/rq/wepp_rq_pipeline.py`
- `tests/rq/test_wepp_rq_pipeline.py`
- Queue graph/catalog deltas if generated

## What to verify
1. `_post_watershed_interchange_rq` cannot run before `_build_hillslope_interchange_rq` in all affected helpers.
2. No pipeline variant with hillslope interchange support is left with cleanup-only dependency.
3. No accidental dependency cycles, deadlocks, or unintended over-serialization.
4. Existing downstream dependencies (watbal, return period, exports, final log job) remain coherent.
5. Regression tests are meaningful and would fail if dependency edge is removed.

## Deliverable format
Produce findings first, ordered by severity:
- `ID`, severity, file/function, issue, required action.

Then provide:
- Overall gate: `pass` or `fail`.
- Residual risks.
- Recommended additional tests (if any).

If no findings, state that explicitly.
