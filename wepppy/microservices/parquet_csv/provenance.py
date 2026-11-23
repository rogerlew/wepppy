"""Exact installed source/binary identity for the required native CLI."""
import hashlib
import json
import math
import re
import os
import stat
from pathlib import Path

ROOT = Path("/opt/parquet-csv")
HEX = re.compile(r'[0-9a-f]{64}\Z')


def _read_regular(path: Path, ceiling: int, *, executable=False):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > ceiling or (executable and not before.st_mode & 0o111):
            raise ValueError('invalid regular file')
        chunks = []
        h = hashlib.sha256()
        total = 0
        while True:
            chunk = stream.read(min(1024 * 1024, ceiling + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > ceiling:
                raise ValueError('file too large')
            if not executable:
                chunks.append(chunk)
            h.update(chunk)
        after = os.fstat(stream.fileno())
        identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
        if identity(before) != identity(after) or total != before.st_size:
            raise ValueError('file changed')
        return h.hexdigest(), b''.join(chunks)


def digest(path: Path) -> str:
    return _read_regular(path, 64 * 1024 * 1024)[0]


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def strict_json(raw):
    def invalid_constant(value):
        raise ValueError('nonfinite JSON constant')
    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError('nonfinite JSON number')
        return parsed
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8')
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
                          parse_constant=invalid_constant, parse_float=finite_float)
    except RecursionError as exc:
        raise ValueError('JSON nesting exceeds parser capacity') from exc


def inventory(root: Path = ROOT) -> dict[str, str]:
    paths = [root / 'rust/Cargo.toml', root / 'rust/Cargo.lock']
    paths.extend(sorted((root / 'rust/src').rglob('*.rs')))
    if not paths[2:]:
        raise ValueError('missing Rust source')
    result = {}
    for path in paths:
        relative = path.relative_to(root)
        if path.is_symlink() or any((root / parent).is_symlink() for parent in relative.parents):
            raise ValueError('symlink source')
        if not path.is_file():
            raise ValueError('missing source')
        result[relative.as_posix()] = digest(path)
    return result


def generate(binary: Path, sidecar: Path, root: Path = ROOT) -> None:
    result = {'version': 1, 'binary_sha256': digest(binary), 'sources': inventory(root)}
    sidecar.write_text(json.dumps(result, indent=2) + '\n')


def validate(binary: Path, sidecar: Path, root: Path = ROOT) -> str:
    if sidecar.is_symlink() or binary.is_symlink() or sidecar.stat().st_size > 65536:
        raise ValueError('invalid provenance file')
    value = strict_json(_read_regular(sidecar, 65536)[1])
    if not isinstance(value, dict) or set(value) != {'version', 'binary_sha256', 'sources'}:
        raise ValueError('invalid provenance schema')
    if type(value['version']) is not int or value['version'] != 1:
        raise ValueError('invalid provenance version')
    expected = inventory(root)
    if value['sources'] != expected or not isinstance(value['binary_sha256'], str) or not HEX.fullmatch(value['binary_sha256']):
        raise ValueError('provenance mismatch')
    actual = _read_regular(binary, 64 * 1024 * 1024, executable=True)[0]
    if actual != value['binary_sha256']:
        raise ValueError('binary mismatch')
    return actual


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('binary', type=Path)
    parser.add_argument('sidecar', type=Path)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    args = parser.parse_args()
    generate(args.binary, args.sidecar, args.source_root)
