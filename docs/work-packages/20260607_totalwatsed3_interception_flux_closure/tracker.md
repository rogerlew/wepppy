# Tracker - totalwatsed3 Interception-Flux Closure

> Living document tracking progress, decisions, risks, and communication for
> this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-06-07 23:41 UTC
**Current phase**: Done
**Last updated**: 2026-06-08 00:24 UTC
**Next milestone**: Package closeout complete
**Security impact**: `none`
**Dedicated security review**: `no`
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog

- [x] Add optional `hillslope_wat.Interception` consumption to
      `wepppy/wepp/interchange/totalwatsed3.py` schema and daily closure
      aggregation (outflow term; default `0` when absent).
- [x] Add the interception outflow to
      `tools/totalwatsed3_daily_closure_audit.py` closure identity.
- [x] Update `docs/dev-notes/totalwatsed-interchange.spec.md` (interception
      outflow term; legacy-vs-openWEPP convention).
- [x] Add/extend focused tests in `tests/wepp/interchange/test_totalwatsed3.py`
      and `tests/tools/test_totalwatsed3_daily_closure_audit.py`
      (openWEPP-with-`Interception` closes; legacy-without-`Interception` unchanged).
- [x] Acceptance: run the totalwatsed3 audit on openWEPP post-WBVAL06
      `indispensable-presenter` output; confirm years `2..6` close within tolerance.

### In Progress

- [ ] None.

### Blocked

- [ ] None (openWEPP `H.wat.Interception` is published as of WBVAL06 / `b6dc2de`).

### Done

- [x] Interception consumption shipped in `wepppy/wepp/interchange/totalwatsed3.py`.
- [x] Audit closure identities updated in `tools/totalwatsed3_daily_closure_audit.py`.
- [x] Spec updated in `docs/dev-notes/totalwatsed-interchange.spec.md`.
- [x] Focused regressions added and passing.
- [x] Acceptance evidence captured at
      `docs/work-packages/20260607_totalwatsed3_interception_flux_closure/artifacts/2026-06-07_execution_evidence.md`.

## Decisions

- 2026-06-07 (Roger): `ET` (`Ep`/`Es`/`Er`) is producer-authoritative and must
  not be changed to absorb interception. Interception is carried as a separate
  first-class outflow in the totalwatsed3 audit.

## Risks

- Legacy vs openWEPP interception convention divergence: legacy runs keep
  interception inside `ET` (no `Interception` column); openWEPP excludes it and
  publishes `I`. Mitigation: the optional-outflow-defaulting-to-0 design closes
  both without branching on producer.

## Notes

- openWEPP side is complete (WBVAL06): `H.wat.Interception` (mm) published,
  `SC-WATBAL-001` v146. This package is the wepppy-side audit consumer that makes
  single-OFE rung-1 WB closure auditable from totalwatsed3.
- 2026-06-08 00:02 UTC: Ran focused tests:
      `wctl run-pytest tests/wepp/interchange/test_totalwatsed3.py tests/tools/test_totalwatsed3_daily_closure_audit.py`
      -> `8 passed`.
- 2026-06-08 00:20 UTC: Acceptance run on openWEPP WBVAL06 post-fix WAT outputs
      recorded in package artifacts. Year-index `2..6` annual residuals with
      interception are `~1.87e-07..2.09e-07 mm`, while without interception they are
      `~14.71..18.94 mm`.
