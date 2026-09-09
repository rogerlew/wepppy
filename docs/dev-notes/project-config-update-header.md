# Project configuration update header

## Legacy-run notice restoration (2026-09-09)

The operator reported a non-actionable manifest warning on the legacy
`downright-houri/portland-10-mofe` run and requested its removal.
This is a conformance fix against the unchanged
[project-owned config contract](../schemas/project-owned-config-contract.md),
sections 5.1 (flattened-config updates), 6.1 (flattened-config provenance
warnings), and 6.2 (legacy loading).

The header must use `current_ron.project_config_status.mode` to render the
configuration-update widget and modal only for `flattened` projects.
At the operator's request, `RonViewModel` exposes this reader status after
explicitly resolving the config: detached controllers do not retain the status,
and copying its uninitialized default would incorrectly hide flattened updates.
Legacy projects do not require a manifest, so they must not initiate an update
availability check or display a manifest warning. Merely checking manifest
existence would also hide required warnings for damaged flattened projects.

Compatibility: no configuration, manifest, NoDb state, API, or model artifact
changes. Legacy runs omit the inactive workflow; flattened projects retain it
whether their manifest is valid, missing, empty, malformed, or unreadable.
Existing update authorization and validation remain authoritative.

Regression evidence uses a cold real Ron controller, the config reader, and
`RonViewModel`: render the legacy header without the controller root,
availability URL, or modal; retain the accessible flattened-project workflow
with valid, missing, empty, and malformed manifests. Run the existing
header/template suite and independently review the bounded patch before handoff.

Validation: 244 focused Python tests passed, 3 skipped; all 835 JavaScript
tests, npm lint, Ron stubtest, test-stub completeness, documentation lint, and
changed-file broad-exception checks passed. Independent correctness review
closed with no unresolved findings after replacing synthetic header status
with real reader/view-model coverage and removing shared test-environment
mutation. The full `tests --maxfail=1` run was stopped in the unrelated
100-year disturbed-soil simulation matrix; it is not a completed full-suite
gate. No production deployment or browser verification was performed.
