from __future__ import annotations

from contextlib import nullcontext

import pytest

from wepppy.nodb.core.landuse import Landuse

pytestmark = pytest.mark.unit


def test_modify_mapping_updates_multi_ofe_assignments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    landuse = Landuse.__new__(Landuse)
    landuse.wd = "/tmp/test-run"
    landuse.managements = {
        "21": object(),
        "22": object(),
        "42": object(),
    }
    # Topaz-level dominant mapping has no "21" values, but MOFE segments do.
    landuse.domlc_d = {"101": "42", "102": "42"}
    landuse.domlc_mofe_d = {
        "101": {"1": "21", "2": "22", "3": "21"},
        "102": {"1": "42"},
    }
    landuse.locked = lambda: nullcontext()

    build_managements_calls: list[bool] = []
    landuse.build_managements = lambda: build_managements_calls.append(True)
    monkeypatch.setattr(
        Landuse,
        "getInstance",
        classmethod(
            lambda cls, wd: (_ for _ in ()).throw(
                AssertionError("modify_mapping should not rehydrate from cache")
            )
        ),
    )

    Landuse.modify_mapping(landuse, "21", "42")

    assert landuse.domlc_d == {"101": "42", "102": "42"}
    assert landuse.domlc_mofe_d == {
        "101": {"1": "42", "2": "22", "3": "42"},
        "102": {"1": "42"},
    }
    assert len(build_managements_calls) == 1
