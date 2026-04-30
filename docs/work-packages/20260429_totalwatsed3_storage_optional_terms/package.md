# totalwatsed3 Storage and Optional Terms Contract Hardening

**Status**: Production rollout gate completed on wepp1; residual closure issue documented (2026-04-30)  
**Timezone**: UTC

## Overview
`totalwatsed3` closure diagnostics for `uncapped-spectacular` show that runoff depth consistency is now fixed, but water-balance interpretation is still ambiguous because storage terms are not explicit enough for full-profile accounting and legacy columns are easy to misread (`TSW` in `H.soil` is a shallow-layer diagnostic, while `Total-Soil Water` in `H.wat` is full-profile unfrozen storage).

This package defines and implements additive optional terms so storage and runoff partition interpretation is explicit, backward-compatible, and auditable across legacy and updated WEPP outputs.

## Objectives
- Add explicit, full-profile storage/capacity terms in `H.wat` using WEPP-aligned names and `mm` units:
  `SoilWaterTotal`, `ProfileDepth`, `ProfilePorosityCap`, `ProfileFCStore`, `ProfileWPStore`.
- Preserve backward compatibility: legacy runs without new columns must still parse and aggregate successfully.
- Prefer producer-authoritative WEPP values for optional storage/capacity terms; `wepppy` only parses/passes through when available.
- Keep `totalwatsed3` additive-only by ingesting optional columns when present (`TSMF`, `QRain`, `QSnow`, and new storage/capacity terms).
- Make closure auditing reproducible and whole-run comparable before/after optional-term rollout.
- Codify the output contract in docs/specs so operators can interpret runoff and storage terms without source-code archaeology.

## Scope
Cross-repository contract work spanning WEPP-forest output writers and WEPPpy interchange/aggregation consumers.

### Included
- WEPP-forest (`/workdir/wepp-forest`) additive `H.wat` output columns for full-profile storage observability:
  `SoilWaterTotal`, `ProfileDepth`, `ProfilePorosityCap`, `ProfileFCStore`, `ProfileWPStore`.
- WEPPpy parser hardening for optional trailing columns in hillslope interchange readers.
- WEPPpy `totalwatsed3` schema and aggregation updates for optional terms and null-safe behavior.
- Daily closure audit updates and regression tests for both legacy and enriched schemas.
- Documentation updates across interchange specs and README semantics.

### Explicitly Out of Scope
- Changes to WEPP runoff physics or subsurface process equations.
- Replacing existing user-visible columns in a non-backward-compatible way.
- Full reruns of every historical production run.
- UI/report redesign outside data-contract wiring and term semantics.

## Stakeholders
- **Primary**: WEPP interchange/report maintainers and hydrology analysts.
- **Reviewers**: WEPP-forest maintainers, WEPPcloud operators.
- **Security Reviewer**: Not required for this scope.
- **Informed**: Marta/Roger investigation participants.

## Success Criteria
- [x] New `H.wat` storage/capacity terms (`SoilWaterTotal`, `ProfileDepth`, `ProfilePorosityCap`, `ProfileFCStore`, `ProfileWPStore`) are emitted as additive optional columns with documented `mm` units and derivations.
- [x] WEPPpy hillslope interchange parsers accept both legacy and enriched layouts, including legacy executables (for example `wepp_dcc52a6`) that omit optional columns.
- [x] `totalwatsed3` exposes all five optional storage/capacity terms directly (`SoilWaterTotal`, `ProfileDepth`, `ProfilePorosityCap`, `ProfileFCStore`, `ProfileWPStore`) when present and nulls when absent.
- [x] Closure audit can report both legacy and enriched-storage closure statistics across the whole run.
- [x] `uncapped-spectacular` re-audit is captured as required production rollout-gate evidence, including independent hillslope reconciliation for `H2637` and `H2809`.
- [x] Specs/docs/tests are updated in the same change set.

## Dependencies

### Prerequisites
- Existing runoff correction package closed: [20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation](../20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation/package.md).
- Access to `uncapped-spectacular` artifacts for before/after audit comparison:
  - `/geodata/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet`

### Blocks
- None for this package. Production evidence was captured on wepp1 because the run is not mounted in the local workspace.

## Related Packages
- **Related**: [20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation](../20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation/package.md)
- **Follow-up**: Optional package for report-level UX surfacing of newly available terms if needed.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium-High.
- **Risk level**: Medium (cross-repo output contract evolution with production audit implications).

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: Output-schema and aggregation semantics only; no auth/session/secrets/new ingress surface changes.
- **Security review artifact**: `N/A`

