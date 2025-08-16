#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

# ---- Inputs ----
sbs_hill_fn    = Path('/wc1/runs/rl/rlew-confirmed-complementarity/wepp/output/loss_pw0.hill.parquet')
mulch15_hill_fn= Path('/wc1/runs/rl/rlew-confirmed-complementarity/omni/scenarios/mulch_15_sbs_map/wepp/output/loss_pw0.hill.parquet')

ID_COL   = 'TopazID'
YIELD_COL= 'Soil Loss'

# If Soil Loss is in kilograms, set KG_PER_TON accordingly.
# Use 1000.0 for metric tonnes; use 907.18474 for US short tons.
KG_PER_TON = 1000.0  # <- change to 907.18474 if you want short tons

# ---- Load ----
sbs   = pd.read_parquet(sbs_hill_fn, columns=[ID_COL, YIELD_COL])
mulch = pd.read_parquet(mulch15_hill_fn, columns=[ID_COL, YIELD_COL])

# ---- Aggregate to hillslope (TopazID) ----
sbs_g   = sbs.groupby(ID_COL, dropna=False, as_index=False)[YIELD_COL].sum().rename(columns={YIELD_COL: 'yield_sbs'})
mulch_g = mulch.groupby(ID_COL, dropna=False, as_index=False)[YIELD_COL].sum().rename(columns={YIELD_COL: 'yield_mulch'})

# ---- Totals & cumulative comparison ----
tot_sbs   = sbs_g['yield_sbs'].sum()
tot_mulch = mulch_g['yield_mulch'].sum()

# Sort SBS by descending yield, compute cumulative fraction
pareto = (
    sbs_g.sort_values('yield_sbs', ascending=False)
         .assign(cum_yield=lambda d: d['yield_sbs'].cumsum(),
                 cum_frac =lambda d: d['cum_yield'] / tot_sbs)
)

# Hillslopes up to the 80% frontier (include the one that crosses 0.8)
pareto_80 = pareto[pareto['cum_frac'] <= 0.8]
if not pareto.empty and pareto_80.empty:
    # edge-case: single hillslope dominates; include top one
    pareto_80 = pareto.iloc[[0]]

# Exact 80% set stats (SBS)
ids_80 = set(pareto_80[ID_COL].tolist())
yield_80_sbs = pareto_80['yield_sbs'].sum()

# Map those same IDs in the mulch scenario (0 if missing)
mulch_on_80 = mulch_g.set_index(ID_COL).reindex(pareto_80[ID_COL]).fillna(0.0).reset_index()
yield_80_mulch = mulch_on_80['yield_mulch'].sum()

# ---- Conversions to tons (if your units are kg) ----
def to_tons(x): return x / KG_PER_TON

tot_sbs_tons        = to_tons(tot_sbs)
tot_mulch_tons      = to_tons(tot_mulch)
yield_80_sbs_tons   = to_tons(yield_80_sbs)
yield_80_mulch_tons = to_tons(yield_80_mulch)

# ---- Summary ----
pct_reduction_total = (1 - (tot_mulch / tot_sbs)) * 100 if tot_sbs else float('nan')
pct_reduction_80    = (1 - (yield_80_mulch / yield_80_sbs)) * 100 if yield_80_sbs else float('nan')

print("=== Totals (all hillslopes) ===")
print(f"SBS total Soil Loss:   {tot_sbs:,.3f}  ({tot_sbs_tons:,.3f} tons)")
print(f"Mulch total Soil Loss: {tot_mulch:,.3f}  ({tot_mulch_tons:,.3f} tons)")
print(f"Total change: {tot_mulch - tot_sbs:,.3f}  ({to_tons(tot_mulch - tot_sbs):,.3f} tons)  "
      f"[{pct_reduction_total:+.2f}%]")

print("\n=== Pareto set (SBS hillslopes contributing ~80% of SBS total) ===")
print(f"Count of hillslopes: {len(ids_80)}")
print(f"SBS yield of this set:   {yield_80_sbs:,.3f}  ({yield_80_sbs_tons:,.3f} tons)")
print(f"Mulch yield (same set):  {yield_80_mulch:,.3f}  ({yield_80_mulch_tons:,.3f} tons)")
print(f"Change on this set: {yield_80_mulch - yield_80_sbs:,.3f}  "
      f"({to_tons(yield_80_mulch - yield_80_sbs):,.3f} tons)  "
      f"[{pct_reduction_80:+.2f}%]")

# ---- Per-hillslope breakdown CSV (top contributing set, in SBS order) ----
out = (
    pareto_80[[ID_COL, 'yield_sbs', 'cum_yield', 'cum_frac']]
    .merge(mulch_g, on=ID_COL, how='left')
    .fillna({'yield_mulch': 0.0})
    .assign(
        yield_sbs_tons   = lambda d: d['yield_sbs']   / KG_PER_TON,
        yield_mulch_tons = lambda d: d['yield_mulch'] / KG_PER_TON,
        delta            = lambda d: d['yield_mulch'] - d['yield_sbs'],
        delta_tons       = lambda d: d['delta'] / KG_PER_TON,
        pct_change       = lambda d: (d['delta'] / d['yield_sbs']).where(d['yield_sbs'] != 0, pd.NA) * 100
    )
)

csv_path = Path('pareto_80_sediment_yield_by_hillslope.csv')
out.to_csv(csv_path, index=False)
print(f"\nWrote breakdown: {csv_path.resolve()}")