from pathlib import Path

import pytest

from wepppy.topo.wbt.wbt_documentation import generate_wbt_documentation


@pytest.mark.unit
@pytest.mark.parametrize("mask", ["netful.vrt", "netful.tif"])
def test_documented_stream_polygons_use_workspace_mask(tmp_path: Path, mask: str) -> None:
    (tmp_path / mask).touch()
    (tmp_path / "netful.geojson").touch()

    markdown = generate_wbt_documentation(tmp_path)

    assert (tmp_path / "README.md").read_text() == markdown
    assert f"{mask}\n└─ netful.geojson" in markdown


@pytest.mark.unit
def test_mixed_stream_masks_have_no_inferred_polygon_source(tmp_path: Path) -> None:
    for name in ("netful.tif", "netful.vrt", "netful.geojson"):
        (tmp_path / name).touch()

    markdown = generate_wbt_documentation(tmp_path, to_readme_md=False)

    assert "└─ netful.geojson" not in markdown
    assert "### `netful.geojson`" in markdown
