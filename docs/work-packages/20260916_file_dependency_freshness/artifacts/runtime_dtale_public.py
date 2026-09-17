#!/usr/bin/env python3
"""Actual authenticated public browse-to-D-Tale acceptance, after coordinated restart.

Creates a unique qa-freshness interactive run containing independently copied
Ron/Watershed metadata and generated two-row Parquet/GeoJSON fixtures. Named
source metadata is copied as bytes, never hydrated. Only copied owners hydrate.
Uses the public browse bridge, upstream grid/dtypes, and real Dash map callback;
no internal loader request, service import, response interception or HTTP stub.
Retains every attempt and disposable file. Requires root's runtime-window signal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import quote, urljoin, urlsplit
from uuid import uuid4

from runtime_project_copy import copy_one, digest_file

ARTIFACTS = Path(__file__).parent


def component_props(value, component_id):
    if isinstance(value, dict):
        props = value.get('props')
        if isinstance(props, dict) and props.get('id') == component_id:
            return props
        for child in value.values():
            found = component_props(child, component_id)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = component_props(child, component_id)
            if found is not None:
                return found
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--label', default='initial')
    parser.add_argument('--source', default='/wc1/runs/th/thespian-cleanness')
    parser.add_argument('--auth-file', help='Private JSON path; values are never retained')
    args = parser.parse_args()
    if not args.execute:
        parser.error('Pass --execute only after root confirms the restart/runtime window')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.label):
        raise ValueError('Use a simple unique artifact label')
    output = ARTIFACTS / f'dtale_public_runtime_{args.label}.json'
    if output.exists():
        raise FileExistsError('Retain prior result and choose a new --label')

    import pyarrow as pa
    import pyarrow.parquet as pq
    import runtime_http
    from wepppy.nodb.core import Watershed

    auth_file = Path(args.auth_file) if args.auth_file else Path('/tmp/wepppy-freshness-runtime-auth.json')
    if not auth_file.exists() and args.auth_file is None:
        auth_file = Path('/workdir/wepppy/docker/secrets/freshness-runtime-auth.json')
    runtime_http.AUTH_FILE = auth_file
    host, client = runtime_http.session()
    origin = urlsplit(host)
    source = Path(args.source).absolute()
    root = Path('/wc1/runs/qa') / ('qa-freshness-dtale-' + uuid4().hex[:12])
    result = {'scope': __doc__, 'started_unix': time.time(), 'uid': os.getuid(),
              'gid': os.getgid(), 'root': str(root), 'runid': root.name,
              'source': str(source), 'source_files': {}, 'http': [], 'checks': {},
              'completed': False, 'retained': [], 'limitations': [
                  'Stable shared logical dataset ID is contractual; reopened generation is fresh.',
                  'Dtypes describes the shell; the lazy grid enforces generation currentness.',
                  'Dash callback proves actual service registry and dropdown state, not rendered map pixels.',
                  'Two-row Parquet is bounded public transport acceptance, not the large-file performance gate.',
                  'A minimal copied run is not a complete watershed or native model execution.',
              ]}

    def save():
        output.write_text(json.dumps(result, indent=2) + '\n')

    def check(name, condition):
        result['checks'][name] = bool(condition)
        save()
        if not condition:
            raise AssertionError(name)

    def http(label, path, *, payload=None):
        url = urljoin(host, path)
        target = urlsplit(url)
        if (target.scheme, target.netloc) != (origin.scheme, origin.netloc):
            raise ValueError('Never forward runtime credentials across origins')
        if payload is not None and target.path != '/weppcloud/dtale/charts/_dash-update-component':
            raise ValueError('Only the actual read-only Dash layout callback may use POST')
        started = time.perf_counter()
        response = client.request('POST' if payload is not None else 'GET', url,
                                  json=payload, allow_redirects=False, timeout=120)
        row = {'label': label, 'method': 'POST' if payload is not None else 'GET',
               'path': target.path, 'query': target.query, 'status': response.status_code,
               'seconds': time.perf_counter() - started, 'bytes': len(response.content),
               'sha256': hashlib.sha256(response.content).hexdigest(),
               'content_type': response.headers.get('Content-Type')}
        # Never retain headers/cookies, credentials, HTML or arbitrary error bodies.
        result['http'].append(row)
        save()
        return response, row

    def load(label, relative='table.parquet'):
        path = f'/weppcloud/runs/{root.name}/config/dtale/{quote(relative)}'
        response, row = http(label, path)
        check(label + '_redirect', response.status_code in (302, 303, 307, 308))
        location = response.headers.get('Location', '')
        resolved = urlsplit(urljoin(host, location))
        check(label + '_same_origin', (resolved.scheme, resolved.netloc) == (origin.scheme, origin.netloc))
        match = re.fullmatch(r'/weppcloud/dtale/main/([A-Za-z0-9_-]+)', resolved.path)
        check(label + '_viewer_location', match is not None)
        data_id = match.group(1)
        row['viewer_path'], row['data_id'] = resolved.path, data_id
        response, _ = http(label + '_viewer', resolved.path)
        check(label + '_viewer_http', response.status_code == 200 and 'text/html' in response.headers.get('Content-Type', ''))
        return data_id

    def grid(label, data_id):
        response, row = http(label, f'/weppcloud/dtale/data/{data_id}?ids=%5B%220-1%22%5D')
        check(label + '_http', response.status_code == 200)
        body = response.json()
        row['body'] = body
        save()
        return body

    def schema(label, data_id):
        response, row = http(label, f'/weppcloud/dtale/dtypes/{data_id}')
        check(label + '_http', response.status_code == 200)
        row['body'] = response.json()
        save()
        return [item['name'] for item in row['body']['dtypes']]

    def map_layout(label, data_id, selected_slug='subcatchments'):
        response, row = http(label, '/weppcloud/dtale/charts/_dash-update-component', payload={
            'output': 'popup-content.children',
            'outputs': {'id': 'popup-content', 'property': 'children'},
            'inputs': [{'id': 'url', 'property': 'pathname', 'value': f'/weppcloud/dtale/charts/{data_id}'},
                       {'id': 'url', 'property': 'search', 'value': '?chart_type=maps&map_type=choropleth&loc_mode=geojson-id'}],
            'state': [], 'changedPropIds': ['url.pathname', 'url.search'],
        })
        check(label + '_http', response.status_code == 200)
        body = response.json()
        props = {name: component_props(body, name) for name in ('geojson-dropdown', 'featureidkey-dropdown')}
        row['map_components'] = props
        save()
        check(label + '_components', all(value is not None for value in props.values()))
        # Use the real dropdown-selection callback to inspect parsed registry
        # properties; initial UI defaults are a separate, unasserted behavior.
        response, selection_row = http(label + '_selection', '/weppcloud/dtale/charts/_dash-update-component', payload={
            'output': '..featureidkey-dropdown.options...featureidkey-dropdown.disabled...featureidkey-dropdown.placeholder..',
            'outputs': [{'id': 'featureidkey-dropdown', 'property': field}
                        for field in ('options', 'disabled', 'placeholder')],
            'inputs': [{'id': 'geojson-dropdown', 'property': 'value', 'value': root.name + '-' + selected_slug}],
            'state': [], 'changedPropIds': ['geojson-dropdown.value'],
        })
        check(label + '_selection_http', response.status_code == 200)
        selected = response.json()['response']['featureidkey-dropdown']
        selection_row['selected_properties'] = selected
        props['selected_properties'] = selected
        save()
        return props

    try:
        if source.resolve() != source:
            raise ValueError('The source must not traverse aliases')
        root.mkdir(mode=0o755, exist_ok=False)
        evidence = root / 'acceptance-evidence'
        evidence.mkdir()
        for name in ('config.cfg', 'ron.nodb', 'watershed.nodb'):
            path = source / name
            if path.is_symlink() or not path.is_file():
                raise ValueError('This fixture needs ordinary config/Ron/Watershed sources')
            result['source_files'][name] = copy_one(path, root / name, path.stat())
            if name.endswith('.nodb'):
                copied = root / name
                payload = json.loads(copied.read_text().replace(str(source), str(root)).replace(source.name, root.name))
                state = payload.get('py/state', payload)
                state.update(wd=str(root), _run_group=None, _group_name=None)
                state.pop('_parent_wd', None)
                copied.write_text(json.dumps(payload) + '\n')
        watershed = Watershed.getInstance(str(root))
        overlay = Path(watershed.subwta_shp)
        channel = Path(watershed.channels_shp)
        for path in (overlay, channel):
            if root not in path.absolute().parents or path.resolve() != path.absolute():
                raise ValueError('Copied Watershed selected a non-disposable overlay path')
            path.parent.mkdir(parents=True, exist_ok=True)

        feature = {'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'properties': {'wepp_id': 1, 'topaz_id': 11, 'mark_old': 'v1'},
             'geometry': {'type': 'Polygon', 'coordinates': [[[-107, 40], [-106, 40], [-106, 41], [-107, 40]]]}}
        ]}
        old_geo = json.dumps(feature, separators=(',', ':')).encode()
        new_geo = old_geo.replace(b'mark_old', b'mark_new')
        overlay.write_bytes(old_geo)
        channel.write_bytes(old_geo)
        for name, content in [('before.geojson', old_geo), ('after.geojson', new_geo)]:
            (evidence / name).write_bytes(content)
        versions = []
        for column, values in [('a', [1, 2]), ('z', [8, 9])]:
            sink = pa.BufferOutputStream()
            pq.write_table(pa.table({'wepp_id': [1, 2], column: values}), sink,
                           compression='NONE', use_dictionary=False, write_statistics=False)
            versions.append(sink.getvalue().to_pybytes())
        check('equal_size_parquet_fixture', len(versions[0]) == len(versions[1]))
        table = root / 'table.parquet'
        table.write_bytes(versions[0])
        for name, content in [('before.parquet', versions[0]), ('after.parquet', versions[1])]:
            (evidence / name).write_bytes(content)
        result['retained'] = [str(path) for path in sorted(evidence.iterdir())]
        result['fixture_hashes'] = {path.name: digest_file(path) for path in sorted(evidence.iterdir())}
        response, _ = http('browse_table', f'/weppcloud/runs/{root.name}/config/browse/table.parquet')
        check('browse_table_success', response.status_code == 200)
        first_id = load('first')
        first = grid('first_grid', first_id)
        check('first_schema', 'a' in schema('first_schema', first_id))
        check('first_rows', [int(first['results'][str(index)]['a']) for index in range(2)] == [1, 2])
        first_map = map_layout('first_map', first_id)
        overlay_key = root.name + '-subcatchments'
        check('map_registered', overlay_key in [item['value'] for item in first_map['geojson-dropdown']['options']])
        check('map_original_properties', 'mark_old' in [item['value'] for item in first_map['selected_properties']['options']])

        info = table.stat()
        os.utime(table, ns=(info.st_atime_ns, info.st_mtime_ns + 2_000_000_000))
        check('metadata_only_logical_id', load('touch') == first_id)
        check('metadata_only_rows', grid('touch_grid', first_id) == first)
        table.write_bytes(versions[0])
        os.utime(table, ns=(info.st_atime_ns, info.st_mtime_ns))
        check('same_bytes_logical_id', load('same_bytes') == first_id)
        check('same_bytes_rows', grid('same_bytes_grid', first_id) == first)

        table.write_bytes(versions[1])
        os.utime(table, ns=(info.st_atime_ns, info.st_mtime_ns))
        check('changed_same_size_mtime', table.stat().st_size == info.st_size and table.stat().st_mtime_ns == info.st_mtime_ns)
        old = grid('old_generation_grid', first_id)
        check('old_grid_visible_conflict', old.get('success') is False and old.get('code') == 'changed_source' and isinstance(old.get('error'), str))
        check('old_grid_no_success_payload', not ({'columns', 'results', 'total'} & old.keys()))
        check('old_shell_schema_retained', 'a' in schema('old_shell_schema', first_id) and 'z' not in schema('old_shell_schema_repeat', first_id))
        check('reopened_shared_logical_id', load('reopened') == first_id)
        fresh = grid('fresh_grid', first_id)
        names = schema('fresh_schema', first_id)
        check('fresh_schema_replaced', 'z' in names and 'a' not in names)
        check('fresh_rows', [int(fresh['results'][str(index)]['z']) for index in range(2)] == [8, 9])

        geo_info = overlay.stat()
        overlay.write_bytes(new_geo)
        os.utime(overlay, ns=(geo_info.st_atime_ns, geo_info.st_mtime_ns))
        check('map_same_size_mtime', overlay.stat().st_size == geo_info.st_size and overlay.stat().st_mtime_ns == geo_info.st_mtime_ns)
        check('map_change_table_id_reused', load('map_changed') == first_id)
        props = map_layout('changed_map', first_id)
        property_names = [item['value'] for item in props['selected_properties']['options']]
        check('map_actual_registration_refreshed', 'mark_new' in property_names and 'mark_old' not in property_names)
        overlay.rename(evidence / 'removed-overlay.geojson')
        check('optional_map_missing_table_available', load('map_removed') == first_id)
        props = map_layout('removed_map', first_id, selected_slug='channels')
        check('missing_map_registration_removed', overlay_key not in [item['value'] for item in props['geojson-dropdown']['options']])
        check('remaining_map_registered', root.name + '-channels' in [item['value'] for item in props['geojson-dropdown']['options']])
        result['completed'] = True
    except BaseException as exc:  # Acceptance boundary: preserve failures without leaking request/secret details.
        result['error'] = {'type': type(exc).__name__, 'message': str(exc) if isinstance(exc, AssertionError) else 'Details omitted; inspect the last retained phase/status and fixture.'}
        raise
    finally:
        unchanged = True
        for name, original in result['source_files'].items():
            try:
                current = digest_file(source / name)
                same = current['sha256'] == original['sha256'] and current['version'] == original['version']
            except OSError:
                same = False
            unchanged = unchanged and same
        result['named_source_unchanged'] = unchanged
        result['completed'] = result['completed'] and unchanged
        result['finished_unix'] = time.time()
        save()
        client.close()
    if not result['completed']:
        raise AssertionError('Public D-Tale acceptance did not complete')
    print('Public D-Tale acceptance passed:', output, flush=True)


if __name__ == '__main__':
    main()
