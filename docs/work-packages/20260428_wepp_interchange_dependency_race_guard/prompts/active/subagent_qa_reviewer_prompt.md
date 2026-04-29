# Sub-Agent Prompt: QA Reviewer Pass (Test Quality and Validation Gate)

Role: `qa_reviewer`

Assess test sufficiency and validation quality for the WEPP interchange dependency race fix.

## Scope
- `tests/rq/test_wepp_rq_pipeline.py`
- Validation command outputs
- Queue graph verification evidence

## QA questions
1. Do tests cover every helper where `_post_watershed_interchange_rq` is enqueued?
2. Do tests assert dependency identity (not just call count/order side effects)?
3. Would tests fail if someone reverts dependency to cleanup-only?
4. Is queue-graph verification included and interpreted correctly?
5. Are docs/contracts updated together with code changes?

## Required outputs
- Findings table with severity (`high`, `medium`, `low`, `none`) and disposition guidance.
- QA gate recommendation: `closure-ready` or `not closure-ready`.
- Explicit list of missing validation steps, if any.
