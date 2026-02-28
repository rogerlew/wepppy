from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.materialize import materialize_file, materialize_path_if_archive
from wepppy.runtime_paths.parquet_sidecars import (
    find_existing_retired_root_resource_relpath,
    list_existing_retired_root_resources,
    logical_parquet_to_sidecar_relpath,
    pick_existing_parquet_path,
    pick_existing_parquet_relpath,
    require_directory_parquet_path,
    sidecar_relpath_to_logical_parquet,
)

pytestmark = pytest.mark.unit


def test_materialize_file_returns_existing_file_path(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    target = wd / "landuse" / "landuse.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"pq")

    assert materialize_file(str(wd), "landuse/landuse.parquet") == str(target)


def test_materialize_file_raises_for_missing_and_directory(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "landuse").mkdir()

    with pytest.raises(FileNotFoundError):
        materialize_file(str(wd), "landuse/missing.parquet")

    with pytest.raises(IsADirectoryError):
        materialize_file(str(wd), "landuse")


def test_materialize_path_if_archive_handles_absolute_and_relative_inputs(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    absolute = tmp_path / "already-absolute.txt"

    assert materialize_path_if_archive(str(wd), absolute) == str(absolute)
    assert materialize_path_if_archive(str(wd), "climate/wepp_cli.parquet") == str(
        wd / "climate" / "wepp_cli.parquet"
    )


def test_parquet_sidecar_mapping_roundtrip_for_in_scope_patterns() -> None:
    assert logical_parquet_to_sidecar_relpath("landuse/landuse.parquet") == "landuse.parquet"
    assert logical_parquet_to_sidecar_relpath("soils/soils.parquet") == "soils.parquet"
    assert logical_parquet_to_sidecar_relpath("climate/wepp_cli.parquet") == "climate.wepp_cli.parquet"
    assert logical_parquet_to_sidecar_relpath("watershed/hillslopes.parquet") == "watershed.hillslopes.parquet"
    assert logical_parquet_to_sidecar_relpath("dem/dem.parquet") is None

    assert sidecar_relpath_to_logical_parquet("landuse.parquet") == "landuse/landuse.parquet"
    assert sidecar_relpath_to_logical_parquet("soils.parquet") == "soils/soils.parquet"
    assert sidecar_relpath_to_logical_parquet("climate.wepp_cli.parquet") == "climate/wepp_cli.parquet"
    assert sidecar_relpath_to_logical_parquet("watershed.hillslopes.parquet") == "watershed/hillslopes.parquet"
    assert sidecar_relpath_to_logical_parquet("dem.parquet") is None


def test_find_and_list_retired_root_resources(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "landuse.parquet").write_bytes(b"l")
    (wd / "soils.parquet").write_bytes(b"s")
    (wd / "climate.wepp_cli.parquet").write_bytes(b"c")
    (wd / "watershed.channels.parquet").write_bytes(b"w")
    (wd / "wepp_cli_pds_mean_metric.csv").write_text("x", encoding="utf-8")

    assert (
        find_existing_retired_root_resource_relpath(str(wd), "climate/wepp_cli.parquet")
        == "climate.wepp_cli.parquet"
    )
    assert find_existing_retired_root_resource_relpath(str(wd), "dem/dem.parquet") is None

    assert list_existing_retired_root_resources(str(wd)) == [
        "climate.wepp_cli.parquet",
        "landuse.parquet",
        "soils.parquet",
        "watershed.channels.parquet",
        "wepp_cli_pds_mean_metric.csv",
    ]


def test_pick_existing_parquet_relpath_and_path_use_canonical_directory_only(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    canonical = wd / "climate" / "wepp_cli.parquet"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_bytes(b"pq")
    (wd / "climate.wepp_cli.parquet").write_bytes(b"retired")

    assert pick_existing_parquet_relpath(str(wd), "climate/wepp_cli.parquet") == "climate/wepp_cli.parquet"
    assert pick_existing_parquet_path(str(wd), "climate/wepp_cli.parquet") == canonical
    assert pick_existing_parquet_relpath(str(wd), "dem/dem.parquet") is None


def test_require_directory_parquet_path_enforces_migration_required_for_retired_root(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "watershed.hillslopes.parquet").write_bytes(b"retired")

    with pytest.raises(NoDirError) as exc_info:
        require_directory_parquet_path(str(wd), "watershed/hillslopes.parquet")

    assert exc_info.value.code == "NODIR_MIGRATION_REQUIRED"


def test_require_directory_parquet_path_raises_file_not_found_when_absent(tmp_path: Path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    with pytest.raises(FileNotFoundError):
        require_directory_parquet_path(str(wd), "watershed/hillslopes.parquet")
