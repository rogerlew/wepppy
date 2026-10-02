"""Disposable S04/S08 regression probes; print booleans, never inspect real run data.

Run: wctl exec -T weppcloud python <repository-relative path to this file>
Expected after containment: both records report ``private_canary_read=false``;
S04 reports ``external_read=blocked`` and S08 reports HTTP 403.
"""
import importlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq
import duckdb

from wepppy.query_engine.app.feature_access import require_datasets
from wepppy.query_engine.catalog import CatalogEntry, DatasetCatalog
from wepppy.query_engine.context import RunContext
from wepppy.query_engine.core import run_query
from wepppy.query_engine.payload import QueryRequest


def main():
    with TemporaryDirectory(prefix="fa02-private-proof-") as name:
        root = Path(name)
        public = root / "public"
        public.mkdir()
        private = root / "batch/private"
        private.mkdir(parents=True)
        os.environ["BATCH_RUNNER_ROOT"] = str(root / "batch")
        pq.write_table(pa.table({"id": [1]}), public / "data.parquet")
        source = private / "result.parquet"
        pq.write_table(pa.table({"value": ["synthetic-private-canary"]}), source)
        entry = CatalogEntry("data.parquet", ".parquet", 0, "")
        context = RunContext("public", public, None, DatasetCatalog(public, [entry]))
        request = SimpleNamespace(state=SimpleNamespace(), path_params={}, headers={}, cookies={})
        require_datasets(request, public, [entry.path], entries=[entry])
        query = QueryRequest(datasets=[entry.path], computed_columns=[{
            "alias": "leak", "sql": f"(SELECT value FROM read_parquet('{source}'))",
        }])
        try:
            result = run_query(context, query)
        except duckdb.PermissionException:
            print(json.dumps({"finding": "S04", "declared_dataset_admission": "allowed",
                              "private_canary_read": False, "external_read": "blocked"}))
        else:
            print(json.dumps({"finding": "S04", "declared_dataset_admission": "allowed",
                              "private_canary_read": any(row.get("leak") == "synthetic-private-canary"
                                                         for row in result.records)}))

        module = importlib.import_module("wepppy.webservices.dtale.dtale")
        module.DTALE_INTERNAL_TOKEN = "disposable-proof-token"
        # Optional NoDb map discovery is independent of table authorization.
        module._ensure_geojson_assets = lambda *args: None
        (private / "data.csv").write_text("value\nsynthetic-private-canary\n")
        loaded = module.app.test_client().post("/internal/load", json={
            "runid": "private", "config": "batch", "path": "data.csv",
            "resource_public": False,
            "access_claims": {
                "token_class": "user", "sub": "reproduction-user",
                "jti": "reproduction-token", "exp": 4_102_444_800,
            },
            "feature_id": "batch_runner",
        }, headers={"X-DTALE-TOKEN": "disposable-proof-token"})
        assert loaded.status_code == 200, loaded.status_code
        data_id = loaded.json["data_id"]
        try:
            anonymous = module.app.test_client().get(f"/dtale/data/{data_id}",
                                                      query_string={"ids": json.dumps(["0-1"])})
            print(json.dumps({"finding": "S08", "load_status": loaded.status_code,
                              "anonymous_grid_status": anonymous.status_code,
                              "private_canary_read": "synthetic-private-canary" in anonymous.get_data(as_text=True)}))
        finally:
            module._discard_dataset(data_id)


if __name__ == "__main__":
    main()
