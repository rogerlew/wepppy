"""Collect private image evidence using the qualified, confined scanner pair.

A trusted build receipt binds source and lock to the image. Collection does not
approve findings and is deliberately separate from the policy evaluator.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import uuid

from tools.security.evaluate_dependency_evidence import (
    TOOL_HASHES, TOOL_VERSIONS, NPM_COMMAND, NPM_CONFIG, checked_file, read_json,
    SCIENTIFIC_CONFIG_HASH, SCIENTIFIC_MANIFEST_HASH,
    require, canonical_hash, SCOPE_HASHES,
)
from tools.security.import_dependency_evidence import EvidenceError

SCANNER_IMAGE = 'sha256:9823645c452a9a994f575ed238e1a4f67365acbf8e842db769060820fab06449'
NODE_IMAGE = 'docker.io/library/node:20-alpine@sha256:afdf98210b07b586eb71fa22ba2e432e058e4cd1304d31ed60888755b8c865fb'

# Qualified scanner diagnostics preserve the conservative finding universe.
# Do not enable Go symbol filtering: it can remove advisory rows.
QUALIFIED_WARNINGS = {
    'syft': 'WARN unable to get filesystem cache at /.cache/syft: '
            "unable to create directory at '/.cache/syft': mkdir /.cache: read-only file system",
    'grype': 'WARN go binary packages were found but none carry function symbols; '
             'go vulnerability matching falls back to module granularity and may report false positives. '
             'if scanning an SBOM, regenerate it with symbol capture enabled for more precise results.',
}


def analysis_diagnostic(tool, line, *, qualified_scope=False):
    if not re.search(r'\b(?:WARN|ERROR|FATAL)\b', line):
        return False
    # Accept only the complete known message, optionally prefixed by elapsed time.
    message = re.sub(r'^\[\d+\]\s+', '', line)
    return not qualified_scope or message != QUALIFIED_WARNINGS.get(tool)


def sha(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'regular report required')
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def copy_regular(source, destination):
    descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'regular report required')
        with destination.open('xb') as target:
            destination.chmod(0o600)
            shutil.copyfileobj(stream, target)


def now():
    return datetime.now(timezone.utc).isoformat()


def private_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    path.chmod(0o600)


def mount(source, target, readonly=True):
    require(',' not in str(source) and ',' not in target, 'unsupported mount path')
    return ['--mount', f'type=bind,src={source},dst={target}' + (',readonly' if readonly else '')]


def container(image, entrypoint, *, network=False, root=False):
    command = ['docker', 'run', '--rm', '--read-only', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--user',
               '0:0' if root else f'{os.getuid()}:{os.getgid()}',
               '--memory', '2g', '--cpus', '2']
    if not network:
        command += ['--network', 'none']
    if image == SCANNER_IMAGE:
        # The qualified Redis-based scanner carrier declares /data. Override
        # that exact unused path so Docker cannot create a writable volume.
        command += ['--tmpfs', '/data:ro,nosuid,nodev,noexec,size=1m']
    # Image and entrypoint are appended after explicit per-command mounts/env.
    return command, ['--entrypoint', entrypoint, image]


class Collector:
    def __init__(self, output):
        self.output = output.resolve()
        self.output.mkdir(mode=0o700)
        self.commands = []

    def run(self, name, command, allowed=(0,)):
        started = now()
        stdout = self.output / (name + '.stdout')
        stderr = self.output / (name + '.stderr')
        with stdout.open('xb') as out, stderr.open('xb') as err:
            stdout.chmod(0o600)
            stderr.chmod(0o600)
            result = subprocess.run(command, stdout=out, stderr=err, check=False)
        self.commands.append({'name': name, 'command': command, 'started_at': started,
                              'finished_at': now(), 'exit_status': result.returncode,
                              'stdout_sha256': sha(stdout), 'stderr_sha256': sha(stderr)})
        private_json(self.output / (name + '-command.json'), self.commands[-1])
        require(result.returncode in allowed, f'{name} failed; private command log retained')
        return stdout, result.returncode

    def collect(self, args):
        require(re.fullmatch('sha256:[0-9a-f]{64}', args.image_id), 'exact image ID required')
        require(re.fullmatch('[0-9a-f]{40}', args.source_revision), 'exact source revision required')
        inputs = self.output / 'inputs'
        inputs.mkdir(mode=0o700)
        build_raw = checked_file(args.build_receipt, args.build_receipt_sha256)
        build = read_json(build_raw)
        require(build['image_id'] == args.image_id and build['source_revision'] == args.source_revision,
                'build receipt subject mismatch')
        require(build['source_clean'] is True and type(build['exit_status']) is int and build['exit_status'] == 0,
                'successful clean build required')
        lock_hash = sha(args.lock)
        require(build['static_build_lock_sha256'] == lock_hash, 'build lock mismatch')
        config = Path(__file__).with_name('syft_scientific_data.json').resolve()
        snapshots = [('build-receipt.json', build_raw),
                     ('scientific-config.json', checked_file(config, SCIENTIFIC_CONFIG_HASH)),
                     ('scientific-manifest.json', checked_file(args.scientific_manifest, SCIENTIFIC_MANIFEST_HASH)),
                     ('package-lock.json', checked_file(args.lock, lock_hash))]
        for name, expected in TOOL_HASHES.items():
            snapshots.append((name, checked_file(args.tools / name, expected)))
        for name, raw in snapshots:
            path = inputs / name
            path.write_bytes(raw)
            path.chmod(0o700 if name in TOOL_HASHES else 0o600)
        args.tools = inputs
        args.lock = inputs / 'package-lock.json'
        args.build_receipt = inputs / 'build-receipt.json'
        args.scientific_manifest = inputs / 'scientific-manifest.json'
        config = inputs / 'scientific-config.json'
        # BuildKit's cached static-builder layers do not create a runnable
        # daemon image. Fetch the same immutable, already selected Node input.
        self.run('npm-image-prepare', ['docker', 'pull', NODE_IMAGE])
        for role, reference in [('candidate', args.image_id), ('scanner', SCANNER_IMAGE), ('npm', NODE_IMAGE)]:
            metadata_path, _ = self.run(role + '-image-metadata', ['docker', 'image', 'inspect',
                '--format', '{"id":{{json .Id}},"volumes":{{json (index .Config "Volumes")}}}', reference])
            metadata = read_json(metadata_path.read_bytes())
            expected_volumes = {'/data': {}} if role == 'scanner' else None
            require(metadata['volumes'] == expected_volumes or
                    (expected_volumes is None and metadata['volumes'] == {}),
                    'image declares unqualified implicit volumes')
            if role == 'candidate':
                require(metadata['id'] == args.image_id, 'candidate image identity changed')
        archive = self.output / 'image.tar'
        self.run('image-export', ['docker', 'image', 'save', '--output', str(archive), args.image_id])
        archive.chmod(0o600)
        probe = inputs / 'archive_inventory.py'
        probe.write_bytes(Path(__file__).with_name('archive_inventory.py').read_bytes())
        probe.chmod(0o600)
        filesystem = self.output / 'filesystem.tar'
        name = 'dependency-inventory-' + uuid.uuid4().hex
        created_path, _ = self.run('filesystem-create', ['docker', 'create', '--name', name,
            '--network', 'none', '--read-only', '--cap-drop', 'ALL', '--security-opt',
            'no-new-privileges', '--entrypoint', '/bin/true', args.image_id])
        container_id = created_path.read_text().strip()
        require(re.fullmatch('[0-9a-f]{64}', container_id), 'invalid created container identity')
        try:
            identity_path, _ = self.run('filesystem-identity', ['docker', 'container', 'inspect',
                '--format', '{"image_id":{{json .Image}},"running":{{json .State.Running}},"started_at":{{json .State.StartedAt}}}', container_id])
            identity = read_json(identity_path.read_bytes())
            require(identity['image_id'] == args.image_id and identity['running'] is False and
                    identity['started_at'] == '0001-01-01T00:00:00Z', 'filesystem container subject/state mismatch')
            self.run('filesystem-export', ['docker', 'container', 'export', '--output', str(filesystem), container_id])
        finally:
            # This never-started container was created by this invocation only.
            self.run('filesystem-remove', ['docker', 'container', 'rm', container_id])
        filesystem.chmod(0o600)
        filesystem_hash = sha(filesystem)
        inv_path, _ = self.run('inventory', [sys.executable, '-I', '-S', '-B', str(probe),
            '--archive', str(filesystem), '--image-id', args.image_id,
            '--scientific-config', str(config), '--scientific-manifest', str(args.scientific_manifest)])
        require(sha(filesystem) == filesystem_hash, 'filesystem archive changed during inventory')
        inventory = read_json(inv_path.read_bytes())
        require(inventory['static_build_lock_sha256'] == lock_hash, 'image lock differs from build')
        private_json(self.output / 'inventory.json', inventory)
        cache = self.output / 'cache'
        cache.mkdir(mode=0o700)
        reports = self.output / 'reports'
        reports.mkdir(mode=0o700)
        syft_tmp = self.output / 'syft-tmp'
        syft_tmp.mkdir(mode=0o700)
        grype_config = self.output / 'grype.yaml'
        grype_config.write_text('include-matcher-suppressions: true\n')
        grype_config.chmod(0o600)
        refresh_start, refresh_end = container(SCANNER_IMAGE, '/grype', network=True)
        refresh_start += ['--tmpfs', '/tmp:rw,nosuid,nodev,size=256m', '--env',
                          'GRYPE_CHECK_FOR_APP_UPDATE=false', '--env', 'GRYPE_DB_CACHE_DIR=/cache']
        refresh_start += mount(args.tools / 'grype', '/grype') + mount(cache, '/cache', False)
        refresh_start += mount(Path('/etc/ssl/certs/ca-certificates.crt'), '/etc/ssl/certs/ca-certificates.crt')
        self.run('database-refresh', refresh_start + refresh_end + ['db', 'update'])
        refreshed_at = now()
        database = cache / '6' / 'vulnerability.db'
        db_before = sha(database)
        database.chmod(0o600)
        scan_start, scan_end = container(SCANNER_IMAGE, '/syft')
        scan_start += ['--env', 'SYFT_CHECK_FOR_APP_UPDATE=false']
        scan_start += mount(args.tools / 'syft', '/syft') + mount(archive, '/image.tar')
        scan_start += mount(reports, '/reports', False) + mount(syft_tmp, '/tmp', False)
        scan_start += mount(config, '/syft.yaml')
        self.run('syft', scan_start + scan_end + ['scan', 'docker-archive:/image.tar',
                 '-o', 'syft-json=/reports/syft.json', '--config', '/syft.yaml'])
        sbom = reports / 'syft.json'
        sbom_before = sha(sbom)
        sbom.chmod(0o600)
        grype_start, grype_end = container(SCANNER_IMAGE, '/grype')
        grype_start += ['--tmpfs', '/tmp:rw,nosuid,nodev,size=256m', '--env',
                        'GRYPE_CHECK_FOR_APP_UPDATE=false', '--env', 'GRYPE_DB_AUTO_UPDATE=false',
                        '--env', 'GRYPE_DB_CACHE_DIR=/cache', '--env', 'GRYPE_LOG_LEVEL=debug']
        grype_start += mount(args.tools / 'grype', '/grype') + mount(cache, '/cache')
        grype_start += mount(sbom, '/sbom.json') + mount(reports, '/reports', False)
        grype_start += mount(grype_config, '/grype.yaml')
        self.run('grype', grype_start + grype_end + ['sbom:/sbom.json', '-o', 'json',
                 '--file', '/reports/grype.json', '--config', '/grype.yaml'])
        scanned_at = now()
        sha(reports / 'grype.json')
        (reports / 'grype.json').chmod(0o600)
        audit_work = self.output / 'npm-work'
        audit_work.mkdir(mode=0o700)
        shutil.copyfile(args.lock, audit_work / 'package-lock.json')
        node_start, node_end = container(NODE_IMAGE, 'npm', network=True)
        node_start += ['--tmpfs', '/tmp:rw,nosuid,nodev,size=256m', '--workdir', '/work',
                       '--env', 'HOME=/tmp', '--env', 'NODE_ENV=development',
                       '--env', 'NPM_CONFIG_USERCONFIG=/tmp/empty-user.npmrc',
                       '--env', 'NPM_CONFIG_GLOBALCONFIG=/dev/null', '--env', 'NPM_CONFIG_OMIT=',
                       '--env', 'NPM_CONFIG_PRODUCTION=false']
        node_start += mount(audit_work, '/work', False)
        npm_config_path, _ = self.run('npm-config', node_start + node_end +
                                     ['config', 'list', '--json', *NPM_COMMAND[4:-1]])
        npm_config = read_json(npm_config_path.read_bytes())
        require(npm_config['omit'] == [] and npm_config['production'] is False,
                'npm effective environment omits dependencies')
        require(set(npm_config['include']) == set(NPM_CONFIG['include']), 'npm include scope mismatch')
        npm_path, npm_exit = self.run('npm-audit', node_start + node_end + NPM_COMMAND[1:], allowed=(0, 1))
        require(sha(audit_work / 'package-lock.json') == lock_hash, 'npm changed lock')
        npm = read_json(npm_path.read_bytes())
        require('error' not in npm and 'vulnerabilities' in npm, 'npm audit failed')
        require(sha(database) == db_before and sha(sbom) == sbom_before, 'scan inputs changed')
        bundle = self.output / 'bundle'
        bundle.mkdir(mode=0o700)
        for source, name in [(sbom, 'syft.json'), (reports / 'grype.json', 'grype.json'),
                             (npm_path, 'npm-audit.json'), (args.lock, 'package-lock.json'),
                             (database, 'vulnerability.db'), (self.output / 'inventory.json', 'inventory.json'),
                             (config, 'scientific-config.json'), (args.scientific_manifest, 'scientific-manifest.json'),
                             (args.build_receipt, 'build-receipt.json'), (probe, 'archive_inventory.py')]:
            copy_regular(source, bundle / name)
        receipt = dict(schema_version=1, image_id=args.image_id, source_revision=args.source_revision,
            source_clean=True, lock_sha256=lock_hash, static_build_lock_sha256=lock_hash,
            scanned_at=scanned_at, database_refreshed_at=refreshed_at, database_refresh_exit=0,
            syft_exit=0, grype_exit=0, inventory_exit=0, npm_exit=npm_exit,
            database_hash_before=db_before, database_hash_after=sha(database),
            sbom_hash_before=sbom_before, sbom_hash_after=sha(sbom),
            tool_versions=TOOL_VERSIONS, tool_sha256=TOOL_HASHES,
            npm_audited_at=now(), npm_command=NPM_COMMAND, npm_config=NPM_CONFIG,
            npm_report_sha256=sha(npm_path), npm_lock_hash_before=lock_hash,
            npm_lock_hash_after=sha(audit_work / 'package-lock.json'), npm_scope='all-lock-dependencies',
            image_archive_sha256=sha(archive), filesystem_archive_sha256=filesystem_hash,
            inventory_probe_sha256=sha(probe), inventory_method='never-started-export-v1',
            trusted_python_version=sys.version,
            build_receipt_sha256=args.build_receipt_sha256,
            scientific_config_sha256=SCIENTIFIC_CONFIG_HASH,
            scientific_manifest_sha256=SCIENTIFIC_MANIFEST_HASH,
            scientific_files_verified=inventory['scientific_files_verified'], commands=self.commands)
        # Raw diagnostics remain evidence; do not claim a clean parser result
        # merely because a tool returned zero. Evaluator also checks native rows.
        sbom_data = read_json(sbom.read_bytes())
        grype_data = read_json((reports / 'grype.json').read_bytes())
        grype_scope = {key: value for key, value in grype_data['descriptor']['configuration'].items()
                       if key != 'file'}
        qualified_scope = (canonical_hash(sbom_data['descriptor']['configuration']) == SCOPE_HASHES['syft']
                           and canonical_hash(grype_scope) == SCOPE_HASHES['grype'])
        receipt['qualified_diagnostics'] = []
        receipt['analysis_errors'] = [f for f in sbom_data['files'] if f.get('errors') or
            any(u != 'unknowns-labeler: no package identified in executable file' for u in f.get('unknowns', []))]
        for tool in ('syft', 'grype'):
            for line in (self.output / (tool + '.stderr')).read_text().splitlines():
                if analysis_diagnostic(tool, line, qualified_scope=qualified_scope):
                    receipt['analysis_errors'].append({'tool': tool, 'diagnostic': line})
                elif re.search(r'\bWARN\b', line):
                    receipt['qualified_diagnostics'].append({'tool': tool, 'diagnostic': line,
                        'reason': 'Qualified pinned scanner scope; no input or advisory rows suppressed'})
        private_json(bundle / 'receipt.json', receipt)
        for path in self.output.iterdir():
            if path.is_file() and path.suffix in {'.stdout', '.stderr'} and path.stat().st_size:
                copy_regular(path, bundle / path.name)
        files = {p.name: {'sha256': sha(p), 'size_bytes': p.stat().st_size} for p in bundle.iterdir()}
        private_json(bundle / 'manifest.json', {'schema_version': 1, 'image_id': args.image_id, 'files': files})
        return sha(bundle / 'manifest.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('image-id', 'source-revision', 'build-receipt-sha256'):
        parser.add_argument('--' + name, required=True)
    for name in ('build-receipt', 'lock', 'scientific-manifest', 'tools', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    for name in ('build_receipt', 'lock', 'scientific_manifest', 'tools'):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    try:
        print(Collector(args.output).collect(args))
    except (EvidenceError, OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f'Collection failed: {exc}\n')


if __name__ == '__main__':
    main()
