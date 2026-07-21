# ADR: PATH-CE v2 Parameterization — Sddc Outlet Constraint, Treatment Cost Contract, Severity Map

Status: Accepted (decisions D1–D5 ratified by Roger Lew 2026-07-20; finalized at package closure 2026-07-21)
Date: 2026-07-20

## Context

The vendored PATH Cost-Effective mod (`wepppy/nodb/mods/path_ce/`) was a stale port of Jackson Nakae's optimization model. Its water-quality constraint used summed hillslope NTU as a proxy for outlet sediment discharge, its fallback model forced every site to be treated (`== 1`), and it carried no contrast-group aggregation, threshold sweep, or reports. Jackson's current code (PATH-cost-effective @ `4e3b4a6`) resolves all of this. Work package `docs/work-packages/20260720_path_ce_v2/` resyncs the vendored model as a faithful extraction; this ADR records the parameterization deltas that change model behavior relative to the pre-v2 mod.

## Decision

Adopt Jackson's `4e3b4a6` parameterization wholesale, with wepppy-side contracts fixed as follows.

1. **Water-quality constraint is real outlet Sddc, not NTU.** `Sddc post-fire` is the scalar outlet `Avg. Ann. sediment discharge from outlet` (tons) for the `sbs_map` scenario, sourced from `omni/scenarios.out.parquet` (falling back to contrast `control_v`). Per-site `Sddc reduction {treatment}` columns come from Omni outlet contrast deltas (`control_v − v`). The constraint requires total selected reduction ≥ `Sddc post-fire − sddc_threshold` (clipped at 0). Consequence: Omni contrasts are structurally required (D3); users neutralize the constraint by setting `sddc_threshold ≥ Sddc post-fire`, not by omitting contrasts.
2. **Secondary (fallback) model preserves optional treatment.** `sum(x[t][i]) <= 1` per site, matching upstream; the pre-v2 `== 1` variant is removed. The fallback maximizes total Sddc reduction subject to the same per-site Sdyd constraints, and can legitimately return negative total reduction on datasets where forced Sdyd equality constraints select treatments with negative outlet deltas.
3. **Treatment cost contract (D4).** Each treatment is a vector `{label, scenario, unit_cost, quantity, fixed_cost}` serialized in `path_ce.nodb` with `unit_cost` in **$/acre** and `quantity` in tons/acre (Jackson's native convention; UI shows English/SI via unitizer). Per-site cost is `area (acres) × unit_cost × quantity`. The prepared frame's `area_sum`/`area` column is in **hectares** (data prep scales raw m² by 1e-4, matching upstream), so the solver wrapper converts the area column to acres (`× 2.47105`) before solving — the faithful core itself stays hectare-based, and core-parity tests certify it against upstream goldens on that basis, while seam tests certify the acre contract. Defaults are Jackson's report defaults: unit cost $2,475/acre for all three mulch tiers; quantities 0.5 / 1 / 2 tons/acre; fixed costs $500 / $1,000 / $1,500 (scenarios `mulch_15/30/60_sbs_map`). **Open upstream item:** Jackson's own pipeline multiplies $/acre against hectare areas (a unit defect); flagged to him. Our seam computes on acres regardless of his resolution, so wepppy costs are ~2.47× upstream's for identical inputs until he fixes it.
4. **Treatment labels are contract, not decoration.** Prepared-frame columns are keyed `"Sdyd post-treat {label}"` etc., and data prep derives labels from scenario names (`mulch_{n}_sbs_map → {n/30:g} tons/acre`). Configured labels must match this derivation; `presets.py` encodes and tests it. Because the faithful core pairs treatments to reduction columns **positionally**, the solver wrapper validates every configured label against the frame's reduction columns (erroring with the available labels), prunes unconfigured reduction columns, and realigns the treatment vectors to column order — making any configured order or subset safe.
5. **Burn severity code map (extended).** High = {105, 119, 129} ∪ {105015/030/060, 119015/030/060}; Moderate = {118, 120, 130} ∪ {118015/030/060, 120015/030/060}; Low = {106, 121, 131} ∪ {106015/030/060, 121015/030/060}. The 6-digit codes cover disturbed-landuse × mulch-cover combinations. In grouped (contrast-group) mode, a group's severity is derived from its **most frequent landuse code by hillslope row count** (ties broken by the largest numeric code — upstream `most_common_landuse_key`) and can be unmapped when unburned hillslopes dominate the group — the severity filter is only meaningful in per-hillslope modes; the UI must caveat this. (Area-weighted dominance would be a behavior change requiring separate ratification and new goldens.)
6. **Thresholds and unit labels.** `sddc_threshold` compares against the Omni outlet artifact, whose unit is **tonne/yr** (metric); the UI's unitized input uses that canonical unit (`weight-annual` category). `sdyd_threshold` compares against the prepared-data yield, whose unit is the **mixed tonne/acre** (tonnes from Omni divided by acres) — no unitizer category matches, so the UI labels it plainly. Upstream labels both as "tons"; the tonne-vs-ton looseness and the mixed tonne/acre unit are flagged to Jackson. The threshold sweep quantizes both to integers (upstream behavior); the primary solve uses the user's un-quantized values.
7. **Unitizer factor correction (platform).** Wiring the unitized Sddc input surfaced a pre-existing wepppy defect: the `ton→tonne` and `ton/yr→tonne/yr` conversions used factor 25.4 (the inch→mm factor). Corrected to 0.90718474 in `wepppy/nodb/unitizer.py` with the generated map regenerated and factor/round-trip regression tests (`tests/nodb/test_unitizer_conversions.py`).

## Decision Provenance (Required for Parameterization Changes)

Decision Venue: wepppy work-package session (Claude Code ↔ Roger), 2026-07-20 UTC
Participants Present: Roger Lew, Claude Code (executor); model author Jackson Nakae (upstream, informed)
Decision Owner(s): Roger Lew (D1–D5 ratification 2026-07-20 19:50 UTC)
Implementer(s): Claude Code (explicit executor assignment for this package)

## Change Summary

| Aspect | Pre-v2 vendored | v2 (this ADR) |
| --- | --- | --- |
| Outlet constraint | `NTU post-fire` summed over hillslopes as Sddc proxy | scalar outlet Sddc (tons) + contrast-derived per-site reductions |
| Fallback model | `sum(x) == 1` (every site forced treated) | `sum(x) <= 1` (sites may stay untreated) |
| Untreatable classes | single class | adds strictly-increasing-Sdyd subclass (styled separately in reports) |
| Treatments | 3 mulch presets, quantity fixed 1.0, fixed_cost 0 | full vectors; defaults $2,475/ac × {0.5,1,2} t/ac + {$500,$1k,$1.5k} fixed |
| Severity map | 3-digit codes only | extended 6-digit disturbed×mulch codes |
| Aggregation | none (per-hillslope only) | contrast-group aggregation (psv), runoff-weighted NTU, undisturbed backfill |
| Sweep | none | binary-search bounds + bounded grid (≤ ~75×75 solves) |

## Rationale

Faithful extraction of the model author's current code keeps future upstream syncs diffable and puts the scientific parameterization decisions where they belong (with Jackson), while wepppy owns the data seam (parquet-native inputs, $/acre-on-acres cost basis, logging, persistence).

## Alternatives Considered

1. Keep NTU proxy constraint — rejected: it is not the model author's current science and requires no fewer Omni artifacts.
2. Serialize costs in SI ($/ha) — rejected (D4): Jackson's convention is $/acre; unitizer handles display in both systems; converting at the seam invites double-conversion bugs.
3. Re-architect rather than faithful extraction — rejected: the pre-v2 port's structural rewrite is precisely what made this resync expensive.

## Consequences

- PATH-CE requires user-provisioned Omni scenarios *and* outlet contrasts for every configured treatment (precondition validation, Phase 2).
- Sites whose Sdyd increases under every treatment are force-excluded even when they would help the outlet constraint (observed dominating on the `austere-inaction` validation run). This is faithful upstream behavior and is surfaced in reports rather than altered.
- No backward compatibility with pre-v2 `path_ce.nodb` config or `<wd>/path/` artifacts (ratified); migration is re-running the mod.

## Evidence

- Delta assessment: `docs/work-packages/20260720_path_ce_v2/artifacts/2026-07-20_delta_assessment.md`
- Executional goldens (both schemas, both solver paths): `artifacts/2026-07-20_phase0_goldens.md`, `artifacts/goldens/`
- Validation-run findings: `artifacts/2026-07-20_validation_run_austere.md`
- Parity tests: `tests/nodb/mods/path_ce/` (23 tests green in the weppcloud container, 2026-07-20)

## Risk and Rollback Notes

Risks: partial Omni contrast coverage in existing runs (mulch_60-only is the norm); grouped-mode severity filter surprise; upstream $/acre-vs-hectare discrepancy pending Jackson's confirmation. Rollback: the pre-v2 mod remains in git history; no live consumers depend on pre-v2 artifacts (mod never publicly released).

## Implementation Notes

Vendored modules: `path_ce_solver.py`, `data_prep.py`, `threshold_sweep.py` (faithful; seam changes documented in module docstrings). `presets.py` carries the treatment-vector contract. Phase 2 replaces the controller config schema and RQ orchestration; interim shims in `presets.py` and the retained `data_loader.py` are deleted there.
