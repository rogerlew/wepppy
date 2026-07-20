# Omni Mod State Synchronization Contract Decision

**Status**: Accepted; implementation conformance pending
**Decision time**: 2026-07-20 21:08 UTC
**Starting implementation revision**: `a0c21b8727ca6b10c9dc1946087473d793a3554b`
**Registered owner**: REM-01, borrowing only the listed DOM-02/DOM-25A/DOM-25B boundaries
**Operator approval**: Explicitly granted on 2026-07-20 21:23 UTC for GOV-00A expansion, ratification, implementation, tests, and remediation-package completion.

## Applicable Authority

- `docs/adrs/ADR-0001-time-limited-publication-embargo-for-omni-contrasts.md`, especially the accepted decision that Omni Scenarios and Omni Contrasts are gated independently.
- `wepppy/weppcloud/feature_registry/specification.md`, governing role/backend visibility, prerequisites, persisted mod state, and UI consumption.
- `wepppy/weppcloud/feature_registry/feature_registry.yaml`, preserving `omni_contrasts` as `internal`, `min_role: dev`, and `requires_features: [omni]`.

No authorized-flow RQ response/payload/queue behavior, CSRF, output-scope, NoDb concurrency, or
feature-export manifest contract changes apply. The existing contrast RQ entry
points are in scope only to enforce the same Dev/Root authorization boundary
already governing contrast activation. The CAP-gated contrast report is in
scope only to add canonical run access and that Dev/Root boundary.

## Discrepancy Classification

Dual review determined this is an intended behavior change, not a strict
conformance restoration. The accepted ADR requires independent maturity/access
gating, but the current feature-registry specification explicitly makes active
prerequisites a visibility condition. The requested discoverability behavior
therefore changes normative registry semantics even though it preserves the
embargo, role gate, backend policy, data contract, and RQ behavior.

## Normative Delta

The feature-registry contract distinguishes menu discoverability from enablement and active rendering:

- `menu_min_role: user` makes Omni Contrasts visible in the Mods menu to every user;
- callers below `min_role: dev` receive a disabled checkbox with the exact reason `Not Authorized` directly below its label;
- authorized callers missing `omni` receive a disabled unchecked checkbox with `Enable Omni Scenarios first`;
- `requires_features` is validated when enabling and does not auto-enable the dependent option;
- only `enable_dependencies` may add other persisted mods automatically;
- checkbox `checked` means only that the feature's own id is in the authoritative
  persisted mod list;
- checkbox `enabled` requires authorization and satisfied prerequisites, except
  that an authorized already-active legacy feature remains enabled for cleanup;
- section, preflight navigation, and dynamic loading require the feature's own
  persisted id, its persisted prerequisites, authorization, a usable shared
  controller, and a non-child run;
- contrast-result bootstrap metadata is false for callers/runs where the
  contrast section is not authorized and active; and
- contrast run, dry-run, and delete entry points require Dev or Root in
  addition to their existing JWT scope and run-access boundaries; the report
  requires CAP, canonical run access, and Dev or Root.

Enabling `omni` may add its declared `treatments` dependency, but it must never add `omni_contrasts`. When `omni` becomes active, an authorized contrast checkbox becomes enabled but remains unchecked; the contrasts section and preflight entry remain inactive. Explicitly enabling `omni_contrasts` still requires `omni`. Disabling `omni` while contrasts is active must be rejected so persisted state cannot violate that prerequisite.

## Rationale and Rejected Alternatives

Independent state matches the accepted embargo ADR and the presence of two registry ids and two user-facing checkboxes. A combined toggle was rejected because it prevents users from running scenarios without internal contrast analysis. Auto-enabling contrasts was rejected because it violates explicit user intent and the publication-embargo boundary. Hiding contrasts until scenarios is active was rejected because authorized users need consistent feature discoverability and because it made the option appear to be implicitly created by the scenarios action.

## Compatibility Impact

The change is backward compatible for valid run states. Existing runs with only `omni` remain scenarios-only. Existing runs with both ids keep both controls. An authorized user may uncheck a legacy active contrast whose scenario prerequisite or shared controller file is missing; its active section/preflight may remain unavailable during cleanup, but the checked menu state and disable action remain available. New invalid states are prevented by enable and disable guards.

## Security Impact

Security impact is high because the package crosses registered authorization and persisted-state boundaries. The internal `min_role: dev` enable, dynamic-load, action, and report-data gates remain mandatory. Unauthorized users may see only the disabled menu option and `Not Authorized`; they must not enable, dynamically load, render the contrast section/preflight control, invoke contrast actions, receive contrast-result bootstrap metadata, or view contrast reports.

## Proposed Regression Evidence

- Registry/runtime/template: every user sees Omni Contrasts; ordinary users get disabled `Not Authorized`; authorized users without scenarios get disabled `Enable Omni Scenarios first`.
- Project endpoint: enabling Omni Scenarios does not add contrasts; enabling contrasts without scenarios fails; disabling scenarios while contrasts is active fails.
- Authorization: ordinary users cannot POST the contrasts toggle or GET its dynamic section, with no persisted or active-DOM mutation.
- Action/data authorization: User, PowerUser, and Admin contrast run, dry-run,
  delete, and report requests are rejected before domain mutation/read; Dev and
  Root retain their valid RQ flows only with existing JWT scope and run access;
  the report retains CAP and requires newly added canonical run access.
- Role matrix: User, PowerUser, and Admin are denied POST/dynamic GET; Dev and
  Root are allowed when prerequisites and run authorization are satisfied.
- Legacy cleanup: persisted contrasts without scenarios, with and without the
  shared Omni state file, renders checked for an authorized user, keeps the
  section/preflight unavailable, permits disable, and remains removed after refresh.
- Server render/bootstrap: contrasts visibility and `runContext.mods.flags.omni_contrasts` follow only the contrasts persisted id.
- Project controller: explicit contrast enable loads its section and remounts the shared Omni controller; scenario enable leaves the contrasts checkbox/nav/section inactive.
- Targeted pytest and Jest suites plus frontend lint and controller bundle rebuild.

## Ratification Gate

The first dual review findings are accepted and resolved in the proposed
GOV-00A bounded cross-owner mechanism, REM-01 registration, high security
triage, explicit disabled-state contract, authorization tests, and legacy-state
semantics. A fresh pair of independent read-only reviews must approve these
amendments. Their findings and disposition must be committed in the standalone
ancestor before implementation begins.

Both reviewers approved the corrected ancestor after disposition with no
remaining high- or medium-severity findings. Implementation remains pending
until the standalone ancestor is committed.

The first final security review then found that direct contrast RQ and report
entry points did not enforce the ADR's Dev/Root action/data boundary. The
operator's direction to expand and complete REM-01 authorizes this finite
security scope amendment, but the new boundary must receive dual review and a
second standalone docs-only ancestor before those production routes are edited.
