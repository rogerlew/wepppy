from __future__ import annotations

import os
import re
from functools import lru_cache
from html import escape as html_escape, unescape as html_unescape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple, TypedDict
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from cmarkgfm import github_flavored_markdown_to_html as markdown_to_html  # type: ignore[import-not-found]
from flask import Blueprint, Response, abort, current_app, jsonify, redirect, render_template, request  # type: ignore[import-not-found]

from wepppy.weppcloud.usersum_anchors import usersum_anchor_slug
from wepppy.weppcloud.usersum_docs.pg_search import (
    PostgresUsersumSearchBackend,
    UsersumSearchUnavailableError,
)
from wepppy.weppcloud.usersum_docs.runtime_catalog import (
    RuntimeCatalog,
    RuntimeDoc,
    filter_nav_tree_for_visibility,
    load_runtime_catalog,
)
from wepppy.weppcloud.utils.helpers import url_for_run

usersum_bp = Blueprint("usersum", __name__, template_folder="templates")

_BASE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _BASE_DIR.parents[3]
_DB_DIR = _BASE_DIR / "db"
_SPEC_DIR = _BASE_DIR / "input-file-specifications"
_WEPPCLOUD_DIR = _BASE_DIR / "weppcloud"
_PATH_DIR = _BASE_DIR / "path"
_GITHUB_BLOB_BASE_URL = "https://github.com/rogerlew/wepppy/blob/master"
_CATEGORY_ROOTS: Dict[str, Path] = {
    "db": _DB_DIR,
    "input-file-specifications": _SPEC_DIR,
    "weppcloud": _WEPPCLOUD_DIR,
    "path": _PATH_DIR,
}
_ROLE_RANK = {"user": 0, "operator": 1, "developer": 2, "internal": 3}
_VALID_DOC_ROLES = set(_ROLE_RANK)
_DEFAULT_SEARCH_ROLE = "user"
_DEFAULT_SEARCH_LIMIT = 20
_MAX_SEARCH_LIMIT = 100
_RANK_TO_ROLE = {rank: role for role, rank in _ROLE_RANK.items()}
_HEADER_ROLE_OPTIONS_BY_WEPPCLOUD_ROLE: Dict[str, Tuple[str, ...]] = {
    "poweruser": ("user", "operator"),
    "admin": ("user", "operator", "developer"),
    "root": ("user", "operator", "developer", "internal"),
}

