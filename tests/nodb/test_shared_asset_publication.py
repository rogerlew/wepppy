"""Exercise both producers, query publication and Feature Export on the same bytes."""
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from wepppy.nodb.mods.features_export import (
    build_dependency_snapshot,
    load_layer_catalog,
    resolve_export_plan,
)
from wepppy.query_engine.catalog import load_catalog
from wepppy.query_engine.catalog_refresh import pending_catalog_requests, refresh_catalog
from wepppy.query_engine.context import RunContext
from wepppy.query_engine.core import run_query
from wepppy.query_engine.payload import QueryRequest
from wepppy.topo.peridot.peridot_runner import post_abstract_watershed
from wepppy.wepp.interchange.watershed_interchange import run_wepp_watershed_interchange

pytestmark = pytest.mark.unit


def test_managed_publications_reach_both_consumers(tmp_path, monkeypatch):
    root = tmp_path / "runs"
    wd = root / "ab" / "ab-test"
    watershed = wd / "watershed"
    watershed.mkdir(parents=True)
    header = "topaz_id,area,centroid_lon,centroid_lat\n"
    (watershed / "hillslopes.csv").write_text(header + "11,900,-116,46\n")
    (watershed / "channels.csv").write_text(header + "14,100,-116,46\n")
    output = wd / "wepp/output"
    output.mkdir(parents=True)
    fixture = Path(__file__).resolve().parents[1] / "wepp/interchange/test_project/output"
    shutil.copyfile(fixture / "loss_pw0.txt", output / "loss_pw0.txt")

    monkeypatch.setenv("QUERY_CATALOG_REFRESH_ENABLED", "true")
    monkeypatch.setenv("QUERY_CATALOG_ROOTS_JSON", json.dumps([{
        "path": str(root), "layout": "sharded", "namespace": "test:runs",
        "coordination": str(tmp_path / "locks"),
    }]))
    monkeypatch.setattr(
        "wepppy.rq.query_catalog_rq.enqueue_catalog_refresh", lambda *a, **kw: {"state": "pending"}
    )

    post_abstract_watershed(str(wd), verbose=False)
    run_wepp_watershed_interchange(
        output, pass_family="hbp", run_ebe_interchange=False, run_chan_out_interchange=False,
        run_soil_interchange=False, run_chnwb_interchange=False,
    )

    assert sorted(r["asset_path"] for r in pending_catalog_requests(wd)) == [
        "watershed", "wepp/output/interchange",
    ]
    refresh_catalog(wd)
    assert not pending_catalog_requests(wd)
    catalog = load_catalog(wd)
    context = RunContext(runid=wd.name, base_dir=wd, scenario=None, catalog=catalog)
    hill_key = "watershed/hillslopes.parquet"
    loss_key = "wepp/output/interchange/loss_pw0.hill.parquet"
    for key in (hill_key, loss_key):
        assert [e for e in catalog.entries() if e.path == key] == [catalog.get(key)]
    hills = run_query(context, QueryRequest(datasets=[hill_key], columns=["topaz_id", "area"]))
    assert hills.records == [{"topaz_id": 11, "area": 900}]
    losses = run_query(context, QueryRequest(
        datasets=[loss_key], columns=["wepp_id", '"Hillslope Area" AS area'],
        order_by=["wepp_id"], limit=1,
    ))
    assert losses.records == [{"wepp_id": 1, "area": 10.5}]

    geometry = watershed / "geometry.geojson"
    geometry.write_text('{"type":"FeatureCollection","features":[]}')
    (wd / "wepp.nodb").write_text("{}")
    (wd / "watershed.nodb").write_text("{}")
    layers = load_layer_catalog()
    plan = resolve_export_plan({
        "format": "geoparquet", "units": "si", "output_scopes": ["baseline"],
        "layers": ["watershed.subcatchments", "wepp.summary.hillslopes"],
    }, layers)
    snapshot = build_dependency_snapshot(
        plan, layers, wd, nodb_ref_resolver=lambda *_: str(geometry), content_hash_mode="sha256",
    )
    expected = {"watershed_hillslope_attributes": hill_key, "wepp_loss_hill": loss_key}
    assert sorted(
        (e.dependency_id, e.relpath, e.content_hash_value)
        for e in snapshot.entries if e.dependency_id in expected
    ) == sorted(
        (source_id, path, hashlib.sha256((wd / path).read_bytes()).hexdigest())
        for source_id, path in expected.items()
    )
