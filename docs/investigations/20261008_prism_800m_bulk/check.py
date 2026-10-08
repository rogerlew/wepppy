"""Bounded live PRISM experiment; not a production client or cache.

Run the phases documented in findings.md from any directory.
Successful downloads are reused so rerunning analysis does not hit PRISM.
Raw CSV bytes are retained losslessly as gzip alongside request evidence.
"""

import argparse
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import time
from urllib.parse import urljoin
import zipfile

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import Affine
import requests


OUT = Path(__file__).resolve().parent / "evidence"
RPC = "https://prism.oregonstate.edu/explorer/dataexplorer/rpc.php"
VARIABLES = "ppt tmin tmax tdmean soltotal"
COLS = ["ppt (mm)", "tmin (degrees C)", "tmax (degrees C)",
        "tdmean (degrees C)", "soltotal (MJ/m^2/day)"]
SITES = {
    "palouse": (-116.5, 46.5),
    "olympic": (-123.7, 47.8),
    "sierra": (-119.5, 37.7),
    "deathvalley": (-116.87, 36.46),
    "rockies": (-105.64, 40.28),
    "tucson": (-110.97, 32.22),
    "oklahoma": (-97.44, 35.18),
    "houston": (-95.37, 29.76),
    "asheville": (-82.55, 35.60),
    "miami": (-80.19, 25.76),
    "maine": (-68.59, 45.90),
    "duluth": (-92.10, 46.79),
}


def write_json(name, value):
    (OUT / f"{name}.json").write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def request(label, url, data=None):
    start = time.monotonic()
    response = requests.get(url, timeout=(15, 60)) if data is None else requests.post(
        url, data=data, timeout=(15, 60)
    )
    write_json(label, {
        "url": url, "request": data, "status": response.status_code,
        "seconds": time.monotonic() - start, "headers": dict(response.headers),
        "body": response.text,
    })
    response.raise_for_status()
    return response


def geometry():
    meta = json.loads((OUT / "grid_geometry.json").read_text())
    return Affine(*meta["transform"][:6]), meta


def initialize_grid():
    """Acquire one actual grid to establish geometry, never infer it from 4 km."""
    if (OUT / "grid_geometry.json").exists():
        return
    url = "https://services.nacse.org/prism/data/get/us/800m/ppt/20200101"
    start = time.monotonic()
    response = requests.get(url, timeout=(15, 60))
    response.raise_for_status()
    archive = Path("/tmp/prism_800m_ppt_20200101.zip")
    archive.write_bytes(response.content)
    with zipfile.ZipFile(archive) as z:
        tif = next(n for n in z.namelist() if n.endswith(".tif"))
    with rasterio.open(f"/vsizip/{archive}/{tif}") as ds:
        write_json("grid_geometry", dict(url=url, headers=dict(response.headers),
            bytes=len(response.content), seconds=time.monotonic()-start,
            sha256=hashlib.sha256(response.content).hexdigest(), local_archive=str(archive),
            crs=ds.crs.to_string(), transform=list(ds.transform), width=ds.width,
            height=ds.height, nodata=ds.nodata, bounds=list(ds.bounds), tags=ds.tags()))


def snap(lon, lat):
    """Native NAD83 grid axes; WGS84/NAD83 operation must be explicit in production."""
    transform, meta = geometry()
    col_float, row_float = ~transform * (lon, lat)
    row, col = math.floor(row_float), math.floor(col_float)
    if not (0 <= row < meta["height"] and 0 <= col < meta["width"]):
        raise ValueError("Outside PRISM grid extent")
    x, y = transform * (col + 0.5, row + 0.5)
    return {"lon": round(x, 10), "lat": round(y, 10), "row": row, "col": col}


