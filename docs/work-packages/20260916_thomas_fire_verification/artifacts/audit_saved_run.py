"""Independent arithmetic/raster audit. Run reads only; evidence writes here only."""
import hashlib
import csv
import json
import math
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import rasterio
from wepppy.nodb.mods.postfire_debris_flow import report

RUN = Path("/wc1/runs/ne/nervous-mesquite")
OUT = Path(__file__).resolve().parent
MODULE = RUN / "postfire_debris_flow"
ATTEMPT = "a909f2c1b3c0468084d31a8cdd0e24f2"
PRED = MODULE / "attempts" / ATTEMPT / "predictors"
# Published M1 rows; https://ghsc.code-pages.usgs.gov/lhp/pfdf/guide/models/s17.html
COEFFICIENTS = {15: (-3.63, .41, .67, .70), 30: (-3.61, .26, .39, .50),
                60: (-3.21, .17, .20, .22)}


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    with rasterio.open(path) as src:
        return src.read(1, masked=True).astype("float64"), src.transform


def main():
    manifest = json.loads((MODULE / "manifest.json").read_text())
    snapshot = manifest["predictor_snapshot"]
    tracked = set(MODULE.rglob("*.json")) | set(MODULE.rglob("*.tif")) | set(MODULE.rglob("*.parquet"))
    tracked |= set(RUN.glob("*.nodb")) | {RUN / "redisprep.dump"}
    recorded = dict(manifest["sources_sha256"])
    recorded.update(snapshot["sources_sha256"])
    recorded.update({str(PRED / "prepared" / n): v for n, v in snapshot["prepared_sha256"].items()})
    tracked |= {Path(p) for p in recorded}
    before = {str(p.relative_to(RUN)): sha(p) for p in sorted(tracked) if p.is_file()}
    mismatches = [p for p, expected in recorded.items() if sha(Path(p)) != expected]
    tables = {n: pq.read_table(MODULE / (n + ".parquet")).to_pylist()
              for n in ("design", "events", "inverse")}
    climate = pq.read_table(RUN / "climate/wepp_cli.parquet").to_pylist()
    rainfall_errors = []
    for row in tables["events"]:
        source = climate[row["row_ordinal"]]
        rainfall_errors.append(abs(row["intensity_mm_per_hour"] - source[f"peak_intensity_{row['duration_minutes']}"]))
        assert (row["year"],row["month"],row["day_of_month"],row["precipitation_mm"]) == (source["year"],source["month"],source["day_of_month"],source["prcp"])
    with (RUN / "climate/atlas14_intensity_pds_mean_metric.csv").open() as stream:
        lines = list(csv.reader(stream))
    header = [v.strip() for v in next(r for r in lines if r and r[0].startswith("by duration for ARI"))]
    # The first matching rows are the mean table, before confidence bounds.
    noaa = {d: next(r for r in lines if r and r[0] == f"{d}-min:") for d in (15,30,60)}
    noaa_errors = [abs(row["intensity_mm_per_hour"] - float(noaa[row["duration_minutes"]][header.index(str(row["return_interval_years"]))])) for row in tables["design"]]
    table_hashes = {n: sha(MODULE / (n + ".parquet")) == manifest["tables"][n]["sha256"] for n in tables}
    T, F, S = [snapshot["predictors"][k]["value"] for k in ("T", "F", "S")]

    def probability(duration, rainfall, soil=S):
        b, ct, cf, cs = COEFFICIENTS[duration]
        return 1 / (1 + math.exp(-(b + rainfall * (ct*T + cf*F + cs*soil))))

    checks = {}
    for name, rows in tables.items():
        available = [r for r in rows if r["status"] == "available"]
        errors, units = [], []
        for row in available:
            d = row["duration_minutes"]
            units.append(abs(row["rainfall_mm"] - row["intensity_mm_per_hour"] * d / 60))
            expected = row["target_probability"] if name == "inverse" else row["probability"]
            errors.append(abs(probability(d, row["rainfall_mm"]) - expected))
        checks[name] = dict(rows=len(rows), available=len(available),
                            max_probability_error=max(errors), max_unit_error_mm=max(units))

    common, transform = read(PRED / "valid_mask.tif")
    use = common.filled(0) > 0
    basin, _ = read(PRED / "prepared/mask.tif")
    basin_use = basin.filled(0) > 0
    dnbr, _ = read(PRED / "prepared/dnbr.tif")
    soil, soil_transform = read(RUN / "rusle/k_polaris_nomograph.tif")
    intersection, _ = read(PRED / "wbt/intersection.tif")
    sbs, _ = read(PRED / "prepared/sbs.tif")
    dem, _ = read(PRED / "prepared/dem.tif")
    slope, _ = read(PRED / "wbt/slope.tif")
    assert soil_transform == transform and soil.shape == common.shape
    independent = dict(T=float(intersection[use].mean()), F=float(dnbr[use].mean()), S=float(soil[use].mean()))
    z = dem.filled(np.nan)
    dzdx = ((z[:-2, 2:] + 2*z[1:-1, 2:] + z[2:, 2:]) -
            (z[:-2, :-2] + 2*z[1:-1, :-2] + z[2:, :-2])) / (8*transform.a)
    dzdy = ((z[2:, :-2] + 2*z[2:, 1:-1] + z[2:, 2:]) -
            (z[:-2, :-2] + 2*z[:-2, 1:-1] + z[:-2, 2:])) / (8*abs(transform.e))
    horn = np.full(z.shape, np.nan)
    horn[1:-1, 1:-1] = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    comparable = basin_use & np.isfinite(horn) & ~np.ma.getmaskarray(slope)
    steep = horn >= 23
    burned = np.isin(sbs.filled(-9999), [2, 3])
    known = (~steep & np.isfinite(horn)) | ~np.ma.getmaskarray(sbs)
    independent_intersection = steep & burned
    raster = dict(basin_cells=int(basin_use.sum()), common_cells=int(use.sum()),
                  area_km2=float(basin_use.sum()*abs(transform.a*transform.e)/1e6),
                  independent_predictors=independent,
                  predictor_abs_errors={k: abs(independent[k]-v) for k,v in zip(("T","F","S"),(T,F,S))},
                  max_horn_slope_error_degrees=float(np.max(np.abs(horn[comparable]-slope[comparable]))),
                  horn_threshold_disagreements=int(np.sum((steep != (slope.filled(-1)>=23)) & comparable)),
                  intersection_disagreements=int(np.sum((independent_intersection != (intersection.filled(-1)>0)) & use & known)),
                  mod_high_fraction_all_basin=float((burned & basin_use).sum()/basin_use.sum()),
                  sbs_unknown_basin=int((np.ma.getmaskarray(sbs) & basin_use).sum()))
    state = json.loads((RUN / "postfire_debris_flow.nodb").read_text())["py/state"]
    assessment = report.open_assessment(RUN, state["_config"], expected_attempt=ATTEMPT)
    projected = report.view(assessment)
    report_check = dict(attempt_id=projected["attempt_id"], summary=projected["summary"],
                        design_matches=projected["design"] == tables["design"],
                        inverse_matches=projected["inverse"] == tables["inverse"],
                        event_rows_in_selected_duration=projected["events"]["unfiltered_total"])
    after = {str(p.relative_to(RUN)): sha(p) for p in sorted(tracked) if p.is_file()}
    evidence = dict(run="nervous-mesquite", attempt=ATTEMPT, model=manifest["model"],
                    source_hash_mismatches=mismatches, table_hashes_match=table_hashes,
                    arithmetic=checks, raster=raster, report=report_check,
                    rainfall_source_checks=dict(max_event_intensity_error=max(rainfall_errors),
                                                max_noaa_design_intensity_error=max(noaa_errors),
                                                january_9_2018_cli={k:climate[13888][k] for k in ("prcp","dur","tp","ip")}),
                    design=tables["design"], inverse=tables["inverse"],
                    january_9_2018=[r for r in tables["events"] if (r["year"],r["month"],r["day_of_month"]) == (2018,1,9)],
                    same_storm=dict(I15_mm_h=24, rainfall_mm=6, probability=probability(15,6),
                                    published_san_ysidro_probability=.69,
                                    soil_only_counterfactual_for_69=(math.log(.69/.31)+3.63-6*(.41*T+.67*F))/(6*.70)),
                    monitored_files=len(before), unchanged=before == after, before_sha256=before,
                    changed_files=[p for p in before if before[p] != after.get(p)])
    (OUT / "saved_run_audit.json").write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k:v for k,v in evidence.items() if k not in ("before_sha256","design","report")}, indent=2))
    assert not mismatches and all(table_hashes.values()) and before == after
    assert max(rainfall_errors) == max(noaa_errors) == 0
    assert all(v["max_probability_error"] < 1e-12 and v["max_unit_error_mm"] < 1e-12 for v in checks.values())
    assert all(v < 1e-12 for v in raster["predictor_abs_errors"].values())
    assert raster["horn_threshold_disagreements"] == raster["intersection_disagreements"] == 0
    assert report_check["design_matches"] and report_check["inverse_matches"]


if __name__ == "__main__":
    main()
