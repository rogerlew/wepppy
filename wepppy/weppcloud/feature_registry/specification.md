# WEPPcloud Feature and Config Registry Specification (MVP)

Status: Draft v1-mvp (2026-05-22)  
Scope: User-facing WEPPcloud metadata for both run features and interface configs.

FA-01 amendment prepared 2026-10-01: [feature access contract](../../../docs/schemas/feature-access-governance-contract.md). Group access, public inspection/action separation and conservative multi-OFE maturity are specified below; implementation and the independent-review ancestor checkpoint are pending. Existing code/tests describe the earlier MVP until that checkpoint is implemented.

## Purpose

Define one authority boundary for lifecycle labels, visibility policy, and user-facing availability so WEPPcloud does not duplicate this logic across routes and templates.

This specification covers two registries in one subsystem:

- `feature_registry`: run-page/header capabilities (for example `roads`, `rusle`).
- `config_registry`: launchable interface configs (for example `disturbed9002`, `disturbed9002_wbt`, `reveg`).

## UX Policy (Non-Negotiable)

- Public projects expose existing feature views/results read-only to viewers
  without action permission, subject to the explicit publication-embargo
  exception in FA-01 and ADR-0001. New inspect-only restricted-feature views must not initialize that feature.
- Action controls require the feature's effective role/group entitlement and
  existing operation/run authorization; otherwise disable/omit them with a clear reason. FA-01 adds no general owner/writer gate and preserves anonymous functionality.
- `menu_min_role` may provide disabled name discovery; it is not read or action
  authorization and does not release embargoed results.
- A caller without effective feature entitlement receives the exact disabled
  reason `Not Authorized`; a group grant can satisfy entitlement below `min_role`.
- Informational config cards may be shown without launch authority; launch
  controls require the config and project-creation permissions.
- Project `readonly` independently disables mutations for every feature group.
- Disabled discovery controls must explain the restriction; they do not grant
  action permission.

## Canonical Authority

The registry authority lives here:

- `wepppy/weppcloud/feature_registry/feature_registry.yaml` (authoritative feature data)
- `wepppy/weppcloud/feature_registry/config_registry.yaml` (authoritative config data)
- `wepppy/weppcloud/feature_registry/schema.py` (shared validation)
- `wepppy/weppcloud/feature_registry/runtime.py` (loader/query helpers)

The two YAML files above are the only hand-edited metadata sources.

Locale and run capability authority are explicit non-owners of this registry.
`config_registry.yaml` continues to own Interface visibility, maturity, role,
backend, labels, and ordering only. It MUST NOT gain `locale_profile`, dataset
availability, runtime locale tokens, or capability-graph metadata. Interface
labels, filenames, links, and config tokens cannot supply or override effective
`.cfg` locale. The Config Builder and project-config contracts own their typed
locale/capability authority separately.

## Shared Enums (Both Registries)

- `maturity`: `stable | preview | experimental | deprecated | internal`
- `internal_reason`: `compute | api_constrained | beta | publication_embargo | null`
- `embargo_until`: `YYYY-MM-DD | null`
- `min_role`: `user | poweruser | dev | admin | root`
- `menu_min_role`: optional `user | poweruser | dev | admin | root`; defaults
  to `min_role` and may only broaden disabled menu discoverability
- `requires_backend`: `any | wbt | topaz`
- Feature `access_group`: optional stable account-group key.
- Feature `access_mode`: `role_or_group | group_only` when a group is declared.

`internal_reason` must be present only when `maturity=internal`.
`embargo_until` is required only when `internal_reason=publication_embargo`.
`min_role` must be `dev` when `maturity=internal`.
For FA-01, this is retained legacy metadata, not a bypass of `group_only`.
Current account-group membership is evaluated separately from the static loader.
An internal beta is represented by `maturity=internal`,
`internal_reason=beta`, and `min_role=dev`; `beta` is not a maturity value.