def sample_locations():
    locations = []
    transform, _ = geometry()
    for name, (lon, lat) in SITES.items():
        center = snap(lon, lat)
        locations.append(dict(name=name, original_lon=lon, original_lat=lat, **center))
        if name in ("sierra", "tucson", "oklahoma", "asheville"):
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == dc == 0:
                        continue
                    x, y = transform * (center["col"] + dc + 0.5, center["row"] + dr + 0.5)
                    locations.append(dict(name=f"{name[:5]}{dr+1}{dc+1}", **snap(x, y)))
    for name, lon, lat in (("pacific", -124.9, 40.0), ("superior", -88.0, 47.5),
                           ("coast", -124.40, 42.0), ("keywest", -81.78, 24.56)):
        locations.append(dict(name=name, **snap(lon, lat)))
    for name, lon, lat in (("pal_orig", -116.5, 46.5), ("sier_orig", -119.5, 37.7)):
        locations.append(dict(name=name, **dict(snap(lon, lat), lon=lon, lat=lat)))
    center = snap(*SITES["palouse"])
    for name, offset in (("pal_sw", -0.002), ("pal_ne", 0.002)):
        locations.append(dict(name=name, **dict(center, lon=center["lon"]+offset,
                                              lat=center["lat"]+offset)))
    return locations


def bulk(label, locations, start, end, stability="stable"):
    destination = OUT / f"{label}.csv.gz"
    if destination.exists():
        print(label, "using retained CSV", flush=True)
        return
    params = dict(spares="800m", interp="0", stats=VARIABLES, units="si", range="daily",
                  start=start, end=end, stability=stability, call="pp/daily_timeseries_mp",
                  proc="gridserv", lons="|".join(str(p["lon"]) for p in locations),
                  lats="|".join(str(p["lat"]) for p in locations),
                  names="|".join(p["name"] for p in locations))
    begin = time.monotonic()
    response = request(label + "_submit", RPC, params).json()
    ticket = response.get("gricket")
    polls = 0
    while "result" not in response:
        if response.get("errors"):
            raise ValueError(response["errors"])
        if not ticket or "delay" not in response:
            raise ValueError(f"Unexpected response: {response}")
        if time.monotonic() - begin > 600:
            raise TimeoutError(f"Retained ticket {ticket}; resume polling explicitly")
        time.sleep(5)
        polls += 1
        response = request(f"{label}_poll_{polls}", RPC, {
            "call": "pp/checkup", "proc": "gridserv", "gricket": ticket,
        }).json()
    if response.get("errors"):
        raise ValueError(response["errors"])
    ready = time.monotonic() - begin
    csv_url = urljoin("https://prism.oregonstate.edu/explorer/tmp/", response["result"]["csv"])
    download = requests.get(csv_url, timeout=(15, 60))
    download.raise_for_status()
    raw = download.content
    if b"Name,Longitude,Latitude" not in raw:
        raise ValueError("Response does not contain a PRISM CSV header")
    destination.write_bytes(gzip.compress(raw, mtime=0))
    result = dict(locations=len(locations), start=start, end=end, ready_seconds=ready,
                  total_seconds=time.monotonic()-begin, polls=polls, csv_url=csv_url,
                  headers=dict(download.headers), bytes=len(raw),
                  sha256=hashlib.sha256(raw).hexdigest())
    write_json(label + "_download", result)
    print(label, result, flush=True)


def read_csv(path):
    text = gzip.decompress(path.read_bytes()).decode("utf-8-sig")
    lines = text.splitlines()
    header = next(i for i, line in enumerate(lines) if line.startswith("Name,Longitude,Latitude"))
    return pd.read_csv(io.StringIO("\n".join(lines[header:]))), lines[:header]


