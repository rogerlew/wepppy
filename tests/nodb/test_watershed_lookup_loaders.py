from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Tuple

import duckdb
import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def watershed_context(monkeypatch: pytest.MonkeyPatch) -> Tuple[Any, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    nodb_pkg = ModuleType("wepppy.nodb")
    nodb_pkg.__path__ = [str(repo_root / "wepppy" / "nodb")]
    core_pkg = ModuleType("wepppy.nodb.core")
    core_pkg.__path__ = [str(repo_root / "wepppy" / "nodb" / "core")]

    for module_name in list(sys.modules):
        if module_name == "wepppy.nodb" or module_name.startswith("wepppy.nodb."):
            monkeypatch.delitem(sys.modules, module_name, raising=False)

    monkeypatch.setitem(sys.modules, "wepppy.nodb", nodb_pkg)
    monkeypatch.setitem(sys.modules, "wepppy.nodb.core", core_pkg)

    watershed_module = importlib.import_module("wepppy.nodb.core.watershed")
    return watershed_module, watershed_module.Watershed


def _make_watershed(tmp_path: Path, watershed_cls: Any) -> Any:
    watershed = watershed_cls.__new__(watershed_cls)
    watershed.wd = str(tmp_path)
    (tmp_path / "watershed").mkdir(parents=True, exist_ok=True)
    watershed._subs_summary = {
        "10": SimpleNamespace(
            area=1.1,
            length=2.2,
            width=3.3,
            centroid=SimpleNamespace(lnglat=(-116.0, 47.0)),
        )
    }
    watershed._chns_summary = {
        "14": SimpleNamespace(
            area=4.4,
            length=5.5,
            width=6.6,
        )
    }
    return watershed


def _write_hillslopes_parquet(path: Path) -> None:
    with duckdb.connect() as con:
        con.execute(
            f"""
            COPY (
                SELECT
                    '10'::VARCHAR AS topaz_id,
                    12.5::DOUBLE AS area,
                    111.0::DOUBLE AS length,
                    0.45::DOUBLE AS slope_scalar,
                    22.0::DOUBLE AS width,
                    -116.1::DOUBLE AS centroid_lon,
                    47.2::DOUBLE AS centroid_lat
            ) TO '{path}' (FORMAT PARQUET)
            """
        )


def _write_channels_parquet(path: Path) -> None:
    with duckdb.connect() as con:
        con.execute(
            f"""
            COPY (
                SELECT
                    '14'::VARCHAR AS topaz_id,
                    44.5::DOUBLE AS area,
                    75.0::DOUBLE AS length
            ) TO '{path}' (FORMAT PARQUET)
            """
        )


def test_hillslope_lookup_methods_read_parquet_and_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    watershed_context: Tuple[Any, Any],
) -> None:
    watershed_module, watershed_cls = watershed_context
    watershed = _make_watershed(tmp_path, watershed_cls)
    hillslopes_parquet = tmp_path / "hillslopes.parquet"
    _write_hillslopes_parquet(hillslopes_parquet)

    monkeypatch.setattr(
        watershed_module,
        "pick_existing_parquet_path",
        lambda _wd, relpath: str(hillslopes_parquet)
        if relpath == "watershed/hillslopes.parquet"
        else None,
    )

    assert watershed.hillslope_area("10") == pytest.approx(12.5)
    assert watershed.hillslope_length("10") == pytest.approx(111.0)
    assert watershed.hillslope_slope("10") == pytest.approx(0.45)
    assert watershed.hillslope_centroid_lnglat("10") == pytest.approx((-116.1, 47.2))

    hillslopes_parquet.unlink()
    assert watershed.hillslope_area("10") == pytest.approx(12.5)


