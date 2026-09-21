# Standalone runner menu cleanup

Status: completed locally, not deployed. Scope: remove Culvert Runner and Batch Runner from the run-header
Mods menu only. No runner route, registry entry, saved state, permission,
deployment or push changes. No new metadata mechanism is needed for two fixed
standalone workflows.

Authority: feature registry specification, Standalone runners and the Mods menu.
User approved the menu removal and local checkpoint commit on 2026-09-21,
explaining that these workflows have no run-level UI controls.
See [decision](artifacts/20260921_contract_decision.md) and [tracker](tracker.md).

Outcome: three-line menu-only filter; 335 registry/render tests pass. Existing
standalone workflows and persisted mods are untouched. No push or deployment.
