"""Read-only projection of one accepted, validated postfire result bundle."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import logging
import os
from pathlib import Path
import re

from . import production, rainfall_io as io, results
from .response_curve import response_curve, rainfall_provenance

__all__ = ['ReportError', 'Assessment', 'attempt_id', 'open_assessment', 'summary',
           'view', 'artifact_names', 'open_attachment']
_logger = logging.getLogger(__name__)
ATTEMPT_ID = re.compile(r'[0-9a-f]{32}\Z')
EVENT_ID = re.compile(r'[0-9a-f]{64}:(0|[1-9][0-9]{0,5})\Z')
DEFAULT_QUERY = dict(duration_minutes=15, min_probability=None, year=None,
                     sort='row_ordinal', descending=False, limit=100, offset=0)
_WARNINGS = {'area_outside_study_range', 'partial_dnbr_coverage'}
_REASONS = {'missing_input', 'missing_provenance', 'empty_dnbr', 'incomplete_k_coverage',
            'zero_valid_support', 'unresolved_intersection', 'zero_relief', 'zero_area',
            'terrain_potentially_truncated', 'watershed_area_mismatch'}


class ReportError(ValueError):
    """Sanitized report transport failure."""

    def __init__(self, code, status=409):
        self.code, self.status = code, status
        self.message = {
            'invalid_input': 'Invalid report request.',
            'assessment_replaced': 'The accepted assessment changed. Reload this report.',
            'not_found': 'The requested saved result was not found.',
            'results_unavailable': 'Saved results could not be read. Reload or return to the run control.',
        }[code]
        super().__init__(self.message)


def attempt_id(value):
    if not isinstance(value, str) or not ATTEMPT_ID.fullmatch(value):
        raise ReportError('invalid_input', 400)
    return value


def _artifact_record(wd, accepted, name):
    relative = f'postfire_debris_flow/attempts/{accepted["id"]}/results/{name}'
    record = accepted.get('artifacts', {}).get(relative)
    if (not isinstance(record, list) or len(record) != 5 or record[0] != relative
            or any(type(v) is not int or v < 0 for v in record[1:4])
            or not io.hash_value(record[4])):
        raise ReportError('results_unavailable')
    return Path(wd) / relative, record


def _state(wd):
    try:
        return production.state_at(wd)
    except (ValueError, KeyError, TypeError) as exc:
        raise ReportError('results_unavailable') from exc


@dataclass(frozen=True)
class Assessment:
    wd: Path
    accepted: dict
    catalog: results.ResultCatalog
    current: bool | None
    newer_attempt: dict | None

    def recheck(self):
        if _state(self.wd)['last_successful_run'] != self.accepted:
            raise ReportError('assessment_replaced')


def open_assessment(wd, config, expected_attempt=None):
    """Never initialize optional state or reconcile RQ during a report read."""
    wd = Path(wd).absolute()
    state = _state(wd)
    accepted = deepcopy(state['last_successful_run'])
    if accepted is None:
        if expected_attempt is not None:
            raise ReportError('assessment_replaced')
        return None
    identity = accepted.get('id')
    if not isinstance(identity, str) or not ATTEMPT_ID.fullmatch(identity):
        raise ReportError('results_unavailable')
    if expected_attempt is not None and identity != expected_attempt:
        raise ReportError('assessment_replaced')
    manifest_path, record = _artifact_record(wd, accepted, 'manifest.json')
    try:
        catalog = results.open_results(manifest_path.parent, expected_manifest_sha256=record[4])
        model = accepted.get('model', 'M1')
        assessment_id = accepted['snapshot']['dnbr'] if model == 'M1' else identity
        if catalog.manifest['model'] != model or catalog.manifest['identity']['assessment_id'] != assessment_id:
            raise ReportError('results_unavailable')
    except (io.RainfallError, OSError, KeyError, TypeError) as exc:
        if _state(wd)['last_successful_run'] != accepted:
            raise ReportError('assessment_replaced') from exc
        raise ReportError('results_unavailable') from exc
    current = None
    prep_path = wd / 'redisprep.dump'
    if not prep_path.is_symlink() and prep_path.is_file():
        try:
            projected = production.get_state(wd, config, reconcile=False)['results']
            if projected is not None and projected['id'] == identity:
                current = projected['current']
        except Exception:  # broad-except: optional currentness boundary preserves validated saved values.
            _logger.exception('Postfire report currentness could not be checked')
    latest = state.get('run_attempt')
    newer = None
    if latest and latest.get('id') != identity:
        newer = {key: latest.get(key) for key in ('id', 'model', 'phase')}
        newer['model'] = latest.get('model', 'M1')
    assessment = Assessment(wd, accepted, catalog, current, newer)
    assessment.recheck()
    return assessment


def summary(assessment):
    m = assessment.catalog.manifest
    predictors = m['predictor_snapshot']
    coverage = m.get('coverage')
    return dict(
        soil_source=('NRCS-derived STATSGO fine-earth Kf' if predictors['schema_version']==3
                     else 'POLARIS/RUSLE Nomograph K (legacy)' if m['model']=='M1' else 'Recorded soil thickness'),
        rainfall_provenance=rainfall_provenance(m['identity'],m['request']['frequency_source']),
        model=m['model'], completed_at=assessment.accepted.get('completed_at'),
        assessment_id=m['identity']['assessment_id'], current=assessment.current,
        newer_attempt=assessment.newer_attempt, climate_mode=m['identity']['climate_mode'],
        date_semantics=m['identity']['date_semantics'], frequency_source=m['request']['frequency_source'],
        frequency={key: m['frequency'].get(key) if io.number(m['frequency'].get(key)) else None
                   for key in ('represented_years', 'year_min', 'year_max', 'wet_years')},
        area_km2=predictors['area_km2'],
        coverage=None if coverage is None else {key: coverage[key] for key in
                   ('total_cells', 'valid_cells', 'excluded_cells', 'valid_fraction')},
        warnings=[code if code in _WARNINGS else 'unrecorded_warning' for code in predictors['warnings']],
        predictors=[dict(name=name, value=value['value'], unit=value['units'],
                         reason=value['reason'] if value['reason'] in _REASONS or value['reason'] is None
                         else 'unrecorded_reason') for name, value in predictors['predictors'].items()],
    )


def view(assessment, query=None):
    query = dict(DEFAULT_QUERY if query is None else query)
    payload = dict(schema_version=1, status='absent', attempt_id=None, summary=None,
                   response_curve=None, design=[], inverse=[], events=dict(rows=[], total=0, unfiltered_total=0), query=query)
    if assessment is None:
        return payload
    catalog = assessment.catalog
    page = results.list_events(catalog, **query)
    import pyarrow.compute as pc
    total = pc.sum(pc.equal(catalog.events['duration_minutes'], query['duration_minutes'])).as_py() or 0
    payload.update(status='available', attempt_id=assessment.accepted['id'], summary=summary(assessment),
                   response_curve=response_curve(catalog.manifest,catalog.design.to_pylist(),query['duration_minutes']),
                   design=catalog.design.to_pylist(),
                   inverse=[row for row in catalog.inverse.to_pylist() if row['target_probability'] == .5],
                   events=dict(rows=page['rows'], total=page['total'], unfiltered_total=total))
    assessment.recheck()
    return payload


def artifact_names(assessment):
    names = production.FILES
    if assessment.catalog.manifest['predictor_snapshot']['schema_version'] in (2, 3):
        names = (*names, 'valid_mask.tif')
    return names


def open_attachment(assessment, name):
    """Transfer an already verified descriptor; caller owns it until response close."""
    if name not in artifact_names(assessment):
        raise ReportError('not_found', 404)
    path, record = _artifact_record(assessment.wd, assessment.accepted, name)
    limit = io.MAX_PREDICTOR_BYTES if name == 'valid_mask.tif' else io.MAX_TEXT if name == 'manifest.json' else io.MAX_BYTES
    stream = io.open_local(path, limit)
    try:
        before = os.fstat(stream.fileno())
        # Restore may change inode timestamps without changing accepted content.
        # Pin persisted size/hash; timestamps detect mutations during this read.
        if before.st_size != record[1]:
            raise ReportError('results_unavailable')
        digest = hashlib.sha256()
        size = 0
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            size += len(block)
            if size > limit:
                raise ReportError('results_unavailable')
            digest.update(block)
        after = os.fstat(stream.fileno())
        if (digest.hexdigest() != record[4] or size != before.st_size
                or (after.st_size, after.st_mtime_ns, after.st_ctime_ns) !=
                (before.st_size, before.st_mtime_ns, before.st_ctime_ns)):
            raise ReportError('results_unavailable')
        assessment.recheck()
        stream.seek(0)
        return stream
    except BaseException:  # broad-except: descriptor ownership boundary, including cancellation; re-raises.
        stream.close()
        raise