## Hardening and Callus Softening (Required for incident/remediation packages)
- **Failure signature(s)**:
  - Apparent non-physical daily closure residual spikes despite runoff basis correction.
  - Misinterpretation risk from similarly named but semantically different storage terms (`TSW` vs `Total-Soil Water`).
- **Related prior hardening efforts**:
  - [20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation](../20260429_uncapped_spectacular_totalwatsed3_runoff_reconciliation/package.md)
- **Health signals**:
  - Reduced ambiguity in closure audit interpretation.
  - Stable parser behavior across legacy and enriched output files.
  - Clear operator guidance on which columns represent full-profile storage vs diagnostic surrogates.
- **Danger signals**:
  - Header/schema drift causing interchange parse failures.
  - Non-additive contract changes that break existing run consumers.
- **Observation window**: 14 days after deployment of enriched outputs.
- **Temporary calluses introduced**: Legacy fallback/null semantics for optional columns retained until all active binaries emit enriched terms.
- **Callus softening hypothesis (if applicable)**: After observation confirms complete rollout and no legacy producers, fallback-only pathways can be reduced in a dedicated cleanup package.

## References
- `/workdir/wepp-forest/src/watbal.for` - full-profile `watcon`/`frozwt` accounting and `TSMF` derivation.
- `/workdir/wepp-forest/src/watbal_hourly.for` - hourly-equivalent storage and `TSMF` derivation path.
- `/workdir/wepp-forest/src/watbalprint.for` - watershed `ivers=3` WAT row writer.
- `/workdir/wepp-forest/src/outfil.for` - hillslope output header definitions for wat/soil/element files.
- `/workdir/wepppy/wepppy/wepp/interchange/hill_wat_interchange.py` - strict WAT header parsing and schema mapping.
- `/workdir/wepppy/wepppy/wepp/interchange/hill_soil_interchange.py` - SOIL layout handling including `TSMF`.
- `/workdir/wepppy/wepppy/wepp/interchange/hill_element_interchange.py` - optional `QRain`/`QSnow` parsing.
- `/workdir/wepppy/wepppy/wepp/interchange/totalwatsed3.py` - watershed daily aggregator contract.
- `/workdir/wepppy/tools/totalwatsed3_daily_closure_audit.py` - repeatable closure audit.
- `/workdir/wepppy/docs/dev-notes/totalwatsed-interchange.spec.md` - normative totalwatsed spec and column semantics.

## Deliverables
- WEPP-forest output contract update proposal and implementation patch for additive optional storage/capacity terms.
- WEPPpy interchange parser compatibility updates and regressions.
- `totalwatsed3` optional-term ingestion updates with schema/docs/tests.
- Closure-audit artifacts (summary + top-days + whole-run closure comparison) for `uncapped-spectacular` after enriched-term rollout (blocked until run mount is available).

## Follow-up Work
- Optional report/API exposure of new storage/capacity terms if analysts need first-class downstream access.
- Optional retirement package for fallback branches once legacy producers are no longer in service.

## Closure Notes

**Closed**: 2026-04-30 04:09 UTC.

**Summary**: Parser, WEPP-forest producer output, `totalwatsed3`, audit tooling, docs, and tests are implemented. Production regeneration/audit completed on wepp1 without container takedown. The regenerated `totalwatsed3.parquet` exposes the optional columns and has hash `20f39d30280c9ccaf20754778e57c9e5595711ea334c8ffab82def2d89f68ca2`; the prior artifact is backed up as `totalwatsed3.parquet.bak.20260430T040509Z`.

**Review follow-up**: Independent review findings were addressed on 2026-04-30: `totalwatsed3` now supports production-shaped date-keyed `H.element.parquet` rows without `sim_day_index`, WEPP-forest `watbalprint.for` now matches the widened `ivers=3` WAT header, and validation commands were rerun successfully.

**Production findings**: Whole-run reconstructed closure with legacy storage is `-13,813.464759 mm` (`-16.855844%` of rain + melt), with max absolute daily closure `541.600205 mm` on 1996-02-06. H2637 closure with storage is `-119,246.654467 mm`; H2809 closure with storage is `-297,116.718881 mm`. The production `H.wat.parquet` is legacy, so the five new WAT storage/capacity fields are exposed but null for all rows.

**Lessons Learned**: Parser-first rollout kept legacy layouts safe while WEPP-forest output was widened. The production gate needs an explicit mount/preflight check before the final audit step.

**Archive Status**: Ready to archive after downstream report-consumer spot check or follow-up package creation for the residual closure issue.
