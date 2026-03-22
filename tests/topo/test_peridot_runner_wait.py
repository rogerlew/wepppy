import threading
import time
from pathlib import Path

import pandas as pd
import pytest

from wepppy.topo.peridot import peridot_runner


def _patch_dummy_watershed_and_translator(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyWatershedState:
        delineation_backend_is_topaz = True
        delineation_backend_is_wbt = False

    class DummyWatershed:
        @staticmethod
        def getInstance(_wd: str) -> DummyWatershedState:
            return DummyWatershedState()

    class DummyTranslator:
        def __init__(self, *_args, **_kwargs):
            pass

        @staticmethod
        def wepp(top: int) -> int:
            return top + 100

        @staticmethod
        def chn_enum(top: int) -> int:
            return top // 10

    import wepppy.nodb.core as nodb_core
    import wepppy.topo.watershed_abstraction as watershed_abstraction

    monkeypatch.setattr(nodb_core, "Watershed", DummyWatershed)
    monkeypatch.setattr(watershed_abstraction, "WeppTopTranslator", DummyTranslator)


@pytest.mark.unit
def test_run_peridot_waits_for_subwta_arc(tmp_path, monkeypatch):
    wd = str(tmp_path)
    subwta_dir = tmp_path / "dem" / "topaz"
    subwta_dir.mkdir(parents=True)
    subwta_arc = subwta_dir / "SUBWTA.ARC"

    monkeypatch.setenv("PERIDOT_INPUT_WAIT_S", "1.0")

    called = {}

    class DummyProc:
        def wait(self):
            called["wait"] = True

    def dummy_popen(cmd, stdout=None, stderr=None):
        called["cmd"] = cmd
        return DummyProc()

    monkeypatch.setattr(peridot_runner, "_get_bin", lambda: "/fake/bin/abstract_watershed")
    monkeypatch.setattr(peridot_runner, "Popen", dummy_popen)

    def delayed_write():
        time.sleep(0.1)
        subwta_arc.write_text("ok", encoding="utf-8")

    thread = threading.Thread(target=delayed_write, daemon=True)
    thread.start()

    peridot_runner.run_peridot_abstract_watershed(
        wd,
        clip_hillslopes=False,
        verbose=False,
    )
    thread.join(timeout=1.0)

    assert "cmd" in called
    assert called.get("wait") is True
    assert "--skip-flowpaths" in called["cmd"]


@pytest.mark.unit
def test_run_peridot_wbt_defaults_to_skip_flowpaths(tmp_path, monkeypatch):
    wd = str(tmp_path)
    subwta_dir = tmp_path / "dem" / "wbt"
    subwta_dir.mkdir(parents=True)
    (subwta_dir / "subwta.tif").write_text("ok", encoding="utf-8")

    called = {}

    class DummyProc:
        def wait(self):
            called["wait"] = True

    def dummy_popen(cmd, stdout=None, stderr=None):
        called["cmd"] = cmd
        return DummyProc()

    monkeypatch.setattr(peridot_runner, "_get_wbt_bin", lambda: "/fake/bin/wbt_abstract_watershed")
    monkeypatch.setattr(peridot_runner, "Popen", dummy_popen)

    peridot_runner.run_peridot_wbt_abstract_watershed(
        wd,
        clip_hillslopes=False,
        verbose=False,
    )

    assert "cmd" in called
    assert called.get("wait") is True
    assert "--skip-flowpaths" in called["cmd"]


@pytest.mark.unit
def test_post_abstract_watershed_prefers_parquet_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    watershed_dir = tmp_path / "watershed"
    watershed_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "topaz_id": [11],
            "area": [10.0],
            "centroid_lon": [-116.8],
            "centroid_lat": [46.8],
        }
    ).to_parquet(watershed_dir / "hillslopes.parquet", index=False)
    pd.DataFrame(
        {
            "topaz_id": [14],
            "area": [5.0],
            "centroid_lon": [-116.7],
            "centroid_lat": [46.7],
        }
    ).to_parquet(watershed_dir / "channels.parquet", index=False)
    pd.DataFrame(
        {
            "topaz_id": [111],
            "area": [999.0],
            "centroid_lon": [-100.0],
            "centroid_lat": [40.0],
        }
    ).to_csv(watershed_dir / "hillslopes.csv", index=False)
    pd.DataFrame(
        {
            "topaz_id": [444],
            "area": [777.0],
            "centroid_lon": [-100.0],
            "centroid_lat": [40.0],
        }
    ).to_csv(watershed_dir / "channels.csv", index=False)

    catalog_updates = []
    monkeypatch.setattr(
        peridot_runner,
        "_update_catalog_entry",
        lambda wd, rel: catalog_updates.append((wd, rel)),
    )

    peridot_runner.post_abstract_watershed(str(tmp_path), verbose=False)

    hills_df = pd.read_parquet(watershed_dir / "hillslopes.parquet")
    channels_df = pd.read_parquet(watershed_dir / "channels.parquet")
    assert hills_df["topaz_id"].tolist() == [11]
    assert channels_df["topaz_id"].tolist() == [14]
    assert str(hills_df["topaz_id"].dtype) == "Int32"
    assert str(hills_df["wepp_id"].dtype) == "Int32"
    assert str(channels_df["topaz_id"].dtype) == "Int32"
    assert str(channels_df["wepp_id"].dtype) == "Int32"
    assert str(channels_df["chn_enum"].dtype) == "Int32"
    assert (watershed_dir / "hillslopes.csv").exists()
    assert (watershed_dir / "channels.csv").exists()
    assert (str(tmp_path), "watershed/flowpaths.parquet") in catalog_updates


