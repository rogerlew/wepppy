"""Session-authorized, read-only views of an accepted postfire assessment."""
from __future__ import annotations

import logging
import math
from pathlib import Path
import re

from flask import Blueprint, Response, g, jsonify, render_template, request, send_file
from flask_login import current_user
from redis.exceptions import RedisError
from werkzeug.exceptions import HTTPException

from wepppy.nodb.core import Ron
from wepppy.nodb.core.ron import RonViewModel
from wepppy.nodb.unitizer import precisions as UNITIZER_PRECISIONS
from wepppy.nodb.mods.postfire_debris_flow import report as reader
from wepppy.nodb.mods.postfire_debris_flow import rainfall_io, production, results
from wepppy.weppcloud.user_preferences import resolve_unitizer_presentation
from wepppy.weppcloud.utils.helpers import authorize, url_for_run
from .._run_context import load_run_context

_logger = logging.getLogger(__name__)
postfire_report_bp = Blueprint('postfire_report', __name__)
_PREFIX = '/runs/<runid>/<config>'


@postfire_report_bp.after_request
def no_store(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


@postfire_report_bp.errorhandler(Exception)
def report_error(exc):
    # Deliberate HTTP boundary also covers run-context preprocessing and auth.
    # Never expose the shared decorator's raw stacktrace/host-path payload.
    if isinstance(exc, reader.ReportError):
        code, message, status = exc.code, exc.message, exc.status
    elif isinstance(exc, HTTPException):
        status = exc.code or 500
        code = 'forbidden' if status in (401, 403) else 'not_found' if status == 404 else 'invalid_input'
        message = 'Access denied.' if status in (401, 403) else 'The report request could not be completed.'
    else:
        _logger.exception('Postfire report request failed')
        status = 503 if isinstance(exc, (RedisError, ConnectionError, TimeoutError)) else 409 if isinstance(
            exc, (rainfall_io.RainfallError, production.WorkflowError, OSError)) else 500
        code, message = 'results_unavailable', reader.ReportError('results_unavailable').message
    if request.endpoint == 'postfire_report.report':
        # This small error document remains readable even when shell state fails.
        from markupsafe import escape
        body = ('<!doctype html><html lang="en"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>Post-fire likelihood report unavailable</title><main>'
                '<h1>Post-fire likelihood report unavailable</h1><p>' + str(escape(message)) +
                '</p><p><a href="">Reload report</a></p></main></html>')
        return Response(body, status=status, mimetype='text/html')
    return jsonify(error=dict(code=code, message=message)), status


def _context(runid, config):
    authorize(runid, config)
    context = getattr(g, 'run_context', None) or load_run_context(runid, config)
    return str(context.active_root)


def _arguments(allowed):
    if any(key not in allowed | {'pup'} or len(request.args.getlist(key)) != 1 for key in request.args):
        raise reader.ReportError('invalid_input', 400)


def _integer(key, default):
    value = request.args.get(key)
    if value is None:
        return default
    if re.fullmatch(r'-?(0|[1-9][0-9]*)', value) is None or len(value) > 16:
        raise reader.ReportError('invalid_input', 400)
    return int(value)


def _query():
    _arguments(set(reader.DEFAULT_QUERY) | {'attempt_id'})
    query = dict(reader.DEFAULT_QUERY)
    for key in ('duration_minutes', 'limit', 'offset'):
        query[key] = _integer(key, query[key])
    for key in ('min_probability', 'year'):
        value = request.args.get(key)
        if value not in (None, ''):
            try:
                number = float(value)
            except ValueError as exc:
                raise reader.ReportError('invalid_input', 400) from exc
            if not math.isfinite(number) or (key == 'year' and number != int(number)):
                raise reader.ReportError('invalid_input', 400)
            query[key] = int(number) if key == 'year' else number
    query['sort'] = request.args.get('sort', query['sort'])
    descending = request.args.get('descending', 'false')
    if (descending not in ('true', 'false') or query['sort'] not in ('row_ordinal', 'rainfall_mm', 'probability')
            or query['duration_minutes'] not in (15, 30, 60) or not 1 <= query['limit'] <= 1000
            or not 0 <= query['offset'] <= 200000 or query['min_probability'] is not None
            and not 0 <= query['min_probability'] <= 1):
        raise reader.ReportError('invalid_input', 400)
    query['descending'] = descending == 'true'
    return query


def _urls(runid, config, assessment):
    scope = dict(runid=runid, config=config)
    return dict(query=url_for_run('postfire_report.query', **scope),
                event=url_for_run('postfire_report.event', **scope),
                control=url_for_run('run_0.runs0', **scope, _anchor='postfire-debris-flow'),
                artifacts={} if assessment is None else {
                    name: url_for_run('postfire_report.attachment', **scope,
                                      attempt_id=assessment.accepted['id'], name=name)
                    for name in reader.artifact_names(assessment)})


@postfire_report_bp.get(_PREFIX + '/report/postfire_debris_flow/')
def report(runid, config):
    wd = _context(runid, config)
    _arguments(set())
    assessment = reader.open_assessment(wd, config)
    seed = reader.view(assessment)
    seed['urls'] = _urls(runid, config, assessment)
    # Required shell readers may load existing state, never create missing state.
    if not (Path(wd) / 'ron.nodb').is_file() or not (Path(wd) / 'unitizer.nodb').is_file():
        raise reader.ReportError('results_unavailable', 503)
    ron = Ron.getInstance(wd)
    unitizer = resolve_unitizer_presentation(wd)
    html = render_template('reports/postfire_debris_flow/report.htm', runid=runid, config=config,
                           ron=ron, current_ron=RonViewModel(ron), user=current_user,
                           unitizer_nodb=unitizer, precisions=UNITIZER_PRECISIONS,
                           postfire_report_seed=seed, postfire_report_error=None)
    if assessment is not None:
        assessment.recheck()
    return html


@postfire_report_bp.get(_PREFIX + '/query/postfire_debris_flow/')
def query(runid, config):
    wd = _context(runid, config)
    parameters = _query()
    identity = reader.attempt_id(request.args.get('attempt_id'))
    assessment = reader.open_assessment(wd, config, identity)
    payload = reader.view(assessment, parameters)
    payload['urls'] = _urls(runid, config, assessment)
    return jsonify(payload)


@postfire_report_bp.get(_PREFIX + '/query/postfire_debris_flow/event')
def event(runid, config):
    wd = _context(runid, config)
    _arguments({'attempt_id', 'event_id'})
    identity = reader.attempt_id(request.args.get('attempt_id'))
    event_id = request.args.get('event_id')
    if not isinstance(event_id, str) or not reader.EVENT_ID.fullmatch(event_id):
        raise reader.ReportError('invalid_input', 400)
    assessment = reader.open_assessment(wd, config, identity)
    try:
        rows = results.get_event(assessment.catalog, event_id)['rows']
    except KeyError as exc:
        raise reader.ReportError('not_found', 404) from exc
    assessment.recheck()
    return jsonify(attempt_id=identity, rows=rows)


@postfire_report_bp.get(_PREFIX + '/report/postfire_debris_flow/files/<name>')
def attachment(runid, config, name):
    wd = _context(runid, config)
    _arguments({'attempt_id'})
    identity = reader.attempt_id(request.args.get('attempt_id'))
    assessment = reader.open_assessment(wd, config, identity)
    stream = reader.open_attachment(assessment, name)
    try:
        response = send_file(stream, as_attachment=True, download_name=name,
                             mimetype='application/json' if name == 'manifest.json' else
                             'image/tiff' if name == 'valid_mask.tif' else 'application/octet-stream',
                             conditional=False, etag=False)
        response.call_on_close(stream.close)
        return response
    except BaseException:  # broad-except: descriptor transfer failed; caller owns cleanup and re-raises.
        stream.close()
        raise
