"""Routes for wepp blueprint extracted from app.py."""

import wepppy
import os
import pathlib

from datetime import datetime
import re
import uuid
from wepppy.weppcloud.utils.runid import generate_runid
import json
import traceback
from urllib.parse import unquote, urlsplit
try:
    import pyarrow.lib as _pyarrow_lib
    import pyarrow.parquet as _pyarrow_parquet
except ModuleNotFoundError:  # pragma: no cover - runtime image normally includes pyarrow
    _pyarrow_lib = None
    _pyarrow_parquet = None

import redis
from itsdangerous import BadSignature, Signer

from .._common import *  # noqa: F401,F403
from flask import current_app, session
from werkzeug.exceptions import HTTPException

import wepppy
from wepppy.all_your_base import isint
from wepppy.config.secrets import get_secret
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.base import NoDbStaleWriteError, get_configs
from wepppy.nodb.core import (
    Climate,
    Landuse,
    LanduseCustomMappingError,
    Ron,
    Soils,
    Topaz,
    Watershed,
    Wepp,
)
from wepppy.nodb.unitizer import Unitizer
from wepppy.nodb.mods.observed import Observed
from wepppy.nodb.mods.rangeland_cover import RangelandCover
from wepppy.nodb.mods.rhem import Rhem
from wepppy.nodb.mods.treatments import Treatments
from wepppy.nodb.mods.ash_transport import Ash
from wepppy.nodb.mods.baer import Baer
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.debris_flow import DebrisFlow
from wepppy.nodb.mods.roads import Roads
from wepppy.nodb.mods.geneva import Geneva
from wepppy.nodb.mods.rusle import Rusle
from wepppy.nodb.mods.swat import Swat
from wepppy.nodb.mods.swat.print_prt import mask_to_tokens
from wepppy.nodb.mods.openet import OpenET_TS
from wepppy.nodb.mods.omni import Omni, OmniScenario
from wepppy.nodb.mods.features_export import (
    FeaturesExportProfileError,
    FeaturesExportServiceError,
    load_builtin_profiles,
    load_layer_catalog,
    resolve_published_profile_request,
)
import wepppy.nodb.mods.omni as omni_mod
from wepppy.nodb.core.climate import Climate
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.runtime_paths.parquet_sidecars import pick_existing_parquet_relpath
from wepppy.weppcloud.routes.nodb_api.landuse_bp import build_landuse_report_context
from wepppy.weppcloud.utils.cap_guard import requires_cap
from wepppy.weppcloud.utils import auth_tokens
from wepppy.weppcloud.utils.helpers import (
    get_wd, authorize, get_run_owners_lazy,
    is_omni_child_run,
    authorize_and_handle_with_exception_factory,
    handle_with_exception_factory
)
from wepppy.weppcloud.feature_registry.runtime import (
    build_header_mod_options,
    config_maturity_badge,
    config_registry_by_id,
    feature_maturity_badge,
    feature_registry_by_id,
    load_feature_registry,
    user_meets_min_role,
)
from wepppy.weppcloud.utils.browse_cookie import (
    browse_cookie_name,
    browse_cookie_path,
)


run_0_bp = Blueprint('run_0', __name__,
                     template_folder='templates')

SESSION_TOKEN_TTL_SECONDS = 4 * 24 * 60 * 60
SESSION_TOKEN_SCOPES = ["rq:status", "rq:enqueue", "rq:export"]
DEFAULT_BROWSE_JWT_COOKIE_NAME = "wepp_browse_jwt"
BROWSE_JWT_COOKIE_NAME_ENV = "WEPP_BROWSE_JWT_COOKIE_NAME"
DEFAULT_SITE_PREFIX = "/weppcloud"
_SYSTEM_LANDUSE_CUSTOM_MAPPING_RELPATH = "landuse/landuse_user_defined_mapping.json"

VAPID_PUBLIC_KEY = ''
_VAPID_PATH = pathlib.Path('/workdir/weppcloud2/microservices/wepppush/vapid.json')
if _VAPID_PATH.exists():
    with _VAPID_PATH.open() as fp:
        vapid = json.load(fp)
        VAPID_PUBLIC_KEY = vapid.get('publicKey', '')

# Preflight TOC Emoji Mapping
# Maps TOC anchor hrefs to TaskEnum members for emoji display.
# TaskEnum.emoji() is the single source of truth for all task emojis.
# See docs/ui-docs/control-ui-styling/preflight_behavior.md for architecture.
TOC_TASK_ANCHOR_TO_TASK = {
    '#map': TaskEnum.fetch_dem,
    '#disturbed-sbs': TaskEnum.init_sbs_map,
    '#channel-delineation': TaskEnum.build_channels,
    '#set-outlet': TaskEnum.set_outlet,
    '#subcatchments-delineation': TaskEnum.build_subcatchments,
    '#rangeland-cover': TaskEnum.build_rangeland_cover,
    '#landuse': TaskEnum.build_landuse,
    '#climate': TaskEnum.build_climate,
    '#rap-ts': TaskEnum.fetch_rap_ts,
    '#openet-ts': TaskEnum.fetch_openet_ts,
    '#soils': TaskEnum.build_soils,
    '#treatments': TaskEnum.build_treatments,
    '#wepp': TaskEnum.run_wepp_watershed,
    '#rusle': TaskEnum.build_rusle,
    '#ash': TaskEnum.run_watar,
    '#rhem': TaskEnum.run_rhem,
    '#omni-scenarios': TaskEnum.run_omni_scenarios,
    '#omni-contrasts': TaskEnum.run_omni_contrasts,
    '#observed': TaskEnum.run_observed,
    '#debris-flow': TaskEnum.run_debris,
    '#roads': TaskEnum.run_roads,
    '#geneva': TaskEnum.run_geneva,
    '#features-export': TaskEnum.run_features_export,
    '#dss-export': TaskEnum.dss_export,
    '#path-cost-effective': TaskEnum.run_path_cost_effective,
    '#team': TaskEnum.project_init,  # Using project init emoji as placeholder
}

TOC_TASK_EMOJI_MAP = {anchor: task.emoji() for anchor, task in TOC_TASK_ANCHOR_TO_TASK.items()}

if _pyarrow_lib is not None:
    _FEATURES_EXPORT_PARQUET_SCHEMA_EXCEPTIONS: tuple[type[Exception], ...] = (
        OSError,
        ValueError,
        _pyarrow_lib.ArrowException,
    )
else:  # pragma: no cover - pyarrow missing in non-runtime contexts
    _FEATURES_EXPORT_PARQUET_SCHEMA_EXCEPTIONS = (OSError, ValueError)


def _feature_spec(mod_name: str):
    return feature_registry_by_id().get(mod_name)


def _feature_role_display(min_role: str) -> str:
    display = {
        "user": "User",
        "poweruser": "PowerUser",
        "dev": "Dev",
        "admin": "Admin",
        "root": "Root",
    }
    return display.get(min_role, min_role)


def _feature_role_enabled(mod_name: str, *, playwright_load_all: bool) -> bool:
    if bool(playwright_load_all):
        return True
    spec = _feature_spec(mod_name)
    if spec is None:
        return False
    return user_meets_min_role(current_user, spec.min_role)


def _feature_role_restriction_message(mod_name: str) -> str:
    spec = _feature_spec(mod_name)
    if spec is None:
        return f"Unknown module '{mod_name}'."
    return f"{spec.label} is restricted to {_feature_role_display(spec.min_role)} users"


def _openet_admin_enabled(*, playwright_load_all: bool) -> bool:
    return _feature_role_enabled("openet_ts", playwright_load_all=playwright_load_all)