_INDEX_DOC_DESCRIPTIONS: Dict[str, str] = {
    "usersum.db.climate_file_parameters": "Explains each field in a CLIGEN climate file and how WEPPcloud interprets it.",
    "usersum.db.management_file_parameters": "Defines the management file parameters that control operations, vegetation, residue, and disturbance behavior.",
    "usersum.db.soil_file_parameters": "Defines the soil file parameters that control infiltration, erodibility, hydraulic behavior, and profile structure.",
    "usersum.input_file_specifications.cligenparms": "Describes the CLIGEN station statistics file format used to generate stochastic climate inputs.",
    "usersum.input_file_specifications.climate_file_spec": "Describes the daily climate file structure that WEPP reads during simulation.",
    "usersum.input_file_specifications.plant_file_spec": "Describes the plant and management file format used to represent vegetation, operations, and scenarios.",
    "usersum.input_file_specifications.soil_file_spec": "Describes the WEPP soil file format, including layers, texture, and hydraulic properties.",
    "usersum.path.quick_start": "Walks through the PATH Cost-Effective workflow for evaluating treatment options and erosion outcomes.",
    "usersum.weppcloud.accessibility_statement": "Summarizes WEPPcloud accessibility commitments, current conformance evidence, and known limitations.",
    "usersum.weppcloud.ag_field_mod": "Introduces the agricultural field workflow and the inputs needed for field-scale WEPP modeling.",
    "usersum.weppcloud.bootstrap": "Explains the bootstrap workflow for repeated runs, uncertainty exploration, and comparative analysis.",
    "usersum.weppcloud.clearing_locks": "Shows how to recover from lock-related errors by opening the PowerUser panel and using the Clear Locks action.",
    "usersum.weppcloud.climate_options": "Explains climate data sources, weather-generation choices, and configuration options used by WEPPcloud.",
    "usersum.weppcloud.controls.channel_delineation": "Documents the channel delineation control and the advanced settings used to derive channel networks.",
    "usersum.weppcloud.data_attribution": "Lists the datasets, map services, and regional sources that WEPPcloud depends on.",
    "usersum.weppcloud.disturbed_land_soil_lookup": "Explains how disturbed land classes map to soil properties and calibration assumptions.",
    "usersum.weppcloud.enduser_authoring_guide": "Defines how to write ENDUSER.md documentation for non-developer WEPPcloud audiences using plain language, clear workflows, and explicit interpretation guidance.",
    "usersum.weppcloud.enduser_stub_authoring_guide": "Defines how to write lightweight end-user stub docs for focused topics such as file locations, map preparation, and short procedural references.",
    "usersum.weppcloud.faq": "Answers common questions about WEPPcloud workflows, assumptions, outputs, and model behavior.",
    "usersum.weppcloud.quick_start": "Walks a new user through a standard first WEPPcloud run using the current (Un)Disturbed workflow.",
    "usersum.weppcloud.getting_started": "Provides the fastest path from a new run to a working project with core controls explained.",
    "usersum.weppcloud.undisturbed_earth": "Explains when to use the global Earth interface and what data, limits, and checks matter most before starting a run.",
    "usersum.weppcloud.mods_overview": "Introduces the optional modules that extend WEPPcloud with additional workflows and domain capabilities.",
    "usersum.weppcloud.observed_model_fitting": "Explains how to compare model output against observations and tune runs with observed data.",
    "usersum.weppcloud.profile_jwt_dataset_access_python_r": "Shows how advanced users can access WEPPcloud datasets programmatically from Python or R.",
    "usersum.weppcloud.references": "Collects the core technical and scientific references behind WEPPcloud and related workflows.",
    "usersum.weppcloud.rq_engine": "Documents the queue-backed execution layer that runs background jobs and asynchronous workflows.",
    "usersum.weppcloud.sbs_map_preparation": "Explains how to prepare a soil burn severity raster for upload, including supported raster styles, validation checks, and common fixes.",
    "usersum.weppcloud.user_guide": "Provides a broader tour of the WEPPcloud interface, workflows, and expected user actions.",
    "usersum.weppcloud.models.wepp": "Explains when to use the core WEPP model, how to interpret runoff and sediment outputs, and what limits still matter.",
    "usersum.weppcloud.models.ash_transport": "Explains when to use post-fire ash transport outputs, how to interpret ash export summaries, and the limits of the screening workflow.",
    "usersum.weppcloud.models.debris_flow": "Explains debris-flow probability and volume screening for burned basins across storm durations and recurrence intervals.",
    "usersum.weppcloud.models.gridded_rusle": "Explains how Gridded RUSLE maps long-term erosion potential and how to interpret factor rasters and hotspot patterns.",
    "usersum.weppcloud.models.culvert_modeling": "Explains when culvert hydro-enforcement improves drainage paths and how to interpret conditioned watershed outputs near engineered crossings.",
    "usersum.weppcloud.models.roads": "Explains the road-network erosion workflow, how to prepare road attributes, and how to compare road results against the baseline watershed.",
    "usersum.weppcloud.models.revegetation": "Explains post-fire recovery scenarios, cover transforms, and how revegetation assumptions change runoff and erosion over time.",
    "usersum.weppcloud.models.rhem": "Explains when the RHEM rangeland workflow is appropriate and how to interpret runoff, soil-loss, and sediment-yield outputs.",
    "usersum.weppcloud.models.agricultural_fields": "Explains field and sub-field WEPP workflows for mapped crop boundaries, rotations, and management comparisons.",
    "usersum.weppcloud.models.wepp_swat": "Explains the WEPP-SWAT+ routing workflow and how to interpret SWAT+ channel routing as an extension of WEPP hillslope outputs.",
    "usersum.weppcloud.models.hec_dss_export": "Explains how WEPP channel and outlet time series are exported to HEC-DSS for downstream HEC workflows such as HEC-RAS.",
    "usersum.weppcloud.wepp_advanced_options": "Explains advanced WEPP settings that affect hydrology, erosion, soils, and calibration behavior.",
    "usersum.weppcloud.wepp_forest_change_log": "Tracks WEPP-forest binary build history, compiler lineage, and release notes for executable version selection.",
    "usersum.weppcloud.wepp_interchange": "Explains where WEPP interchange Parquet outputs live, what the main tables represent, and which files are most useful for common hillslope, watershed, and event questions.",
    "usersum.weppcloud.wepp_model": "Introduces the WEPP model, what it simulates, and how its outputs should be interpreted.",
    "usersum.weppcloud.wepp_usersum_2024": "Preserves the Windows WEPP user summary as a cleaned technical reference with historical context and links to the current plant, soil, and climate file specifications.",
    "usersum.weppcloud.weppcloud_runs_directory_structure": "Shows where WEPPcloud stores key `.nodb`, geometry, landuse, soil, WEPP input, and interchange output files within a run directory.",
    "usersum.source.nodb": "Introduces the NoDb run-state system that underpins WEPPcloud project configuration and persistence.",
    "usersum.source.ash_transport": "Describes the ash transport module, its assumptions, and how ash-related outputs are managed.",
    "usersum.source.debris_flow": "Describes the debris flow module, required inputs, and the outputs it produces.",
    "usersum.source.disturbed": "Explains how the (Un)Disturbed interfaces parameterize land use and soils across unburned and burned severity classes and how to interpret the resulting runoff and erosion scenarios.",
    "usersum.source.features_export": "Explains how to export geospatial features, attributes, and derived datasets from a run.",
    "usersum.source.observed": "Describes the observed-data controller used to load and work with calibration or validation datasets.",
    "usersum.source.omni": "Explains how to use Omni Scenarios for whole-run comparisons and Omni Contrasts for targeted treatment comparisons.",
    "usersum.source.openet": "Explains how OpenET-derived evapotranspiration data are incorporated into climate and analysis workflows.",
    "usersum.source.rap": "Explains how Rangeland Analysis Platform cover data are integrated into WEPPcloud workflows.",
    "usersum.source.rhem": "Describes the RHEM workflow and how rangeland erosion modeling is configured in WEPPcloud.",
    "usersum.source.roads": "Describes the roads workflow for road-network erosion, delivery, and reporting outputs.",
    "usersum.source.rusle": "Describes the RUSLE workflow and how empirical erosion estimates are configured and reported.",
    "usersum.source.treatments": "Explains the treatments module used to define, compare, and apply management treatments.",
    "usersum.source.revegetation": "Explains revegetation cover transforms and how post-disturbance recovery scenarios are configured.",
    "usersum.source.soils": "Summarizes the soil datasets, file handling, and package-level utilities used in WEPP soil preparation.",
    "vendor.weppcloud_wbt.culvert_web_app_hydroenforcement": "Documents the culvert hydroenforcement workflow used to condition drainage for terrain analysis.",
    "vendor.weppcloud_wbt.hillslopes_topaz_spec": "Documents the Hillslopes TOPAZ-style derivation workflow used in terrain and watershed preprocessing.",
}