def analyze():
    reports = {}
    for path in sorted(OUT.glob("*.csv.gz")):
        label = path.name.removesuffix(".csv.gz")
        df, metadata = read_csv(path)
        info = json.loads((OUT / f"{label}_download.json").read_text())
        expected_dates = pd.date_range(info["start"], info["end"])
        metrics = dict(rows=len(df), locations=int(df.Name.nunique()),
                       expected_rows=info["locations"]*len(expected_dates),
                       duplicates=int(df.duplicated(["Name", "Date"]).sum()), metadata=metadata)
        submitted = json.loads((OUT / f"{label}_submit.json").read_text())["request"]["names"].split("|")
        metrics["omitted_locations"] = sorted(set(submitted) - set(df.Name))
        metrics["unexpected_locations"] = sorted(set(df.Name) - set(submitted))
        metrics["calendar_mismatches"] = [name for name, g in df.groupby("Name")
            if list(pd.to_datetime(g.Date)) != list(expected_dates)]
        values = df[COLS].apply(pd.to_numeric, errors="coerce")
        metrics["nonfinite"] = {k:int((~np.isfinite(values[k])).sum()) for k in COLS}
        metrics["sentinel_minus9999"] = {k:int((values[k] == -9999).sum()) for k in COLS}
        valid = values.mask(values <= -9990)
        metrics["ranges"] = {k:[float(valid[k].min()), float(valid[k].max())] for k in COLS}
        metrics["negative_ppt"] = int((valid[COLS[0]] < 0).sum())
        metrics["negative_solar"] = int((valid[COLS[4]] < 0).sum())
        metrics["tmin_gt_tmax"] = int((valid[COLS[1]] > valid[COLS[2]]).sum())
        metrics["dew_below_tmin"] = int((valid[COLS[3]] < valid[COLS[1]]).sum())
        metrics["dew_above_tmax"] = int((valid[COLS[3]] > valid[COLS[2]]).sum())
        metrics["locations_with_missing"] = sorted(df.loc[values.isna().any(axis=1) |
            (values <= -9990).any(axis=1), "Name"].unique().tolist())
        metrics["per_location"] = {}
        for name, group in df.groupby("Name"):
            v = valid.loc[group.index]
            metrics["per_location"][name] = {
                "rows":len(group), "missing_rows":int(v.isna().any(axis=1).sum()),
                "ppt_sum_mm":float(v[COLS[0]].sum()), "ppt_max_mm":float(v[COLS[0]].max()),
                "wet_days":int((v[COLS[0]] > 0).sum()),
                "dew_below_tmin":int((v[COLS[3]] < v[COLS[1]]).sum()),
            }
        metrics["same_cell_comparisons"] = {}
        for target, other in (("palouse", "pal_orig"), ("palouse", "pal_sw"),
                              ("palouse", "pal_ne"), ("sierra", "sier_orig")):
            if other in set(df.Name):
                a = values.loc[df.Name == target].to_numpy()
                b = values.loc[df.Name == other].to_numpy()
                metrics["same_cell_comparisons"][other] = bool(np.array_equal(a, b, equal_nan=True))
        if label == "sample_2020":
            spatial = {}
            for name, prefix in (("sierra", "sierr"), ("tucson", "tucso"),
                                 ("oklahoma", "oklah"), ("asheville", "ashev")):
                group = df[(df.Name == name) | df.Name.str.match(prefix + "[0-2][0-2]$")]
                table = group.pivot(index="Date", columns="Name", values=COLS[0])
                spatial[name] = dict(cells=table.shape[1], mixed_wet_dry_days=int(
                    ((table.min(axis=1) == 0) & (table.max(axis=1) > 0)).sum()),
                    max_daily_spatial_range_mm=float((table.max(axis=1)-table.min(axis=1)).max()),
                    annual_total_range_mm=[float(table.sum().min()), float(table.sum().max())])
            write_json("spatial_2020", spatial)
        reports[label] = metrics
        print(label, {k:v for k,v in metrics.items() if k not in ("per_location", "metadata")})
    # JSON nulls explicitly represent entirely missing locations, not zeros.
    def clean(obj):
        if isinstance(obj, float) and not math.isfinite(obj):
            return None
        if isinstance(obj, dict):
            return {k:clean(v) for k,v in obj.items()}
        if isinstance(obj, list):
            return [clean(v) for v in obj]
        return obj
    write_json("analysis", clean(reports))


