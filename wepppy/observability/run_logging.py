"""Run-file logging without idle descriptors that pin deleted NFS files."""
from __future__ import annotations

import logging
import sys

from .safe_traceback import UNAVAILABLE

__all__ = ["RunFileHandler"]


class RunFileHandler(logging.FileHandler):
    """Append each record with a stream scoped to that write, not the logger."""

    def __init__(self, filename, *, encoding=None, errors=None):
        # Preserve eager creation/validation, but never retain even an unused FD.
        super().__init__(filename, mode="a", encoding=encoding, errors=errors)
        self._release_stream()

    def _release_stream(self):
        stream, self.stream = self.stream, None
        if stream is not None:
            stream.close()

    def emit(self, record):
        # Handler.handle already takes this RLock; also protect direct emit calls.
        self.acquire()
        try:
            try:
                try:
                    super().emit(record)
                finally:
                    self._release_stream()
            except OSError:
                # A deleted run or failed file sink must not kill QueueListener
                # and prevent Redis/console delivery. Never recreate the parent.
                self.handleError(record)
        finally:
            self.release()

    def handleError(self, record):
        # stdlib prints raw Message/Arguments. Keep F5's value-free sink failure
        # even in scripts which have not installed the process logging adapter.
        try:
            sys.stderr.write(UNAVAILABLE + "\n")
        except (OSError, ValueError):
            pass  # The diagnostic sink itself is unavailable; no raw fallback.
