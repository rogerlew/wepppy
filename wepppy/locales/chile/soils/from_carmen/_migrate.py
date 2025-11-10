"""One-off helper to re-encode legacy Chile soils into 7778 format."""

from __future__ import annotations

from glob import glob
from os.path import join as _join
from os.path import split as _split

from wepppy.wepp.soils.utils import WeppSoilUtil


def migrate_soils(pattern: str = "*.sol", destination: str = "..") -> None:
    """Convert each matching `.sol` file to the WEPP 7778 format."""
    for sol_fn in glob(pattern):
        print(sol_fn)

        wsu = WeppSoilUtil(
            sol_fn,
            compute_erodibilities=True,
            compute_conductivity=True,
        )
        wsu7778 = wsu.to7778()

        wsu7778.write(_join(destination, _split(sol_fn)[-1]))


if __name__ == "__main__":
    migrate_soils()
