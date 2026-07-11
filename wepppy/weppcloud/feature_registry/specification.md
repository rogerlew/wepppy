# WEPPcloud Feature and Config Registry Specification (MVP)

Status: Draft v1-mvp (2026-05-22)  
Scope: User-facing WEPPcloud metadata for both run features and interface configs.

## Purpose

Define one authority boundary for lifecycle labels, visibility policy, and user-facing availability so WEPPcloud does not duplicate this logic across routes and templates.

This specification covers two registries in one subsystem:

- `feature_registry`: run-page/header capabilities (for example `roads`, `rusle`).
- `config_registry`: launchable interface configs (for example `disturbed9002`, `disturbed9002_wbt`, `reveg`).

## UX Policy (Non-Negotiable)

- Visible means usable.
- If a feature is shown, user can use/toggle it.
- If a config is shown, user can launch it.
- Only exception: project `readonly` state on existing run surfaces.
- Do not show tease-only controls that user cannot use.

## Canonical Authority

The registry authority lives here:

- `wepppy/weppcloud/feature_registry/feature_registry.yaml` (authoritative feature data)
- `wepppy/weppcloud/feature_registry/config_registry.yaml` (authoritative config data)
- `wepppy/weppcloud/feature_registry/schema.py` (shared validation)
- `wepppy/weppcloud/feature_registry/runtime.py` (loader/query helpers)

The two YAML files above are the only hand-edited metadata sources.

## Shared Enums (Both Registries)

- `maturity`: `stable | preview | experimental | deprecated | internal`
- `internal_reason`: `compute | api_constrained | beta | publication_embargo | null`
- `embargo_until`: `YYYY-MM-DD | null`
- `min_role`: `user | poweruser | dev | admin | root`
- `requires_backend`: `any | wbt | topaz`

`internal_reason` must be present only when `maturity=internal`.
`embargo_until` is required only when `internal_reason=publication_embargo`.
`min_role` must be `dev` when `maturity=internal`.
An internal beta is represented by `maturity=internal`,
`internal_reason=beta`, and `min_role=dev`; `beta` is not a maturity value.

User-facing maturity definitions are published in:

- `wepppy/weppcloud/routes/usersum/weppcloud/user-guide.md` (`Feature Maturity Labels`)

Classification rules for maintainers/implementers:

- Choose the least-optimistic maturity label supported by current evidence.
- Do not classify as `stable` if regional transferability, validation coverage, or operational support is still materially unresolved.
- If a feature is visible in WEPPcloud UI, it must be usable (except project `readonly` state).

## Feature Registry MVP Schema

Required fields per feature entry:

- `id`: stable feature key (for example `roads`, `rusle`)
- `label`: user-facing label
- `maturity`
- `internal_reason`
- `embargo_until`
- `min_role`
- `requires_backend`
- `requires_features`: list of prerequisite feature ids
- `section_template`: template path for feature section rendering

Optional fields:

- `nav_label`: run-page navigation label when different from `label`
- `section_id`: section anchor id for async section rendering and nav wiring
- `section_class`: section wrapper class (defaults to `wc-stack`)
- `adr_reference`: optional repo-relative ADR link under `docs/adrs/*.md` for release-governance rationale
- `enable_dependencies`: mod ids to auto-enable when this feature is enabled
- `disable_blockers`: mod ids that must be disabled before this feature can be disabled

Optional top-level fields:

- `internal_prerequisites`: non-toggle prerequisite ids allowed in
  `requires_features` and `enable_dependencies` (for example `disturbed`, `polaris`)

## Config Registry MVP Schema

Required fields per config entry:

- `id`: stable config key used in launch forms and run URLs (for example `disturbed9002_wbt`)
- `label`: user-facing label
- `cfg_path`: config file path under `wepppy/nodb/configs/`
- `maturity`
- `internal_reason`
- `embargo_until`
- `min_role`
- `requires_backend`

Optional fields:

- `replaced_by`: config `id` used as migration hint when entry is `deprecated`

Optional top-level rules:

- `overrides`: declarative config-attribute override rules applied at runtime

Per-override schema:

- `id`: stable rule key
- `when.cfg_bool.section`: config section name (for example `wepp`)
- `when.cfg_bool.option`: config option name (for example `multi_ofe`)
- `when.cfg_bool.equals`: boolean match value
- `set.maturity`: maturity value to apply when rule matches
- `set.internal_reason`: nullable internal reason that must satisfy maturity/internal_reason contract
- `set.embargo_until`: nullable ISO date required when `set.internal_reason=publication_embargo`

## Runtime Semantics

Feature visibility/usability requires all:

- caller role is at least `min_role`
- backend matches `requires_backend` (or it is `any`)
- all `requires_features` are active for the run

Config visibility/selectability requires all:

- caller role is at least `min_role`
- `cfg_path` resolves to an existing config file

Backend matching policy for configs:

- On backend-specific surfaces with an active backend context, backend must match `requires_backend` (or be `any`).
- On `/interfaces/` launch surfaces (no active run/backend yet), role + config existence apply and backend remains part of config metadata/presentation.

