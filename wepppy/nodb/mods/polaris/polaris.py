"""POLARIS run-scoped raster retrieval and alignment controller."""

from __future__ import annotations

import ast
import inspect
import json
import logging
import os
import re
from datetime import datetime, timezone
from itertools import product
from os.path import exists as _exists
from os.path import join as _join
from typing import Any, ClassVar, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from wepppy.all_your_base.geo import raster_stacker
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.core import Ron
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.query_engine.activate import update_catalog_entry

__all__ = [
    "PolarisNoDbLockedException",
    "PolarisConfigError",
    "fetch_polaris_catalog_layer_ids",
    "parse_polaris_layer_id",
    "Polaris",
]

LOGGER = logging.getLogger(__name__)

POLARIS_BASE_URL_DEFAULT = "http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/"
POLARIS_README_PATH = "Readme"
POLARIS_VRT_PATH = "vrt/"
POLARIS_INDEX_TIMEOUT_SECONDS = 60

POLARIS_PROPERTIES: tuple[str, ...] = (
    "alpha",
    "bd",
    "clay",
    "hb",
    "ksat",
    "lambda",
    "n",
    "om",
    "ph",
    "sand",
    "silt",
    "theta_r",
    "theta_s",
)
POLARIS_STATISTICS: tuple[str, ...] = ("mean", "mode", "p5", "p50", "p95")
POLARIS_DEPTHS: tuple[str, ...] = ("0_5", "5_15", "15_30", "30_60", "60_100", "100_200")

POLARIS_DEFAULT_PROPERTIES: tuple[str, ...] = ("sand", "clay", "bd", "om")
POLARIS_DEFAULT_STATISTICS: tuple[str, ...] = ("mean",)
POLARIS_DEFAULT_DEPTHS: tuple[str, ...] = ("0_5",)

POLARIS_PROPERTY_UNITS: dict[str, str] = {
    "silt": "%",
    "sand": "%",
    "clay": "%",
    "bd": "g/cm3",
    "theta_s": "m3/m3",
    "theta_r": "m3/m3",
    "ksat": "log10(cm/hr)",
    "ph": "N/A",
    "om": "log10(%)",
    "lambda": "N/A",
    "hb": "log10(kPa)",
    "n": "N/A",
    "alpha": "log10(kPa-1)",
}
POLARIS_LOG10_PROPERTIES: frozenset[str] = frozenset({"hb", "alpha", "ksat", "om"})
POLARIS_RESAMPLE_METHODS: frozenset[str] = frozenset(
    {"near", "bilinear", "cubic", "cubic_spline", "lanczos", "average", "mode"}
)

_LAYER_HREF_RE = re.compile(r'href="([A-Za-z0-9_]+\.vrt)"')
_LAYER_NAME_RE = re.compile(
    r"^(?P<property>[a-z_]+)_(?P<stat>mean|mode|p5|p50|p95)_(?P<depth>\d+_\d+)$"
)


class PolarisNoDbLockedException(Exception):
    """Compatibility exception for lock-related failures."""


class PolarisConfigError(ValueError):
    """Raised when POLARIS configuration is invalid."""


def _normalize_base_url(value: str) -> str:
    text = str(value).strip()
    if not text:
        raise PolarisConfigError("POLARIS base_url cannot be empty.")
    return text.rstrip("/") + "/"


def _parse_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    raise PolarisConfigError(f"Could not parse boolean value '{value}'.")


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("[") or text.startswith("("):
            try:
                parsed = ast.literal_eval(text)
            except (ValueError, SyntaxError):
                parsed = [part.strip() for part in text.split(",")]
        else:
            parsed = [part.strip() for part in text.split(",")]
    elif isinstance(value, (list, tuple, set)):
        parsed = list(value)
    else:
        raise PolarisConfigError(f"Expected list-like value, got '{type(value).__name__}'.")

    normalized: list[str] = []
    for part in parsed:
        token = str(part).strip().lower()
        if token:
            normalized.append(token)
    # Preserve order while deduplicating.
    return list(dict.fromkeys(normalized))


def _axis_from_value(value: Any, *, allowed: tuple[str, ...], default: tuple[str, ...], label: str) -> list[str]:
    selected = _coerce_str_list(value) if value is not None else list(default)
    if not selected:
        selected = list(default)
    if selected == ["all"]:
        return list(allowed)

    invalid = [part for part in selected if part not in allowed]
    if invalid:
        raise PolarisConfigError(
            f"Invalid {label} value(s): {invalid}. Allowed values: {list(allowed)} or ['all']."
        )
    return selected


def _select_layers_from_axes(properties: list[str], statistics: list[str], depths: list[str]) -> list[str]:
    return [f"{prop}_{stat}_{depth}" for prop, stat, depth in product(properties, statistics, depths)]


