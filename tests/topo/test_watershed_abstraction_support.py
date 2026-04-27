import numpy as np
import pytest

from wepppy.topo.watershed_abstraction import watershed_abstraction
from wepppy.topo.watershed_abstraction.support import cummnorm_distance


@pytest.mark.unit
def test_cummnorm_distance_normalizes_integer_distances() -> None:
    distance_p = cummnorm_distance(np.array([1, 1, 2], dtype=np.int64))

    assert distance_p.dtype == np.float64
    np.testing.assert_allclose(distance_p, np.array([0.0, 1.0 / 3.0, 1.0]))


@pytest.mark.unit
def test_transform_px_to_wgs_returns_geojson_coordinate_lists(monkeypatch) -> None:
    class DummyTransformer:
        def __init__(self, **_kwargs) -> None:
            pass

        @staticmethod
        def transform(e, n):
            return (
                np.asarray(e, dtype=np.float64) + 100.0,
                np.asarray(n, dtype=np.float64) + 200.0,
            )

    monkeypatch.setattr(watershed_abstraction, "GeoTransformer", DummyTransformer)

    properties, coordinates = watershed_abstraction.transform_px_to_wgs(
        (
            "+proj=utm",
            np.array([0, 1]),
            np.array([2, 3]),
            [10.0, 30.0, 0.0, 100.0, 0.0, -30.0],
            {"id": 1},
        )
    )

    assert properties == {"id": 1}
    assert coordinates == [[110.0, 240.0], [140.0, 210.0]]
