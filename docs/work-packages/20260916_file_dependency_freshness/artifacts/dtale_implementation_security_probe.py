"""Independent real-reader/access probes for the bounded D-Tale change."""
import importlib
import json
import os
from types import SimpleNamespace

import duckdb
import pandas as pd
import pytest

from tests.microservices.test_dtale_freshness import dtale_service, _load, _grid, _rewrite

_module = importlib.import_module("wepppy.webservices.dtale.dtale")
_real_ensure = _module._ensure_geojson_assets


def test_actual_read_denial_rejects_cached_lazy_reads_and_loader(tmp_path, dtale_service):
    module = dtale_service
    assert os.geteuid() != 0
    source = tmp_path / "data.parquet"
    pd.DataFrame({"a": [1, 2]}).to_parquet(source, index=False)
    loaded = _load(module, tmp_path)
    assert loaded.status_code == 200
    data_id = loaded.json["data_id"]
    lazy = module.LAZY_PARQUET_DATASETS[data_id]
    assert lazy.rows() == 2
    assert len(lazy.base_df) == 1
    mode = source.stat().st_mode
    source.chmod(0)
    try:
        for access in (lazy.rows, lambda: lazy.base_df, lambda: lazy.load_data([0, 2])):
            with pytest.raises(module._SourceChangedError) as failure:
                access()
            assert isinstance(failure.value.__cause__, PermissionError)
        grid = _grid(module, data_id)
        assert grid.status_code == 200
        assert grid.json["success"] is False and grid.json["code"] == "changed_source"
        assert "results" not in grid.json
        denied = _load(module, tmp_path)
        assert denied.status_code == 409
        assert denied.json["description"] == denied.json["error"]["message"]
    finally:
        source.chmod(mode)


def test_actual_filtered_count_exception_rechecks_source(tmp_path, dtale_service, monkeypatch):
    module = dtale_service
    source = tmp_path / "data.parquet"
    pd.DataFrame({"a": [1, 2]}).to_parquet(source, index=False)
    filtered = SimpleNamespace(where_sql='"a" > ?', params=[0])
    lazy = module.LazyParquetDtaleInstance(source, compiled_filter=filtered)
    native_count = module.count_filtered_parquet_rows

    def changed_count(*args):
        _rewrite(source, pd.DataFrame({"z": [8, 9]}))
        return native_count(*args)

    monkeypatch.setattr(module, "count_filtered_parquet_rows", changed_count)
    with pytest.raises(module._SourceChangedError) as failure:
        lazy.rows()
    assert isinstance(failure.value.__context__, duckdb.BinderException)
    assert lazy._rows is None
    monkeypatch.setattr(module, "count_filtered_parquet_rows", native_count)
    stable = module.LazyParquetDtaleInstance(source, compiled_filter=filtered)
    with pytest.raises(duckdb.BinderException):
        stable.rows()


def test_optional_denial_removes_only_affected_overlay(tmp_path, dtale_service):
    module = dtale_service
    assert os.geteuid() != 0
    source = tmp_path / "map.geojson"
    source.write_text(json.dumps({"type": "FeatureCollection", "features": [{
        "type": "Feature", "properties": {"id": "1"},
        "geometry": {"type": "Point", "coordinates": [0, 0]},
    }]}))
    runid = tmp_path.name
    first_id, second_id = runid + "-one", runid + "-two"
    affected = runid + "-affected"
    unrelated = runid + "-unrelated"
    try:
        for data_id in (first_id, second_id):
            module._register_geojson_asset(runid, "affected", source, data_id=data_id, make_default=True)
        module._register_geojson_asset(runid, "unrelated", source, data_id=second_id)
        unrelated_record = next(item for item in module.dtale_custom_geojson.CUSTOM_GEOJSON if item["key"] == unrelated)
        mode = source.stat().st_mode
        source.chmod(0)
        try:
            assert module._register_geojson_asset(runid, "affected", source, data_id=first_id) == (None, None)
        finally:
            source.chmod(mode)
        assert affected not in module.REGISTERED_GEOJSON
        assert all(item["key"] != affected for item in module.dtale_custom_geojson.CUSTOM_GEOJSON)
        assert first_id not in module.MAP_CHOICES
        assert all(choice[1] == unrelated for choice in module.MAP_CHOICES[second_id])
        assert first_id not in module.MAP_DEFAULTS and second_id not in module.MAP_DEFAULTS
        assert unrelated in module.REGISTERED_GEOJSON
        assert any(item is unrelated_record for item in module.dtale_custom_geojson.CUSTOM_GEOJSON)
    finally:
        module._remove_geojson_asset(affected)
        module._remove_geojson_asset(unrelated)


def test_absent_controllers_clear_only_run_assets(tmp_path, dtale_service):
    module = dtale_service
    source = tmp_path / "map.geojson"
    source.write_text('{"type":"FeatureCollection","features":[]}')
    runid = tmp_path.name
    keys = []
    try:
        for slug in ("subcatchments", "channels", "ag-fields-boundaries", "ag-fields-subfields"):
            key, _ = module._register_geojson_asset(runid, slug, source, data_id=runid)
            keys.append(key)
        other, _ = module._register_geojson_asset(runid + "-other", "channels", source, data_id=runid + "-other")
        keys.append(other)
        _real_ensure(runid, tmp_path, runid)
        assert all(key not in module.REGISTERED_GEOJSON for key in keys[:-1])
        assert other in module.REGISTERED_GEOJSON
        assert runid not in module.MAP_CHOICES and runid not in module.MAP_DEFAULTS
    finally:
        for key in keys:
            module._remove_geojson_asset(key)


def test_config_fallback_selection_rebinds_equal_bytes(tmp_path, dtale_service):
    module = dtale_service
    fallback = tmp_path / "test/data.parquet"
    fallback.parent.mkdir()
    pd.DataFrame({"a": [1, 2]}).to_parquet(fallback, index=False)
    loaded = _load(module, tmp_path)
    data_id = loaded.json["data_id"]
    previous = module.LAZY_PARQUET_DATASETS[data_id]
    preferred = tmp_path / "data.parquet"
    preferred.write_bytes(fallback.read_bytes())
    assert _load(module, tmp_path).json["data_id"] == data_id
    current = module.LAZY_PARQUET_DATASETS[data_id]
    assert current is not previous and current.path == preferred
    _rewrite(preferred, pd.DataFrame({"a": [8, 9]}))
    assert _grid(module, data_id).json["code"] == "changed_source"
