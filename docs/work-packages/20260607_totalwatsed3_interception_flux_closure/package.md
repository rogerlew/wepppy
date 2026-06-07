# totalwatsed3 Interception-Flux Closure

**Status**: Closed 2026-06-08 UTC
**Created**: 2026-06-07 UTC

## Overview

openWEPP now publishes the daily canopy/residue interception flux `I` to its
hillslope WAT parquet as the optional column `hillslope_wat.Interception` (mm),
governed by `SC-WATBAL-001` v146. In openWEPP's water-balance identity,
interception is a **separate outflow** and is **excluded from `ET`**
(`... + S - I - Q - ET - D - Qd`). openWEPP closed its single-OFE water balance to
~`1e-6 mm/yr` for the `indispensable-presenter` validation run under its own
complete-identity audit (SNOWSCI-S1 + WBVAL06).

The acceptance surface for water-balance closure, however, is the **totalwatsed3
daily closure audit** (`wepppy/wepp/interchange/totalwatsed3.py` +
`tools/totalwatsed3_daily_closure_audit.py`). totalwatsed3 currently closes
`Precipitation - (Runoff + Lateral Flow + ET + Percolation) - ΔStorage` with **no
interception-flux outflow** and carries `InterceptionStorage` only as a storage
passthrough. Run on openWEPP post-WBVAL06 output, its audit therefore still shows a
residual ≈ `+I` (~26.8 mm/yr max), because openWEPP's `ET` excludes interception
and totalwatsed3 does not consume the new `Interception` column. Single-OFE rung-1
WB closure is not auditable on the real surface until this is fixed.

## Objectives

- Add the daily interception flux `I` (`hillslope_wat.Interception`) as a
  first-class outflow in the totalwatsed3 daily closure and the closure-audit tool.
- Make the change **backward-compatible with legacy WEPP runs**: when the
  `Interception` column is absent (legacy via the wepppyo3 interchange, where
  interception is already inside `ET`), `I` defaults to `0` and the existing
  closure is unchanged; when present (openWEPP, where `ET` excludes interception),
  `I` is consumed. The single optional-outflow term closes both producers.
- Validate that the totalwatsed3 audit closes on openWEPP's post-WBVAL06
  `indispensable-presenter` output for years `2..6` within tolerance.

## Scope

### Included

- `wepppy/wepp/interchange/totalwatsed3.py` — schema + daily closure aggregation
  (consume optional `Interception`, add it to the outflow sum).
- `tools/totalwatsed3_daily_closure_audit.py` — add `Interception` to the closure
  identity outflows.
- `docs/dev-notes/totalwatsed-interchange.spec.md` — document the interception
  outflow term and the legacy-vs-openWEPP convention.
- Focused tests: `tests/wepp/interchange/test_totalwatsed3.py`,
  `tests/tools/test_totalwatsed3_daily_closure_audit.py`.
- Acceptance run against openWEPP post-WBVAL06 `indispensable-presenter` output.

### Explicitly Out of Scope

- **Do not change `ET` (`Ep`/`Es`/`Er`) or any producer ET computation.** It is
  producer-authoritative physics; interception is a separate first-class outflow,
  not folded into ET.
- No openWEPP changes (the `Interception` publication is complete on that side).
- No change to legacy WEPP / wepppyo3 interchange closure semantics beyond making
  the optional `Interception` term default to 0 when absent.
- No silent term invention: the interception outflow must consume the published
  `hillslope_wat.Interception` value (units `mm`), not a reconstruction.

## Implementation Fidelity and Evidence

- **Fidelity target**: `faithful consumption` of the openWEPP-published
  `hillslope_wat.Interception` flux as a closure outflow.
- **Authoritative source(s)**: openWEPP `SC-WATBAL-001` v146 closure identity
  (`... + S - I - Q - ET - D - Qd`); openWEPP `H.wat.Interception` column.
- **Cutover proof required**: totalwatsed3 daily closure audit on openWEPP
  post-WBVAL06 `indispensable-presenter` output closes for years `2..6` within
  the existing closure tolerance; legacy-run closure is unchanged
  (regression: a run without an `Interception` column still closes as before).
- **Acceptance evidence type**: `both` (run-artifact closure evidence + regression
  tests).

## Stakeholders

- **Primary**: totalwatsed3 / WB-audit maintainers and openWEPP validation owners.
- **Reviewers**: interchange maintainers; Claude Code (openWEPP-side closure review).
- **Security Reviewer**: not required (local flat-file aggregation, no network).
- **Informed**: WBVAL / rung-1 roadmap owners (single-OFE closure gate).

## Success Criteria

- [x] totalwatsed3 daily closure consumes optional `hillslope_wat.Interception`
      as an outflow; absent column defaults to `0`.
- [x] `tools/totalwatsed3_daily_closure_audit.py` includes the interception
      outflow in its closure identity.
- [x] totalwatsed3 audit closes on openWEPP post-WBVAL06 `indispensable-presenter`
      output for years `2..6` within tolerance.
- [x] Legacy-run closure is unchanged when `Interception` is absent (regression).
- [x] `ET` computation is untouched.
- [x] Focused tests pass; package and tracker docs updated.

## Closure Summary

- Implemented interception consumption in
  `wepppy/wepp/interchange/totalwatsed3.py` with optional-default-to-`0`
  semantics for absent/null source values.
- Updated closure identities in
  `tools/totalwatsed3_daily_closure_audit.py` to include interception in both
  reported and reconstructed outflow surfaces.
- Added/updated focused tests in:
  - `tests/wepp/interchange/test_totalwatsed3.py`
  - `tests/tools/test_totalwatsed3_daily_closure_audit.py`
- Acceptance evidence is captured in:
  - `docs/work-packages/20260607_totalwatsed3_interception_flux_closure/artifacts/2026-06-07_execution_evidence.md`

## Provenance

Follow-on from openWEPP WBVAL06 (commit `b6dc2de`), per the decision (Roger,
2026-06-07) that ET is producer-authoritative and interception must be carried as
a separate first-class outflow in the audit rather than folded into ET. See the
openWEPP WBVAL06 worker-handoff and roadmap item 6a.
