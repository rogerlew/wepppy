"""Enriched solver goldens from Jackson's UNMODIFIED code (commit 4e3b4a6).

Post-review regeneration (Codex findings 4+5): records full ordered outputs
(untreatable id sets, increase-class ids, complete final-Sdyd table, per-
treatment cost-vector sums) instead of counts/sums, and adds filtered cases
(slope_range + bs_threshold). Overwrites the three solver golden JSONs; the
original Phase 0 generators are retained for provenance.

Usage: python make_goldens_enriched.py <out_dir>
Requires the pinned env (pandas 2.2.2, PuLP 3.3.0, pyarrow 23.0.1) and
/workdir/PATH-cost-effective @ 4e3b4a6 on disk.
"""
import sys, json, io
from contextlib import redirect_stdout

sys.path.insert(0, "/workdir/PATH-cost-effective")
import numpy as np
import pandas as pd
from PATH_CE import ce_select_sites_flexible
from PATH_data_prep import prepare_ce_and_plot_data

OUT = sys.argv[1] if len(sys.argv) > 1 else "."


def capture(data, treatments, cost, qty, fixed, cases):
    out = []
    for case in cases:
        kwargs = dict(
            data=data, treatments=treatments, treatment_cost=cost,
            treatment_quantity=qty, fixed_cost=fixed,
            sdyd_threshold=case["sdyd_threshold"], sddc_threshold=case["sddc_threshold"],
        )
        if case.get("slope_range") is not None:
            kwargs["slope_range"] = tuple(case["slope_range"])
        if case.get("bs_threshold") is not None:
            kwargs["bs_threshold"] = list(case["bs_threshold"])
        with redirect_stdout(io.StringIO()):
            res = ce_select_sites_flexible(**kwargs)
        if res is None:
            out.append({**case, "result": None})
            continue
        (status, cost_vectors, syrt, selected, treat_hills, sddc_red, final_sddc,
         _hs, sdyd_df, untreatable, total_cost, total_fixed, untreat_inc) = res
        id_col = "wepp_id" if "wepp_id" in data.columns else "contrast_id"
        out.append({
            **case,
            "primary_status": int(status),
            "selected_hillslopes": sorted(int(x) for x in selected),
            "treatment_hillslopes": [sorted(int(x) for x in t) for t in treat_hills],
            "total_cost": round(float(total_cost), 2),
            "total_fixed_cost": round(float(total_fixed), 2),
            "total_sddc_reduction": round(float(sddc_red), 6),
            "final_sddc": round(float(final_sddc), 6),
            "untreatable_ids": sorted(int(x) for x in untreatable[id_col].tolist()),
            "untreatable_increase_ids": sorted(int(x) for x in untreat_inc[id_col].tolist()) if len(untreat_inc) else [],
            "sdyd_final": [
                [int(i), round(float(v), 6)]
                for i, v in sorted(
                    zip(sdyd_df[id_col].tolist(), pd.to_numeric(sdyd_df["final_Sdyd"]).tolist())
                )
            ],
            "cost_vector_sums": {
                t: round(float(pd.to_numeric(cv).sum()), 2) for t, cv in cost_vectors.items()
            },
            "syrt_sum": round(float(pd.to_numeric(syrt).sum()), 6),
        })
        print(f"  case {case}: status={status} n_sel={len(selected)} cost={total_cost:.0f}")
    return out


def write(path, payload):
    with open(path, "w") as f:
        json.dump(payload, f, indent=1)
    print("wrote", path)


ENV = {"pandas": pd.__version__, "numpy": np.__version__}

# --- honeyed-marathoner (contrast_id, single treatment) + filtered cases ---
print("honeyed-marathoner")
frame = pd.read_parquet(f"{OUT}/prepared_frame.parquet")
t1, c1, q1, f1 = ["2 tons/acre"], [2475.0], [2.0], [1500.0]
cases1 = [
    {"sdyd_threshold": 15, "sddc_threshold": 43000},
    {"sdyd_threshold": 5, "sddc_threshold": 40000},
    {"sdyd_threshold": 1, "sddc_threshold": 35000},
    {"sdyd_threshold": 5, "sddc_threshold": 40000, "slope_range": [10, 35]},
    {"sdyd_threshold": 5, "sddc_threshold": 40000, "slope_range": [10, 35],
     "bs_threshold": ["High", "Moderate"]},
]
write(f"{OUT}/solver_goldens.json", {
    "upstream_commit": "4e3b4a6",
    "run": "honeyed-marathoner (cumulative contrasts + psv, 471 hillslopes, 100 contrast groups)",
    "env": ENV, "treatments": t1, "treatment_cost": c1, "treatment_quantity": q1, "fixed_cost": f1,
    "cases": capture(frame, t1, c1, q1, f1, cases1),
})