def parity():
    """Compare parsed bulk artifacts with independent point and grid products."""
    locations = json.loads((OUT / "locations.json").read_text())
    for variable, date, label, column in (
        ("ppt", "20200101", "sample_2020", COLS[0]),
        ("ppt", "20261001", "sample_recent", COLS[0]),
        ("soltotal", "20200101", "sample_2020", COLS[4]),
    ):
        url = f"https://services.nacse.org/prism/data/get/us/800m/{variable}/{date}"
        archive = Path(f"/tmp/prism_800m_{variable}_{date}.zip")
        evidence_name = f"grid_{variable}_{date}"
        if not archive.exists():
            start = time.monotonic()
            response = requests.get(url, timeout=(15, 60))
            response.raise_for_status()
            archive.write_bytes(response.content)
            write_json(evidence_name + "_download", dict(url=url, headers=dict(response.headers),
                seconds=time.monotonic()-start, bytes=len(response.content),
                sha256=hashlib.sha256(response.content).hexdigest()))
        with zipfile.ZipFile(archive) as z:
            tif = next(n for n in z.namelist() if n.endswith(".tif"))
            for name in z.namelist():
                if name.endswith((".info.txt", ".prj", ".xml")):
                    (OUT / Path(name).name).write_bytes(z.read(name))
        df, _ = read_csv(OUT / f"{label}.csv.gz")
        df = df[df.Date == pd.Timestamp(date).strftime("%Y-%m-%d")]
        rows = []
        with rasterio.open(f"/vsizip/{archive}/{tif}") as ds:
            transform, meta = geometry()
            if ds.transform != transform or (ds.width, ds.height) != (meta["width"], meta["height"]):
                raise ValueError("Grid geometry changed")
            for loc in locations:
                val = float(ds.read(1, window=((loc["row"], loc["row"]+1),
                                              (loc["col"], loc["col"]+1)))[0, 0])
                selected = df[df.Name == loc["name"]]
                bulk_value = None if selected.empty else float(selected.iloc[0][column])
                rows.append(dict(name=loc["name"], row=loc["row"], col=loc["col"],
                                 grid=val, bulk=bulk_value,
                                 difference=None if bulk_value is None else bulk_value-val))
            write_json(evidence_name + "_samples", dict(tags=ds.tags(), crs=ds.crs.to_string(),
                nodata=ds.nodata, transform=list(ds.transform), rows=rows,
                archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))
        print(evidence_name, "max absolute difference", max(
            abs(p["difference"]) for p in rows if p["difference"] is not None), flush=True)
    for name in ("palouse", "deathvalley", "miami"):
        loc = next(p for p in locations if p["name"] == name)
        params = dict(spares="800m", interp="0", stats=VARIABLES, units="si", range="daily",
                      start="20200101", end="20201231", stability="stable",
                      call="pp/daily_timeseries", proc="gridserv", lon=loc["lon"], lat=loc["lat"])
        body = request(f"point_{name}_2020", RPC, params).json()
        point = body["result"]["data"]
        df, _ = read_csv(OUT / "sample_2020.csv.gz")
        bulk_values = df.loc[df.Name == name, COLS]
        comparisons = {var:bool(np.array_equal(np.array(point[var]), bulk_values[col].to_numpy()))
                       for var, col in zip(VARIABLES.split(), COLS)}
        write_json(f"point_{name}_comparison", comparisons)
        print(name, comparisons, flush=True)


def freshness():
    base = "https://services.nacse.org/prism/data/get/"
    for variable in VARIABLES.split():
        for period in ("19810101/19810103", "20200101/20201231", "20261001/20261007"):
            label = f"release_{variable}_{period.replace('/', '_')}"
            request(label, f"{base}releaseDate/us/800m/{variable}/{period}?json=true")
            time.sleep(1)


def extra_probes():
    locations = sample_locations()[:2]
    bulk("label_stable_recent", locations, "20261001", "20261007", "stable")
    params = dict(spares="800m", interp="0", stats=VARIABLES, units="si", range="daily",
                  start="20261007", end="20261010", stability="early",
                  lon=locations[0]["lon"], lat=locations[0]["lat"],
                  call="pp/daily_timeseries", proc="gridserv")
    request("point_unpublished_dates", RPC, params)
    base = "https://services.nacse.org/prism/data/get/"
    request("release_unpublished_dates", base +
            "releaseDate/us/800m/ppt/20261007/20261010?json=true")
    for variable in VARIABLES.split():
        request(f"release_after_{variable}_recent", base +
                f"releaseDate/us/800m/{variable}/20261001/20261007?json=true")
        time.sleep(1)


