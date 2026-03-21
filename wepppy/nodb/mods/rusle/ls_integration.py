"""RUSLE LS integration runner for WEPPpy NoDb workflows.

This module provides a focused, implementation-ready integration path for the
`RusleLsFactor` WBT command. It stages canonical LS outputs under `wd/rusle`,
invokes WBT with explicit routing/mask/cap controls, and writes
`rusle/manifest.json` provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import os
from os.path import exists as _exists
from os.path import join as _join
from typing import Optional

from whitebox_tools import WhiteboxTools


@dataclass(frozen=True)
class RusleLsResult:
    """Paths for LS artifacts produced by :func:`run_rusle_ls_factor`."""

    ls: str
    l: str
    s: str
    sca: str
    effective_slope_length: str
    manifest: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_manifest(path: str) -> dict:
    if not _exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def _write_manifest(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)


def run_rusle_ls_factor(
    wd: str,
    dem: str,
    *,
    sca: Optional[str] = None,
    slope_deg: Optional[str] = None,
    channel_mask: Optional[str] = None,
    blocking_mask: Optional[str] = None,
    routing_mode: str = "dinf",
    max_slope_length_m: float = 304.8,
    m_regime: str = "moderate",
    verbose: bool = False,
) -> RusleLsResult:
    """Run `RusleLsFactor` and write canonical LS artifacts + manifest.

    Args:
        wd: Run working directory.
        dem: DEM raster path.
        sca: Optional precomputed SCA raster (`m^2/m`).
        slope_deg: Optional precomputed slope raster in degrees.
        channel_mask: Optional channel stop-mask raster (`>0` means stop).
        blocking_mask: Optional blocking stop-mask raster (`>0` means stop).
        routing_mode: Routing mode (`dinf`, `fd8`, `d8`).
        max_slope_length_m: Effective slope-length cap in meters.
        m_regime: Optional `m` regime (`slight`, `moderate`, `high_rill`).
        verbose: Forwarded to WBT wrapper.

    Returns:
        `RusleLsResult` containing emitted artifact paths.
    """

    if not _exists(dem):
        raise FileNotFoundError(f"DEM path does not exist: {dem}")

    rusle_dir = _join(wd, "rusle")
    os.makedirs(rusle_dir, exist_ok=True)

    ls_path = _join(rusle_dir, "ls.tif")
    l_path = _join(rusle_dir, "l.tif")
    s_path = _join(rusle_dir, "s.tif")
    sca_path = _join(rusle_dir, "sca.tif")
    eff_path = _join(rusle_dir, "effective_slope_length.tif")
    manifest_path = _join(rusle_dir, "manifest.json")

    wbt = WhiteboxTools(verbose=verbose, raise_on_error=True)
    wbt.set_working_dir(rusle_dir)

    ret = wbt.rusle_ls_factor(
        dem=dem,
        output=ls_path,
        l_output=l_path,
        s_output=s_path,
        sca_output=sca_path,
        effective_slope_length_output=eff_path,
        sca=sca or "",
        slope_deg=slope_deg or "",
        channel_mask=channel_mask or "",
        blocking_mask=blocking_mask or "",
        routing=routing_mode,
        max_slope_length_m=max_slope_length_m,
        m_regime=m_regime,
    )

    if ret != 0:
        raise RuntimeError(f"RusleLsFactor failed with return code: {ret}")

    stop_components: list[str] = []
    if channel_mask:
        stop_components.append("channel_mask")
    if blocking_mask:
        stop_components.append("blocking_mask")

    ls_manifest = {
        "tool": "RusleLsFactor",
        "tool_version": "unknown",
        "l_method": "desmet_govers_1996",
        "s_method": "mccool_rusle_piecewise",
        "m_method": "mccool_1989_beta_moderate_base",
        "m_regime": m_regime,
        "routing_mode": routing_mode,
        "dem_hydrologically_sound_assumed": True,
        "max_slope_length_m": max_slope_length_m,
        "max_slope_length_basis": "rusle2_handbook_1000ft",
        "stop_mask_components": stop_components,
        "stop_mask_routing_behavior": "terminal_sink_no_renormalization",
        "sca_source": "input" if sca else "derived",
        "slope_source": "input" if slope_deg else "derived",
        "blocking_mask_source": "input_raster" if blocking_mask else "none",
        "generated_utc": _utc_now_iso(),
        "artifacts": asdict(
            RusleLsResult(
                ls=ls_path,
                l=l_path,
                s=s_path,
                sca=sca_path,
                effective_slope_length=eff_path,
                manifest=manifest_path,
            )
        ),
    }

    manifest = _load_manifest(manifest_path)
    manifest["ls"] = ls_manifest
    _write_manifest(manifest_path, manifest)

    return RusleLsResult(
        ls=ls_path,
        l=l_path,
        s=s_path,
        sca=sca_path,
        effective_slope_length=eff_path,
        manifest=manifest_path,
    )
