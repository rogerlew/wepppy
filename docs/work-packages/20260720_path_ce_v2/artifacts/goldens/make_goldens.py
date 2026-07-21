"""Phase 0: reference goldens from Jackson's unmodified solver (commit 4e3b4a6)."""
import sys, json, io
from contextlib import redirect_stdout
sys.path.insert(0, "/workdir/PATH-cost-effective")
import numpy as np
import pandas as pd
from PATH_data_prep import prepare_ce_and_plot_data
from PATH_CE import ce_select_sites_flexible

r = "/wc1/runs/ho/honeyed-marathoner"
hills = pd.read_parquet(f"{r}/omni/scenarios.hillslope_summaries.parquet")
contrasts = pd.read_parquet(f"{r}/omni/contrasts.out.parquet")
char = pd.read_parquet(f"{r}/watershed/hillslopes.parquet")
totals = pd.read_parquet(f"{r}/omni/scenarios.out.parquet")

with redirect_stdout(io.StringIO()):
    _, _, _, final_df = prepare_ce_and_plot_data(
        hillslopes=hills, contrasts=contrasts, hillslope_char=char,
        contrast_groups=f"{r}/omni/contrast_id_definitions.psv",
        outlet_totals=totals, write_outputs=False,
    )

# clean exactly as PATH_CE_Report_Universal.qmd section 2 does
data = final_df.copy().replace([np.inf, -np.inf], np.nan)
for col in [c for c in data.columns if "Sddc" in c or "Sdyd" in c]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)
data = data.dropna(subset=["contrast_id", "area_sum"]).fillna(0)

print("Sdyd post-fire range:", round(data["Sdyd post-fire"].min(),3), "-", round(data["Sdyd post-fire"].max(),3))
print("Sddc post-fire:", data["Sddc post-fire"].iloc[0])

treatments = ["2 tons/acre"]; cost=[2475.0]; qty=[2.0]; fixed=[1500.0]
cases = []
for sdyd_thr, sddc_thr in [(15, 43000), (5, 40000), (1, 35000)]:
    with redirect_stdout(io.StringIO()):
        res = ce_select_sites_flexible(
            data=data, treatments=treatments, treatment_cost=cost,
            treatment_quantity=qty, fixed_cost=fixed,
            sdyd_threshold=sdyd_thr, sddc_threshold=sddc_thr,
        )
    if res is None:
        cases.append({"sdyd_threshold": sdyd_thr, "sddc_threshold": sddc_thr, "result": None})
        continue
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
        "sdyd_df_sum": round(float(pd.to_numeric(sdyd_df["final_Sdyd"]).sum()), 4),
    })
    print(f"sdyd={sdyd_thr} sddc={sddc_thr}: status={status} n_sel={len(selected)} cost={total_cost:.0f} final_sddc={final_sddc:.1f}")

golden = {
    "upstream_commit": "4e3b4a6",
    "run": "honeyed-marathoner (cumulative contrasts + psv, 471 hillslopes, 100 contrast groups)",
    "env": {"pandas": pd.__version__, "numpy": np.__version__},
    "treatments": treatments, "treatment_cost": cost, "treatment_quantity": qty, "fixed_cost": fixed,
    "cases": cases,
}
with open("/tmp/pathce-ref/solver_goldens.json", "w") as f:
    json.dump(golden, f, indent=1)
data.to_parquet("/tmp/pathce-ref/prepared_frame.parquet", index=False)
print("wrote solver_goldens.json + prepared_frame.parquet")
