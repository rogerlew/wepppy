"""Actual D-Tale readers and Flask grid responses on disposable sources."""
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pandas as pd
import pytest

pytestmark = pytest.mark.microservice


@pytest.fixture
def dtale_service(tmp_path, monkeypatch):
    module = importlib.import_module("wepppy.webservices.dtale.dtale")
    previous = set(module.DATASETS)
    monkeypatch.setattr(module, "DTALE_INTERNAL_TOKEN", "freshness-test-token")
    monkeypatch.setattr(module, "get_wd", lambda runid: str(tmp_path))
    # Table generation tests isolate optional NoDb map discovery; map state is
    # exercised directly below with the real parser and upstream registry.
    monkeypatch.setattr(module, "_ensure_geojson_assets", lambda *args: None)
    yield module
    for data_id in set(module.DATASETS) - previous:
        module._discard_dataset(data_id)
        module.MAP_CHOICES.pop(data_id, None)
        module.MAP_DEFAULTS.pop(data_id, None)


def _load(module, root, path="data.parquet", **payload):
    return module.app.test_client().post("/internal/load", json={
        "runid": root.name, "config": "test", "path": path, **payload,
    }, headers={"X-DTALE-TOKEN": "freshness-test-token"})


def _grid(module, data_id):
    # The reverse proxy strips APP_ROOT before reaching this Flask route.
    path = f"/dtale/data/{data_id}"
    return module.app.test_client().get(path, query_string={"ids": json.dumps(["0-1"])})


def _rewrite(path, frame):
    before = path.stat()
    frame.to_parquet(path, index=False)
    assert path.stat().st_size == before.st_size
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))


def test_eager_csv_restored_metadata_refreshes_and_touch_reuses(tmp_path, dtale_service):
    module = dtale_service
    source = tmp_path / "data.csv"
    source.write_text("a\n1\n2\n")
    first = _load(module, tmp_path, "data.csv")
    assert first.status_code == 200
    data_id = first.json["data_id"]
    original = module.global_state.get_data(data_id)
    stat = source.stat()
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1000000000))
    assert _load(module, tmp_path, "data.csv").json["fingerprint"] == first.json["fingerprint"]
    assert module.global_state.get_data(data_id) is original
    source.write_text("a\n8\n9\n")
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    second = _load(module, tmp_path, "data.csv")
    assert second.json["data_id"] == data_id
    assert second.json["fingerprint"] != first.json["fingerprint"]
    assert module.global_state.get_data(data_id)["a"].tolist() == [8, 9]


def test_lazy_schema_drift_visible_failure_and_relaunch(tmp_path, dtale_service):
    module = dtale_service
    source = tmp_path / "data.parquet"
    pd.DataFrame({"a": [1, 2]}).to_parquet(source, index=False)
    loaded = _load(module, tmp_path)
    assert loaded.status_code == 200
    data_id = loaded.json["data_id"]
    assert _grid(module, data_id).status_code == 200
    lazy = module.LAZY_PARQUET_DATASETS[data_id]
    _rewrite(source, pd.DataFrame({"z": [8, 9]}))
    for read in (lazy.rows, lambda: lazy.base_df):
        with pytest.raises(module._SourceChangedError):
            read()
    failure = _grid(module, data_id)
    assert failure.status_code == 200
    assert failure.json == {"success": False, "error": module._SOURCE_CHANGED_MESSAGE, "code": "changed_source"}
    reloaded = _load(module, tmp_path)
    assert reloaded.status_code == 200
    assert reloaded.json["data_id"] == data_id
    assert module.LAZY_PARQUET_DATASETS[data_id].load_data([0, 2])["z"].tolist() == [8, 9]
    assert any(column["name"] == "z" for column in _grid(module, data_id).json["columns"])


def test_same_byte_symlink_retarget_rebinds_and_later_change_is_detected(tmp_path, dtale_service):
    module = dtale_service
    first, second = tmp_path / "first.parquet", tmp_path / "second.parquet"
    pd.DataFrame({"a": [1, 2]}).to_parquet(first, index=False)
    second.write_bytes(first.read_bytes())
    source = tmp_path / "data.parquet"
    source.symlink_to(first.name)
    initial = _load(module, tmp_path)
    data_id = initial.json["data_id"]
    previous = module.LAZY_PARQUET_DATASETS[data_id]
    source.unlink()
    source.symlink_to(second.name)
    reloaded = _load(module, tmp_path)
    assert reloaded.json["data_id"] == data_id
    assert module.LAZY_PARQUET_DATASETS[data_id] is not previous
    _rewrite(second, pd.DataFrame({"a": [8, 9]}))
    assert _grid(module, data_id).json["code"] == "changed_source"


