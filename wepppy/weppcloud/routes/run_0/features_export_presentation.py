"""Build the Features Export catalog, selectors and profiles for the run page."""

import json
import logging
import pathlib

from wepppy.nodb.core import Ron
from wepppy.nodb.mods.features_export import (
    FeaturesExportProfileError,
    FeaturesExportServiceError,
    load_builtin_profiles,
    load_layer_catalog,
    resolve_published_profile_request,
)

from .features_export_columns import (
    _features_export_column_contract,
    _features_export_discover_layer_columns,
)


FEATURES_EXPORT_FAMILY_ORDER = [
    "watershed",
    "landuse",
    "soils",
    "wepp",
    "ash_watar",
    "swat_interchange",
    "agfields_spatial",
    "agfields_metrics",
    "omni_scenarios",
    "omni_contrasts",
]

FEATURES_EXPORT_FAMILY_LABELS = {
    "watershed": "Watershed",
    "landuse": "Landuse",
    "soils": "Soils",
    "wepp": "WEPP",
    "ash_watar": "Ash / WATAR",
    "omni_scenarios": "Omni Scenarios",
    "omni_contrasts": "Omni Contrasts",
    "swat_interchange": "SWAT Interchange",
    "agfields_spatial": "AgFields Spatial",
    "agfields_metrics": "AgFields Metrics",
}

FEATURES_EXPORT_UI_FAMILY_BY_RAW = {
    "wepp_summary": "wepp",
    "wepp_temporal": "wepp",
    "wepp_interchange": "wepp",
    "ash": "ash_watar",
    "ag_fields_spatial": "agfields_spatial",
    "ag_fields_metrics": "agfields_metrics",
}

def _format_features_export_family_label(family: str) -> str:
    if family in FEATURES_EXPORT_FAMILY_LABELS:
        return FEATURES_EXPORT_FAMILY_LABELS[family]
    tokens = [token for token in family.split("_") if token]
    if not tokens:
        return family
    return " ".join(token.capitalize() for token in tokens)


def _format_features_export_layer_label(layer_id: str, *, catalog_layer_raw: dict[str, object]) -> str:
    raw_label = catalog_layer_raw.get("label")
    if isinstance(raw_label, str) and raw_label.strip():
        return raw_label.strip()
    tail = layer_id.split(".")[-1].strip()
    if not tail:
        return layer_id
    return " ".join(token.capitalize() for token in tail.replace("_", " ").split())


def _features_export_ui_family(raw_family: str) -> str:
    return FEATURES_EXPORT_UI_FAMILY_BY_RAW.get(raw_family, raw_family)


def _features_export_selector_requirements(family: str) -> list[str]:
    requirements: list[str] = []
    if family == "omni_scenarios":
        requirements.append("omni_scenario")
    elif family == "omni_contrasts":
        requirements.append("omni_contrast")
    elif family == "swat_interchange":
        requirements.append("swat")
    if family == "agfields_metrics":
        requirements.append("agfields_auto_prep")
    return requirements


