"""Routes for landuse blueprint extracted from app.py."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

from flask import Response

from .._common import Blueprint, jsonify, parse_request_payload, render_template, request
from .._common import exception_factory, get_wd, success_factory  # noqa: F401

from wepppy.nodb.core import Landuse, LanduseMode, Ron


landuse_bp = Blueprint('landuse', __name__)


def _coerce_landuse_code(value: Any) -> str:
    if value in (None, ''):
        raise ValueError('landuse missing')
    try:
        return str(int(value))
    except (TypeError, ValueError) as exc:
        raise ValueError('landuse must be an integer value') from exc


def _iter_values(raw: Any) -> Iterable[Any]:
    if isinstance(raw, str):
        yield from (segment.strip() for segment in raw.split(','))
        return
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
        for item in raw:
            if item in (None, ''):
                continue
            if isinstance(item, str):
                yield from (segment.strip() for segment in item.split(','))
            else:
                yield item
        return
    if raw not in (None, ''):
        yield raw


def _coerce_topaz_ids(raw: Any) -> List[str]:
    candidate_ids: List[str] = []
    for value in _iter_values(raw):
        if value in (None, ''):
            continue
        try:
            candidate_ids.append(str(int(value)))
        except (TypeError, ValueError) as exc:
            raise ValueError(f'invalid topaz id: {value!r}') from exc
    return candidate_ids


def build_landuse_report_context(landuse: Landuse) -> Dict[str, object]:
    """Prepare dataset options and report rows for landuse summaries."""
    dataset_source = getattr(landuse, "available_datasets", [])
    datasets = [
        dataset
        for dataset in dataset_source
        if getattr(dataset, "kind", None) == "mapping"
    ]

    dataset_options: List[Tuple[str, str]] = []
    for dataset in datasets:
        key = getattr(dataset, "key", "")
        label = getattr(dataset, "label", key)
        description = getattr(dataset, "description", "")
        management_file = getattr(dataset, "management_file", "")
        if description and management_file:
            label = f"{description} ({management_file})"
        dataset_options.append((key, label))

    prefix_order = sorted(datasets, key=lambda ds: len(ds.key), reverse=True)
    report_rows: List[Dict[str, object]] = []

    report_source = getattr(landuse, "report", [])
    if isinstance(report_source, Mapping):
        report_entries = list(report_source.get("rows", []))
    else:
        try:
            report_entries = list(report_source)
        except TypeError:
            report_entries = []

    for entry in report_entries:
        row = dict(entry)
        key_str = str(row.get('key', ''))
        selected_dataset = next((ds for ds in prefix_order if key_str.startswith(ds.key)), None)
        row['_dataset'] = selected_dataset
        row['_dataset_key'] = selected_dataset.key if selected_dataset else None
        report_rows.append(row)

    return {
        'dataset_options': dataset_options,
        'coverage_percentages': getattr(landuse, "coverage_percentages", ()),
        'report_rows': report_rows,
    }


@landuse_bp.route('/runs/<string:runid>/<config>/tasks/set_landuse_mode/', methods=['POST'])
def set_landuse_mode(runid: str, config: str) -> Response:
    """Update landuse mode and single selection for the active run."""
    payload = parse_request_payload(request)

    try:
        mode_raw = payload.get('mode', None)
        mode = int(mode_raw) if mode_raw is not None else None
        single_selection = payload.get('landuse_single_selection', None)
    except (TypeError, ValueError):
        return exception_factory('mode and landuse_single_selection must be provided', runid=runid)

    if mode is None:
        return exception_factory('mode and landuse_single_selection must be provided', runid=runid)

    if single_selection is None:
        return success_factory()

    wd = get_wd(runid)
    landuse = Landuse.getInstance(wd)

    try:
        landuse.mode = LanduseMode(mode)
        landuse.single_selection = str(single_selection)
    except Exception as exc:
        del exc  # explicit discard to silence linters while preserving behaviour
        return exception_factory('error setting landuse mode', runid=runid)

    return success_factory()


@landuse_bp.route('/runs/<string:runid>/<config>/tasks/set_landuse_db/', methods=['POST'])
def set_landuse_db(runid: str, config: str) -> Response:
    """Persist NLCD database selection for the landuse controller."""
    payload = parse_request_payload(request)
    db = payload.get('landuse_db', None)

    if db is None:
        return exception_factory('landuse_db must be provided', runid=runid)

    wd = get_wd(runid)
    landuse = Landuse.getInstance(wd)

    try:
        landuse.nlcd_db = db
    except Exception:
        return exception_factory('error setting landuse mode', runid=runid)

    return success_factory()


@landuse_bp.route('/runs/<string:runid>/<config>/tasks/modify_landuse_coverage', methods=['POST'])
@landuse_bp.route('/runs/<string:runid>/<config>/tasks/modify_landuse_coverage/', methods=['POST'])
def modify_landuse_coverage(runid: str, config: str) -> Response:
    """Adjust coverage percentages for a given domain and cover class."""
    wd = get_wd(runid)

    payload = parse_request_payload(request)
    dom = payload.get('dom')
    cover = payload.get('cover')
    value = payload.get('value')

    if dom is None or cover is None or value is None:
        return exception_factory('dom, cover, and value must be provided', runid=runid)

    try:
        Landuse.getInstance(wd).modify_coverage(str(dom), str(cover), float(value))
    except Exception:
        return exception_factory('Failed to modify landuse coverage', runid=runid)

    return success_factory()


@landuse_bp.route('/runs/<string:runid>/<config>/tasks/modify_landuse_mapping/', methods=['POST'])
def task_modify_landuse_mapping(runid: str, config: str) -> Response:
    """Re-map domain identifiers in the landuse controller."""
    wd = get_wd(runid)

    payload = parse_request_payload(request)
    dom = payload.get('dom', None)
    newdom = payload.get('newdom', None)

    if dom is None or newdom is None:
        return exception_factory('dom and newdom must be provided', runid=runid)

    landuse = Landuse.getInstance(wd)
    try:
        landuse.modify_mapping(str(dom), str(newdom))
    except Exception:
        return exception_factory('Failed to modify landuse mapping', runid=runid)

    return success_factory()


@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse')
@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse/')
def query_landuse(runid: str, config: str) -> Response:
    """Return the landuse domain metadata dictionary."""
    wd = get_wd(runid)
    return jsonify(Landuse.getInstance(wd).domlc_d)


@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse/subcatchments')
@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse/subcatchments/')
def query_landuse_subcatchments(runid: str, config: str) -> Response:
    """Return subcatchment summary table for landuse."""
    wd = get_wd(runid)
    return jsonify(Landuse.getInstance(wd).subs_summary)


@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse/channels')
@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse/channels/')
def query_landuse_channels(runid: str, config: str) -> Response:
    """Return channel summary table for landuse."""
    wd = get_wd(runid)
    return jsonify(Landuse.getInstance(wd).chns_summary)


@landuse_bp.route('/runs/<string:runid>/<config>/report/landuse')
@landuse_bp.route('/runs/<string:runid>/<config>/report/landuse/')
def report_landuse(runid: str, config: str) -> Response:
    """Render the HTML landuse report for the current run."""
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:
        landuse = Landuse.getInstance(wd)
        landuseoptions = landuse.landuseoptions
        report_context = build_landuse_report_context(landuse)

        return render_template(
            'reports/landuse.htm',
            runid=runid,
            config=config,
            landuse=landuse,
            landuseoptions=landuseoptions,
            dataset_options=report_context['dataset_options'],
            coverage_percentages=report_context['coverage_percentages'],
            report=report_context['report_rows'],
        )

    except Exception:
        return exception_factory('Reporting landuse failed', runid=runid)


@landuse_bp.route('/runs/<string:runid>/<config>/tasks/modify_landuse/', methods=['POST'])
def task_modify_landuse(runid: str, config: str) -> Response:
    """Bulk modify landuse codes for the supplied Topaz identifiers."""
    wd = get_wd(runid)
    landuse = Landuse.getInstance(wd)

    try:
        payload = parse_request_payload(request)
        topaz_ids = _coerce_topaz_ids(payload.get('topaz_ids'))
        lccode = _coerce_landuse_code(payload.get('landuse'))
    except Exception as exc:
        message = 'Unpacking Modify Landuse Args Failed'
        detail = str(exc).strip()
        if detail:
            message = f'{message}: {detail}'
        return exception_factory(message, runid=runid)

    try:
        landuse.modify(topaz_ids, lccode)
    except Exception:
        return exception_factory('Modifying Landuse Failed', runid=runid)

    return success_factory()


@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse/cover/subcatchments')
@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse/cover/subcatchments/')
def query_landuse_cover_subcatchments(runid: str, config: str) -> Response:
    """Return coverage summaries for hillslope landuse."""
    wd = get_wd(runid)
    d = Landuse.getInstance(wd).hillslope_cancovs
    return jsonify(d)
