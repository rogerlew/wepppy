"""Check both Tenderfoot snapshots and reproduce the October manuscript comparison.

Run with the repository .venv Python. No live model execution or network access.
Outlet comparisons use paired annual tables to avoid repeated baseline rounding.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
CASES = {
    "experimental": (HERE, "turbinate-melodrama"),
    "larger": (HERE.parent / "tenderfoot", "animal-misgiving"),
}
SCENARIOS = ["undisturbed", "thinning_30_75", "thinning_65_90"]
ANNUAL = {
    "Total water discharge from outlet": "water_m3",
    "Total sediment discharge from outlet": "sediment_t",
    "Total channel soil loss": "channel_loss_t",
}
LONG_TERM = {
    "water_m3": "Avg. Ann. water discharge from outlet",
    "sediment_t": "Avg. Ann. sediment discharge from outlet",
    "channel_loss_t": "Avg. Ann. total channel soil loss",
}


def summary(root):
    frame = pd.read_parquet(root / "wepp/output/interchange/loss_pw0.out.parquet")
    assert not frame.key.duplicated().any()
    return frame.set_index("key").value


def annual(root):
    frame = pd.read_parquet(root / "wepp/output/interchange/loss_pw0.all_years.out.parquet")
    frame = frame[frame.key.isin(ANNUAL)].pivot(index="year", columns="key", values="value").rename(columns=ANNUAL)
    assert list(frame.index) == list(range(1, 101))
    assert not frame.isna().any().any()
    return frame


def analyze_case(case, directory, runid):
    raw = directory / "raw"
    manifest = json.loads((directory / "snapshot_manifest.json").read_text())
    for entry in manifest["files"]:
        assert hashlib.sha256((raw / entry["path"]).read_bytes()).hexdigest() == entry["sha256"], entry["path"]
    omni = json.loads((raw / "omni.nodb").read_text())["py/state"]
    dependencies = 0
    for dep in omni["_contrast_dependency_tree"].values():
        for source in dep["dependencies"].values():
            path = raw / source["loss_path"].split(f"/{runid}/", 1)[1]
            assert hashlib.sha1(path.read_bytes()).hexdigest() == source["sha1"]
            dependencies += 1
    hills = pd.read_parquet(raw / "omni/scenarios.hillslope_summaries.parquet")
    hills = {s: hills[hills.scenario == s].set_index("Topaz ID").sort_index() for s in SCENARIOS}
    combined = pd.read_parquet(raw / "omni/scenarios.out.parquet")
    source_annual, scenario_rows = {}, []
    for s in SCENARIOS:
        root = raw if s == "undisturbed" else raw / "_pups/omni/scenarios" / s
        metrics = summary(root)
        np.testing.assert_allclose(combined[combined.scenario == s].set_index("key").value.reindex(metrics.index), metrics)
        assert hills[s].index.equals(hills["undisturbed"].index)
        np.testing.assert_allclose(hills[s]["Landuse Area (ha)"], hills["undisturbed"]["Landuse Area (ha)"])
        source_annual[s] = annual(root)
        for col, key in LONG_TERM.items():
            assert np.isclose(source_annual[s][col].mean(), metrics[key], rtol=.001, atol=.11)
        area = metrics["Total contributing area to outlet"]
        hill_area = hills[s]["Landuse Area (ha)"].sum()
        hill_loss = hills[s]["Soil Loss (kg/yr)"].sum() / 1000
        scenario_rows.append({
            "case": case, "runid": runid, "scenario": s, "area_ha": area,
            "hillslope_area_ha": hill_area, "hillslope_loss_t": hill_loss,
            "hillslope_loss_t_ha": hill_loss / hill_area,
            "precip_mm": metrics["Avg. Ann. Precipitation volume in contributing area"] / area / 10,
            "water_mm": source_annual[s].water_m3.mean() / area / 10,
            **source_annual[s].mean().to_dict(),
        })
    definitions = {}
    for line in (raw / "omni/contrast_id_definitions.psv").read_text().splitlines():
        cid, ids = line.split("|")
        definitions[int(cid)] = set(map(int, ids.split(",")))
    assert sorted(definitions) == list(range(1, len(definitions) + 1))
    assert len(definitions) % 2 == 0
    groups = [definitions[c] for c in range(1, len(definitions) + 1, 2)]
    assert all(definitions[c] == definitions[c + 1] for c in range(1, len(definitions) + 1, 2))
    assert sum(map(len, groups)) == len(set.union(*groups)) == len(hills["undisturbed"])
    assert set.union(*groups) == set(hills["undisturbed"].index)
    exported = pd.read_parquet(raw / "omni/contrasts.out.parquet")
    baseline = summary(raw)
    contrast_rows, annual_rows = [], []
    mismatches = 0
    for cid, ids in sorted(definitions.items()):
        name = omni["_contrast_names"][cid - 1]
        s = name.split("__to__")[1]
        sidepath = raw / f"omni/contrasts/contrast_{cid:05d}.tsv"
        assert hashlib.sha1(sidepath.read_bytes()).hexdigest() == omni["_contrast_dependency_tree"][name]["sidecar_sha1"]
        side = pd.read_csv(sidepath, sep="\t", header=None, names=["id", "path"])
        assert len(side) == len(hills[s]) and not side.id.duplicated().any()
        assert set(side.loc[side.path.str.contains(f"/scenarios/{s}/"), "id"]) == ids
        assert json.loads((raw / f"omni/contrasts/contrast_{cid:05d}.status.json").read_text())["status"] == "completed"
        root = raw / f"_pups/omni/contrasts/{cid}"
        metrics = summary(root)
        ex = exported[exported.contrast_id == cid].set_index("key")
        np.testing.assert_allclose(ex.value.reindex(metrics.index), metrics)
        mismatches += int((~np.isclose(ex.control_v, baseline.reindex(ex.index), rtol=1e-10, atol=1e-8)).sum())
        values = annual(root)
        for col, key in LONG_TERM.items():
            assert np.isclose(values[col].mean(), metrics[key], rtol=.001, atol=.11)
        delta = values - source_annual["undisturbed"]
        annual_rows.append(delta.assign(case=case, scenario=s, contrast_id=cid).reset_index())
        h, b = hills[s], hills["undisturbed"]
        ids = sorted(ids)
        treated = [i for i in ids if h.loc[i, "Landuse Key"] != b.loc[i, "Landuse Key"]]
        local_loss = (h.loc[ids, "Soil Loss (kg/yr)"] - b.loc[ids, "Soil Loss (kg/yr)"]).sum() / 1000
        expected = b["Soil Loss (kg/yr)"].sum() / 1000 + local_loss
        assert np.isclose(metrics["Avg. Ann. total hillslope soil loss"], expected, atol=.12, rtol=0)
        contrast_rows.append({
            "case": case, "scenario": s, "contrast_id": cid, "group": (cid + 1) // 2,
            "treated_area_ha": h.loc[treated, "Landuse Area (ha)"].sum(),
            "local_hillslope_loss_delta_t": local_loss,
            **delta.mean().to_dict(),
        })
    contrasts = pd.DataFrame(contrast_rows)
    additions, diagnostics = [], []
    for s in SCENARIOS[1:]:
        delta = source_annual[s] - source_annual["undisturbed"]
        selected = contrasts[contrasts.scenario == s]
        for metric in LONG_TERM:
            full = delta[metric].mean()
            isolated = selected[metric].sum()
            additions.append({"case": case, "scenario": s, "metric": metric,
                              "full_delta": full, "sum_isolated": isolated,
                              "excess_percent": 100 * (isolated / full - 1)})
        for metric in ["water_m3", "sediment_t"]:
            diagnostics.append({"case": case, "scenario": s, "metric": metric,
                                "increase_years": int((delta[metric] > 0).sum()),
                                "mean": delta[metric].mean(), "median": delta[metric].median()})
        full_hill = (hills[s]["Soil Loss (kg/yr)"] - hills["undisturbed"]["Soil Loss (kg/yr)"]).sum() / 1000
        assert np.isclose(selected.local_hillslope_loss_delta_t.sum(), full_hill, rtol=1e-12)
    checks = {"files_verified": len(manifest["files"]), "dependency_hashes_verified": dependencies,
              "groups": len(groups), "contrasts": len(definitions), "export_control_mismatches": mismatches}
    return scenario_rows, contrasts, pd.concat(annual_rows), additions, diagnostics, checks


def main():
    OUT.mkdir(exist_ok=True)
    scenarios, contrasts, annuals, additions, diagnostics, checks = [], [], [], [], [], {}
    for case, (directory, runid) in CASES.items():
        s, c, a, add, d, check = analyze_case(case, directory, runid)
        scenarios.extend(s)
        contrasts.append(c)
        annuals.append(a)
        additions.extend(add)
        diagnostics.extend(d)
        checks[case] = check
    frames = {"scenarios": pd.DataFrame(scenarios), "contrasts": pd.concat(contrasts),
              "contrast_annual_deltas": pd.concat(annuals), "additivity": pd.DataFrame(additions),
              "annual_diagnostics": pd.DataFrame(diagnostics)}
    for name, frame in frames.items():
        frame.to_csv(OUT / f"{name}.csv", index=False)
    (OUT / "validation.json").write_text(json.dumps(checks, indent=2) + "\n")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True, layout="constrained")
    for ax, case, title in zip(axes, CASES, ["Experimental-forest application (30.84 km²)", "Larger-basin comparison (269.93 km²)"]):
        values = frames["additivity"].query("case == @case and metric == 'sediment_t'").set_index("scenario").loc[SCENARIOS[1:]]
        x = np.arange(2)
        ax.bar(x - .18, values.full_delta, .36, label="Full scenario", color="#267eab")
        ax.bar(x + .18, values.sum_isolated, .36, label="Sum of isolated groups", color="#be5a22")
        ax.set_xticks(x, ["30/75", "65/90"])
        ax.set_xlabel("Canopy/ground cover (%)")
        ax.set_ylabel("Outlet sediment increase (tonne/year)")
        ax.set_title(title, fontsize=10)
        ax.legend(fontsize=8)
    for suffix in ["png", "svg"]:
        fig.savefig(OUT / f"basin_comparison.{suffix}", dpi=200)
    plt.close(fig)
    print(frames["additivity"].to_string(index=False))
    print(json.dumps(checks))


if __name__ == "__main__":
    main()
