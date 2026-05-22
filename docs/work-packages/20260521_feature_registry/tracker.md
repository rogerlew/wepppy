# Tracker - WEPPcloud Feature and Config Registry Implementation

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-05-22 02:12 UTC  
**Current phase**: Implementation complete; validation complete  
**Last updated**: 2026-05-22 04:15 UTC  
**Next milestone**: Package closeout review and optional follow-on cleanup  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog

- [x] Implement `feature_registry` and `config_registry` runtime contracts (data files, schema validation, loader/query helpers).
- [x] Replace route-level duplicated feature labels/policy with `feature_registry` consumption in `project_bp.py`.
- [x] Replace run-page duplicated feature metadata with `feature_registry` consumption in `run_0_bp.py` and header template consumers.
- [x] Replace hardcoded interface config launch values/labels in `interfaces.htm` with `config_registry`-driven rendering hooks.
- [x] Add maturity badge rendering in targeted UI/doc surfaces from registry data.
- [x] Add/update regressions for policy parity and rendering behavior.
- [x] Update docs and close out package artifacts.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Work package scaffolded (`package.md`, `tracker.md`, active ExecPlan path defined) (2026-05-22 02:12 UTC).
- [x] Initial feature-registry specification authored at `wepppy/weppcloud/feature_registry/specification.md` and linked into package references (2026-05-22 02:12 UTC).
- [x] Added package entry to `PROJECT_TRACKER.md` Backlog (2026-05-22 02:12 UTC).
- [x] Scope update: keep one work-package and add `config_registry` alongside `feature_registry` with shared maturity policy (2026-05-22 03:05 UTC).
- [x] Added maturity-label definitions to usersum user guide and linked them from the package + ExecPlan (2026-05-22 03:18 UTC).

## Timeline

- **2026-05-22 02:12 UTC** - Package created and scoped.
- **2026-05-22 02:12 UTC** - Tracker initialized with initial task board and risk register.
- **2026-05-22 02:12 UTC** - Active ExecPlan authored for implementation execution.
- **2026-05-22 03:05 UTC** - Package expanded to dual-registry MVP (`feature_registry` + `config_registry`) in same execution stream.
- **2026-05-22 03:18 UTC** - Maturity label classification definitions published in user guide and referenced by package artifacts.
- **2026-05-22 04:15 UTC** - Dual registries implemented and wired to targeted routes/templates with regression coverage.

## Decisions Log

### 2026-05-22 02:12 UTC: Use backend-owned registry as single authority
**Context**: Feature metadata currently exists in multiple locations across backend and templates, creating drift risk.

**Options considered**:
1. Keep metadata in templates/routes and add conventions only.
2. Put metadata in usersum docs manifest and read from docs layer.
3. Create a backend-owned `feature_registry` contract and make routes/templates consume it.

**Decision**: Option 3.

**Impact**: One canonical source controls lifecycle labels and policy semantics; reduces duplication and drift.

### 2026-05-22 02:19 UTC: Keep registry MVP minimal; remove separate `enable_roles`
**Context**: Showing features users cannot use is a known UX frustration. We need a direct rule: visible means usable.

**Options considered**:
1. Keep separate `enable_roles` in schema.
2. Remove `enable_roles`; derive usability from visibility + run prerequisites + readonly.

**Decision**: Option 2.

**Impact**: Simpler contract, less policy duplication, and no tease-only controls outside readonly state.

### 2026-05-22 03:05 UTC: Keep feature and config registries together in one work-package
**Context**: Interface configs (for example `disturbed9002`, `disturbed9002_wbt`, `reveg`) also need maturity labeling and visibility policy.

**Options considered**:
1. Create a second package for config lifecycle metadata.
2. Keep a single package with two registries and shared maturity semantics.

**Decision**: Option 2.

**Impact**: Prevents duplicated policy plumbing, keeps release/maturity semantics aligned, and ships one cohesive contract boundary.

### 2026-05-22 03:18 UTC: Use user guide as maturity-classification authority
**Context**: Registry implementation required explicit, user-visible guidance for assigning maturity labels before coding.

**Options considered**:
1. Keep maturity semantics only in spec/work-package internals.
2. Publish maturity semantics in usersum user guide and reference them from package artifacts.

**Decision**: Option 2.

**Impact**: Classification criteria are visible to users and maintainers, and implementation has one explicit guidance source.

### 2026-05-22 04:15 UTC: Ship dual-registry runtime and consumers
**Context**: Package implementation needed to move from documentation/spec into runtime-enforced registry consumption.

**Options considered**:
1. Keep implementation scope docs-only and defer runtime adoption.
2. Implement runtime registries now and migrate targeted consumers in same package execution.

**Decision**: Option 2.

