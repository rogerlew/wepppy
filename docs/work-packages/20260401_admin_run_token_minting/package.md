# Admin Run-Scoped Token Minting for Sync and Debug Workflows

**Status**: Complete (2026-04-01)

## Overview
This package adds an admin-only, run-scoped JWT minting workflow directly from the PowerUser panel. The token is intended for cross-server run sync and agent/debug API access, with a short fixed lifetime to reduce exposure risk.

## Objectives
- Add an admin-only run-scoped token mint endpoint with a fixed 24-hour TTL.
- Expose a matching admin-only control in the PowerUser panel Actions column.
- Reuse existing profile token UI styling and interaction patterns (mint/copy/status feedback).
- Document claim/scope/audience/TTL behavior and operator usage.
- Add regression coverage for endpoint authorization and UI rendering behavior.

## Scope
This package covers WEPPcloud Flask routes/templates for token minting UI + endpoint behavior and token contract docs.

### Included
- New run-scoped token endpoint requiring Admin/Root privileges.
- PowerUser panel UI action and token display/copy flow.
- Token contract and user-facing docs updates.
- Route/template tests and targeted QA gates.

### Explicitly Out of Scope
- Replacing profile token minting.
- Expanding non-admin token issuance surfaces.
- Full run-sync pipeline rewiring (follow-up package if needed).

## Stakeholders
- **Primary**: WEPPcloud admins and operators performing run sync/debug.
- **Reviewers**: WEPPcloud route/template/auth maintainers.
- **Informed**: Docs maintainers and automation users.

## Success Criteria
- [x] Admin-only endpoint mints run-scoped token with fixed 24-hour TTL.
- [x] Endpoint rejects non-admin callers with canonical error payload.
- [x] PowerUser Actions column shows mint controls only for admins.
- [x] Mint/copy UX follows profile token styling and behavior.
- [x] Tests cover endpoint auth/claims/TTL and template visibility.
- [x] Auth contract and usersum/operator docs updated.
- [x] QA gates pass; medium/high findings are resolved before closure.

## Dependencies

### Prerequisites
- Existing JWT utility contract in `wepppy/weppcloud/utils/auth_tokens.py`.
- Existing PowerUser panel in `wepppy/weppcloud/templates/controls/poweruser_panel.htm`.

### Blocks
- Follow-up work to consume run-scoped tokens inside run-sync enqueue path.

## Related Packages
- **Related**: `docs/work-packages/20260219_cross_service_auth_tokens/`
- **Related**: `docs/work-packages/20260330_disturbed_panel_modal/` (PowerUser panel evolution)
- **Follow-up**: credentialed run-sync execution path wiring in RQ jobs.

## Timeline Estimate
- **Expected duration**: 1 focused session
- **Complexity**: Medium
- **Risk level**: Medium

## References
- `wepppy/weppcloud/routes/user.py`
- `wepppy/weppcloud/routes/command_bar/command_bar.py`
- `wepppy/weppcloud/templates/controls/poweruser_panel.htm`
- `wepppy/weppcloud/templates/user/profile.html`
- `docs/dev-notes/auth-token.spec.md`
- `wepppy/weppcloud/routes/usersum/weppcloud/getting-started.md`

## Deliverables
- New admin-only run token endpoint.
- PowerUser panel token mint UI block.
- Updated token contract docs and usersum note.
- Added/updated route and template tests.
- Code review and QA review artifacts with medium/high findings resolved:
  - `docs/work-packages/20260401_admin_run_token_minting/artifacts/code_review_findings.md`
  - `docs/work-packages/20260401_admin_run_token_minting/artifacts/qa_review_findings.md`

## Follow-up Work
- Optional: pass minted run token through run-sync enqueue and worker fetch path.
- Optional: add explicit audit trail persistence for admin-minted run tokens.
