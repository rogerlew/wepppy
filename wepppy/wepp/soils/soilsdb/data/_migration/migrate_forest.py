"""One-off migration script that upgrades the legacy Forest soils to WEPP 7778."""

from __future__ import annotations

import os
from glob import glob
from os.path import split as _split

from wepppy.wepp.soils.utils import WeppSoilUtil


def migrate_forest_library(
    source_pattern: str = "../Forest2006/*.sol",
    target_directory: str = "../Forest",
) -> None:
    """Convert the legacy soils referenced by ``source_pattern`` to 7778 format."""
    for fn in glob(source_pattern):
        absolute = os.path.abspath(fn)
        print(absolute)
        _, tail = _split(absolute)

        soil = WeppSoilUtil(absolute)
        soil.to7778().write(f"{target_directory}/{tail}")


if __name__ == "__main__":  # pragma: no cover - developer migration hook
    migrate_forest_library()
