# Project Config Update UI (WP09)

**Status**: Complete (2026-08-26)
**Initiative branch**: `feature/project-owned-config`
**Starting revision**: `64919058e`
**Security impact**: high; dedicated review required

## Objective

Implement the contract-ratified run-page UI for project-owned configuration
updates: one asynchronous read-only page-load check, a nonblocking digest
warning, an accessible complete preview, explicit apply and job-state handling,
and nested-run linkage to the top-level configuration authority.

## Compatibility and Security Plan

The UI is progressive enhancement and remains dormant while the WP08 feature
flag is off. It must not alter legacy project rendering or mutate on page load.
Availability uses existing run-read authority; preview/apply remain enforced by
the backend's owner/Admin/Root boundary. The browser never constructs config
values or trusts cached authorization. Nested pages use their existing composite
run identity so rq-engine resolves the top-level authority.

## Success Criteria

- [x] One page-load availability request performs no project write.
- [x] Available updates create a run-header notice and complete accessible modal.
- [x] Authenticated digest mismatch is visible, nonblocking, and deduplicated.
- [x] Apply submits the exact preview and trigger, then reports job lifecycle.
- [x] Stale, unavailable, active-job, forbidden, and generic errors are actionable.
- [x] Keyboard, focus, live-region, frontend, docs, and full-suite gates pass.
