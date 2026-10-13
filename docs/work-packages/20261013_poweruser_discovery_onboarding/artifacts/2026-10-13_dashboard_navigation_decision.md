# PUUX-01A bounded GL Dashboard navigation checkpoint

Base: a8de37a0db1e678e76eefb36a991514036fb9a9c. Date: 2026-10-13 UTC.
Operator instruction: regular non-PowerUsers need GL Dashboard access; move its
link to More. This authorizes the bounded navigation correction now, not the
remaining PUUX-01 onboarding implementation.

Current source: routes/gl_dashboard.py:gl_dashboard calls authorize(runid,
config) without a PowerUser requirement. The sole generic navigation link is in
the role-guarded PowerUser Panel. Intended delta: add the same destination after
Browse in the run and shared report More menus, remove its panel duplicate.

Canonical delta is docs/ui-docs/contracts/gl-dashboard-navigation-contract.md.
Shared docs/ui-docs/controller-contract.md presentation conventions apply.
Feature-access governance, registry eligibility, output-scope and dashboard
scientific contracts remain unchanged. This is navigation visibility, not an
access grant. Keep run-aware URL resolution, new-tab preference and all route
checks. Security impact low for this bounded template-only change; independent
contract security review still required by contract-first sequencing.

Valid states: ordinary authorized user, PowerUser, Admin/Root and authorized
public anonymous viewer receive the link. No outputs yet keeps existing route
behavior. Unauthorized private-run requests retain denial. Use current viewed
run/config and existing helper for child runs. Hostile run IDs and requests must
not gain a new access path; no new request parameter is accepted.

Validation: existing relevant template/route tests plus direct Jinja readback of
both menu links for ordinary and public viewers; inspect preserved route guard.
No account mutation, model run or full regression suite is justified by moving
an existing anchor. Final evidence must identify actual checks and limits.

Independent correctness and security reviews passed with no findings; see
2026-10-13_dashboard_navigation_reviews.md. Commit this standalone checkpoint
before runtime edits.
