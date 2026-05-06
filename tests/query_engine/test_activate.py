from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.query_engine.activate import activate_query_engine, update_catalog_entry

pytestmark = pytest.mark.unit


def _write_parquet(path: Path, table: pa.Table) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)


def test_activate_query_engine_readonly(tmp_path: Path) -> None:
    (tmp_path / "READONLY").write_text("locked", encoding="utf-8")
    with pytest.raises(PermissionError):
        activate_query_engine(tmp_path, run_interchange=False)


def test_activate_query_engine_readonly_reuses_catalog(tmp_path: Path) -> None:
    table = pa.table({"id": [1], "value": ["a"]})
    rel = "data/sample.parquet"
    file_path = tmp_path / rel
    _write_parquet(file_path, table)

    activate_query_engine(tmp_path, run_interchange=False)
    catalog_path = tmp_path / "_query_engine" / "catalog.json"
    initial_mtime = catalog_path.stat().st_mtime

    (tmp_path / "READONLY").write_text("locked", encoding="utf-8")
    catalog = activate_query_engine(tmp_path, run_interchange=False)

    assert catalog_path.stat().st_mtime == initial_mtime
    assert any(entry["path"] == rel for entry in catalog["files"])


def test_update_catalog_entry(tmp_path: Path) -> None:
    table = pa.table({"id": [1, 2], "value": ["a", "b"]})
    rel = "data/sample.parquet"
    file_path = tmp_path / rel
    _write_parquet(file_path, table)

    # initial activation builds catalog
    activate_query_engine(tmp_path, run_interchange=False)

    catalog_path = tmp_path / "_query_engine" / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    assert any(entry["path"] == rel for entry in catalog["files"])

    # modify file and update entry
    table_updated = pa.table({"id": [1, 2, 3], "value": ["a", "b", "c"]})
    _write_parquet(file_path, table_updated)

    entry = update_catalog_entry(tmp_path, rel)
    assert entry is not None
    assert entry["path"] == rel

    catalog = json.loads(catalog_path.read_text())
    updated_entry = next(item for item in catalog["files"] if item["path"] == rel)
    assert updated_entry["size_bytes"] == file_path.stat().st_size

    # remove file and ensure catalog entry removed
    file_path.unlink()
    removed = update_catalog_entry(tmp_path, rel)
    assert removed is None
    catalog = json.loads(catalog_path.read_text())
    assert all(item["path"] != rel for item in catalog["files"])


def test_activate_query_engine_rejects_retired_root_parquet_sidecars(tmp_path: Path) -> None:
    table = pa.table({"topaz_id": [1], "value": ["a"]})
    sidecar_rel = "landuse.parquet"
    _write_parquet(tmp_path / sidecar_rel, table)

    with pytest.raises(ValueError, match="Migration required"):
        activate_query_engine(tmp_path, run_interchange=False, force_refresh=True)


def test_activate_query_engine_rejects_mixed_canonical_and_retired_root_sidecars(
    tmp_path: Path,
) -> None:
    table = pa.table({"topaz_id": [1], "value": ["a"]})
    _write_parquet(tmp_path / "landuse" / "landuse.parquet", table)
    _write_parquet(tmp_path / "landuse.parquet", table)

    with pytest.raises(ValueError, match="Migration required"):
        activate_query_engine(tmp_path, run_interchange=False, force_refresh=True)


def test_activate_query_engine_scenario_ignores_parent_sidecars(tmp_path: Path) -> None:
    parent = tmp_path / "run"
    scenario = parent / "_pups" / "omni" / "scenarios" / "child"
    scenario.mkdir(parents=True)

    table = pa.table({"topaz_id": [1], "value": ["a"]})
    parent_sidecar = parent / "landuse.parquet"
    _write_parquet(parent_sidecar, table)

    catalog = activate_query_engine(scenario, run_interchange=False, force_refresh=True)
    logical_rel = "landuse/landuse.parquet"
    by_path = {entry["path"]: entry for entry in catalog["files"]}

    assert logical_rel not in by_path


def test_update_catalog_entry_allows_parent_assets(tmp_path: Path) -> None:
    parent = tmp_path / "run"
    scenario = parent / "_pups" / "omni" / "scenarios" / "child"
    dataset_rel = Path("watershed") / "hillslopes.parquet"

    table = pa.table({"id": [10], "value": ["parent"]})
    dataset_path = parent / dataset_rel
    _write_parquet(dataset_path, table)

    scenario.mkdir(parents=True)
    parent_watershed = parent / "watershed"
    parent_watershed.mkdir(exist_ok=True)
    (scenario / "watershed").symlink_to(parent_watershed, target_is_directory=True)

    activate_query_engine(scenario, run_interchange=False)

    entry = update_catalog_entry(scenario, dataset_rel.as_posix())
    assert entry is not None
    assert entry["path"] == dataset_rel.as_posix()


def test_update_catalog_entry_rejects_traversal(tmp_path: Path) -> None:
    activate_query_engine(tmp_path, run_interchange=False)
    with pytest.raises(ValueError):
        update_catalog_entry(tmp_path, "../outside.parquet")


