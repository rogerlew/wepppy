"""Same-build archive validation that preserves the durable mutation fence."""

import hashlib
from pathlib import Path

from .policy import require_settled
from .records import ProtectedProjectError, marker, read, safe_path


def validate_restore(wd, zf, restore_members):
    admission = marker(wd)
    members = zf.namelist()
    has_incoming = any(relative.as_posix() == "provenance/declarative.json"
                       for _, _, relative in restore_members)
    if admission is None:
        if has_incoming:
            raise ProtectedProjectError("Declarative archives can only restore their original project")
        return False
    require_settled(wd)
    normalized = [relative.as_posix() for _, _, relative in restore_members]
    if len(normalized) != len(set(normalized)):
        raise ProtectedProjectError("Archive has duplicate resolved paths")
    if any(member.filename.rstrip("/") != relative.as_posix()
           for member, _, relative in restore_members):
        raise ProtectedProjectError("Declarative archive paths must be canonical")
    if not has_incoming or "READONLY" not in members:
        raise ProtectedProjectError("Archive lacks declarative protection")
    # Provenance stays in place even when extraction is killed. Validate all of it
    # before removal of any scientific file; an old/different archive is not recovery.
    for path in (Path(wd) / "provenance").rglob("*"):
        relative = str(path.relative_to(wd))
        safe_path(wd, relative)
        if path.is_file():
            if members.count(relative) != 1 or zf.read(relative) != path.read_bytes():
                raise ProtectedProjectError("Archive provenance does not match this build")
    protected = read(wd, "provenance/protected.json")
    for member, _, relative in restore_members:
        name = relative.as_posix()
        if not member.is_dir() and (relative.parts[0] == "dem" or
                                    len(relative.parts) == 1 and name.endswith(".nodb")):
            if name not in protected:
                raise ProtectedProjectError("Archive adds an unrecorded protected artifact")
    for relative, expected in protected.items():
        safe_path(wd, relative)
        if members.count(relative) != 1:
            raise ProtectedProjectError("Archive is missing a protected artifact")
        with zf.open(relative) as stream:
            observed = hashlib.file_digest(stream, "sha256").hexdigest()
        if observed != expected:
            raise ProtectedProjectError("Archive protected content does not match this build")
    return True