User-facing maturity definitions are published in:

- `wepppy/weppcloud/routes/usersum/weppcloud/user-guide.md` (`Feature Maturity Labels`)

Classification rules for maintainers/implementers:

- Choose the least-optimistic maturity label supported by current evidence.
- Do not classify as `stable` if regional transferability, validation coverage, or operational support is still materially unresolved.
- Public feature inspection and action permission are separate under FA-01.

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

- `access_group` and `access_mode`: FA-01 internal-feature action policy. Initial
  group keys match the feature IDs. OpenET, Batch and human Culvert access use
  `group_only`; Omni Contrasts, PATH-CE and AgFields use `role_or_group`.
  Omission preserves legacy role behavior outside this changed inventory.
- `nav_label`: run-page navigation label when different from `label`
- `section_id`: section anchor id for async section rendering and nav wiring
- `section_class`: section wrapper class (defaults to `wc-stack`)
- `adr_reference`: optional repo-relative ADR link under `docs/adrs/*.md` for release-governance rationale
- `enable_dependencies`: mod ids to auto-enable when this feature is enabled
- `disable_blockers`: mod ids that must be disabled before this feature can be disabled
- `menu_min_role`: minimum role allowed to see the menu option even when the
  caller cannot enable it; omission preserves existing visibility semantics

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

Feature action availability requires all:

- effective feature entitlement: current group membership for `group_only`,
  legacy `min_role` audience or current membership for `role_or_group`, and
  legacy role audience when no group policy is declared
- existing operation/run authorization; public access never substitutes for restricted-feature entitlement, but ordinary anonymous behavior remains unchanged
- backend matches `requires_backend` (or it is `any`)
- all `requires_features` are active for the run

Public read-only feature sections follow FA-01 independently of the action
audience. Retained readable results do not disappear merely because current
backend/prerequisites prevent execution. Embargoed reads require effective
feature entitlement plus run access. Group-only OpenET/Batch actions have no
Admin/Dev/Root override. Account-store errors never fall back to broader roles.

An entry with explicit `menu_min_role` uses discoverable menu semantics:

- a caller with effective action entitlement or at or above `menu_min_role` sees the menu option; public read-only sections remain separately discoverable;
- a caller without effective action entitlement sees a disabled checkbox with `Not Authorized`, regardless of broad role;
- an authorized caller missing `requires_features` sees a disabled unchecked
  checkbox with `Enable <feature labels> first`;
- when prerequisites become active, the checkbox becomes enabled without being
  checked and without activating the run-page section or preflight navigation;
- an authorized caller may always disable an already-active feature, including
  cleanup of a legacy state whose prerequisite is missing.

`requires_features` is an enable-time guard and never auto-enables a feature.
Only `enable_dependencies` may add another feature to the persisted mod list.
Run-page sections require the feature's own state and the applicable inspection
policy; a prerequisite's state cannot substitute for that id. Action/preflight
navigation additionally reflects action permission. Missing optional state
must render safely without creating controllers or starting jobs.

Config visibility/selectability requires all:

- caller role is at least `min_role`
- `cfg_path` resolves to an existing config file

Backend matching policy for configs:

- On backend-specific surfaces with an active backend context, backend must match `requires_backend` (or be `any`).
- On `/interfaces/` launch surfaces (no active run/backend yet), role + config existence apply and backend remains part of config metadata/presentation.
- Launch availability additionally follows `docs/schemas/project-creation-policy.md`; its anonymous-creation restriction does not grant roles or hide informational card content.

Config attribute overrides are applied after YAML validation, from
`config_registry.yaml` `overrides` in file order.

- General precedence is `effective runtime override > declared YAML maturity`,
  subject to the conservative `multi-ofe-is-preview` rule: declared Stable or
  Preview becomes/remains Preview; Experimental, Internal and Deprecated remain
  unchanged. A representation flag cannot promote or remove restrictions.
