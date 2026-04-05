"""Routes for wepp blueprint extracted from app.py."""

import io
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import wepppy

from .._common import *  # noqa: F401,F403

from wepppy.all_your_base import isfloat, isint
from wepppy.nodb import mods as nodb_mods
from wepppy.nodb.core import Landuse, Ron, Climate, Watershed, Wepp
from wepppy.nodb.core.management_overrides import (
    apply_disturbed_management_overrides,
    normalize_disturbed_class_for_management_lookup,
    resolve_disturbed_scalar_replacements,
)
from wepppy.nodb.core.ron import RonViewModel
from wepppy.nodb.mods.features_export.service import (
    FeaturesExportServiceError,
    load_publication_registry,
    normalize_published_profile_id,
    resolve_published_artifact_path,
    resolve_published_profile_request,
)
from wepppy.nodb.unitizer import Unitizer, precisions, converters
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.wepp import management
from wepppy.wepp.reports import ChannelSummaryReport, HillSummaryReport, OutletSummaryReport
from wepppy.wepp.reports import TotalWatbalReport
from wepppy.wepp.reports.report_base import ReportBase
from wepppy.wepp.reports.row_data import parse_name, parse_units
from wepppy.wepp.reports.output_scope import normalize_output_scope, scoped_dataset_path
from wepppy.weppcloud.utils.helpers import (error_factory, exception_factory, parse_rec_intervals, authorize_and_handle_with_exception_factory)
from wepppy.weppcloud.utils.cap_guard import requires_cap
from wepppy.query_engine import resolve_run_context
from wepppy.query_engine.payload import QueryRequest
from wepppy.query_engine import run_query
import json
from flask import Response, abort

wepp_bp = Blueprint('wepp', __name__)

_DISTURBED_PREVIEW_TEXTURES: tuple[tuple[str, str, str], ...] = (
    ("clay", "Clay", "clay loam"),
    ("loam", "Loam", "loam"),
    ("sand", "Sand", "sand loam"),
    ("silt", "Silt", "silt loam"),
)

_DISTURBED_PREVIEW_TEXTURE_ALIASES = {
    "clay": "clay loam",
    "clay loam": "clay loam",
    "loam": "loam",
    "sand": "sand loam",
    "sand loam": "sand loam",
    "silt": "silt loam",
    "silt loam": "silt loam",
}


def _build_disturbed_preview_context(mods) -> dict[str, object]:
    normalized_mods = tuple(mods or ())
    return {
        "disturbed_preview_available": "disturbed" in normalized_mods,
        "disturbed_preview_textures": tuple(
            (slug, label) for slug, label, _texture_name in _DISTURBED_PREVIEW_TEXTURES
        ),
    }


def _normalize_disturbed_preview_texture(texture: str) -> str | None:
    token = re.sub(r"[\s_-]+", " ", (texture or "").strip().lower())
    return _DISTURBED_PREVIEW_TEXTURE_ALIASES.get(token)


def _wants_csv() -> bool:
    fmt = (request.args.get('format') or '').lower()
    if fmt == 'csv':
        return True
    accept = request.headers.get('Accept', '')
    return 'text/csv' in accept.lower()


def _resolve_output_scope():
    """Resolve and validate the report output scope from request args."""
    try:
        return normalize_output_scope(request.args.get("output_scope"))
    except ValueError as exc:
        response = error_factory(str(exc))
        response.status_code = 400
        return response


def _daily_simulation_date_sql(dataset_alias: str) -> str:
    """Build a stable date expression for daily WEPP interchange datasets.

    Some daily interchange rows can carry a terminal overflow month/day pair
    (for example `month=13`, `day_of_month=1`) while `year` and `julian`
    remain ordered and usable. Constructing the chart index from `year` and
    `julian` keeps the streamflow query resilient to that overflow row.
    """
    return f"MAKE_DATE({dataset_alias}.year, 1, 1) + ({dataset_alias}.julian - 1)"


def _safe_gt_timestamp(a, b) -> bool:
    if a is None or b is None:
        return False
    try:
        return int(a) > int(b)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:46", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return False


def _first_valid_timestamp(prep, *redis_fields):
    for field in redis_fields:
        try:
            value = prep.redis.hget(prep.run_id, field)
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:54", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            value = None
        if value not in (None, ""):
            return value
    return None


def _wepp_outputs_exist(wd: str, climate: Climate) -> bool:
    output_dir = _join(wd, "wepp", "output")
    loss_pw0 = _join(output_dir, "loss_pw0.txt")
    if _exists(loss_pw0):
        return True

    # Interchange conversion can delete raw text outputs; treat the converted loss parquet
    # as evidence that watershed results exist.
    if _exists(_join(output_dir, "interchange", "loss_pw0.out.parquet")):
        return True

    try:
        ss_batch_storms = getattr(climate, "ss_batch_storms", None)
        if ss_batch_storms:
            for storm in ss_batch_storms:
                ss_batch_key = storm.get("ss_batch_key")
                if not ss_batch_key:
                    continue
                if _exists(_join(output_dir, f"{ss_batch_key}/loss_pw0.txt")):
                    return True
                if _exists(_join(output_dir, ss_batch_key, "interchange", "loss_pw0.out.parquet")):
                    return True
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:83", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return False

    return False


def _resolve_published_export_relpath(wd: str, profile: str) -> str | None:
    canonical_profile = normalize_published_profile_id(profile)
    if canonical_profile is None:
        return None

    try:
        registry = load_publication_registry(wd)
    except FeaturesExportServiceError:
        return None

    profiles = registry.get("profiles")
    if not isinstance(profiles, dict):
        return None
    entry = profiles.get(canonical_profile)
    if not isinstance(entry, dict):
        return None

    artifact_relpath = str(entry.get("artifact_relpath") or "").strip()
    if not artifact_relpath:
        return None

    wd_path = Path(wd).resolve()
    artifact_path = (wd_path / artifact_relpath).resolve()
    try:
        artifact_path.relative_to(wd_path)
    except ValueError:
        return None
    if not artifact_path.is_file():
        return None
    return artifact_relpath


