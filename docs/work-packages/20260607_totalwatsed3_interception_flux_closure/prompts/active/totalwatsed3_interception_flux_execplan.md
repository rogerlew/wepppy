# ExecPlan: Consume the openWEPP Interception Flux in totalwatsed3 Closure

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to
date as work proceeds.

This plan is maintained in accordance with
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

openWEPP (independent of the wepppyo3 legacy interchange) now writes the daily
canopy/residue interception flux `I` directly into its hillslope WAT parquet as
`hillslope_wat.Interception` (mm), and — unlike legacy WEPP — **excludes
interception from `ET`**, treating it as a separate outflow in its closure
identity `... + S - I - Q - ET - D - Qd` (`SC-WATBAL-001` v146, openWEPP commit
`b6dc2de`). openWEPP's own audit closes the single-OFE balance to ~`1e-6 mm/yr`.

The water-balance acceptance surface is the **totalwatsed3** daily closure audit,
which today closes `Precipitation - (Runoff + Lateral Flow + ET + Percolation) -
ΔStorage` with no interception-flux outflow. Run on openWEPP output it leaves a
residual ≈ `+I` (~26.8 mm/yr). After this work, an operator or validation agent
can run the totalwatsed3 audit on openWEPP output and see it close.

The fix is small and producer-agnostic: add `Interception` as an optional outflow
defaulting to `0`. Legacy runs (interception already in `ET`, no `Interception`
column) close exactly as before; openWEPP runs (`ET` excludes interception,
`Interception` present) now close. **`ET` (`Ep`/`Es`/`Er`) must not change** — it
is producer-authoritative physics.

Observable outcome: the totalwatsed3 daily closure audit closes (within the
existing closure tolerance) on openWEPP's post-WBVAL06 `indispensable-presenter`
output for years `2..6`, and legacy-run closure is unchanged.

## Plan

1. `wepppy/wepp/interchange/totalwatsed3.py`: parse/pass-through optional
   `Interception` (mm) from `H.wat`; add it to the daily closure outflow sum
   alongside Runoff/Lateral/ET/Percolation; default missing to `0` (legacy).
2. `tools/totalwatsed3_daily_closure_audit.py`: include the interception outflow
   in the reported (and reconstructed) closure identity.
3. `docs/dev-notes/totalwatsed-interchange.spec.md`: document the interception
   outflow term and the legacy-vs-openWEPP convention (legacy: in `ET`, no `I`;
   openWEPP: separate `I`, `ET` excludes it).
4. Tests: openWEPP-style row with `Interception` closes with the new term; legacy
   row without `Interception` closes unchanged (regression).
5. Acceptance run: totalwatsed3 audit on openWEPP post-WBVAL06
   `indispensable-presenter` output; confirm years `2..6` close within tolerance.

## Constraints

- Do not change `ET` / `Ep` / `Es` / `Er` or any producer ET computation.
- Do not alter openWEPP; the `Interception` publication is complete there.
- Consume the published `hillslope_wat.Interception` value (mm); do not
  reconstruct or invent the term.
- Optional-defaults-to-0 semantics must keep legacy closure bit-for-bit unchanged.

## Acceptance

- totalwatsed3 daily closure audit closes on openWEPP post-WBVAL06
  `indispensable-presenter` output, years `2..6`, within the existing tolerance.
- Legacy run (no `Interception` column) closure unchanged.
- Focused tests pass; `wctl doc-lint` clean for this package + PROJECT_TRACKER.

## Progress

- 2026-06-07: package scoped; not yet started.

## Surprises & Discoveries

- (none yet)

## Decision Log

- 2026-06-07 (Roger): `ET` is producer-authoritative; interception is carried as a
  separate first-class outflow in the audit rather than folded into `ET`.

## Outcomes & Retrospective

- (pending execution)