- Missing/null/absent matched config attributes do not trigger a rule.
- Boolean override matching is strict (`true|false|yes|no|on|off|1|0`); invalid tokens fail validation.

If action conditions fail, suppress or disable the launch/toggle action with a
reason; public inspect-only views remain governed by FA-01. Explicit
`menu_min_role` name discovery remains permitted, including the embargo case.

Registry validation/load failures are treated as fatal for page render in MVP
(surface returns exception response rather than partial render).

The reserved project-owned Config Builder token `config` is not a shared
Interfaces preset and MUST NOT be added to `config_registry.yaml`. When a run
uses token `config` and its valid root `config-manifest.json` declares
`source_kind=builder`, the run header MUST present Preview maturity. Missing or
malformed manifest state does not invent Builder provenance. Every
Builder-created project remains Preview regardless of its selected backend,
representation, or WEPP binary until a separately ratified promotion changes
this rule.

When a feature is visible:

- enable its toggle only when action authorization and prerequisites pass
- if project is `readonly`, disable with explicit readonly reason

Registry file order is authoritative for display order in MVP.

### Standalone runners and the Mods menu

Accepted and locally validated 2026-09-21; not deployed. The run-header Mods menu excludes
`culvert_runner` and `batch_runner` for every role and backend, including
`include_all` preview/test rendering and runs with either id already active.
These are standalone workflows without run-level UI controls, so a run-level
toggle is misleading. Keep their registry metadata, standalone entry points,
authorization and persisted run state unchanged. This is a menu-only exclusion,
not feature removal or disabling; other feature visibility rules are unchanged.

## Validation Rules

- `id` unique and non-empty within each registry.
- shared enum values required.
- `internal_reason` is non-null only when `maturity=internal`.
- `embargo_until` must be null unless `internal_reason=publication_embargo`, and must be an ISO date (`YYYY-MM-DD`) when set.
- `min_role` must be `dev` when `maturity=internal`.
- FA-01 group metadata is accepted only for explicitly registered internal
  features. Require a non-empty `access_group` with `access_mode`; reject an
  unknown mode. Resolve membership at request time, not in schema validation.
- `menu_min_role`, when present, must be a valid role whose authorized audience
  is a superset of the `min_role` audience. Role names are not a linear rank:
  `dev` authorizes Dev/Root while `admin` authorizes Admin/Root. Validation must
  compare those concrete audiences, so neither can broaden the other. The field
  changes menu discoverability only and never grants enable or dynamic-section
  authorization.
- For a `publication_embargo` feature, effective role/group entitlement governs every action or
  data entry point registered by that feature's accepted domain/remediation
  contract. Menu discoverability never satisfies this server authorization.
- `adr_reference` (when present) must be repo-relative, remain under `docs/adrs/`, reference a `.md` file, and reference an existing file.
- feature `requires_features` and `enable_dependencies` entries must reference known run-mod ids (registry feature ids or `internal_prerequisites`).
- feature `section_template` must be repo-relative, remain under `wepppy/weppcloud/templates/`, and reference an existing file.
- feature `disable_blockers` entries must reference existing feature ids.
- config `cfg_path` must be repo-relative, remain under `wepppy/nodb/configs/`, and reference an existing file.
- config `replaced_by` (when present) must reference an existing config id.

## Consumption Rules

- `project_bp.py` uses `feature_registry` for labels and feature-allow checks.
- `run_0_bp.py` uses `feature_registry` for feature visibility decisions.
- Publication-embargo action/data routes registered by an accepted domain or
  remediation contract enforce the same effective role/group entitlement in addition to
  every applicable/additive JWT scope, run-access, CAP, session, and CSRF
  boundary named by that contract.
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
    min_role: poweruser
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

## Explicit Non-Goals

- No separate `enable_roles` field.
- No large metadata taxonomy in v1.
- FA-01 adds bounded account-group records and shared access evaluation, not a
  new identity service, arbitrary policy language or generalized role hierarchy.
