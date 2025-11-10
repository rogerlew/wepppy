"""Utilities for synthesizing multi-OFE WEPP soil files."""

from __future__ import annotations

import os
from typing import Iterable, List, Optional

from os.path import exists as exists
from os.path import join as _join
from os.path import split as _split


def read_soil_lines(fn: str) -> List[str]:
    """Return the raw lines from a WEPP soil file."""
    with open(fn) as fp:
        return fp.readlines()


class SoilMultipleOfeSynth(object):
    """Compose a multi-OFE WEPP soil file from single-OFE soil definitions."""

    def __init__(self, stack: Optional[Iterable[str]] = None) -> None:
        """
        Parameters
        ----------
        stack:
            Iterable of absolute soil file paths (one per OFE) to combine.
        """
        self.stack: List[str] = list(stack or [])

    @property
    def description(self) -> str:
        """Return a multi-line summary describing the composed soil file."""
        s = [
            "<wepppy.wepp.soils.utils.SoilMultipleOfe>",
            "Current Working Directory",
            os.getcwd(),
            "Stack:",
        ] + self.stack
        s = [f"# {L}" for L in s]
        return "\n".join(s)

    @property
    def num_ofes(self) -> int:
        """Return the number of OFE soil inputs that have been staged."""
        return len(self.stack)

    @property
    def stack_of_fns(self) -> bool:
        """Return True if every file referenced in ``stack`` exists."""
        return all(exists(fn) for fn in self.stack)

    def write(self, dst_fn: str, ksflag: int = 0) -> None:
        """Write the merged soil definition to ``dst_fn``."""
        assert len(self.stack) > 0

        versions = set()
        for fn in self.stack:
            lines = read_soil_lines(fn)
            for L in lines:
                if not L.startswith('#'):
                    versions.add(L)
                    break

        assert len(versions) == 1, f"Soils must be of the same version ({versions})"
        version = versions.pop() 

        s = [f"{version}\n{self.description}\nAny comments:\n{self.num_ofes} {ksflag}\n"]

        for fn in self.stack:
            lines = read_soil_lines(fn)
            i = 0
            for L in lines:
                if not L.startswith('#'):
                    if i > 2:
                        s.append(L)
                    i += 1
        s.append('\n\n')

        with open(dst_fn, 'w') as pf:
            pf.write(''.join(s))
