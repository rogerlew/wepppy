"""Routes for wepp blueprint extracted from app.py."""

import io
import re
from datetime import datetime

import pandas as pd
import wepppy

from .._common import *  # noqa: F401,F403

from wepppy.all_your_base import isint
from wepppy.nodb.core import Landuse, Ron, Climate, Watershed, Wepp
from wepppy.nodb.unitizer import Unitizer, precisions, converters
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.wepp import management
from wepppy.wepp.reports import ChannelSummaryReport, HillSummaryReport, OutletSummaryReport
from wepppy.wepp.reports import TotalWatbalReport
from wepppy.wepp.reports.report_base import ReportBase
from wepppy.wepp.reports.row_data import parse_name, parse_units
from wepppy.weppcloud.utils.helpers import (error_factory, exception_factory, parse_rec_intervals, authorize_and_handle_with_exception_factory)
import json
from wepppy.query_engine import activate_query_engine, resolve_run_context, run_query
from wepppy.query_engine.payload import QueryRequest
from flask import Response, abort

wepp_bp = Blueprint('wepp', __name__)


def _wants_csv() -> bool:
    fmt = (request.args.get('format') or '').lower()
    if fmt == 'csv':
        return True
    accept = request.headers.get('Accept', '')
    return 'text/csv' in accept.lower()


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
        try:
            return converter(value)
        except Exception:
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


@wepp_bp.route('/runs/<string:runid>/<config>/tasks/set_run_wepp_routine', methods=['POST'])
@wepp_bp.route('/runs/<string:runid>/<config>/tasks/set_run_wepp_routine/', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_set_hourly_seepage(runid, config):
    payload = parse_request_payload(request, boolean_fields={'state'})

    routine = payload.get('routine')
    if routine is None:
        return error_factory('routine is None')

    routine = str(routine)
    if routine not in ['wepp_ui', 'pmet', 'frost', 'tcr', 'snow', 'run_flowpaths']:
        return error_factory("routine not in ['wepp_ui', 'pmet', 'frost', 'tcr', 'snow', 'run_flowpaths']")

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
        elif routine == 'pmet':
            wepp.set_run_pmet(bool(state))
        elif routine == 'frost':
            wepp.set_run_frost(bool(state))
        elif routine == 'tcr':
            wepp.set_run_tcr(bool(state))
        elif routine == 'snow':
            wepp.set_run_snow(bool(state))
        elif routine == 'run_flowpaths':
            wepp.set_run_flowpaths(bool(state))

    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory({'routine': routine, 'state': bool(state)})


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/results')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/results/')
@authorize_and_handle_with_exception_factory
def report_wepp_results(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)
    
    try:
        prep = RedisPrep.getInstance(wd)
    except FileNotFoundError:
        prep = None

    try:
        return render_template('controls/wepp_reports.htm',
                               climate=climate,
                               prep=prep,
                               runid=runid,
                               config=config,
                               user=current_user)
    except:
        return exception_factory('Error building reports template', runid=runid)



@wepp_bp.route('/runs/<string:runid>/<config>/query/subcatchments_summary')
@wepp_bp.route('/runs/<string:runid>/<config>/query/subcatchments_summary/')
@authorize_and_handle_with_exception_factory
def query_subcatchments_summary(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:
        subcatchments_summary = ron.subs_summary()

        return jsonify(subcatchments_summary)
    except:
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
    except:
        return exception_factory('Error building summary', runid=runid)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/prep_details')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/prep_details/')
@authorize_and_handle_with_exception_factory
def get_wepp_prep_details(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    subcatchments_summary = ron.subs_summary(abbreviated=True)
    channels_summary = ron.chns_summary(abbreviated=True)

    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/prep_details.htm', runid=runid, config=config,
                            unitizer_nodb=unitizer,
                            precisions=wepppy.nodb.unitizer.precisions,
                            subcatchments_summary=subcatchments_summary,
                            channels_summary=channels_summary,
                            user=current_user,
                            ron=ron)


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

    flowpaths_n = len(glob(_join(wd, 'wepp/flowpaths/output/*.plot.dat')))
    subs_n = len(glob(_join(wd, 'wepp/output/*.pass.dat')))
    subs_n += len(glob(_join(wd, 'wepp/output/*/*.pass.dat')))

    return render_template('reports/wepp_run_summary.htm', runid=runid, config=config,
                           flowpaths_n=flowpaths_n,
                           subs_n=subs_n,
                           ron=ron)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/summary')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/summary/')
@authorize_and_handle_with_exception_factory
def report_wepp_loss(runid, config):
    extraneous = request.args.get('extraneous', None) == 'true'

    wd = get_wd(runid)
    is_singlestorm = Climate.getInstance(wd).is_single_storm
    
    # Try to instantiate reports - they may fail if interchange files are missing
    try:
        out_rpt = OutletSummaryReport(wd)
    except Exception:
        out_rpt = None
        
    try:
        hill_rpt = HillSummaryReport(wd)
    except Exception:
        hill_rpt = None
        
    try:
        chn_rpt = ChannelSummaryReport(wd)
    except Exception:
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
        current_ron=ron,
        extraneous=extraneous,
        out_rpt=out_rpt,
        hill_rpt=hill_rpt,
        chn_rpt=chn_rpt,
        unitizer_nodb=unitizer,
        precisions=wepppy.nodb.unitizer.precisions,
        is_singlestorm=is_singlestorm,
        user=current_user,
    )


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/yearly_watbal')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/yearly_watbal/')
@authorize_and_handle_with_exception_factory
def report_wepp_yearly_watbal(runid, config):
    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))

    except:
        exclude_yr_indxs = [0, 1]

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    totwatbal = TotalWatbalReport(wd, exclude_yr_indxs=exclude_yr_indxs)

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
                            ron=ron,
                            user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/avg_annual_by_landuse')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/avg_annual_by_landuse/')