@pytest.mark.unit
def test_post_abstract_watershed_legacy_csv_fallback_logs_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    watershed_dir = tmp_path / "watershed"
    watershed_dir.mkdir(parents=True)
    (watershed_dir / "hillslopes.csv").write_text(
        "topaz_id,area,centroid_lon,centroid_lat\n1,10.0,-116.8,46.8\n",
        encoding="utf-8",
    )
    (watershed_dir / "channels.csv").write_text(
        "topaz_id,area,centroid_lon,centroid_lat\n4,5.0,-116.7,46.7\n",
        encoding="utf-8",
    )

    caplog.set_level("WARNING")
    peridot_runner.post_abstract_watershed(str(tmp_path), verbose=False)

    assert (watershed_dir / "hillslopes.parquet").exists()
    assert (watershed_dir / "channels.parquet").exists()
    assert "Legacy fallback path active" in caplog.text


@pytest.mark.unit
def test_post_abstract_watershed_refreshes_readme_and_flowpaths_fallback(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    watershed_dir = tmp_path / "watershed"
    watershed_dir.mkdir(parents=True)

    pd.DataFrame(
        {
            "topaz_id": [11],
            "area": [10.0],
            "centroid_lon": [-116.8],
            "centroid_lat": [46.8],
        }
    ).to_parquet(watershed_dir / "hillslopes.parquet", index=False)
    pd.DataFrame(
        {
            "topaz_id": [14],
            "area": [5.0],
            "centroid_lon": [-116.7],
            "centroid_lat": [46.7],
        }
    ).to_parquet(watershed_dir / "channels.parquet", index=False)
    (watershed_dir / "flowpaths.csv").write_text(
        "topaz_id,fp_id,area,centroid_lon,centroid_lat\n11,1,1.0,-116.8,46.8\n",
        encoding="utf-8",
    )
    slope_dir = watershed_dir / "slope_files" / "hillslopes"
    slope_dir.mkdir(parents=True)
    (slope_dir / "hill_11.slp").write_text("slope 11", encoding="utf-8")
    (slope_dir / "hill_12.slp").write_text("slope 12", encoding="utf-8")
    (watershed_dir / "README.md").write_text(
        """# Watershed Output Manifest

Generated by Peridot during watershed abstraction.

## Execution Flags and Inputs

- `command`: `wbt_abstract_watershed`
- `max_points`: `80`
- `clip_hillslopes`: `false`
- `clip_hillslope_length`: `300.000`
- `bieger2015_widths`: `false`
- `skip_flowpaths`: `false`
- `representative_flowpath`: `false`

## File Manifest

stale

## Tabular Schema Summary

stale

## Conditional Outputs and Notes

- flowpaths expected
""",
        encoding="utf-8",
    )

    caplog.set_level("WARNING")
    peridot_runner.post_abstract_watershed(str(tmp_path), verbose=False)

    flowpaths_df = pd.read_parquet(watershed_dir / "flowpaths.parquet")
    assert str(flowpaths_df["topaz_id"].dtype) == "Int32"
    assert str(flowpaths_df["fp_id"].dtype) == "Int32"
    assert "using watershed/flowpaths.csv because watershed/flowpaths.parquet is missing" in caplog.text

    readme = (watershed_dir / "README.md").read_text(encoding="utf-8")
    assert "| wepp_id | int32 |" in readme
    assert "| chn_enum | int32 |" in readme
    assert "| watershed/README.md | markdown |" in readme
    assert "| watershed/slope_files/hillslopes/* | slp bundle |" in readme
    assert "2 files" in readme
    assert "watershed/slope_files/hillslopes/hill_11.slp" not in readme
    assert "- `representative_flowpath`: `false`" in readme


@pytest.mark.unit
@pytest.mark.parametrize(
    ("missing_name", "expected_text"),
    [
        ("hillslopes", "Missing watershed hillslope table"),
        ("channels", "Missing watershed channel table"),
    ],
)
def test_post_abstract_watershed_requires_primary_tables(
    tmp_path: Path,
    missing_name: str,
    expected_text: str,
) -> None:
    watershed_dir = tmp_path / "watershed"
    watershed_dir.mkdir(parents=True)
    if missing_name != "hillslopes":
        pd.DataFrame(
            {
                "topaz_id": [11],
                "area": [10.0],
                "centroid_lon": [-116.8],
                "centroid_lat": [46.8],
            }
        ).to_parquet(watershed_dir / "hillslopes.parquet", index=False)
    if missing_name != "channels":
        pd.DataFrame(
            {
                "topaz_id": [14],
                "area": [5.0],
                "centroid_lon": [-116.7],
                "centroid_lat": [46.7],
            }
        ).to_parquet(watershed_dir / "channels.parquet", index=False)

    with pytest.raises(FileNotFoundError, match=expected_text):
        peridot_runner.post_abstract_watershed(str(tmp_path), verbose=False)


@pytest.mark.unit
def test_migrate_watershed_outputs_from_legacy_csv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    watershed_dir = tmp_path / "watershed"
    watershed_dir.mkdir(parents=True)
    (watershed_dir / "hillslopes.csv").write_text(
        "topaz_id,area,centroid_lon,centroid_lat\n1,10.0,-116.8,46.8\n",
        encoding="utf-8",
    )
    (watershed_dir / "channels.csv").write_text(
        "topaz_id,area,centroid_lon,centroid_lat\n4,5.0,-116.7,46.7\n",
        encoding="utf-8",
    )
    (watershed_dir / "flowpaths.csv").write_text(
        "topaz_id,fp_id,area,centroid_lon,centroid_lat\n1,1,1.0,-116.8,46.8\n",
        encoding="utf-8",
    )

    _patch_dummy_watershed_and_translator(monkeypatch)
    monkeypatch.setattr(peridot_runner, "_update_catalog_entry", None)

    changed = peridot_runner.migrate_watershed_outputs(str(tmp_path), remove_csv=True, verbose=False)

    assert changed is True
    assert (watershed_dir / "hillslopes.parquet").exists()
    assert (watershed_dir / "channels.parquet").exists()
    assert (watershed_dir / "flowpaths.parquet").exists()
    assert not (watershed_dir / "hillslopes.csv").exists()
    assert not (watershed_dir / "channels.csv").exists()
    assert not (watershed_dir / "flowpaths.csv").exists()


@pytest.mark.unit
def test_migrate_watershed_outputs_keeps_csv_when_remove_csv_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    watershed_dir = tmp_path / "watershed"
    watershed_dir.mkdir(parents=True)
    (watershed_dir / "hillslopes.csv").write_text(
        "topaz_id,area,centroid_lon,centroid_lat\n1,10.0,-116.8,46.8\n",
        encoding="utf-8",
    )
    (watershed_dir / "channels.csv").write_text(
        "topaz_id,area,centroid_lon,centroid_lat\n4,5.0,-116.7,46.7\n",
        encoding="utf-8",
    )

    _patch_dummy_watershed_and_translator(monkeypatch)
    monkeypatch.setattr(peridot_runner, "_update_catalog_entry", None)

    changed = peridot_runner.migrate_watershed_outputs(str(tmp_path), remove_csv=False, verbose=False)

    assert changed is True
    assert (watershed_dir / "hillslopes.parquet").exists()
    assert (watershed_dir / "channels.parquet").exists()
    assert (watershed_dir / "hillslopes.csv").exists()
    assert (watershed_dir / "channels.csv").exists()


@pytest.mark.unit
def test_migrate_watershed_outputs_prefers_existing_parquet_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    watershed_dir = tmp_path / "watershed"
    watershed_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "topaz_id": [11],
            "area": [10.0],
            "centroid_lon": [-116.8],
            "centroid_lat": [46.8],
        }
    ).to_parquet(watershed_dir / "hillslopes.parquet", index=False)
    pd.DataFrame(
        {
            "topaz_id": [14],
            "area": [5.0],
            "centroid_lon": [-116.7],
            "centroid_lat": [46.7],
        }
    ).to_parquet(watershed_dir / "channels.parquet", index=False)
    (watershed_dir / "hillslopes.csv").write_text(
        "topaz_id,area,centroid_lon,centroid_lat\n999,10.0,-100.0,40.0\n",
        encoding="utf-8",
    )
    (watershed_dir / "channels.csv").write_text(
        "topaz_id,area,centroid_lon,centroid_lat\n994,5.0,-100.0,40.0\n",
        encoding="utf-8",
    )

    _patch_dummy_watershed_and_translator(monkeypatch)
    monkeypatch.setattr(peridot_runner, "_update_catalog_entry", None)

    changed = peridot_runner.migrate_watershed_outputs(str(tmp_path), remove_csv=False, verbose=False)

    assert changed is True
    hills_df = pd.read_parquet(watershed_dir / "hillslopes.parquet")
    channels_df = pd.read_parquet(watershed_dir / "channels.parquet")
    assert hills_df["topaz_id"].tolist() == [11]
    assert channels_df["topaz_id"].tolist() == [14]
    assert hills_df["wepp_id"].tolist() == [111]
    assert channels_df["wepp_id"].tolist() == [114]
    assert channels_df["chn_enum"].tolist() == [1]


@pytest.mark.unit
def test_wait_for_file_times_out(tmp_path):
    missing = tmp_path / "missing.txt"
    with pytest.raises(FileNotFoundError):
        peridot_runner._wait_for_file(str(missing), timeout_s=0.1, poll_s=0.02)