_PARAM_HEADER_RE = re.compile(r"^#### `([^`]+)` —\s*(.+)$")
_DETAIL_RE = re.compile(r"^- \*\*([^*]+)\*\*: ?(.*)$")
_WHITESPACE_RE = re.compile(r"\s+")
_WORD_TOKEN_RE = re.compile(r"[a-z0-9_]+")
_ANCHOR_HREF_RE = re.compile(
    r'(<a\b[^>]*?\bhref\s*=\s*)(["\'])(.*?)(\2)',
    re.IGNORECASE | re.DOTALL,
)
_HEADING_RE = re.compile(
    r"<h(?P<level>[1-6])(?P<attrs>[^>]*)>(?P<body>.*?)</h\1>",
    re.IGNORECASE | re.DOTALL,
)
_HEADING_ID_ATTR_RE = re.compile(r'\bid\s*=\s*(["\'])(?P<id>.*?)\1', re.IGNORECASE | re.DOTALL)


class ParameterDetail(TypedDict):
    label: str
    text: str


class ParameterEntry(TypedDict):
    parameter: str
    summary: str
    details: List[ParameterDetail]
    section: str | None
    group: str | None
    file: str
    search_blob: str


class SearchResult(TypedDict):
    doc_id: str
    title: str
    rel_path: str
    min_role: str
    category: str
    snippet: str
    score: float
    route_url: str
    breadcrumb: List[str]


def _normalise_spaces(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.strip())


def _repo_relative_markdown_path(path: Path) -> str:
    return path.resolve().relative_to(_REPO_ROOT).as_posix()


def _github_blob_url(path: Path) -> str:
    return f"{_GITHUB_BLOB_BASE_URL}/{quote(_repo_relative_markdown_path(path))}"


def _doc_path_label(rel_path: str) -> str:
    return rel_path


@lru_cache(maxsize=1)
def _catalog() -> RuntimeCatalog:
    return load_runtime_catalog(usersum_base_dir=_BASE_DIR, repo_root=_REPO_ROOT)


def _coerce_bool(value: str | None) -> bool:
    if value is None:
        return False
    lowered = value.strip().lower()
    return lowered in {"1", "true", "yes", "on", "extended", "-e", "--extended"}


def _highest_role_ceiling(roles: Sequence[str]) -> str:
    return max(roles, key=lambda role: _ROLE_RANK[role])


def _roles_up_to_ceiling(role_ceiling: str) -> Set[str]:
    ceiling_rank = _ROLE_RANK[role_ceiling]
    return {role for role, rank in _ROLE_RANK.items() if rank <= ceiling_rank}


def _normalise_role_token(raw_role: Any) -> str:
    if isinstance(raw_role, str):
        return raw_role.strip().lower()
    role_name = getattr(raw_role, "name", None)
    if role_name is not None:
        return str(role_name).strip().lower()
    return str(raw_role).strip().lower()


def _caller_weppcloud_role_context() -> Tuple[bool, Set[str]]:
    try:
        from flask_login import current_user  # type: ignore[import-not-found]
    except ImportError:
        return False, set()

    is_authenticated = bool(getattr(current_user, "is_authenticated", False))
    if not is_authenticated:
        return False, set()

    role_tokens: Set[str] = set()
    roles_attr = getattr(current_user, "roles", None)
    if roles_attr is not None:
        role_items = roles_attr if isinstance(roles_attr, (list, tuple, set)) else [roles_attr]
        for role_item in role_items:
            token = _normalise_role_token(role_item)
            if token:
                role_tokens.add(token)

    attr_role_map = {
        "is_root": "root",
        "is_admin": "admin",
        "is_poweruser": "poweruser",
        "is_operator": "operator",
        "can_operate": "operator",
        "is_developer": "developer",
        "can_develop": "developer",
        "is_internal_docs": "internal",
        "is_internal": "internal",
        "can_view_internal_docs": "internal",
    }
    for attr_name, token in attr_role_map.items():
        if bool(getattr(current_user, attr_name, False)):
            role_tokens.add(token)

    return True, role_tokens


def _header_role_options() -> List[str]:
    is_authenticated, role_tokens = _caller_weppcloud_role_context()
    if not is_authenticated:
        return []
    for weppcloud_role in ("root", "admin", "poweruser"):
        if weppcloud_role in role_tokens:
            return list(_HEADER_ROLE_OPTIONS_BY_WEPPCLOUD_ROLE[weppcloud_role])
    return []


def _requested_role_ceiling_or_default(raw_values: Sequence[str]) -> str:
    requested_roles = _split_csv_values(raw_values)
    valid_roles = [role for role in requested_roles if role in _VALID_DOC_ROLES]
    if not valid_roles:
        return _DEFAULT_SEARCH_ROLE
    return _highest_role_ceiling(valid_roles)


def _discovery_role_ceiling(
    *,
    caller_max_role: str,
    header_role_options: Sequence[str],
    header_selected_role: str,
) -> str:
    if not header_role_options:
        return _DEFAULT_SEARCH_ROLE

    selected_role = header_selected_role if header_selected_role in header_role_options else _DEFAULT_SEARCH_ROLE
    effective_rank = min(_ROLE_RANK[selected_role], _ROLE_RANK[caller_max_role])
    return _RANK_TO_ROLE[effective_rank]


def _caller_max_role() -> str:
    is_authenticated, role_tokens = _caller_weppcloud_role_context()
    if not is_authenticated:
        return "user"

    if {"root", "internal", "internal-docs", "internal_docs"} & role_tokens:
        return "internal"
    if {"admin", "developer", "dev"} & role_tokens:
        return "developer"
    if {"operator", "ops", "poweruser"} & role_tokens:
        return "operator"
    return "user"


