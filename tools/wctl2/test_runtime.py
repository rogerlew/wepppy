"""Container-side prerequisites and source-integrity receipt for worktree tests."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path('/workdir/wepppy')
STATIC = Path('wepppy/weppcloud/static-src')
SOURCE_SUFFIXES = {'.py', '.pyi', '.json', '.toml', '.ini', '.cfg', '.yaml', '.yml', '.js', '.html'}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def source_manifest(root: Path) -> dict[str, str]:
    result = subprocess.run(
        ['git', '-C', str(root), 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
        check=True, capture_output=True,
    )
    files = {}
    for name in sorted(set(os.fsdecode(result.stdout).split('\0'))):
        path = root / name
        if path.suffix not in SOURCE_SUFFIXES:
            continue
        if path.is_symlink():
            files[name] = 'symlink:' + os.readlink(path)
        elif path.is_file():
            files[name] = digest(path)
        else:
            files[name] = 'missing'
    return files


def source_changes(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))


def parser_check(root: Path, name: str) -> dict:
    from wepppy.microservices.shape_converter.parser_provenance import validate_parser_executable
    from wepppy.microservices.shape_converter.convert import _parser_cli_path, _geoparquet_parser_cli_path
    binary = _parser_cli_path() if name == 'shape_parser_cli' else _geoparquet_parser_cli_path()
    valid, reason = validate_parser_executable(binary)
    if not valid:
        raise ValueError(f'{name}: {reason}; supply --{name.replace("_cli", "").replace("_", "-")} with adjacent provenance, or use an image containing it')
    payload = json.loads(Path(f'{binary}.json').read_text())
    crate = root / 'wepppy/microservices/shape_converter/rust' / name
    recorded = payload['source']['files']
    validate_parser_sources(crate, recorded)
    return {'files': {str(binary): digest(binary), str(Path(f'{binary}.json')): digest(Path(f'{binary}.json'))}}


def validate_parser_sources(crate: Path, recorded: list[dict]) -> None:
    name = crate.name
    expected = {'Cargo.toml', 'Cargo.lock'} | {str(p.relative_to(crate)) for p in (crate / 'src').rglob('*.rs')}
    if {row['path'] for row in recorded} != expected:
        raise ValueError(f'{name}: provenance source inventory differs from candidate; rebuild using the canonical parser build')
    for row in recorded:
        path = crate / row['path']
        if path.stat().st_size != row['size_bytes'] or digest(path) != row['sha256']:
            raise ValueError(f'{name}: provenance does not match candidate {row["path"]}')


def node_lock_check(candidate: Path, provider: Path) -> dict:
    needed = (candidate / 'package.json', candidate / 'package-lock.json', provider / 'package.json', provider / 'package-lock.json', provider / 'node_modules/.package-lock.json')
    if any(not path.is_file() for path in needed):
        raise ValueError('Node dependency manifests missing; run wctl --project-dir <candidate> run-npm ci or supply a compatible --runtime-root')
    for name in ('package.json', 'package-lock.json'):
        if digest(candidate / name) != digest(provider / name):
            raise ValueError(f'Node {name} differs from candidate; run npm ci in candidate instead of borrowing dependencies')
    expected = json.loads((candidate / 'package-lock.json').read_text())['packages']
    installed = json.loads((provider / 'node_modules/.package-lock.json').read_text())['packages']
    for name, entry in installed.items():
        wanted = expected.get(name)
        if wanted is None or any(entry.get(k) != wanted.get(k) for k in ('version', 'integrity', 'resolved')):
            raise ValueError(f'Installed Node dependency differs from lock: {name}; run npm ci')
    return {'files': {str(path): digest(path) for path in needed}}


def browser_check(root: Path, borrowed: bool) -> dict:
    candidate = root / STATIC
    provider = Path('/opt/wctl-runtime') if borrowed else candidate
    identity = node_lock_check(candidate, provider)
    script = """const {chromium} = require('@playwright/test');