def _query_arg_is_true(name: str) -> bool:
    return str(request.args.get(name, "")).strip().lower() in {"true", "1", "yes"}


def _playwright_load_all_enabled() -> bool:
    if not _query_arg_is_true("playwright_load_all"):
        return False
    if not bool(current_app.config.get("TEST_SUPPORT_ENABLED")):
        return False
    return user_meets_min_role(current_user, "admin")


def _normalize_landuse_custom_mapping_relpath(value: object) -> str | None:
    token = str(value or "").strip()
    if not token:
        return None

    normalized = token.replace("\\", "/").lstrip("/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.strip().lower()
    return normalized or None


def _recover_stale_system_landuse_custom_mapping_reference(
    landuse: object,
    exc: Exception | None = None,
) -> bool:
    relpath = None
    details = getattr(exc, "details", None)
    if isinstance(details, dict):
        relpath = details.get("custom_mapping_relpath")
    if relpath in (None, ""):
        relpath = getattr(landuse, "custom_mapping_relpath", None)

    normalized_relpath = _normalize_landuse_custom_mapping_relpath(relpath)
    if normalized_relpath != _SYSTEM_LANDUSE_CUSTOM_MAPPING_RELPATH:
        return False

    raw_relpath = str(relpath).strip() if relpath not in (None, "") else _SYSTEM_LANDUSE_CUSTOM_MAPPING_RELPATH
    current_app.logger.warning(
        "Recovering stale system landuse custom mapping reference during run load: %s",
        raw_relpath,
    )

    clear_stale = getattr(landuse, "_clear_stale_system_custom_mapping_reference", None)
    if callable(clear_stale):
        try:
            return bool(clear_stale(raw_relpath))
        except Exception:
            current_app.logger.exception(
                "Failed stale system custom map cleanup via Landuse helper",
                extra={"custom_mapping_relpath": raw_relpath},
            )

    # Recovery boundary fallback: keep run pages loadable even if helper wiring
    # drifts on legacy instances.
    try:
        setattr(landuse, "_custom_mapping_relpath", None)
        islocked = getattr(landuse, "islocked", None)
        if callable(islocked) and islocked():
            return True
        locked = getattr(landuse, "locked", None)
        if callable(locked):
            try:
                with locked():
                    setattr(landuse, "_custom_mapping_relpath", None)
            except Exception:
                current_app.logger.exception(
                    "Failed to persist stale custom map cleanup during run load; "
                    "continuing with in-memory recovery",
                    extra={"custom_mapping_relpath": raw_relpath},
                )
        return True
    except Exception:
        current_app.logger.exception(
            "Failed stale custom map recovery during run load",
            extra={"custom_mapping_relpath": raw_relpath},
        )
        return False


def _call_landuse_with_stale_mapping_recovery(landuse: object, producer):
    try:
        return producer()
    except LanduseCustomMappingError as exc:
        if not _recover_stale_system_landuse_custom_mapping_reference(landuse, exc):
            raise
        return producer()
    except NoDbStaleWriteError:
        if not _recover_stale_system_landuse_custom_mapping_reference(landuse):
            raise
        return producer()

def _mod_ui_definitions() -> dict[str, dict[str, object]]:
    definitions: dict[str, dict[str, object]] = {}
    for entry in load_feature_registry():
        definitions[entry.id] = {
            "label": entry.nav_label,
            "section_id": entry.section_id,
            "section_class": entry.section_class,
            "template": entry.section_template,
        }
    return definitions


MOD_UI_DEFINITIONS = _mod_ui_definitions()


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


_FEATURES_EXPORT_INTERCHANGE_HEADING_RE = re.compile(r"^###\s+`([^`]+\.parquet)`\s*$")


def _infer_features_export_display_unit(column_id: str) -> str:
    token = str(column_id or "").strip().lower()
    if not token:
        return "non-unitized"

    suffix_units = [
        ("_mm", "mm"),
        ("_cm", "cm"),
        ("_m", "m"),
        ("_m2", "m2"),
        ("_m3", "m3"),
        ("_kg_ha", "kg/ha"),
        ("_kg_m2", "kg/m2"),
        ("_kg", "kg"),
        ("_ha", "ha"),
        ("_c", "C"),
        ("_cms", "cms"),
        ("_pct", "%"),
    ]
    for suffix, unit in suffix_units:
        if token.endswith(suffix):
            return unit

    if token.startswith("pct_") or token.endswith("_percent") or token.endswith("_percentage"):
        return "%"
    return "non-unitized"


def _features_export_column_label(column_id: str) -> str:
    token = str(column_id or "").strip()
    if not token:
        return ""
    if any(ch in token for ch in (" ", "-", "/", "%", ".")):
        return token
    return token.replace("_", " ")


def _features_export_column_match_key(column_id: str) -> str:
    token = str(column_id or "").strip().lower()
    if not token:
        return ""
    return re.sub(r"[^a-z0-9]+", "", token)


def _features_export_decode_metadata_value(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore").strip()
    if isinstance(value, str):
        return value.strip()
    return ""


def _features_export_metadata_lookup(metadata: dict, *keys: str) -> str:
    if not isinstance(metadata, dict):
        return ""
    for key in keys:
        byte_key = key.encode("utf-8")
        if byte_key in metadata:
            resolved = _features_export_decode_metadata_value(metadata.get(byte_key))
            if resolved:
                return resolved
        if key in metadata:
            resolved = _features_export_decode_metadata_value(metadata.get(key))
            if resolved:
                return resolved
    return ""


def _features_export_parse_markdown_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return []
    return [cell.strip() for cell in stripped.split("|")[1:-1]]


def _features_export_parse_interchange_readme(
    readme_path: pathlib.Path,
) -> dict[str, dict[str, dict[str, dict[str, str]]]]:
    if not readme_path.is_file():
        return {}

    try:
        lines = readme_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    parsed: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
    current_file = ""
    in_table = False
    for raw_line in lines:
        line = raw_line.strip()
        heading_match = _FEATURES_EXPORT_INTERCHANGE_HEADING_RE.match(line)
        if heading_match:
            current_file = heading_match.group(1).strip().lower()
            parsed.setdefault(current_file, {"exact": {}, "match": {}})
            in_table = False
            continue

        if not current_file:
            continue
        if line.lower() == "| column | type | units | description |":
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            in_table = False
            continue

        cells = _features_export_parse_markdown_table_row(line)
        if len(cells) < 4:
            continue
        if all(not cell or set(cell) <= {"-", ":"} for cell in cells):
            continue

        column_name = cells[0].strip()
        if not column_name or column_name.lower() == "column":
            continue

        doc: dict[str, str] = {"label": column_name}
        units = cells[2].strip()
        description = cells[3].strip()
        if units:
            doc["display_unit"] = units
        if description:
            doc["description"] = description

        file_docs = parsed[current_file]
        exact = file_docs.setdefault("exact", {})
        match = file_docs.setdefault("match", {})
        exact.setdefault(column_name, doc)
        match_key = _features_export_column_match_key(column_name)
        if match_key:
            match.setdefault(match_key, doc)
    return parsed


def _features_export_find_source_readme(source_path: pathlib.Path, wd_path: pathlib.Path) -> pathlib.Path | None:
    current = source_path.parent
    while True:
        candidate = current / "README.md"
        if candidate.is_file():
            return candidate
        if current == wd_path:
            return None
        if wd_path not in current.parents and current != wd_path:
            return None
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _features_export_lookup_readme_column_doc(
    readme_columns: dict[str, dict[str, dict[str, str]]] | None,
    column_id: str,
) -> dict[str, str]:
    if not isinstance(readme_columns, dict):
        return {}

    exact = readme_columns.get("exact")
    if isinstance(exact, dict):
        exact_doc = exact.get(column_id)
        if isinstance(exact_doc, dict):
            return dict(exact_doc)

    match = readme_columns.get("match")
    if isinstance(match, dict):
        key = _features_export_column_match_key(column_id)
        match_doc = match.get(key)
        if isinstance(match_doc, dict):
            return dict(match_doc)
    return {}


def _features_export_parquet_source_columns(
    path: pathlib.Path,
    *,
    readme_columns: dict[str, dict[str, dict[str, str]]] | None = None,
) -> list[dict]:
    if _pyarrow_parquet is None:
        return []

    try:
        schema = _pyarrow_parquet.read_schema(path)
    except _FEATURES_EXPORT_PARQUET_SCHEMA_EXCEPTIONS:
        return []

    columns: list[dict] = []
    for field in schema:
        column_id = str(field.name or "").strip()
        if not column_id:
            continue
        metadata = field.metadata if isinstance(field.metadata, dict) else {}
        readme_doc = _features_export_lookup_readme_column_doc(readme_columns, column_id)
        metadata_label = _features_export_metadata_lookup(metadata, "label", "display_name", "long_name")
        metadata_description = _features_export_metadata_lookup(metadata, "description", "desc")
        metadata_unit = _features_export_metadata_lookup(metadata, "units", "unit")
        readme_label = str(readme_doc.get("label") or "").strip()
        readme_description = str(readme_doc.get("description") or "").strip()
        readme_unit = str(readme_doc.get("display_unit") or "").strip()
        display_unit = metadata_unit or readme_unit or _infer_features_export_display_unit(column_id)
        columns.append(
            {
                "column_id": column_id,
                "label": metadata_label or readme_label or _features_export_column_label(column_id),
                "display_unit": display_unit,
                "description": metadata_description or readme_description,
                "default_selected": True,
            }
        )
    return columns


def _features_export_resolve_source_path(
    *,
    wd: pathlib.Path,
    source: dict,
    scenarios: list[dict],
    contrasts: list[dict],
    swat_catalog: dict,
) -> pathlib.Path | None:
    locator = source.get("locator") if isinstance(source.get("locator"), dict) else {}
    kind = str(locator.get("kind") or "").strip()
    value = str(locator.get("value") or "").strip()
    if not kind or not value:
        return None

    if kind == "relpath":
        return wd / value
    if kind != "path_template":
        return None

    latest_swat_run = str(swat_catalog.get("latest_run_id") or "latest").strip() or "latest"
    all_swat_tables = swat_catalog.get("all_tables", [])
    swat_table = ""
    if isinstance(all_swat_tables, list) and all_swat_tables:
        swat_table = str(all_swat_tables[0] or "").strip()

    context = {
        "scope_root": "output",
        "scenario_id": str(scenarios[0].get("id")) if scenarios else "",
        "contrast_id": str(contrasts[0].get("id")) if contrasts else "",
        "swat_run_id": latest_swat_run,
        "table_name": swat_table,
        "crs_token": "WGS",
    }
    try:
        resolved = value.format_map(context)
    except KeyError:
        return None
    return wd / resolved


def _features_export_discover_layer_columns(
    *,
    wd: str | None,
    raw_layer: dict,
    scenarios: list[dict],
    contrasts: list[dict],
    swat_catalog: dict,
) -> list[dict]:
    if not wd:
        return []

    wd_path = pathlib.Path(wd)
    if not wd_path.exists():
        return []

    discovered_by_id: dict[str, dict] = {}
    discovered_order: list[str] = []
    readme_cache: dict[pathlib.Path, dict[str, dict[str, dict[str, dict[str, str]]]]] = {}
    for source_entry in raw_layer.get("sources", []):
        if not isinstance(source_entry, dict):
            continue
        if str(source_entry.get("kind") or "").strip() != "parquet":
            continue
        source_path = _features_export_resolve_source_path(
            wd=wd_path,
            source=source_entry,
            scenarios=scenarios,
            contrasts=contrasts,
            swat_catalog=swat_catalog,
        )
        if source_path is None or not source_path.exists():
            continue
        readme_columns: dict[str, dict[str, dict[str, str]]] = {}
        readme_path = _features_export_find_source_readme(source_path, wd_path)
        if readme_path is not None:
            parsed_readme = readme_cache.get(readme_path)
            if parsed_readme is None:
                parsed_readme = _features_export_parse_interchange_readme(readme_path)
                readme_cache[readme_path] = parsed_readme
            readme_columns = parsed_readme.get(source_path.name.lower(), {})
        for column in _features_export_parquet_source_columns(source_path, readme_columns=readme_columns):
            column_id = str(column.get("column_id") or "").strip()
            if not column_id:
                continue
            existing = discovered_by_id.get(column_id)
            if existing is None:
                discovered_by_id[column_id] = dict(column)
                discovered_order.append(column_id)
                continue

            existing_description = str(existing.get("description") or "").strip()
            incoming_description = str(column.get("description") or "").strip()
            if not existing_description and incoming_description:
                existing["description"] = incoming_description

            existing_unit = str(existing.get("display_unit") or "").strip()
            incoming_unit = str(column.get("display_unit") or "").strip()
            if (
                (not existing_unit or existing_unit == "non-unitized")
                and incoming_unit
                and incoming_unit != "non-unitized"
            ):
                existing["display_unit"] = incoming_unit

            fallback_label = _features_export_column_label(column_id)
            existing_label = str(existing.get("label") or "").strip()
            incoming_label = str(column.get("label") or "").strip()
            if (
                (not existing_label or existing_label == fallback_label)
                and incoming_label
                and incoming_label != fallback_label
            ):
                existing["label"] = incoming_label
    return [discovered_by_id[column_id] for column_id in discovered_order]


def _features_export_column_contract(
    raw_layer: dict,
    *,
    discovered_columns: list[dict] | None = None,
) -> tuple[list[dict], set[str]]:
    join_contract = raw_layer.get("join") if isinstance(raw_layer.get("join"), dict) else {}
    geometry_contract = raw_layer.get("geometry") if isinstance(raw_layer.get("geometry"), dict) else {}
    measures = raw_layer.get("measures") if isinstance(raw_layer.get("measures"), dict) else {}
    explicit_columns = raw_layer.get("columns") if isinstance(raw_layer.get("columns"), list) else []
    columns = discovered_columns if discovered_columns else explicit_columns

    required_columns: set[str] = set()
    required_seen_keys: set[str] = set()

    def _add_required_column(candidate: str) -> None:
        token = str(candidate or "").strip()
        if not token:
            return
        dedupe_key = _features_export_column_match_key(token) or token.lower()
        if dedupe_key in required_seen_keys:
            return
        required_seen_keys.add(dedupe_key)
        required_columns.add(token)

    primary_key = str(join_contract.get("primary_key") or "").strip()
    if primary_key:
        _add_required_column(primary_key)
    for feature_key in geometry_contract.get("feature_id_keys", []):
        _add_required_column(str(feature_key or ""))

    normalized_columns: list[dict] = []
    seen_column_keys: set[str] = set()
    required_keys = {
        key
        for key in (_features_export_column_match_key(column_id) for column_id in required_columns)
        if key
    }
    for entry in columns:
        if not isinstance(entry, dict):
            continue
        column_id = str(entry.get("column_id") or "").strip()
        dedupe_key = _features_export_column_match_key(column_id) or column_id
        if not column_id or dedupe_key in seen_column_keys:
            continue
        seen_column_keys.add(dedupe_key)
        unit_meta = entry.get("unit") if isinstance(entry.get("unit"), dict) else {}
        is_required = column_id in required_columns or dedupe_key in required_keys
        display_unit = (
            str(entry.get("display_unit") or "").strip()
            or
            str(unit_meta.get("display_unit") or "").strip()
            or _infer_features_export_display_unit(column_id)
        )
        normalized_columns.append(
            {
                "column_id": column_id,
                "label": str(entry.get("label") or _features_export_column_label(column_id)),
                "description": str(entry.get("description") or "").strip(),
                "display_unit": display_unit,
                "required": is_required,
                "default_selected": bool(entry.get("default_selected", True) or is_required),
            }
        )

    if not normalized_columns:
        derived_columns: set[str] = set(required_columns)
        for measure in measures.get("optional", []):
            if isinstance(measure, str):
                token = measure.strip()
                if token:
                    derived_columns.add(token)
                continue
            if not isinstance(measure, dict):
                continue
            aliases = measure.get("key_aliases", [])
            if isinstance(aliases, list):
                for alias in aliases:
                    token = str(alias or "").strip()
                    if token:
                        derived_columns.add(token)
        for column_id in sorted(derived_columns):
            dedupe_key = _features_export_column_match_key(column_id) or column_id
            if dedupe_key in seen_column_keys:
                continue
            seen_column_keys.add(dedupe_key)
            is_required = column_id in required_columns or dedupe_key in required_keys
            normalized_columns.append(
                {
                    "column_id": column_id,
                    "label": _features_export_column_label(column_id),
                    "description": "",
                    "display_unit": _infer_features_export_display_unit(column_id),
                    "required": is_required,
                    "default_selected": is_required,
                }
            )

    for required_column in sorted(required_columns):
        dedupe_key = _features_export_column_match_key(required_column) or required_column
        if dedupe_key in seen_column_keys:
            continue
        seen_column_keys.add(dedupe_key)
        normalized_columns.append(
            {
                "column_id": required_column,
                "label": _features_export_column_label(required_column),
                "description": "",
                "display_unit": _infer_features_export_display_unit(required_column),
                "required": True,
                "default_selected": True,
            }
        )

    normalized_columns.sort(
        key=lambda item: (
            0 if item["required"] else 1,
            str(item["label"]).lower(),
            str(item["column_id"]).lower(),
        )
    )
    return normalized_columns, required_columns


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
    except Exception:
        # Boundary catch: keep runs page rendering resilient if catalog load fails.
        __import__("logging").getLogger(__name__).exception(
            "Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:features_export_catalog_load"
        )
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
    except Exception:
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

@run_0_bp.route('/sw.js')
def service_worker():
    from flask import make_response, send_from_directory
    response = make_response(send_from_directory('static/js', 'webpush_service_worker.js'))
    response.headers['Service-Worker-Allowed'] = '/'
    return response


# Redirect to the correct to the full run path
@run_0_bp.route('/runs/<string:runid>/')
@handle_with_exception_factory
def runs0_nocfg(runid):
    run_root = pathlib.Path(get_wd(runid)).resolve()
    pup_relpath = request.args.get('pup')
    active_root = run_root

    if pup_relpath:
        pups_root = (run_root / '_pups').resolve()
        candidate = (pups_root / pup_relpath).resolve()
        try:
            candidate.relative_to(pups_root)
        except ValueError:
            abort(404)

        if not candidate.is_dir():
            abort(404)

        active_root = candidate

    try:
        ron = Ron.getInstance(str(active_root))
    except FileNotFoundError:
        abort(404)

    target_args = {'runid': runid, 'config': ron.config_stem}
    if pup_relpath:
        target_args['pup'] = pup_relpath

    next_target = _sanitize_runs0_next_target(request.args.get("next"), runid, ron.config_stem)
    if next_target:
        response = redirect(next_target)
        if _set_run_session_jwt_cookie(
            response,
            runid=runid,
            config=ron.config_stem,
            require_root=_next_target_requires_root(next_target, runid, ron.config_stem),
        ):
            return response
        target_args['next'] = next_target
        return redirect(url_for_run('run_0.runs0', **target_args))

    return redirect(url_for_run('run_0.runs0', **target_args))


def _bool_env(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    token = raw.strip().lower()
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"0", "false", "no", "off"}:
        return False
    return default


def _normalize_site_prefix(prefix: str | None) -> str:
    if not prefix:
        return ""
    trimmed = prefix.strip()
    if not trimmed or trimmed == "/":
        return ""
    return "/" + trimmed.strip("/")


def _site_prefix() -> str:
    configured = current_app.config.get("SITE_PREFIX", DEFAULT_SITE_PREFIX)
    return _normalize_site_prefix(configured)


def _browse_jwt_cookie_name() -> str:
    value = (os.getenv(BROWSE_JWT_COOKIE_NAME_ENV) or "").strip()
    return value or DEFAULT_BROWSE_JWT_COOKIE_NAME


def _browse_jwt_cookie_key(runid: str, config: str) -> str:
    return browse_cookie_name(_browse_jwt_cookie_name(), runid, config)


def _browse_jwt_cookie_path(runid: str, config: str) -> str:
    return browse_cookie_path(_site_prefix(), runid, config)


def _batch_browse_compat_cookie_path() -> str:
    prefix = _site_prefix()
    return prefix or "/"


def _cookie_samesite() -> str:
    value = (os.getenv("WEPP_AUTH_SESSION_COOKIE_SAMESITE") or "lax").strip().lower()
    if value in {"lax", "strict", "none"}:
        return value
    return "lax"


def _request_is_secure() -> bool:
    forwarded_proto = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
    if forwarded_proto in {"https", "http"}:
        return forwarded_proto == "https"

    forwarded_ssl = (request.headers.get("X-Forwarded-Ssl") or "").strip().lower()
    if forwarded_ssl in {"on", "off"}:
        return forwarded_ssl == "on"

    return bool(request.is_secure)


def _session_cookie_secure() -> bool:
    default_secure = _request_is_secure()
    if os.getenv("WEPP_AUTH_SESSION_COOKIE_SECURE") is None:
        return default_secure
    return _bool_env("WEPP_AUTH_SESSION_COOKIE_SECURE", default=default_secure)


def _parse_user_id(raw: object) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def _normalize_role_names(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        candidates = [part.strip() for part in raw.split(",") if part.strip()]
    elif isinstance(raw, (list, tuple, set)):
        candidates = [str(item).strip() for item in raw if str(item).strip()]
    else:
        candidates = [str(raw).strip()] if str(raw).strip() else []

    names: list[str] = []
    seen: set[str] = set()
    for role in candidates:
        key = role.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(role)
    return names


def _session_identity_claims() -> tuple[int | None, list[str]]:
    user_id = _parse_user_id(session.get("_user_id") or session.get("user_id"))
    roles = _normalize_role_names(
        session.get("_roles_mask") or session.get("_roles") or session.get("roles")
    )
    return user_id, roles


def _owner_matches_user(owner: object, user_id: int) -> bool:
    owner_id = getattr(owner, "id", None)
    if owner_id is None:
        return False
    try:
        return int(owner_id) == int(user_id)
    except (TypeError, ValueError):
        return False


def _request_current_user_identity() -> tuple[int | None, set[str]]:
    try:
        user_obj = current_user
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:330", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return None, set()

    try:
        if not bool(getattr(user_obj, "is_authenticated", False)):
            return None, set()
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:336", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return None, set()

    user_id = _parse_user_id(getattr(user_obj, "id", None))
    if user_id is None:
        get_id = getattr(user_obj, "get_id", None)
        if callable(get_id):
            try:
                user_id = _parse_user_id(get_id())
            except Exception:
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:345", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                user_id = None

    elevated_roles: set[str] = set()
    has_role = getattr(user_obj, "has_role", None)
    if callable(has_role):
        for role_name in ("Admin", "Root"):
            try:
                if has_role(role_name):
                    elevated_roles.add(role_name.lower())
            except Exception:
                # Boundary catch: preserve contract behavior while logging unexpected failures.
                __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:355", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
                continue

    return user_id, elevated_roles


def _authorization_runid(runid: str) -> str:
    raw = str(runid or "")
    parts = raw.split(";;")
    if len(parts) >= 3 and parts[-2] in {"omni", "omni-contrast"} and parts[-1]:
        return ";;".join(parts[:-2])
    return raw


def _session_user_authorized_for_run(runid: str, user_id: int | None, roles: list[str]) -> bool:
    auth_runid = _authorization_runid(runid)
    wd = get_wd(auth_runid, prefer_active=False)
    if Ron.ispublic(wd):
        return True

    role_set = {role.lower() for role in roles}
    fallback_user_id: int | None = None
    fallback_roles: set[str] = set()
    if user_id is None or not {"admin", "root"} & role_set:
        fallback_user_id, fallback_roles = _request_current_user_identity()
        role_set.update(fallback_roles)

    if "admin" in role_set or "root" in role_set:
        return True

    owners = get_run_owners_lazy(auth_runid)
    if not owners:
        return not auth_runid.startswith("batch;;")

    effective_user_id = user_id if user_id is not None else fallback_user_id
    if effective_user_id is None:
        return False
    return any(_owner_matches_user(owner, effective_user_id) for owner in owners)


def _resolve_session_id_from_request() -> str | None:
    sid = getattr(session, "sid", None)
    if sid:
        return str(sid)

    cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "session")
    raw_cookie = request.cookies.get(cookie_name)
    if not raw_cookie:
        return None

    use_signer = current_app.config.get("SESSION_USE_SIGNER", True)
    if not use_signer:
        return str(raw_cookie)

    secret = current_app.config.get("SECRET_KEY") or get_secret("SECRET_KEY")
    if not secret:
        return None

    signer = Signer(secret, salt="flask-session", key_derivation="hmac")
    try:
        return signer.unsign(raw_cookie).decode("utf-8")
    except BadSignature:
        return None


def _store_session_marker(runid: str, session_id: str) -> None:
    key = f"auth:session:run:{runid}:{session_id}"
    conn_kwargs = redis_connection_kwargs(RedisDB.SESSION)
    redis_conn = redis.Redis(**conn_kwargs)
    try:
        redis_conn.setex(key, SESSION_TOKEN_TTL_SECONDS, "1")
    finally:
        close_fn = getattr(redis_conn, "close", None)
        if callable(close_fn):
            close_fn()


def _set_run_session_jwt_cookie(response, *, runid: str, config: str, require_root: bool = False) -> bool:
    user_id, roles = _session_identity_claims()
    fallback_user_id: int | None = None
    fallback_roles: set[str] = set()
    role_set = {role.lower() for role in roles}
    if user_id is None or not {"admin", "root"} & role_set:
        fallback_user_id, fallback_roles = _request_current_user_identity()
        if user_id is None and fallback_user_id is not None:
            user_id = fallback_user_id
        if fallback_roles:
            roles = _normalize_role_names([*roles, *sorted(fallback_roles)])
            role_set = {role.lower() for role in roles}

    if require_root and "root" not in role_set:
        return False

    session_id = _resolve_session_id_from_request()
    if not session_id:
        if _session_user_authorized_for_run(runid, user_id, roles):
            session_id = uuid.uuid4().hex
        else:
            return False

    if not _session_user_authorized_for_run(runid, user_id, roles):
        return False

    extra_claims: dict[str, object] = {
        "token_class": "session",
        "session_id": session_id,
        "runid": runid,
        "config": config,
        "jti": uuid.uuid4().hex,
    }
    if user_id is not None:
        extra_claims["user_id"] = user_id
    if roles:
        extra_claims["roles"] = roles

    token_payload = auth_tokens.issue_token(
        session_id,
        scopes=SESSION_TOKEN_SCOPES,
        audience="rq-engine",
        expires_in=SESSION_TOKEN_TTL_SECONDS,
        extra_claims=extra_claims,
    )
    token_value = token_payload.get("token")
    if not isinstance(token_value, str) or not token_value:
        return False

    _store_session_marker(runid, session_id)
    response.set_cookie(
        key=_browse_jwt_cookie_key(runid, config),
        value=token_value,
        max_age=SESSION_TOKEN_TTL_SECONDS,
        httponly=True,
        secure=_session_cookie_secure(),
        samesite=_cookie_samesite(),
        path=_browse_jwt_cookie_path(runid, config),
    )
    if str(runid).startswith("batch;;"):
        response.set_cookie(
            key=_browse_jwt_cookie_name(),
            value=token_value,
            max_age=SESSION_TOKEN_TTL_SECONDS,
            httponly=True,
            secure=_session_cookie_secure(),
            samesite=_cookie_samesite(),
            path=_batch_browse_compat_cookie_path(),
        )
    return True


def _next_target_requires_root(next_target: str, runid: str, config: str) -> bool:
    try:
        parsed = urlsplit(str(next_target))
    except ValueError:
        # Malformed next targets should not escalate cookie claims.
        return False

    path = parsed.path or ""
    expected_prefix = f"{_site_prefix()}/runs/{runid}/{config}/"
    if not path.startswith(expected_prefix):
        return False

    relpath = path[len(expected_prefix):].lstrip("/")
    if not relpath:
        return False

    route, _, subpath = relpath.partition("/")
    if route not in {"browse", "download", "gdalinfo", "dtale", "files", "schema"}:
        return False

    from wepppy.microservices.browse.auth import is_root_only_path

    return is_root_only_path(subpath)


def _sanitize_runs0_next_target(next_value: str | None, runid: str, config: str) -> str | None:
    if not next_value:
        return None

    try:
        parsed = urlsplit(str(next_value))
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:486", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return None

    if parsed.scheme or parsed.netloc:
        return None

    path = parsed.path or ""
    if not path:
        return None
    if path.startswith("//"):
        return None
    if not path.startswith("/"):
        path = "/" + path.lstrip("/")
    if _path_has_unsafe_segments(path):
        return None

    run_base = f"{_site_prefix()}/runs/{runid}/"
    if not path.startswith(run_base):
        return None

    remainder = path[len(run_base):]
    if not remainder or remainder == config:
        normalized_path = f"{run_base}{config}/"
    elif remainder.startswith(f"{config}/"):
        normalized_path = f"{run_base}{remainder}"
    else:
        normalized_path = f"{run_base}{config}/{remainder.lstrip('/')}"

    expected_prefix = f"{run_base}{config}/"
    if not normalized_path.startswith(expected_prefix):
        return None

    if parsed.query:
        normalized_path = f"{normalized_path}?{parsed.query}"
    if parsed.fragment:
        normalized_path = f"{normalized_path}#{parsed.fragment}"
    return normalized_path


def _path_has_unsafe_segments(path: str) -> bool:
    normalized = path.replace("\\", "/")
    for segment in normalized.split("/"):
        if not segment:
            continue
        decoded = _fully_unquote_segment(segment).strip()
        if decoded in {".", ".."}:
            return True
        if "/" in decoded or "\\" in decoded:
            return True
    return False


def _fully_unquote_segment(segment: str, *, max_rounds: int = 8) -> str:
    decoded = str(segment)
    for _ in range(max_rounds):
        candidate = unquote(decoded)
        if candidate == decoded:
            break
        decoded = candidate
    return decoded

def _log_access(wd, current_user, ip):
    assert _exists(wd)

    fn, runid = _split(wd.rstrip('/'))
    fn = _join(fn, '.{}'.format(runid))
    with open(fn, 'a') as fp:
        email = getattr(current_user, 'email', '<anonymous>')
        fp.write('{},{},{}\n'.format(email, ip, datetime.now()))


def _build_runs0_context(runid, config, playwright_load_all):
    global VAPID_PUBLIC_KEY
    from wepppy.nodb.mods.revegetation import Revegetation
    from wepppy.wepp.soils import soilsdb
    from wepppy.wepp import management
    from wepp_runner.wepp_runner import get_linux_wepp_bin_opts
    from wepppy.wepp.management.managements import landuse_management_mapping_options
    from wepppy.weppcloud.app import db, Run

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    base_wd = str(ctx.run_root)
    ron = Ron.getInstance(wd)
    map_object_payload = ron.map.to_payload() if ron.map is not None else None
    map_object_json = json.dumps(map_object_payload, indent=2) if map_object_payload else ""

    # check config from url matches config from Ron
    if config != ron.config_stem:
        target_args = {'runid': runid, 'config': ron.config_stem}
        if ctx.pup_relpath:
            target_args['pup'] = ctx.pup_relpath
        return {'redirect': url_for_run('run_0.runs0', **target_args)}

    if ctx.pup_root and not ron.readonly:
        try:
            ron.readonly = True
        except Exception as exc:
            current_app.logger.warning('Failed to mark pup project as readonly: %s', exc)

    landuse = Landuse.load_detached(wd, allow_nonexistent=True)
    if landuse is None:
        landuse = Landuse.getInstance(wd)
    soils = Soils.getInstance(wd)
    climate = Climate.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    watershed = Watershed.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)
    site_prefix = current_app.config['SITE_PREFIX']

    # Browse links should follow truth-on-disk: prefer canonical WD-level sidecars,
    # fall back to legacy in-tree parquets when present, otherwise hide.
    browse_watershed_hillslopes_parquet = pick_existing_parquet_relpath(
        wd, "watershed/hillslopes.parquet"
    )
    browse_watershed_channels_parquet = pick_existing_parquet_relpath(
        wd, "watershed/channels.parquet"
    )
    browse_landuse_parquet = pick_existing_parquet_relpath(wd, "landuse/landuse.parquet")
    browse_soils_parquet = pick_existing_parquet_relpath(wd, "soils/soils.parquet")

    if watershed.delineation_backend_is_topaz:
        topaz = Topaz.getInstance(wd)
    else:
        topaz = None

    mods_list = ron.mods or []
    openet_role_enabled = _feature_role_enabled(
        "openet_ts",
        playwright_load_all=playwright_load_all,
    )
    show_openet_ts = openet_role_enabled and ('openet_ts' in mods_list or playwright_load_all)

    observed = Observed.tryGetInstance(wd)
    rangeland_cover = RangelandCover.tryGetInstance(wd)
    rhem = Rhem.tryGetInstance(wd)
    openet_ts = OpenET_TS.tryGetInstance(wd) if show_openet_ts else None
    disturbed = Disturbed.tryGetInstance(wd)
    baer = Baer.tryGetInstance(wd) if 'baer' in ron.mods else None
    ash = Ash.tryGetInstance(wd)
    skid_trails = wepppy.nodb.mods.SkidTrails.tryGetInstance(wd)
    reveg = Revegetation.tryGetInstance(wd)
    omni = Omni.tryGetInstance(wd)
    treatments = Treatments.tryGetInstance(wd)
    redis_prep = RedisPrep.tryGetInstance(wd)
    debris_flow = DebrisFlow.tryGetInstance(wd) if 'debris_flow' in ron.mods else None
    roads = Roads.tryGetInstance(wd) if 'roads' in mods_list else None
    geneva = Geneva.tryGetInstance(wd) if 'geneva' in mods_list else None
    rusle = Rusle.tryGetInstance(wd) if 'rusle' in mods_list else None
    swat = Swat.tryGetInstance(wd) if 'swat' in ron.mods else None
    swat_print_prt_rows = []
    swat_print_prt_meta = {}
    if swat is not None and swat.print_prt is not None:
        swat_print_prt_meta = {
            "nyskip": int(swat.print_prt.nyskip),
            "day_start": int(swat.print_prt.day_start),
            "yrc_start": int(swat.print_prt.yrc_start),
            "day_end": int(swat.print_prt.day_end),
            "yrc_end": int(swat.print_prt.yrc_end),
            "interval": int(swat.print_prt.interval),
        }
        try:
            rows = swat.print_prt.objects.iter_rows(swat.print_prt.object_order)
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:637", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            rows = swat.print_prt.objects.iter_rows()
        for object_name, mask in rows:
            daily, monthly, yearly, avann = mask_to_tokens(int(mask))
            swat_print_prt_rows.append(
                {
                    "object": object_name,
                    "daily": daily == "y",
                    "monthly": monthly == "y",
                    "yearly": yearly == "y",
                    "avann": avann == "y",
                }
            )

    if redis_prep is not None:
        rq_job_ids = redis_prep.get_rq_job_ids()
    else:
        rq_job_ids = {}

    landuseoptions = _call_landuse_with_stale_mapping_recovery(
        landuse,
        lambda: landuse.landuseoptions,
    )
    landuse_report_context = _call_landuse_with_stale_mapping_recovery(
        landuse,
        lambda: build_landuse_report_context(landuse),
    )
    soildboptions = soilsdb.load_db()

    critical_shear_options = management.load_channel_d50_cs()
    reveg_cover_transform_options = [
        ("", "Observed"),
        ("20-yr_Recovery.csv", "20-Year Recovery"),
        ("20-yr_PartialRecovery.csv", "20-Year Partial Recovery"),
        ("user_cover_transform", "User-Defined Transform")
    ]
    wepp_bin_options = [(opt, opt) for opt in get_linux_wepp_bin_opts()]

    _log_access(base_wd, current_user, request.remote_addr)
    timestamp = datetime.now()
    run_record = Run.query.filter(Run.runid == runid).first()
    if run_record is not None:
        run_record.last_accessed = timestamp
    else:
        Run.query.filter_by(runid=runid).update({'last_accessed': timestamp})
    db.session.commit()

    show_rap_ts = 'rap_ts' in mods_list or playwright_load_all
    show_treatments = 'treatments' in mods_list or playwright_load_all
    show_ash = (('ash' in mods_list) and (ash is not None)) or playwright_load_all
    is_omni_child = is_omni_child_run(runid, wd=wd, pup_relpath=ctx.pup_relpath)
    show_omni = (
        (('omni' in mods_list) or playwright_load_all)
        and ((omni is not None) or playwright_load_all)
        and not is_omni_child
    )
    show_omni_contrasts = show_omni and _feature_role_enabled(
        "omni_contrasts",
        playwright_load_all=playwright_load_all,
    )
    show_observed = (observed is not None) or playwright_load_all
    allow_debris_flow = (
        _feature_role_enabled("debris_flow", playwright_load_all=playwright_load_all)
    )
    show_debris_flow = allow_debris_flow and (debris_flow is not None or playwright_load_all)
    show_roads = ('roads' in mods_list and roads is not None) or playwright_load_all
    show_geneva = ('geneva' in mods_list and geneva is not None) or playwright_load_all
    show_features_export = 'features_export' in mods_list or playwright_load_all
    show_dss_export = 'dss_export' in mods_list or playwright_load_all
    show_path_ce = 'path_ce' in mods_list or playwright_load_all
    rusle_backend_supported = bool(getattr(watershed, "delineation_backend_is_wbt", False))
    show_rusle = (
        (('rusle' in mods_list) or playwright_load_all)
        and (('disturbed' in mods_list) or playwright_load_all)
        and (rusle_backend_supported or playwright_load_all)
        and ((rusle is not None) or playwright_load_all)
    )
    rusle_rap_year_options = rusle.available_rap_years() if rusle is not None else []

    bootstrap_admin_disabled = bool(getattr(run_record, "bootstrap_disabled", False)) if run_record else False
    bootstrap_is_anonymous = not bool(getattr(run_record, "owner_id", None)) if run_record else True
    
    omni_has_ran_scenarios = bool(omni and omni.has_ran_scenarios)
    omni_has_ran_contrasts = bool(omni and omni.has_ran_contrasts)

    feature_registry_entries = load_feature_registry()
    mod_visibility = {entry.id: False for entry in feature_registry_entries}
    mod_visibility.update(
        {
            'rap_ts': show_rap_ts,
            'openet_ts': show_openet_ts,
            'treatments': show_treatments,
            'ash': show_ash,
            'omni': show_omni,
            'omni_contrasts': show_omni_contrasts,
            'observed': show_observed,
            'debris_flow': show_debris_flow,
            'roads': show_roads,
            'geneva': show_geneva,
            'features_export': show_features_export,
            'dss_export': show_dss_export,
            'path_ce': show_path_ce,
            'rusle': show_rusle,
        }
    )
    header_mod_options = build_header_mod_options(
        active_mods=set(mods_list),
        user=current_user,
        is_wbt=rusle_backend_supported,
        include_all=bool(playwright_load_all),
    )
    maturity_definition_href = (
        url_for('usersum.view_markdown', category='weppcloud', filename='user-guide.md')
        + '#feature-maturity-labels'
    )
    feature_maturity_labels = {
        entry.id: feature_maturity_badge(entry)
        for entry in feature_registry_entries
    }
    run_config_spec = config_registry_by_id().get(config)
    run_config_maturity_label = (
        config_maturity_badge(run_config_spec) if run_config_spec is not None else None
    )

    features_export_catalog_payload = {}
    features_export_bootstrap_payload = {}
    features_export_utm_epsg = None
    if show_features_export:
        features_export_utm_epsg = _resolve_features_export_utm_epsg(ron)
        features_export_catalog_payload = _build_features_export_catalog_payload(wd)
        features_export_bootstrap_payload = _build_features_export_bootstrap_payload(
            wd,
            ron,
            features_export_utm_epsg,
        )

    context = dict(
        user=current_user,
        site_prefix=site_prefix,
        playwright_load_all=playwright_load_all,
        topaz=topaz,
        soils=soils,
        ron=ron,
        landuse=landuse,
        climate=climate,
        wepp=wepp,
        wepp_bin_options=wepp_bin_options,
        rhem=rhem,
        openet_ts=openet_ts,
        disturbed=disturbed,
        baer=baer,
        ash=ash,
        skid_trails=skid_trails,
        reveg=reveg,
        watershed=watershed,
        unitizer_nodb=unitizer,
        observed=observed,
        rangeland_cover=rangeland_cover,
        omni=omni,
        OmniScenario=OmniScenario,
        treatments=treatments,
        debris_flow=debris_flow,
        roads=roads,
        geneva=geneva,
        rusle=rusle,
        rusle_rap_year_options=rusle_rap_year_options,
        swat=swat,
        swat_print_prt_rows=swat_print_prt_rows,
        swat_print_prt_meta=swat_print_prt_meta,
        rq_job_ids=rq_job_ids,
        landuseoptions=landuseoptions,
        landcover_datasets=landuse.landcover_datasets,
        landuse_report_rows=landuse_report_context['report_rows'],
        landuse_dataset_options=landuse_report_context['dataset_options'],
        landuse_coverage_percentages=landuse_report_context['coverage_percentages'],
        landuse_management_mapping_options=landuse_management_mapping_options,
        soildboptions=soildboptions,
        critical_shear_options=critical_shear_options,
        reveg_cover_transform_options=reveg_cover_transform_options,
        climate_catalog=climate.catalog_datasets_payload(include_hidden=True),
        precisions=wepppy.nodb.unitizer.precisions,
        run_id=runid,
        runid=runid,
        config=config,
        map_object_payload=map_object_payload,
        map_object_json=map_object_json,
        toc_task_emojis=TOC_TASK_EMOJI_MAP,
        pup_relpath=ctx.pup_relpath,
        VAPID_PUBLIC_KEY=VAPID_PUBLIC_KEY,
        show_rap_ts=show_rap_ts,
        show_openet_ts=show_openet_ts,
        openet_admin_enabled=openet_role_enabled,
        show_treatments=show_treatments,
        show_ash=show_ash,
        show_omni=show_omni,
        show_omni_contrasts=show_omni_contrasts,
        show_observed=show_observed,
        show_debris_flow=show_debris_flow,
        allow_debris_flow=allow_debris_flow,
        show_roads=show_roads,
        show_geneva=show_geneva,
        show_features_export=show_features_export,
        show_dss_export=show_dss_export,
        show_path_ce=show_path_ce,
        show_rusle=show_rusle,
        rusle_backend_supported=rusle_backend_supported,
        maturity_definition_href=maturity_definition_href,
        feature_maturity_labels=feature_maturity_labels,
        run_config_maturity_label=run_config_maturity_label,
        run_config_maturity_href=maturity_definition_href,
        header_mod_options=header_mod_options,
        omni_user_defined_contrast_limit=int(getattr(omni_mod, "USER_DEFINED_CONTRAST_LIMIT", 200)),
        is_omni_child=is_omni_child,
        omni_has_ran_scenarios=omni_has_ran_scenarios,
        omni_has_ran_contrasts=omni_has_ran_contrasts,
        mod_visibility=mod_visibility,
        bootstrap_admin_disabled=bootstrap_admin_disabled,
        bootstrap_is_anonymous=bootstrap_is_anonymous,
        browse_watershed_hillslopes_parquet=browse_watershed_hillslopes_parquet,
        browse_watershed_channels_parquet=browse_watershed_channels_parquet,
        browse_landuse_parquet=browse_landuse_parquet,
        browse_soils_parquet=browse_soils_parquet,
        features_export_catalog_payload=features_export_catalog_payload,
        features_export_bootstrap_payload=features_export_bootstrap_payload,
        features_export_utm_epsg=features_export_utm_epsg,
        features_export_submit_url=f"/rq-engine/api/runs/{runid}/{config}/export/features",
        features_export_profile_resolve_url=(
            f"/rq-engine/api/runs/{runid}/{config}/export/features/profile/resolve"
        ),
        features_export_download_url_template=(
            f"{current_app.config.get('SITE_PREFIX', '').rstrip('/')}/runs/{runid}/{config}/download/__ARTIFACT_RELPATH__"
        ),
    )
    return context

@run_0_bp.route('/runs/<string:runid>/<config>/')
@requires_cap(gate_reason="Complete verification to view this run.")
def runs0(runid, config):
    assert config is not None

    try:
        authorize(runid, config)

        # Check if migrations are needed (unless skip_migration_check is set)
        skip_migration_check = _query_arg_is_true("skip_migration_check")
        playwright_load_all = _playwright_load_all_enabled()

        if not skip_migration_check and not playwright_load_all:
            wd = get_wd(runid)
            if _exists(wd):
                from wepppy.tools.migrations.runner import check_migrations_needed

                migration_status = check_migrations_needed(wd)
                gated_migrations = {
                    "nodb_version",
                    "watersheds",
                    "landuse_parquet",
                    "soils_parquet",
                }
                needs_migration = any(
                    entry.get("name") in gated_migrations and entry.get("would_apply")
                    for entry in migration_status.get("migrations", [])
                )
                if needs_migration:
                    # Redirect to migration page
                    return redirect(url_for_run('run_0.migration_page', runid=runid, config=config))

        context = _build_runs0_context(runid, config, playwright_load_all)
        if 'redirect' in context:
            return redirect(context['redirect'])
        return render_template('runs0_pure.htm', **context)
    except HTTPException:
        raise
    except Exception as exc:
        stacktrace = traceback.format_exc()
        # Reuse exception_factory for logging + run exception log side effects.
        exception_factory(msg=exc, stacktrace=stacktrace, runid=runid, details=stacktrace)
        return _render_run_internal_error_page(runid, config, stacktrace)


@run_0_bp.route('/runs/<string:runid>/<config>/migrate')
@authorize_and_handle_with_exception_factory
def migration_page(runid, config):
    """Display migration status page for a run that needs migrations."""
    from wepppy.tools.migrations.runner import check_migrations_needed
    from wepppy.weppcloud.app import get_run_owners
    
    wd = get_wd(runid)
    if not _exists(wd):
        abort(404)
    
    ron = Ron.getInstance(wd)
    migration_status = check_migrations_needed(wd)
    if not migration_status.get("needs_migration"):
        return redirect(url_for_run('run_0.runs0', runid=runid, config=config))
    
    # Check if user can migrate (owner or admin)
    is_owner = False
    is_admin = False
    try:
        owners = get_run_owners(runid)
        is_owner = current_user in owners if owners else True
        is_admin = current_user.has_role('Admin') if hasattr(current_user, 'has_role') else False
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:857", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        is_owner = True  # Allow if we can't determine ownership
    
    can_migrate = is_owner or is_admin
    is_readonly = ron.readonly
    
    context = {
        'runid': runid,
        'config': config,
        'ron': ron,
        'migration_status': migration_status,
        'can_migrate': can_migrate,
        'is_readonly': is_readonly,
        'is_owner': is_owner,
        'is_admin': is_admin,
        'user': current_user,
        'url_for_run': url_for_run,
    }
    return render_template('run_0/rq-migration-status.htm', **context)


@run_0_bp.route('/runs/<string:runid>/<config>/view/mod/<string:mod_name>')
@authorize_and_handle_with_exception_factory
def view_mod_section(runid, config, mod_name):
    mod_info = MOD_UI_DEFINITIONS.get(mod_name)
    if not mod_info:
        return error_factory('Unknown module')
    if not _feature_role_enabled(mod_name, playwright_load_all=False):
        return error_factory(_feature_role_restriction_message(mod_name))

    context = _build_runs0_context(runid, config, playwright_load_all=False)
    if 'redirect' in context:
        return redirect(context['redirect'])

    if not context['mod_visibility'].get(mod_name):
        return error_factory('Module is not enabled for this run')

    section_inner = render_template(mod_info['template'], **context)
    section_html = render_template(
        'run_0/mod_section_wrapper.htm',
        section_id=mod_info['section_id'],
        section_class=mod_info.get('section_class', 'wc-stack'),
        section_html=section_inner,
    )
    return success_factory({
        'mod': mod_name,
        'section_id': mod_info['section_id'],
        'html': section_html,
    })

@run_0_bp.route('/create', strict_slashes=False)
@login_required
@handle_with_exception_factory
def create_index():
    try:
        rq_engine_token = _issue_rq_engine_token()
    except auth_tokens.JWTConfigurationError as exc:
        current_app.logger.exception("Failed to issue rq-engine token for create index")
        return exception_factory(f"JWT configuration error: {exc}")
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/run_0/run_0_bp.py:914", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory()

    configs = get_configs()
    rows = []
    create_action = "/rq-engine/create/"
    for cfg in sorted(configs):
        if cfg == '_defaults':
            continue

        variants = [
            {
                "label": cfg,
                "overrides": {},
                "config": cfg,
                "action_url": create_action,
            },
            {
                "label": f"{cfg} ned1/2016",
                "overrides": {"general:dem_db": "ned1/2016"},
                "config": cfg,
                "action_url": create_action,
            },
            {
                "label": f"{cfg} WhiteBoxTools",
                "overrides": {"watershed:delineation_backend": "wbt"},
                "config": cfg,
                "action_url": create_action,
            },
        ]
        rows.append({"config": cfg, "variants": variants})

    cap_base_url = None
    cap_asset_base_url = None
    cap_site_key = None
    if current_user.is_anonymous:
        cap_base_url = (current_app.config.get("CAP_BASE_URL") or os.getenv("CAP_BASE_URL", "/cap")).rstrip("/")
        cap_asset_base_url = (
            current_app.config.get("CAP_ASSET_BASE_URL")
            or os.getenv("CAP_ASSET_BASE_URL", f"{cap_base_url}/assets")
        ).rstrip("/")
        cap_site_key = current_app.config.get("CAP_SITE_KEY") or os.getenv("CAP_SITE_KEY", "")

    return render_template(
        "run_0/create_index.htm",
        rows=rows,
        cap_base_url=cap_base_url,
        cap_asset_base_url=cap_asset_base_url,
        cap_site_key=cap_site_key,
        rq_engine_token=rq_engine_token,
    )

def create_run_dir(current_user):
    wd = None
    dir_created = False
    while not dir_created:
        email = getattr(current_user, "email", "")
        runid = generate_runid(email)

        wd = get_wd(runid)
        if _exists(wd):
            continue

        os.makedirs(wd)
        dir_created = True

    return runid, wd


def _issue_rq_engine_token() -> str:
    subject = None
    if hasattr(current_user, "get_id"):
        subject = current_user.get_id()
    if not subject:
        subject = getattr(current_user, "id", None)
    if not subject:
        subject = getattr(current_user, "email", None)
    if not subject:
        raise RuntimeError("Unable to resolve user subject for rq-engine token")

    roles = [
        str(getattr(role, "name", role)).strip()
        for role in (getattr(current_user, "roles", None) or [])
        if str(getattr(role, "name", role)).strip()
    ]

    token_payload = auth_tokens.issue_token(
        str(subject),
        scopes=["rq:enqueue"],
        audience="rq-engine",
        extra_claims={
            "roles": roles,
            "token_class": "user",
            "email": getattr(current_user, "email", None),
            "jti": uuid.uuid4().hex,
        },
    )
    token = token_payload.get("token")
    if not token:
        raise RuntimeError("Failed to issue rq-engine token")
    return token


def _render_run_not_found_page() -> Response:
    view_args = getattr(request, "view_args", {}) or {}
    runid = view_args.get("runid") or request.args.get("runid") or ""
    config = view_args.get("config") or request.args.get("config") or ""
    context = {
        "runid": runid,
        "config": config,
        "diff_runid": "",
        "project_href": "",
        "breadcrumbs_html": "",
        "error_message": "This run either doesn't exist or you don't have access to it.",
        "page_title": "Run Not Found",
    }
    return make_response(render_template("browse/not_found.htm", **context), 404)


def _render_run_internal_error_page(runid: str, config: str, stacktrace: str) -> Response:
    context = {
        "runid": runid,
        "config": config,
        "stacktrace": stacktrace,
    }
    return make_response(render_template("errors/run_0_internal_error.htm", **context), 500)


@run_0_bp.app_errorhandler(403)
def _runs0_forbidden(error):  # pragma: no cover - flask error hook
    return _render_run_not_found_page()


@run_0_bp.app_errorhandler(404)
def _runs0_not_found(error):  # pragma: no cover - flask error hook
    return _render_run_not_found_page()
