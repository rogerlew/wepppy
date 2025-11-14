from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from wepppy.wepp.interchange import hec_ras_boundary as boundary


class _StubTranslator:
    def wepp(self, *, top):  # type: ignore[override]
        return int(top)


class _StubWatershed:
    def __init__(self, subwta_path: Path, metric_path: Path) -> None:
        self.subwta = str(subwta_path)
        self.relief = str(metric_path)
        self.discha = None
        self.logger = None

    def translator_factory(self):
        return _StubTranslator()


class _DummyTransformer:
    def __init__(self, *_, **__):
        pass

    def transform(self, x, y):
        return x / 1000.0, y / 1000.0


@pytest.mark.unit
def test_build_boundary_condition_features_creates_geojson_and_gml(tmp_path, monkeypatch):
    subwta_path = tmp_path / "SUBWTA.ARC"
    metric_path = tmp_path / "RELIEF.ARC"
    subwta_path.write_text("subwta")
    metric_path.write_text("relief")

    subwta = np.array(
        [
            [0, 1114, 1114],
            [1114, 1114, 1114],
            [0, 0, 1114],
        ],
        dtype=np.int32,
    )
    metric = np.array(
        [
            [12.0, 6.0, 1.0],
            [5.0, 4.0, 2.0],
            [0.0, 0.0, 3.0],
        ],
        dtype=np.float64,
    )
    transform = (0.0, 10.0, 0.0, 0.0, 0.0, -10.0)

    def _fake_read_raster(path, dtype):
        if path == str(subwta_path):
            return subwta, transform, "EPSG:32611"
        if path == str(metric_path):
            return metric, transform, "EPSG:32611"
        raise AssertionError("unexpected path")

    monkeypatch.setattr(boundary, "read_raster", _fake_read_raster)
    monkeypatch.setattr(boundary, "GeoTransformer", _DummyTransformer)

    ws = _StubWatershed(subwta_path, metric_path)
    dest_dir = tmp_path / "boundaries"

    features = boundary.build_boundary_condition_features(ws, [1114], str(dest_dir), boundary_width_m=100.0)

    assert len(features) == 1
    feature = features[0]
    assert feature["geometry"]["type"] == "LineString"
    coords = feature["geometry"]["coordinates"]
    assert coords == [[0.025, -0.075], [0.025, 0.025]]
    assert feature["properties"]["topaz_id"] == 1114
    assert feature["properties"]["width_m"] == 100.0
    assert feature["properties"]["center_lon"] == pytest.approx(0.025)
    assert feature["properties"]["center_lat"] == pytest.approx(-0.025)

    gml_path = dest_dir / "bc_1114.gml"
    assert gml_path.exists()
    content = gml_path.read_text()
    assert "BoundaryCondition" in content
    root = ET.fromstring(content)
    ns = {"gml": "http://www.opengis.net/gml"}
    pos_text = root.find(".//gml:posList", ns).text
    assert pos_text is not None
    assert pos_text.strip() == "0.02500000 -0.07500000 0.02500000 0.02500000"
