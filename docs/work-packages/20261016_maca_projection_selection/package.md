# MACA projection selection

Implement the requested model/scenario control and CCSM4 source-member patch.
Scope is one additive selection field, existing climate UI/build/client seams,
validation and documentation. Preserve scientific transformations and current
GFDL-ESM2G/RCP8.5 default. No queues, dependencies, services, privilege changes,
publication refactors or deployments. Complexity budget: one pure registry,
bounded existing-file changes and regression tests.

Security impact: low. User-selected identifiers enter an existing outbound
request; an exact allowlist prevents arbitrary URL/path construction. No new
endpoint or authorization surface; a dedicated high-impact security artifact is
not required. Independent reviews cover the allowlist and valid-state behavior.

Acceptance: saved and displayed choice reaches actual source URLs and generated
PRN/CLI values. Bounded live CCSM4 acquisition/native generation is required;
full model-period and production deployment claims are excluded.

Execution uses `prompts/active/maca_projection_execplan.md`; canonical authority
is `docs/schemas/maca-cmip5-selection-contract.md` and ADR-0097. Checkpoint and
reviews are under `artifacts/`. Prior working-tree changes remain separate.
