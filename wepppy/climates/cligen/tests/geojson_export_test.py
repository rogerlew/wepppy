from pathlib import Path

from wepppy.climates.cligen import CligenStationsManager


def test_geojson_export(tmp_path):
    manager = CligenStationsManager(bbox=[-120, 47, -115, 42])

    assert manager.stations, "No stations found in the bounding box"

    output_path = Path(tmp_path) / "stations.geojson"
    manager.export_to_geojson(str(output_path))

    assert output_path.exists(), "GeoJSON export did not produce a file"
    assert "FeatureCollection" in output_path.read_text()
    assert manager.states["KS"]