require('playwright');
(async () => {const browser = await chromium.launch({headless:true});
 const page = await browser.newPage(); await page.setContent('<title>worktree-ready</title>');
 if(await page.title() !== 'worktree-ready') throw Error('browser readback failed');
 await browser.close();})().catch(() => process.exit(1));"""
    environment = dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=str(candidate / '.playwright-browsers'))
    result = subprocess.run(['node', '-e', script], cwd=candidate, env=environment,
                            capture_output=True, timeout=45)
    if result.returncode:
        raise ValueError('Playwright Chromium launch failed; run wctl run-npm ci and install Chromium in candidate static-src/.playwright-browsers')
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = environment['PLAYWRIGHT_BROWSERS_PATH']
    return identity


def controller_check(root: Path) -> dict:
    # Reuse the real builder and candidate inputs, never a donor's generated JS.
    path = root / 'wepppy/weppcloud/controllers_js/build_controllers_js.py'
    spec = importlib.util.spec_from_file_location('wctl_candidate_controller_builder', path)
    if spec is None or spec.loader is None:
        raise RuntimeError('Cannot load candidate controller builder')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = root / 'wepppy/weppcloud/static/js/controllers-gl.js'
    if subprocess.run(['git', '-C', str(root), 'ls-files', '--error-unmatch', str(output)],
                      capture_output=True).returncode == 0:
        raise ValueError('Controller output is tracked; refusing to overwrite candidate source')
    contents = module.render_controllers(module._collect_controller_modules(), bundle_name='controllers-gl.js')
    module.write_output(contents, output_path=output)
    if output.read_text() != contents:
        raise RuntimeError('Generated controller readback differs')
    return {'files': {str(output): digest(output)}}


def missing_columns(metadata, inspector) -> dict[str, list[str]]:
    missing = {}
    for table in metadata.sorted_tables:
        if not inspector.has_table(table.name, schema=table.schema):
            missing[table.fullname] = [column.name for column in table.columns]
            continue
        present = {column['name'] for column in inspector.get_columns(table.name, schema=table.schema)}
        absent = sorted(column.name for column in table.columns if column.name not in present)
        if absent:
            missing[table.fullname] = absent
    return missing


def database_check() -> dict:
    import sqlalchemy as sa
    from sqlalchemy.exc import SQLAlchemyError
    from wepppy.weppcloud.app import app, db
    try:
        with app.app_context(), db.engine.connect() as connection:
            if connection.dialect.name != 'postgresql':
                raise ValueError('Broad/database profile requires PostgreSQL integration infrastructure')
            with connection.begin():
                connection.exec_driver_sql('SET TRANSACTION READ ONLY')
                connection.exec_driver_sql("SET LOCAL statement_timeout = '5s'")
                missing = missing_columns(db.metadata, sa.inspect(connection))
    except SQLAlchemyError as exc:
        # Connection exceptions can contain credentials/SQL parameters. Report
        # only their class at this operator-facing prerequisite boundary.
        raise RuntimeError(f'Database inspection failed ({type(exc).__name__}); verify test database connectivity') from None
    if missing:
        raise ValueError('Database schema missing ' + json.dumps(missing, sort_keys=True) + '; provision an isolated integration database with canonical migrations. No migration was run.')
    return {'model_columns_present': True, 'inspection': 'read-only; constraints and migrations still require tests'}


def check(name: str, callback, checks: list[dict]) -> None:
    try:
        detail = callback()
    except (OSError, ValueError, RuntimeError, ImportError, subprocess.SubprocessError) as exc:
        checks.append({'name': name, 'ready': False, 'detail': str(exc)})
    else:
        checks.append({'name': name, 'ready': True, 'identity': detail})


def preflight(root: Path, profile: str, borrowed: bool) -> list[dict]:
    checks = []
    if profile in {'broad', 'browser'}:
        check('controllers', lambda: controller_check(root), checks)
        check('browser', lambda: browser_check(root, borrowed), checks)
    if profile in {'broad', 'native'}:
        for name in ('shape_parser_cli', 'geoparquet_parser_cli'):
            check(name, lambda name=name: parser_check(root, name), checks)
    if profile in {'broad', 'database'}:
        check('database', database_check, checks)
    return checks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('broad', 'python', 'browser', 'native', 'database'), default='broad')
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--borrowed-node', action='store_true')
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('pytest_args', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    tests = args.pytest_args[1:] if args.pytest_args[:1] == ['--'] else args.pytest_args
    tests = tests or ['tests']
    if any(arg == '--basetemp' or arg.startswith('--basetemp=') for arg in tests):
        parser.error('Worktree runner owns a short unique --basetemp; remove the override')
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    # Reserve before any preparation. Never overwrite an earlier run receipt.
    with args.receipt.open('x') as stream:
        json.dump({'status': 'preflight_in_progress', 'tests_started': False}, stream)
    report = {'profile': args.profile, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'uid': os.getuid(), 'gid': os.getgid(), 'groups': os.getgroups(),
              'tests_started': False, 'pytest_args': tests}
    report['head'] = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
    before = source_manifest(ROOT)
    report['checks'] = preflight(ROOT, args.profile, args.borrowed_node)
    report['preflight_source_changes'] = source_changes(before, source_manifest(ROOT))
    ready = all(row['ready'] for row in report['checks']) and not report['preflight_source_changes']
    report['status'] = 'ready' if ready else 'not_ready'
    code = 0 if ready else 2
    for row in report['checks']:
        print(f"{row['name']}: {'ready' if row['ready'] else row['detail']}", flush=True)
    report['source_before'] = before
    args.receipt.write_text(json.dumps(report, indent=2) + '\n')
    if ready and not args.preflight_only:
        temporary = tempfile.mkdtemp(prefix='wt-', dir='/tmp')
        report['basetemp'] = temporary
        report['tests_started'] = True
        report['status'] = 'running'
        args.receipt.write_text(json.dumps(report, indent=2) + '\n')
        result = subprocess.run([sys.executable, '-m', 'pytest', *tests, '--basetemp', temporary], cwd=ROOT)
        code = result.returncode
        report['pytest_exitstatus'] = code
        report['status'] = 'passed' if code == 0 else 'failed'
    runtime_files = {path: value for row in report['checks'] if row['ready']
                     for path, value in row['identity'].get('files', {}).items()}
    report['runtime_changes'] = sorted(path for path, value in runtime_files.items()
                                       if not Path(path).is_file() or digest(Path(path)) != value)
    after = source_manifest(ROOT)
    report['source_before'] = before
    report['source_after'] = after
    report['source_changes'] = source_changes(before, after)
    if report['runtime_changes']:
        code = 3
        report['status'] = 'runtime_changed'
    if report['source_changes']:
        code = 3
        report['status'] = 'source_changed'
    report['exitstatus'] = code
    args.receipt.write_text(json.dumps(report, indent=2) + '\n')
    print(f"Worktree validation: {report['status']}; tests_started={report['tests_started']}; receipt={args.receipt}", flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
