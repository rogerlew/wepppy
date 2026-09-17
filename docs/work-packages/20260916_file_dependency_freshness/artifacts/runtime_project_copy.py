#!/usr/bin/env python3
"""Disposable full-project copy for acceptance, without hydrating the source.

No hardlinks, source writes, controller loading, queue calls or model execution.
This fixture utility is intentionally limited to ordinary files/directories.
The named Grizzly source currently has that shape; unexpected links fail visibly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import time
import traceback


def version(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.writing')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


def digest_file(path):
    path = Path(path)
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if version(opened) != version(before):
            raise RuntimeError(f'File changed before read: {path}')
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
        if version(os.fstat(stream.fileno())) != version(opened):
            raise RuntimeError(f'File changed during read: {path}')
    if version(path.stat()) != version(opened):
        raise RuntimeError(f'File changed after read: {path}')
    return {'sha256': digest.hexdigest(), 'version': version(opened),
            'mode': stat.S_IMODE(opened.st_mode), 'bytes': opened.st_size}


def inventory(source):
    directories, files = [], []
    for root, dirs, names in os.walk(source, followlinks=False):
        for name in sorted(dirs):
            path = Path(root) / name
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError(f'Copy fixture requires ordinary directories: {path}')
            directories.append((path.relative_to(source), info))
        for name in sorted(names):
            path = Path(root) / name
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise ValueError(f'Copy fixture requires ordinary files: {path}')
            files.append((path.relative_to(source), info))
    return sorted(directories), sorted(files)


def copy_one(source, destination, expected):
    digest = hashlib.sha256()
    with source.open('rb') as incoming, destination.open('xb') as outgoing:
        opened = os.fstat(incoming.fileno())
        if version(opened) != version(expected):
            raise RuntimeError(f'Source changed since inventory: {source}')
        for block in iter(lambda: incoming.read(1024 * 1024), b''):
            outgoing.write(block)
            digest.update(block)
        if version(os.fstat(incoming.fileno())) != version(opened):
            raise RuntimeError(f'Source changed during copy: {source}')
    if version(source.stat()) != version(opened):
        raise RuntimeError(f'Source changed after copy: {source}')
    shutil.copystat(source, destination, follow_symlinks=False)
    copied = destination.stat()
    if (copied.st_dev, copied.st_ino) == (opened.st_dev, opened.st_ino):
        raise RuntimeError(f'Independent copy unexpectedly shares source inode: {source}')
    return {'sha256': digest.hexdigest(), 'version': version(opened),
            'mode': stat.S_IMODE(opened.st_mode), 'bytes': opened.st_size,
            'copied_version': version(copied)}


def _identity(destination):
    parts = destination.parts
    if len(parts) == 6 and parts[:3] == ('/', 'wc1', 'batch') and parts[4] == 'runs':
        if not parts[3].startswith('qa-'):
            raise ValueError('Disposable batch name must start qa-')
        if not parts[5].startswith(parts[3] + '-'):
            raise ValueError('Batch leaf must include its unique batch name because RedisPrep uses the leaf namespace')
        return 'batch', parts[3], f'batch;;{parts[3]};;{parts[5]}'
    if len(parts) == 5 and parts[:3] == ('/', 'wc1', 'runs') and parts[4].startswith('qa-'):
        if parts[3] != parts[4][:2]:
            raise ValueError('Interactive disposable path must use its canonical two-letter prefix')
        return None, None, parts[4]
    raise ValueError('Destination must be /wc1/batch/qa-*/runs/NAME or /wc1/runs/qa/qa-*')


def prepare_project_copy(source, destination, manifest_path=None):
    """Copy all payloads and rebase only destination metadata; return manifest.

    Root NoDb rewrite follows prepare_fork_run's textual source path/runid
    substitution, then explicitly assigns the disposable identity. A copied
    query catalog gets the same selected-root rebase, with no source activation.
    No scientific settings, dates, values or model inputs are shortened.
    """
    source = Path(source).absolute()
    destination = Path(destination).absolute()
    if source.resolve() != source or destination.resolve() != destination:
        raise ValueError('Fixture roots must not traverse aliases')
    if not source.is_dir() or destination.exists():
        raise ValueError('Source must exist and destination must be new')
    if source in destination.parents or destination in source.parents:
        raise ValueError('Source and destination must be disjoint')
    run_group, group_name, runid = _identity(destination)
    if (source / 'READONLY').exists():
        raise ValueError('This full-copy fixture expects a writable baseline project')
    if (source / '.redisprep-run-id').exists() or (source / '.redisprep-run-id').is_symlink():
        raise ValueError('Never copy a RedisPrep identity override into a disposable project')
    if (source / 'omni.nodb').exists() or (source / '_pups').exists():
        raise ValueError('This fixture expects a baseline without preexisting Omni children')
    directories, files = inventory(source)
    expected_bytes = sum(info.st_size for _, info in files)
    existing_parent = destination.parent
    while not existing_parent.exists():
        existing_parent = existing_parent.parent
    if shutil.disk_usage(existing_parent).free < expected_bytes + 2 * 1024**3:
        raise RuntimeError('Insufficient room for independent copy plus native results')
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(manifest_path or destination.parent / (destination.name + '-copy-manifest.json'))
    if manifest_path.exists():
        raise FileExistsError(manifest_path)
    manifest = {'schema': 'freshness-disposable-copy/v1', 'source': str(source),
                'destination': str(destination), 'runid': runid,
                'run_group': run_group, 'group_name': group_name,
                'started_unix': time.time(), 'status': 'copying',
                'logical_bytes': expected_bytes, 'source_files': {}, 'rebased': []}
    write_json(manifest_path, manifest)
    try:
        destination.mkdir(mode=stat.S_IMODE(source.stat().st_mode) | 0o700)
        for relative, info in sorted(directories, key=lambda item: len(item[0].parts)):
            (destination / relative).mkdir(mode=stat.S_IMODE(info.st_mode) | 0o700)
        for index, (relative, info) in enumerate(files, 1):
            manifest['source_files'][str(relative)] = copy_one(source / relative, destination / relative, info)
            if index % 250 == 0:
                write_json(manifest_path, manifest)
                print(f'COPY {index}/{len(files)} files', flush=True)
        for path in sorted(destination.glob('*.nodb')):
            original = path.read_text()
            text = original.replace(str(source), str(destination)).replace(source.name, runid)
            payload = json.loads(text)
            state = payload.get('py/state', payload)
            if not isinstance(state, dict):
                raise ValueError(f'Nonobject NoDb state: {path}')
            state['wd'] = str(destination)
            state.pop('_parent_wd', None)
            state['_run_group'] = run_group
            state['_group_name'] = group_name
            path.write_text(json.dumps(payload) + '\n')
            manifest['rebased'].append(str(path.relative_to(destination)))
        catalog = destination / '_query_engine/catalog.json'
        if catalog.exists():
            text = catalog.read_text()
            json.loads(text)  # Validate before rewriting copied catalog metadata.
            catalog.write_text(text.replace(str(source), str(destination)))
            manifest['rebased'].append('_query_engine/catalog.json')
        for path in (destination / 'wepp/runs').glob('*.run'):
            if str(source) in path.read_text():
                raise ValueError(f'Unexpected named-source path in copied WEPP runfile: {path}')
        for relative, info in sorted(directories, key=lambda item: len(item[0].parts), reverse=True):
            os.chmod(destination / relative, stat.S_IMODE(info.st_mode))
        current_dirs, current_files = inventory(source)
        if [str(p) for p, _ in current_files] != [str(p) for p, _ in files]:
            raise RuntimeError('Source membership changed during copy')
        if [str(p) for p, _ in current_dirs] != [str(p) for p, _ in directories]:
            raise RuntimeError('Source directory membership changed during copy')
        for relative, info in current_files:
            if version(info) != manifest['source_files'][str(relative)]['version']:
                raise RuntimeError(f'Source changed during whole-project copy: {relative}')
        manifest.update(status='prepared', finished_unix=time.time(), source_unchanged_after_copy=True)
        write_json(manifest_path, manifest)
        print(json.dumps({'status': 'prepared', 'runid': runid, 'destination': str(destination),
                          'manifest': str(manifest_path), 'files': len(files), 'bytes': expected_bytes}), flush=True)
        return manifest
    except BaseException as exc:  # Acceptance boundary: retain partial copy/error; never delete it.
        manifest.update(status='failed', error_type=type(exc).__name__, error=str(exc),
                        traceback=traceback.format_exc(), finished_unix=time.time())
        write_json(manifest_path, manifest)
        raise


def verify_source(manifest, *, hash_bytes=True):
    """Read-only post-run proof, independently rehashing all copied source files."""
    source = Path(manifest['source'])
    _, files = inventory(source)
    if {str(path) for path, _ in files} != set(manifest['source_files']):
        raise RuntimeError('Named source membership changed')
    for relative, info in files:
        expected = manifest['source_files'][str(relative)]
        if version(info) != expected['version']:
            raise RuntimeError(f'Named source version changed: {relative}')
        if hash_bytes and digest_file(source / relative)['sha256'] != expected['sha256']:
            raise RuntimeError(f'Named source bytes changed: {relative}')
    return {'files': len(files), 'hashed_bytes': sum(info.st_size for _, info in files) if hash_bytes else 0,
            'unchanged': True}


def relocate_prepared_copy(manifest_path, destination):
    """Correct an unhydrated prepared fixture identity; retain original evidence."""
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    previous = Path(manifest['destination'])
    destination = Path(destination).absolute()
    group, name, runid = _identity(destination)
    if (manifest['status'] != 'prepared' or not previous.is_dir()
            or (previous / 'omni.nodb').exists() or (previous / '_pups').exists()
            or (previous / '.redisprep-run-id').exists() or (previous / '.redisprep-run-id').is_symlink()
            or destination.exists() or destination.parent != previous.parent
            or destination.resolve() != destination):
        raise ValueError('Only a pristine prepared copy can receive a sibling identity correction')
    original = manifest_path.with_name(manifest_path.stem + '-before-identity-correction.json')
    if original.exists():
        raise FileExistsError(original)
    shutil.copy2(manifest_path, original)
    correction = {'status': 'started', 'old_destination': str(previous),
                  'new_destination': str(destination), 'old_runid': manifest['runid'],
                  'new_runid': runid, 'original_manifest': str(original),
                  'reason': 'RedisPrep ordinary/batch namespace uses the leaf basename; unique batch alone is insufficient',
                  'model_or_controller_hydration': False, 'rewritten': []}
    correction_path = manifest_path.parent / 'copy-identity-correction.json'
    write_json(correction_path, correction)
    try:
        previous.rename(destination)
        selected = sorted(destination.glob('*.nodb'))
        catalog = destination / '_query_engine/catalog.json'
        if catalog.exists():
            selected.append(catalog)
        for path in selected:
            old = path.read_text()
            new = old.replace(str(previous), str(destination)).replace(manifest['runid'], runid)
            json.loads(new)
            path.write_text(new)
            correction['rewritten'].append({'path': str(path.relative_to(destination)),
                                             'before_sha256': hashlib.sha256(old.encode()).hexdigest(),
                                             'after_sha256': hashlib.sha256(new.encode()).hexdigest()})
        manifest.update(destination=str(destination), runid=runid, run_group=group, group_name=name,
                        identity_correction=str(correction_path))
        write_json(manifest_path, manifest)
        correction.update(status='prepared', finished_unix=time.time())
        write_json(correction_path, correction)
        return manifest
    except BaseException as exc:  # Retain bounded fixture correction state, without hiding errors.
        correction.update(status='failed', error=str(exc), traceback=traceback.format_exc())
        write_json(correction_path, correction)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='/wc1/runs/th/thespian-cleanness')
    parser.add_argument('--destination', required=True)
    parser.add_argument('--manifest')
    args = parser.parse_args()
    prepare_project_copy(args.source, args.destination, args.manifest)


if __name__ == '__main__':
    main()
