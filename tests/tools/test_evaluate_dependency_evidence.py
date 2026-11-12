"""Fail-closed dependency policy with complete synthetic evidence bundles."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

import pytest

from tools.security import evaluate_dependency_evidence as gate

pytestmark = pytest.mark.unit
NOW = datetime(2026, 11, 12, 3, tzinfo=timezone.utc)
STAMP = NOW.isoformat()
IMAGE = 'sha256:' + 'a' * 64
POLICY = Path(__file__).resolve().parents[2] / 'docs/work-packages/20261110_wepp1_dependency_security_gate/artifacts/20261110_scope_and_policy_decision.md'


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    artifacts = [{'id':kind, 'name':name, 'version':'1.0', 'type':kind,
                  'locations':[{'path':'/'+name}]} for kind,name in [('python','flask'),('deb','libc6')]]
    lock = {'lockfileVersion':3, 'packages':{'':{'name':'fixture'},'node_modules/example':{'version':'1.0.0'}}}
    scope = json.loads((POLICY.parents[4] / 'tools/security/scanner_scope.json').read_text())
    lock_raw = json.dumps(lock).encode()
    lock_hash = gate.digest(lock_raw)
    scientific_config = {'exclude': ['/data/*.par']}
    scientific_manifest = [{'path': '/data/station.par', 'size': 1, 'sha256': 'd' * 64}]
    monkeypatch.setattr(gate, 'SCIENTIFIC_CONFIG_HASH', gate.digest(json.dumps(scientific_config).encode()))
    monkeypatch.setattr(gate, 'SCIENTIFIC_MANIFEST_HASH', gate.digest(json.dumps(scientific_manifest).encode()))
    probe_raw = Path(gate.__file__).with_name('archive_inventory.py').read_bytes()
    data = {
        'scientific-config.json': scientific_config,
        'scientific-manifest.json': scientific_manifest,
        'build-receipt.json': {'image_id': IMAGE, 'source_revision': 'b' * 40, 'source_clean': True,
                               'exit_status': 0, 'static_build_lock_sha256': lock_hash},
        'syft.json': {'schema':{'version':'16.1.13'}, 'descriptor':{'name':'syft','version':'1.57.1', 'configuration':scope['syft']},
                      'source':{'type':'image','metadata':{'imageID':IMAGE}}, 'artifacts':artifacts, 'files':[{'location':{'path':'/known.so'},'executable':{'format':'elf'},'digests':[{'algorithm':'sha256','value':'c'*64}]}]},
        'grype.json': {'source':{'type':'image','target':{'imageID':IMAGE}},'distro':{},
                      'descriptor':{'name':'grype','version':'0.121.3','timestamp':STAMP,
                                    'db':{'status':{'valid':True,'schemaVersion':'v6.1.10','built':STAMP}},
                                    'configuration':scope['grype']},
                      'matches':[], 'ignoredMatches':[]},
        'npm-audit.json': {'auditReportVersion':2, 'vulnerabilities':{},
                           'metadata':{'dependencies':{'total':1},'vulnerabilities':{'total':0}}},
        'package-lock.json':lock,
        'inventory.json': {'image_id':IMAGE, 'scientific_files_verified': 1, 'static_build_lock_sha256': lock_hash,
                           'python':[{'name':'flask','version':'1.0','path':'/flask'}],
                           'deb':[{'name':'libc6','version':'1.0','path':'/libc6'}], 'native_files':[{'path':'/known.so','sha256':'c'*64}]},
        'receipt.json': {'schema_version':1, 'image_id':IMAGE,'lock_sha256':lock_hash,
                         'source_revision':'b'*40,'source_clean':True,'scanned_at':STAMP,
                         'database_refreshed_at':STAMP,'database_refresh_exit':0,'syft_exit':0,'grype_exit':0,
                         'inventory_exit':0,'npm_exit':0,'analysis_errors':[],
                         'inventory_method':'never-started-export-v1', 'inventory_probe_sha256':gate.digest(probe_raw),
                         'scientific_files_verified':1, 'scientific_config_sha256':gate.SCIENTIFIC_CONFIG_HASH,
                         'scientific_manifest_sha256':gate.SCIENTIFIC_MANIFEST_HASH,
                         'tool_versions':gate.TOOL_VERSIONS, 'tool_sha256':gate.TOOL_HASHES,
                         'npm_command':gate.NPM_COMMAND, 'npm_config':gate.NPM_CONFIG, 'npm_lock_hash_before':lock_hash, 'npm_lock_hash_after':lock_hash,
                         'static_build_lock_sha256':lock_hash,'npm_audited_at':STAMP,'npm_scope':'all-lock-dependencies'},
    }
    approvals = {'schema_version':1,'image_id':IMAGE,'lock_sha256':lock_hash,'findings':[], 'native_coverage':[]}
    with sqlite3.connect(tmp_path / 'vulnerability.db') as conn:
        conn.execute('CREATE TABLE db_metadata(build_timestamp TEXT, model INTEGER, revision INTEGER, addition INTEGER)')
        conn.execute('INSERT INTO db_metadata VALUES (?,6,1,10)', (STAMP,))

    def write():
        (tmp_path/'archive_inventory.py').write_bytes(probe_raw)
        for name,value in data.items():
            (tmp_path/name).write_text(json.dumps(value))
        receipt = data['receipt.json']
        receipt['build_receipt_sha256'] = gate.digest((tmp_path/'build-receipt.json').read_bytes())
        receipt['npm_report_sha256'] = gate.digest((tmp_path/'npm-audit.json').read_bytes())
        for label,name in [('database','vulnerability.db'),('sbom','syft.json')]:
            receipt[label+'_hash_before'] = receipt[label+'_hash_after'] = gate.digest((tmp_path/name).read_bytes())
        (tmp_path/'receipt.json').write_text(json.dumps(receipt))
        manifest = {'schema_version':1,'image_id':IMAGE,'files':{}}
        for name in gate.REQUIRED:
            (tmp_path/name).chmod(0o600)
            raw=(tmp_path/name).read_bytes()
            manifest['files'][name]={'sha256':gate.digest(raw),'size_bytes':len(raw)}
        manifest_raw=json.dumps(manifest).encode()
        (tmp_path/'manifest.json').write_bytes(manifest_raw)
        approval_raw=json.dumps(approvals).encode()
        (tmp_path/'approvals.json').write_bytes(approval_raw)
        return dict(bundle=tmp_path, manifest_hash=gate.digest(manifest_raw), image_id=IMAGE,
                    lock_hash=lock_hash, source_revision='b'*40, policy=POLICY, policy_hash=gate.POLICY_SHA256,
                    dispositions=tmp_path/'approvals.json', dispositions_hash=gate.digest(approval_raw), now=NOW)
    return data, approvals, write


def finding(data):
    return {'artifact':copy.deepcopy(data['syft.json']['artifacts'][0]),
            'vulnerability':{'id':'CVE-fixture','namespace':'nvd:cpe','severity':'High'}, 'relatedVulnerabilities':[]}


def test_clean_complete_bundle(evidence):
    data, approvals, write=evidence
    assert gate.evaluate(**write())['accepted']


@pytest.mark.parametrize('source', ['matches','ignoredMatches'])
def test_ignored_and_primary_findings_both_block(evidence, source):
    data, _, write=evidence
    data['grype.json'][source].append(finding(data))
    result=gate.evaluate(**write())
    assert result['accepted'] is False
    assert result['blocking'] == {'High':1}


def test_exact_approved_finding_and_expiry(evidence):
    data, approvals, write=evidence
    row=finding(data)
    data['grype.json']['matches'].append(row)
    approvals['findings'].append({'key':gate.finding_key('matches',row),'disposition':'accepted-risk',
        'owner':'fixture owner','approver':'fixture reviewer','rationale':'fixture only',
        'evidence':'private receipt','compensating_control':'fixture control','created_at':STAMP,
        'expires_at':(NOW+timedelta(days=1)).isoformat(),'review_trigger':'fixture trigger'})
    assert gate.evaluate(**write())['accepted']
    approvals['findings'][0]['expires_at']=(NOW-timedelta(seconds=1)).isoformat()
    with pytest.raises(gate.EvidenceError, match='expired'):
        gate.evaluate(**write())


@pytest.mark.parametrize('mutation', ['stale','future','image','tool','parser','inventory','database','filter','unknown_schema','npm_error','dirty'])
def test_adverse_evidence_fails_closed(evidence, mutation):
    data, _, write=evidence
    if mutation=='stale': data['receipt.json']['scanned_at']=(NOW-timedelta(hours=25)).isoformat()
    if mutation=='future': data['receipt.json']['scanned_at']=(NOW+timedelta(minutes=6)).isoformat()
    if mutation=='image': data['grype.json']['source']['target']['imageID']='sha256:'+'b'*64
    if mutation=='tool': data['syft.json']['descriptor']['version']='unqualified'
    if mutation=='parser': data['syft.json']['files']=[{'unknowns':['parser panic']}]
    if mutation=='inventory': data['inventory.json']['python'].append({'name':'missing','version':'1'})
    if mutation=='database': data['grype.json']['descriptor']['db']['status']['built']=(NOW-timedelta(hours=1)).isoformat()
    if mutation=='filter': data['grype.json']['descriptor']['configuration']['only-fixed']=True
    if mutation=='unknown_schema': data['syft.json']['schema']['version']='17'
    if mutation=='npm_error': data['npm-audit.json']['error']={'message':'remote failure'}
    if mutation=='dirty': data['receipt.json']['source_clean']=False
    with pytest.raises(gate.EvidenceError): gate.evaluate(**write())


@pytest.mark.parametrize('target', ['manifest.json','syft.json','vulnerability.db','approvals.json'])
def test_tampered_bytes_rejected(evidence,target):
    _, _, write=evidence
    kwargs=write()
    path=kwargs['bundle']/target
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(gate.EvidenceError): gate.evaluate(**kwargs)


def test_arbitrary_policy_hash_does_not_define_implemented_policy(evidence):
    _, _, write=evidence
    kwargs=write(); kwargs['policy_hash']='f'*64
    with pytest.raises(gate.EvidenceError,match='not implemented'): gate.evaluate(**kwargs)


def test_native_executable_cannot_disappear(evidence):
    data, _, write=evidence
    data['syft.json']['files']=[{'location':{'path':'/lib/unidentified.so'},
        'unknowns':['unknowns-labeler: no package identified in executable file']}]
    with pytest.raises(gate.EvidenceError,match='native'): gate.evaluate(**write())


def test_related_higher_severity_cannot_be_downgraded(evidence):
    data, _, write = evidence
    row = finding(data)
    row['vulnerability']['severity'] = 'Low'
    row['relatedVulnerabilities'] = [{'id':'related-CVE','namespace':'nvd:cpe','severity':'Critical'}]
    data['grype.json']['matches'].append(row)
    assert gate.evaluate(**write())['blocking'] == {'Critical':1}


@pytest.mark.parametrize('change', ['catalogers','omitted_file','file_error','npm_scope'])
def test_coverage_reviewer_regressions(evidence, change):
    data, _, write = evidence
    if change == 'catalogers':
        data['syft.json']['descriptor']['configuration']['catalogers']['used'] = ['dpkg-db-cataloger']
    elif change == 'omitted_file':
        data['inventory.json']['native_files'] = [{'path':'/omitted.so','sha256':'e'*64}]
    elif change == 'file_error':
        data['syft.json']['files'] = [{'errors':['parser failed']}]
    else:
        data['npm-audit.json']['metadata']['dependencies']['total'] = 2
    with pytest.raises(gate.EvidenceError):
        gate.evaluate(**write())


def test_production_only_npm_command_rejected(evidence):
    data, _, write = evidence
    data['receipt.json']['npm_command'] = ['npm','audit','--json','--omit=dev']
    with pytest.raises(gate.EvidenceError, match='command/config'):
        gate.evaluate(**write())


def test_python_inventory_pep503_name_normalization(evidence):
    data, _, write = evidence
    data['syft.json']['artifacts'][0]['name'] = 'backports-zstd'
    data['inventory.json']['python'][0]['name'] = 'backports.zstd'
    assert gate.evaluate(**write())['accepted']


@pytest.mark.parametrize('field,value', [('distro','alpine:3.22'),('add-cpes-if-none',True)])
def test_matching_configuration_cannot_change(evidence, field, value):
    data, _, write = evidence
    data['grype.json']['descriptor']['configuration'][field] = value
    with pytest.raises(gate.EvidenceError, match='scope'):
        gate.evaluate(**write())


def test_known_executable_digest_must_match_direct_inventory(evidence):
    data, _, write = evidence
    data['syft.json']['files'] = [{'location':{'path':'/known.so'},'executable':{'format':'elf'},
        'digests':[{'algorithm':'sha256','value':'d'*64}]}]
    data['inventory.json']['native_files'] = [{'path':'/known.so','sha256':'c'*64}]
    with pytest.raises(gate.EvidenceError, match='digest differs'):
        gate.evaluate(**write())


def test_empty_native_hash_cannot_be_approved(evidence):
    data, approvals, write = evidence
    data['syft.json']['files'] = [{'location':{'path':'/unknown.so'},'executable':{'format':'elf'},
        'unknowns':['unknowns-labeler: no package identified in executable file']}]
    data['inventory.json']['native_files'] = [{'path':'/unknown.so','sha256':''}]
    approvals['native_coverage'] = [{'file_sha256':'','paths':['/unknown.so'],'owner':True,
        'approver':True,'evidence':True,'advisory_coverage':True}]
    with pytest.raises(gate.EvidenceError, match='native file hash'):
        gate.evaluate(**write())


def test_grype_key_preserves_identity_without_daily_epss_noise(evidence):
    data, _, _ = evidence
    row = finding(data)
    before = gate.finding_key('matches',row)
    row['vulnerability']['epss'] = [{'date':'2026-11-12','score':0.3}]
    assert gate.finding_key('matches',row) == before
    row['artifact']['locations'][0]['path'] = '/another-installation'
    assert gate.finding_key('matches',row) != before


def test_empty_native_evidence_rejected(evidence):
    data, _, write = evidence
    data['syft.json']['files'] = []
    data['inventory.json']['native_files'] = []
    with pytest.raises(gate.EvidenceError, match='native executable inventory empty'):
        gate.evaluate(**write())


def test_malformed_low_advisory_cannot_pass(evidence):
    data, _, write = evidence
    row = finding(data)
    row['vulnerability'] = {'severity':'Low'}
    data['grype.json']['matches'].append(row)
    with pytest.raises(gate.EvidenceError, match='advisory identity'):
        gate.evaluate(**write())


@pytest.mark.parametrize('change', ['exclude', 'manifest', 'count', 'method', 'probe', 'build', 'lock'])
def test_producer_authority_evidence_is_required(evidence, change):
    data, _, write = evidence
    if change == 'exclude':
        data['scientific-config.json']['exclude'].append('/all/**')
    elif change == 'manifest':
        data['scientific-manifest.json'][0]['sha256'] = 'e' * 64
    elif change == 'count':
        data['receipt.json']['scientific_files_verified'] = 0
    elif change == 'method':
        data['receipt.json']['inventory_method'] = 'candidate-python-startup'
    elif change == 'probe':
        data['receipt.json']['inventory_probe_sha256'] = 'e' * 64
    elif change == 'build':
        data['build-receipt.json']['source_clean'] = False
    else:
        data['inventory.json']['static_build_lock_sha256'] = 'e' * 64
    with pytest.raises(gate.EvidenceError):
        gate.evaluate(**write())
