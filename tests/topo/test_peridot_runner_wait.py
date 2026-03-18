import threading
import time
from pathlib import Path

import pytest

from wepppy.topo.peridot import peridot_runner


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
def test_post_abstract_watershed_removes_stale_flowpaths_parquet(
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
    stale_parquet = watershed_dir / "flowpaths.parquet"
    stale_parquet.write_bytes(b"stale")

    catalog_updates = []
    monkeypatch.setattr(
        peridot_runner,
        "_update_catalog_entry",
        lambda wd, rel: catalog_updates.append((wd, rel)),
    )

    peridot_runner.post_abstract_watershed(str(tmp_path), verbose=False)

    assert not stale_parquet.exists()
    assert (str(tmp_path), "watershed/flowpaths.parquet") in catalog_updates


@pytest.mark.unit
def test_wait_for_file_times_out(tmp_path):
    missing = tmp_path / "missing.txt"
    with pytest.raises(FileNotFoundError):
        peridot_runner._wait_for_file(str(missing), timeout_s=0.1, poll_s=0.02)
