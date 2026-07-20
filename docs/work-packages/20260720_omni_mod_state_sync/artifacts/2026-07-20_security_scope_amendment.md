# REM-01 Direct Action and Report Security Scope Amendment

**Status**: Accepted by dual review
**Date**: 2026-07-20
**Trigger**: Final security review finding SEC-04
**Authority**: Operator direction to expand, ratify, and complete REM-01

## Finding

The accepted Omni embargo ADR permits unauthorized users to discover only the
disabled feature name. The existing contrast run, dry-run, and delete entry
points enforce JWT scope and run access but do not separately require Dev or
Root. The contrast report has a CAP boundary but lacks both the canonical
run-access check and a Dev/Root role check. These omissions contradict the
ratified action/data boundary and prevent REM-01 security closure.

## Finite Amendment

REM-01 additionally borrows only these entry-point authorization checks:

- `wepppy/microservices/rq_engine/omni_routes.py`: require a Dev or Root claim
  before entering contrast run, dry-run, or delete domain behavior;
- `wepppy/weppcloud/routes/nodb_api/omni_bp.py`: preserve the CAP boundary and
  require both canonical `authorize(runid, config)` run access and the feature
  registry's `min_role: dev` policy before reading or rendering the contrast
  report; and
- focused role-matrix tests proving User, PowerUser, and Admin denial and Dev
  and Root allowance, with denied requests never entering domain behavior.

The amendment does not authorize changes to payload parsing, authorized-flow response shapes,
queue wiring, RQ functions, deletion semantics, report content or formatting,
artifacts, overlays, output data, or model behavior. Existing JWT scope, run
access, CAP, session, CSRF, and exception contracts remain additive mandatory
boundaries. New denial paths use only the canonical authorization status and
payload contracts for the relevant Flask or RQ boundary.

## Acceptance

- Both independent reviewers approve this exact boundary with no unresolved
  high/medium finding.
- A docs-only standalone ancestor records the register, contract decision,
  security artifact, raw confirmations, and disposition before route edits.
- Full role-matrix tests pass for every added entry-point gate. Additional
  negative tests prove that RQ JWT scope and run access still deny Dev/Root,
  and that Flask CAP and run access remain mandatory alongside role. Every
  denied request must stop before contrast domain behavior.

Both independent reviewers approved this finite amendment after the findings
in `2026-07-20_security_scope_review_disposition.md` were resolved. Production
route edits remain gated on the standalone docs-only ancestor commit.