def _is_doc_visible(doc: RuntimeDoc, caller_max_role: str) -> bool:
    return _ROLE_RANK[doc["min_role"]] <= _ROLE_RANK[caller_max_role]


def _split_csv_values(raw_values: Sequence[str]) -> List[str]:
    values: List[str] = []
    for raw in raw_values:
        for token in raw.split(","):
            value = token.strip().lower()
            if value:
                values.append(value)
    return values


def _parse_search_role_ceiling(raw_values: Sequence[str], *, caller_max_role: str) -> str:
    requested_roles = _split_csv_values(raw_values)
    if not requested_roles:
        return _DEFAULT_SEARCH_ROLE

    invalid_roles = sorted({role for role in requested_roles if role not in _VALID_DOC_ROLES})
    if invalid_roles:
        raise ValueError(f'Invalid role filter: {", ".join(invalid_roles)}.')

    requested_ceiling = _highest_role_ceiling(requested_roles)
    caller_rank = _ROLE_RANK[caller_max_role]
    requested_rank = _ROLE_RANK[requested_ceiling]

    if requested_rank > caller_rank:
        raise PermissionError(
            f"Requested role filter ceiling is not allowed: {requested_ceiling} (max allowed: {caller_max_role})."
        )

    effective_rank = min(requested_rank, caller_rank)
    return _RANK_TO_ROLE[effective_rank]


def _parse_search_categories(raw_values: Sequence[str]) -> Set[str] | None:
    requested_categories = _split_csv_values(raw_values)
    if not requested_categories:
        return None

    available_categories = {doc["category"] for doc in _catalog().docs}
    unknown_categories = sorted({value for value in requested_categories if value not in available_categories})
    if unknown_categories:
        raise ValueError(f'Invalid category filter: {", ".join(unknown_categories)}.')
    return set(requested_categories)


def _parse_int_query_arg(name: str, *, default: int, min_value: int, max_value: int | None = None) -> int:
    raw_value = request.args.get(name)
    if raw_value is None or not raw_value.strip():
        return default

    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise ValueError(f'Query parameter "{name}" must be an integer.') from exc

    if parsed < min_value:
        raise ValueError(f'Query parameter "{name}" must be >= {min_value}.')
    if max_value is not None and parsed > max_value:
        raise ValueError(f'Query parameter "{name}" must be <= {max_value}.')
    return parsed


def _resolve_linked_markdown_path(source_path: Path, href_path: str) -> Path | None:
    rel_token = href_path.strip()
    if not rel_token:
        return None

    candidate: Path
    if rel_token.startswith("/"):
        candidate = (_REPO_ROOT / rel_token.lstrip("/")).resolve()
    else:
        candidate = (source_path.parent / rel_token).resolve()

    if not candidate.is_file():
        return None
    if candidate.suffix.lower() != ".md":
        return None
    if _REPO_ROOT not in candidate.parents:
        return None
    return candidate


def _route_for_repo_markdown(path: Path) -> str | None:
    rel_path = _repo_relative_markdown_path(path)
    doc = _catalog().docs_by_rel_path.get(rel_path)
    if doc is not None:
        return _doc_route_url(doc)
    return url_for_run("usersum.view_src_markdown", rel_path=rel_path)


def _doc_route_url(doc: RuntimeDoc) -> str:
    return url_for_run("usersum.view_doc", doc_id=doc["doc_id"])


def _default_index_description(title: str) -> str:
    return f"Open documentation for {title}."