def verify():
    """Offline acceptance for this retained experiment, including expected omissions."""
    reports = json.loads((OUT / "analysis.json").read_text())
    for label, metrics in reports.items():
        download = json.loads((OUT / f"{label}_download.json").read_text())
        raw = gzip.decompress((OUT / f"{label}.csv.gz").read_bytes())
        assert len(raw) == download["bytes"]
        assert hashlib.sha256(raw).hexdigest() == download["sha256"]
        expected_omissions = ["coast", "pacific"] if label.startswith("sample_") else []
        assert metrics["omitted_locations"] == expected_omissions, (label, metrics)
        assert not metrics["unexpected_locations"]
        assert not metrics["calendar_mismatches"]
        assert metrics["duplicates"] == 0
        assert all(n == 0 for n in metrics["nonfinite"].values())
        assert all(n == 0 for n in metrics["sentinel_minus9999"].values())
        assert metrics["negative_ppt"] == metrics["negative_solar"] == metrics["tmin_gt_tmax"] == 0
        assert all(metrics["same_cell_comparisons"].values())
        days = len(pd.date_range(download["start"], download["end"]))
        assert metrics["rows"] == (download["locations"] - len(expected_omissions)) * days
    for path in OUT.glob("grid_*_samples.json"):
        data = json.loads(path.read_text())
        for row in data["rows"]:
            if row["bulk"] is None:
                assert row["grid"] == data["nodata"]
            else:
                assert abs(row["difference"]) <= 0.00501, row  # CSV 0.01 display precision + float error
    for name in ("palouse", "deathvalley", "miami"):
        assert all(json.loads((OUT / f"point_{name}_comparison.json").read_text()).values())
    small, _ = read_csv(OUT / "scale_100.csv.gz")
    large, _ = read_csv(OUT / "scale_500.csv.gz")
    subset = large[large.Name.isin(small.Name)].reset_index(drop=True)
    pd.testing.assert_frame_equal(small, subset)
    for variable in VARIABLES.split():
        before = json.loads((OUT / f"release_{variable}_20261001_20261007.json").read_text())
        after = json.loads((OUT / f"release_after_{variable}_recent.json").read_text())
        assert json.loads(before["body"]) == json.loads(after["body"])
    write_json("verification", dict(status="passed", reports=len(reports),
        primary_rows=sum(v["rows"] for k,v in reports.items() if k != "label_stable_recent"),
        limitations="Sampled access/parity only; no provider revision transition or WEPP execution tested."))
    print("PASS: completeness, known masked omissions, physical checks, cell identity, point/grid parity, "
          "batch-size invariance, and unchanged recent revision manifests")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["grid", "sample", "scale", "freshness", "parity",
                                         "extras", "analyze", "verify"])
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    if args.phase == "grid":
        initialize_grid()
    elif args.phase == "sample":
        locations = sample_locations()
        write_json("locations", locations)
        for year in (1981, 2020, 2025):
            bulk(f"sample_{year}", locations, f"{year}0101", f"{year}1231")
        bulk("sample_recent", locations, "20261001", "20261007", "early")
    elif args.phase == "scale":
        transform, _ = geometry()
        center = snap(*SITES["oklahoma"])
        locations = []
        for dr in range(20):
            for dc in range(25):
                lon, lat = transform * (center["col"]+dc+0.5, center["row"]+dr+0.5)
                locations.append(dict(name=f"r{dr}c{dc}", **snap(lon, lat)))
        write_json("scale_locations", locations)
        bulk("scale_100", locations[:100], "20200101", "20201231")
        bulk("scale_500", locations, "20200101", "20201231")
    elif args.phase == "freshness":
        freshness()
    elif args.phase == "parity":
        parity()
    elif args.phase == "extras":
        extra_probes()
    elif args.phase == "verify":
        verify()
    else:
        analyze()
