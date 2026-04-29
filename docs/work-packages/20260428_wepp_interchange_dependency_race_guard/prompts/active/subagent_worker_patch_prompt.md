# Sub-Agent Prompt: Worker Patch (Queue Dependency Race Guard)

Role: `worker`

Implement the minimal code/test patch for this race fix.

## Context
Production failure showed `_build_hillslope_interchange_rq` and `_post_watershed_interchange_rq` overlapping on the same run, causing intermittent `H.wat.parquet.tmp` commit failure. Fix by dependency ordering, not delays.

## Required edits
1. `wepppy/rq/wepp_rq_pipeline.py`
   - In each affected enqueue helper, ensure `tasks._post_watershed_interchange_rq` depends on:
     - `tasks._post_run_cleanup_out_rq`
     - and the corresponding `tasks._build_hillslope_interchange_rq` job reference (when present in that helper).
   - Keep existing behavior unchanged outside dependency fan-in.

2. `tests/rq/test_wepp_rq_pipeline.py`
   - Add/update assertions that verify `_post_watershed_interchange_rq` depends on hillslope interchange in each affected helper.
   - Keep tests deterministic and scoped.

3. Queue contract docs (only if drift requires it)
   - If `wctl check-rq-graph` reports drift, run `python tools/check_rq_dependency_graph.py --write` and include resulting catalog/graph updates.

## Validation
Run:
- `wctl run-pytest tests/rq/test_wepp_rq_pipeline.py --maxfail=1`
- `wctl check-rq-graph`
- if drift: `python tools/check_rq_dependency_graph.py --write`
- `git diff --check`

## Output requirements
In your final response, provide:
- Files changed.
- Dependency edges changed (before vs after).
- Test/validation command results.
- Any residual risk or open follow-up.
