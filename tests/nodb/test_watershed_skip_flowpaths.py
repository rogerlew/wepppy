from __future__ import annotations

import pytest

from wepppy.nodb.core.watershed import Watershed


pytestmark = pytest.mark.unit


def test_skip_flowpaths_defaults_true() -> None:
    watershed = Watershed.__new__(Watershed)
    watershed._skip_flowpaths = False

    assert watershed.skip_flowpaths is True