def _annotate_nav_tree_for_index(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    annotated: List[Dict[str, Any]] = []
    for node in nodes:
        payload = dict(node)
        if payload.get("kind") == "section":
            payload["children"] = _annotate_nav_tree_for_index(payload.get("children", []))
        else:
            doc_id = str(payload["doc_id"])
            payload["description"] = _INDEX_DOC_DESCRIPTIONS.get(
                doc_id,
                _default_index_description(str(payload["title"])),
            )
        annotated.append(payload)
    return annotated


def _rewrite_markdown_href(source_path: Path, href: str) -> str:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc:
        return href

    path_part = parsed.path
    if not path_part or not path_part.lower().endswith(".md"):
        return href

    linked_path = _resolve_linked_markdown_path(source_path, unquote(path_part))
    if linked_path is None:
        return href

    routed_path = _route_for_repo_markdown(linked_path)
    if routed_path is None:
        return href

    return urlunsplit(("", "", routed_path, parsed.query, parsed.fragment))


def _rewrite_markdown_links(source_path: Path, content_html: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        href_value = html_unescape(match.group(3))
        rewritten_href = _rewrite_markdown_href(source_path, href_value)
        if rewritten_href == href_value:
            return match.group(0)
        return (
            f"{match.group(1)}{match.group(2)}"
            f"{html_escape(rewritten_href, quote=True)}"
            f"{match.group(4)}"
        )

    return _ANCHOR_HREF_RE.sub(_replace, content_html)


def _add_heading_anchors(content_html: str) -> str:
    slug_counts: Dict[str, int] = {}

    def _reserve_slug(slug: str) -> str:
        count = slug_counts.get(slug, 0)
        if count == 0:
            slug_counts[slug] = 1
            return slug
        while True:
            candidate = f"{slug}-{count}"
            count += 1
            if candidate not in slug_counts:
                slug_counts[slug] = count
                slug_counts[candidate] = 1
                return candidate

    def _replace(match: re.Match[str]) -> str:
        level = match.group("level")
        attrs = match.group("attrs") or ""
        body = match.group("body")
        existing_id_match = _HEADING_ID_ATTR_RE.search(attrs)
        if existing_id_match is not None:
            existing_id = existing_id_match.group("id").strip()
            if existing_id:
                slug_counts.setdefault(existing_id, 1)
            return match.group(0)
        base_slug = usersum_anchor_slug(body) or "section"
        anchor_id = _reserve_slug(base_slug)
        escaped_anchor_id = html_escape(anchor_id, quote=True)
        return f'<h{level}{attrs} id="{escaped_anchor_id}">{body}</h{level}>'

    return _HEADING_RE.sub(_replace, content_html)


def _doc_breadcrumbs(doc: RuntimeDoc) -> List[Dict[str, str | None]]:
    catalog = _catalog()
    breadcrumbs: List[Dict[str, str | None]] = []
    for item in doc["breadcrumbs"]:
        maybe_doc = catalog.docs_by_nav_key.get(item["key"])
        href = _doc_route_url(maybe_doc) if maybe_doc is not None else None
        breadcrumbs.append({"title": item["title"], "href": href})
    if breadcrumbs:
        breadcrumbs[-1]["href"] = None
    return breadcrumbs


def _render_with_usersum_shell(
    template_name: str,
    *,
    caller_max_role: str,
    active_doc: RuntimeDoc | None = None,
    breadcrumbs: List[Dict[str, str | None]] | None = None,
    **template_kwargs: Any,
):
    catalog = _catalog()
    header_role_options = _header_role_options()
    header_selected_role = template_kwargs.pop(
        "header_selected_role",
        _requested_role_ceiling_or_default(request.args.getlist("role")),
    )
    if header_role_options and header_selected_role not in header_role_options:
        header_selected_role = _DEFAULT_SEARCH_ROLE
    discovery_role_ceiling = _discovery_role_ceiling(
        caller_max_role=caller_max_role,
        header_role_options=header_role_options,
        header_selected_role=header_selected_role,
    )

    nav_tree = filter_nav_tree_for_visibility(
        catalog.nav_tree,
        docs_by_id=catalog.docs_by_id,
        caller_max_role=discovery_role_ceiling,
        active_doc_id=active_doc["doc_id"] if active_doc else None,
    )
    nav_tree = _annotate_nav_tree_for_index(nav_tree)
    return render_template(
        template_name,
        nav_tree=nav_tree,
        breadcrumbs=breadcrumbs or [],
        active_doc=active_doc,
        header_search_query=request.args.get("q", "").strip(),
        header_role_options=header_role_options,
        header_selected_role=header_selected_role,
        url_for_run=url_for_run,
        **template_kwargs,
    )


def _render_markdown_document(
    path: Path,
    *,
    title: str,
    doc_path_label: str,
    caller_max_role: str,
    active_doc: RuntimeDoc | None,
    breadcrumbs: List[Dict[str, str | None]] | None = None,
):
    markdown_source = path.read_text(encoding="utf-8")
    content_html = markdown_to_html(markdown_source)
    content_html = _add_heading_anchors(content_html)
    content_html = _rewrite_markdown_links(path, content_html)
    repo_rel_path = _repo_relative_markdown_path(path)
    return _render_with_usersum_shell(
        "usersum/view.htm",
        caller_max_role=caller_max_role,
        active_doc=active_doc,
        breadcrumbs=breadcrumbs,
        title=title,
        content_html=content_html,
        doc_path_label=doc_path_label,
        github_file_url=_github_blob_url(path),
        raw_markdown_url=url_for_run("usersum.raw_markdown", rel_path=repo_rel_path),
    )


def _resolve_repo_markdown_path(rel_path: str) -> Path:
    candidate = (_REPO_ROOT / rel_path).resolve()
    if not candidate.is_file():
        abort(404)
        raise RuntimeError("unreachable")
    if candidate.suffix.lower() != ".md" or _REPO_ROOT not in candidate.parents:
        abort(404)
    return candidate


def _doc_for_view_alias(category: str, filename: str) -> RuntimeDoc | None:
    alias = f"/usersum/view/{category}/{filename}"
    return _catalog().docs_by_legacy_route_path.get(alias)


def _doc_for_vendor_alias(vendor_id: str, filename: str) -> RuntimeDoc | None:
    alias = f"/usersum/vendor/{vendor_id}/{filename}"
    return _catalog().docs_by_vendor_route_path.get(alias)


def _resolve_doc_or_404(doc_id: str, caller_max_role: str) -> RuntimeDoc:
    doc = _catalog().docs_by_id.get(doc_id)
    if doc is None:
        abort(404)
        raise RuntimeError("unreachable")
    if not _is_doc_visible(doc, caller_max_role):
        abort(404)
        raise RuntimeError("unreachable")
    return doc


@usersum_bp.route("/usersum/", strict_slashes=False)
def usersum_index():
    caller_max_role = _caller_max_role()
    return _render_with_usersum_shell(
        "usersum/index.htm",
        caller_max_role=caller_max_role,
        title="WEPPcloud UserSummary Documentation",
    )


@usersum_bp.route("/usersum/doc/<doc_id>")
def view_doc(doc_id: str):
    caller_max_role = _caller_max_role()
    doc = _resolve_doc_or_404(doc_id, caller_max_role)
    path = _resolve_repo_markdown_path(doc["rel_path"])
    return _render_markdown_document(
        path,
        title=doc["title"],
        doc_path_label=_doc_path_label(doc["rel_path"]),
        caller_max_role=caller_max_role,
        active_doc=doc,
        breadcrumbs=_doc_breadcrumbs(doc),
    )


@usersum_bp.route("/usersum/view/<category>/<path:filename>")
def view_markdown(category: str, filename: str):
    caller_max_role = _caller_max_role()
    doc = _doc_for_view_alias(category, filename)
    if doc is None:
        abort(404)
        raise RuntimeError("unreachable")
    if not _is_doc_visible(doc, caller_max_role):
        abort(404)
        raise RuntimeError("unreachable")

    path = _resolve_repo_markdown_path(doc["rel_path"])
    return _render_markdown_document(
        path,
        title=doc["title"],
        doc_path_label=_doc_path_label(doc["rel_path"]),
        caller_max_role=caller_max_role,
        active_doc=doc,
        breadcrumbs=_doc_breadcrumbs(doc),
    )


@usersum_bp.route("/usersum/vendor/<vendor_id>/<path:filename>")
def view_vendor_markdown(vendor_id: str, filename: str):
    caller_max_role = _caller_max_role()
    doc = _doc_for_vendor_alias(vendor_id, filename)
    if doc is None:
        abort(404)
        raise RuntimeError("unreachable")
    if not _is_doc_visible(doc, caller_max_role):
        abort(404)
        raise RuntimeError("unreachable")
    path = _resolve_repo_markdown_path(doc["rel_path"])
    return _render_markdown_document(
        path,
        title=doc["title"],
        doc_path_label=_doc_path_label(doc["rel_path"]),
        caller_max_role=caller_max_role,
        active_doc=doc,
        breadcrumbs=_doc_breadcrumbs(doc),
    )


@usersum_bp.route("/usersum/src/<path:rel_path>")
def view_src_markdown(rel_path: str):
    caller_max_role = _caller_max_role()
    manifest_doc = _catalog().docs_by_rel_path.get(rel_path)
    if manifest_doc is not None and not _is_doc_visible(manifest_doc, caller_max_role):
        abort(404)
        raise RuntimeError("unreachable")

    require_manifest = _coerce_bool(current_app.config.get("USERSUM_REQUIRE_MANIFEST_FOR_SRC")) or _coerce_bool(
        os.getenv("USERSUM_REQUIRE_MANIFEST_FOR_SRC")
    )
    if require_manifest and manifest_doc is None:
        abort(404)
        raise RuntimeError("unreachable")

    path = _resolve_repo_markdown_path(rel_path)
    title = manifest_doc["title"] if manifest_doc is not None else rel_path
    breadcrumbs = _doc_breadcrumbs(manifest_doc) if manifest_doc is not None else []
    return _render_markdown_document(
        path,
        title=title,
        doc_path_label=_doc_path_label(rel_path),
        caller_max_role=caller_max_role,
        active_doc=manifest_doc,
        breadcrumbs=breadcrumbs,
    )


@usersum_bp.route("/usersum/src//<path:rel_path>")
def view_src_markdown_legacy(rel_path: str):
    return redirect(url_for_run("usersum.view_src_markdown", rel_path=rel_path), code=308)


@usersum_bp.route("/usersum/raw/<path:rel_path>")
def raw_markdown(rel_path: str):
    caller_max_role = _caller_max_role()
    manifest_doc = _catalog().docs_by_rel_path.get(rel_path)
    if manifest_doc is not None and not _is_doc_visible(manifest_doc, caller_max_role):
        abort(404)
        raise RuntimeError("unreachable")
    path = _resolve_repo_markdown_path(rel_path)
    markdown_source = path.read_text(encoding="utf-8")
    return Response(markdown_source, mimetype="text/markdown")


def _tokenize_search_query(query: str) -> List[str]:
    tokens = _WORD_TOKEN_RE.findall(query.lower())
    seen: Set[str] = set()
    unique_tokens: List[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        unique_tokens.append(token)
    return unique_tokens


def _score_in_memory_doc(doc: RuntimeDoc, query: str, tokens: Sequence[str]) -> float:
    title_text = doc["title"].lower()
    headings_text = " ".join(doc["headings"]).lower()
    body_text = doc["body_text"].lower()

    score = 0.0
    matched = False
    for token in tokens:
        if token in title_text:
            score += 4.0
            matched = True
        if token in headings_text:
            score += 2.5
            matched = True
        if token in body_text:
            score += 1.0
            matched = True

    phrase = _normalise_spaces(query).lower()
    if phrase:
        if phrase in title_text:
            score += 4.0
            matched = True
        elif phrase in headings_text:
            score += 2.0
            matched = True
        elif phrase in body_text:
            score += 1.25
            matched = True
    if not matched:
        return 0.0
    return score


def _snippet_from_text(text: str, query: str, tokens: Sequence[str]) -> str:
    if not text:
        return ""
    haystack = text.lower()
    phrase = _normalise_spaces(query).lower()
    index = haystack.find(phrase) if phrase else -1
    if index < 0:
        for token in tokens:
            index = haystack.find(token)
            if index >= 0:
                break
    if index < 0:
        preview = text[:220].strip()
        return f"{preview}..." if len(text) > 220 else preview
    start = max(index - 70, 0)
    end = min(index + 150, len(text))
    snippet = text[start:end].strip()
    if start > 0:
        snippet = f"...{snippet}"
    if end < len(text):
        snippet = f"{snippet}..."
    return snippet


def _render_search_snippet_html(snippet_text: str) -> str:
    normalized = _normalise_spaces(snippet_text)
    if not normalized:
        return ""
    return markdown_to_html(normalized).strip()


def _postgres_search_backend() -> PostgresUsersumSearchBackend | None:
    if _coerce_bool(current_app.config.get("USERSUM_SEARCH_DISABLE_POSTGRES")):
        return None
    db_url = str(
        current_app.config.get("SQLALCHEMY_DATABASE_URI")
        or os.getenv("DATABASE_URL")
        or ""
    ).strip()
    if not db_url.lower().startswith("postgresql"):
        return None
    return _cached_postgres_search_backend(db_url)


@lru_cache(maxsize=2)
def _cached_postgres_search_backend(db_url: str) -> PostgresUsersumSearchBackend:
    return PostgresUsersumSearchBackend(db_url)


def _search_documents(
    query: str,
    *,
    role_ceiling: str,
    categories: Set[str] | None,
    limit: int,
    offset: int,
    caller_max_role: str,
) -> Tuple[List[SearchResult], int, str | None]:
    catalog = _catalog()
    normalized_query = _normalise_spaces(query)
    if not normalized_query:
        return [], 0, None
    role_scope = _roles_up_to_ceiling(role_ceiling)

    backend = _postgres_search_backend()
    if backend is not None:
        try:
            backend.ensure_synced(catalog.docs)
            pg_results, total = backend.search(
                query=normalized_query,
                roles=sorted(role_scope, key=lambda role: _ROLE_RANK[role]),
                categories=sorted(categories) if categories else None,
                limit=limit,
                offset=offset,
            )
            results: List[SearchResult] = []
            for row in pg_results:
                doc = catalog.docs_by_id.get(row["doc_id"])
                if doc is None:
                    continue
                if not _is_doc_visible(doc, caller_max_role):
                    continue
                results.append(
                    SearchResult(
                        doc_id=row["doc_id"],
                        title=row["title"],
                        rel_path=row["rel_path"],
                        min_role=row["min_role"],
                        category=row["category"],
                        snippet=_render_search_snippet_html(str(row["snippet"])),
                        score=round(float(row["score"]), 6),
                        route_url=_doc_route_url(doc),
                        breadcrumb=[item["title"] for item in doc["breadcrumbs"]],
                    )
                )
            return results, total, None
        except UsersumSearchUnavailableError as exc:
            if _coerce_bool(current_app.config.get("USERSUM_SEARCH_STRICT_POSTGRES")):
                raise
            warning = f"PostgreSQL search unavailable, using in-memory fallback: {exc}"
        else:
            warning = None
    else:
        warning = None

    tokens = _tokenize_search_query(normalized_query)
    matches: List[SearchResult] = []
    for doc in catalog.visible_docs(caller_max_role):
        if doc["min_role"] not in role_scope:
            continue
        if categories is not None and doc["category"] not in categories:
            continue
        score = _score_in_memory_doc(doc, normalized_query, tokens)
        if score <= 0:
            continue
        matches.append(
            SearchResult(
                doc_id=doc["doc_id"],
                title=doc["title"],
                rel_path=doc["rel_path"],
                min_role=doc["min_role"],
                category=doc["category"],
                snippet=_render_search_snippet_html(
                    _snippet_from_text(doc["body_text"], normalized_query, tokens)
                ),
                score=round(score, 6),
                route_url=_doc_route_url(doc),
                breadcrumb=[item["title"] for item in doc["breadcrumbs"]],
            )
        )

    matches.sort(key=lambda item: (-item["score"], item["title"].lower(), item["rel_path"]))
    total = len(matches)
    return matches[offset : offset + limit], total, warning


def _parse_parameter_file(path: Path) -> List[ParameterEntry]:
    section: str | None = None
    group: str | None = None
    entries: List[ParameterEntry] = []

    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("## "):
            section = line[3:].strip()
            index += 1
            continue
        if line.startswith("### "):
            group = line[4:].strip()
            index += 1
            continue

        header_match = _PARAM_HEADER_RE.match(line)
        if header_match:
            parameter = header_match.group(1).strip()
            summary = header_match.group(2).strip()
            details: List[ParameterDetail] = []

            next_index = index + 1
            while next_index < len(lines):
                candidate = lines[next_index]
                if candidate.startswith("#### ") or candidate.startswith("### ") or candidate.startswith("## "):
                    break
                detail_match = _DETAIL_RE.match(candidate)
                if detail_match:
                    details.append(
                        {"label": detail_match.group(1).strip(), "text": detail_match.group(2).strip()}
                    )
                next_index += 1

            detail_text = " ".join(f"{detail['label']} {detail['text']}" for detail in details)
            entries.append(
                {
                    "parameter": parameter,
                    "summary": summary,
                    "details": details,
                    "section": section,
                    "group": group,
                    "file": path.name,
                    "search_blob": _normalise_spaces(
                        " ".join([parameter, summary, section or "", group or "", path.name, detail_text])
                    ).lower(),
                }
            )
            index = next_index
            continue
        index += 1
    return entries


@lru_cache(maxsize=1)
def _load_parameter_catalog() -> Tuple[Dict[str, List[ParameterEntry]], List[ParameterEntry]]:
    by_name: Dict[str, List[ParameterEntry]] = {}
    all_entries: List[ParameterEntry] = []
    if not _DB_DIR.exists():
        return by_name, all_entries
    for path in sorted(_DB_DIR.glob("*.md")):
        for entry in _parse_parameter_file(path):
            all_entries.append(entry)
            by_name.setdefault(entry["parameter"].lower(), []).append(entry)
    return by_name, all_entries


def _format_parameter_entry(entry: ParameterEntry, include_extended: bool) -> List[str]:
    lines: List[str] = [f"{entry['parameter']} — {entry['summary']}"]
    context_parts: List[str] = []
    if entry["section"]:
        context_parts.append(entry["section"])
    if entry["group"]:
        context_parts.append(entry["group"])
    context_label = " › ".join(context_parts)
    lines.append(f"Context: {context_label} [{entry['file']}]" if context_label else f"Source: {entry['file']}")
    for detail in entry["details"]:
        if not include_extended and detail["label"].lower() == "extended":
            continue
        lines.append(f"{detail['label']}: {detail['text']}")
    return lines


@usersum_bp.route("/usersum/api/parameter")
def usersum_api_parameter():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": {"message": "Parameter name is required."}}), 400
    include_extended = _coerce_bool(request.args.get("extended"))
    by_name, _ = _load_parameter_catalog()
    entries = by_name.get(name.lower())
    if not entries:
        return jsonify({"error": {"message": f'No entries found for "{name}".'}}), 404
    lines: List[str] = []
    for entry in entries:
        lines.extend(_format_parameter_entry(entry, include_extended))
        lines.append("")
    if lines:
        lines.pop()
    return jsonify({"lines": lines})


@usersum_bp.route("/usersum/api/keyword")
def usersum_api_keyword():
    keyword = request.args.get("q") or request.args.get("keyword")
    if not keyword or not keyword.strip():
        return jsonify({"error": {"message": "Keyword is required."}}), 400
    term = keyword.strip().lower()
    _, entries = _load_parameter_catalog()
    matches: List[ParameterEntry] = []
    seen: Set[Tuple[str, str, str | None, str | None, str]] = set()
    for entry in entries:
        if term in entry["search_blob"]:
            identity = (entry["parameter"], entry["summary"], entry["section"], entry["group"], entry["file"])
            if identity in seen:
                continue
            seen.add(identity)
            matches.append(entry)
        if len(matches) >= 25:
            break
    if not matches:
        return jsonify({"lines": [f'No matches found for "{keyword}".']}), 200

    lines: List[str] = []
    for entry in matches:
        context_parts: List[str] = []
        if entry["section"]:
            context_parts.append(entry["section"])
        if entry["group"]:
            context_parts.append(entry["group"])
        context_label = " › ".join(context_parts)
        lines.append(
            f"{entry['parameter']} — {entry['summary']} [{context_label}] ({entry['file']})"
            if context_label
            else f"{entry['parameter']} — {entry['summary']} ({entry['file']})"
        )
    return jsonify({"lines": lines})


@usersum_bp.route("/usersum/api/search")
def usersum_api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": {"message": 'Search query "q" is required.'}}), 400

    caller_max_role = _caller_max_role()
    try:
        role_ceiling = _parse_search_role_ceiling(request.args.getlist("role"), caller_max_role=caller_max_role)
        categories = _parse_search_categories(request.args.getlist("category"))
        limit = _parse_int_query_arg("limit", default=_DEFAULT_SEARCH_LIMIT, min_value=1, max_value=_MAX_SEARCH_LIMIT)
        offset = _parse_int_query_arg("offset", default=0, min_value=0)
    except ValueError as exc:
        return jsonify({"error": {"message": str(exc)}}), 400
    except PermissionError as exc:
        return jsonify({"error": {"message": str(exc)}}), 403

    try:
        results, total, warning = _search_documents(
            query,
            role_ceiling=role_ceiling,
            categories=categories,
            limit=limit,
            offset=offset,
            caller_max_role=caller_max_role,
        )
    except UsersumSearchUnavailableError as exc:
        return jsonify({"error": {"message": str(exc)}}), 503

    payload = {
        "results": [
            {
                "doc_id": result["doc_id"],
                "title": result["title"],
                "rel_path": result["rel_path"],
                "min_role": result["min_role"],
                "category": result["category"],
                "snippet": result["snippet"],
                "score": result["score"],
                "breadcrumb": result["breadcrumb"],
            }
            for result in results
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
    if warning:
        payload["warning"] = warning
    return jsonify(payload)


@usersum_bp.route("/usersum/search")
def usersum_search():
    query = request.args.get("q", "").strip()
    caller_max_role = _caller_max_role()
    categories: Set[str] | None = None
    role_ceiling = _DEFAULT_SEARCH_ROLE
    limit = _DEFAULT_SEARCH_LIMIT
    offset = 0
    error_message: str | None = None
    warning_message: str | None = None

    try:
        role_ceiling = _parse_search_role_ceiling(request.args.getlist("role"), caller_max_role=caller_max_role)
        categories = _parse_search_categories(request.args.getlist("category"))
        limit = _parse_int_query_arg("limit", default=_DEFAULT_SEARCH_LIMIT, min_value=1, max_value=_MAX_SEARCH_LIMIT)
        offset = _parse_int_query_arg("offset", default=0, min_value=0)
    except (ValueError, PermissionError) as exc:
        error_message = str(exc)

    results: List[SearchResult] = []
    total = 0
    if query and error_message is None:
        try:
            results, total, warning_message = _search_documents(
                query,
                role_ceiling=role_ceiling,
                categories=categories,
                limit=limit,
                offset=offset,
                caller_max_role=caller_max_role,
            )
        except UsersumSearchUnavailableError as exc:
            error_message = str(exc)

    category_options = sorted({doc["category"] for doc in _catalog().visible_docs(caller_max_role)})
    return _render_with_usersum_shell(
        "usersum/search.htm",
        caller_max_role=caller_max_role,
        title="Usersum Search",
        query=query,
        selected_role=role_ceiling,
        header_selected_role=role_ceiling,
        category_options=category_options,
        selected_categories=sorted(categories) if categories else [],
        results=results,
        total=total,
        limit=limit,
        offset=offset,
        error_message=error_message,
        warning_message=warning_message,
    )


__all__ = ["usersum_bp"]
