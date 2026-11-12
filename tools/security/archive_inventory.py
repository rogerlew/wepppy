"""Read an exported image filesystem without extracting or executing its files."""
from __future__ import annotations

from email.parser import BytesParser
from email.policy import compat32
import fnmatch
import hashlib
from pathlib import PurePosixPath
import tarfile


def canonical_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name:
        raise ValueError('unsafe filesystem archive path')
    return '/' + str(path).removeprefix('./')


def native_header(header):
    magic = header[:4]
    if magic == b'\x7fELF':
        return (len(header) >= 20 and header[5] in (1, 2)
                and int.from_bytes(header[16:18], 'little' if header[5] == 1 else 'big') in (2, 3))
    return magic[:2] == b'MZ' or magic in {
        b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xcf\xfa\xed\xfe',
        b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'}


def identity_field(fields, name):
    values = fields.get_all(name, [])
    if fields.defects or len(values) != 1 or not values[0].strip():
        raise ValueError('ambiguous or malformed package metadata')
    return values[0].strip()


def inventory_archive(archive, config, approved, image_id):
    """Hash regular files and reconcile every excluded name, including dot names.

    The Docker export is a merged filesystem, not an overlay layer tar. Duplicate
    paths and unsupported node/link relationships fail instead of being merged.
    """
    expected = {row['path']: row for row in approved}
    if not expected or len(expected) != len(approved):
        raise ValueError('invalid scientific manifest')
    patterns = {}
    for pattern in config['exclude']:
        path = PurePosixPath(pattern)
        if not path.is_absolute() or any(c in str(path.parent) for c in '*?['):
            raise ValueError('unqualified scientific glob')
        patterns.setdefault(str(path.parent), []).append(path.name)
    nodes, regular, hardlinks, python, deb = {}, {}, {}, [], []
    metadata_aliases = set()
    matched = set()
    lock_path = '/workdir/wepppy/wepppy/weppcloud/static-src/package-lock.json'
    with tarfile.open(archive, mode='r|') as stream:
        for member in stream:
            name = canonical_path(member.name)
            if name in nodes:
                raise ValueError('duplicate filesystem archive path')
            nodes[name] = member.type
            path = PurePosixPath(name)
            metadata_root = path.name.endswith(('.dist-info', '.egg-info'))
            legacy_metadata = path.name.endswith('.egg-info') and (member.isfile() or member.islnk())
            if metadata_root and not member.isdir() and not legacy_metadata:
                raise ValueError('linked or non-directory metadata root requires qualification')
            metadata = legacy_metadata or (path.name in ('METADATA', 'PKG-INFO')
                        and path.parent.name.endswith(('.dist-info', '.egg-info')))
            if metadata and not (member.isfile() or member.islnk()):
                raise ValueError('nonregular package metadata requires qualification')
            scientific = any(fnmatch.fnmatchcase(path.name, pattern)
                             for pattern in patterns.get(str(path.parent), []))
            if scientific:
                matched.add(name)
                if name not in expected or not member.isfile():
                    raise ValueError('scientific exclusion is extra or nonregular')
            if member.islnk():
                hardlinks[name] = canonical_path(member.linkname)
                if metadata:
                    metadata_aliases.add(name)
                continue
            if not member.isfile():
                continue
            capture = scientific or metadata or name == '/var/lib/dpkg/status'
            if capture and member.size > 32 * 1024 * 1024:
                raise ValueError('metadata/scientific input exceeds qualified size')
            digest = hashlib.sha256()
            content = bytearray()
            header = b''
            with stream.extractfile(member) as source:
                while block := source.read(1024 * 1024):
                    if not header:
                        header = block[:64]
                    digest.update(block)
                    if capture:
                        content.extend(block)
            record = {'sha256': digest.hexdigest(), 'size': member.size,
                      'native': native_header(header)}
            regular[name] = record
            if scientific:
                approved_row = expected[name]
                if record['sha256'] != approved_row['sha256'] or member.size != approved_row['size']:
                    raise ValueError('scientific data requires requalification')
                if b'\0' in content or content.startswith(b'PK\x03\x04'):
                    raise ValueError('binary scientific exclusion')
                content.decode('utf-8')
            if metadata:
                fields = BytesParser(policy=compat32).parsebytes(bytes(content), headersonly=True)
                identity = {'name': identity_field(fields, 'Name'), 'version': identity_field(fields, 'Version')}
                record['python_identity'] = identity
                python.append({**identity, 'path': name})
            if name == '/var/lib/dpkg/status':
                for paragraph in bytes(content).split(b'\n\n'):
                    if not paragraph.strip():
                        continue
                    fields = BytesParser(policy=compat32).parsebytes(paragraph, headersonly=True)
                    status = identity_field(fields, 'Status').split()
                    if (len(status) != 3 or status[0] not in {'unknown', 'install', 'hold', 'deinstall', 'purge'}
                            or status[1] != 'ok' or status[2] not in {'installed', 'not-installed', 'config-files'}):
                        raise ValueError('unsupported Debian package state')
                    if status[2] == 'installed':
                        deb.append({'name': identity_field(fields, 'Package'),
                                    'version': identity_field(fields, 'Version'), 'path': name})
    if matched != set(expected):
        raise ValueError('scientific exclusion match set changed')
    for name in nodes:
        if any(str(parent) in nodes and nodes[str(parent)] != tarfile.DIRTYPE
               for parent in PurePosixPath(name).parents):
            raise ValueError('filesystem path has a non-directory or symlink parent')
    for name in expected:
        if any(nodes.get(str(parent)) == tarfile.SYMTYPE for parent in PurePosixPath(name).parents):
            raise ValueError('scientific path traverses symlink')
    pending = dict(hardlinks)
    while pending:
        resolved = [name for name, target in pending.items() if target in regular]
        if not resolved:
            raise ValueError('unresolved hardlink relationship')
        for name in resolved:
            regular[name] = regular[pending.pop(name)]
    for name in sorted(metadata_aliases):
        if 'python_identity' not in regular[name]:
            raise ValueError('metadata hardlink target lacks qualified identity')
        python.append({**regular[name]['python_identity'], 'path': name})
    native = [{'path': name, 'sha256': row['sha256']} for name, row in regular.items() if row['native']]
    if not python or not deb or not native or lock_path not in regular:
        raise ValueError('incomplete filesystem inventory')
    return {'image_id': image_id, 'python': python, 'deb': deb, 'native_files': native,
            'scientific_files_verified': len(matched),
            'static_build_lock_sha256': regular[lock_path]['sha256']}


if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path
    import resource

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--image-id', required=True)
    parser.add_argument('--scientific-config', type=Path, required=True)
    parser.add_argument('--scientific-manifest', type=Path, required=True)
    args = parser.parse_args()
    # Bound malicious archive/metadata resource use in this trusted subprocess.
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    result = inventory_archive(args.archive, json.loads(args.scientific_config.read_text()),
                               json.loads(args.scientific_manifest.read_text()), args.image_id)
    print(json.dumps(result, sort_keys=True))
