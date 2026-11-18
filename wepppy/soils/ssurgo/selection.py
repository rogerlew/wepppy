"""Whole-collection mirror/SDA selection with durable, source-separated evidence."""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time

from .source import (ACQUISITION_DEADLINE, JSON_PROFILE, SoilDataSource,
                     SoilDataSourceError, SoilServiceUnavailable, cache_evidence, utc_now)

SOURCE_BUDGET_SECONDS = 30.0
TOTAL_BUDGET_SECONDS = 60.0
OUTCOMES = {'success', 'unavailable', 'coverage_miss', 'contract_error'}
REASONS = {'selected', 'cache_reused', 'dns_unavailable', 'connection_failed',
           'deadline_exceeded', 'http_429', 'http_5xx', 'not_ready',
           'missing_components', 'source_contract_error', 'selection_persistence_error'}


class SoilSourceSelectionError(SoilDataSourceError):
    def __init__(self, selection):
        self.selection = selection
        reasons = ', '.join(attempt['reason'] for attempt in selection['attempts'])
        super().__init__('Soil source selection failed: ' + reasons)


def deployment_default():
    """Return identity/policy without modifying saved project overrides."""
    mode = os.environ.get('SOIL_DATA_MODE', '')
    if mode in ('', 'legacy-xml'):
        return SoilDataSource().identity(), 'explicit'
    if mode != 'mirror-first':
        raise SoilDataSourceError('Invalid deployment soil source mode')
    endpoint = os.environ.get('SOIL_DATA_ENDPOINT')
    release = os.environ.get('SOIL_DATA_RELEASE')
    if not endpoint or not release:
        raise SoilDataSourceError('Mirror-first deployment requires endpoint and release')
    return SoilDataSource(endpoint, JSON_PROFILE, release).identity(), 'mirror-first'


def _identity(value):
    if not isinstance(value, dict) or set(value) != {'endpoint', 'profile', 'release'}:
        raise SoilDataSourceError('Malformed selection identity')
    if SoilDataSource(**value).identity() != value:
        raise SoilDataSourceError('Noncanonical selection identity')
    return value


def _timestamp(value):
    if not isinstance(value, str):
        raise SoilDataSourceError('Malformed selection timestamp')
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise SoilDataSourceError('Selection timestamp lacks timezone')
    return parsed


def validate_selection(event, supplier=None):
    fields = {'schema_version', 'policy', 'configured_primary', 'actual_supplier',
              'historical_rows_unknown', 'selected_at', 'attempts'}
    try:
        if not isinstance(event, dict) or set(event) != fields or type(event['schema_version']) is not int or event['schema_version'] != 1:
            raise SoilDataSourceError('Malformed soil selection event')
        primary = _identity(event['configured_primary'])
        if event['policy'] != 'mirror-first' or primary['profile'] != JSON_PROFILE:
            raise SoilDataSourceError('Malformed soil selection policy')
        selected_at = _timestamp(event['selected_at'])
        attempts = event['attempts']
        if not isinstance(attempts, list) or not 1 <= len(attempts) <= 2:
            raise SoilDataSourceError('Malformed soil selection attempts')
        previous_end = None
        for index, attempt in enumerate(attempts):
            if not isinstance(attempt, dict) or set(attempt) != {'identity', 'started_at', 'ended_at', 'outcome', 'reason'}:
                raise SoilDataSourceError('Malformed soil selection attempt')
            expected = primary if index == 0 else SoilDataSource().identity()
            if _identity(attempt['identity']) != expected or attempt['outcome'] not in OUTCOMES or attempt['reason'] not in REASONS:
                raise SoilDataSourceError('Invalid soil selection attempt')
            start, end = _timestamp(attempt['started_at']), _timestamp(attempt['ended_at'])
            if start > end or end > selected_at or (previous_end is not None and start < previous_end):
                raise SoilDataSourceError('Invalid soil selection chronology')
            previous_end = end
            allowed = {
                'success': {'selected', 'cache_reused'},
                'unavailable': {'dns_unavailable', 'connection_failed', 'deadline_exceeded', 'http_429', 'http_5xx', 'not_ready'},
                'coverage_miss': {'missing_components'},
                'contract_error': {'source_contract_error', 'selection_persistence_error'},
            }
            if attempt['reason'] not in allowed[attempt['outcome']]:
                raise SoilDataSourceError('Invalid soil selection outcome/reason')
            if index < len(attempts) - 1 and attempt['outcome'] not in ('unavailable', 'coverage_miss'):
                raise SoilDataSourceError('Invalid fallback eligibility in selection history')
        actual = event['actual_supplier']
        if actual is None:
            if supplier is not None or any(a['outcome'] == 'success' for a in attempts) or event['historical_rows_unknown'] is not None:
                raise SoilDataSourceError('Failed selection cannot claim a supplier')
        else:
            _identity(actual)
            if attempts[-1]['outcome'] != 'success' or attempts[-1]['identity'] != actual or type(event['historical_rows_unknown']) is not bool:
                raise SoilDataSourceError('Soil selection supplier differs from final attempt')
            if supplier is not None and actual != supplier:
                raise SoilDataSourceError('Soil selection supplier differs from cache binding')
    except (TypeError, ValueError, KeyError, RecursionError) as exc:
        raise SoilDataSourceError('Malformed soil selection event') from exc


