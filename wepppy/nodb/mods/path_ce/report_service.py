"""PATH-CE HTML report rendering (Phase 3; D1/D2 — in-worker Quarto, HTML only).

Stages a scratch render directory, writes the machine-to-machine payload JSON
the vendored QMD consumes, invokes the Quarto CLI, and promotes outputs to
``<wd>/path/report/``. The QMD and its static assets live in
``wepppy/nodb/mods/path_ce/report/``; plotly.min.js is staged from the
installed Python plotly package so the browser bundle always matches the
version that produced the figure JSON.

Requires both WGS geojsons (interactive + folium maps have no missing-spatial
guard upstream); callers skip rendering with a warning when they are absent
(the precondition report already surfaces this).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

__all__ = [
    "PathCEReportError",
    "REPORT_DIR",
    "REPORT_HTML",
    "build_payload",
    "render_report",
]

logger = logging.getLogger(__name__)

REPORT_DIR = "report"
REPORT_HTML = "PATH_CE_Report.html"

_QMD_NAME = "PATH_CE_Report.qmd"
_ASSETS_ROOT = Path(__file__).parent / "report"

RENDER_TIMEOUT_SECONDS = 1800


class PathCEReportError(RuntimeError):
    """Raised when the Quarto render fails or required inputs are missing."""


def _plotly_bundle_path() -> Path:
    import plotly

    bundle = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
    if not bundle.exists():
        raise PathCEReportError(f"plotly.min.js not found in plotly package data: {bundle}")
    return bundle


def build_payload(
    wd: str,
    config: Mapping[str, Any],
    artifacts: Mapping[str, str],
    subcatchments_geojson: str,
    channels_geojson: Optional[str],
    staging: Path,
) -> Dict[str, Any]:
    """Build the QMD payload; geojson paths are staged relative to the render cwd."""
    treatments = list(config["treatments"])
    wd_path = Path(wd)
    payload: Dict[str, Any] = {
        "sdyd_threshold": config["sdyd_threshold"],
        "sddc_threshold": config["sddc_threshold"],
        "slope_range": config.get("slope_range"),
        "severity_filter": config.get("severity_filter"),
        "treatments": [t["label"] for t in treatments],
        "treatment_cost": [t["unit_cost"] for t in treatments],
        "treatment_quantity": [t["quantity"] for t in treatments],
        "fixed_cost": [t["fixed_cost"] for t in treatments],
        "input_files": {
            "prepared_frame": str(wd_path / artifacts["prepared_frame"]),
            "sweep": str(wd_path / artifacts["sweep"]),
        },
        "spatial_files": {
            # staged copies (relative to render cwd) so the report's download
            # links and interactive loaders resolve within the report tree
            "subcatchments_geojson": f"static/{Path(subcatchments_geojson).name}",
            "channels_geojson": f"static/{Path(channels_geojson).name}" if channels_geojson else None,
        },
    }
    return payload


def _copy_run_geojson(wd_path: Path, relpath: str, staging: Path) -> None:
    """Copy a run geojson into staging with containment + content validation.

    These files end up in the publicly served report tree, so refuse symlinks,
    paths escaping the run directory, and non-GeoJSON content.
    """
    src = wd_path / relpath
    if src.is_symlink():
        raise PathCEReportError(f"refusing symlinked spatial input: {relpath}")
    if not src.is_file():
        raise PathCEReportError(f"spatial input not found: {relpath}")
    resolved = src.resolve()
    if not resolved.is_relative_to(wd_path.resolve()):
        raise PathCEReportError(f"spatial input escapes the run directory: {relpath}")
    try:
        content = json.loads(resolved.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise PathCEReportError(f"spatial input is not valid JSON: {relpath} ({exc})") from exc
    if not isinstance(content, dict) or content.get("type") not in ("FeatureCollection", "Feature"):
        raise PathCEReportError(f"spatial input is not GeoJSON: {relpath}")
    shutil.copy(resolved, staging / "static" / Path(relpath).name)


def _populate_staging(
    staging: Path, wd: str, subcatchments_geojson: str, channels_geojson: Optional[str]
) -> None:
    shutil.copy(_ASSETS_ROOT / _QMD_NAME, staging / _QMD_NAME)
    shutil.copytree(_ASSETS_ROOT / "static", staging / "static")
    shutil.copy(_plotly_bundle_path(), staging / "static" / "js" / "vendor" / "plotly.min.js")

    wd_path = Path(wd)
    _copy_run_geojson(wd_path, subcatchments_geojson, staging)
    if channels_geojson:
        _copy_run_geojson(wd_path, channels_geojson, staging)
    (staging / "static" / "downloads").mkdir(parents=True, exist_ok=True)


def _run_quarto(cmd: List[str], staging: Path, env: Dict[str, str]) -> "subprocess.CompletedProcess[str]":
    """Run quarto in its own process group so a timeout kills the kernel too."""
    proc = subprocess.Popen(
        cmd,
        cwd=staging,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=RENDER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        proc.communicate()
        raise
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


def render_report(
    wd: str,
    config: Mapping[str, Any],
    artifacts: Mapping[str, str],
    subcatchments_geojson: Optional[str],
    channels_geojson: Optional[str],
) -> str:
    """Render the HTML report; returns the report's wd-relative path.

    Raises :class:`PathCEReportError` on missing spatial inputs or a failed
    render (with the log tail in the message).
    """
    if not subcatchments_geojson:
        raise PathCEReportError(
            "subcatchments.WGS.geojson is required for the report maps; "
            "re-run the watershed WGS exports (see precondition warnings)."
        )

    staging: Optional[Path] = None
    try:
        staging = Path(tempfile.mkdtemp(prefix="path_ce_report_", dir="/tmp"))
        try:
            _populate_staging(staging, wd, subcatchments_geojson, channels_geojson)
        except OSError as exc:
            raise PathCEReportError(f"failed to stage report inputs: {exc}") from exc
        payload = build_payload(
            wd, config, artifacts, subcatchments_geojson, channels_geojson, staging
        )
        payload_path = staging / "payload.json"
        payload_path.write_text(json.dumps(payload, indent=1))

        cmd: List[str] = [
            "quarto",
            "render",
            _QMD_NAME,
            "--to",
            "html",
        ]
        env = {
            # inherit the worker env (first-party in-worker render, D1) so
            # wepppy's import-time integrations resolve; override the paths
            # jupyter/matplotlib write to and deliver the payload via env var
            # (-P injection would require papermill in the image)
            **os.environ,
            "PATH_REPORT_INPUT_JSON": str(payload_path),
            "HOME": str(staging),
            "QUARTO_PYTHON": "/opt/venv/bin/python",
            "MPLCONFIGDIR": str(staging / ".mpl"),
            "XDG_CACHE_HOME": str(staging / ".cache"),
            "XDG_DATA_HOME": str(staging / ".data"),
        }
        result = _run_quarto(cmd, staging, env)
        log_tail = ((result.stdout or "") + "\n" + (result.stderr or ""))[-4000:]
        if result.returncode != 0:
            raise PathCEReportError(
                f"quarto render failed (exit {result.returncode}); log tail:\n{log_tail}"
            )

        html_path = staging / REPORT_HTML
        if not html_path.exists():
            raise PathCEReportError(
                f"quarto render reported success but {REPORT_HTML} was not produced; "
                f"log tail:\n{log_tail}"
            )

        # near-atomic publish: assemble the complete tree beside the live one,
        # then swap via rename so readers never observe a partial report
        # (dot-prefixed staging names are unservable — the route rejects
        # hidden segments)
        report_parent = Path(wd) / "path"
        report_parent.mkdir(parents=True, exist_ok=True)
        report_dir = report_parent / REPORT_DIR
        incoming_dir = report_parent / f".{REPORT_DIR}.incoming"
        retired_dir = report_parent / f".{REPORT_DIR}.retired"
        for leftover in (incoming_dir, retired_dir):
            if leftover.exists():
                shutil.rmtree(leftover)
        incoming_dir.mkdir(parents=True)
        shutil.copy(html_path, incoming_dir / REPORT_HTML)
        # static tree ships the runtime-loaded scripts (Quarto cannot inline
        # dynamically created <script> tags) and the download CSVs
        shutil.copytree(staging / "static", incoming_dir / "static")
        if report_dir.exists():
            os.rename(report_dir, retired_dir)
        os.rename(incoming_dir, report_dir)
        shutil.rmtree(retired_dir, ignore_errors=True)
        logger.info("PATH-CE report rendered to %s", report_dir / REPORT_HTML)
        return f"path/{REPORT_DIR}/{REPORT_HTML}"
    except subprocess.TimeoutExpired as exc:
        raise PathCEReportError(
            f"quarto render timed out after {RENDER_TIMEOUT_SECONDS}s"
        ) from exc
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
