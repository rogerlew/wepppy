import numpy as np
import pytest

from wepppy.topo.topaz import topaz as topaz_mod


pytestmark = pytest.mark.unit


def test_create_dednm_input_uses_gdal_for_vrt(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    dem_path = tmp_path / "dem.vrt"
    dem_path.write_text("stub")

    class DummyBand:
        DataType = 1

        @staticmethod
        def ReadAsArray():
            return np.array([[1.0, 2.0], [3.0, 4.0]])

    class DummyDs:
        @staticmethod
        def GetRasterBand(_index: int):
            return DummyBand()

    gdal_open_calls = []

    def fake_gdal_open(path: str):
        gdal_open_calls.append(path)
        return DummyDs()

    monkeypatch.setattr(topaz_mod.gdal, "Open", fake_gdal_open)
    monkeypatch.setattr(topaz_mod, "imread", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("no backend")))

    class DummyTopaz:
        def __init__(self, dem: str, topaz_wd: str) -> None:
            self.dem = dem
            self.topaz_wd = topaz_wd
            self.dednm_inp = None

    dummy = DummyTopaz(str(dem_path), str(tmp_path))

    topaz_mod.TopazRunner._create_dednm_input(dummy)

    assert gdal_open_calls
    dednm_path = tmp_path / "DEDNM.INP"
    assert dednm_path.exists()
    lines = dednm_path.read_text().splitlines()
    assert len(lines) == 4
    assert dummy.dednm_inp == "DEDNM.INP"
