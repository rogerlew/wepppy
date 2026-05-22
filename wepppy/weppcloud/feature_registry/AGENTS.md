# Feature Registry Agent Guide

This guide is the local playbook for edits under `wepppy/weppcloud/feature_registry/`.

## Scope and Authority

Single-source metadata lives here:

- `feature_registry.yaml` for run feature/mod metadata.
- `config_registry.yaml` for interface config metadata.
- `schema.py` for contract validation.
- `runtime.py` for load/query/role helpers.
- `specification.md` for normative behavior.

If behavior changes through conversation, update `specification.md` in the same change.

## Core Touch Surfaces

When changing feature/config metadata, these are the main consumers:

- `wepppy/weppcloud/routes/run_0/run_0_bp.py`
  - Uses `feature_registry_by_id()` and `load_feature_registry()` for mod visibility and dynamic section loading (`/view/mod/<mod_name>`).
  - Uses `build_header_mod_options()` for the Mods dropdown.
  - Uses `config_registry_by_id()` for run header config maturity.
- `wepppy/weppcloud/routes/nodb_api/project_bp.py`
  - Uses registry roles/backend/dependencies to gate `set_mod`.
- `wepppy/weppcloud/routes/weppcloud_site.py`
  - Uses `load_config_registry()` + `user_meets_min_role()` for `/interfaces/` visibility.
- `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`
  - TOC and section layout are still hand-wired per feature id.
- `wepppy/weppcloud/templates/header/_run_header_fixed.htm`
  - Mod list and maturity pills consume registry-derived context.
- `wepppy/weppcloud/templates/interfaces.htm`
  - Interface cards use `visible_config_ids` and config maturity labels from registry context.
- `wepppy/weppcloud/controllers_js/project.js`
  - Dynamic mod show/hide relies on `data-mod-nav` and `data-mod-section` ids plus `MOD_BOOTSTRAP_MAP`.

## What Feature Registry Enforces

`schema.py` + `runtime.py` enforce these contracts:

- Valid enums for maturity, internal reason, backend, and min role.
- `internal_reason` required only when `maturity=internal`.
- `embargo_until` required for `internal_reason=publication_embargo`, and must be ISO `YYYY-MM-DD`.
- `min_role` must be `dev` when `maturity=internal`.
- `adr_reference` optional, but when set must point to an existing `docs/adrs/*.md` file.
- Unique ids, existing template/config paths, and dependency/blocker references.
- Config attribute overrides from YAML `overrides` (for example, `multi_ofe -> preview`).
- Role/backend/prerequisite visibility checks via `user_meets_min_role()` and `backend_matches_requirement()`.

## What Registry Does Not Enforce

These remain manual and must be updated separately:

- Route auth decorators and ownership checks:
  - `@login_required`, `authorize(...)`, `@requires_cap`, Flask-Security policy.
- Hard-coded role checks in templates/routes outside registry helpers
  - Example: admin/dev utility links in `interfaces.htm`, run-header menu buttons.
- Static TOC/control-shell placement in `runs0_pure.htm`.
- JS bootstrap/controller wiring in `project.js` and `run_page_bootstrap.js.j2`.
- Docs access model under `routes/usersum/*` (`user/operator/developer/internal`) is separate from feature-registry roles.

## Edit Checklist

For feature/config lifecycle or visibility changes:

1. Update YAML (`feature_registry.yaml` and/or `config_registry.yaml`).
2. Update `specification.md` when contract/policy changes.
3. Update run-template/JS touchpoints if the feature has TOC/section/bootstrap effects.
4. Update tests covering role/visibility/validation.
5. Run targeted checks:
   - `wctl run-pytest tests/weppcloud/routes/test_feature_registry_runtime.py`
   - `wctl run-pytest tests/weppcloud/routes/test_project_bp.py`
   - `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py`
   - `wctl run-pytest tests/weppcloud/routes/test_weppcloud_site_interfaces_route.py`
   - `wctl doc-lint --path wepppy/weppcloud/feature_registry/specification.md`

## Common Failure Modes

- New feature id added to registry, but no matching `data-mod-nav`/`data-mod-section` in `runs0_pure.htm`.
- `section_template` exists but controller bootstrap mapping is missing, causing dead UI controls after dynamic enable.
- Internal feature set to `admin` instead of `dev` (schema reject).
- `publication_embargo` uses non-ISO date (schema reject).
- Feature role semantics confused with usersum docs role semantics.
