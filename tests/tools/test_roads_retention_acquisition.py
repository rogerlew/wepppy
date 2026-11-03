"""Offline acquisition evidence and owned-cache association, without soil builds."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sqlite3
import xml.etree.ElementTree as ET

import pytest
import requests

pytestmark = pytest.mark.unit
PATH = Path(__file__).resolve().parents[2] / 'docs/work-packages/20261029_roads_parameterization_program/artifacts/acquire_r7_retention_source.py'


@pytest.fixture(scope='module')
def helper():
    spec = importlib.util.spec_from_file_location('roads_retention_acquisition', PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def xml_payload(query, values):
    fields = [field.strip().split('.')[-1] for field in query.split('FROM', 1)[0][7:].split(',')]
    root = ET.Element('NewDataSet')
    tag = '{http://www.w3.org/2001/XMLSchema}'
    schema = ET.SubElement(root, tag + 'schema')
    element = ET.SubElement(schema, tag + 'element', name='Table')
    sequence = ET.SubElement(ET.SubElement(element, tag + 'complexType'), tag + 'sequence')
    for field in fields:
        ET.SubElement(sequence, tag + 'element', name=field)
    for value in values:
        row = ET.SubElement(root, 'Table')
        for field in fields:
            child = ET.SubElement(row, field)
            token = value.get(field)
            child.text = str(token) if token is not None else None
    return ET.tostring(root)


@pytest.fixture
def cohort(helper):
    components = [dict(mukey=key, cokey=key * 10, compname='first', comppct_r=100,
                       hydricrating='No', muname='001') for key in helper.MUKEYS]
    # One known component lacks horizon support; each map unit still has a horizon.
    components.append(dict(components[0], cokey=999, comppct_r=0))
    components.insert(1, dict(components[0], compname='discarded duplicate'))
    horizons = [dict(cokey=key * 10, chkey=key * 100, hzname='A', hzdepb_r='20.0',
                     hzdept_r=0, dbthirdbar_r='1.5', wthirdbar_r='16.2', wfifteenbar_r='7.2')
                for key in helper.MUKEYS]
    return dict(component=components, chorizon=horizons,
        corestrictions=[dict(cokey=key * 10, reskind='Lithic') for key in helper.MUKEYS[1:]],
        chfrags=[dict(chkey=key * 100, fragvol_r=value) for key in helper.MUKEYS[1:] for value in (3, 99)],
        chtexturegrp=[dict(chkey=key * 100, texture=value) for key in helper.MUKEYS for value in ('L', 'discarded')])


@pytest.fixture
def declared(helper, tmp_path, monkeypatch):
    root = tmp_path / 'cohort'
    def unexpected_network(*args, **kwargs):
        pytest.fail('Declaration must not access transport')
    monkeypatch.setattr(helper.ssurgo.requests, 'post', unexpected_network)
    helper.declare(root)
    helper.save(root / 'execution-review.json', dict(declaration_sha256=helper.sha(root / 'declaration.json'),
        implementation_review_pass=True, scientific_review_pass=True, files={str(PATH): helper.sha(PATH)}))
    return root


def transport_for(helper, cohort, *, status=200):
    calls = []
    def post(url, *, data, headers, timeout):
        table = data['query'].split('FROM ', 1)[1].split()[0]
        calls.append(table)
        return SimpleNamespace(content=xml_payload(data['query'], cohort[table]), status_code=status,
            headers=requests.structures.CaseInsensitiveDict({
                'Date': 'Tue, 03 Nov 2026 00:00:00 GMT', 'Content-Type': 'application/xml',
                'Set-Cookie': 'secret-test-cookie', 'X-Private': 'private-test-value'}))
    return post, calls


def test_owned_collection_finalized_raw_association_and_safe_headers(helper, declared, cohort, monkeypatch):
    transport, calls = transport_for(helper, cohort)
    monkeypatch.setattr(helper.ssurgo.requests, 'post', transport)
    helper.acquire(declared)
    assert calls == list(helper.TABLES)
    receipt = helper.read(declared / 'acquisition.json')
    association = helper.read(declared / 'cache-association.json')
    assert receipt['passed'] and receipt['source_association_valid']
    assert set(receipt['represented_mukeys']) == set(helper.MUKEYS)
    assert receipt['source_builds'] == receipt['native_calls'] == 0
    assert association['tables']['component']['raw_rows'] == 9
    assert association['tables']['component']['cached_rows'] == 8
    assert association['tables']['chorizon']['cached_bad_parent_keys'] == [999]
    assert association['tables']['chfrags']['cached_bad_parent_keys'] == [helper.MUKEYS[0] * 100]
    assert association['cache']['journal_mode'] == 'delete'
    assert not list(declared.glob('*.sqlite-*'))
    for path, value in receipt['artifacts'].items():
        assert helper.sha(declared / path) == value
    assert 'cache-association.json' in receipt['artifacts'] and 'collection.sqlite' in receipt['artifacts']
    for record in receipt['requests']:
        assert set(record['safe_response_headers']) == {'Date', 'Content-Type'}
    for path in declared.rglob('*.json'):
        assert 'secret-test-cookie' not in path.read_text() and 'private-test-value' not in path.read_text()
    with sqlite3.connect(f'file:{declared}/collection.sqlite?mode=ro&immutable=1', uri=True) as connection:
        assert connection.execute('SELECT compname,hydricrating,muname FROM component WHERE cokey=?',
                                  (helper.MUKEYS[0] * 10,)).fetchone() == ('first', 'No', '1')
        assert {row[0] for row in connection.execute('SELECT fragvol_r FROM chfrags')} == {3.0}


def test_entire_empty_auxiliary_preserves_owned_missing_parent_gap(helper, declared, cohort, monkeypatch):
    cohort['chfrags'] = []
    transport, _ = transport_for(helper, cohort)
    monkeypatch.setattr(helper.ssurgo.requests, 'post', transport)
    helper.acquire(declared)
    result = helper.read(declared / 'cache-association.json')['tables']['chfrags']
    assert result['empty_response_early_return']
    assert len(result['missing_parent_keys']) == 7 and result['cached_bad_parent_keys'] == []


@pytest.mark.parametrize('kind', ['value', 'bad_parent', 'row'])
def test_finalized_cache_tampering_cannot_retain_association(helper, declared, cohort, monkeypatch, kind):
    transport, _ = transport_for(helper, cohort)
    monkeypatch.setattr(helper.ssurgo.requests, 'post', transport)
    helper.acquire(declared)
    with sqlite3.connect(declared / 'collection.sqlite') as connection:
        if kind == 'value':
            connection.execute('UPDATE chorizon SET wthirdbar_r=17.2')
        elif kind == 'row':
            connection.execute('DELETE FROM component WHERE cokey=999')
        else:
            connection.execute('DELETE FROM bad_chorizon_cokey')
    with pytest.raises(ValueError, match='differ|disagree'):
        helper.compare_cache(declared, helper.read(declared / 'declaration.json'),
                             helper.read(declared / 'acquisition.json')['requests'])


def test_owned_timeout_retry_retains_both_attempts(helper, declared, cohort, monkeypatch):
    success, calls = transport_for(helper, cohort)
    first = True
    def retry(*args, **kwargs):
        nonlocal first
        if first:
            first = False
            raise requests.exceptions.ConnectTimeout('do not serialize request exception')
        return success(*args, **kwargs)
    monkeypatch.setattr(helper.ssurgo.requests, 'post', retry)
    monkeypatch.setattr(helper.ssurgo.time, 'sleep', lambda seconds: None)
    helper.acquire(declared)
    receipt = helper.read(declared / 'acquisition.json')
    assert len(receipt['requests']) == 6
    assert receipt['requests'][0]['error_class'] == 'ConnectTimeout'
    assert receipt['requests'][1]['attempt'] == 2 and receipt['passed']
    assert calls == list(helper.TABLES)


@pytest.mark.parametrize('failure', ['http', 'missing_material', 'foreign_parent'])
def test_partial_failure_has_false_association_and_retained_raw_evidence(helper, declared, cohort, monkeypatch, failure):
    if failure == 'missing_material':
        cohort['component'] = [row for row in cohort['component'] if row['mukey'] != helper.MUKEYS[-1]]
    if failure == 'foreign_parent':
        cohort['chorizon'][0]['cokey'] = 12345
    transport, _ = transport_for(helper, cohort, status=503 if failure == 'http' else 200)
    monkeypatch.setattr(helper.ssurgo.requests, 'post', transport)
    with pytest.raises(SystemExit, match='Acquisition failed'):
        helper.acquire(declared)
    receipt = helper.read(declared / 'acquisition.json')
    assert not receipt['passed'] and not receipt['source_association_valid']
    assert receipt['association_sha256'] is None
    assert list((declared / 'requests').glob('*.xml'))
    assert not (declared / 'cache-association.json').exists()


def test_receipt_drift_blocks_before_transport(helper, declared, cohort, monkeypatch):
    transport, calls = transport_for(helper, cohort)
    monkeypatch.setattr(helper.ssurgo.requests, 'post', transport)
    with (declared / 'declaration.json').open('a') as stream:
        stream.write('\n')
    with pytest.raises(ValueError, match='identity mismatch'):
        helper.acquire(declared)
    assert calls == [] and not (declared / 'acquisition-start.json').exists()


def test_empty_xml_values_preserved_and_omitted_values_rejected(helper):
    query = helper.owned_query('chfrags', [100])
    raw = xml_payload(query, [dict(chkey=100, fragvol_r=None)])
    assert helper.projection(raw, query)[2] == [[100, None]]
    root = ET.fromstring(raw)
    row = root.find('Table')
    row.remove(row.find('fragvol_r'))
    with pytest.raises(ValueError, match='positional extractor'):
        helper.projection(ET.tostring(root), query)


def test_nonfinite_source_cannot_become_cache_null(helper):
    query = helper.owned_query('chfrags', [100])
    raw = xml_payload(query, [dict(chkey=100, fragvol_r='NaN')])
    with pytest.raises(ValueError, match='Nonfinite source'):
        helper.projection(raw, query)


def test_undeclared_material_is_blocked_before_transport(helper, declared, cohort):
    transport, calls = transport_for(helper, cohort)
    recorder = helper.Recorder(declared, helper.read(declared / 'declaration.json'), transport)
    query = helper.owned_query('component', list(helper.MUKEYS) + [2711196])
    with pytest.raises(ValueError, match='parent boundary'):
        recorder(helper.ssurgo._ssurgo_url, data={'query': query, 'format': 'xml'},
                 headers={'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}, timeout=30)
    assert calls == []


def test_oversize_raw_response_is_retained_as_incomplete(helper, declared, monkeypatch):
    def oversized(*args, **kwargs):
        return SimpleNamespace(content=b'x' * (helper.MAX_BYTES + 1), status_code=200, headers={})
    monkeypatch.setattr(helper.ssurgo.requests, 'post', oversized)
    with pytest.raises(SystemExit, match='Acquisition failed'):
        helper.acquire(declared)
    receipt = helper.read(declared / 'acquisition.json')
    record = receipt['requests'][0]
    assert not receipt['source_association_valid'] and not record['body_complete']
    assert (declared / record['raw_path']).stat().st_size == helper.MAX_BYTES
    assert record['response_sha256'] != record['raw_sha256']