def test_hillslope_lookup_methods_reload_when_cached_lookup_is_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    watershed_context: Tuple[Any, Any],
) -> None:
    watershed_module, watershed_cls = watershed_context
    watershed = _make_watershed(tmp_path, watershed_cls)
    hillslopes_parquet = tmp_path / "hillslopes.parquet"
    _write_hillslopes_parquet(hillslopes_parquet)

    watershed._sub_area_lookup = {"99": 99.0}
    watershed._sub_length_lookup = {"99": 199.0}
    watershed._sub_slope_lookup = {"99": 0.99}
    watershed._sub_centroid_lookup = {"99": (-1.0, -1.0)}

    monkeypatch.setattr(
        watershed_module,
        "pick_existing_parquet_path",
        lambda _wd, relpath: str(hillslopes_parquet)
        if relpath == "watershed/hillslopes.parquet"
        else None,
    )

    assert watershed.hillslope_area("10") == pytest.approx(12.5)
    assert watershed.hillslope_length("10") == pytest.approx(111.0)
    assert watershed.hillslope_slope("10") == pytest.approx(0.45)
    assert watershed.hillslope_centroid_lnglat("10") == pytest.approx((-116.1, 47.2))

    assert "10" in watershed._sub_area_lookup
    assert "10" in watershed._sub_length_lookup
    assert "10" in watershed._sub_slope_lookup
    assert "10" in watershed._sub_centroid_lookup


def test_watershed_getstate_excludes_transient_lookup_caches(
    tmp_path: Path,
    watershed_context: Tuple[Any, Any],
) -> None:
    _, watershed_cls = watershed_context
    watershed = _make_watershed(tmp_path, watershed_cls)
    watershed._wbt = object()
    watershed._sub_area_lookup = {"10": 12.5}
    watershed._chn_area_lookup = {"14": 4.4}

    state = watershed.__getstate__()

    assert "_wbt" not in state
    assert "_sub_area_lookup" not in state
    assert "_chn_area_lookup" not in state


def test_channel_lookup_methods_reload_when_cached_lookup_is_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    watershed_context: Tuple[Any, Any],
) -> None:
    watershed_module, watershed_cls = watershed_context
    watershed = _make_watershed(tmp_path, watershed_cls)
    channels_parquet = tmp_path / "channels.parquet"
    _write_channels_parquet(channels_parquet)

    watershed._chn_area_lookup = {"994": 99.0}
    watershed._chn_length_lookup = {"994": 199.0}

    monkeypatch.setattr(
        watershed_module,
        "pick_existing_parquet_path",
        lambda _wd, relpath: str(channels_parquet)
        if relpath == "watershed/channels.parquet"
        else None,
    )

    assert watershed.channel_area("14") == pytest.approx(44.5)
    assert watershed.channel_length("14") == pytest.approx(75.0)

    assert "14" in watershed._chn_area_lookup
    assert "14" in watershed._chn_length_lookup


def test_hillslope_width_falls_back_when_lookup_missing_topaz_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    watershed_context: Tuple[Any, Any],
) -> None:
    watershed_module, watershed_cls = watershed_context
    watershed = _make_watershed(tmp_path, watershed_cls)
    hillslopes_csv = tmp_path / "watershed" / "hillslopes.csv"
    hillslopes_csv.write_text("topaz_id,width\n99,41.0\n", encoding="utf-8")

    monkeypatch.setattr(
        watershed_module,
        "pick_existing_parquet_path",
        lambda _wd, _relpath: None,
    )

    assert watershed.hillslope_width("10") == pytest.approx(3.3)


def test_channel_width_reads_csv_when_parquet_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    watershed_context: Tuple[Any, Any],
) -> None:
    watershed_module, watershed_cls = watershed_context
    watershed = _make_watershed(tmp_path, watershed_cls)
    channels_csv = tmp_path / "watershed" / "channels.csv"
    channels_csv.write_text("topaz_id,width\n14,9.5\n", encoding="utf-8")

    monkeypatch.setattr(
        watershed_module,
        "pick_existing_parquet_path",
        lambda _wd, _relpath: None,
    )

    assert watershed.channel_width("14") == pytest.approx(9.5)

    channels_csv.write_text("topaz_id,width\n14,18.5\n", encoding="utf-8")
    assert watershed.channel_width("14") == pytest.approx(9.5)


def test_hillslope_slope_raises_when_parquet_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    watershed_context: Tuple[Any, Any],
) -> None:
    watershed_module, watershed_cls = watershed_context
    watershed = _make_watershed(tmp_path, watershed_cls)

    monkeypatch.setattr(
        watershed_module,
        "pick_existing_parquet_path",
        lambda _wd, _relpath: None,
    )

    with pytest.raises(Exception, match="Cannot find slope without hillslope.parquet file"):
        watershed.hillslope_slope("10")
