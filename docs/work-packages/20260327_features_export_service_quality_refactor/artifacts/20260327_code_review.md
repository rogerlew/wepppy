# Code Review - Features Export Service Quality Refactor

Date: 2026-03-28  
Reviewer: Codex

## Scope Reviewed
- `wepppy/nodb/mods/features_export/service.py`
- `wepppy/nodb/mods/features_export/discovery.py`
- `wepppy/nodb/mods/features_export/column_selection.py`
- `wepppy/nodb/mods/features_export/cache_rehydration.py`
- `tests/nodb/mods/test_features_export_service.py`
- `wepppy/nodb/mods/features_export/specification.md`

## Findings
- No unresolved high findings.
- No unresolved medium findings.

## Closed During Package Execution
1. High (closed): carrier discovery path treated required missing/unsupported sources as warnings.
   - Fix: `discover_layer_sources()` now raises `MaterializationContractError` for required dependency/file/kind failures.
   - Service translation now returns canonical `materialization_error`.
2. Medium (closed): hidden join-key fallback in legacy merge path selected arbitrary non-geometry column.
   - Fix: `_ensure_join_key_column()` now requires explicit contract candidates (`primary_key`, `fallback_keys`, `feature_id_keys`) and fails explicitly when unresolved.
3. Medium (closed): broad exception swallow in touched service path.
   - Fix: replaced with narrow handling and collaborator extraction; changed-file broad-catch check reports net delta `-1`.

## Regression/Contract Coverage Added
- Required-source failure branches (dependency missing, file missing, unsupported kind, unresolved join).
- Join-key contract enforcement and fallback-key selection.
- Malformed cache-layer output fallback behavior.
- Carrier required-source strictness behavior.

## Residual Risk
- `service.py` remains a large file and still benefits from additional phased decomposition, but this package removed the identified contract-quality blockers and stabilized behavior.