def validate_selection_history(conn, supplier, historical_rows_unknown):
    """Validate optional additive history before any collection can reuse the cache."""
    try:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name='soil_data_selection'").fetchone() is None:
            return
        columns = [(row[1], row[2].upper(), row[5]) for row in conn.execute('PRAGMA table_info(soil_data_selection)')]
        if columns != [('id', 'INTEGER', 1), ('event', 'TEXT', 0)]:
            raise SoilDataSourceError('Malformed soil selection history schema')
        for row in conn.execute('SELECT event FROM soil_data_selection ORDER BY id'):
            event = json.loads(row[0])
            validate_selection(event, supplier)
            if event['historical_rows_unknown'] != historical_rows_unknown:
                raise SoilDataSourceError('Soil selection history differs from cache origin flag')
    except (sqlite3.Error, ValueError, TypeError, RecursionError) as exc:
        raise SoilDataSourceError('Malformed soil selection history') from exc


def _publish_latest(path, event):
    if path is None:
        return
    temporary = None
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', dir=target.parent, prefix='.soil-selection-', delete=False) as stream:
            temporary = stream.name
            json.dump(event, stream, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except (OSError, ValueError, TypeError) as exc:
        raise SoilDataSourceError('Soil selection evidence publication failed') from exc
    finally:
        if temporary is not None and os.path.exists(temporary):
            try:
                os.unlink(temporary)
            except OSError as exc:
                raise SoilDataSourceError('Soil selection temporary cleanup failed') from exc


def _record_selection(collection, event, latest_path):
    try:
        validate_selection(event, collection.data_source.identity())
        validate_selection_history(collection.conn, collection.data_source.identity(), event['historical_rows_unknown'])
        with collection.conn:
            collection.conn.execute('CREATE TABLE IF NOT EXISTS soil_data_selection(id INTEGER PRIMARY KEY, event TEXT NOT NULL)')
            collection.conn.execute('INSERT INTO soil_data_selection(event) VALUES(?)', (json.dumps(event, sort_keys=True),))
        _publish_latest(latest_path, event)
        collection.selection_event = event
    except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
        raise SoilDataSourceError('Soil selection evidence persistence failed') from exc


def soil_collection(mukeys, use_statsgo=False, cache_db_path=None, *, endpoint=None,
                    profile='legacy-xml', release=None, fallback_to_sda=False,
                    fallback_cache_db_path=None):
    from .ssurgo import SurgoSoilCollection

    if type(fallback_to_sda) is not bool:
        raise SoilDataSourceError('Invalid soil fallback setting')
    if not fallback_to_sda:
        return SurgoSoilCollection(mukeys, use_statsgo=use_statsgo, cache_db_path=cache_db_path,
                                   endpoint=endpoint, profile=profile, release=release)
    if profile != JSON_PROFILE or endpoint is None:
        raise SoilDataSourceError('SDA fallback requires an explicit JSON primary')
    primary = SoilDataSource(endpoint, profile, release)
    if cache_db_path is not None and fallback_cache_db_path is None:
        raise SoilDataSourceError('File-backed fallback requires a separate SDA cache path')
    if cache_db_path is not None and os.path.realpath(cache_db_path) == os.path.realpath(fallback_cache_db_path):
        raise SoilDataSourceError('Primary and fallback caches must be separate')
    keys = list(mukeys)
    latest_path = str(cache_db_path) + '.selection.json' if cache_db_path is not None else None
    try:
        if latest_path is not None and os.path.lexists(latest_path):
            os.unlink(latest_path)
    except OSError as exc:
        raise SoilDataSourceError('Cannot invalidate prior soil selection evidence') from exc
    event = {'schema_version': 1, 'policy': 'mirror-first', 'configured_primary': primary.identity(),
             'actual_supplier': None, 'historical_rows_unknown': None, 'selected_at': utc_now(), 'attempts': []}
    total_deadline = time.monotonic() + TOTAL_BUDGET_SECONDS
    for index, (source, cache) in enumerate(((primary, cache_db_path), (SoilDataSource(), fallback_cache_db_path))):
        attempt = {'identity': source.identity(), 'started_at': utc_now(), 'ended_at': None,
                   'outcome': 'contract_error', 'reason': 'source_contract_error'}
        collection = None
        token = ACQUISITION_DEADLINE.set(min(total_deadline, time.monotonic() + SOURCE_BUDGET_SECONDS))
        try:
            collection = SurgoSoilCollection(keys, use_statsgo=use_statsgo, cache_db_path=cache, **source.identity())
            present = {int(row[0]) for row in collection.conn.execute('SELECT DISTINCT mukey FROM component')}
            if index == 0 and set(collection.mukeys) - present:
                attempt.update(outcome='coverage_miss', reason='missing_components')
            else:
                historical_rows_unknown = cache_evidence(collection.conn)['binding']['historical_rows_unknown']
                attempt.update(outcome='success', reason='cache_reused' if collection._sync_n == 0 else 'selected')
                event['actual_supplier'] = source.identity()
                event['historical_rows_unknown'] = historical_rows_unknown
        except SoilServiceUnavailable as exc:
            attempt.update(outcome='unavailable', reason=exc.reason)
        except (SoilDataSourceError, sqlite3.Error, OSError, ValueError) as exc:
            attempt['ended_at'] = utc_now()
            event['attempts'].append(attempt)
            event['selected_at'] = utc_now()
            validate_selection(event)
            _publish_latest(latest_path, event)
            raise SoilSourceSelectionError(event) from exc
        finally:
            ACQUISITION_DEADLINE.reset(token)
            if collection is not None and attempt['outcome'] != 'success':
                collection._disconnect()
        attempt['ended_at'] = utc_now()
        event['attempts'].append(attempt)
        event['selected_at'] = utc_now()
        if attempt['outcome'] == 'success':
            try:
                _record_selection(collection, event, latest_path)
            except SoilDataSourceError:
                collection._disconnect()
                raise
            return collection
    validate_selection(event)
    _publish_latest(latest_path, event)
    raise SoilSourceSelectionError(event)
