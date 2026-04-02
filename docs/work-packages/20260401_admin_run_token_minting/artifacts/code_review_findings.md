# Code Review Findings - Admin Run-Scoped Token Minting

Date: 2026-04-01
Reviewer: Codex

## Summary
- High findings: 0 open
- Medium findings: 0 open
- Resolved during review: 1 medium

## Findings

### [Resolved][Medium] `authorize(... )` HTTP 403 could be masked as 500 in run-token mint route
- Location: `wepppy/weppcloud/routes/user.py` (`mint_run_token`)
- Risk: A broad catch in the route could swallow `HTTPException` from `authorize(runid, config)` and turn an access denial into an internal-server response.
- Resolution:
  - Added explicit `except HTTPException: raise` in `mint_run_token`.
  - Removed the newly introduced broad `except Exception` block from `mint_run_token` so unexpected exceptions are not silently translated.
  - Added regression coverage in `tests/weppcloud/routes/test_user_profile_token.py::test_run_token_mint_preserves_authorize_forbidden`.

## Final Disposition
No open medium/high findings remain.