@authorize_and_handle_with_exception_factory
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
def report_wepp_avg_annual_watbal(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    hill_rpt = wepp.report_hill_watbal()
    chn_rpt = None
    try:
        chn_rpt = wepp.report_chn_watbal()
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
                            ron=ron,
                            user=current_user)


@wepp_bp.route('/runs/<string:runid>/<config>/plot/wepp/streamflow')
@wepp_bp.route('/runs/<string:runid>/<config>/plot/wepp/streamflow/')
@authorize_and_handle_with_exception_factory
def plot_wepp_streamflow(runid, config):
    res = request.args.get('exclude_yr_indxs')
    if res:
        exclude_yr_indxs = [int(yr) for yr in res.split(',') if isint(yr)]
    else:
        exclude_yr_indxs = [0, 1]

    wd = get_wd(runid)
    stream_rel_path = 'wepp/output/interchange/totalwatsed3.parquet'
    stream_parquet = _join(wd, stream_rel_path)
    if not _exists(stream_parquet):
        return error_factory('totalwatsed3.parquet is not available; please run the WEPP interchange workflow first.')

    try:
        activate_query_engine(wd, run_interchange=False)
        run_context = resolve_run_context(wd, auto_activate=False)
    except FileNotFoundError:
        return error_factory('Unable to resolve query engine catalog for this run')
    except Exception:
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
                "date_parts": {
                    "year": "stream.year",
                    "month": "stream.month",
                    "day": "stream.day_of_month",
                },
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
                {"column": "Runoff", "key": "runoff", "label": "Runoff", "group": "flow", "color": "#FF3B30", "units": "mm", "description": "Daily runoff depth"},
                {"column": "Baseflow", "key": "baseflow", "label": "Baseflow", "group": "flow", "color": "#1e90ff", "units": "mm", "description": "Daily baseflow depth"},
                {"column": "Lateral Flow", "key": "lateral_flow", "label": "Lateral Flow", "group": "flow", "color": "#32cd32", "units": "mm", "description": "Daily lateral flow depth"},
                {"column": "Precipitation", "key": "precipitation", "label": "Precipitation", "group": "meteo", "role": "precip", "color": "#FF6F30", "units": "mm", "description": "Daily precipitation depth"},
                {"column": "Rain+Melt", "key": "rain_melt", "label": "Rain + Melt", "group": "meteo", "role": "rain_melt", "color": "#00B2A9", "units": "mm", "description": "Daily rain plus melt depth"},
            ],
            "compact": True,
        },
    }

    try:
        query = QueryRequest(**payload_dict)
    except Exception:
        return exception_factory('Invalid streamflow query payload', runid=runid)

    try:
        result = run_query(run_context, query)
    except Exception:
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
        streamflow_data_json=timeseries_json,
        streamflow_query_json=payload_json,
        streamflow_sql=result.sql,
        ron=ron,
        user=current_user,
    )


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/return_periods')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/return_periods/')
@authorize_and_handle_with_exception_factory
def report_wepp_return_periods(runid, config):
    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))
    except:
        exclude_yr_indxs = None

    try:
        res = request.args.get('exclude_months')
        exclude_months = []
        for month in res.split(','):
            if isint(month):
                exclude_months.append(int(month))
    except:
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
        chn_topaz_id_of_interest=chn_topaz_id_of_interest
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
                            exclude_months=exclude_months)


@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/frq_flood')
@wepp_bp.route('/runs/<string:runid>/<config>/report/wepp/frq_flood/')
@authorize_and_handle_with_exception_factory
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
        return exception_factory(runid=runid)


@wepp_bp.route('/runs/<string:runid>/<config>/report/chn_summary/<topaz_id>')
@wepp_bp.route('/runs/<string:runid>/<config>/report/chn_summary/<topaz_id>/')
@authorize_and_handle_with_exception_factory
def report_ron_chn_summary(runid, config, topaz_id):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        return render_template('reports/hill.htm', runid=runid, config=config,
                            ron=ron,
                            d=ron.chn_summary(topaz_id))
    except Exception:
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
def report_ron_sub_summary(runid, config, topaz_id):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    return render_template('reports/hill.htm', runid=runid, config=config,
                           ron=ron,
                           d=ron.sub_summary(topaz_id))


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
        return exception_factory(runid=runid)


@wepp_bp.route('/runs/<string:runid>/<config>/resources/flowpaths_loss.tif')
@authorize_and_handle_with_exception_factory
def resources_flowpaths_loss(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        loss_grid_wgs = _join(ron.plot_dir, 'flowpaths_loss.WGS.tif')

        if _exists(loss_grid_wgs):
            return send_file(loss_grid_wgs, mimetype='image/tiff')

        return error_factory('loss_grid_wgs does not exist')

    except Exception:
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
        return exception_factory(runid=runid)
