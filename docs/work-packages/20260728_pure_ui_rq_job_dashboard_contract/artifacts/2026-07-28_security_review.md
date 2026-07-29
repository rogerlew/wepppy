# Security Review - SURF-07 Pure UI RQ Job Dashboard Contract

## Metadata

- **Package**:
  `docs/work-packages/20260728_pure_ui_rq_job_dashboard_contract/`
- **Reviewer**: `/root/surf07_security_review` (independent, read-only)
- **Date**: 2026-07-28
- **Scope reviewed**: poll-auth fallback, token acquisition and storage,
  metadata rendering, cancellation, and server authorization
- **Commit/branch context**: uncommitted SURF-07 diff on `master` from
  `50a0a895b`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: yes
- **Triage rationale**: The production repair adds authenticated recovery to
  job-info polling and therefore touches token transport and job metadata.
- **Threat model assumptions**:
  - the fallback bridge remains cookie-authenticated, same-origin, and
    CSRF-protected;
  - the minted token retains only its existing `rq:status` authority;
  - job identifiers are untrusted URL components; and
  - server-side cancellation remains the authority for job/run access.

## Findings

No high, medium, or low security findings remain.

## Verdict

- **Gate status**: pass
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: ship

## Surface Checks

- A 401 or 403 causes exactly one authenticated retry; a second failure stops
  and surfaces the canonical error.
- Fallback tokens come from the fixed authenticated same-origin bridge, remain
  memory-only, and are sent only to the fixed rq-engine job-info endpoint.
- Job identifiers are URL-encoded.
- Descriptions, identifiers, errors, and tracebacks remain escaped before HTML
  insertion.
- Cancellation remains confirmation-gated and single-submit client-side.
- Server cancellation retains JWT scope, revocation, session-marker,
  run-access, and Culvert checks.
- Open, optional, and required polling policy remains server-owned.

## Validation Evidence

- Four real inline Jest regressions passed.
- 119 render/template tests passed.
- 149 polling, token, session, cancellation, and payload tests passed.
- `git diff --check` passed.

## Residual Risk

The CAP decorator remains present and unchanged on the Flask dashboard route,
but the retained focused suite does not exercise that decorator directly.
This is a low-risk evidence gap rather than a discovered bypass; direct
rendering and the server-side authorization suites cover the changed boundary.

## Sign-off

- **Security reviewer**: `/root/surf07_security_review`, 2026-07-28
- **Package owner**: Codex, 2026-07-28
