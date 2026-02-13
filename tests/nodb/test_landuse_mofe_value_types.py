from __future__ import annotations

import pytest

from wepppy.nodb.core.landuse import Landuse

pytestmark = pytest.mark.unit


def test_post_instance_loaded_normalizes_domlc_mofe_values_to_strings() -> None:
    # Bypass __init__ to test load-time normalization behavior without any run setup.
    instance = object.__new__(Landuse)
    instance.domlc_mofe_d = {"12": {"2": 111, "10": "42", "1": None}}

    result = Landuse._post_instance_loaded(instance)
    assert result is instance

    assert list(instance.domlc_mofe_d["12"].keys()) == ["1", "2", "10"]
    assert instance.domlc_mofe_d["12"]["2"] == "111"
    assert instance.domlc_mofe_d["12"]["10"] == "42"
    assert instance.domlc_mofe_d["12"]["1"] is None

