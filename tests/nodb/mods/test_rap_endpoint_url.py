from __future__ import annotations

import pytest

from wepppy.landcover.rap import rangeland_analysis_platform as rap_module


pytestmark = pytest.mark.unit


def test_build_rap_cover_source_url_v3_uses_https_base_and_v3_subdir() -> None:
    source_url = rap_module._build_rap_cover_source_url("v3", "2025")

    assert source_url.startswith("/vsicurl/https://rangeland.ntsg.umt.edu/")
    assert source_url.endswith("/rap-vegetation-cover/v3/vegetation-cover-v3-2025.tif")
