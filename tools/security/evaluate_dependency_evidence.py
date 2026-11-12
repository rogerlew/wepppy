#!/usr/bin/env python3
"""Evaluate a privately retained, independently identified dependency bundle.

This is a policy component; it does not collect evidence or authorize deployment.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import sqlite3
import stat
import os

from tools.security.import_dependency_evidence import EvidenceError, _validate_manifest

POLICY_SHA256 = '2c381b5cf53b40278a1145d8bbf32e314647be8328010aaa9005ae414cd4e6be'
REQUIRED = {'syft.json', 'grype.json', 'npm-audit.json', 'package-lock.json',
            'inventory.json', 'receipt.json', 'vulnerability.db',
            'scientific-config.json', 'scientific-manifest.json',
            'build-receipt.json', 'archive_inventory.py'}
SCIENTIFIC_CONFIG_HASH = '11ed929c6c6d2ef2b689eee0a6bbb14c58e3a98b1897f9115636512d5a98d3e9'
SCIENTIFIC_MANIFEST_HASH = '593b9e98a66da5ceda2c4efbb6c12fbe08d997dd00e817ec06a3fd3fe1074812'
TOOL_VERSIONS = {'syft': '1.57.1', 'grype': '0.121.3'}
TOOL_HASHES = {
    'syft': 'de3982edbbc250c4a40764c7b1f30bbf54b681f9b99391ee6b85bfdfa5d4dffe',
    'grype': '30f8f7de5dda71952a20d4955034d30a081a5d10e6bd00d67ce78b56fd0251dc',
}
NPM_COMMAND = ['npm', 'audit', '--package-lock-only', '--json', '--include=dev', '--include=optional', '--include=peer', '--ignore-scripts']
NPM_CONFIG = {'omit': [], 'include': ['dev', 'optional', 'peer'], 'production': False}
SEVERITIES = {'Critical', 'High', 'Medium', 'Low', 'Negligible', 'Unknown'}
ECOSYSTEMS = {'python', 'deb', 'npm', 'binary', 'rust-crate', 'go-module'}
SCOPE_HASHES = {'syft': 'da255fd4efbfaff93f3cee3e40397449e984b81c32d26b75cfbb1f710ce238c5',
                'grype': '7e3e6b4ec1dffc9ff1538fa5b0697751c5326189e25d6874210ca4d915a2c282'}
SEVERITY_RANK = {'Negligible':0, 'Low':1, 'Medium':2, 'High':3, 'Critical':4, 'Unknown':5}



def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def read_json(raw):
    return json.loads(raw, object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(EvidenceError('nonfinite JSON number')))


def timestamp(value):
    require(isinstance(value, str), 'missing timestamp')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'timestamp must include timezone')
    return result


def fresh(value, now):
    result = timestamp(value)
    require(now - timedelta(hours=24) <= result <= now + timedelta(minutes=5), 'stale or future evidence')
    return result


def package_name(name, ecosystem):
    return re.sub(r'[-_.]+', '-', name).lower() if ecosystem == 'python' else name


def finding_key(source, row):
    if source == 'npm':
        # npm rows describe both direct advisories and transitive dependency
        # relationships. Retain the whole supported row until normalized by
        # an independently reviewed producer; changed guidance needs re-review.
        identity = row
    else:
        artifact = row['artifact']
        identity = {'artifact':{key:artifact[key] for key in ('id','name','version','type','locations')},
                    'advisories':sorted(
                        ({key:item.get(key) for key in ('id','namespace','severity')}
                         for item in [row['vulnerability'], *row['relatedVulnerabilities']]),
                        key=canonical_hash)}
    return canonical_hash({'source': source, 'identity': identity})


def checked_file(path, expected):
    require(re.fullmatch('[0-9a-f]{64}', expected or '') is not None, 'invalid trusted hash')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode), 'expected regular evidence file')
        data = stream.read()
        after = os.fstat(stream.fileno())
    require((before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
            (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'evidence changed while reading')
    require(digest(data) == expected, 'trusted hash mismatch')
    return data


def approved_records(raw, expected_hash, image_id, lock_hash, now):
    require(digest(raw) == expected_hash, 'disposition approval hash mismatch')
    value = read_json(raw)
    require(set(value) == {'schema_version', 'image_id', 'lock_sha256', 'findings', 'native_coverage'},
            'unsupported approval schema')
    require(type(value['schema_version']) is int and value['schema_version'] == 1, 'unsupported approval version')
    require(value['image_id'] == image_id and value['lock_sha256'] == lock_hash, 'approval subject mismatch')
    entries = {}
    for entry in value['findings']:
        require(set(entry) == {'key', 'disposition', 'owner', 'approver', 'rationale', 'evidence',
                              'compensating_control', 'created_at', 'expires_at', 'review_trigger'},
                'unsupported disposition fields')
        require(entry['key'] not in entries, 'duplicate/conflicting disposition')
        require(entry['disposition'] in {'not-affected', 'verified-not-present', 'accepted-risk'},
                'present finding cannot be labeled fixed or silently deferred')
        for field in ('owner', 'approver', 'rationale', 'evidence', 'compensating_control', 'review_trigger'):
            require(isinstance(entry[field], str) and entry[field].strip(), 'incomplete disposition')
        created, expires = timestamp(entry['created_at']), timestamp(entry['expires_at'])
        require(created <= now + timedelta(minutes=5) and now < expires and created < expires,
                'expired or future disposition')
        if entry['disposition'] == 'accepted-risk':
            require(expires - created <= timedelta(days=30), 'risk acceptance exceeds 30 days')
        entries[entry['key']] = entry
    return entries, value['native_coverage']


def evaluate(bundle: Path, *, manifest_hash: str, image_id: str, lock_hash: str,
             source_revision: str, policy: Path, policy_hash: str, dispositions: Path, dispositions_hash: str,
             now=None):
    now = now or datetime.now(timezone.utc)
    bundle = bundle.resolve(strict=True)
    require(stat.S_IMODE(bundle.stat().st_mode) == 0o700, 'bundle directory must be private')
    require(policy_hash == POLICY_SHA256, 'policy revision is not implemented by this evaluator')
    checked_file(policy, policy_hash)
    manifest_raw = checked_file(bundle / 'manifest.json', manifest_hash)
    manifest = _validate_manifest(manifest_raw, manifest_hash, image_id)
    require(REQUIRED <= set(manifest['files']), 'missing required evidence role')
    files = {}
    for name, record in manifest['files'].items():
        metadata = (bundle / name).lstat()
        require(stat.S_ISREG(metadata.st_mode) and stat.S_IMODE(metadata.st_mode) == 0o600,
                'evidence must be private regular files')
        data = checked_file(bundle / name, record['sha256'])
        require(len(data) == record['size_bytes'], 'evidence size mismatch')
        if name in REQUIRED and name.endswith('.json'):
            files[name] = read_json(data)
    require(manifest['files']['package-lock.json']['sha256'] == lock_hash, 'lock identity mismatch')
    receipt = files['receipt.json']
    require(type(receipt['schema_version']) is int and receipt['schema_version'] == 1, 'unsupported receipt version')
    require(receipt['image_id'] == image_id and receipt['lock_sha256'] == lock_hash, 'receipt subject mismatch')
    require(receipt['source_revision'] == source_revision and re.fullmatch('[0-9a-f]{40}', source_revision) is not None and receipt['source_clean'] is True,
            'clean exact source identity required')
    build = files['build-receipt.json']
    require(build['image_id'] == image_id and build['source_revision'] == source_revision
            and build['source_clean'] is True and type(build['exit_status']) is int
            and build['exit_status'] == 0 and build['static_build_lock_sha256'] == lock_hash,
            'build receipt subject/state mismatch')
    require(receipt['build_receipt_sha256'] == manifest['files']['build-receipt.json']['sha256'],
            'build receipt hash mismatch')
    for role, expected in [('scientific-config.json', SCIENTIFIC_CONFIG_HASH),
                           ('scientific-manifest.json', SCIENTIFIC_MANIFEST_HASH)]:
        require(manifest['files'][role]['sha256'] == expected, 'unqualified scientific exclusion input')
    require(receipt['scientific_config_sha256'] == SCIENTIFIC_CONFIG_HASH and
            receipt['scientific_manifest_sha256'] == SCIENTIFIC_MANIFEST_HASH,
            'scientific exclusion receipt mismatch')
    require(receipt['inventory_method'] == 'never-started-export-v1', 'unqualified inventory authority')
    probe_hash = digest(Path(__file__).with_name('archive_inventory.py').read_bytes())
    require(manifest['files']['archive_inventory.py']['sha256'] == probe_hash == receipt['inventory_probe_sha256'],
            'unqualified inventory probe')
    require(type(receipt['scientific_files_verified']) is int and
            receipt['scientific_files_verified'] == len(files['scientific-manifest.json']) ==
            files['inventory.json']['scientific_files_verified'], 'incomplete scientific file verification')
    require(files['inventory.json']['static_build_lock_sha256'] == lock_hash, 'inventory lock mismatch')
    scan_time = fresh(receipt['scanned_at'], now)
    refresh_time = fresh(receipt['database_refreshed_at'], now)
    require(refresh_time <= scan_time, 'database refresh must precede scan')
    for field in ('database_refresh_exit', 'syft_exit', 'grype_exit', 'inventory_exit'):
        require(type(receipt[field]) is int and receipt[field] == 0, 'failed evidence command')
    # npm audit intentionally exits 1 when advisories exist; those rows are evaluated below.
    require(type(receipt['npm_exit']) is int and receipt['npm_exit'] in {0, 1}, 'failed npm audit command')
    db_hash = manifest['files']['vulnerability.db']['sha256']
    require(receipt['database_hash_before'] == receipt['database_hash_after'] == db_hash,
            'database changed or is not retained')
    require(receipt['sbom_hash_before'] == receipt['sbom_hash_after'] == manifest['files']['syft.json']['sha256'],
            'SBOM changed during scan')
    require(receipt['analysis_errors'] == [], 'unresolved parser/matcher diagnostics')
    require(receipt['tool_versions'] == TOOL_VERSIONS, 'unqualified scanner version')
    require(receipt['tool_sha256'] == TOOL_HASHES, 'unqualified scanner binary')
    require(receipt['static_build_lock_sha256'] == lock_hash, 'static build uses another lock')
    fresh(receipt['npm_audited_at'], now)
    require(receipt['npm_command'] == NPM_COMMAND and receipt['npm_config'] == NPM_CONFIG,
            'npm audit command/config does not cover full lock')
    require(receipt['npm_report_sha256'] == manifest['files']['npm-audit.json']['sha256'] and
            receipt['npm_lock_hash_before'] == receipt['npm_lock_hash_after'] == lock_hash,
            'npm report/lock receipt mismatch')

    sbom, grype, npm = files['syft.json'], files['grype.json'], files['npm-audit.json']
    require(sbom['schema']['version'] == '16.1.13', 'unsupported Syft schema')
    require(canonical_hash(sbom['descriptor']['configuration']) == SCOPE_HASHES['syft'],
            'unqualified Syft scan scope/catalogers')
    for name, report in [('syft', sbom), ('grype', grype)]:
        require(report['descriptor']['name'] == name and report['descriptor']['version'] == TOOL_VERSIONS[name],
                'report scanner identity mismatch')
    require(sbom['source']['type'] == 'image' and sbom['source']['metadata']['imageID'] == image_id,
            'SBOM targets another image')
    require(grype['source']['type'] == 'image' and grype['source']['target']['imageID'] == image_id,
            'scan targets another image')
    require(set(grype) == {'matches', 'ignoredMatches', 'source', 'distro', 'descriptor'}, 'unsupported Grype shape')
    db = grype['descriptor']['db']['status']
    require(db['valid'] is True and db['schemaVersion'] == 'v6.1.10', 'invalid database schema/status')
    fresh(db['built'], now)
    with sqlite3.connect((bundle / 'vulnerability.db').resolve().as_uri() + '?mode=ro', uri=True) as connection:
        metadata = connection.execute('SELECT build_timestamp, model, revision, addition FROM db_metadata').fetchall()
    require(len(metadata) == 1 and metadata[0][1:] == (6, 1, 10), 'retained database schema mismatch')
    require(timestamp(metadata[0][0]) == timestamp(db['built']), 'retained database timestamp mismatch')
    checked_file(bundle / 'vulnerability.db', db_hash)
    fresh(grype['descriptor']['timestamp'], now)
    config = grype['descriptor']['configuration']
    require(canonical_hash({key:value for key,value in config.items() if key != 'file'}) == SCOPE_HASHES['grype'],
            'unqualified Grype matcher/filter scope')
    require(not any(config[k] for k in ('only-fixed', 'only-notfixed', 'ignore-wontfix', 'exclude', 'vex-documents')),
            'scanner filtering is forbidden')
    require(config['include-matcher-suppressions'] is True, 'matcher suppressions must be retained')
    require(config['exp'] == {}, 'unqualified experimental matcher settings')

    artifacts = sbom['artifacts']
    require(isinstance(artifacts, list) and artifacts, 'empty SBOM')
    artifact_by_id = {a['id']: a for a in artifacts}
    require(len(artifact_by_id) == len(artifacts), 'duplicate SBOM artifact identity')
    require(all(a['type'] in ECOSYSTEMS for a in artifacts), 'unreviewed ecosystem')
    inventory = files['inventory.json']
    require(inventory['image_id'] == image_id, 'inventory subject mismatch')
    for ecosystem in ('python', 'deb'):
        direct = {(package_name(p['name'], ecosystem), p['version']) for p in inventory[ecosystem]}
        scanned = {(package_name(p['name'], ecosystem), p['version']) for p in artifacts if p['type'] == ecosystem}
        require(direct and direct <= scanned, 'direct inventory omitted from SBOM')
        for package in inventory[ecosystem]:
            require(any(a['type'] == ecosystem and package_name(a['name'], ecosystem) == package_name(package['name'], ecosystem)
                        and a['version'] == package['version'] and
                        any(location['path'] == package['path'] or location['path'].startswith(package['path'].rstrip('/')+'/')
                            for location in a['locations']) for a in artifacts),
                    'installed package path absent from SBOM')
    approvals, native_coverage = approved_records(checked_file(dispositions, dispositions_hash), dispositions_hash, image_id, lock_hash, now)
    require(isinstance(native_coverage, list), 'malformed native approvals')
    for entry in native_coverage:
        require(set(entry) == {'file_sha256', 'paths', 'owner', 'approver', 'evidence', 'advisory_coverage'},
                'unsupported native approval fields')
        require(isinstance(entry['file_sha256'], str) and re.fullmatch('[0-9a-f]{64}',entry['file_sha256']),
                'invalid native file hash')
        require(isinstance(entry['paths'], list) and entry['paths'] and
                all(isinstance(path,str) and path.startswith('/') for path in entry['paths']), 'invalid native paths')
        require(all(isinstance(entry[key],str) and entry[key].strip()
                    for key in ('owner','approver','evidence','advisory_coverage')), 'incomplete native approval')
    native = {entry['file_sha256']: entry for entry in native_coverage}
    direct_files = {entry['path']: entry['sha256'] for entry in inventory['native_files']}
    require(len(direct_files) == len(inventory['native_files']), 'duplicate native inventory path')
    require(all(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}', value)
                for value in direct_files.values()), 'invalid native inventory digest')
    scanned_executables = {file['location']['path'] for file in sbom['files'] if file.get('executable')}
    require(bool(direct_files) and set(direct_files) == scanned_executables,
            'native executable inventory empty or differs from SBOM')
    require(len(native) == len(native_coverage), 'duplicate native coverage entry')
    native_used = set()
    for file in sbom['files']:
        require(not file.get('errors'), 'SBOM parser failure')
        if file.get('executable'):
            for item in file.get('digests', []):
                if item['algorithm'] == 'sha256':
                    require(item['value'] == direct_files[file['location']['path']],
                            'executable direct digest differs from SBOM')
        unknowns = file.get('unknowns', [])
        if not unknowns:
            continue
        require(unknowns == ['unknowns-labeler: no package identified in executable file'], 'SBOM parser failure')
        key = next((d['value'] for d in file.get('digests', []) if d['algorithm'] == 'sha256'), None)
        direct_key = direct_files.get(file['location']['path'])
        require(direct_key is not None and (key is None or key == direct_key), 'native direct readback missing or mismatched')
        key = direct_key
        require(key in native, 'unresolved native executable coverage')
        entry = native[key]
        require(file['location']['path'] in entry['paths'] and entry['owner'] and entry['evidence']
                and entry['advisory_coverage'], 'incomplete native coverage')
        native_used.add(key)
    require(native_used == set(native), 'stale native coverage approval')

    rows = []
    for source in ('matches', 'ignoredMatches'):
        require(isinstance(grype[source], list), 'malformed findings')
        for row in grype[source]:
            artifact = row['artifact']
            require(artifact['id'] in artifact_by_id, 'scan artifact absent from SBOM')
            original = artifact_by_id[artifact['id']]
            require(all(artifact[k] == original[k] for k in ('name', 'version', 'type')),
                    'scan artifact identity mismatch')
            # Grype can reorder Syft locations. Preserve all fields and duplicate
            # multiplicity; this comparison does not alter finding approval keys.
            require(isinstance(artifact['locations'], list) and isinstance(original['locations'], list)
                    and all(isinstance(location, dict) for location in artifact['locations'] + original['locations']),
                    'malformed artifact locations')
            require(Counter(canonical_hash(location) for location in artifact['locations']) ==
                    Counter(canonical_hash(location) for location in original['locations']),
                    'scan artifact location mismatch')
            advisories = [row['vulnerability'], *row['relatedVulnerabilities']]
            require(all(isinstance(item.get(key), str) and item[key].strip()
                        for item in advisories for key in ('id', 'namespace')), 'missing advisory identity')
            severities = [item['severity'] for item in advisories]
            require(all(severity in SEVERITIES for severity in severities), 'unrecognized severity')
            # Differing alias scores require explicit review, never implicit downgrade.
            severity = max(severities, key=SEVERITY_RANK.__getitem__)
            rows.append((finding_key(source, row), severity))
    require(npm.get('auditReportVersion') == 2 and 'error' not in npm, 'unsupported/failed npm audit')
    require(isinstance(npm['vulnerabilities'], dict) and npm['metadata']['dependencies']['total'] > 0,
            'empty npm inventory')
    lock_packages = files['package-lock.json']['packages']
    require(type(npm['metadata']['dependencies']['total']) is int and
            npm['metadata']['dependencies']['total'] == len(lock_packages) - 1,
            'npm audit does not cover the full lock')
    require(receipt['npm_scope'] == 'all-lock-dependencies', 'npm audit scope is incomplete')
    npm_counts = Counter()
    for name, row in npm['vulnerabilities'].items():
        require(row['name'] == name and row['nodes'] and row['via'], 'malformed npm finding')
        require(all(node in files['package-lock.json']['packages'] for node in row['nodes']),
                'npm finding absent from exact lock')
        severity = {'critical':'Critical', 'high':'High', 'moderate':'Medium', 'low':'Low', 'info':'Negligible'}.get(row['severity'])
        require(severity is not None, 'unrecognized npm severity')
        npm_counts[row['severity']] += 1
        rows.append((finding_key('npm', row), severity))
    require(sum(npm_counts.values()) == npm['metadata']['vulnerabilities']['total'], 'npm finding count mismatch')
    used = set()
    blocked = Counter()
    for key, severity in rows:
        if key in approvals:
            used.add(key)
        elif severity in {'Critical', 'High', 'Medium', 'Unknown'}:
            blocked[severity] += 1
    require(used == set(approvals), 'stale/unmatched disposition')
    return {'accepted': not blocked, 'image_id': image_id, 'lock_sha256': lock_hash,
            'raw_findings':len(rows), 'approved_findings':len(used), 'blocking':dict(blocked),
            'native_coverage_files':len(native_used), 'manifest_sha256':manifest_hash}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'manifest-hash', 'image-id', 'lock-hash', 'source-revision', 'policy', 'policy-hash',
                 'dispositions', 'dispositions-hash'):
        parser.add_argument('--'+name, required=True)
    args = vars(parser.parse_args(argv))
    for name in ('bundle', 'policy', 'dispositions'):
        args[name] = Path(args[name])
    try:
        result = evaluate(**args)
    except (EvidenceError, OSError, ValueError, TypeError, KeyError, sqlite3.DatabaseError) as exc:
        # CLI input/output boundary: report category, never arbitrary input contents.
        print(json.dumps({'accepted':False, 'error':type(exc).__name__}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
