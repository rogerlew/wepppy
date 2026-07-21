"""Unit tests for the PATH-CE report render service (Quarto invocation mocked)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("plotly")

from wepppy.nodb.mods.path_ce import report_service
from wepppy.nodb.mods.path_ce.path_cost_effective import _normalize_config

pytestmark = pytest.mark.unit

ARTIFACTS = {
    "prepared_frame": "path/path_ce_final_data.parquet",
    "sweep": "path/sweep.parquet",
}


def _run_dir(tmp_path: Path) -> Path:
    wd = tmp_path / "run"
    (wd / "path").mkdir(parents=True)
    (wd / "dem" / "wbt").mkdir(parents=True)
    (wd / "dem" / "wbt" / "subcatchments.WGS.geojson").write_text('{"type":"FeatureCollection","features":[]}')
    (wd / "dem" / "wbt" / "channels.WGS.geojson").write_text('{"type":"FeatureCollection","features":[]}')
    (wd / "path" / "path_ce_final_data.parquet").write_bytes(b"stub")
    (wd / "path" / "sweep.parquet").write_bytes(b"stub")
    return wd


def test_build_payload_structure(tmp_path):
    wd = _run_dir(tmp_path)
    config = _normalize_config({"sdyd_threshold": 15.0, "sddc_threshold": 48.2})
    payload = report_service.build_payload(
        str(wd), config, ARTIFACTS,
        "dem/wbt/subcatchments.WGS.geojson", "dem/wbt/channels.WGS.geojson",
        tmp_path,
    )
    assert payload["sdyd_threshold"] == 15.0
    assert payload["treatments"] == ["0.5 tons/acre", "1 tons/acre", "2 tons/acre"]
    assert payload["treatment_cost"] == [2475.0, 2475.0, 2475.0]
    assert payload["treatment_quantity"] == [0.5, 1.0, 2.0]
    assert payload["fixed_cost"] == [500.0, 1000.0, 1500.0]
    assert payload["input_files"]["prepared_frame"].endswith("path/path_ce_final_data.parquet")
    # spatial paths are staged relative to the render cwd
    assert payload["spatial_files"]["subcatchments_geojson"] == "static/subcatchments.WGS.geojson"
    assert payload["spatial_files"]["channels_geojson"] == "static/channels.WGS.geojson"


def test_render_requires_subcatchments(tmp_path):
    wd = _run_dir(tmp_path)
    config = _normalize_config({})
    with pytest.raises(report_service.PathCEReportError, match="subcatchments"):
        report_service.render_report(str(wd), config, ARTIFACTS, None, None)


def _fake_quarto(write_html: bool, returncode: int = 0):
    def _run(cmd, staging, env):
        cwd = Path(staging)
        payload_path = cwd / "payload.json"
        assert payload_path.exists(), "payload.json must be staged before render"
        # staged inputs the QMD depends on
        assert (cwd / "PATH_CE_Report.qmd").exists()
        assert (cwd / "static" / "js" / "vendor" / "plotly.min.js").exists()
        assert (cwd / "static" / "js" / "vendor" / "deck.gl-8.9.31.min.js").exists()
        assert (cwd / "static" / "subcatchments.WGS.geojson").exists()
        assert env.get("HOME") == str(cwd)
        assert env.get("PATH_REPORT_INPUT_JSON") == str(payload_path)
        assert "-P" not in cmd  # papermill-free parameter delivery
        if write_html:
            (cwd / report_service.REPORT_HTML).write_text("<html>report</html>")
            (cwd / "static" / "downloads" / "PATH_prepared_hillslope_data.csv").write_text("a,b\n")
        return SimpleNamespace(returncode=returncode, stdout="rendered", stderr="")

    return _run


def test_render_success_promotes_report_tree(tmp_path, monkeypatch):
    wd = _run_dir(tmp_path)
    config = _normalize_config({"sdyd_threshold": 15.0, "sddc_threshold": 48.2})
    monkeypatch.setattr(report_service, "_run_quarto", _fake_quarto(write_html=True))

    relpath = report_service.render_report(
        str(wd), config, ARTIFACTS,
        "dem/wbt/subcatchments.WGS.geojson", "dem/wbt/channels.WGS.geojson",
    )

    assert relpath == "path/report/PATH_CE_Report.html"
    report_dir = wd / "path" / "report"
    assert (report_dir / "PATH_CE_Report.html").exists()
    assert (report_dir / "static" / "js" / "vendor" / "plotly.min.js").exists()
    assert (report_dir / "static" / "js" / "interactive-hillslope-map.js").exists()
    assert (report_dir / "static" / "downloads" / "PATH_prepared_hillslope_data.csv").exists()
    assert (report_dir / "static" / "subcatchments.WGS.geojson").exists()


def test_render_failure_surfaces_log_tail(tmp_path, monkeypatch):
    wd = _run_dir(tmp_path)
    config = _normalize_config({})

    def _fail(cmd, staging, env):
        return SimpleNamespace(returncode=3, stdout="", stderr="Kernel died horribly")

    monkeypatch.setattr(report_service, "_run_quarto", _fail)
    with pytest.raises(report_service.PathCEReportError, match="Kernel died horribly"):
        report_service.render_report(
            str(wd), config, ARTIFACTS, "dem/wbt/subcatchments.WGS.geojson", None
        )


def test_render_missing_html_is_error(tmp_path, monkeypatch):
    wd = _run_dir(tmp_path)
    config = _normalize_config({})
    monkeypatch.setattr(report_service, "_run_quarto", _fake_quarto(write_html=False))
    with pytest.raises(report_service.PathCEReportError, match="was not produced"):
        report_service.render_report(
            str(wd), config, ARTIFACTS, "dem/wbt/subcatchments.WGS.geojson", None
        )


def test_render_rejects_symlinked_geojson(tmp_path, monkeypatch):
    wd = _run_dir(tmp_path)
    real = wd / "dem" / "wbt" / "subcatchments.WGS.geojson"
    link = wd / "dem" / "wbt" / "evil.WGS.geojson"
    link.symlink_to(real)
    config = _normalize_config({})
    monkeypatch.setattr(report_service, "_run_quarto", _forbid_render)
    with pytest.raises(report_service.PathCEReportError, match="symlink"):
        report_service.render_report(
            str(wd), config, ARTIFACTS, "dem/wbt/evil.WGS.geojson", None
        )


def test_render_rejects_geojson_escaping_run_dir(tmp_path, monkeypatch):
    wd = _run_dir(tmp_path)
    outside = tmp_path / "outside.geojson"
    outside.write_text('{"type":"FeatureCollection","features":[]}')
    config = _normalize_config({})
    monkeypatch.setattr(report_service, "_run_quarto", _forbid_render)
    with pytest.raises(report_service.PathCEReportError, match="escapes|not found"):
        report_service.render_report(
            str(wd), config, ARTIFACTS, "../outside.geojson", None
        )


def test_render_rejects_non_geojson_content(tmp_path, monkeypatch):
    wd = _run_dir(tmp_path)
    (wd / "dem" / "wbt" / "subcatchments.WGS.geojson").write_text('{"not": "geojson"}')
    config = _normalize_config({})
    monkeypatch.setattr(report_service, "_run_quarto", _forbid_render)
    with pytest.raises(report_service.PathCEReportError, match="not GeoJSON"):
        report_service.render_report(
            str(wd), config, ARTIFACTS, "dem/wbt/subcatchments.WGS.geojson", None
        )


def _forbid_render(*args, **kwargs):
    raise AssertionError("quarto must not launch when staging validation fails")


def test_staging_failure_cleans_up_and_wraps(tmp_path, monkeypatch):
    wd = _run_dir(tmp_path)
    config = _normalize_config({})
    created = {}

    real_mkdtemp = report_service.tempfile.mkdtemp

    def _tracking_mkdtemp(*args, **kwargs):
        created["dir"] = real_mkdtemp(*args, **kwargs)
        return created["dir"]

    monkeypatch.setattr(report_service.tempfile, "mkdtemp", _tracking_mkdtemp)
    # missing geojson triggers a staging failure after mkdtemp
    with pytest.raises(report_service.PathCEReportError, match="not found"):
        report_service.render_report(
            str(wd), config, ARTIFACTS, "dem/wbt/missing.WGS.geojson", None
        )
    assert not Path(created["dir"]).exists(), "staging dir must be cleaned up on failure"


def test_rerender_replaces_previous_report(tmp_path, monkeypatch):
    wd = _run_dir(tmp_path)
    config = _normalize_config({})
    stale = wd / "path" / "report"
    stale.mkdir(parents=True)
    (stale / "stale.html").write_text("old")

    monkeypatch.setattr(report_service, "_run_quarto", _fake_quarto(write_html=True))
    report_service.render_report(
        str(wd), config, ARTIFACTS, "dem/wbt/subcatchments.WGS.geojson", None
    )
    assert not (wd / "path" / "report" / "stale.html").exists()
    assert (wd / "path" / "report" / "PATH_CE_Report.html").exists()