def test_lazy_query_exception_checks_generation_and_preserves_stable_errors(tmp_path, dtale_service, monkeypatch):
    module = dtale_service
    source = tmp_path / "data.parquet"
    pd.DataFrame({"a": [1, 2]}).to_parquet(source, index=False)
    lazy = module.LazyParquetDtaleInstance(source)

    def mutate_after_precheck():
        _rewrite(source, pd.DataFrame({"z": [8, 9]}))

    native_connect = module.duckdb.connect
    class Connection:
        def __enter__(self):
            self.connection = native_connect()
            mutate_after_precheck()
            return self.connection
        def __exit__(self, *args):
            self.connection.close()

    with monkeypatch.context() as patch:
        patch.setattr(module.duckdb, "connect", lambda: Connection())
        with pytest.raises(module._SourceChangedError):
            lazy.load_data([0, 2])  # real DuckDB query fails on its old column
    stable = module.LazyParquetDtaleInstance(source, compiled_filter=SimpleNamespace(where_sql="missing_column = ?", params=[1]))
    with pytest.raises(duckdb.BinderException):
        stable.load_data([0, 2])


def test_acquisition_drift_cleans_partial_lazy_state(tmp_path, dtale_service, monkeypatch):
    module = dtale_service
    source = tmp_path / "data.parquet"
    pd.DataFrame({"a": [1, 2]}).to_parquet(source, index=False)
    initialize = module._initialize_lazy_parquet_dataset

    def changing_initialize(*args, **kwargs):
        instance = initialize(*args, **kwargs)
        _rewrite(source, pd.DataFrame({"z": [8, 9]}))
        return instance

    monkeypatch.setattr(module, "_initialize_lazy_parquet_dataset", changing_initialize)
    response = _load(module, tmp_path)
    assert response.status_code == 409
    assert response.json["error"]["code"] == "changed_source"
    data_id = module._make_dataset_id(tmp_path.name, "test", "data.parquet")
    assert data_id not in module.DATASETS
    assert data_id not in module.LAZY_PARQUET_DATASETS
    assert not module.global_state.contains(data_id)


@pytest.mark.parametrize("failure", ["missing", "malformed", "none"])
def test_optional_overlay_refresh_and_failure_cleanup(tmp_path, dtale_service, failure):
    module = dtale_service
    source = tmp_path / "map.geojson"
    def write(label):
        source.write_text(json.dumps({"type": "FeatureCollection", "features": [{
            "type": "Feature", "properties": {"id": "1", "label": label},
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }]}))
    def register(path=source):
        return module._register_geojson_asset(tmp_path.name, "map", path, data_id=tmp_path.name, preferred_keys=("id",), make_default=True)
    write("old")
    key, _ = register()
    before = source.stat()
    write("new")
    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
    register()
    record = next(entry for entry in module.dtale_custom_geojson.CUSTOM_GEOJSON if entry["key"] == key)
    assert record["data"]["features"][0]["properties"]["label"] == "new"
    if failure == "missing":
        source.unlink()
    elif failure == "malformed":
        source.write_text("not json")
    assert register(None if failure == "none" else source) == (None, None)
    assert key not in module.REGISTERED_GEOJSON
    assert all(entry["key"] != key for entry in module.dtale_custom_geojson.CUSTOM_GEOJSON)
    assert tmp_path.name not in module.MAP_CHOICES
    assert tmp_path.name not in module.MAP_DEFAULTS


def test_eager_registration_failure_discards_partial_upstream_state(tmp_path, dtale_service, monkeypatch):
    module = dtale_service
    (tmp_path / "data.csv").write_text("a\n1\n2\n")
    initialize = module._initialize_dtale_dataset
    def fail_after_real_registration(*args, **kwargs):
        initialize(*args, **kwargs)
        raise ValueError("injected startup failure after registration")
    monkeypatch.setattr(module, "_initialize_dtale_dataset", fail_after_real_registration)
    response = _load(module, tmp_path, "data.csv")
    assert response.status_code == 500
    data_id = module._make_dataset_id(tmp_path.name, "test", "data.csv")
    assert not module.global_state.contains(data_id)
    assert data_id not in module.DATASETS


