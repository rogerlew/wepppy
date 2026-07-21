"""Phase 0 addendum: goldens for the designated validation run austere-inaction.

Runs Jackson's unmodified pipeline (4e3b4a6) end-to-end: parquet artifacts ->
prepare_ce_and_plot_data -> ce_select_sites_flexible. 3-treatment grouped mode
(contrast_id schema, wbt backend, disturbed9002_wbt).
"""
import sys, json, io
from contextlib import redirect_stdout
sys.path.insert(0, "/workdir/PATH-cost-effective")
import numpy as np
import pandas as pd
from PATH_data_prep import prepare_ce_and_plot_data
from PATH_CE import ce_select_sites_flexible

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "."

r = "/wc1/runs/au/austere-inaction"
hills = pd.read_parquet(f"{r}/omni/scenarios.hillslope_summaries.parquet")
contrasts = pd.read_parquet(f"{r}/omni/contrasts.out.parquet")
char = pd.read_parquet(f"{r}/watershed/hillslopes.parquet")
totals = pd.read_parquet(f"{r}/omni/scenarios.out.parquet")

with redirect_stdout(io.StringIO()):
    _hills_agg, _outlet, _char_agg, final_df = prepare_ce_and_plot_data(
        hillslopes=hills,
        contrasts=contrasts,
        hillslope_char=char,
        contrast_groups=f"{r}/omni/contrast_id_definitions.psv",
        outlet_totals=totals,
        write_outputs=False,
    )
final_df.to_parquet(f"{OUT_DIR}/prepared_frame_austere.parquet")
print("prepared frame:", final_df.shape, "groups:", sorted(final_df["contrast_id"]))

# Numeric-only inf cleanup: parquet preserves list-typed columns (topaz_ids)
# that Jackson's CSV round-trip stringifies; frame-wide replace() raises on them.
data = final_df.copy()
num = data.select_dtypes(include=[np.number]).columns
data[num] = data[num].replace([np.inf, -np.inf], np.nan)
for col in [c for c in data.columns if "Sddc" in c or "Sdyd" in c]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

treatments = ["0.5 tons/acre", "1 tons/acre", "2 tons/acre"]
cost = [2475.0, 2475.0, 2475.0]; qty = [0.5, 1.0, 2.0]; fixed = [500.0, 1000.0, 1500.0]

cases = []
# post-fire Sddc = 48.3; max achievable reduction 0.1 (only group 12 treatable:
# groups 15/18 have all-negative Sdyd reductions -> upstream forces them untreated)
for sdyd_thr, sddc_thr in [(15, 48.3), (15, 48.2), (15, 48.0)]:
    with redirect_stdout(io.StringIO()):
        res = ce_select_sites_flexible(
            data=data, treatments=treatments, treatment_cost=cost,
            treatment_quantity=qty, fixed_cost=fixed,
            sdyd_threshold=sdyd_thr, sddc_threshold=sddc_thr,
        )
    (status, _cv, _syt, selected, treat_hills, sddc_red, final_sddc,
     _hs, sdyd_df, untreatable, total_cost, total_fixed, untreat_inc) = res
    cases.append({
        "sdyd_threshold": sdyd_thr, "sddc_threshold": sddc_thr,
        "primary_status": int(status),
        "selected_hillslopes": sorted(int(x) for x in selected),
        "treatment_hillslopes": [sorted(int(x) for x in t) for t in treat_hills],
        "total_cost": round(float(total_cost), 2),
        "total_fixed_cost": round(float(total_fixed), 2),
        "total_sddc_reduction": round(float(sddc_red), 4),
        "final_sddc": round(float(final_sddc), 4),
        "n_untreatable": int(len(untreatable)),
        "n_untreatable_increase": int(len(untreat_inc)),
        "sdyd_df_sum": round(float(pd.to_numeric(sdyd_df["final_Sdyd"]).sum()), 6),
    })
    print(f"sdyd={sdyd_thr} sddc={sddc_thr}: status={status} sel={sorted(selected)} "
          f"per-treat={[sorted(t) for t in treat_hills]} cost={total_cost:.0f} final_sddc={final_sddc:.2f}")

golden = {
    "upstream_commit": "4e3b4a6",
    "source": "run austere-inaction (disturbed9002_wbt, grouped contrasts, 3 mulch treatments)",
    "env": {"pandas": pd.__version__, "numpy": np.__version__},
    "treatments": treatments, "treatment_cost": cost, "treatment_quantity": qty, "fixed_cost": fixed,
    "cases": cases,
}
with open(f"{OUT_DIR}/solver_goldens_austere.json", "w") as f:
    json.dump(golden, f, indent=1)
print("wrote solver_goldens_austere.json")
