"""Utility to build ZIP archives entirely in memory."""

from __future__ import annotations

from pathlib import Path
from typing import Union
import io
import zipfile


class InMemoryZip:
    """Minimal helper for composing ZIP files without touching disk."""

    def __init__(self) -> None:
        self._buffer = io.BytesIO()

    def append(self, filename_in_zip: str, file_contents: Union[str, bytes]) -> InMemoryZip:
        """Append ``file_contents`` to the archive under ``filename_in_zip``."""
        with zipfile.ZipFile(self._buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
            zf.writestr(filename_in_zip, file_contents)
            for zfile in zf.filelist:
                zfile.create_system = 0
        return self

    def read(self) -> bytes:
        """Return the raw ZIP bytes."""
        self._buffer.seek(0)
        return self._buffer.read()

    def writetofile(self, filename: Union[str, Path]) -> None:
        """Persist the in-memory archive to ``filename``."""
        path = Path(filename)
        path.write_bytes(self.read())


if __name__ == "__main__":
    imz = InMemoryZip()
    imz.append("test.txt", "Another test").append("test2.txt", "Still another")
    imz.writetofile("test.zip")
