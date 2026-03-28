# Code Review - Features Export Service Compliance Refactor

Date: 2026-03-28  
Reviewer: Codex

## Scope
- `wepppy/nodb/mods/features_export/service.py`
- `wepppy/nodb/mods/features_export/discovery.py`
- `wepppy/nodb/mods/features_export/legacy_source_materializer.py`
- `wepppy/nodb/mods/features_export/carrier_layer_materializer.py`
- `tests/nodb/mods/test_features_export_service.py`

## Findings
- No unresolved high findings.
- No unresolved medium findings.

## Resolved QA Items
1. Legacy source-materialization extracted and policy duplication removed by reusing strict discovery helper behavior.
2. `_materialize_export_payloads` carrier branch complexity reduced by collaborator delegation.
3. Dead wrappers removed from `service.py`.
4. Missing strict-required carrier branch tests added.

## Residual Risk
- `service.py` remains a relatively large file, but medium-severity maintainability and branch-coverage issues identified by QA are now closed.