def _layer_sort_key(layer_id: str) -> tuple[int, int, int]:
    prop, stat, depth = parse_polaris_layer_id(layer_id)
    return (
        POLARIS_PROPERTIES.index(prop),
        POLARIS_STATISTICS.index(stat),
        POLARIS_DEPTHS.index(depth),
    )


def _fetch_url_text(url: str, *, timeout_seconds: int) -> str:
    try:
        with urlopen(url, timeout=int(timeout_seconds)) as response:
            payload = response.read()
    except (HTTPError, URLError, OSError) as exc:
        raise RuntimeError(f"Failed to fetch POLARIS resource: {url}") from exc
    return payload.decode("utf-8", "replace")


def fetch_polaris_catalog_layer_ids(base_url: str = POLARIS_BASE_URL_DEFAULT, *, timeout_seconds: int = POLARIS_INDEX_TIMEOUT_SECONDS) -> list[str]:
    """Fetch available POLARIS VRT layer ids from the endpoint index."""
    normalized = _normalize_base_url(base_url)
    catalog_url = normalized + POLARIS_VRT_PATH
    html = _fetch_url_text(catalog_url, timeout_seconds=timeout_seconds)
    matches = _LAYER_HREF_RE.findall(html)
    layer_ids = [match[:-4].lower() for match in matches if match.lower().endswith(".vrt")]
    if not layer_ids:
        raise RuntimeError(f"POLARIS VRT index returned no layers: {catalog_url}")
    return sorted(set(layer_ids), key=_layer_sort_key)


def parse_polaris_layer_id(layer_id: str) -> tuple[str, str, str]:
    """Return (property, statistic, depth) from a layer id."""
    match = _LAYER_NAME_RE.match(str(layer_id).strip().lower())
    if match is None:
        raise PolarisConfigError(
            f"Invalid POLARIS layer id '{layer_id}'. Expected '<property>_<statistic>_<depth>'."
        )
    prop = match.group("property")
    stat = match.group("stat")
    depth = match.group("depth")
    if prop not in POLARIS_PROPERTIES:
        raise PolarisConfigError(f"Unsupported POLARIS property '{prop}'.")
    if stat not in POLARIS_STATISTICS:
        raise PolarisConfigError(f"Unsupported POLARIS statistic '{stat}'.")
    if depth not in POLARIS_DEPTHS:
        raise PolarisConfigError(f"Unsupported POLARIS depth '{depth}'.")
    return prop, stat, depth


def _build_layer_metadata(layer_id: str) -> dict[str, Any]:
    prop, stat, depth = parse_polaris_layer_id(layer_id)
    return {
        "layer_id": layer_id,
        "property": prop,
        "statistic": stat,
        "depth_cm": depth.replace("_", "-"),
        "units": POLARIS_PROPERTY_UNITS.get(prop, "N/A"),
        "is_log10": prop in POLARIS_LOG10_PROPERTIES,
    }


