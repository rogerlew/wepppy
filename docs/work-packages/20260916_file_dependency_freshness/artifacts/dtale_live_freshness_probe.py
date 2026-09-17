"""Disposable live D-Tale route probe plus real isolated GeoJSON registration.

Run: wctl exec dtale python <this repository path>
Uses the configured secret internally; never emits credentials. Only temporary
batch data and this package's retained artifacts are written. No service restart
or application monkeypatch is used.
"""
import importlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.config.secrets import get_secret


ARTIFACTS = Path(__file__).parent
FIXTURES = ARTIFACTS / "dtale_probe_inputs"
FIXTURES.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:9010"
TOKEN = get_secret("DTALE_INTERNAL_TOKEN") or ""
DATA_IDS = []


def request(path, payload=None, query=None):
    if query:
        path += "?" + urlencode(query)
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request(BASE + path, data=data, headers={
        "Content-Type": "application/json", "X-DTALE-TOKEN": TOKEN,
    })
    started = perf_counter()
    try:
        with urlopen(req, timeout=30) as response:
            status, body = response.status, response.read().decode()
    except HTTPError as exc:
        status, body = exc.code, exc.read().decode()
    try:
        body = json.loads(body)
    except json.JSONDecodeError:
        pass
    return {"status": status, "elapsed_seconds": perf_counter() - started, "body": body}


def load(runid, path):
    result = request("/internal/load", {"runid": runid, "config": "batch", "path": path})
    if result["status"] == 200:
        identity = result["body"]["data_id"]
        if identity not in DATA_IDS:
            DATA_IDS.append(identity)
    return result


def grid(identity):
    return request(f"/dtale/data/{identity}", query={"ids": json.dumps(["0-1"])})


def exercise(root, filename, old_bytes, new_bytes):
    assert len(old_bytes) == len(new_bytes)
    path = root / filename
    (FIXTURES / ("before_" + filename)).write_bytes(old_bytes)
    (FIXTURES / ("after_" + filename)).write_bytes(new_bytes)
    path.write_bytes(old_bytes)
    original = path.stat()
    first = load(root.name, filename)
    if first["status"] != 200:
        return {"first_load": first, "blocked": "Initial live load failed"}
    identity = first["body"]["data_id"]
    before_grid = grid(identity)
    path.write_bytes(new_bytes)
    os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
    rewritten = path.stat()
    second = load(root.name, filename)
    after_grid = grid(identity)
    os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns + 2_000_000_000))
    control = load(root.name, filename)
    control_grid = grid(identity)
    return {
        "bytes": len(old_bytes),
        "equal_size": rewritten.st_size == original.st_size,
        "restored_mtime": rewritten.st_mtime_ns == original.st_mtime_ns,
        "first_load": first, "before_grid": before_grid,
        "same_metadata_load": second, "after_grid": after_grid,
        "changed_mtime_control_load": control, "control_grid": control_grid,
    }


results = {"uid": os.getuid(), "gid": os.getgid(), "health": request("/health")}
batch_root = Path(os.getenv("BATCH_RUNNER_ROOT", "/wc1/batch"))
with TemporaryDirectory(prefix="freshness-c11-", dir=batch_root) as temporary:
    root = Path(temporary)
    results["disposable_batch"] = str(root)
    try:
        results["eager_csv"] = exercise(root, "table.csv", b"a,b\n1,x\n2,y\n", b"a,b\n8,x\n9,y\n")
        parquet_bytes = []
        for column, values in (("a", [1, 2]), ("z", [8, 9])):
            sink = pa.BufferOutputStream()
            pq.write_table(pa.table({column: values}), sink, compression="NONE",
                           write_statistics=False, use_dictionary=False)
            parquet_bytes.append(sink.getvalue().to_pybytes())
        results["lazy_parquet"] = exercise(root, "table.parquet", *parquet_bytes)
    finally:
        if DATA_IDS:
            results["cleanup_live_datasets"] = request(
                "/dtale/cleanup-datasets", query={"dataIds": ",".join(DATA_IDS)},
            )

# Separate actual maintained registration function; it has no inspection HTTP
# endpoint. This process uses real D-Tale state and parsing, with no stubs.
module = importlib.import_module("wepppy.webservices.dtale.dtale")
with TemporaryDirectory(prefix="freshness-c11-geo-") as temporary:
    path = Path(temporary) / "features.geojson"
    feature = {"type": "FeatureCollection", "features": [{"type": "Feature",
        "properties": {"wepp_id": 1, "label": "old"},
        "geometry": {"type": "Point", "coordinates": [1, 2]}}]}
    old_bytes = json.dumps(feature, separators=(",", ":")).encode()
    feature["features"][0]["properties"]["label"] = "new"
    new_bytes = json.dumps(feature, separators=(",", ":")).encode()
    assert len(old_bytes) == len(new_bytes)
    path.write_bytes(old_bytes)
    original = path.stat()
    def register_and_read():
        key, featureidkey = module._register_geojson_asset("freshness-c11", "probe", path)
        entry = next(item for item in module.dtale_custom_geojson.CUSTOM_GEOJSON if item["key"] == key)
        return {"fingerprint": entry["_fingerprint"],
                "label": entry["data"]["features"][0]["properties"]["label"]}
    first = register_and_read()
    path.write_bytes(new_bytes)
    os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
    second = register_and_read()
    os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns + 2_000_000_000))
    control = register_and_read()
    (FIXTURES / "before_features.geojson").write_bytes(old_bytes)
    (FIXTURES / "after_features.geojson").write_bytes(new_bytes)
    results["isolated_real_geojson_registration"] = {
        "bytes": len(old_bytes), "first": first, "same_metadata": second,
        "changed_mtime_control": control,
    }

output = ARTIFACTS / "dtale_live_freshness_probe.json"
output.write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2))