def _build_features_export_catalog_payload(
    wd: str | None = None,
    *,
    scenarios: list[dict] | None = None,
    contrasts: list[dict] | None = None,
    swat_catalog: dict | None = None,
) -> dict:
    scenarios = list(scenarios or [])
    contrasts = list(contrasts or [])
    swat_catalog = dict(swat_catalog or {})

    if wd and not scenarios and not contrasts and not swat_catalog:
        scenarios, contrasts = _discover_features_export_omni_selectors(wd)
        swat_catalog = _discover_features_export_swat_catalog(wd)

    try:
        catalog = load_layer_catalog()
    except Exception:  # broad-except: Render the existing catalog error payload on loader failure.
        logging.getLogger(__name__).exception("Unable to load the Features Export layer catalog")
        return {
            "metadata": {},
            "family_order": list(FEATURES_EXPORT_FAMILY_ORDER),
            "family_labels": dict(FEATURES_EXPORT_FAMILY_LABELS),
            "layers": [],
            "load_error": "Unable to load features export layer catalog.",
        }

    layers_payload: list[dict] = []
    for layer in catalog.layers:
        raw = dict(layer.raw)
        geometry = raw.get("geometry") if isinstance(raw.get("geometry"), dict) else {}
        geometry_type = geometry.get("type") if isinstance(geometry, dict) else None
        raw_family = layer.family
        family = _features_export_ui_family(raw_family)
        discovered_columns = _features_export_discover_layer_columns(
            wd=wd,
            raw_layer=raw,
            scenarios=scenarios,
            contrasts=contrasts,
            swat_catalog=swat_catalog,
        )
        columns, required_columns = _features_export_column_contract(
            raw,
            discovered_columns=discovered_columns,
        )
        layers_payload.append(
            {
                "layer_id": layer.layer_id,
                "label": _format_features_export_layer_label(
                    layer.layer_id,
                    catalog_layer_raw=raw,
                ),
                "family": family,
                "family_label": _format_features_export_family_label(family),
                "family_raw": raw_family,
                "scope_class": layer.scope_class,
                "geometry_type": str(geometry_type or "unknown"),
                "temporal_modes": list(layer.temporal_supported_modes),
                "selector_requirements": _features_export_selector_requirements(family),
                "columns": columns,
                "required_columns": sorted(required_columns),
                "raw": raw,
            }
        )

    metadata = {
        "catalog_version": catalog.metadata.catalog_version,
        "schema_version": catalog.metadata.schema_version,
        "updated_at_utc": catalog.metadata.updated_at_utc,
        "owner": catalog.metadata.owner,
        "status": catalog.metadata.status,
        "allowed_locator_kinds": list(catalog.metadata.allowed_locator_kinds),
        "temporal_modes": list(catalog.metadata.temporal_modes),
        "event_selectors": list(catalog.metadata.event_selectors),
        "path_template_vars": dict(catalog.metadata.path_template_vars),
    }

    return {
        "metadata": metadata,
        "family_order": list(FEATURES_EXPORT_FAMILY_ORDER),
        "family_labels": dict(FEATURES_EXPORT_FAMILY_LABELS),
        "layers": layers_payload,
        "load_error": None,
    }


