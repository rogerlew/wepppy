from __future__ import annotations

import types

import numpy as np
import pytest

from wepppy.topo.watershed_abstraction import mofe_map as mofe_map_module


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_loader_cache() -> None:
    mofe_map_module._load_wepppyo3_mofe_map_assigner.cache_clear()


def test_loader_raises_explicit_error_when_module_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def _missing_module(_name: str):
        raise ModuleNotFoundError("not installed")

    monkeypatch.setattr(mofe_map_module.importlib, "import_module", _missing_module)

    with pytest.raises(RuntimeError, match="MOFE map assignment requires `wepppyo3.watershed_abstraction`"):
        mofe_map_module._load_wepppyo3_mofe_map_assigner()


def test_assign_mofe_map_with_wepppyo3_coerces_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_assigner(subwta, discha, topaz_ids, payload):
        captured["subwta_dtype"] = np.asarray(subwta).dtype
        captured["discha_dtype"] = np.asarray(discha).dtype
        captured["topaz_ids"] = list(topaz_ids)
        captured["payload"] = payload
        return np.ones_like(subwta, dtype=np.int64)

    fake_module = types.SimpleNamespace(assign_mofe_map=_fake_assigner)
    monkeypatch.setattr(mofe_map_module.importlib, "import_module", lambda _name: fake_module)

    result = mofe_map_module.assign_mofe_map_with_wepppyo3(
        subwta=np.array([[171, 171]], dtype=np.int64),
        discha=np.array([[5, 6]], dtype=np.int64),
        topaz_ids=[171],
        d_fractions_by_topaz={171: np.array([0.0, 0.5, 1.0], dtype=np.float32)},
    )

    assert captured["subwta_dtype"] == np.int32
    assert captured["discha_dtype"] == np.int32
    assert captured["topaz_ids"] == [171]
    assert captured["payload"] == {171: [0.0, 0.5, 1.0]}
    assert result.dtype == np.int32
    assert np.array_equal(result, np.array([[1, 1]], dtype=np.int32))
