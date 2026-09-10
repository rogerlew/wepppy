"""Materialized local M1 event/design/inverse results and bounded queries."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re

import pyarrow as pa
import pyarrow.parquet as pq

from . import rainfall
from .rainfall import RainfallInputs
from .rainfall_io import (RainfallError, MAX_TEXT, digest, fail, load_predictors,
                          number, pinned, read_json, read_table, recheck, write_json, validate_predictors)
from .staley2017 import probability, rainfall_threshold

__all__ = ['RainfallError', 'RainfallInputs', 'ResultCatalog', 'build_m1_results',
           'open_results', 'list_events', 'get_event']
COMMON = [('duration_minutes',pa.int64()), ('intensity_mm_per_hour',pa.float64()),
          ('rainfall_mm',pa.float64()), ('probability',pa.float64()),
          ('status',pa.string()), ('reason',pa.string())]
SCHEMAS = {
    'events': pa.schema([('event_id',pa.string()),('row_ordinal',pa.int64()),
                         *[(k,pa.float64()) for k in ('year','month','day_of_month','sim_day_index','precipitation_mm')],
                         ('date_status',pa.string()),*COMMON]),
    'design': pa.schema([('return_interval_years',pa.int64()),('source',pa.string()),
                         ('rank_index',pa.int64()),('positive_samples',pa.int64()),*COMMON]),
    'inverse': pa.schema([('target_probability',pa.float64()),*COMMON]),
}
LIMITS = {'events':600_000, 'design':12, 'inverse':300}


def _forward(rows, predictors):
    values = {k:v['value'] for k,v in predictors.items()}
    for row in rows:
        if row['status'] == 'available':
            if any(v is None for v in values.values()):
                row.update(status='unavailable', reason='missing_predictors')
            else:
                row['probability'] = probability('M1', row['duration_minutes'], **values, rainfall_mm=row['rainfall_mm'])


def _targets(values):
    if not isinstance(values, (list,tuple)) or not 1 <= len(values) <= 100:
        fail('invalid_input', 'Supply 1–100 inverse targets')
    if any(not number(v) or not 0 < v < 1 for v in values) or len(set(values)) != len(values):
        fail('invalid_input', 'Targets must be unique finite probabilities inside (0,1)')
    return tuple(sorted(values))


def build_m1_results(inputs: RainfallInputs, output_dir: Path, *, frequency_source: str,
                     return_intervals, durations, target_probabilities) -> dict:
    """Build a fresh immutable local bundle; contract in docs/rainfall_results.md."""
    context = rainfall.identity(inputs)
    durations = rainfall.selections(durations, rainfall.DURATIONS, 'durations')
    intervals = rainfall.selections(return_intervals, rainfall.INTERVALS, 'return intervals')
    targets = _targets(target_probabilities)
    if frequency_source not in ('cli','noaa'):
        fail('invalid_input', 'Explicit cli or noaa frequency source required')
    consumed = {}
    predictors = load_predictors(inputs.predictor_manifest, inputs.expected_sha256, consumed)
    events, df, frequency = rainfall.climate_events(inputs, durations, consumed)
    parsed = {}
    for source, path in (('cli',inputs.cli_frequency_csv),('noaa',inputs.noaa_csv)):
        if path is not None:
            parsed[source] = rainfall.frequency_csv(path, inputs.expected_sha256, consumed, source=source)
    if frequency_source == 'cli':
        design = rainfall.cli_design(df, intervals, durations, frequency, parsed.get('cli'))
    else:
        design = rainfall.noaa_design(parsed.get('noaa'), intervals, durations)
    _forward(events, predictors['predictors'])
    _forward(design, predictors['predictors'])
    values = {k:v['value'] for k,v in predictors['predictors'].items()}
    inverse = []
    for target in targets:
        for duration in durations:
            if any(v is None for v in values.values()):
                result = {'status':'unavailable','reason':'missing_predictors',
                          'rainfall_mm':None,'intensity_mm_per_hour':None}
            else:
                result = asdict(rainfall_threshold('M1',duration,**values,target_probability=target))
            inverse.append({'target_probability':target,'duration_minutes':duration,
                            'probability':None,**result})
    output = Path(output_dir).absolute()
    if '..' in output.parts or any(p.is_symlink() for p in (output,*output.parents)):
        fail('invalid_input', 'Output path must not traverse symlinks')
    try:
        output.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise RainfallError('output_exists', 'Use a fresh output directory') from exc
    write_json(output/'incomplete.json', {'schema_version':1,'status':'incomplete'})
    tables = {}
    for name, rows in (('events',events),('design',design),('inverse',inverse)):
        table = pa.Table.from_pylist(rows, schema=SCHEMAS[name])
        p = output/f'{name}.parquet'
        with p.open('xb') as stream:
            pq.write_table(table, stream, compression='snappy')
        actual = read_table(p, max_rows=LIMITS[name], schema=SCHEMAS[name])
        if not actual.equals(table):
            fail('invalid_input', 'Result table readback differs')
        tables[name] = {'sha256':digest(p),'rows':len(rows)}
    recheck(consumed)
    manifest = {'schema_version':1,'status':'complete','model':'M1',
                'identity':context,'predictor_snapshot':predictors,
                'sources_sha256':consumed,'frequency':frequency,
                'frequency_metadata':{k:{'title':v['title'],**v['metadata']} for k,v in parsed.items()},
                'units':{'rainfall_mm':'mm','intensity_mm_per_hour':'mm/hour','probability':'fraction'},
                'request':{'frequency_source':frequency_source,'return_intervals':list(intervals),
                           'durations':list(durations),'target_probabilities':list(targets)},
                'tables':tables}
    write_json(output/'manifest.json',manifest)
    return manifest


@dataclass(frozen=True)
class ResultCatalog:
    """Validated in-memory result snapshot; open using open_results."""
    manifest: dict
    events: pa.Table


def open_results(path: Path, *, expected_manifest_sha256: str) -> ResultCatalog:
    directory = Path(path).absolute()
    p = directory/'manifest.json'
    if not p.exists():
        fail('incomplete_output', 'No completed manifest')
    consumed = {}
    pinned(p,{str(p):expected_manifest_sha256},consumed,MAX_TEXT)
    m = read_json(p)
    if m.get('schema_version') != 1 or type(m['schema_version']) is not int or m.get('status') != 'complete' or m.get('model') != 'M1':
        fail('invalid_input', 'Unsupported result manifest')
    if not isinstance(m.get('tables'),dict) or set(m['tables']) != set(SCHEMAS):
        fail('invalid_input', 'Unexpected result table names')
    for key in ('identity','predictor_snapshot','sources_sha256','frequency','request','units'):
        if not isinstance(m.get(key),dict):
            fail('invalid_input', f'Missing result {key}')
    _validate_manifest(m)
    events = None
    for name, schema in SCHEMAS.items():
        info = m['tables'][name]
        if not isinstance(info,dict) or type(info.get('rows')) is not int or not 0 <= info['rows'] <= LIMITS[name]:
            fail('invalid_input', 'Invalid table row count')
        p = directory/f'{name}.parquet'
        pinned(p,{str(p):info.get('sha256')},consumed)
        table = read_table(p,max_rows=LIMITS[name],schema=schema)
        if table.num_rows != info['rows']:
            fail('invalid_input', 'Table count differs from manifest')
        _validate_rows(name, table, m)
        if name == 'events':
            events = table
    recheck(consumed)
    return ResultCatalog(m, events)


def _context(catalog):
    m = catalog.manifest
    # Return detached metadata; callers cannot change later query context.
    import copy
    return copy.deepcopy({k:m[k] for k in ('identity','predictor_snapshot','units')})


def list_events(catalog: ResultCatalog, *, duration_minutes: int, min_probability=None,
                max_probability=None, year=None, sort='row_ordinal', descending=False,
                limit=100, offset=0) -> dict:
    """One duration per event; deterministic ordinal tie-break, nulls last."""
    rainfall.selections([duration_minutes],rainfall.DURATIONS,'duration')
    if duration_minutes not in catalog.manifest['request']['durations']:
        fail('invalid_input', 'Duration was not materialized')
    if sort not in ('row_ordinal','rainfall_mm','probability') or type(descending) is not bool:
        fail('invalid_input', 'Unsupported sort')
    if type(limit) is not int or not 1 <= limit <= 1000 or type(offset) is not int or not 0 <= offset <= 200_000:
        fail('invalid_input', 'Invalid pagination')
    for v in (min_probability,max_probability):
        if v is not None and (not number(v) or not 0 <= v <= 1):
            fail('invalid_input', 'Invalid probability filter')
    if min_probability is not None and max_probability is not None and min_probability > max_probability:
        fail('invalid_input', 'Inverted probability bounds')
    if year is not None and (not number(year) or year != int(year)):
        fail('invalid_input', 'Invalid year filter')
    df = catalog.events.to_pandas(ignore_metadata=True)
    df = df[df.duration_minutes == duration_minutes]
    if min_probability is not None:
        df = df[df.probability >= min_probability]
    if max_probability is not None:
        df = df[df.probability <= max_probability]
    if year is not None:
        df = df[df.year == year]
    keys = [sort] if sort == 'row_ordinal' else [sort,'row_ordinal']
    ascending = [not descending] if len(keys) == 1 else [not descending,True]
    df = df.sort_values(keys,ascending=ascending,na_position='last',kind='stable')
    rows = pa.Table.from_pandas(df.iloc[offset:offset+limit],schema=SCHEMAS['events'],preserve_index=False).to_pylist()
    return {'context':_context(catalog),'total':len(df),'rows':rows}


def get_event(catalog: ResultCatalog, event_id: str) -> dict:
    if not isinstance(event_id,str) or re.fullmatch(r'[0-9a-f]{64}:(0|[1-9][0-9]{0,5})',event_id) is None:
        fail('invalid_input', 'Invalid event ID')
    import pyarrow.compute as pc
    rows = catalog.events.filter(pc.equal(catalog.events['event_id'],event_id)).to_pylist()
    if not rows:
        raise KeyError(event_id)
    rows.sort(key=lambda r:r['duration_minutes'])
    return {'context':_context(catalog),'rows':rows}


def _validate_manifest(m):
    expected_units = {'rainfall_mm':'mm','intensity_mm_per_hour':'mm/hour','probability':'fraction'}
    if m['units'] != expected_units:
        fail('invalid_input', 'Invalid result units')
    context = m['identity']
    if any(not isinstance(context.get(k),str) or not context[k].strip() or len(context[k]) > 256
           for k in ('project_id','climate_mode','assessment_id')) or context.get('date_semantics') not in ('simulation_labels','calendar'):
        fail('invalid_input', 'Invalid result identity')
    validate_predictors(m['predictor_snapshot'])
    request = m['request']
    rainfall.selections(request.get('durations'),rainfall.DURATIONS,'durations')
    rainfall.selections(request.get('return_intervals'),rainfall.INTERVALS,'intervals')
    _targets(request.get('target_probabilities'))
    if request.get('frequency_source') not in ('cli','noaa'):
        fail('invalid_input', 'Invalid result frequency source')
    from .rainfall_io import hash_value
    if not m['sources_sha256'] or any(not isinstance(k,str) or not hash_value(v) for k,v in m['sources_sha256'].items()):
        fail('invalid_input', 'Invalid result source hashes')


def _validate_rows(name, table, m):
    seen = set()
    events = {}
    durations = set(m['request']['durations'])
    intervals = set(m['request']['return_intervals'])
    targets = set(m['request']['target_probabilities'])
    hashes = set(m['sources_sha256'].values())
    predictors = {k:v['value'] for k,v in m['predictor_snapshot']['predictors'].items()}
    missing = any(v is None for v in predictors.values())
    for row in table.to_pylist():
        duration = row['duration_minutes']
        if duration not in durations:
            fail('invalid_input', 'Unrequested result duration')
        status, reason = row['status'], row['reason']
        if status not in ('available','unavailable','nonunique') or (status == 'nonunique' and name != 'inverse'):
            fail('invalid_input', 'Invalid result status')
        if (status == 'available' and reason is not None) or (status != 'available' and (not isinstance(reason,str) or not reason)):
            fail('invalid_input', 'Invalid result reason')
        for key in ('intensity_mm_per_hour','rainfall_mm','probability'):
            value = row[key]
            if value is not None and (not number(value) or value < 0 or (key == 'probability' and value > 1)):
                fail('invalid_input', 'Invalid result number')
        intensity, accumulation = row['intensity_mm_per_hour'],row['rainfall_mm']
        if (intensity is None) != (accumulation is None):
            fail('invalid_input', 'Inconsistent result rainfall availability')
        if intensity is not None:
            import math
            if not math.isclose(accumulation,intensity*(duration/60),rel_tol=1e-14,abs_tol=0.):
                fail('invalid_input', 'Inconsistent result rainfall units')
        if status == 'available' and (accumulation is None or (name != 'inverse' and row['probability'] is None)):
            fail('invalid_input', 'Missing available result values')
        if status != 'available' and row['probability'] is not None:
            fail('invalid_input', 'Unavailable result has probability')
        if name != 'inverse':
            if accumulation is not None:
                expected_probability = None if missing else probability('M1',duration,**predictors,rainfall_mm=accumulation)
                if (row['probability'] != expected_probability or status != ('unavailable' if missing else 'available')
                        or reason != ('missing_predictors' if missing else None)):
                    fail('invalid_input', 'Forward result disagrees with predictor snapshot')
            elif reason not in {'missing_duration','missing_intensity','nonfinite_intensity','negative_intensity',
                                 'missing_noaa','unsupported_combination','zero_placeholder','invalid_year_labels',
                                 'unsupported_record_length','no_positive_samples','insufficient_positive_samples'}:
                fail('invalid_input', 'Invalid missing-rainfall reason')
        else:
            target = row['target_probability']
            if target not in targets:
                fail('invalid_input', 'Unrequested inverse target')
            expected_inverse = ({'status':'unavailable','reason':'missing_predictors',
                                 'rainfall_mm':None,'intensity_mm_per_hour':None} if missing else
                                asdict(rainfall_threshold('M1',duration,**predictors,target_probability=target)))
            if any(row[k] != v for k,v in expected_inverse.items()):
                fail('invalid_input', 'Inverse result disagrees with predictor snapshot')
        if reason == 'insufficient_positive_samples' and name != 'design':
            fail('invalid_input', 'Sample-rank reason requires a design scenario')
        if name == 'events':
            event_id, ordinal = row['event_id'],row['row_ordinal']
            if (not isinstance(event_id,str) or type(ordinal) is not int or not 0 <= ordinal < 200_000
                    or event_id != f'{event_id.split(":")[0]}:{ordinal}' or event_id.split(':')[0] not in hashes):
                fail('invalid_input', 'Invalid persisted event identity')
            if row['date_status'] != rainfall._date_status(row['year'],row['month'],row['day_of_month'],m['identity']['date_semantics']):
                fail('invalid_input', 'Invalid date semantics')
            if not number(row['precipitation_mm']) or row['precipitation_mm'] <= 0:
                fail('invalid_input', 'Invalid wet event')
            if any(row[k] is not None and not number(row[k]) for k in ('year','month','day_of_month','sim_day_index')):
                fail('invalid_input', 'Invalid persisted date fields')
            key = (event_id,duration)
            identity = tuple(row[k] for k in ('row_ordinal','year','month','day_of_month','sim_day_index','precipitation_mm','date_status'))
            if event_id in events and events[event_id] != identity:
                fail('invalid_input', 'Event duration rows disagree')
            events[event_id] = identity
        elif name == 'design':
            if row['return_interval_years'] not in intervals or row['source'] != m['request']['frequency_source']:
                fail('invalid_input', 'Unrequested design scenario')
            if any(row[k] is not None and (type(row[k]) is not int or row[k] < 0) for k in ('rank_index','positive_samples')):
                fail('invalid_input', 'Invalid design sample metadata')
            if row['source'] == 'cli' and accumulation is not None:
                rank, count = row['rank_index'],row['positive_samples']
                if rank is None or count is None or rank >= count:
                    fail('invalid_input', 'CLI rainfall requires a supported positive rank')
            if reason == 'insufficient_positive_samples':
                rank, count = row['rank_index'],row['positive_samples']
                if row['source'] != 'cli' or rank is None or count is None or count == 0 or rank < count:
                    fail('invalid_input', 'Inconsistent insufficient positive samples')
            key = (row['return_interval_years'],duration)
        else:
            if row['target_probability'] not in targets or row['probability'] is not None:
                fail('invalid_input', 'Invalid inverse target/result')
            if status != 'available' and accumulation is not None:
                fail('invalid_input', 'Unavailable inverse has rainfall')
            key = (row['target_probability'],duration)
        if key in seen:
            fail('invalid_input', 'Duplicate result row')
        seen.add(key)
    expected = (len(events) if name == 'events' else len(intervals) if name == 'design' else len(targets))*len(durations)
    if len(seen) != expected:
        fail('invalid_input', 'Missing result combinations')
