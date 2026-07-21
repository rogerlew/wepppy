"""Phase 0 smoke: run Jackson's unmodified pipeline on wepppy parquet artifacts."""
import sys, json
sys.path.insert(0, "/workdir/PATH-cost-effective")
import pandas as pd

from PATH_data_prep import prepare_ce_and_plot_data
from PATH_CE import ce_select_sites_flexible

r = "/wc1/runs/ho/honeyed-marathoner"
hills = pd.read_parquet(f"{r}/omni/scenarios.hillslope_summaries.parquet")
contrasts = pd.read_parquet(f"{r}/omni/contrasts.out.parquet")
char = pd.read_parquet(f"{r}/watershed/hillslopes.parquet")
totals = pd.read_parquet(f"{r}/omni/scenarios.out.parquet")

hills_agg, outlet, char_agg, final_df = prepare_ce_and_plot_data(
    hillslopes=hills,
    contrasts=contrasts,
    hillslope_char=char,
    contrast_groups=f"{r}/omni/contrast_id_definitions.psv",
    outlet_totals=totals,
    write_outputs=False,
)
print("final_df:", final_df.shape)
print("columns:", list(final_df.columns))
sddc_cols = [c for c in final_df.columns if c.startswith("Sddc")]
print("Sddc cols:", sddc_cols)
print("Sddc post-fire head:", final_df["Sddc post-fire"].dropna().head(3).tolist())
