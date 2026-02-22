import os
from pathlib import Path

import pandas as pd
import pytest

from wepppy.nodb.base import redis_lock_client
from wepppy.nodb.mods.swat import swat as swat_module
from wepppy.nodb.mods.swat.swat import Swat


pytestmark = [pytest.mark.nodb, pytest.mark.integration]


class _FakeStdout:
    def __init__(self, lines):
        self._lines = list(lines)
        self._index = 0

    def readline(self):
        if self._index >= len(self._lines):
            return ""
        line = self._lines[self._index]
        self._index += 1
        return line

    def close(self):
        return None


class _FakeProcess:
    def __init__(self, lines=None, returncode=0):
        self._returncode = returncode
        self.stdout = _FakeStdout(lines or [])

    def poll(self):
        if self.stdout._index >= len(self.stdout._lines):
            return self._returncode
        return None

    def wait(self):
        return self._returncode


@pytest.fixture
def swat_instance(tmp_path):
    wd = tmp_path / "run"
    wd.mkdir()

    swat_bin = tmp_path / "swat_bin"
    swat_bin.write_text("#!/bin/sh\nexit 0\n")
    os.chmod(swat_bin, 0o755)

    cfg_path = tmp_path / "config.cfg"
    cfg_path.write_text(
        "\n".join(
            [
                "[nodb]",
                'mods = ["swat"]',
                "",
                "[swat]",
                "enabled = true",
                f"swat_bin = {swat_bin}",
                "swat_interchange_enabled = true",
                "swat_interchange_chunk_rows = 10",
                "",
                "[interchange]",
                "delete_after_interchange = false",
                "",
            ]
        )
        + "\n"
    )

    instance = Swat(str(wd), str(cfg_path))
    yield instance

    if redis_lock_client is not None:
        try:
            redis_lock_client.delete(instance._distributed_lock_key)
        except Exception:
            pass
    Swat._instances.clear()


def test_build_recall_connections_reads_sidecar_watershed_parquets(swat_instance):
    wd = Path(swat_instance.wd)
    hillslopes_parquet = wd / "watershed.hillslopes.parquet"
    channels_parquet = wd / "watershed.channels.parquet"

    pd.DataFrame(
        {
            "topaz_id": [11],
            "wepp_id": [1],
            "chn_enum": [1],
        }
    ).to_parquet(hillslopes_parquet, index=False)
    pd.DataFrame({"topaz_id": [14], "chn_enum": [1]}).to_parquet(channels_parquet, index=False)

    assert swat_instance.build_recall_connections() == [(1, 1)]


def test_run_swat_persists_interchange_summary(monkeypatch, swat_instance):
    (Path(swat_instance.swat_txtinout_dir) / "files_out.out").write_text(
        "HRU                       hru_wb_aa.txt\n"
    )

    monkeypatch.setattr(
        swat_module.subprocess,
        "Popen",
        lambda *args, **kwargs: _FakeProcess(lines=["ok\n"], returncode=0),
    )

    class _RustStub:
        def swat_outputs_to_parquet(self, *args, **kwargs):
            return {"output_paths": ["hru_wb_aa.parquet"], "skipped": []}

    monkeypatch.setattr(
        swat_module, "_load_rust_swat_interchange", lambda: (_RustStub(), None)
    )

    summary = swat_instance.run_swat()
    assert summary.get("interchange_summary") is not None

    Swat._instances.clear()
    reloaded = Swat.getInstance(swat_instance.wd)
    assert reloaded.run_summary["interchange_summary"] == summary["interchange_summary"]


def test_interchange_status_partial_from_skipped(monkeypatch, swat_instance):
    run_dir = Path(swat_instance.swat_outputs_dir) / "run_test"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "files_out.out").write_text("HRU hru_wb_aa.txt\n")

    class _RustStub:
        def swat_outputs_to_parquet(self, *args, **kwargs):
            return {
                "output_paths": ["hru_wb_aa.parquet"],
                "skipped": [{"filename": "hru_ls_aa.txt", "reason": "column_mismatch"}],
            }

    monkeypatch.setattr(
        swat_module, "_load_rust_swat_interchange", lambda: (_RustStub(), None)
    )

    swat_instance.run_swat_interchange(run_dir=str(run_dir))
    assert swat_instance.swat_interchange_status == "partial"


