"""Bounded public ZIP reader for this audit; never writes into a run.

Usage: python read_reference.py URL [member ...]. With no members, list only.
Retained members and provenance are package-owned, not model inputs.
"""
import hashlib
import io
import json
from pathlib import Path
import sys
import struct
import urllib.request
import zipfile


class RemoteZip(io.RawIOBase):
    def __init__(self, url, base=0, size=None):
        self.url = url
        self.base = base
        if size is None:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
                size = int(r.headers["Content-Length"])
        self.size = size
        self.pos = self.transferred = 0

    def seekable(self):
        return True

    def seek(self, offset, whence=0):
        self.pos = offset + (0 if whence == 0 else self.pos if whence == 1 else self.size)
        return self.pos

    def tell(self):
        return self.pos

    def read(self, size=-1):
        size = min(self.size - self.pos, size if size >= 0 else self.size)
        if size <= 0:
            return b""
        if self.transferred + size > 80_000_000:
            raise ValueError("Audit download budget exceeded")
        request = urllib.request.Request(self.url, headers={"Range": f"bytes={self.base+self.pos}-{self.base+self.pos+size-1}"})
        with urllib.request.urlopen(request, timeout=45) as r:
            if r.status != 206:
                raise ValueError("Server did not honor bounded Range request")
            data = r.read(size + 1)
        if len(data) != size:
            raise ValueError("Range length mismatch")
        self.pos += size
        self.transferred += size
        return data


if __name__ == "__main__":
    remote = RemoteZip(sys.argv[1])
    out = Path(__file__).resolve().parent
    requested = sys.argv[2:]
    hash_only = "--hash-only" in requested
    if hash_only:
        requested.remove("--hash-only")
    nested = None
    if requested and requested[0].endswith(".zip"):
        nested = requested.pop(0)
        with zipfile.ZipFile(remote) as outer:
            info = outer.getinfo(nested)
            if info.compress_type != zipfile.ZIP_STORED:
                raise ValueError("Nested archive must be stored")
            remote.seek(info.header_offset)
            header = remote.read(30)
            name_len, extra_len = struct.unpack_from("<HH", header, 26)
            base = info.header_offset + 30 + name_len + extra_len
            outer_bytes = remote.transferred
        remote = RemoteZip(remote.url, base, info.file_size)
        remote.transferred = outer_bytes
    with zipfile.ZipFile(remote) as archive:
        inventory = [{"name": i.filename, "bytes": i.file_size, "compressed_bytes": i.compress_size}
                     for i in archive.infolist()]
        members = []
        for name in requested:
            info = archive.getinfo(name)
            if info.file_size > 100_000_000:
                raise ValueError("Member exceeds audit limit")
            content = archive.read(name)
            target = out / Path(name).name
            if not hash_only:
                target.write_bytes(content)
            members.append({"name": name, "local": None if hash_only else target.name,
                            "sha256": hashlib.sha256(content).hexdigest()})
    evidence = dict(url=remote.url, nested=nested, archive_bytes=remote.size, transferred_bytes=remote.transferred,
                    inventory=inventory, members=members)
    suffix = "_" + Path(nested).stem if nested else ""
    if hash_only:
        suffix += "_source_hash"
    (out / ("reference_zip_inventory" + suffix + ".json")).write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({k: v for k,v in evidence.items() if k != "inventory"}, indent=2))
