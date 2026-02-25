# WEPPcloud Browse Auth Contract
> Authoritative contract for browse microservice authentication and authorization behavior.
> **See also:** `docs/schemas/weppcloud-session-contract.md`, `docs/schemas/weppcloud-csrf-contract.md`, `docs/dev-notes/auth-token.spec.md`

## Normative Status
- This document is normative and authoritative for browse-route auth behavior.
- Requirement keywords `MUST`, `MUST NOT`, `SHOULD`, and `MAY` are interpreted per RFC 2119.
- If implementation and this contract diverge, implementation MUST be corrected or this document MUST be updated in the same change set.

## Scope
- Covers browse microservice routes under `/weppcloud/runs/*`, `/weppcloud/batch/*`, and `/weppcloud/culverts/*`.
- Covers token class requirements, public-run behavior, root-only path behavior, and re-auth redirect behavior.
- Does not redefine JWT claim semantics (`docs/dev-notes/auth-token.spec.md`) or CSRF policy (`docs/schemas/weppcloud-csrf-contract.md`).

## Endpoint Policy Matrix
| Endpoint Family | Anonymous Access | Accepted Token Classes | Extra Constraints |
| --- | --- | --- | --- |
| `/weppcloud/runs/{runid}/{config}/browse/*` | Allowed only for public runs and non-root-only paths | `session`, `user`, `service` | Root-only paths require `Root` role. |
| `/weppcloud/runs/{runid}/{config}/download/*` | Allowed only for public runs and non-root-only paths | `session`, `user`, `service` | Root-only paths require `Root` role. |
| `/weppcloud/runs/{runid}/{config}/gdalinfo/*` | Allowed only for public runs and non-root-only paths | `session`, `user`, `service` | Root-only paths require `Root` role. |
| `/weppcloud/runs/{runid}/{config}/dtale/*` | Not allowed | `session`, `user`, `service` | Root-only paths require `Root` role. |
| `/weppcloud/runs/{runid}/{config}/files/*` | Not allowed | `session`, `user`, `service` | Root-only paths require `Root` role. |
| `/weppcloud/culverts/{uuid}/browse|download|gdalinfo|dtale/*` | Not allowed | `user`, `service` | `download` accepts privileged `user` tokens (`Admin|PowerUser|Dev|Root`); `service` tokens must include `service_groups=culverts`. |
| `/weppcloud/batch/{batch_name}/browse|download|gdalinfo|dtale/*` | Allowed only when base run is public and path is non-root-only | `session`, `user`, `service` | `session` claims may be scoped to batch base run alias (`batch;;{batch_name};;_base`). |

## Group Route Identifier Rules
- Grouped routes (`/batch/*`, `/culverts/*`) MUST authorize against an identifier claim.
- For culvert routes, identifier is `uuid`.
- For batch routes, identifier is `batch_name`, with alias support for `batch;;{batch_name};;_base` when token class is `session`.
- Service tokens MUST include run scope claims (`runs` or `runid`).
- User tokens on grouped routes MUST include at least one privileged role: `Admin`, `PowerUser`, `Dev`, or `Root`.

## Re-Auth Redirect Rules
- For run routes using HTML navigation, 401 responses SHOULD redirect to `/weppcloud/runs/{runid}/?next=<target>`.
- For batch browse routes, 401 responses MUST redirect to `/weppcloud/runs/batch;;{batch_name};;_base/?next=<target>` so the run-session bridge can mint a browse JWT.
- Non-navigation/API contexts MAY return 401/403 directly.

## Cookie and Bridge Expectations
- Browse auth resolution MUST evaluate:
  1. browse JWT cookie candidates, then
  2. bearer token header.
- Invalid/stale cookie auth MUST fall back to bearer token when present.
- Batch run session bridge flows MUST provide a browse cookie that batch routes can consume after run-context re-auth.

## Root-Only Path Rules
- Paths under `_logs` and sensitive filenames such as `exceptions.log` and `exception_factory.log` are root-only.
- Root-only paths MUST return 403 unless the resolved auth context has the `Root` role.

## Source-of-Truth Implementation
- `wepppy/microservices/browse/auth.py`
- `wepppy/microservices/browse/browse.py`
- `wepppy/microservices/browse/_download.py`
- `wepppy/microservices/browse/dtale.py`
- `wepppy/microservices/_gdalinfo.py`
- `wepppy/weppcloud/routes/run_0/run_0_bp.py`

## Conformance Tests (Required)
- `tests/microservices/test_browse_auth_routes.py`
- `tests/weppcloud/routes/test_run_0_nocfg_auth_bridge.py`
- `tests/microservices/test_rq_engine_session_routes.py`

## Change Management
- Any change to browse-route auth policy MUST update this document in the same PR.
- Changes that alter session/cookie bridge behavior MUST also update `docs/schemas/weppcloud-session-contract.md`.
