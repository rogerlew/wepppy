from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.mods.geneva import Geneva
from wepppy.nodb.mods.geneva.errors import GenevaGuardrailError


pytestmark = pytest.mark.unit


def test_set_enabled_rejects_non_wbt_runs_with_canonical_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    geneva = Geneva(str(tmp_path), "0.cfg")

    watershed = SimpleNamespace(delineation_backend_is_wbt=False)
    monkeypatch.setattr(Geneva, "watershed_instance", property(lambda _self: watershed), raising=False)

    with pytest.raises(GenevaGuardrailError) as exc_info:
        geneva.set_enabled(True)

    error = exc_info.value.to_error_payload()["error"]
    assert exc_info.value.code == "unsupported_backend"
    assert "WBT delineation backend" in error["message"]
    assert error["code"] == "unsupported_backend"


def test_set_enabled_rejects_unsupported_domain_with_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    geneva = Geneva(str(tmp_path), "0.cfg")

    watershed = SimpleNamespace(
        delineation_backend_is_wbt=True,
        _centroid=(10.0, 50.0),  # outside US envelope
        outlet=None,
    )
    landuse = SimpleNamespace(nlcd_db="copernicus_landcover", lc_fn="/tmp/landcover.tif")
    soils = SimpleNamespace(ssurgo_db="isric", ssurgo_fn="/tmp/isric.tif")

    monkeypatch.setattr(Geneva, "watershed_instance", property(lambda _self: watershed), raising=False)
    monkeypatch.setattr(Geneva, "landuse_instance", property(lambda _self: landuse), raising=False)
    monkeypatch.setattr(Geneva, "soils_instance", property(lambda _self: soils), raising=False)

    with pytest.raises(GenevaGuardrailError) as exc_info:
        geneva.set_enabled(True)

    payload = exc_info.value.to_error_payload()["error"]
    assert exc_info.value.code == "unsupported_domain"
    assert payload["code"] == "unsupported_domain"
    assert "US-only" in payload["message"]
    details = payload["details"]
    assert details["outside_us"] is True
    assert details["nlcd_compatible"] is False
    assert details["hsg_compatible"] is False