_DOWNLOAD_FILENAME_TOKEN_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_download_filename_token(value: str, *, fallback: str) -> str:
    token = _DOWNLOAD_FILENAME_TOKEN_PATTERN.sub("-", str(value).strip()).strip("-._")
    if token:
        return token
    return fallback


def _published_export_download_filename(runid: str, profile: str) -> str:
    canonical_profile, request_payload = resolve_published_profile_request(profile)
    format_token = str(request_payload.get("format") or "export")
    runid_token = _safe_download_filename_token(runid, fallback="run")
    profile_token = _safe_download_filename_token(canonical_profile, fallback="profile")
    format_token_safe = _safe_download_filename_token(format_token, fallback="export")
    return f"{runid_token}.{profile_token}.{format_token_safe}.zip"


def _wepp_results_invalidated(prep) -> bool:
    run_wepp = _first_valid_timestamp(
        prep,
        "timestamps:run_wepp_watershed",
        "timestamps:run_wepp",
    )
    return not (
        _safe_gt_timestamp(run_wepp, prep.redis.hget(prep.run_id, "timestamps:build_landuse"))
        and _safe_gt_timestamp(run_wepp, prep.redis.hget(prep.run_id, "timestamps:build_soils"))
        and _safe_gt_timestamp(run_wepp, prep.redis.hget(prep.run_id, "timestamps:build_climate"))
    )


def _rusle_outputs_exist(wd: str) -> bool:
    rusle_dir = Path(wd) / "rusle"
    if not rusle_dir.exists():
        return False
    if any(rusle_dir.glob("a_*.tif")):
        return True
    return (rusle_dir / "manifest.json").exists()


def _rusle_results_invalidated(prep) -> bool:
    run_wepp = _first_valid_timestamp(
        prep,
        "timestamps:run_wepp_watershed",
        "timestamps:run_wepp",
    )
    rusle_build = prep.redis.hget(prep.run_id, "timestamps:build_rusle")
    build_climate = prep.redis.hget(prep.run_id, "timestamps:build_climate")

    if run_wepp in (None, ""):
        return not _safe_gt_timestamp(rusle_build, build_climate)

    return not (
        _safe_gt_timestamp(rusle_build, build_climate)
        and _safe_gt_timestamp(rusle_build, run_wepp)
    )


def _resolve_rusle_active_a_relpath(wd: str) -> str | None:
    manifest_path = Path(wd) / "rusle" / "manifest.json"
    if not manifest_path.exists():
        return None

    try:
        with manifest_path.open("r", encoding="utf-8") as stream:
            manifest = json.load(stream)
    except (OSError, ValueError, TypeError):
        return None

    rusle_payload = manifest.get("rusle", {}) if isinstance(manifest, dict) else {}
    artifacts = rusle_payload.get("artifacts", {}) if isinstance(rusle_payload, dict) else {}
    relpath = artifacts.get("a_relpath") if isinstance(artifacts, dict) else None
    if not isinstance(relpath, str):
        return None

    normalized = relpath.replace("\\", "/").strip()
    if not normalized.startswith("rusle/"):
        return None
    if not _exists(_join(wd, normalized)):
        return None
    return normalized


