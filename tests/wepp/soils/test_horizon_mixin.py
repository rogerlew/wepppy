from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from wepppy.wepp.soils.horizon_mixin import HorizonMixin, rosetta_texture_fractions

pytestmark = pytest.mark.unit


def test_rosetta_texture_fractions_derives_silt_from_total_sand_and_clay() -> None:
    assert rosetta_texture_fractions(sand=55.0, clay=20.0) == (55.0, 25.0, 20.0)


@pytest.mark.parametrize(
    ("sand", "clay"),
    [
        (80.0, 30.0),
        (float("nan"), 20.0),
        (55.0, float("inf")),
    ],
)
def test_rosetta_texture_fractions_rejects_nonphysical_texture(sand: float, clay: float) -> None:
    with pytest.raises(ValueError, match="Rosetta texture fractions"):
        rosetta_texture_fractions(sand=sand, clay=clay)


@pytest.mark.parametrize(("bd", "model_name"), [(1.52, "Rosetta3"), (None, "Rosetta2")])
def test_horizon_mixin_passes_derived_silt_to_rosetta(
    monkeypatch: pytest.MonkeyPatch,
    bd: float | None,
    model_name: str,
) -> None:
    predictions: list[dict[str, float]] = []

    class _FakeRosetta:
        def predict_kwargs(self, **kwargs: float) -> dict[str, float]:
            predictions.append(kwargs)
            return {"ks": 12.0, "wp": 0.12, "fc": 0.31}

    monkeypatch.setitem(
        sys.modules,
        "rosetta",
        SimpleNamespace(Rosetta2=_FakeRosetta, Rosetta3=_FakeRosetta),
    )

    class _Horizon(HorizonMixin):
        clay = 20.0
        sand = 55.0
        vfs = 5.0
        bd = None

    horizon = _Horizon()
    horizon.bd = bd
    horizon._rosettaPredict()

    assert predictions == [
        {
            "sand": 55.0,
            "silt": 25.0,
            "clay": 20.0,
            **({"bd": 1.52} if model_name == "Rosetta3" else {}),
        }
    ]
