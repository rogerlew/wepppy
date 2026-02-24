# Route Classification - WEPPcloud CSRF Rollout

Date: 2026-02-24  
Source inventory: `artifacts/route_inventory_raw.txt`

## Inventory Summary

- Raw hits: 89 decorator lines
- Filtered Flask route decorators in `wepppy/weppcloud/routes/**/*.py`: 87
- Non-route documentation hits removed: 2 (`wepppy/weppcloud/routes/nodb_api/README.md`)

## Classification Rules

1. Cookie-auth browser mutation routes (`POST|PUT|PATCH|DELETE`) are CSRF-protected by default.
2. Non-browser or infrastructure boundary routes are exempt only with explicit rationale.
3. Safe methods (`GET|HEAD|OPTIONS|TRACE`) do not require CSRF.

## Classified Route Families

### A) Cookie-auth browser mutation routes (CSRF required)

These remain protected by default under global CSRF middleware:

- WEPPcloud auth/session mutation APIs:
  - `/api/auth/rq-engine-token`
  - `/api/auth/session-heartbeat`
  - `/api/auth/reset-browser-state`
- Security/UI mutations:
  - `/login` (POST)
  - `/oauth/<provider>/disconnect` (POST)
  - `/profile/mint-token` (POST)
  - `/tasks/usermod/` (POST)
- Bootstrap run mutations:
  - `/runs/<runid>/<config>/bootstrap/{enable,mint-token,checkout,disable}`
- Recorder/agent/readme/command-bar mutations:
  - recorder endpoints
  - agent chat create/send/terminate endpoints
  - readme save/preview endpoints
  - command-bar POST endpoints
- NODB task mutations:
  - all `/runs/<runid>/<config>/tasks/*` POST routes in `nodb_api/*`
  - mixed GET/POST task routes (`reset_disturbed`, `load_extended_land_soil_lookup`, `abstract_watershed`, `ash_contaminant`, etc.) where POST remains CSRF-protected
- Other mixed browser POST routes:
  - batch runner create/validate/mutation POSTs
  - combined watershed URL generator POST
  - WEPPcloudR proxy POST
  - CAP verify POST

### B) Non-browser boundary route (explicit exemption)

- `/api/bootstrap/verify-token` (`GET|POST`) in `routes/bootstrap.py`
  - Rationale: Caddy `forward_auth` infrastructure endpoint for git/agent flows, not a browser cookie mutation UI route.
  - Control retained: bootstrap token verification logic and access checks still enforce auth boundary.
  - Action: explicit `@csrf.exempt`.

### C) Safe-method-only paths

- Not included in mutation inventory; CSRF not applicable.

## Notes

- This classification intentionally does **not** add broad blueprint-level exemptions.
- Exemptions are tracked in `artifacts/csrf_exemptions_register.md`.