def _discover_features_export_omni_selectors(wd: str) -> tuple[list[dict], list[dict]]:
    wd_path = pathlib.Path(wd)
    scenarios_root = wd_path / "_pups" / "omni" / "scenarios"
    contrasts_root = wd_path / "_pups" / "omni" / "contrasts"

    def _discover(root: pathlib.Path) -> list[dict]:
        if not root.is_dir():
            return []
        rows = []
        for entry in sorted(root.iterdir(), key=lambda item: item.name.lower()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            rows.append({"id": entry.name, "label": entry.name})
        return rows

    return _discover(scenarios_root), _discover(contrasts_root)


def _discover_features_export_swat_catalog(wd: str) -> dict:
    outputs_root = pathlib.Path(wd) / "swat" / "outputs"
    if not outputs_root.is_dir():
        return {"runs": [], "latest_run_id": None, "tables_by_run": {}, "all_tables": []}

    run_entries: list[tuple[str, pathlib.Path, int]] = []
    for entry in outputs_root.iterdir():
        if not entry.is_dir() or not entry.name.startswith("run_"):
            continue
        run_id = entry.name[len("run_") :].strip() or entry.name
        try:
            mtime_ns = entry.stat().st_mtime_ns
        except OSError:
            mtime_ns = 0
        run_entries.append((run_id, entry, mtime_ns))

    run_entries.sort(key=lambda row: (-row[2], row[0]))
    tables_by_run: dict[str, list[str]] = {}
    all_tables: set[str] = set()
    runs_payload: list[dict] = []

    for run_id, run_dir, _mtime_ns in run_entries:
        interchange_dir = run_dir / "interchange"
        tables: set[str] = set()
        if interchange_dir.is_dir():
            for path in interchange_dir.iterdir():
                if not path.is_file():
                    continue
                stem = path.stem.strip()
                if stem:
                    tables.add(stem)
        table_list = sorted(tables)
        tables_by_run[run_id] = table_list
        all_tables.update(table_list)
        runs_payload.append({"id": run_id, "label": run_id})

    latest_run_id = runs_payload[0]["id"] if runs_payload else None
    return {
        "runs": runs_payload,
        "latest_run_id": latest_run_id,
        "tables_by_run": tables_by_run,
        "all_tables": sorted(all_tables),
    }


def _features_export_layer_discovery_available(
    *,
    wd: pathlib.Path,
    layer,
    roads_scope_available: bool,
    scenarios: list[dict],
    contrasts: list[dict],
    swat_catalog: dict,
) -> bool:
    raw_layer = layer.raw if isinstance(layer.raw, dict) else {}
    ui_family = _features_export_ui_family(layer.family)

    if ui_family == "omni_scenarios":
        return bool(scenarios)
    if ui_family == "omni_contrasts":
        return bool(contrasts)
    if ui_family == "swat_interchange":
        return bool(swat_catalog.get("runs"))

    required_locators: list[dict] = []
    for source in raw_layer.get("sources", []):
        if not isinstance(source, dict):
            continue
        if bool(source.get("required", False)):
            locator = source.get("locator")
            if isinstance(locator, dict):
                required_locators.append(locator)
    for dependency in raw_layer.get("dependencies", []):
        if not isinstance(dependency, dict):
            continue
        if bool(dependency.get("required", False)):
            locator = dependency.get("locator")
            if isinstance(locator, dict):
                required_locators.append(locator)

    template_context = {
        "scope_root": "output",
        "scenario_id": scenarios[0]["id"] if scenarios else "",
        "contrast_id": contrasts[0]["id"] if contrasts else "",
        "swat_run_id": str(swat_catalog.get("latest_run_id") or "none"),
        "table_name": "",
        "crs_token": "WGS",
    }

    for locator in required_locators:
        kind = str(locator.get("kind") or "").strip()
        value = str(locator.get("value") or "").strip()
        if not kind or not value:
            continue
        if kind == "nodb_ref":
            continue
        if kind == "relpath":
            candidate = wd / value
        elif kind == "path_template":
            try:
                expanded = value.format_map(template_context)
            except KeyError:
                return False
            candidate = wd / expanded
        else:
            continue
        if not candidate.exists():
            return False

    return True


def _build_features_export_discovery_payload(
    wd: str,
    *,
    scenarios: list[dict],
    contrasts: list[dict],
    swat_catalog: dict,
) -> dict:
    wd_path = pathlib.Path(wd)
    roads_scope_available = (wd_path / "wepp" / "roads" / "output").is_dir()
    try:
        catalog = load_layer_catalog()
    except Exception:  # broad-except: Keep run-page discovery available when the catalog loader fails.
        logging.getLogger(__name__).exception("Unable to load the Features Export catalog for discovery")
        return {
            "roads_scope_available": roads_scope_available,
            "available_layer_ids": [],
            "available_families": [],
            "refresh_channel": "features_export",
        }

    available_layer_ids: list[str] = []
    available_families: set[str] = set()
    for layer in catalog.layers:
        if not _features_export_layer_discovery_available(
            wd=wd_path,
            layer=layer,
            roads_scope_available=roads_scope_available,
            scenarios=scenarios,
            contrasts=contrasts,
            swat_catalog=swat_catalog,
        ):
            continue
        available_layer_ids.append(layer.layer_id)
        available_families.add(_features_export_ui_family(layer.family))

    return {
        "roads_scope_available": roads_scope_available,
        "available_layer_ids": sorted(set(available_layer_ids)),
        "available_families": sorted(available_families),
        "refresh_channel": "features_export",
    }


def _resolve_features_export_utm_epsg(ron: Ron) -> int | None:
    map_obj = getattr(ron, "map", None)
    if map_obj is None:
        return None
    srid = getattr(map_obj, "srid", None)
    if isinstance(srid, int) and srid > 0:
        return srid
    if isinstance(srid, str):
        candidate = srid.strip()
        if candidate.isdigit():
            parsed = int(candidate)
            if parsed > 0:
                return parsed
    return None


def _features_export_unique_tokens(values: object) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _build_virtual_prep_wepp_gpkg_gdb_profile(
    *,
    roads_scope_available: bool,
    scenarios: list[dict],
    available_layer_ids: set[str],
) -> dict[str, object] | None:
    try:
        _canonical_profile, request_payload = resolve_published_profile_request("prep-wepp-gpkg-gdb")
    except FeaturesExportServiceError:
        return None

    if not isinstance(request_payload, dict):
        return None

    profile_request = json.loads(json.dumps(request_payload, sort_keys=True, separators=(",", ":")))
    if not isinstance(profile_request, dict):
        return None

    requested_scopes = set(_features_export_unique_tokens(profile_request.get("output_scopes")))
    if not requested_scopes:
        requested_scopes.add("baseline")
    if roads_scope_available:
        requested_scopes.add("roads")
    profile_request["output_scopes"] = [scope for scope in ("baseline", "roads") if scope in requested_scopes]

    scenario_ids = _features_export_unique_tokens(
        [entry.get("id") for entry in scenarios if isinstance(entry, dict)]
    )
    omni_scenarios_layer_id = "omni.scenarios.hillslopes"
    if scenario_ids and omni_scenarios_layer_id in available_layer_ids:
        layer_ids = _features_export_unique_tokens(profile_request.get("layers"))
        if omni_scenarios_layer_id not in layer_ids:
            layer_ids.append(omni_scenarios_layer_id)
        profile_request["layers"] = layer_ids
        profile_request["scenarios"] = scenario_ids
        profile_request.pop("contrast_ids", None)

    return profile_request


def _build_features_export_bootstrap_payload(wd: str, ron: Ron, resolved_utm_epsg: int | None) -> dict:
    scenarios, contrasts = _discover_features_export_omni_selectors(wd)
    swat_catalog = _discover_features_export_swat_catalog(wd)
    discovery_payload = _build_features_export_discovery_payload(
        wd,
        scenarios=scenarios,
        contrasts=contrasts,
        swat_catalog=swat_catalog,
    )
    preferred_swat_run_id = swat_catalog.get("latest_run_id") or "latest"
    try:
        profile_rows = list(load_builtin_profiles())
    except (FeaturesExportProfileError, OSError):
        profile_rows = []
    profile_requests: dict[str, dict[str, object]] = {}
    profile_buttons: list[dict[str, str]] = []
    for profile in profile_rows:
        key = str(profile.get("key") or "").strip()
        request_mapping = profile.get("request")
        if not key or not isinstance(request_mapping, dict):
            continue
        profile_requests[key] = dict(request_mapping)
        profile_buttons.append(
            {
                "key": key,
                "label": str(profile.get("label") or key),
            }
        )

    available_layer_ids = set(_features_export_unique_tokens(discovery_payload.get("available_layer_ids")))
    virtual_profile_key = "prep_wepp_gpkg_gdb"
    virtual_profile_request = _build_virtual_prep_wepp_gpkg_gdb_profile(
        roads_scope_available=bool(discovery_payload.get("roads_scope_available", True)),
        scenarios=scenarios,
        available_layer_ids=available_layer_ids,
    )
    if isinstance(virtual_profile_request, dict):
        profile_requests[virtual_profile_key] = virtual_profile_request
        profile_buttons.append(
            {
                "key": virtual_profile_key,
                "label": "Post Wepp (GPKG + GDB)",
            }
        )

    default_profile_key = "post_wepp"
    default_profile = profile_requests.get(default_profile_key, {})
    default_tabular = default_profile.get("tabular")
    if not isinstance(default_tabular, dict):
        default_tabular = {"concatenate_tables": False, "temporal_layout": "wide"}
    default_output_scopes = default_profile.get("output_scopes")
    if not isinstance(default_output_scopes, list) or not default_output_scopes:
        default_output_scopes = ["baseline"]

    return {
        "defaults": {
            "format": str(default_profile.get("format") or "geopackage"),
            "units": str(default_profile.get("units") or "project"),
            "crs": str(default_profile.get("crs") or "wgs"),
            "output_scopes": list(default_output_scopes),
            "tabular": dict(default_tabular),
        },
        "profiles": profile_requests,
        "profile_buttons": profile_buttons,
        "default_profile_key": default_profile_key,
        "resolved_utm_epsg": resolved_utm_epsg,
        "utm_available": resolved_utm_epsg is not None,
        "omni": {
            "scenarios": scenarios,
            "contrasts": contrasts,
        },
        "swat": {
            "preferred_run_id": preferred_swat_run_id,
            "runs": swat_catalog["runs"],
            "tables_by_run": swat_catalog["tables_by_run"],
            "all_tables": swat_catalog["all_tables"],
        },
        "discovery": discovery_payload,
        "runtime": {
            "readonly": bool(getattr(ron, "readonly", False)),
        },
    }
