# Security Review - SURF-11 Geneva Summary Report Contract

## Metadata

- **Package**:
  `docs/work-packages/20260728_pure_ui_geneva_summary_report_contract/`
- **Reviewer**: `/root/surf11_review` (independent, read-only)
- **Date**: 2026-07-28
- **Scope reviewed**: report initialization, authenticated run queries, map
  payload validation, no-store responses, and embedded JSON safety
- **Commit/branch context**: uncommitted SURF-11 diff on `master` from
  `a0583871b`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: yes
- **Triage rationale**: SURF-11 verifies authenticated, run-scoped report and
  map queries. It changes tests and documentation but retains production
  authorization, validation, and response behavior.
- **Threat model assumptions**:
  - callers retain the existing authorization decorator and run context;
  - POST map inputs remain schema and measure allowlisted; and
  - report payloads continue through Jinja `tojson`.

## Findings

| ID | Severity | Surface | Description | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Browser data integrity | A proposed template bootstrap duplicated the controller's existing lifecycle owner and would double-bind request handlers. | Remove the duplicate bootstrap and prove the single controller-owned initializer. | Resolved |

## Verdict

- **Gate status**: pass
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: ship

## Surface Checks

- Existing authorization and `load_run_context` run scoping are unchanged.
- Query and report responses retain no-store headers.
- POST map schema and measure validation are unchanged.
- Run URLs remain encoded and run-scoped.
- Embedded JSON continues to use Jinja `tojson`.
- No production template, controller, route, generated bundle, dependency,
  RQ/worker, subprocess, secret, or external-egress change remains.

## Validation Evidence

- The Jest lifecycle regression proves exactly one `DOMContentLoaded`
  initializer is registered and that invoking it initializes the report.
- Direct rendering proves exact selected filters, run URLs, payload, map
  controls, accessibility, and empty/error targets.
- Focused route/render, service, and Jest suites pass.
- Full frontend lint and tests pass.

## Residual Risk

No new residual risk beyond the existing authenticated Geneva report/query
surface.

## Sign-off

- **Security reviewer**: `/root/surf11_review`, 2026-07-28
- **Package owner**: Codex, 2026-07-28