Config attribute overrides are applied after YAML validation, from
`config_registry.yaml` `overrides` in file order.

- Rule precedence is `effective runtime override > declared YAML maturity`.
- Missing/null/absent matched config attributes do not trigger a rule.
- Boolean override matching is strict (`true|false|yes|no|on|off|1|0`); invalid tokens fail validation.

If conditions fail, hide the entry from user-facing launch/toggle surfaces.

Registry validation/load failures are treated as fatal for page render in MVP
(surface returns exception response rather than partial render).

When a feature is visible:

- enable toggle by default
- if project is `readonly`, disable with explicit readonly reason

Registry file order is authoritative for display order in MVP.

## Validation Rules

- `id` unique and non-empty within each registry.
- shared enum values required.
- `internal_reason` is non-null only when `maturity=internal`.
- `embargo_until` must be null unless `internal_reason=publication_embargo`, and must be an ISO date (`YYYY-MM-DD`) when set.
- `min_role` must be `dev` when `maturity=internal`.
- `adr_reference` (when present) must be repo-relative, remain under `docs/adrs/`, reference a `.md` file, and reference an existing file.
- feature `requires_features` and `enable_dependencies` entries must reference known run-mod ids (registry feature ids or `internal_prerequisites`).
- feature `section_template` must be repo-relative, remain under `wepppy/weppcloud/templates/`, and reference an existing file.
- feature `disable_blockers` entries must reference existing feature ids.
- config `cfg_path` must be repo-relative, remain under `wepppy/nodb/configs/`, and reference an existing file.
- config `replaced_by` (when present) must reference an existing config id.

## Consumption Rules

- `project_bp.py` uses `feature_registry` for labels and feature-allow checks.
- `run_0_bp.py` uses `feature_registry` for feature visibility decisions.
- `_run_header_fixed.htm` uses registry-derived mod option lists, maturity labels, and role gating.
- `runs0_pure.htm` section/nav layout remains template-defined in MVP; visibility and maturity metadata are registry-driven via `run_0_bp.py` context.
- `weppcloud_site.py` computes role-aware config visibility and maturity labels from `config_registry`.
- `interfaces.htm` keeps a curated card layout in MVP, while launch buttons and maturity display are registry-informed/gated.

## UI Presentation Expectations (Maturity)

- Documentation surfaces: use plain text maturity definitions (no pills).
- Maturity pills are opt-in and must be explicitly approved per surface in this section. Do not add pills to new surfaces by default.
- Mods dropdown rule: do not render feature maturity pills/labels in `_run_header_fixed.htm` Mods dropdown.
- Link target: every approved maturity pill links to `wepppy/weppcloud/routes/usersum/weppcloud/user-guide.md#feature-maturity-labels`.
- Interfaces card rule: `interfaces.htm` renders exactly one maturity pill per interface card, even when a card exposes multiple config launch buttons.
- Interfaces card selection rule: when a card contains multiple config launch buttons, the card pill uses the card's primary/canonical config maturity (not one pill per button).
- Run header rule: render interface maturity pill adjacent to the NoDb version token in `_run_header_fixed.htm`.
- Feature control-shell rule: render feature maturity pill adjacent to the control label/title in the control-shell summary header.
- Styling contract: reuse `wc-run-header__version` pill styling for maturity pills across these surfaces.
- Theme-metric constraint: do not add new theme-metric variables solely for maturity pills in MVP.
- Accessibility contract: maturity pills include descriptive `title`/`aria-label` text indicating the maturity class.

## Minimal Examples

```yaml
# feature_registry.yaml
version: 1
features:
  - id: roads
    label: Roads
    maturity: stable
    internal_reason: null
    min_role: user
    requires_backend: wbt
    requires_features: []
    section_template: controls/roads_pure.htm
```

```yaml
# config_registry.yaml
version: 1
configs:
  - id: disturbed9002
    label: Disturbed (CONUS)
    cfg_path: wepppy/nodb/configs/disturbed9002.cfg
    maturity: stable
    internal_reason: null
    min_role: user
    requires_backend: any
  - id: disturbed9002_wbt
    label: Disturbed + WBT (CONUS)
    cfg_path: wepppy/nodb/configs/disturbed9002_wbt.cfg
    maturity: preview
    internal_reason: null
    min_role: user
    requires_backend: wbt
  - id: reveg
    label: Reveg
    cfg_path: wepppy/nodb/configs/reveg.cfg
    maturity: experimental
    internal_reason: null
    min_role: user
    requires_backend: any
overrides:
  - id: multi-ofe-is-preview
    when:
      cfg_bool:
        section: wepp
        option: multi_ofe
        equals: true
    set:
      maturity: preview
      internal_reason: null
```

## Explicit Non-Goals (MVP)

- No separate `enable_roles` field.
- No large metadata taxonomy in v1.
- No auth model redesign.

## Test Expectations

At minimum:

- schema validation tests for shared enums and cross-field rules
- feature parity tests for header/run-page render lists from registry
- feature visibility tests from backend + prerequisites + role
- config launch-surface render tests from registry data in `interfaces.htm`
- toggle endpoint behavior parity for visible features