- No PowerUser suspension, reapplication or permanent-revocation workflow.

## Test Expectations

At minimum:

- schema validation tests for shared enums and cross-field rules
- feature parity tests for header/run-page render lists from registry
- feature visibility tests from backend + prerequisites + role
- discoverable-disabled tests for menu role, authorization reason,
  prerequisites, active legacy cleanup, and dynamic prerequisite activation
- parity tests proving entries without `menu_min_role` retain existing
  role/backend/prerequisite hiding, including RUSLE
- schema negatives for unknown `menu_min_role` and for a menu audience that is
  not a superset of the enable audience
- config launch-surface render tests from registry data in `interfaces.htm`
- toggle endpoint behavior parity for visible features

## Post-fire debris-flow production increment

The 2026-09-15 owner-authorized report increment adds a **View likelihood report**
link within the existing eligible control, including the never-run state. It
does not add a registry option or change roles, enabling, prerequisites or
backend/locale gates. Authorized direct report inspection remains available for
retained results after the mod is disabled. Run access is always enforced.
See the [report contract](../../../docs/ui-docs/contracts/postfire-debris-flow-report-contract.md#exact-read-interface--2026-09-15).
Implementation conformance is pending its standalone checkpoint.

The postfire_debris_flow feature is preview, requires user role and WBT, requires
Disturbed and enables RUSLE (and its existing POLARIS dependency). No upstream
build occurs on enabling. Effective CONUS locale eligibility comes from run
capability authority, not registry labels. Eligible absent optional NoDb state
renders the upload/run control. See the [production M1 contract](../../nodb/mods/postfire_debris_flow/docs/production_m1.md#execution-contract-2026-09-10)
and [UI contract](../../../docs/ui-docs/contracts/postfire-debris-flow-control-contract.md).
Runtime registration/conformance is pending the production package checkpoint.

## Kf source amendment — 2026-09-16

Status: accepted 2026-09-16 after two independent reviews; implementation
conformance verified on forest, 2026-09-16. The [Kf source/runtime contract](../../nodb/mods/postfire_debris_flow/docs/kf_source.md)
is the controlling amendment for new production M1.

Postfire keeps disturbed, user role, preview, WBT and CONUS constraints. Its enable_dependencies becomes empty; enabling postfire must no longer enable POLARIS or RUSLE. Existing enabled standalone features remain enabled. The runtime YAML change belongs after the ancestor checkpoint; current YAML still implements the earlier dependency behavior.
Earlier conflicting requirements remain the historical/legacy contract only
once this checkpoint is accepted; do not reinterpret old accepted artifacts.

Kf cutover acceptance also covers the immediate browser state: removing RUSLE
must retain the enabled postfire controller/report link before and after reload.
Remove the postfire POLARIS/RUSLE frontend propagation rule together with the
registry dependency metadata; neither is a substitute for the other.

## Single User-Defined Builder exception (2026-09-25)

SUDI-01, [Single User-Defined inputs](../../../docs/schemas/single-user-defined-inputs-contract.md), defines the bounded creation-time exception to ordinary
Builder Disturbed support and adds independent mode5 landuse/soil uploads.
Checked projects exclude Disturbed/SBS and their dependent features across UI,
activation and direct execution, and disable buffer geometry and management
overrides. Unchecked/legacy behavior remains unchanged. The checkbox does not
select an input mode. Preserve the option through capability refresh and preserve
accepted sources across rebuilds/mode switches. Compatible cover/soil modifiers
retain their existing precedence on generated copies; all non-buffer OFEs receive
the selected single source. Existing authorization, response, persistence and
controller invariants remain in force. This explicit exception governs where
earlier unconditional Disturbed statements conflict; no other defaults change.
Implementation conformance is pending the SUDI-01 checkpoint and validation.
