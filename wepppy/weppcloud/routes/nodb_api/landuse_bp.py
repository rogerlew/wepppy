"""Routes for landuse blueprint extracted from app.py."""

from __future__ import annotations

from typing import Iterable, List, Mapping, MutableMapping, Sequence

from flask import Response

from .._common import Blueprint, jsonify, render_template, request
from .._common import exception_factory, get_wd, success_factory  # noqa: F401

from wepppy.nodb.core import Landuse, LanduseMode, Ron


landuse_bp = Blueprint('landuse', __name__)


@landuse_bp.route('/runs/<string:runid>/<config>/tasks/set_landuse_mode/', methods=['POST'])
def set_landuse_mode(runid: str, config: str) -> Response:
    """Update landuse mode and single selection for the active run."""
    try:
        mode = int(request.form.get('mode', None))
        single_selection = request.form.get('landuse_single_selection', None)
    except Exception:
        return exception_factory('mode and landuse_single_selection must be provided', runid=runid)

    if single_selection is None:
        return success_factory()

    wd = get_wd(runid)
    landuse = Landuse.getInstance(wd)

    try:
        landuse.mode = LanduseMode(mode)
        landuse.single_selection = single_selection
    except Exception:
        return exception_factory('error setting landuse mode', runid=runid)

    return success_factory()


@landuse_bp.route('/runs/<string:runid>/<config>/tasks/set_landuse_db/', methods=['POST'])
def set_landuse_db(runid: str, config: str) -> Response:
    """Persist NLCD database selection for the landuse controller."""
    try:
        db = request.form.get('landuse_db', None)
    except Exception:
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

    payload = request.get_json(silent=True) or {}
    dom = payload.get('dom')
    cover = payload.get('cover')
    value = payload.get('value')

    Landuse.getInstance(wd).modify_coverage(dom, cover, value)

    return success_factory()


@landuse_bp.route('/runs/<string:runid>/<config>/tasks/modify_landuse_mapping/', methods=['POST'])
def task_modify_landuse_mapping(runid: str, config: str) -> Response:
    """Re-map domain identifiers in the landuse controller."""
    wd = get_wd(runid)

    payload = request.get_json(silent=True) or {}
    dom = payload.get('dom', None)
    newdom = payload.get('newdom', None)

    landuse = Landuse.getInstance(wd)
    landuse.modify_mapping(dom, newdom)

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

        return render_template('reports/landuse.htm', runid=runid, config=config,
                               landuse=landuse,
                               landuseoptions=landuseoptions,
                               report=landuse.report)

    except Exception:
        return exception_factory('Reporting landuse failed', runid=runid)


@landuse_bp.route('/runs/<string:runid>/<config>/tasks/modify_landuse/', methods=['POST'])
def task_modify_landuse(runid: str, config: str) -> Response:
    """Bulk modify landuse codes for the supplied Topaz identifiers."""
    wd = get_wd(runid)
    landuse = Landuse.getInstance(wd)

    try:
        topaz_ids = request.form.get('topaz_ids', None)
        topaz_ids = topaz_ids.split(',')
        topaz_ids = [str(int(v)) for v in topaz_ids]
        lccode = request.form.get('landuse', None)
        lccode = str(int(lccode))
    except Exception:
        return exception_factory('Unpacking Modify Landuse Args Faied', runid=runid)

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
