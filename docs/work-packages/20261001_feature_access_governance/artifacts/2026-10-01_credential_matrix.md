# FA-01 credential and Culvert compatibility matrix

Source: `36f35b6f0`. Independent read-only source review by `/root/contract_security`, 2026-10-01. Subsequent read-only deployed inspection is recorded in [M0 evidence](2026-10-01_milestone_zero.md). No bearer values/signing secrets were exposed; no positive workflow compatibility pass is claimed.

## Culvert operations

Paths below are relative to `/rq-engine/api` unless explicitly prefixed.

| Method / path | Current admission | Current resource limit / evidence |
| --- | --- | --- |
| POST `/culverts-wepp-batch/` | Verified JWT + `culvert:batch:submit` | No required class, registered subject or resource claim; creates new UUID. `culvert_routes.py:culverts_wepp_batch` |
| POST `/culverts-wepp-batch/{batch_uuid}/retry/{point_id}` | Verified JWT + `culvert:batch:retry` | UUID/batch/point/path validity, but no credential-to-batch binding. `culverts_retry_run` |
| POST `/culverts-wepp-batch/{batch_uuid}/finalize` | Verified JWT + `culvert:batch:retry` | Existing valid UUID, but no credential-to-batch binding. `culverts_finalize_batch` |
| GET `/jobstatus/{job_id}`, GET `/jobinfo/{job_id}`, POST `/jobinfo` | Poll mode `open`, `token_optional`, or `required`; authenticated poll requires `rq:status` | No per-job owner/resource check. `job_routes.py:_authorize_polling_request` and handlers |
| POST `/canceljob/{job_id}` | `rq:status` or `culvert:batch:submit` | Submit scope plus `culvert_batch_uuid` job metadata skips ordinary run authorization; other status path checks run only when metadata has `runid`. `job_routes.py:canceljob` |
| `/weppcloud/culverts/{uuid}/browse`, schema, gdalinfo, dtale | User/service classes only; no anonymous/session | Service batch resource claim; current user privileged-role gate. These paths do not currently require `service_groups=culverts`. `browse/auth.py:authorize_group_request` and callers |
| `/weppcloud/culverts/{uuid}/download/{subpath}` | Same class/resource checks | Also requires `service_groups=culverts` for service token. `browse/_download.py:download_culvert_with_subpath` |

Submit/retry/finalize return a **different** seven-day service browse credential: inherited subject, `runs=[batch_uuid]`, `service_groups=[culverts]`, new `jti`, rq-engine audience, and no supplied `scope` claim (`culvert_routes.py` browse-token helper). It cannot satisfy `rq:status`-authenticated polling or convert via the rq-engine session bridge. Open-mode polling remains independently available without a token.

`auth.py:require_jwt` verifies configured signature/audience, required `jti`, revocation and requested scopes. Shared decoding validates time claims when present; normal issuance supplies them. Do not conflate issued-token defaults with decoder-required fields or silently change legacy credential shape/TTL.

Existing fixtures intentionally issue submit/retry credentials without token class/resource claims (`tests/microservices/test_rq_engine_culverts.py`) and accept dual-scope Culvert cancellation without run claims (`test_rq_engine_jobinfo.py`). They are compatibility leads, not deployed approval. The submitting integration may have workflow-wide reach; requiring a new per-batch claim would change behavior and needs an explicit decision.

## Human and derivative credentials

| Issuer / source | Identity / scopes | Required FA-01 treatment |
| --- | --- | --- |
| `routes/user.py:mint_profile_token` | User class; numeric User ID; 90 days; run/query/rq scopes; no Culvert submit/retry | Trusted human adapter; live group checks for restricted admission only |
| `routes/user.py:mint_run_token` | Admin/Root human-issued service, `admin-run-token:<id>`, `service_groups=[admin-run-token]`, one run, 24 hours | Human delegation, not independent integration; verify trusted issuance and live originating account |
| `rq_engine/session_routes.py:issue_session_token` | Bearer `rq:status` + run checks or same-origin cookie path; four-day run session with fixed scope bundle | Preserve human/anonymous/integration origin for restricted admission; ordinary session behavior unchanged |
| `run_0_bp.py:_set_run_session_jwt_cookie` | Separate Flask four-day session issuer including Batch compatibility cookie | Same restricted-admission provenance boundary; retain existing scope-bundle distinction |
| `command_bar/command_bar.py` MCP issuance | Human-derived query-only token; subject from Flask-Security `get_id()`, not necessarily numeric account ID | Trusted mapping to canonical User ID; no numeric-sub assumption. Normal MCP scope/audience does not permit rq conversion |
| Independent registered Culvert integration | Verified service subject `culvert-batch-submit-90d`, submit-only, no run claims; expired | Preserve registered operation path and normal expiry rejection; deployed evidence below |
| Returned Culvert browse credential | Batch-bound derivative, independent of operation credential scope bundle | Keep originating principal classification when newly issued; no polling or implicit scope grant |

Current `_identity_from_claims` in rq-engine parses `user_id`/numeric `sub` without token-class provenance, then can copy it into a session. New group enforcement cannot reuse that as human proof. Grouped browse currently checks JWT `jti` but does not invoke session-marker/tombstone validation; the existing session contract already requires tombstone rejection. This is a separate conformance obligation, not permission to change session lifetimes.

## Restricted-feature provenance interface

Use a resolved internal principal with `principal_kind` (`anonymous`, `human`, `integration`), canonical `principal_id` and trusted provenance reference, alongside existing token class/scopes/resource/time/revocation data. It grants no permission by itself. Explicit adapters resolve user tokens, authenticated Flask identities, trusted admin-run-token delegation, command-bar identities and registered integrations.

For new derivatives, carry resolved origin in a versioned signed claim populated by the issuer, never caller input. Legacy sessions require authoritative human binding or transparent reissuance through verified identity before newly protected group access; numeric subjects alone are insufficient. The canonical FA-01 Tokens section freezes `feature_access_principal` version 1 and trusted adapters/legacy handling for restricted operations only. Ordinary anonymous functionality remains unchanged; the creator-grant proposal is withdrawn. Implementation is pending.

Human Culvert groups do not create operation scopes. Initial supported human submission can use operator-issued user-class credentials carrying the existing Culvert scopes via `_scripts/issue_auth_token.py`; do not silently add these scopes to every PowerUser/profile token or delegate the independent integration secret. This bounded issuance path is recorded in the canonical FA-01 transport contract.

## Deployed evidence and operational dependency

The operator identified the Culvert client on wepp2; read-only inspection and actual wepp1 validator checks are recorded in [M0 evidence](2026-10-01_milestone_zero.md). The verified configured credential is service-class, submit-only, no run claims; it is expired and must remain rejected. Source client files match the deployed files for submit/poll/download; retry/finalize/cancel are not called by those client paths. Server polling is open. Per-deployment maintainer account identity is verified locally and on wepp1, with email-based lookup required elsewhere before seeding.

Credential renewal and successful live integration acceptance remain explicit later-stage dependencies. No token mutation or expiry bypass is authorized by this checkpoint. Preserve normal revocation via JWT `jti` and the current denylist mechanism; the non-secret token fingerprint is retained for audit.