def test_overlay_feature_id_refresh_and_surviving_default(tmp_path, dtale_service):
    module = dtale_service
    source = tmp_path / "map.geojson"
    def write(property_name):
        source.write_text(json.dumps({"type": "FeatureCollection", "features": [{
            "type": "Feature", "properties": {property_name: "1"},
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }]}))
    write("channel_id")
    ids = [tmp_path.name, tmp_path.name + "-other"]
    for data_id in ids:
        key, _ = module._register_geojson_asset(tmp_path.name, "channels", source, data_id=data_id, loc_candidates=("channel_id", "reach_id"))
    write("reach_id")
    module._register_geojson_asset(tmp_path.name, "channels", source, data_id=ids[0], loc_candidates=("channel_id", "reach_id"))
    for data_id in ids:
        assert module.MAP_DEFAULTS[data_id]["featureidkey"] == "reach_id"
        assert len([choice for choice in module.MAP_CHOICES[data_id] if choice[1] == key]) == 1
        assert module.MAP_CHOICES[data_id][0][2] == "reach_id"
    obsolete_key, _ = module._register_geojson_asset(tmp_path.name, "obsolete", source, data_id=ids[0], make_default=True)
    module._remove_geojson_asset(obsolete_key)
    assert module.MAP_DEFAULTS[ids[0]]["geojson"] == key
    assert module.MAP_DEFAULTS[ids[0]]["loc_candidates"] == ("channel_id", "reach_id")
    module._remove_geojson_asset(key)


def test_filter_relaunch_revalidates_schema_without_dropping_partition(tmp_path, dtale_service, monkeypatch):
    import base64
    module = dtale_service
    monkeypatch.setattr(module, "BROWSE_PARQUET_FILTERS_ENABLED", True)
    source = tmp_path / "data.parquet"
    pd.DataFrame({"a": [1, 2]}).to_parquet(source, index=False)
    pqf = base64.urlsafe_b64encode(json.dumps({"kind": "condition", "field": "a", "operator": "GreaterThan", "value": "1"}).encode()).decode()
    first = _load(module, tmp_path, pqf=pqf)
    assert first.status_code == 200
    data_id = first.json["data_id"]
    assert module.LAZY_PARQUET_DATASETS[data_id].rows() == 1
    _rewrite(source, pd.DataFrame({"a": [8, 9]}))
    second = _load(module, tmp_path, pqf=pqf)
    assert second.status_code == 200 and second.json["data_id"] == data_id
    assert module.LAZY_PARQUET_DATASETS[data_id].rows() == 2
    _rewrite(source, pd.DataFrame({"z": [8, 9]}))
    invalid = _load(module, tmp_path, pqf=pqf)
    assert invalid.status_code == 422
    assert data_id not in module.DATASETS
    assert data_id not in module.LAZY_PARQUET_DATASETS


def test_lazy_alias_loop_reports_visible_source_failure(tmp_path, dtale_service):
    module = dtale_service
    target = tmp_path / "original.parquet"
    pd.DataFrame({"a": [1, 2]}).to_parquet(target, index=False)
    alias = tmp_path / "data.parquet"
    alias.symlink_to(target.name)
    first = _load(module, tmp_path)
    assert first.status_code == 200
    alias.unlink()
    alias.symlink_to(alias.name)
    response = _grid(module, first.json["data_id"])
    assert response.status_code == 200
    assert response.json["code"] == "changed_source"
    assert response.json["success"] is False


def test_loader_config_fallback_rebinds_when_preferred_root_source_appears(tmp_path, dtale_service):
    module = dtale_service
    fallback = tmp_path / "test" / "data.parquet"
    fallback.parent.mkdir()
    pd.DataFrame({"a": [1, 2]}).to_parquet(fallback, index=False)
    first = _load(module, tmp_path)
    assert first.status_code == 200
    data_id = first.json["data_id"]
    old = module.LAZY_PARQUET_DATASETS[data_id]
    preferred = tmp_path / "data.parquet"
    preferred.write_bytes(fallback.read_bytes())
    second = _load(module, tmp_path)
    assert second.status_code == 200 and second.json["data_id"] == data_id
    assert module.LAZY_PARQUET_DATASETS[data_id] is not old
    assert module.DATASETS[data_id].path == preferred
    _rewrite(preferred, pd.DataFrame({"a": [8, 9]}))
    assert _grid(module, data_id).json["code"] == "changed_source"