**Impact**: Registry metadata now drives feature labels/dependencies and interface config maturity presentation in targeted user-facing surfaces.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Behavior regressions while replacing hardcoded feature maps | Medium | Medium | Parity-first migration and focused regression suite before removing legacy maps | Open |
| Behavior regressions while replacing hardcoded interface cards/buttons | Medium | Medium | Migrate launch surfaces in small slices with render tests | Open |
| Hidden coupling between template booleans and route context | Medium | Medium | Migrate in small slices with render tests for each surface | Open |
| Reintroduction of duplicate metadata in new code paths | Medium | Medium | Enforce registry-first rule in package docs and tests | Open |
| Ambiguous lifecycle semantics for `internal` features/configs | Low | Medium | Require `internal_reason` and explicit user-facing copy rules | Open |

## Verification Checklist

### Code Quality
- [x] Targeted WEPPcloud route tests pass.
- [ ] Frontend/controller JS tests pass for touched behavior.
- [x] No new lint/type regressions in touched modules.

### Security
- [x] Security impact triage recorded (`low`) with rationale.
- [x] Dedicated security artifact not required.
- [ ] Authorization and role-based visibility behavior remains regression tested on touched routes/templates.

### Documentation
- [x] Package docs scaffolded (`package.md`, `tracker.md`, active ExecPlan).
- [x] Contract docs updated to dual-registry MVP schema.
- [x] `PROJECT_TRACKER.md` updated at significant lifecycle transitions.

### Testing
- [x] New/updated tests cover dual-registry validation and consumer parity.
- [x] Existing route/template regressions remain green.
- [ ] Manual sanity check for run-header mods, run-page visibility, and interfaces config launch availability completed.

## Progress Notes

### 2026-05-22 02:12 UTC: Package Authoring Session
**Agent/Contributor**: Codex

**Work completed**:
- Created package brief and tracker for feature registry implementation.
- Defined success criteria, scope boundaries, and initial risk register.
- Authored active ExecPlan path and package kickoff linkage.
- Registered package in `PROJECT_TRACKER.md`.

**Blockers encountered**:
- None.

**Next steps**:
- Implement registry contract/runtime loader.
- Wire first backend consumer with parity tests before broader migration.
- Continue milestone execution per active ExecPlan.

**Test results**:
- Docs scaffolding only; implementation tests not run in this session.

### 2026-05-22 02:19 UTC: MVP Schema Simplification
**Agent/Contributor**: Codex

**Work completed**:
- Updated feature registry specification to MVP schema.
- Removed `enable_roles` from the contract.
- Added explicit UX policy: visible implies usable except readonly.
- Aligned package docs with MVP-first scope.

**Blockers encountered**:
- None.

**Next steps**:
- Implement registry files exactly to MVP schema.
- Migrate first backend/template consumers with parity tests.

**Test results**:
- Docs-only changes; implementation tests not run in this session.

### 2026-05-22 03:05 UTC: Dual-Registry Scope Update
**Agent/Contributor**: Codex

**Work completed**:
- Expanded specification from single feature registry to dual-registry model.
- Added `config_registry` contract for interface configs and shared maturity policy.
- Updated package scope/task board to implement `feature_registry` and `config_registry` in one stream.

**Blockers encountered**:
- None.

**Next steps**:
- Implement registry files (`feature_registry.yaml`, `config_registry.yaml`) and shared schema/runtime loader.
- Migrate `interfaces.htm` render data from hardcoded launch entries to `config_registry`.

**Test results**:
- Docs-only changes; implementation tests not run in this session.

### 2026-05-22 03:18 UTC: Maturity Label Definitions
**Agent/Contributor**: Codex

**Work completed**:
- Added a prominent `Feature Maturity Labels` section in usersum user guide with definitions for `stable`, `preview`, `experimental`, `deprecated`, and `internal`.
- Added explicit classification rules (least-optimistic label, no premature `stable`, visible implies usable except readonly).
- Referenced the user-guide section from package prerequisites/references and ExecPlan acceptance criteria.

**Blockers encountered**:
- None.

**Next steps**:
- Implement registry entries using these definitions as the classification authority.

**Test results**:
- Docs-only changes; implementation tests not run in this session.

### 2026-05-22 04:15 UTC: Runtime + Consumer Implementation
**Agent/Contributor**: Codex

**Work completed**:
- Added registry runtime and validation modules under `wepppy/weppcloud/feature_registry/` with dual YAML authorities.
- Migrated `project_bp.py` mod label/dependency/disable-guard metadata to `feature_registry`.
- Migrated `run_0_bp.py` mod UI definition source and header mod options to `feature_registry`.
- Migrated `weppcloud_site.interfaces` and `interfaces.htm` launch config values and maturity badges to `config_registry`.
- Added registry-focused regression coverage and template badge rendering tests.

**Blockers encountered**:
- None.

**Next steps**:
- Optional: widen run-page nav/section label extraction from hardcoded template literals to registry-driven labels in a follow-on cleanup.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_feature_registry_runtime.py tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/routes/test_project_bp.py tests/weppcloud/routes/test_run_0_openet_admin_gate.py --maxfail=1`
- Result: 112 passed, 0 failed.
