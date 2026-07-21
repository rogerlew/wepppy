"""Phase 0: 3-treatment reference goldens from Jackson's pacificcreek prepared data."""
import sys, json, io
from contextlib import redirect_stdout
sys.path.insert(0, "/workdir/PATH-cost-effective")
import numpy as np
import pandas as pd
from PATH_CE import ce_select_sites_flexible

src = "/workdir/PATH-cost-effective/docs/static/downloads/PATH_prepared_hillslope_data.csv"
data = pd.read_csv(src)
red_cols = [c for c in data.columns if "reduction" in c]
print("reduction cols:", red_cols)
print("rows:", len(data), "| Sdyd post-fire range:",
      round(data["Sdyd post-fire"].min(),2), "-", round(data["Sdyd post-fire"].max(),2),
      "| Sddc post-fire:", data["Sddc post-fire"].iloc[0])

data = data.replace([np.inf, -np.inf], np.nan)
for col in [c for c in data.columns if "Sddc" in c or "Sdyd" in c]:
    data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)
data = data.dropna(subset=["wepp_id", "area"]).fillna(0)

treatments = ["0.5 tons/acre", "1 tons/acre", "2 tons/acre"]
cost = [2475.0, 2475.0, 2475.0]; qty = [0.5, 1.0, 2.0]; fixed = [500.0, 1000.0, 1500.0]

sddc_pf = float(data["Sddc post-fire"].iloc[0])
cases = []
for sdyd_thr, sddc_thr in [(15, 1), (10, 1), (5, 1), (10, 0)]:
    with redirect_stdout(io.StringIO()):
        res = ce_select_sites_flexible(
            data=data, treatments=treatments, treatment_cost=cost,
            treatment_quantity=qty, fixed_cost=fixed,
            sdyd_threshold=sdyd_thr, sddc_threshold=sddc_thr,
        )
    if res is None:
        cases.append({"sdyd_threshold": sdyd_thr, "sddc_threshold": sddc_thr, "result": None})
        print(f"sdyd={sdyd_thr} sddc={sddc_thr}: no solution")
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
    print(f"sdyd={sdyd_thr} sddc={sddc_thr}: status={status} n_sel={len(selected)} "
          f"per-treat={[len(t) for t in treat_hills]} cost={total_cost:.0f} final_sddc={final_sddc:.1f}")

golden = {
    "upstream_commit": "4e3b4a6",
    "source": "docs/static/downloads/PATH_prepared_hillslope_data.csv (pacificcreek, wepp_id schema, 3 treatments)",
    "env": {"pandas": pd.__version__, "numpy": np.__version__},
    "treatments": treatments, "treatment_cost": cost, "treatment_quantity": qty, "fixed_cost": fixed,
    "cases": cases,
}
with open("/tmp/pathce-ref/solver_goldens_3treat.json", "w") as f:
    json.dump(golden, f, indent=1)
print("wrote solver_goldens_3treat.json")
