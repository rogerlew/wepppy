# F7 failure-class and consumer matrix

**Status**: Initial discovery; verify all rows at M0  
**Date**: 2026-11-12 UTC

The broken shared assumption is: enabling a support-only feature flag is
sufficient authorization for state-changing test routes, and a false default is
sufficient proof that production cannot expose them.

| Surface or consumer | Current dependency path | Risk/compatibility concern | Required evidence | Initial disposition |
| --- | --- | --- | --- | --- |
| `configuration.config_app` | environment to Flask config | No deployment profile; flag alone controls capability | profile enum/default/startup matrix | Confirmed defect |
| Blueprint registration | Flask config to URL map | Enabled flag registers routes in any environment | actual route inventory by profile | Confirmed defect |
| Test ping | anonymous GET | Advertises support state without auth | bearer cases and production absence | Confirmed defect |
| Test create | anonymous POST to run initialization | Anonymous disk/state creation | bearer before parse/create; no-side-effect denial | Confirmed defect |
| Test delete | anonymous DELETE through `get_wd` | Any named resolvable run can be removed | bearer before resolution; explicit non-production authority | Confirmed defect |
| Flask-WTF CSRF | global mutation protection | Bearer automation can be blocked or cookie auth accidentally trusted | bounded exemption; cookie-alone denial | In scope |
| WEPP_AUTH issuer | file-backed secret to JWT | Existing mechanism must support exact audience/scope without widening other tokens | focused issue/decode tests | Reuse candidate |
| wctl auth command | host wrapper to container issuer | Current command prints token; smoke needs non-retaining capture | CLI unit tests and sanitized output scan | In scope |
| wctl Playwright ping | wrapper to `/tests/api/ping` | Currently anonymous and errors suggest only flag enablement | automatic mint/header; fail-fast errors | Confirmed consumer |
| `run-page-smoke.spec.js` | direct create/delete | Missing bearer after server hardening | shared helper migration | Confirmed consumer |
| `a11y/axe-runs0.spec.js` | direct create/delete | Existing session logic must not substitute for support bearer | shared helper plus authenticated UI compatibility | Confirmed consumer |
| `mods-menu.spec.js` | direct create/delete | Missing bearer | shared helper migration | Confirmed consumer |
| `controller-regression.spec.js` | direct create/delete | Missing bearer | shared helper migration | Confirmed consumer |
| `page-load.spec.js` | direct create/delete | Missing bearer | shared helper migration | Confirmed consumer |
| `storm-event-analyzer.spec.js` | direct create/delete | Missing bearer | shared helper migration | Confirmed consumer |
| `playwright_load_all` query behavior | support flag plus Admin role | Profile changes could unintentionally alter optional-controller preview | retain existing Admin/flag checks; focused regression | Compatibility row |
| Dev Compose | common env plus `.env` | Must explicitly opt into development; avoid breaking ordinary dev startup | rendered dev config and smoke | In scope |
| Prod Compose | generated env file | Host override can drift unless literals win | rendered prod config and negative override fixture | Confirmed variant |
| wepp1 override | base prod plus host override | Later merge must not replace production literals | rendered wepp1 model | In scope evidence |
| forest1/test-prod | production Compose family | Test support must not be enabled merely because host is non-public | explicit disposition; no implicit exception | In scope evidence |
| Legacy HPC Compose | legacy dev target | Behavior may drift; target is unsupported | document exclusion or exact compatibility evidence | Unresolved at scaffold |
| Canary smoke Compose | isolated canary | May not need test routes; must not inherit unsafe profile | rendered inventory | Unresolved at scaffold |
| Raw Flask/Gunicorn startup | no Compose profile | Missing value must fail closed to production | direct startup tests | In scope |
| Docs and agent instructions | flag-only setup guidance | Agents may keep making anonymous requests | update canonical wrapper/profile/token guidance | Confirmed consumer |
| Logs/reports/process env | transient JWT | Token can leak during automation | exact-token negative scan; never persist raw evidence | In scope |
| F5 traceback sanitizer | configured secret snapshot | JWT is dynamic, not a configured static secret | prove headers/locals are never captured or logged; no registry expansion | Verified design constraint pending test |
| F1-F6 package evidence | separate revisions and grades | Roll-up can overstate partial or deployment-pending work | exact readiness matrix and owner receipts | In scope coordination |
| F8 port hardening | separate Compose network exposure | Tempting scope coupling | separate package/deploy decision | Out of scope |

## Search Boundary

Search route registration, configuration readers, Compose variants, wctl
Playwright/auth code, every `/tests/api/` reference, generated/static smoke
consumers, documentation, and F1-F6 package gates. Follow indirect request
helpers and Compose merges rather than relying only on same-name search.

The matrix excludes ordinary project creation/deletion policy, unrelated JWT
audiences/scopes, RQ queue wiring, Kubernetes/openwepp deployment, and F8 port
publication. If implementation evidence exposes a shared consumer inside the
authorized class, add it before closure.

## Completion Rule

Every in-scope row must be repaired or verified unaffected with executable
evidence. Every unresolved deployment variant must remain named in the final
readiness/deployment plan. Route status alone cannot prove absence or lack of a
filesystem side effect.