def _write_json(path: str, payload: Mapping[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)


def _write_markdown(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as stream:
        stream.write(text)


class Polaris(NoDbBase):
    """NoDb controller that retrieves and aligns POLARIS rasters for a run."""

    __name__: ClassVar[str] = "Polaris"
    filename: ClassVar[str] = "polaris.nodb"

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)
        with self.locked():
            os.makedirs(self.polaris_dir, exist_ok=True)
            self._last_layers = []
            self._last_fetch_utc = None
            self._last_manifest_relpath = "polaris/manifest.json"

    @property
    def polaris_dir(self) -> str:
        return _join(self.wd, "polaris")

    @property
    def source_vrt_dir(self) -> str:
        return _join(self.polaris_dir, "source_vrt")

    @property
    def manifest_path(self) -> str:
        return _join(self.polaris_dir, "manifest.json")

    @property
    def readme_path(self) -> str:
        return _join(self.polaris_dir, "README.md")

    def _config_axis(self, option: str, *, allowed: tuple[str, ...], default: tuple[str, ...], label: str) -> list[str]:
        raw = self.config_get_raw("polaris", option, None)
        return _axis_from_value(raw, allowed=allowed, default=default, label=label)

    def _config_layers(self) -> list[str]:
        raw = self.config_get_raw("polaris", "layers", None)
        layers = _coerce_str_list(raw)
        if layers == ["all"]:
            return layers
        for layer_id in layers:
            parse_polaris_layer_id(layer_id)
        return layers

    @property
    def base_url(self) -> str:
        raw = self.config_get_str("polaris", "base_url", POLARIS_BASE_URL_DEFAULT)
        return _normalize_base_url(raw)

    @property
    def request_timeout_seconds(self) -> int:
        value = self.config_get_int("polaris", "request_timeout_seconds", POLARIS_INDEX_TIMEOUT_SECONDS)
        if value is None or int(value) <= 0:
            return POLARIS_INDEX_TIMEOUT_SECONDS
        return int(value)

    @property
    def keep_source_intermediates(self) -> bool:
        raw = self.config_get_raw("polaris", "keep_source_intermediates", None)
        return _parse_bool(raw, default=False)

    @property
    def resample_method(self) -> str:
        value = self.config_get_str("polaris", "resample", "bilinear")
        method = str(value).strip().lower()
        if method not in POLARIS_RESAMPLE_METHODS:
            raise PolarisConfigError(
                f"Unsupported polaris.resample '{method}'. Allowed values: {sorted(POLARIS_RESAMPLE_METHODS)}."
            )
        return method

    def _runtime_request(self, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        request_payload: Mapping[str, Any] = payload or {}

        properties = _axis_from_value(
            request_payload.get("properties"),
            allowed=POLARIS_PROPERTIES,
            default=tuple(self._config_axis("properties", allowed=POLARIS_PROPERTIES, default=POLARIS_DEFAULT_PROPERTIES, label="properties")),
            label="properties",
        )
        statistics = _axis_from_value(
            request_payload.get("statistics"),
            allowed=POLARIS_STATISTICS,
            default=tuple(self._config_axis("statistics", allowed=POLARIS_STATISTICS, default=POLARIS_DEFAULT_STATISTICS, label="statistics")),
            label="statistics",
        )
        depths = _axis_from_value(
            request_payload.get("depths"),
            allowed=POLARIS_DEPTHS,
            default=tuple(self._config_axis("depths", allowed=POLARIS_DEPTHS, default=POLARIS_DEFAULT_DEPTHS, label="depths")),
            label="depths",
        )

        explicit_layers_raw = request_payload.get("layers", None)
        explicit_layers = _coerce_str_list(explicit_layers_raw) if explicit_layers_raw is not None else self._config_layers()
        if explicit_layers != ["all"]:
            for layer_id in explicit_layers:
                parse_polaris_layer_id(layer_id)

        keep_source_intermediates = _parse_bool(
            request_payload.get("keep_source_intermediates"),
            default=self.keep_source_intermediates,
        )
        force_refresh = _parse_bool(request_payload.get("force_refresh"), default=False)

        return {
            "properties": properties,
            "statistics": statistics,
            "depths": depths,
            "explicit_layers": explicit_layers,
            "keep_source_intermediates": keep_source_intermediates,
            "force_refresh": force_refresh,
            "base_url": self.base_url,
            "request_timeout_seconds": self.request_timeout_seconds,
            "resample": self.resample_method,
        }

    def _resolve_layers(self, request_d: Mapping[str, Any]) -> list[str]:
        catalog = fetch_polaris_catalog_layer_ids(
            request_d["base_url"],
            timeout_seconds=int(request_d["request_timeout_seconds"]),
        )
        explicit_layers = list(request_d["explicit_layers"])
        if explicit_layers == ["all"]:
            selected = catalog
        else:
            selected = _select_layers_from_axes(
                request_d["properties"],
                request_d["statistics"],
                request_d["depths"],
            )
            selected.extend(explicit_layers)

        deduped = list(dict.fromkeys(layer_id.lower() for layer_id in selected))
        missing = [layer_id for layer_id in deduped if layer_id not in catalog]
        if missing:
            raise PolarisConfigError(
                "Requested POLARIS layer(s) not available in remote catalog: "
                f"{missing[:10]}"
            )
        return sorted(deduped, key=_layer_sort_key)

    def _maybe_write_source_vrt(self, layer_id: str, source_vrt_url: str, *, keep_source_intermediates: bool, timeout_seconds: int) -> str:
        if not keep_source_intermediates:
            return source_vrt_url
        os.makedirs(self.source_vrt_dir, exist_ok=True)
        source_vrt_text = _fetch_url_text(source_vrt_url, timeout_seconds=timeout_seconds)
        source_vrt_path = _join(self.source_vrt_dir, f"{layer_id}.vrt")
        _write_markdown(source_vrt_path, source_vrt_text)
        return source_vrt_path

    def _write_polaris_readme(
        self,
        *,
        generated_at: str,
        request_d: Mapping[str, Any],
        records: list[dict[str, Any]],
    ) -> None:
        lines = [
            "# POLARIS Layers",
            "",
            "Run-scoped POLARIS raster retrieval and alignment metadata.",
            "",
            "## Attribution",
            "",
            "- Source dataset: POLARIS PROPERTIES v1.0 (Duke endpoint).",
            f"- Base URL: `{request_d['base_url']}`",
            f"- Source Readme: `{request_d['base_url']}{POLARIS_README_PATH}`",
            "",
            "## Retrieval Metadata",
            "",
            f"- Generated UTC: `{generated_at}`",
            f"- GeoTIFF output only: `true`",
            f"- Keep source intermediates: `{str(bool(request_d['keep_source_intermediates'])).lower()}`",
            f"- Resample method: `{request_d['resample']}`",
            "",
            "## Config Request",
            "",
            f"- Properties: `{request_d['properties']}`",
            f"- Statistics: `{request_d['statistics']}`",
            f"- Depths: `{request_d['depths']}`",
            f"- Explicit layers: `{request_d['explicit_layers']}`",
            "",
            "## Layer Inventory",
            "",
            "| Layer | Output | Status | Units | log10 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for record in records:
            lines.append(
                f"| `{record['layer_id']}` | `{record['output_relpath']}` | `{record['status']}` | "
                f"`{record['units']}` | `{str(bool(record['is_log10'])).lower()}` |"
            )
        lines.extend(
            [
                "",
                "## Notes",
                "",
                "- `hb`, `alpha`, `ksat`, and `om` are log10-space properties in POLARIS.",
                "- Aligned outputs are projected/resampled to match the run DEM grid.",
            ]
        )
        _write_markdown(self.readme_path, "\n".join(lines) + "\n")

    def acquire_and_align(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Fetch requested POLARIS layers and align them to the run raster grid."""
        func_name = inspect.currentframe().f_code.co_name
        self.logger.info("%s.%s(payload_keys=%s)", self.class_name, func_name, sorted((payload or {}).keys()))

        request_d = self._runtime_request(payload)
        layer_ids = self._resolve_layers(request_d)

        ron = Ron.getInstance(self.wd)
        dem_fn = ron.dem_fn
        if not _exists(dem_fn):
            raise FileNotFoundError(f"Cannot align POLARIS layers without run DEM: {dem_fn}")

        os.makedirs(self.polaris_dir, exist_ok=True)
        if request_d["keep_source_intermediates"]:
            os.makedirs(self.source_vrt_dir, exist_ok=True)

        records: list[dict[str, Any]] = []
        for layer_id in layer_ids:
            output_fn = _join(self.polaris_dir, f"{layer_id}.tif")
            output_relpath = os.path.relpath(output_fn, self.wd).replace(os.sep, "/")
            source_vrt_url = f"{request_d['base_url']}{POLARIS_VRT_PATH}{layer_id}.vrt"

            metadata = _build_layer_metadata(layer_id)
            metadata["source_vrt_url"] = source_vrt_url
            metadata["output_relpath"] = output_relpath

            if _exists(output_fn) and not request_d["force_refresh"]:
                metadata["status"] = "skipped_existing"
                records.append(metadata)
                continue

            source_ref = self._maybe_write_source_vrt(
                layer_id,
                source_vrt_url,
                keep_source_intermediates=bool(request_d["keep_source_intermediates"]),
                timeout_seconds=int(request_d["request_timeout_seconds"]),
            )
            raster_stacker(
                source_ref,
                dem_fn,
                output_fn,
                resample=request_d["resample"],
            )
            update_catalog_entry(self.wd, output_relpath)
            metadata["status"] = "aligned"
            records.append(metadata)

        generated_at = datetime.now(timezone.utc).isoformat()
        manifest = {
            "generated_at": generated_at,
            "base_url": request_d["base_url"],
            "readme_url": f"{request_d['base_url']}{POLARIS_README_PATH}",
            "request": {
                "properties": request_d["properties"],
                "statistics": request_d["statistics"],
                "depths": request_d["depths"],
                "explicit_layers": request_d["explicit_layers"],
                "keep_source_intermediates": request_d["keep_source_intermediates"],
                "force_refresh": request_d["force_refresh"],
                "resample": request_d["resample"],
            },
            "records": records,
        }
        _write_json(self.manifest_path, manifest)
        self._write_polaris_readme(generated_at=generated_at, request_d=request_d, records=records)

        with self.locked():
            self._last_layers = layer_ids
            self._last_fetch_utc = generated_at
            self._last_manifest_relpath = "polaris/manifest.json"

        prep = RedisPrep.tryGetInstance(self.wd)
        if prep is not None:
            prep.timestamp(TaskEnum.fetch_polaris)

        return {
            "generated_at": generated_at,
            "layers_requested": len(layer_ids),
            "layers_written": sum(1 for record in records if record["status"] == "aligned"),
            "layers_skipped": sum(1 for record in records if record["status"] == "skipped_existing"),
            "manifest_relpath": "polaris/manifest.json",
            "readme_relpath": "polaris/README.md",
        }
