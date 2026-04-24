# Controllers-GL Cache Hardening Rollout

**Status**: Done (2026-04-24)  
**Timezone**: UTC

## Overview
A stale `controllers-gl.js` bundle on WEPPcloud caused real run-control drift in production. This package hardened frontend bundle loading so every page that depends on `controllers-gl.js` uses consistent cache-busting (`static_url`) and always loads the stale-client detector (`controllers_gl_stale_check.js`).

## Objectives
- Standardize all `controllers-gl.js` template includes to `{{ static_url('js/controllers-gl.js') }}`.
- Ensure every template that loads `controllers-gl.js` also loads `controllers_gl_stale_check.js` immediately after it.
- Add regression coverage to prevent future drift.
- Execute explicit code review and QA review gates before closure.

## Scope

### Included
- Template inventory + remediation for all `wepppy/weppcloud/**` templates that include `controllers-gl.js`.
- Script include normalization to `static_url(...)` where template context supports it (all inventoried WEPPcloud templates).
- Missing `controllers_gl_stale_check.js` includes added immediately after `controllers-gl.js`.
- Targeted render/JS regression updates to lock in the invariant.
- Code review and QA review artifacts.

### Explicitly Out of Scope
- Backend API behavior changes.
- New stale-detection mechanisms beyond existing `controllers_gl_stale_check.js`.
- Session/auth and CSRF contract changes.
- UI redesign of stale banner copy/style.

## Stakeholders
- **Primary**: WEPPcloud frontend and platform maintainers.
- **Reviewers**: correctness and QA gates captured in package artifacts.
- **Security Reviewer**: Not required by triage.
- **Informed**: RQ operators and support engineers handling run-control incidents.

## Success Criteria
- [x] Repository grep confirms no remaining `url_for('static', filename='js/controllers-gl.js')` or raw `/static/js/controllers-gl.js` references in WEPPcloud templates.
- [x] Repository inventory confirms every WEPPcloud template loading `controllers-gl.js` also loads `controllers_gl_stale_check.js` immediately after.
- [x] Targeted frontend/controller and template render tests pass.
- [x] Code review artifact completed with no unresolved medium/high findings.
- [x] QA review artifact completed with no unresolved medium/high findings.
- [x] `PROJECT_TRACKER.md` and package tracker/ExecPlan updated through closure.

## Dependencies

### Prerequisites
- Existing stale-check implementation from `docs/mini-work-packages/completed/20260213_stale_controllers_gl_refresh_prompt.md`.
- Existing context processor support in `wepppy/weppcloud/_context_processors.py` (`static_url`, `controllers_gl_expected_build_id`).

### Blocks
- None.

## Related Packages
- **Related**: `docs/mini-work-packages/completed/20260213_stale_controllers_gl_refresh_prompt.md`
- **Related**: `docs/work-packages/20260411_rq_operator_experience_hardening/package.md` (review-gate style precedent)

## Timeline Estimate
- **Estimated**: 1-2 focused sessions.
- **Actual**: Completed in one focused execution pass on 2026-04-24.
- **Risk level**: Low-Medium.

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Changes are template include hygiene and stale-banner coverage; no auth/session boundary, token handling, or new public mutation surfaces.
- **Security review artifact**: `N/A`

## References
- `wepppy/weppcloud/_context_processors.py` - cache-busted static helper and expected build id injection.
- `wepppy/weppcloud/static/js/controllers_gl_stale_check.js` - stale-client banner logic.
- `wepppy/weppcloud/controllers_js/templates/controllers.js.j2` - bundle build id exposure.
- `docs/mini-work-packages/completed/20260213_stale_controllers_gl_refresh_prompt.md` - original stale-check rollout.

## Deliverables
- Template include remediation patch for `controllers-gl.js` + stale checker across all inventoried WEPPcloud templates.
- Updated regression test coverage in `tests/weppcloud/test_stale_controllers_gl_template_wiring.py`.
- Validation evidence captured in tracker + review artifacts.
- `artifacts/2026-04-24_code_review.md` and `artifacts/2026-04-24_qa_review.md` with closed findings.

## Follow-up Work
- Optional server-side telemetry for stale-client incidents can be handled in a separate package if incidents recur.

## Closure Notes
Closed on 2026-04-24 after all required milestones completed (inventory, implementation, regression, validations, review gates, and lifecycle doc updates). No unresolved medium/high findings remain.