# --- pacificcreek (wepp_id, 3 treatments) ---
print("pacificcreek")
data3 = pd.read_csv("/workdir/PATH-cost-effective/docs/static/downloads/PATH_prepared_hillslope_data.csv")
data3 = data3.replace([np.inf, -np.inf], np.nan)
for col in [c for c in data3.columns if "Sddc" in c or "Sdyd" in c]:
    data3[col] = pd.to_numeric(data3[col], errors="coerce").fillna(0)
data3 = data3.dropna(subset=["wepp_id", "area"]).fillna(0)
t3 = ["0.5 tons/acre", "1 tons/acre", "2 tons/acre"]
c3, q3, f3 = [2475.0] * 3, [0.5, 1.0, 2.0], [500.0, 1000.0, 1500.0]
cases3 = [
    {"sdyd_threshold": 15, "sddc_threshold": 1},
    {"sdyd_threshold": 10, "sddc_threshold": 1},
    {"sdyd_threshold": 5, "sddc_threshold": 1},
    {"sdyd_threshold": 10, "sddc_threshold": 0},
]
write(f"{OUT}/solver_goldens_3treat.json", {
    "upstream_commit": "4e3b4a6",
    "source": "docs/static/downloads/PATH_prepared_hillslope_data.csv (pacificcreek, wepp_id schema, 3 treatments)",
    "env": ENV, "treatments": t3, "treatment_cost": c3, "treatment_quantity": q3, "fixed_cost": f3,
    "cases": capture(data3, t3, c3, q3, f3, cases3),
})

# --- austere-inaction (contrast_id grouped, 3 treatments) ---
print("austere-inaction")
framea = pd.read_parquet(f"{OUT}/prepared_frame_austere.parquet")
framea = framea.copy()
num = framea.select_dtypes(include=[np.number]).columns
framea[num] = framea[num].replace([np.inf, -np.inf], np.nan)
for col in [c for c in framea.columns if "Sddc" in c or "Sdyd" in c]:
    framea[col] = pd.to_numeric(framea[col], errors="coerce").fillna(0)
casesa = [
    {"sdyd_threshold": 15, "sddc_threshold": 48.3},
    {"sdyd_threshold": 15, "sddc_threshold": 48.2},
    {"sdyd_threshold": 15, "sddc_threshold": 48.0},
]
write(f"{OUT}/solver_goldens_austere.json", {
    "upstream_commit": "4e3b4a6",
    "source": "run austere-inaction (disturbed9002_wbt, grouped contrasts, 3 mulch treatments)",
    "env": ENV, "treatments": t3, "treatment_cost": c3, "treatment_quantity": q3, "fixed_cost": f3,
    "cases": capture(framea, t3, c3, q3, f3, casesa),
})

# --- filtered data-prep golden: austere with slope_range (upstream prepare) ---
print("austere-inaction filtered prep (slope_range 20-35)")
r = "/wc1/runs/au/austere-inaction"
with redirect_stdout(io.StringIO()):
    _, _, _, filtered_df = prepare_ce_and_plot_data(
        hillslopes=pd.read_parquet(f"{r}/omni/scenarios.hillslope_summaries.parquet"),
        contrasts=pd.read_parquet(f"{r}/omni/contrasts.out.parquet"),
        hillslope_char=pd.read_parquet(f"{r}/watershed/hillslopes.parquet"),
        contrast_groups=f"{r}/omni/contrast_id_definitions.psv",
        outlet_totals=pd.read_parquet(f"{r}/omni/scenarios.out.parquet"),
        slope_range=(20, 35),
        write_outputs=False,
    )
filtered_df.to_parquet(f"{OUT}/prepared_frame_austere_slope20_35.parquet")
print("wrote prepared_frame_austere_slope20_35.parquet", filtered_df.shape)
