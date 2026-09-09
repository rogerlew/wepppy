# M3 Soil Evidence Catalog

Planned artifacts, not completed evidence:

- `source_inventory.csv`: project/source availability, map units, revisions,
  provenance, substitutions, acquisition needs, and fixture paths/hashes.
- `soil_contract.md`: original THICK semantics and resolved SSURGO derivation.
- `study_protocol.md`: fixed terrain panel, diagnostic inputs, comparison
  metrics, coverage rules, and criteria recorded before interpreting results.
- `interval_audit.csv`, `component_audit.csv`, `catchment_coverage.csv`: auditable
  records of inclusions, exclusions, missing support, and aggregation.
- `source_comparison.csv`, `m3_sensitivity.csv`, plots, and `soil_decision.md`:
  paired thickness/model effects and the scientific source recommendation.
- `validation.md` and dated correctness/security reviews: exact commands,
  generated artifacts, regression evidence, findings, and closure.

Version minimal deterministic input fixtures under the applicable WEPPpy test
tree, following its AGENTS and storage conventions. Retain public source
metadata and hashes. Prefer a minimal component/horizon/map-unit subset to
copying complete project SQLite databases. Large generated products remain in
an isolated study workspace with reproducible recipes. The terrain fixture
panel is already committed in the sibling WBT repository; do not duplicate it.
