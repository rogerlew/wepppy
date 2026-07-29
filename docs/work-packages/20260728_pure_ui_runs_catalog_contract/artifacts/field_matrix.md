# SURF-06 Runs Catalog Contract Matrix

| Boundary | Risk-bearing contract | Verified evidence |
| --- | --- | --- |
| Page | authenticated table/map shell, canonical endpoints and initial state | actual ordinary/Admin render and page route |
| Ownership | ordinary caller sees only owned runs; alias ignored | `test_user_runs_admin_scope.py` database/route set |
| Admin scope | protected user directory; exact ID/email catalog and map scope | database/route set + actual inline client |
| Catalog | safe metadata, sorting, search, pagination, TTL/modified state | hostile actual-inline render + lifecycle test |
| Map | valid centers only, bounded view, safe labels/links, empty/error states | map routes + actual inline map path |
| Readonly | readonly rows cannot be selected or deleted | actual client + HTTP 400 route regression |
| Delete request | explicit confirmation, encoded exact run/config POST, CSRF | actual inline test + missing-CSRF blueprint test |
| Delete enqueue | reauthorization, queued TTL state, default RQ job ID | exact route enqueue + RQ worker tests |
| Polling | same-origin status, bounded retry, terminal mapping | actual inline finished/failed execution |
| Reload | finished deletion removes only its row; failures remain visible | actual inline execution + worker cleanup |
| Security | no scope widening, unauthorized delete, unsafe output, or CSRF bypass | `2026-07-28_security_review.md` passed |