def test_activate_query_engine_tracks_parent_symlinks(tmp_path: Path) -> None:
    parent = tmp_path / "run"
    scenario = parent / "_pups" / "omni" / "scenarios" / "child"
    dataset_rel = Path("watershed") / "hillslopes.parquet"

    table = pa.table({"id": [5], "value": ["parent"]})
    dataset_path = parent / dataset_rel
    _write_parquet(dataset_path, table)

    scenario.mkdir(parents=True)
    parent_watershed = parent / "watershed"
    parent_watershed.mkdir(exist_ok=True)
    (scenario / "watershed").symlink_to(parent_watershed, target_is_directory=True)

    catalog = activate_query_engine(scenario, run_interchange=False)
    assert any(entry["path"] == dataset_rel.as_posix() for entry in catalog["files"])


def test_activate_query_engine_includes_base_assets_with_pups_symlinks(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    dataset_rel = Path("watershed") / "hillslopes.parquet"

    table = pa.table({"id": [1], "value": ["base"]})
    _write_parquet(run_dir / dataset_rel, table)

    scenario = run_dir / "_pups" / "omni" / "scenarios" / "child"
    scenario.mkdir(parents=True)
    (scenario / "watershed").symlink_to(run_dir / "watershed", target_is_directory=True)

    catalog = activate_query_engine(run_dir, run_interchange=False)
    paths = {entry["path"] for entry in catalog["files"]}
    assert dataset_rel.as_posix() in paths


def test_activate_query_engine_reuses_existing_catalog(tmp_path: Path) -> None:
    table = pa.table({"id": [1], "value": ["a"]})
    rel = "data/sample.parquet"
    file_path = tmp_path / rel
    _write_parquet(file_path, table)

    catalog_path = tmp_path / "_query_engine" / "catalog.json"

    activate_query_engine(tmp_path, run_interchange=False)
    initial_mtime = catalog_path.stat().st_mtime

    # Should short-circuit and reuse the existing catalog
    catalog = activate_query_engine(tmp_path, run_interchange=False)

    assert catalog_path.stat().st_mtime == initial_mtime
    assert any(entry["path"] == rel for entry in catalog["files"])

    time.sleep(1)
    activate_query_engine(tmp_path, run_interchange=False, force_refresh=True)
    assert catalog_path.stat().st_mtime > initial_mtime


def test_activate_query_engine_run_interchange_propagates_pass_family(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "wepp" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "wepppy.nodb.core.climate.Climate.getInstance",
        lambda _wd: SimpleNamespace(calendar_start_year=2007, is_single_storm=False),
    )
    monkeypatch.setattr(
        "wepppy.nodb.core.wepp.Wepp.getInstance",
        lambda _wd: SimpleNamespace(pass_family="hbp"),
    )
    monkeypatch.setattr(
        "wepppy.wepp.interchange.run_wepp_hillslope_interchange",
        lambda _path, **kwargs: calls.append(("hill", kwargs["pass_family"])),
    )
    monkeypatch.setattr(
        "wepppy.wepp.interchange.run_wepp_watershed_interchange",
        lambda _path, **kwargs: calls.append(("watershed", kwargs["pass_family"])),
    )
    monkeypatch.setattr(
        "wepppy.wepp.interchange.generate_interchange_documentation",
        lambda _path: None,
    )
    monkeypatch.setattr(
        "wepppy.wepp.interchange.needs_major_refresh",
        lambda _path: True,
    )
    monkeypatch.setattr(
        "wepppy.wepp.interchange.remove_incompatible_interchange",
        lambda _path: None,
    )

    activate_query_engine(tmp_path, run_interchange=True, force_refresh=True)

    assert calls == [("hill", "hbp"), ("watershed", "hbp")]


def test_activate_query_engine_run_interchange_does_not_suppress_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "wepp" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "wepppy.nodb.core.climate.Climate.getInstance",
        lambda _wd: SimpleNamespace(calendar_start_year=2007, is_single_storm=False),
    )
    monkeypatch.setattr(
        "wepppy.nodb.core.wepp.Wepp.getInstance",
        lambda _wd: SimpleNamespace(pass_family="legacy_ascii"),
    )
    monkeypatch.setattr(
        "wepppy.wepp.interchange.run_wepp_hillslope_interchange",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("deterministic failure")),
    )
    monkeypatch.setattr(
        "wepppy.wepp.interchange.needs_major_refresh",
        lambda _path: True,
    )
    monkeypatch.setattr(
        "wepppy.wepp.interchange.remove_incompatible_interchange",
        lambda _path: None,
    )

    with pytest.raises(RuntimeError, match="deterministic failure"):
        activate_query_engine(tmp_path, run_interchange=True, force_refresh=True)


def test_activate_query_engine_rejects_unsupported_pass_family(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "wepp" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "wepppy.nodb.core.climate.Climate.getInstance",
        lambda _wd: SimpleNamespace(calendar_start_year=2007, is_single_storm=False),
    )
    monkeypatch.setattr(
        "wepppy.nodb.core.wepp.Wepp.getInstance",
        lambda _wd: SimpleNamespace(pass_family="auto"),
    )

    with pytest.raises(ValueError, match="pass_family must be 'legacy_ascii' or 'hbp'"):
        activate_query_engine(tmp_path, run_interchange=True, force_refresh=True)
