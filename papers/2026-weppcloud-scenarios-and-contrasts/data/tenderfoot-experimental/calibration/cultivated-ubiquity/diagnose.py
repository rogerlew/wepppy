"""Read-only baseline diagnostics from the retained cultivated-ubiquity snapshot."""

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
flow = pd.read_csv(RAW / "observed/Channels-Streamflow_(mm)-Daily.csv", parse_dates=["date"])
hill = pd.read_csv(RAW / "observed/Hillslopes-Streamflow_(mm)-Daily.csv", parse_dates=["date"])
balance = pd.read_parquet(RAW / "wepp/output/interchange/totalwatsed3.parquet")
channel = pd.read_parquet(RAW / "wepp/output/interchange/chanwb.parquet")
assert flow.date.is_unique and flow.date.equals(hill.date)
source = pd.read_csv(ROOT.parents[1] / "observed/lote_observed_daily_1992-2015.csv", parse_dates=["Date"])
assert np.array_equal(flow.date.to_numpy(), source.Date.to_numpy())
assert np.allclose(flow.Observed, source["Streamflow (mm)"], rtol=0, atol=5e-7)
channel["date"] = pd.to_datetime(dict(year=channel.year, month=channel.month, day=channel.day_of_month))
matched = flow.merge(channel, on="date", validate="one_to_one")
area_m2 = float(balance.Area.max())
# Observed's channel comparator normalizes by the summed hillslope area.
assert np.allclose(matched.Modeled, matched["Outflow (m^3)"] * 1000 / area_m2, rtol=0, atol=5e-7)
metrics = {}
for label, data in (("outlet", flow), ("hillslopes", hill)):
    m, o = data.Modeled, data.Observed
    metrics[label] = {
        "matched_days": len(data), "modeled_mean_mm_day": float(m.mean()),
        "observed_mean_mm_day": float(o.mean()),
        "volume_bias_percent": float(100 * (m.sum() / o.sum() - 1)),
        "nse": float(1 - ((m-o)**2).sum() / ((o-o.mean())**2).sum()),
        "correlation": float(m.corr(o)),
    }
monthly = flow.groupby(flow.date.dt.month).agg(
    accepted_days=("Observed", "size"), modeled_mm_day=("Modeled", "mean"),
    observed_mm_day=("Observed", "mean"),
)
monthly.index.name = "month"
monthly.to_csv(ROOT / "matched_monthly.csv", float_format="%.6f")
columns = ["Precipitation", "Rain+Melt", "Runoff", "Lateral Flow", "Percolation",
           "Baseflow", "Aquifer losses", "Transpiration", "Evaporation", "ET", "Streamflow"]
annual = balance.groupby("year")[columns].sum().loc[1993:2015]
annual.to_csv(ROOT / "modeled_annual_water_balance.csv", float_format="%.6f")
metrics["modeled_annual_means_1993_2015_mm"] = annual.mean().to_dict()
(ROOT / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
fig, axes = plt.subplots(2, 1, figsize=(10, 7), constrained_layout=True)
for col, label, color in [("Observed", "Observed LOTE", "black"), ("Modeled", "WEPP outlet", "#1676a3")]:
    sample = flow.loc[flow.date.dt.year == 2012].set_index("date")[col]
    sample = sample.reindex(pd.date_range("2012-01-01", "2012-12-31"))
    axes[0].plot(sample.index, sample, label=label, color=color, linewidth=1.2)
axes[0].set(title="2012 hydrograph — accepted observation days only", ylabel="Streamflow (mm/day)")
axes[0].legend()
axes[1].plot(monthly.index, monthly.observed_mm_day, "o-", color="black", label="Observed LOTE")
axes[1].plot(monthly.index, monthly.modeled_mm_day, "o-", color="#1676a3", label="WEPP outlet")
axes[1].set(title="1992–2015 monthly means on matched days (unequal seasonal coverage)",
            xlabel="Month", ylabel="Streamflow (mm/day)", xticks=range(1, 13), xlim=(1, 12))
axes[1].legend()
fig.savefig(ROOT / "baseline_diagnostics.png", dpi=170)
plt.close(fig)
manifest = {
    "acquired_date": "2026-10-08", "run_url": "https://wc.openwepp.org/weppcloud/runs/cultivated-ubiquity/disturbed9002_wbt/",
    "host": "hpc", "source_path": "/tank/kubernetes/weppcloud/weppcloud-wc1/pvc-d4c5528b-3204-438b-909a-61af286d6fea/runs/cu/cultivated-ubiquity",
    "scope": "Non-atomic read-only copy of selected metadata, observations, output tables, and representative prepared inputs. Raw snapshot ignored by Git; not a complete reproducible WEPP run.",
    "files": [{"path": str(f.relative_to(RAW)), "bytes": f.stat().st_size,
               "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
              for f in sorted(RAW.rglob("*")) if f.is_file()],
}
(ROOT / "snapshot_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(metrics, indent=2))
