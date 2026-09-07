# Change Inventory

Discovery baseline: `a64c39f8523ba7efab0e13c4973026700f1d780d`, 2026-09-07 20:40 UTC. Source inspection only; no runtime policy is implemented.

| Surface | Observed behavior | Planned change or investigation |
| --- | --- | --- |
| `wepppy/microservices/rq_engine/project_routes.py`, `create` | Supports rq_token, Bearer, session cookie, or CAPTCHA; CAPTCHA is selected before cookie fallback when supplied | Gate anonymous creation before side effects; preserve token precedence and invalid-credential errors; ensure valid sessions with a supplied CAPTCHA are not incorrectly treated as anonymous in restricted mode |
| `wepppy/weppcloud/configuration.py` | Environment-backed Flask configuration | Expose policy with default true and matching API parsing; examine existing helpers before choosing a small shared helper |
| `wepppy/weppcloud/routes/weppcloud_site.py`, `interfaces` | Supplies CAPTCHA settings and role-filtered configuration IDs | Supply server-derived creation availability without weakening role visibility |
| `wepppy/weppcloud/templates/interfaces.htm` | Many regional/legacy forms, CAPTCHA prompts, anonymous asset loading, and inline creation context-menu logic | Gate every creation surface, including variants; tolerate absent forms; retain informational sections and authenticated actions |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py`, `create_index` | `/create` index already requires login; forms target rq-engine | Preserve; test authenticated use with restriction enabled |
| Builder, fork, archive restore, batch, and test routes | Separate surfaces can allocate runs; `/config-builder/` UI already requires login | Verify backend authorization independently; inventory anonymous alternatives and document exact exclusions, especially fork |
| `docker/docker-compose.dev.yml`, `docker/docker-compose.prod.yml` | Web and API have separate environment definitions | Pass flag to both; setting `.env` alone is insufficient unless propagated; inspect HPC/host overrides, avoid unnecessary worker configuration |
| `docker/defaults.env`, `docker/README.md` | Operator default/configuration documentation surfaces | Document default true, false example, affected services, restart/recreate requirements, scope, verification, and rollback; do not edit local secrets or `.env` |
| `docs/ui-docs/cap-js-captcha-auth.md` | Backend section still describes `/create/<config>` | Correct route documentation while explaining conditional creation CAPTCHA; retain unrelated CAPTCHA requirements |
| `wepppy/weppcloud/routes/usersum/weppcloud/getting-started.md` and rq-engine README/OpenAPI | User and API descriptions can promise anonymous creation | Update conditional availability and `403` response; leave generated usersum index untouched |

## Additional Risks and Decisions to Resolve

Stale pages and already-issued CAPTCHA tokens must fail safely after enablement. A logged-in visitor may carry a stale CAPTCHA field; restriction must depend on authenticated identity rather than the presence of that field. Invalid explicit credentials must not fall through to a permissive path. Test expired rq_token session reauthentication and cookie origin/CSRF enforcement without loosening existing rules.

JWT (signed API token) caller types need inspection: preserve currently authorized service/agent callers under existing scopes rather than imposing an invented browser-login requirement. Record which caller types actually exist. Anonymous, inactive/deleted-user sessions, and malformed or expired tokens must not become authorized merely because claims are present.

Do not disable the Cap service globally: login, registration, fork, and report/run viewing have independent CAPTCHA use. Any shared template macro edit requires checking these consumers; prefer page-local policy conditions.

Before implementing, finalize boolean syntax, empty/malformed configuration handling, and canonical contract location. Proposed policy/error details live in `package.md#behavior-and-decision-provenance` until reviewed and promoted. Confirm exact alternative-creation scope before describing this as a site-wide login requirement.

## Regression Entry Points

Extend `tests/microservices/test_rq_engine_project_routes.py`, `tests/weppcloud/test_configuration.py`, `tests/weppcloud/routes/test_weppcloud_site_interfaces_route.py`, and `tests/weppcloud/routes/test_run_0_create_token.py`. Exercise real Jinja rendering for every regional and legacy creation form, not only template-context mocks. Find existing frontend creation/context-menu coverage before adding focused behavior tests.

The API matrix covers unset/true/false; anonymous with absent, invalid, and valid CAPTCHA; valid browser cookie; valid rq_token/Bearer; expired token with valid/invalid session; invalid explicit auth; and authenticated session plus CAPTCHA. Inspect absent/empty/populated optional fields and supported legacy configuration tokens independently. Assert rejected requests do not invoke creation helpers, consume CAPTCHA, or create records/files, then confirm the boundary with a real Compose workflow.
