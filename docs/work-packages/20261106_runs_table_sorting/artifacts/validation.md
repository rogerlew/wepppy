# RUNS-TABLE-02 validation and operational evidence

## Confirmed failure and bounded repair

Before reload, authenticated read-only Chromium navigation on forest sent
`sort=ttl_deletion_at&direction=asc`, but the running page rewrote its URL to
`sort=last_modified&direction=asc`; a subsequent response omitted the sorting
link. Fresh-code template navigation reversed correctly. These observations
identified stale route/template state across the running development workers,
not an intentional disabled state in the template. No new sort transport was
needed. Separately, unconstrained content widths produced moving/offscreen
headers; fixed scoped colgroups and wrapping address that layout defect.

Verified host `forest`, container `43f5e96d9f52`, workdir `/workdir/wepppy`, and
Gunicorn master PID7/parent1 with `wepppy.weppcloud.app:app`, then sent SIGHUP
using `wctl docker compose exec -T weppcloud`. Only development web workers were
reloaded. Afterwards the real page accepted Creation date → Automatic deletion
ascending → descending → ascending, with identical deletion-header bounds
across reversals; see [read-only browser log](forest-readonly-smoke.log).
No project mutations were submitted and no production deployment was performed.

## Regression evidence

- New disabled-after-unknown Python regression failed before the change.
- Both post-bulk ordering regressions failed before the change.
- `wctl run-pytest tests/weppcloud/routes/test_user_runs_admin_scope.py tests/weppcloud/routes/test_runs_catalog_contract.py --maxfail=1`: 29 passed (29 warnings).
- The independent correctness reviewer also ran the 29-test route set successfully.
- Those tests include Chromium with the real template, real Python normalization
  and sorting helpers, and actual Pure/UI CSS for ordinary and owner-column
  layouts. Pointer and keyboard reversal, switch from creation sort, actual
  ordered rows, fixed measured widths, long unbroken text, pagination, empty
  filtering, one help link and narrow horizontal scrolling all pass.
- `wctl run-npm test`: 124 suites / 1,069 tests passed. Existing lifecycle-cell
  assertions were updated for the explicitly relocated help link.
- `wctl run-npm lint`: passed.
- `wctl run-python wepppy/weppcloud/controllers_js/build_controllers_js.py`: passed;
  no generated bundle diff (production changes are inline template/Python).
- Scoped documentation lint and diff whitespace checks: passed.
- Final independent correctness/UX and security reviews: PASS, no findings.

## Validation limits and broad-suite disposition

The fresh broad Python sweep is omitted for this bounded follow-up under the
nearest `wepppy/weppcloud/AGENTS.md` handoff rule (run it "or document why skipped").
The previous feature sweep passed 13,218 tests (423 skipped) and took one hour;
this follow-up changes only table presentation and a small catalog ordering
partition, with no authorization, persistence, queue, model or schema changes.
The affected route, ordering, browser and complete frontend suites were rerun.
The prior full-suite result is historical evidence, not a fresh full-suite pass.

The isolated Chromium regression uses a simplified base shell; the separate
forest read-only check covers real application navigation and worker behavior.
The user's affected URL was requested but not supplied; forest reproduction is
confirmed, while production instance status is not claimed.