def _render_report_csv(*, runid, report: ReportBase, unitizer, slug, table=None):
    df = report.to_dataframe()
    df = _apply_unitizer_preferences(df, unitizer)

    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)

    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    filename_parts = [runid, timestamp, slug]
    if table:
        filename_parts.append(table)
    filename = '-'.join(filename_parts) + '.csv'

    return Response(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


def _render_dataframe_csv(*, runid, df: pd.DataFrame, slug: str, table: str | None = None):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)

    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    parts = [runid, timestamp, slug]
    if table:
        parts.append(table)
    filename = '-'.join(parts) + '.csv'

    return Response(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


def _unitizer_preferences(unitizer):
    try:
        return unitizer.preferences()
    except TypeError:
        return unitizer.preferences


def _convert_scalar_to_preference(value, units, preferences):
    if value in (None, ''):
        return value, units or ''
    if not units:
        return value, ''

    unitclass = _determine_unitclass(units)
    if not unitclass:
        return value, _display_units(units)

    base_key = _find_unit_key(unitclass, units)
    pref_choice = preferences.get(unitclass, base_key)
    pref_key = _find_unit_key(unitclass, pref_choice)
    converter = _get_converter(unitclass, base_key, pref_key)
    converted = value
    if converter:
        converted = _convert_value(value, converter)

    precision = precisions[unitclass].get(pref_key, precisions[unitclass].get(base_key, 3))
    try:
        converted = round(float(converted), precision)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:169", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        pass

    return converted, _display_units(pref_key)


def _build_outlet_summary_dataframe(report, unitizer, include_extraneous=False):
    preferences = _unitizer_preferences(unitizer)
    rows = []
    for row in report.rows(include_extraneous=include_extraneous):
        value, value_units = _convert_scalar_to_preference(row.value, row.units, preferences)
        per_area_value, per_area_units = _convert_scalar_to_preference(
            row.per_area_value, row.per_area_units, preferences
        )
        rows.append(
            {
                "Metric": row.label,
                "Value": value,
                "Value Units": value_units,
                "Per Unit Area": per_area_value,
                "Per Unit Area Units": per_area_units,
            }
        )
    return pd.DataFrame(rows, columns=["Metric", "Value", "Value Units", "Per Unit Area", "Per Unit Area Units"])


_RETURN_PERIOD_METRIC_ORDER = [
    "Precipitation Depth",
    "Runoff",
    "Peak Discharge",
    "10-min Peak Rainfall Intensity",
    "15-min Peak Rainfall Intensity",
    "30-min Peak Rainfall Intensity",
    "Storm Duration",
    "Sediment Yield",
    "Hill Sed Del",
    "Hill Streamflow",
    "Soluble Reactive P",
    "Particulate P",
    "Total P",
]

_RETURN_PERIOD_DISPLAY_LABELS = {
    "Precipitation Depth": "Precipitation",
    "Runoff": "Runoff",
    "Peak Discharge": "Peak Discharge",
    "10-min Peak Rainfall Intensity": "10-min Peak Rainfall Intensity",
    "15-min Peak Rainfall Intensity": "15-min Peak Rainfall Intensity",
    "30-min Peak Rainfall Intensity": "30-min Peak Rainfall Intensity",
    "Storm Duration": "Storm Duration",
    "Sediment Yield": "Sediment Yield",
    "Hill Sed Del": "Hill Sed Del",
    "Hill Streamflow": "Hill Streamflow",
    "Soluble Reactive P": "Soluble Reactive P",
    "Particulate P": "Particulate P",
    "Total P": "Total P",
}


def _slugify_return_period_key(key: str) -> str:
    slug = key.lower()
    slug = slug.replace("+", " plus ")
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "return-period"


def _format_return_period_date(entry, base_year: int) -> str:
    try:
        month = int(entry.get("mo", 0))
        day = int(entry.get("da", 0))
        year = int(entry.get("year", 0))
        computed_year = int(base_year) - 1 + year
        return f"{month:02d}/{day:02d}/{computed_year:04d}"
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:243", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return ""


def _return_period_column_label(metric_key: str, units: str | None) -> str:
    label = _RETURN_PERIOD_DISPLAY_LABELS.get(metric_key, metric_key)
    if units:
        return f"{label} ({units})"
    return label


def _build_return_period_simple_dataframe(report, metric_key, unitizer):
    dataset = report.return_periods.get(metric_key, {})
    if not dataset:
        return pd.DataFrame()

    units = report.units_d.get(metric_key)
    column_label = _return_period_column_label(metric_key, units)

    rows = []
    for interval_key, entry in sorted(dataset.items(), key=lambda kv: float(kv[0]), reverse=True):
        value = entry.get(metric_key)
        rows.append(
            {
                "Recurrence Interval (years)": float(interval_key),
                "Date": _format_return_period_date(entry, report.y0),
                column_label: value,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return _apply_unitizer_preferences(df, unitizer)


def _build_return_period_extraneous_dataframe(report, metric_key, unitizer):
    dataset = report.return_periods.get(metric_key, {})
    if not dataset:
        return pd.DataFrame()

    first_entry = next(iter(dataset.values()), {})
    available_metrics = [
        key for key in _RETURN_PERIOD_METRIC_ORDER if key in first_entry
    ]

    rows = []
    for interval_key, entry in sorted(dataset.items(), key=lambda kv: float(kv[0]), reverse=True):
        row = {
            "Recurrence Interval (years)": float(interval_key),
            "Date": _format_return_period_date(entry, report.y0),
        }
        for metric in available_metrics:
            units = report.units_d.get(metric)
            label = _return_period_column_label(metric, units)
            row[label] = entry.get(metric)
        if "weibull_rank" in entry:
            row["Rank"] = entry.get("weibull_rank")
        if "weibull_T" in entry:
            row["Weibull T"] = entry.get("weibull_T")
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return _apply_unitizer_preferences(df, unitizer)


def _apply_unitizer_preferences(df, unitizer):
    try:
        preferences = unitizer.preferences()
    except TypeError:
        preferences = unitizer.preferences
    renames = {}

    for column in list(df.columns):
        name = parse_name(column)
        base_units = parse_units(column)
        if base_units:
            unitclass = _determine_unitclass(base_units)
            if unitclass:
                base_key = _find_unit_key(unitclass, base_units)
                pref_choice = preferences.get(unitclass, base_key)
                pref_key = _find_unit_key(unitclass, pref_choice)
                target_units = _display_units(pref_key)
                converter = _get_converter(unitclass, base_key, pref_key)
                if converter:
                    df[column] = df[column].apply(lambda value: _convert_value(value, converter))
                renames[column] = f"{name} ({target_units})"
            else:
                renames[column] = f"{name} ({base_units})"
        else:
            renames[column] = name

    return df.rename(columns=renames)


def _determine_unitclass(unit):
    if not unit:
        return None
    target = unit.split(',')[0]
    for unitclass, options in precisions.items():
        for key in options.keys():
            if key.split(',')[0] == target:
                return unitclass
    return None


def _find_unit_key(unitclass, unit):
    target = (unit or '').split(',')[0]
    for key in precisions[unitclass].keys():
        if key.split(',')[0] == target:
            return key
    return unit


def _display_units(unit):
    return (unit or '').split(',')[0]


def _get_converter(unitclass, from_unit, to_unit):
    mapping = converters.get(unitclass, {})
    candidates = [
        (from_unit, to_unit),
        (from_unit.split(',')[0], to_unit),
        (from_unit, to_unit.split(',')[0]),
        (from_unit.split(',')[0], to_unit.split(',')[0]),
    ]
    for pair in candidates:
        converter = mapping.get(pair)
        if converter:
            return converter
    return None


def _convert_value(value, converter):
    if value in (None, ''):
        return value
    try:
        return converter(float(value))
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:383", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        try:
            return converter(value)
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:386", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            return value

@wepp_bp.route('/runs/<string:runid>/<config>/view/channel_def/<chn_key>')
@wepp_bp.route('/runs/<string:runid>/<config>/view/channel_def/<chn_key>/')
@authorize_and_handle_with_exception_factory
def view_channel_def(runid, config, chn_key):
    wd = get_wd(runid)
    assert wd is not None

    try:
        chn_d = management.get_channel(chn_key)
    except KeyError:
        return error_factory('Could not find channel def with key "%s"' % chn_key)

    return jsonify(chn_d)


@wepp_bp.route('/runs/<string:runid>/<config>/view/management/<key>')
@wepp_bp.route('/runs/<string:runid>/<config>/view/management/<key>/')
@authorize_and_handle_with_exception_factory
def view_management(runid, config, key):
    wd = get_wd(runid)
    assert wd is not None

    landuse = Landuse.getInstance(wd)
    man = landuse.managements[str(key)].get_management()
    contents = repr(man)

    r = Response(response=contents, status=200, mimetype="text/plain")
    r.headers["Content-Type"] = "text/plain; charset=utf-8"
    return r


@wepp_bp.route('/runs/<string:runid>/<config>/view/management_effective/<key>/<texture>')
@wepp_bp.route('/runs/<string:runid>/<config>/view/management_effective/<key>/<texture>/')
@authorize_and_handle_with_exception_factory
def view_management_effective(runid, config, key, texture):
    wd = get_wd(runid)
    assert wd is not None

    requested_texture = _normalize_disturbed_preview_texture(texture)
    if requested_texture is None:
        valid_textures = ", ".join(label for _slug, label, _name in _DISTURBED_PREVIEW_TEXTURES)
        return error_factory(
            f"Invalid texture '{texture}'. Expected one of: {valid_textures}.",
            status_code=400,
            code="invalid_texture",
        )

    landuse = Landuse.getInstance(wd)
    man_summary = landuse.managements.get(str(key))
    if man_summary is None:
        return error_factory(
            f'Could not find management with key "{key}"',
            status_code=404,
            code="management_not_found",
        )

    disturbed = nodb_mods.Disturbed.tryGetInstance(wd)
    if disturbed is None:
        return error_factory(
            "Disturbed mod is not enabled for this run; disturbed-effective preview is unavailable.",
            status_code=400,
            code="disturbed_not_enabled",
        )

    management_obj = man_summary.get_management()
    disturbed_class, disturbed_class_str = normalize_disturbed_class_for_management_lookup(
        getattr(man_summary, "disturbed_class", None)
    )
    replacements = disturbed.land_soil_replacements_d.get((requested_texture, disturbed_class))

    rdmax, xmxlai = resolve_disturbed_scalar_replacements(
        disturbed_class=disturbed_class,
        disturbed_class_str=disturbed_class_str,
        replacements=replacements,
        # Preview output should expose lookup-effective replacement parameters
        # directly, even when cancov override exists on the summary.
        cancov_override=None,
    )

    if isfloat(rdmax):
        management_obj.set_rdmax(float(rdmax))

    if isfloat(xmxlai):
        management_obj.set_xmxlai(float(xmxlai))

    if replacements is not None:
        apply_disturbed_management_overrides(management_obj, replacements)

    contents = repr(management_obj)
    response = Response(response=contents, status=200, mimetype="text/plain")
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


@wepp_bp.route('/runs/<string:runid>/<config>/tasks/set_run_wepp_routine', methods=['POST'])
@wepp_bp.route('/runs/<string:runid>/<config>/tasks/set_run_wepp_routine/', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_set_hourly_seepage(runid, config):
    payload = parse_request_payload(request, boolean_fields={'state'})

    routine = payload.get('routine')
    if routine is None:
        return error_factory('routine is None')

    routine = str(routine)
    if routine not in ['wepp_ui', 'wepp_watershed', 'pmet', 'frost', 'tcr', 'snow']:
        return error_factory("routine not in ['wepp_ui', 'wepp_watershed', 'pmet', 'frost', 'tcr', 'snow']")

    state = payload.get('state', None)
    if state is None:
        return error_factory('state is None')
    if isinstance(state, str):
        return error_factory('state must be boolean')

    try:
        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)

        if routine == 'wepp_ui':
            wepp.set_run_wepp_ui(bool(state))
        elif routine == 'wepp_watershed':
            wepp.set_run_wepp_watershed(bool(state))
        elif routine == 'pmet':
            wepp.set_run_pmet(bool(state))
        elif routine == 'frost':
            wepp.set_run_frost(bool(state))
        elif routine == 'tcr':
            wepp.set_run_tcr(bool(state))
        elif routine == 'snow':
            wepp.set_run_snow(bool(state))
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:459", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error setting state', runid=runid)

    return success_factory({'routine': routine, 'state': bool(state)})


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/results')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/results/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view WEPP reports.")
def report_wepp_results(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)
    
    try:
        prep = RedisPrep.getInstance(wd)
    except FileNotFoundError:
        prep = None

    has_results = _wepp_outputs_exist(wd, climate)
    wepp_results_stale = bool(prep is not None and has_results and _wepp_results_invalidated(prep))
    run_results_title = "Run Results" + (" (stale)" if wepp_results_stale else "")

    totalwatsed3_exists = _exists(
        _join(wd, 'wepp', 'output', 'interchange', 'totalwatsed3.parquet')
    )
    totalwatsed2_exists = _exists(
        _join(wd, 'wepp', 'output', 'totalwatsed2.parquet')
    )
    interchange_readme_exists = _exists(
        _join(wd, 'wepp', 'output', 'interchange', 'README.md')
    )
    storm_event_analyzer_ready = _exists(
        _join(wd, 'climate', 'wepp_cli_pds_mean_metric.csv')
    )
    prep_details_export_relpath = _resolve_published_export_relpath(wd, "prep-details")
    post_wepp_geopackage_export_relpath = _resolve_published_export_relpath(wd, "prep-wepp")
    post_wepp_geodatabase_export_relpath = _resolve_published_export_relpath(
        wd,
        "prep-wepp-geodatabase",
    )
    prep_details_export_download_url = (
        url_for_run(
            'wepp.download_features_export_published',
            runid=runid,
            config=config,
            profile='prep-details',
        )
        if prep_details_export_relpath
        else None
    )
    post_wepp_geopackage_export_download_url = (
        url_for_run(
            'wepp.download_features_export_published',
            runid=runid,
            config=config,
            profile='prep-wepp',
        )
        if post_wepp_geopackage_export_relpath
        else None
    )
    post_wepp_geodatabase_export_download_url = (
        url_for_run(
            'wepp.download_features_export_published',
            runid=runid,
            config=config,
            profile='prep-wepp-geodatabase',
        )
        if post_wepp_geodatabase_export_relpath
        else None
    )

    try:
        return render_template('controls/wepp_reports.htm',
                               climate=climate,
                               prep=prep,
                               runid=runid,
                               config=config,
                               run_results_title=run_results_title,
                               wepp_results_stale=wepp_results_stale,
                               totalwatsed3_exists=totalwatsed3_exists,
                               totalwatsed2_exists=totalwatsed2_exists,
                               interchange_readme_exists=interchange_readme_exists,
                               storm_event_analyzer_ready=storm_event_analyzer_ready,
                               prep_details_export_download_url=prep_details_export_download_url,
                               post_wepp_geopackage_export_download_url=post_wepp_geopackage_export_download_url,
                               post_wepp_geodatabase_export_download_url=post_wepp_geodatabase_export_download_url,
                               user=current_user)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:504", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error building reports template', runid=runid)


@wepp_bp.route('/runs/<string:runid>/<config>/download/features/published/<string:profile>')
@wepp_bp.route('/runs/<string:runid>/<config>/download/features/published/<string:profile>/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to download published features exports.")
def download_features_export_published(runid: str, config: str, profile: str):
    wd = get_wd(runid)
    try:
        artifact_path, _artifact_relpath = resolve_published_artifact_path(
            wd,
            profile=profile,
        )
        filename = _published_export_download_filename(runid, profile)
        return send_file(
            str(artifact_path),
            as_attachment=True,
            download_name=filename,
        )
    except FeaturesExportServiceError as exc:
        response = error_factory(str(exc), code=exc.code, details=exc.details)
        response.status_code = exc.status_code
        return response
    except FileNotFoundError as exc:
        response = error_factory(str(exc), code='not_found')
        response.status_code = 404
        return response


@wepp_bp.route('/runs/<string:runid>/<config>/report/rusle/results')
@wepp_bp.route('/runs/<string:runid>/<config>/report/rusle/results/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view RUSLE reports.")
def report_rusle_results(runid, config):
    wd = get_wd(runid)

    try:
        prep = RedisPrep.getInstance(wd)
    except FileNotFoundError:
        prep = None

    has_results = _rusle_outputs_exist(wd)
    if not has_results:
        return ""

    rusle_results_stale = bool(prep is not None and _rusle_results_invalidated(prep))
    run_results_title = "Run Results" + (" (stale)" if rusle_results_stale else "")

    rusle_manifest_exists = _exists(_join(wd, "rusle", "manifest.json"))
    rusle_readme_exists = _exists(_join(wd, "rusle", "README.md"))
    rusle_active_a_relpath = _resolve_rusle_active_a_relpath(wd)

    try:
        return render_template(
            "controls/rusle_reports.htm",
            runid=runid,
            config=config,
            run_results_title=run_results_title,
            rusle_results_stale=rusle_results_stale,
            rusle_manifest_exists=rusle_manifest_exists,
            rusle_readme_exists=rusle_readme_exists,
            rusle_active_a_relpath=rusle_active_a_relpath,
            user=current_user,
        )
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:557", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error building RUSLE reports template', runid=runid)



@wepp_bp.route('/runs/<string:runid>/<config>/query/subcatchments_summary')
@wepp_bp.route('/runs/<string:runid>/<config>/query/subcatchments_summary/')
@authorize_and_handle_with_exception_factory
def query_subcatchments_summary(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:
        subcatchments_summary = ron.subs_summary()

        return jsonify(subcatchments_summary)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:520", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error building summary', runid=runid)



@wepp_bp.route('/runs/<string:runid>/<config>/query/channels_summary')
@wepp_bp.route('/runs/<string:runid>/<config>/query/channels_summary/')
@authorize_and_handle_with_exception_factory
def query_channels_summary(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:
        channels_summary = ron.chns_summary()

        return jsonify(channels_summary)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:536", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error building summary', runid=runid)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/prep_details')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/prep_details/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view WEPP reports.")
def get_wepp_prep_details(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    subcatchments_summary = ron.subs_summary(abbreviated=True)
    channels_summary = ron.chns_summary(abbreviated=True)

    unitizer = Unitizer.getInstance(wd)
    disturbed_preview_context = _build_disturbed_preview_context(getattr(ron, "mods", ()))

    return render_template('reports/wepp/prep_details.htm', runid=runid, config=config,
                            unitizer_nodb=unitizer,
                            precisions=wepppy.nodb.unitizer.precisions,
                            subcatchments_summary=subcatchments_summary,
                            channels_summary=channels_summary,
                            user=current_user,
                            ron=ron,
                            **disturbed_preview_context)


@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/phosphorus_opts')
@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/phosphorus_opts/')
@authorize_and_handle_with_exception_factory
def query_wepp_phos_opts(runid, config):
    wd = get_wd(runid)
    phos_opts = Wepp.getInstance(wd).phosphorus_opts.asdict()
    return jsonify(phos_opts)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/run_summary')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/run_summary/')
@authorize_and_handle_with_exception_factory
def report_wepp_run_summary(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    subs_n = None
    interchange_path = _join(wd, "wepp/output/interchange/loss_pw0.hill.parquet")
    if _exists(interchange_path):
        try:
            import pyarrow.parquet as pq

            subs_n = pq.ParquetFile(interchange_path).metadata.num_rows
        except Exception:
            # Boundary catch: preserve contract behavior while logging unexpected failures.
            __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:585", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
            subs_n = None

    if subs_n is None:
        subs_n = len(glob(_join(wd, 'wepp/output/*.pass.dat')))
        subs_n += len(glob(_join(wd, 'wepp/output/*/*.pass.dat')))

    return render_template('reports/wepp_run_summary.htm', runid=runid, config=config,
                           subs_n=subs_n,
                           ron=ron)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/summary')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/summary/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view WEPP reports.")
def report_wepp_loss(runid, config):
    output_scope = _resolve_output_scope()
    if isinstance(output_scope, Response):
        return output_scope

    extraneous = request.args.get('extraneous', None) == 'true'

    wd = get_wd(runid)
    is_singlestorm = Climate.getInstance(wd).is_single_storm
    
    # Try to instantiate reports - they may fail if interchange files are missing
    try:
        out_rpt = OutletSummaryReport(wd, output_scope=output_scope)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:610", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        out_rpt = None
        
    try:
        hill_rpt = HillSummaryReport(wd, output_scope=output_scope)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:615", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        hill_rpt = None
        
    try:
        chn_rpt = ChannelSummaryReport(wd, output_scope=output_scope)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:620", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        chn_rpt = None
    
    unitizer = Unitizer.getInstance(wd)
    ron = Ron.getInstance(wd)

    if _wants_csv():
        if out_rpt is None:
            abort(400, description="CSV export not available - reports not generated")
        table_key = (request.args.get('table') or 'outlet').lower()
        if table_key == 'outlet':
            df = _build_outlet_summary_dataframe(out_rpt, unitizer, include_extraneous=extraneous)
            return _render_dataframe_csv(
                runid=runid,
                df=df,
                slug="summary",
                table=table_key,
            )
        elif table_key == 'hillslopes':
            if hill_rpt is None:
                abort(400, description="Hillslopes report not available")
            return _render_report_csv(
                runid=runid,
                report=hill_rpt,
                unitizer=unitizer,
                slug="summary",
                table=table_key,
            )
        elif table_key == 'channels':
            if chn_rpt is None:
                abort(400, description="Channels report not available")
            return _render_report_csv(
                runid=runid,
                report=chn_rpt,
                unitizer=unitizer,
                slug="summary",
                table=table_key,
            )
        else:
            abort(400, description=f"Unknown summary table '{table_key}'")

    return render_template(
        'reports/wepp/summary.htm',
        runid=runid,
        config=config,
        ron=ron,
        current_ron=RonViewModel(ron),
        extraneous=extraneous,
        out_rpt=out_rpt,
        hill_rpt=hill_rpt,
        chn_rpt=chn_rpt,
        unitizer_nodb=unitizer,
        precisions=wepppy.nodb.unitizer.precisions,
        is_singlestorm=is_singlestorm,
        output_scope=output_scope,
        user=current_user,
    )


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/yearly_watbal')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/yearly_watbal/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view WEPP reports.")
def report_wepp_yearly_watbal(runid, config):
    output_scope = _resolve_output_scope()
    if isinstance(output_scope, Response):
        return output_scope

    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:690", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        exclude_yr_indxs = [0, 1]

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    totwatbal = TotalWatbalReport(wd, exclude_yr_indxs=exclude_yr_indxs, output_scope=output_scope)

    unitizer = Unitizer.getInstance(wd)

    if _wants_csv():
        return _render_report_csv(
            runid=runid,
            report=totwatbal,
            unitizer=unitizer,
            slug="yearly_watbal",
            table="yearly",
        )

    return render_template('reports/wepp/yearly_watbal.htm', runid=runid, config=config,
                            unitizer_nodb=unitizer,
                            precisions=wepppy.nodb.unitizer.precisions,
                            rpt=totwatbal,
                            exclude_yr_indxs=exclude_yr_indxs,
                            output_scope=output_scope,
                            ron=ron,
                            user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/avg_annual_by_landuse')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/avg_annual_by_landuse/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view WEPP reports.")
def report_wepp_avg_annual_by_landuse(runid, config):
    from wepppy.wepp.reports import AverageAnnualsByLanduseReport
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    wepp = Wepp.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)
    report = AverageAnnualsByLanduseReport(wd)

    if _wants_csv():
        return _render_report_csv(
            runid=runid,
            report=report,
            unitizer=unitizer,
            slug="avg_annuals_by_landuse",
            table=request.args.get('table')
        )

    return render_template('reports/wepp/avg_annuals_by_landuse.htm', runid=runid, config=config,
                        unitizer_nodb=unitizer,
                        precisions=wepppy.nodb.unitizer.precisions,
                        report=report,
                        ron=ron,
                        user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/avg_annual_watbal')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/avg_annual_watbal/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view WEPP reports.")
def report_wepp_avg_annual_watbal(runid, config):
    output_scope = _resolve_output_scope()
    if isinstance(output_scope, Response):
        return output_scope

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    hill_rpt = wepp.report_hill_watbal(output_scope=output_scope)
    chn_rpt = None
    try:
        chn_rpt = wepp.report_chn_watbal(output_scope=output_scope)
    except FileNotFoundError:
        chn_rpt = None

    unitizer = Unitizer.getInstance(wd)

    if _wants_csv():
        table_key = (request.args.get('table') or 'hillslopes').lower()
        reports = {
            'hillslopes': hill_rpt,
        }
        if chn_rpt is not None:
            reports['channels'] = chn_rpt
        report_obj = reports.get(table_key)
        if report_obj is None:
            abort(400, description=f"Unknown water balance table '{table_key}'")
        return _render_report_csv(
            runid=runid,
            report=report_obj,
            unitizer=unitizer,
            slug="avg_annual_watbal",
            table=table_key,
        )

    return render_template('reports/wepp/avg_annual_watbal.htm', runid=runid, config=config,
                            unitizer_nodb=unitizer,
                            precisions=wepppy.nodb.unitizer.precisions,
                            hill_rpt=hill_rpt,
                            chn_rpt=chn_rpt,
                            output_scope=output_scope,
                            ron=ron,
                            user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/plot/wepp/streamflow')
@wepp_bp.route('/runs/<string:runid>/<config>/plot/wepp/streamflow/')
@authorize_and_handle_with_exception_factory
def plot_wepp_streamflow(runid, config):
    output_scope = _resolve_output_scope()
    if isinstance(output_scope, Response):
        return output_scope

    res = request.args.get('exclude_yr_indxs')
    if res:
        exclude_yr_indxs = [int(yr) for yr in res.split(',') if isint(yr)]
    else:
        exclude_yr_indxs = [0, 1]

    wd = get_wd(runid)
    stream_rel_path = scoped_dataset_path('wepp/output/interchange/totalwatsed3.parquet', output_scope)
    stream_parquet = _join(wd, stream_rel_path)
    if not _exists(stream_parquet):
        return error_factory('totalwatsed3.parquet is not available; please run the WEPP interchange workflow first.')

    try:
        run_context = resolve_run_context(wd, auto_activate=True, run_interchange=False)
    except FileNotFoundError:
        return error_factory('Unable to resolve query engine catalog for this run')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:812", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error activating query engine', runid=runid)

    payload_dict = {
        "datasets": [
            {
                "path": stream_rel_path,
                "alias": "stream",
            }
        ],
        "columns": [
            "stream.year AS year",
            "stream.\"Precipitation\"",
            "stream.\"Rain+Melt\"",
            "stream.\"Lateral Flow\"",
            "stream.Baseflow",
            "stream.Runoff",
        ],
        "computed_columns": [
            {
                "alias": "flow_date",
                "sql": _daily_simulation_date_sql("stream"),
            }
        ],
        "order_by": ["flow_date"],
        "include_schema": True,
        "include_sql": True,
        "reshape": {
            "type": "timeseries",
            "index": {"column": "flow_date", "key": "date"},
            "year_column": "year",
            "exclude_year_indexes": exclude_yr_indxs,
            "series": [
                {"column": "Baseflow", "key": "baseflow", "label": "Baseflow", "group": "flow", "color": "#1e90ff", "units": "mm", "description": "Daily baseflow depth"},
                {"column": "Lateral Flow", "key": "lateral_flow", "label": "Lateral Flow", "group": "flow", "color": "#32cd32", "units": "mm", "description": "Daily lateral flow depth"},
                {"column": "Runoff", "key": "runoff", "label": "Runoff", "group": "flow", "color": "#FF3B30", "units": "mm", "description": "Daily runoff depth"},
                {"column": "Precipitation", "key": "precipitation", "label": "Precipitation", "group": "meteo", "role": "precip", "color": "#FF6F30", "units": "mm", "description": "Daily precipitation depth"},
                {"column": "Rain+Melt", "key": "rain_melt", "label": "Rain + Melt", "group": "meteo", "role": "rain_melt", "color": "#00B2A9", "units": "mm", "description": "Daily rain plus melt depth"},
            ],
            "compact": True,
        },
    }

    try:
        query = QueryRequest(**payload_dict)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:861", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Invalid streamflow query payload', runid=runid)

    try:
        result = run_query(run_context, query)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:866", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error running streamflow query', runid=runid)

    if result.formatted is None:
        return error_factory('Streamflow query did not produce a timeseries payload')

    try:
        timeseries_json = json.dumps(result.formatted, ensure_ascii=False)
        payload_json = json.dumps(payload_dict, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        return exception_factory('Error serializing query engine response', runid=runid)

    ron = Ron.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)
    return render_template(
        'reports/wepp/daily_streamflow_graph.htm',
        runid=runid,
        config=config,
        unitizer_nodb=unitizer,
        precisions=wepppy.nodb.unitizer.precisions,
        exclude_yr_indxs=exclude_yr_indxs,
        exclude_yr_indxs_csv=','.join(str(yr) for yr in exclude_yr_indxs),
        output_scope=output_scope,
        streamflow_data_json=timeseries_json,
        streamflow_query_json=payload_json,
        streamflow_sql=result.sql,
        ron=ron,
        user=current_user,
    )


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/return_periods')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/return_periods/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view WEPP reports.")
def report_wepp_return_periods(runid, config):
    output_scope = _resolve_output_scope()
    if isinstance(output_scope, Response):
        return output_scope

    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:907", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        exclude_yr_indxs = None

    try:
        res = request.args.get('exclude_months')
        exclude_months = []
        for month in res.split(','):
            if isint(month):
                exclude_months.append(int(month))
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:916", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        exclude_months = None

    # get method and gringorten_correction
    # method default is cta gringorten_correction default is False
    method = request.args.get('method', 'cta')
    if method not in ['cta', 'am']:
        return error_factory('method must be either cta or am')
    
    gringorten_correction = request.args.get('gringorten_correction', 'false').lower() == 'true'

    extraneous = request.args.get('extraneous', None) == 'true'

    chn_topaz_id_of_interest = request.args.get('chn_topaz_id_of_interest', None)
    if chn_topaz_id_of_interest is not None:
        chn_topaz_id_of_interest = int(chn_topaz_id_of_interest)

    wd = get_wd(runid)

    climate = Climate.getInstance(wd)
    rec_intervals = parse_rec_intervals(request, climate.years)

    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    report = wepp.report_return_periods(
        rec_intervals=rec_intervals, 
        exclude_yr_indxs=exclude_yr_indxs,
        method=method, 
        gringorten_correction=gringorten_correction, 
        exclude_months=exclude_months,
        chn_topaz_id_of_interest=chn_topaz_id_of_interest,
        wait_for_inputs=False,
        output_scope=output_scope,
    )

    translator = Watershed.getInstance(wd).translator_factory()
    unitizer = Unitizer.getInstance(wd)

    measure_order = [key for key in _RETURN_PERIOD_METRIC_ORDER if key in report.return_periods]
    for key in report.return_periods.keys():
        if key not in measure_order:
            measure_order.append(key)

    slug_map = { _slugify_return_period_key(key): key for key in measure_order }

    if _wants_csv():
        if not slug_map:
            abort(404, description="No return period data available")
        table_slug = (request.args.get('table') or '').lower()
        if not table_slug:
            table_slug = next(iter(slug_map.keys()), None)
        metric_key = slug_map.get(table_slug)
        if metric_key is None:
            abort(400, description=f"Unknown return period table '{table_slug}'")

        if extraneous:
            df = _build_return_period_extraneous_dataframe(report, metric_key, unitizer)
        else:
            df = _build_return_period_simple_dataframe(report, metric_key, unitizer)

        if df.empty:
            abort(404, description="No return period data available for requested table")

        return _render_dataframe_csv(
            runid=runid,
            df=df,
            slug="return_periods",
            table=table_slug,
        )

    return render_template('reports/wepp/return_periods.htm', runid=runid, config=config,
                            extraneous=extraneous,
                            chn_topaz_id_of_interest=chn_topaz_id_of_interest,
                            chn_topaz_id_options=wepp.chn_topaz_ids_of_interest,
                            gringorten_correction=gringorten_correction,
                            unitizer_nodb=unitizer,
                            precisions=wepppy.nodb.unitizer.precisions,
                            report=report,
                            translator=translator,
                            ron=ron,
                            user=current_user,
                            measure_order=measure_order,
                            method=method,
                            exclude_yr_indxs=exclude_yr_indxs,
                            exclude_months=exclude_months,
                            output_scope=output_scope)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/frq_flood')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/frq_flood/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view WEPP reports.")
def report_wepp_frq_flood(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    report = Wepp.getInstance(wd).report_frq_flood()
    translator = Watershed.getInstance(wd).translator_factory()

    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/frq_flood.htm', runid=runid, config=config,
                            unitizer_nodb=unitizer,
                            precisions=wepppy.nodb.unitizer.precisions,
                            report=report,
                            translator=translator,
                            ron=ron,
                            user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/sediment_characteristics')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/sediment_characteristics/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view WEPP reports.")
def report_wepp_sediment_delivery(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    sediment = Wepp.getInstance(wd).report_sediment_delivery()
    translator = Watershed.getInstance(wd).translator_factory()

    unitizer = Unitizer.getInstance(wd)

    if _wants_csv():
        table_key = request.args.get('table') or 'class-info'
        reports = {
            'class-info': sediment.class_info_report,
            'channel-class-fractions': sediment.channel.class_fraction_report,
            'channel-particles': sediment.channel.particle_distribution_report,
            'hill-class-fractions': sediment.hillslope.class_fraction_report,
            'hill-particles': sediment.hillslope.particle_distribution_report,
        }
        report = reports.get(table_key)
        if report is None:
            abort(400, description=f"Unknown sediment characteristics table '{table_key}'")

        return _render_report_csv(
            runid=runid,
            report=report,
            unitizer=unitizer,
            slug="sediment_characteristics",
            table=table_key,
        )

    return render_template('reports/wepp/sediment_characteristics.htm', runid=runid, config=config,
                            unitizer_nodb=unitizer,
                            precisions=wepppy.nodb.unitizer.precisions,
                            sediment=sediment,
                            translator=translator,
                            ron=ron,
                            user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/phosphorus/subcatchments')
@wepp_bp.route('/runs/<string:runid>/<config>/query/wepp/phosphorus/subcatchments/')
@authorize_and_handle_with_exception_factory
def query_wepp_sub_phosphorus(runid, config):
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('Total P Density'))


@wepp_bp.route('/runs/<string:runid>/<config>/query/chn_summary/<topaz_id>')
@wepp_bp.route('/runs/<string:runid>/<config>/query/chn_summary/<topaz_id>/')
@authorize_and_handle_with_exception_factory
def query_ron_chn_summary(runid, config, topaz_id):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    return jsonify(ron.chn_summary(topaz_id))


@wepp_bp.route('/runs/<string:runid>/<config>/query/sub_summary/<topaz_id>')
@wepp_bp.route('/runs/<string:runid>/<config>/query/sub_summary/<topaz_id>/')
@authorize_and_handle_with_exception_factory
def query_ron_sub_summary(runid, config, topaz_id):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        return jsonify(ron.sub_summary(topaz_id))
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:1091", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory(runid=runid)


@wepp_bp.route('/runs/<string:runid>/<config>/report/chn_summary/<topaz_id>')
@wepp_bp.route('/runs/<string:runid>/<config>/report/chn_summary/<topaz_id>/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view WEPP reports.")
def report_ron_chn_summary(runid, config, topaz_id):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        disturbed_preview_context = _build_disturbed_preview_context(getattr(ron, "mods", ()))
        return render_template('reports/hill.htm', runid=runid, config=config,
                            ron=ron,
                            d=ron.chn_summary(topaz_id),
                            **disturbed_preview_context)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:1106", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory(runid=runid)


@wepp_bp.route('/runs/<string:runid>/<config>/query/topaz_wepp_map')
@wepp_bp.route('/runs/<string:runid>/<config>/query/topaz_wepp_map/')
@authorize_and_handle_with_exception_factory
def query_topaz_wepp_map(runid, config):
    wd = get_wd(runid)
    translator = Watershed.getInstance(wd).translator_factory()

    d = dict([(wepp, translator.top(wepp=wepp)) for wepp in translator.iter_wepp_sub_ids()])

    return jsonify(d)




@wepp_bp.route('/runs/<string:runid>/<config>/report/sub_summary/<topaz_id>')
@wepp_bp.route('/runs/<string:runid>/<config>/report/sub_summary/<topaz_id>/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view WEPP reports.")
def report_ron_sub_summary(runid, config, topaz_id):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    disturbed_preview_context = _build_disturbed_preview_context(getattr(ron, "mods", ()))
    return render_template('reports/hill.htm', runid=runid, config=config,
                           ron=ron,
                           d=ron.sub_summary(topaz_id),
                           **disturbed_preview_context)


@wepp_bp.route('/runs/<string:runid>/<config>/resources/wepp_loss.tif')
@authorize_and_handle_with_exception_factory
def resources_wepp_loss(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        loss_grid_wgs = _join(ron.plot_dir, 'loss.WGS.tif')

        if _exists(loss_grid_wgs):
            return send_file(loss_grid_wgs, mimetype='image/tiff')

        return error_factory('loss_grid_wgs does not exist')

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:1149", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory(runid=runid)

@wepp_bp.route('/runs/<string:runid>/<config>/query/bound_coords')
@wepp_bp.route('/runs/<string:runid>/<config>/query/bound_coords/')
@authorize_and_handle_with_exception_factory
def query_bound_coords(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        bound_wgs_json = _join(ron.topaz_wd, 'BOUND.WGS.JSON')

        if _exists(bound_wgs_json):
            with open(bound_wgs_json) as fp:
                js = json.load(fp)
                coords = js['features'][0]['geometry']['coordinates'][0]
                coords = [ll[::-1] for ll in coords]

                return success_factory(coords)

        return error_factory('Could not determine coords')

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/wepp_bp.py:1189", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory(runid=runid)