def test_interchange_error_clears_summary(monkeypatch, swat_instance):
    run_dir = Path(swat_instance.swat_outputs_dir) / "run_error"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "files_out.out").write_text("HRU hru_wb_aa.txt\n")

    with swat_instance.locked():
        swat_instance.swat_interchange_summary = {"output_paths": ["old.parquet"]}
        swat_instance.swat_interchange_status = "complete"

    class _RustStub:
        def swat_outputs_to_parquet(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        swat_module, "_load_rust_swat_interchange", lambda: (_RustStub(), None)
    )

    with pytest.raises(RuntimeError):
        swat_instance.run_swat_interchange(run_dir=str(run_dir))

    assert swat_instance.swat_interchange_status == "error"
    assert swat_instance.swat_interchange_summary is None


def test_interchange_failed_status_from_version_manifest(monkeypatch, swat_instance):
    run_dir = Path(swat_instance.swat_outputs_dir) / "run_failed"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "files_out.out").write_text("HRU hru_wb_aa.txt\n")

    class _RustStub:
        def swat_outputs_to_parquet(self, run_output_dir, **kwargs):
            interchange_dir = Path(kwargs["interchange_dir"])
            interchange_dir.mkdir(parents=True, exist_ok=True)
            version_path = interchange_dir / "interchange_version.json"
            version_path.write_text('{"status": "failed"}')
            raise RuntimeError("failed")

    monkeypatch.setattr(
        swat_module, "_load_rust_swat_interchange", lambda: (_RustStub(), None)
    )

    with pytest.raises(RuntimeError):
        swat_instance.run_swat_interchange(run_dir=str(run_dir))

    assert swat_instance.swat_interchange_status == "failed"
    assert swat_instance.swat_interchange_summary is None


def test_interchange_manifest_fallback(monkeypatch, swat_instance):
    run_dir = Path(swat_instance.swat_outputs_dir) / "run_manifest"
    run_dir.mkdir(parents=True, exist_ok=True)

    source_manifest = Path(swat_instance.swat_txtinout_dir) / "files_out.out"
    source_manifest.write_text("HRU hru_wb_aa.txt\n")

    class _RustStub:
        def swat_outputs_to_parquet(self, run_output_dir, **kwargs):
            manifest_path = kwargs.get("manifest_path")
            assert manifest_path is not None
            assert Path(manifest_path).exists()
            return {"output_paths": ["hru_wb_aa.parquet"], "skipped": []}

    monkeypatch.setattr(
        swat_module, "_load_rust_swat_interchange", lambda: (_RustStub(), None)
    )

    swat_instance.run_swat_interchange(run_dir=str(run_dir))


def test_interchange_manifest_fallback_skips_historical_run(monkeypatch, swat_instance):
    old_run_dir = Path(swat_instance.swat_outputs_dir) / "run_old"
    new_run_dir = Path(swat_instance.swat_outputs_dir) / "run_new"
    old_run_dir.mkdir(parents=True, exist_ok=True)
    new_run_dir.mkdir(parents=True, exist_ok=True)
    os.utime(old_run_dir, (1, 1))

    source_manifest = Path(swat_instance.swat_txtinout_dir) / "files_out.out"
    source_manifest.write_text("HRU hru_wb_aa.txt\n")

    swat_instance.swat_interchange_include = ["hru_wb_aa.txt"]

    class _RustStub:
        def swat_outputs_to_parquet(self, run_output_dir, **kwargs):
            assert kwargs.get("manifest_path") is None
            return {"output_paths": ["hru_wb_aa.parquet"], "skipped": []}

    monkeypatch.setattr(
        swat_module, "_load_rust_swat_interchange", lambda: (_RustStub(), None)
    )

    swat_instance.run_swat_interchange(run_dir=str(old_run_dir))
    assert not (old_run_dir / "files_out.out").exists()


def test_estimate_total_area_returns_none_without_hillslope_parquet(swat_instance):
    assert swat_instance._estimate_total_area_ha() is None
