# WEPPcloud Feature and Config Registry Implementation

**Status**: Open (2026-05-21)  
**Timezone**: UTC

## Overview

This package implements a single authority boundary under `wepppy/weppcloud/feature_registry/` with two registries:

- `feature_registry` for run-page/header capabilities.
- `config_registry` for launchable interfaces/configs.

The goal is to remove duplicated hardcoded metadata across routes/templates and make lifecycle labels (`stable`, `preview`, `experimental`, `deprecated`, `internal`) consistent for both features and configs.

The package is MVP-first and keeps metadata minimal. It explicitly does not add separate `enable_roles`.

## Objectives

- Implement canonical registry contract/runtime under `wepppy/weppcloud/feature_registry/`.
- Remove hardcoded feature metadata duplication from backend routes/templates.
- Remove hardcoded interface-config launch metadata from `interfaces.htm` and related route context.
- Drive maturity labels/badges from registry data for both feature and config surfaces.
- Enforce UX rule: visible implies usable (except `readonly` on existing run surfaces).
- Add regressions for registry validation, policy decisions, and rendered availability.

## Scope

### Included

- Registry data contracts and runtime loader implementation aligned to:
  - `wepppy/weppcloud/feature_registry/specification.md`
- Feature consumer adoption in:
  - `wepppy/weppcloud/routes/nodb_api/project_bp.py`
  - `wepppy/weppcloud/routes/run_0/run_0_bp.py`
  - `wepppy/weppcloud/templates/header/_run_header_fixed.htm`
  - `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`
  - `wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2`
- Config consumer adoption in:
  - `wepppy/weppcloud/routes/weppcloud_site.py`
  - `wepppy/weppcloud/templates/interfaces.htm`
- Focused backend/frontend regression updates.

### Explicitly Out of Scope

- New NoDb runtime feature state model.
- New auth model or role model redesign.
- Large redesign of run-page IA/layout.
- Non-WEPPcloud service adoption (for example `preflight2` or external services) beyond consumer hooks needed by WEPPcloud.

## Implementation Fidelity and Evidence (Required for modernization/migrations)

- **Fidelity target**: `faithful extraction`
- **Authoritative source path(s)**:
  - `wepppy/weppcloud/routes/nodb_api/project_bp.py` (`MOD_DISPLAY_NAMES`, dependency/guard semantics)
  - `wepppy/weppcloud/routes/run_0/run_0_bp.py` (`MOD_UI_DEFINITIONS`, mod visibility)
  - `wepppy/weppcloud/templates/header/_run_header_fixed.htm` (`header_mod_options`)
  - `wepppy/weppcloud/templates/interfaces.htm` (hardcoded config launch cards/buttons)
- **Cutover proof required**:
  - Removed/reduced hardcoded duplicate metadata and replaced with registry-derived values at runtime.
  - Route/template behavior parity validated by existing and new regression tests.
- **Acceptance evidence type**: `both` (fixture-only tests + rendered output assertions where applicable)

## Stakeholders

- **Primary**: WEPPcloud users/operators consuming feature labels, mod toggles, and interface launch options.
- **Reviewers**: WEPPcloud route maintainers, controllers JS maintainers.
- **Security Reviewer**: Not required by triage for this package.
- **Informed**: usersum docs maintainers and NoDb module maintainers.

## Success Criteria

- [ ] Registry subsystem exists with both `feature_registry` and `config_registry` contracts plus validation.
- [ ] `project_bp` and `run_0_bp` consume `feature_registry` metadata for targeted policy decisions.
- [ ] Header mods menu and run-page mod surfaces render from `feature_registry` metadata/ordering.
- [ ] `interfaces.htm` launch options render from `config_registry` metadata/ordering instead of hardcoded config entries.
- [ ] User-facing maturity labels (including `internal` reason context) are rendered from registry data on targeted surfaces.
- [ ] Regression tests pass for route policy, template rendering, and JS integration on touched surfaces.
- [ ] Documentation is updated and linked from this package, including implementation/contract decisions.

## Dependencies

### Prerequisites

- Existing spec document:
  - `wepppy/weppcloud/feature_registry/specification.md`
- Classification guidance source:
  - `wepppy/weppcloud/routes/usersum/weppcloud/user-guide.md` (`Feature Maturity Labels`)
- Existing coverage baseline for touched areas:
  - `tests/weppcloud/routes/test_project_bp.py`
  - `tests/weppcloud/routes/test_pure_controls_render.py`
  - `wepppy/weppcloud/controllers_js/__tests__/project.test.js`

### Blocks

- Future work that adds new feature toggles or interface configs should depend on these registries to avoid reintroducing duplication.

## Related Packages

- **Related**: [20260401_usersum_docs_engine](../20260401_usersum_docs_engine/package.md)
- **Related**: [20260408_usersum_role_filter](../20260408_usersum_role_filter/package.md)

## Timeline Estimate

- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium-High.
- **Risk level**: Medium (cross-surface contract unification across routes/templates/tests).

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Changes centralize existing visibility/label policy and launch metadata; no new auth/token/secrets/egress surface is introduced.
- **Security review artifact**: `N/A`

## References

- `wepppy/weppcloud/feature_registry/specification.md`
- `wepppy/weppcloud/routes/nodb_api/project_bp.py`
- `wepppy/weppcloud/routes/run_0/run_0_bp.py`
- `wepppy/weppcloud/templates/header/_run_header_fixed.htm`
- `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`
- `wepppy/weppcloud/routes/weppcloud_site.py`
- `wepppy/weppcloud/templates/interfaces.htm`
- `wepppy/weppcloud/routes/usersum/weppcloud/mods-overview.md`
- `wepppy/weppcloud/routes/usersum/weppcloud/user-guide.md` (`Feature Maturity Labels`)

## Deliverables

- Registry implementation files under `wepppy/weppcloud/feature_registry/`:
  - `feature_registry` data
  - `config_registry` data
  - shared schema + runtime helpers
- Route/template consumers migrated to registry metadata for targeted surfaces.
- Regression tests for registry + consumer parity.
- Work-package execution artifacts and closure notes.

## Follow-up Work

- Add registry-backed tooling for changelog/release-note generation by maturity transitions.
- Consider extending registry consumption to additional WEPPcloud surfaces after this package closes.

## Kickoff Prompt

- Active ExecPlan: `docs/work-packages/20260521_feature_registry/prompts/active/feature_registry_execplan.md`
