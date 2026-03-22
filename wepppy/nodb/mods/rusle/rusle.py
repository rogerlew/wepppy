"""NoDb facade for end-to-end RUSLE orchestration."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from os.path import exists as _exists
from os.path import join as _join
from typing import Any, Mapping, Sequence

import numpy as np
import rasterio

from wepppy.climates.cligen.cligen import cli_calculate_static_r
from wepppy.landcover.rap import RangelandAnalysisPlatformV3
from wepppy.nodb.base import NoDbBase, TriggerEvents, nodb_setter
from wepppy.nodb.core import Climate, Landuse, Ron, Watershed
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.polaris import Polaris
from wepppy.query_engine.activate import update_catalog_entry

from .c_integration import RusleCResult, run_rusle_c_factor
from .k_integration import RusleKResult, run_rusle_k_factors
from .ls_integration import RusleLsResult, run_rusle_ls_factor

__all__ = ["Rusle"]

SUPPORTED_C_MODES: tuple[str, ...] = ("observed_rap", "scenario_sbs")
SUPPORTED_K_MODES: tuple[str, ...] = ("polaris_nomograph", "polaris_epic")

RUSLE_POLARIS_PROPERTIES: tuple[str, ...] = ("sand", "silt", "clay", "om", "bd", "ksat")
RUSLE_POLARIS_STATISTICS: tuple[str, ...] = ("mean",)
RUSLE_POLARIS_DEPTHS: tuple[str, ...] = ("0_5", "5_15")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _relative_path(base: str, path: str) -> str:
    return os.path.relpath(path, base).replace(os.sep, "/")


def _load_manifest(path: str) -> dict[str, Any]:
    if not _exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def _write_manifest(path: str, payload: Mapping[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(dict(payload), stream, indent=2, sort_keys=True)


def _coerce_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    token = str(value).strip().lower()
    if token in {"true", "1", "yes", "on"}:
        return True
    if token in {"false", "0", "no", "off"}:
        return False
    raise ValueError(f"Could not parse boolean value {value!r}")


def _coerce_mode_list(
    value: Any,
    *,
    allowed: Sequence[str],
    fallback: Sequence[str],
) -> list[str]:
    allowed_set = set(allowed)
    if value is None:
        selected = list(fallback)
    elif isinstance(value, str):
        selected = [token.strip() for token in value.split(",") if token.strip()]
    elif isinstance(value, (list, tuple, set)):
        selected = [str(token).strip() for token in value if str(token).strip()]
    else:
        raise ValueError(f"Expected a list-like mode selection, got {type(value).__name__}")

    selected = list(dict.fromkeys(selected))
    if not selected:
        selected = list(fallback)

    invalid = [mode for mode in selected if mode not in allowed_set]
    if invalid:
        raise ValueError(f"Unsupported mode(s): {invalid}. Allowed: {tuple(allowed)}")

    return selected


def _read_float_band(path: str) -> tuple[np.ndarray, dict[str, Any]]:
    with rasterio.open(path) as dataset:
        data = dataset.read(1).astype(np.float64)
        profile = dict(dataset.profile)
        nodata = dataset.nodata

    if nodata is not None:
        data[np.isclose(data, float(nodata), equal_nan=True)] = np.nan
    data[~np.isfinite(data)] = np.nan
    return data, profile


def _write_float_raster(path: str, data: np.ndarray, profile: Mapping[str, Any], *, nodata: float = -9999.0) -> None:
    out_profile = dict(profile)
    out_profile.update(
        {
            "driver": "GTiff",
            "dtype": "float32",
            "count": 1,
            "nodata": nodata,
            "compress": "deflate",
        }
    )
    writable = np.where(np.isfinite(data), data, nodata).astype(np.float32)
    with rasterio.open(path, "w", **out_profile) as dataset:
        dataset.write(writable, 1)


class Rusle(NoDbBase):
    """Compose LS/R/K/C/P components and emit final mode-specific `A` rasters."""

    __name__ = "Rusle"
    filename = "rusle.nodb"

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: str | None = None,
        group_name: str | None = None,
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)
        default_rap_year = int(RangelandAnalysisPlatformV3.latest_completed_year())
        configured_rap_year = self.config_get_int("rusle", "rap_year", default_rap_year)
        configured_modes = _coerce_mode_list(
            self.config_get_raw("rusle", "k_modes", None),
            allowed=SUPPORTED_K_MODES,
            fallback=("polaris_nomograph",),
        )
        configured_default_k = self.config_get_str("rusle", "default_k_mode", configured_modes[0])
        if configured_default_k not in configured_modes:
            configured_modes.append(configured_default_k)

        with self.locked():
            os.makedirs(self.rusle_dir, exist_ok=True)
            self._c_mode = self.config_get_str("rusle", "c_mode", "observed_rap")
            self._rap_year = int(configured_rap_year)
            self._k_modes = configured_modes
            self._default_k_mode = configured_default_k
            self._p_value = float(self.config_get_float("rusle", "p_value", 1.0))
            self._last_build_artifacts: dict[str, str] = {}

    def on(self, evt: TriggerEvents) -> None:
        return None

    @property
    def rusle_dir(self) -> str:
        return _join(self.wd, "rusle")

    @property
    def rusle_rap_dir(self) -> str:
        return _join(self.rusle_dir, "rap")

    @property
    def c_mode(self) -> str:
        return str(getattr(self, "_c_mode", "observed_rap"))

    @c_mode.setter
    @nodb_setter
    def c_mode(self, value: str) -> None:
        token = str(value).strip()
        if token not in SUPPORTED_C_MODES:
            raise ValueError(f"Unsupported c_mode {value!r}; expected one of {SUPPORTED_C_MODES}")
        self._c_mode = token

    @property
    def rap_year(self) -> int:
        return int(getattr(self, "_rap_year", int(RangelandAnalysisPlatformV3.latest_completed_year())))

    @rap_year.setter
    @nodb_setter
    def rap_year(self, value: int) -> None:
        self._rap_year = int(value)

    @property
    def k_modes(self) -> list[str]:
        return list(getattr(self, "_k_modes", ["polaris_nomograph"]))

    @k_modes.setter
    @nodb_setter
    def k_modes(self, value: Sequence[str]) -> None:
        self._k_modes = _coerce_mode_list(
            value,
            allowed=SUPPORTED_K_MODES,
            fallback=("polaris_nomograph",),
        )

    @property
    def default_k_mode(self) -> str:
        return str(getattr(self, "_default_k_mode", "polaris_nomograph"))

    @default_k_mode.setter
    @nodb_setter
    def default_k_mode(self, value: str) -> None:
        token = str(value).strip()
        if token not in SUPPORTED_K_MODES:
            raise ValueError(f"Unsupported default_k_mode {value!r}; expected one of {SUPPORTED_K_MODES}")
        self._default_k_mode = token

    @property
    def p_value(self) -> float:
        return float(getattr(self, "_p_value", 1.0))

    @p_value.setter
    @nodb_setter
    def p_value(self, value: float) -> None:
        self._p_value = float(value)

    @property
    def last_build_artifacts(self) -> dict[str, str]:
        return dict(getattr(self, "_last_build_artifacts", {}))

    def available_rap_years(self) -> list[int]:
        os.makedirs(self.rusle_rap_dir, exist_ok=True)
        manager = RangelandAnalysisPlatformV3(wd=self.rusle_rap_dir, bbox=None)
        years = manager.available_years(include_cached=True)
        return sorted(int(year) for year in years)

    def parse_inputs(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        raw = dict(payload or {})

        c_mode = str(raw.get("c_mode", self.c_mode)).strip()
        if c_mode not in SUPPORTED_C_MODES:
            raise ValueError(f"Unsupported c_mode {c_mode!r}; expected one of {SUPPORTED_C_MODES}")

        rap_year = int(raw.get("rap_year", self.rap_year))
        rap_years = self.available_rap_years()
        if rap_years and rap_year not in rap_years:
            raise ValueError(
                f"rap_year {rap_year} is not available; choose one of {rap_years[0]}..{rap_years[-1]}"
            )

        k_modes = _coerce_mode_list(
            raw.get("k_modes", self.k_modes),
            allowed=SUPPORTED_K_MODES,
            fallback=self.k_modes,
        )

        default_k_mode = str(raw.get("default_k_mode", self.default_k_mode)).strip()
        if default_k_mode not in SUPPORTED_K_MODES:
            raise ValueError(
                f"Unsupported default_k_mode {default_k_mode!r}; expected one of {SUPPORTED_K_MODES}"
            )
        if default_k_mode not in k_modes:
            raise ValueError("default_k_mode must be included in k_modes")

        p_value = float(raw.get("p_value", self.p_value))
        force_polaris_refresh = _coerce_bool(raw.get("force_polaris_refresh"), default=False)

        return {
            "c_mode": c_mode,
            "rap_year": rap_year,
            "k_modes": k_modes,
            "default_k_mode": default_k_mode,
            "p_value": p_value,
            "force_polaris_refresh": force_polaris_refresh,
        }

    def _extract_static_r(self, payload: Mapping[str, Any]) -> float:
        candidates = ("mean_annual_r", "annual_r", "r_factor")
        for key in candidates:
            value = payload.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        raise ValueError("Static R payload does not include a numeric mean annual R factor")

    def _write_constant_from_dem(self, dem_path: str, output_path: str, value: float) -> None:
        with rasterio.open(dem_path) as dataset:
            dem = dataset.read(1).astype(np.float64)
            profile = dict(dataset.profile)
            nodata = dataset.nodata

        valid = np.isfinite(dem)
        if nodata is not None:
            valid &= ~np.isclose(dem, float(nodata), equal_nan=True)
        constant = np.full(dem.shape, np.nan, dtype=np.float64)
        constant[valid] = float(value)
        _write_float_raster(output_path, constant, profile)

    def _expected_polaris_layers(self) -> list[str]:
        layers: list[str] = []
        for prop in RUSLE_POLARIS_PROPERTIES:
            for stat in RUSLE_POLARIS_STATISTICS:
                for depth in RUSLE_POLARIS_DEPTHS:
                    layers.append(f"{prop}_{stat}_{depth}")
        return layers

    def _polaris_payload(self, *, force_refresh: bool) -> dict[str, Any]:
        return {
            "force_refresh": bool(force_refresh),
            "properties": list(RUSLE_POLARIS_PROPERTIES),
            "statistics": list(RUSLE_POLARIS_STATISTICS),
            "depths": list(RUSLE_POLARIS_DEPTHS),
        }

    def _polaris_layers_need_refresh(self, payload: Mapping[str, Any]) -> tuple[bool, str]:
        expected_layers = self._expected_polaris_layers()
        for layer_id in expected_layers:
            layer_path = _join(self.wd, "polaris", f"{layer_id}.tif")
            if not _exists(layer_path):
                return True, "missing_layer"

        manifest_path = _join(self.wd, "polaris", "manifest.json")
        if not _exists(manifest_path):
            return True, "missing_manifest"

        manifest = _load_manifest(manifest_path)
        request_payload = manifest.get("request", {})
        if list(request_payload.get("properties", [])) != list(payload["properties"]):
            return True, "properties_drift"
        if list(request_payload.get("statistics", [])) != list(payload["statistics"]):
            return True, "statistics_drift"
        if list(request_payload.get("depths", [])) != list(payload["depths"]):
            return True, "depths_drift"

        expected_relpaths = {f"polaris/{layer_id}.tif" for layer_id in expected_layers}
        records = manifest.get("records", [])
        record_relpaths = {
            str(record.get("output_relpath"))
            for record in records
            if isinstance(record, dict) and record.get("output_relpath")
        }
        if not expected_relpaths.issubset(record_relpaths):
            return True, "record_inventory_drift"

        return False, "aligned"

    def _ensure_polaris_layers(self, *, force_refresh: bool) -> dict[str, Any]:
        payload = self._polaris_payload(force_refresh=force_refresh)
        need_refresh, reason = self._polaris_layers_need_refresh(payload)
        fetched = bool(force_refresh) or need_refresh
        summary: dict[str, Any] = {"layers_requested": len(self._expected_polaris_layers())}
        if fetched:
            summary = Polaris.getInstance(self.wd).acquire_and_align(payload=payload)
        return {
            "fetched": fetched,
            "reason": reason if not force_refresh else "force_refresh",
            "payload": payload,
            "summary": summary,
        }

    def _resolve_observed_rap(self, *, extent: Sequence[float], rap_year: int) -> str:
        os.makedirs(self.rusle_rap_dir, exist_ok=True)
        manager = RangelandAnalysisPlatformV3(wd=self.rusle_rap_dir, bbox=extent)
        rap_path = manager.get_dataset_fn(rap_year)
        update_catalog_entry(self.wd, _relative_path(self.wd, rap_path))
        return rap_path

    def _selected_k_path(self, k_result: RusleKResult, *, default_k_mode: str) -> str:
        k_paths = {
            "polaris_nomograph": k_result.nomograph,
            "polaris_epic": k_result.epic,
        }
        selected = k_paths.get(default_k_mode)
        if selected is None:
            raise ValueError(f"K output for default mode {default_k_mode!r} is not available")
        return selected

    def _write_final_a(
        self,
        *,
        r_path: str,
        k_path: str,
        ls_path: str,
        c_path: str,
        p_path: str,
        output_path: str,
    ) -> None:
        r_data, profile = _read_float_band(r_path)
        k_data, _ = _read_float_band(k_path)
        ls_data, _ = _read_float_band(ls_path)
        c_data, _ = _read_float_band(c_path)
        p_data, _ = _read_float_band(p_path)

        valid = (
            np.isfinite(r_data)
            & np.isfinite(k_data)
            & np.isfinite(ls_data)
            & np.isfinite(c_data)
            & np.isfinite(p_data)
        )
        a_data = np.full(r_data.shape, np.nan, dtype=np.float64)
        a_data[valid] = r_data[valid] * k_data[valid] * ls_data[valid] * c_data[valid] * p_data[valid]
        _write_float_raster(output_path, a_data, profile)

    def _write_readme(self, *, options: Mapping[str, Any], artifacts: Mapping[str, str]) -> str:
        readme_path = _join(self.rusle_dir, "README.md")
        lines = [
            "# RUSLE Outputs",
            "",
            f"- Generated UTC: `{_utc_now_iso()}`",
            f"- C mode: `{options['c_mode']}`",
            f"- K modes selected: `{', '.join(options['k_modes'])}`",
            f"- Default K mode: `{options['default_k_mode']}`",
            f"- RAP year: `{options['rap_year']}`",
            f"- P value: `{options['p_value']}`",
            "",
            "## Primary outputs",
            "",
            f"- A (mode-specific): `{artifacts['a_relpath']}`",
            f"- C (mode-specific): `{artifacts['c_relpath']}`",
            f"- K (default mode source): `{artifacts['k_relpath']}`",
        ]
        with open(readme_path, "w", encoding="utf-8") as stream:
            stream.write("\n".join(lines) + "\n")
        return readme_path

    def build(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        options = self.parse_inputs(payload)
        with self.locked():
            self._c_mode = options["c_mode"]
            self._rap_year = int(options["rap_year"])
            self._k_modes = list(options["k_modes"])
            self._default_k_mode = options["default_k_mode"]
            self._p_value = float(options["p_value"])

        ron = Ron.getInstance(self.wd)
        climate = Climate.getInstance(self.wd)
        landuse = Landuse.getInstance(self.wd)
        watershed = Watershed.getInstance(self.wd)
        disturbed = Disturbed.tryGetInstance(self.wd)

        dem_path = ron.dem_fn
        if not _exists(dem_path):
            raise FileNotFoundError(f"DEM path does not exist: {dem_path}")

        cli_path = climate.cli_path
        if not _exists(cli_path):
            raise FileNotFoundError(f"Climate CLI path does not exist: {cli_path}")

        landuse_path = landuse.lc_fn
        if not _exists(landuse_path):
            raise FileNotFoundError(f"Landuse raster path does not exist: {landuse_path}")

        polaris_state = self._ensure_polaris_layers(force_refresh=bool(options["force_polaris_refresh"]))

        r_metrics = cli_calculate_static_r(cli_path)
        r_scalar = self._extract_static_r(r_metrics)
        r_path = _join(self.rusle_dir, "r.tif")
        self._write_constant_from_dem(dem_path, r_path, r_scalar)
        update_catalog_entry(self.wd, _relative_path(self.wd, r_path))

        channel_mask = watershed.netful if watershed.netful and _exists(watershed.netful) else None
        ls_result: RusleLsResult = run_rusle_ls_factor(
            self.wd,
            dem_path,
            channel_mask=channel_mask,
        )
        for path in asdict(ls_result).values():
            if path and _exists(path):
                update_catalog_entry(self.wd, _relative_path(self.wd, path))

        k_result: RusleKResult = run_rusle_k_factors(
            self.wd,
            statistic="mean",
            selected_modes=options["k_modes"],
            default_k_mode=options["default_k_mode"],
            write_default_k=False,
        )
        update_catalog_entry(self.wd, _relative_path(self.wd, k_result.manifest))

        c_output_filename = f"c_{options['c_mode']}.tif"
        if options["c_mode"] == "observed_rap":
            if ron.map is None:
                raise ValueError("Observed RAP mode requires a run map extent")
            rap_path = self._resolve_observed_rap(extent=ron.map.extent, rap_year=int(options["rap_year"]))
            c_result: RusleCResult = run_rusle_c_factor(
                self.wd,
                dem_path,
                c_mode="observed_rap",
                c_output_filename=c_output_filename,
                rap=rap_path,
            )
        else:
            sbs_path: str | None = None
            if disturbed is not None and disturbed.has_map and disturbed.disturbed_path is not None:
                if _exists(disturbed.disturbed_path):
                    sbs_path = disturbed.disturbed_path
            c_result = run_rusle_c_factor(
                self.wd,
                dem_path,
                c_mode="scenario_sbs",
                c_output_filename=c_output_filename,
                landuse=landuse_path,
                sbs=sbs_path,
            )

        p_path = _join(self.rusle_dir, "p.tif")
        self._write_constant_from_dem(dem_path, p_path, float(options["p_value"]))
        update_catalog_entry(self.wd, _relative_path(self.wd, p_path))

        selected_k_path = self._selected_k_path(k_result, default_k_mode=options["default_k_mode"])
        a_filename = f"a_{options['c_mode']}_{options['default_k_mode']}.tif"
        a_path = _join(self.rusle_dir, a_filename)
        self._write_final_a(
            r_path=r_path,
            k_path=selected_k_path,
            ls_path=ls_result.ls,
            c_path=c_result.c,
            p_path=p_path,
            output_path=a_path,
        )
        update_catalog_entry(self.wd, _relative_path(self.wd, a_path))

        artifacts = {
            "r_relpath": _relative_path(self.wd, r_path),
            "ls_relpath": _relative_path(self.wd, ls_result.ls),
            "k_relpath": _relative_path(self.wd, selected_k_path),
            "c_relpath": _relative_path(self.wd, c_result.c),
            "p_relpath": _relative_path(self.wd, p_path),
            "a_relpath": _relative_path(self.wd, a_path),
        }
        readme_path = self._write_readme(options=options, artifacts=artifacts)
        update_catalog_entry(self.wd, _relative_path(self.wd, readme_path))

        manifest_path = _join(self.rusle_dir, "manifest.json")
        manifest = _load_manifest(manifest_path)
        manifest["rusle"] = {
            "generated_utc": _utc_now_iso(),
            "options": {
                "c_mode": options["c_mode"],
                "k_modes": list(options["k_modes"]),
                "default_k_mode": options["default_k_mode"],
                "rap_year": int(options["rap_year"]),
                "p_value": float(options["p_value"]),
            },
            "static_r": {
                "mean_annual_r": float(r_scalar),
                "source_cli": cli_path,
            },
            "polaris": polaris_state,
            "artifacts": artifacts,
        }
        _write_manifest(manifest_path, manifest)
        update_catalog_entry(self.wd, _relative_path(self.wd, manifest_path))

        with self.locked():
            self._last_build_artifacts = artifacts

        return {
            "mode": options["c_mode"],
            "default_k_mode": options["default_k_mode"],
            "rap_year": int(options["rap_year"]),
            "artifacts": artifacts,
        }

