# Uncapped-Spectacular totalwatsed3 Runoff Reconciliation

**Status**: Closed (2026-04-29)
**Timezone**: UTC

## Overview
This package resolves a runoff-depth aggregation defect in `totalwatsed3` where `Runoff` was derived from `QOFE` rather than watershed outlet runoff volume (`runvol`). The issue inflated daily runoff depths in MOFE runs and produced non-physical precipitation/runoff interpretations.

## Objectives
- Correct `Runoff` derivation in `totalwatsed3` to use `H.pass.runvol` over aggregated `Area`.
- Regenerate the production `uncapped-spectacular` `totalwatsed3.parquet` on `wepp1` without container restarts.
- Create a repeatable daily-closure audit tool and run it against the refreshed production artifact.
- Capture production evidence as package artifacts.

## Scope

### Included
- `wepppy/wepp/interchange/totalwatsed3.py` runoff-depth calculation update.
- Regression coverage for runoff-depth semantics in `tests/wepp/interchange/test_totalwatsed3.py`.
- Repeatable audit CLI: `tools/totalwatsed3_daily_closure_audit.py` with unit tests.
- Production run refresh for:
  - `/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet`
- Production audit outputs captured in package artifacts.

### Explicitly Out of Scope
- Changes to WEPP physics, FORTRAN runoff generation, or baseflow process equations.
- Rerunning full WEPP hillslope/watershed simulations.
- Broad interchange README generation performance fixes.

## Stakeholders
- **Primary**: WEPP interchange/report maintainers, hydrology analysts.
- **Reviewers**: WEPPcloud operators and model QA analysts.
- **Security Reviewer**: Not required.
- **Informed**: Marta/Roger investigation thread participants.

## Success Criteria
- [x] `Runoff` in generated `totalwatsed3` equals `runvol / Area * 1000`.
- [x] Production `uncapped-spectacular` parquet regenerated in place on `wepp1`.
- [x] No container restart/takedown required for regeneration.
- [x] Repeatable daily closure audit tool added, tested, and executed on refreshed parquet.
- [x] Work-package artifacts include production path and audit evidence.

## Dependencies

### Prerequisites
- Existing `H.pass.parquet` and `H.wat.parquet` for `uncapped-spectacular`.
- Production `wepp1` operational access.

### Blocks
- None.

## Related Packages
- **Related**: [20260428_wepp_interchange_dependency_race_guard](../20260428_wepp_interchange_dependency_race_guard/package.md)

## Timeline Estimate
- **Expected duration**: single focused session.
- **Complexity**: Medium.
- **Risk level**: Medium (production data refresh).

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: data derivation/reporting correction and production file refresh; no auth/session/egress surface changes.
- **Security review artifact**: `N/A`

## References
- `wepppy/wepp/interchange/totalwatsed3.py` - authoritative runoff-depth derivation.
- `tests/wepp/interchange/test_totalwatsed3.py` - runoff regression assertions.
- `tools/totalwatsed3_daily_closure_audit.py` - repeatable audit tool.
- `docs/work-packages/20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation/artifacts/2026-04-29_wepp1_artifact_manifest.md` - production evidence and path manifest.

## Deliverables
- Runoff basis fix (`Runoff <- runvol/Area*1000`) with tests/docs updates.
- New repeatable audit tool and unit coverage.
- Regenerated production parquet:
  - `/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet`
- Production audit outputs:
  - `artifacts/2026-04-29_uncapped_spectacular_daily_closure_audit_summary.json`
  - `artifacts/2026-04-29_uncapped_spectacular_daily_closure_audit_top_days.csv`

## Closure Notes

**Closed**: 2026-04-29

**Summary**: Implemented and validated the runoff derivation correction, then surgically patched runtime code in `weppcloud` on `wepp1` (with backups) and regenerated `uncapped-spectacular` `totalwatsed3.parquet` without stopping containers. Post-refresh verification confirmed exact runoff consistency (`max abs Runoff - runvol/Area*1000 = 0.0`). The new repeatable closure-audit tool was run against the refreshed parquet and artifacts were captured.

**Lessons Learned**: `Wepp._build_totalwatsed3()` couples data rebuild with `generate_interchange_documentation()`, which scans multi-GB parquet inputs and is expensive for production hotfixes. For targeted regeneration, invoking `run_totalwatsed3(...)` directly is operationally safer.

**Archive Status**: Evidence artifacts retained under `artifacts/` and include the explicit wepp1 parquet path and audit outputs.
