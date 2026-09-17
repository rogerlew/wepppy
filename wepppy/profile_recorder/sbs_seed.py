"""Immutable SBS response-event seeds and verified multipart bytes."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import NamedTuple
from uuid import uuid4

from requests import RequestException

MARKER = '_sbs_seed_version'


class SbsSeed(NamedTuple):
    name: str
    payload: bytes


def _version(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _entry(seed_upload_root, event_id):
    if not isinstance(event_id, str) or not event_id:
        raise ValueError('SBS seed requires a response event ID')
    root = Path(seed_upload_root).resolve()
    entry = (root / 'sbs' / 'events' / hashlib.sha256(event_id.encode()).hexdigest()).resolve()
    if not entry.is_relative_to(root):
        raise ValueError('SBS event seed escapes upload root')
    return root, entry


@contextmanager
def _directory(seed_upload_root, event_id, *, create=False):
    root, entry = _entry(seed_upload_root, event_id)
    if create:
        root.mkdir(parents=True, exist_ok=True)
    descriptors = []
    try:
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(descriptor)
        if _version(os.fstat(descriptor)) != _version(root.stat()) or root.resolve() != root:
            raise ValueError('SBS seed root changed while opening')
        parts = entry.relative_to(root).parts
        created = False
        for index, part in enumerate(parts):
            if create:
                try:
                    os.mkdir(part, mode=0o700 if index == len(parts) - 1 else 0o777,
                             dir_fd=descriptor)
                    if index == len(parts) - 1:
                        created = True
                except FileExistsError:
                    pass
            descriptor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                 dir_fd=descriptor)
            descriptors.append(descriptor)
        def validate():
            if (_entry(seed_upload_root, event_id) != (root, entry)
                    or _version(os.fstat(descriptor))[:2] != _version(entry.stat())[:2]):
                raise ValueError('SBS event directory changed during access')
        validate()
        yield descriptor, created, validate
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _read_stable(path, *, dir_fd=None):
    fd = os.open(path, os.O_RDONLY | (os.O_NOFOLLOW if dir_fd is not None else 0), dir_fd=dir_fd)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('SBS seed must be an ordinary file')
        value = stream.read(before.st_size + 1)
        if (len(value) != before.st_size or _version(os.fstat(stream.fileno())) != _version(before)
                or _version(os.stat(path, dir_fd=dir_fd, follow_symlinks=dir_fd is None)) != _version(before)):
            raise ValueError('SBS seed changed while reading')
    return value


def _json_record(descriptor, name, value):
    temporary = f'{name}.{uuid4().hex}'
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=descriptor)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write('\n')
    os.replace(temporary, name, src_dir_fd=descriptor, dst_dir_fd=descriptor)


def _read_from_directory(descriptor, event_id, validate):
    directory_version = _version(os.fstat(descriptor))
    status_version = _version(os.stat('status.json', dir_fd=descriptor, follow_symlinks=False))
    status = json.loads(_read_stable('status.json', dir_fd=descriptor))
    if not isinstance(status, dict) or status.get('status') != 'complete' or status.get('event_id') != event_id:
        raise ValueError('SBS event capture is not complete')
    receipt_version = _version(os.stat('receipt.json', dir_fd=descriptor, follow_symlinks=False))
    receipt = json.loads(_read_stable('receipt.json', dir_fd=descriptor))
    if (not isinstance(receipt, dict)
            or set(receipt) != {'version', 'event_id', 'payload', 'size', 'sha256'}
            or type(receipt['version']) is not int or receipt['version'] != 1
            or receipt['event_id'] != event_id
            or type(receipt['size']) is not int or receipt['size'] < 0):
        raise ValueError('Invalid SBS event receipt')
    name = receipt['payload']
    if (not isinstance(name, str) or Path(name).name != name
            or name != 'input_upload_sbs' + Path(name).suffix):
        raise ValueError('Invalid SBS event payload name')
    payload = _read_stable(name, dir_fd=descriptor)
    if len(payload) != receipt['size'] or hashlib.sha256(payload).hexdigest() != receipt['sha256']:
        raise ValueError('SBS event seed does not match its receipt')
    validate()
    if (_version(os.fstat(descriptor)) != directory_version
            or _version(os.stat('receipt.json', dir_fd=descriptor, follow_symlinks=False)) != receipt_version
            or _version(os.stat('status.json', dir_fd=descriptor, follow_symlinks=False)) != status_version):
        raise ValueError('SBS event receipt changed while reading')
    return SbsSeed(name, payload)


def read_event_seed(seed_upload_root, event_id, *, required=False):
    """Return verified bytes, or None only for unmarked history with no entry."""
    try:
        root, entry = _entry(seed_upload_root, event_id)
        logical_entry = root / 'sbs' / 'events' / hashlib.sha256(event_id.encode()).hexdigest()
        if not os.path.lexists(logical_entry) and not required:
            return None
        with _directory(seed_upload_root, event_id) as (descriptor, _, validate):
            return _read_from_directory(descriptor, event_id, validate)
    except (OSError, ValueError, TypeError) as exc:
        raise RequestException(f'Unable to verify SBS event seed: {exc}') from exc


def capture_event_seed(seed_upload_root, event_id, source):
    """Stream the selected main file into a descriptor-bound retained record."""
    source = Path(source)
    with _directory(seed_upload_root, event_id, create=True) as (descriptor, created, validate):
        if not created:
            accepted = _read_from_directory(descriptor, event_id, validate)
            current = _read_stable(source)
            if accepted.payload != current or accepted.name != 'input_upload_sbs' + source.suffix:
                raise ValueError('Repeated SBS event has different selected bytes')
            return
        _json_record(descriptor, 'status.json', {'status': 'working', 'event_id': event_id})
        try:
            name = 'input_upload_sbs' + source.suffix
            digest = hashlib.sha256()
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o666, dir_fd=descriptor)
            with os.fdopen(fd, 'wb') as outgoing, source.open('rb') as incoming:
                before = os.fstat(incoming.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise ValueError('Selected SBS source must be an ordinary file')
                remaining = before.st_size + 1
                length = 0
                while remaining:
                    chunk = incoming.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    digest.update(chunk)
                    outgoing.write(chunk)
                    length += len(chunk)
                    remaining -= len(chunk)
                if (length != before.st_size
                        or _version(os.fstat(incoming.fileno())) != _version(before)
                        or _version(source.stat()) != _version(before)):
                    raise ValueError('Selected SBS source changed during capture')
            validate()
            copied = _read_stable(name, dir_fd=descriptor)
            if len(copied) != length or hashlib.sha256(copied).hexdigest() != digest.hexdigest():
                raise ValueError('Captured SBS bytes do not match the source')
            del copied
            from wepppy.all_your_base.file_digest import sha256_file
            if (sha256_file(source) != digest.hexdigest()
                    or _version(source.stat()) != _version(before)):
                raise ValueError('Selected SBS bytes changed during capture')
            validate()
            _json_record(descriptor, 'receipt.json', {'version': 1, 'event_id': event_id,
                         'payload': name, 'size': length, 'sha256': digest.hexdigest()})
            _json_record(descriptor, 'status.json', {'status': 'complete', 'event_id': event_id})
        except (OSError, ValueError) as exc:
            # Retain partial work through the same authorized directory descriptor.
            _json_record(descriptor, 'status.json', {'status': 'failed', 'event_id': event_id,
                                                  'error': str(exc)})
            raise


__all__ = ['MARKER', 'SbsSeed', 'capture_event_seed', 'read_event_seed']
