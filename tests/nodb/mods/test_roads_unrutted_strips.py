"""RUPC-01 geometry and native-input boundaries."""
from pathlib import Path

import pytest
from shapely.geometry import LineString
from wepppy.nodb.mods.roads import _unrutted

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def test_normalization_coalesces_subdivision_and_duplicate():
    first = LineString([(0, 0), (1, 0)])
    second = LineString([(1, 0), (2, 0)])
    rows = [{"geometry": g, "signature": "same", "source": str(i)}
            for i, g in enumerate([first, second, first])]
    result = _unrutted.crossings(rows)
    assert len(result) == 1
    assert result[0]["geometry"].length == 2
    assert result[0]["sources"] == ["0", "1", "2"]
    reverse = _unrutted.crossings(list(reversed(rows)))
    assert reverse[0]["key"] == result[0]["key"]


def test_normalization_conflicts_but_allows_point_crossing():
    a = {"geometry": LineString([(0, 0), (2, 0)]), "signature": "a", "source": "a"}
    b = {"geometry": LineString([(1, 0), (3, 0)]), "signature": "b", "source": "b"}
    with pytest.raises(ValueError, match="conflicting"):
        _unrutted.crossings([a, b])
    b["geometry"] = LineString([(1, -1), (1, 1)])
    assert len(_unrutted.crossings([a, b])) == 2


def test_readback_rejects_zero_native_dimensions(tmp_path: Path):
    path = tmp_path / "p.slp"
    path.write_text("97.3\n1\n180 0.0\n2 1.0\n0,0.1 1,0.1\n")
    with pytest.raises(ValueError, match="positive"):
        _unrutted.slope_area(path)


def test_transverse_geometry_preserves_target_before_width_compression():
    geometry = _unrutted.road_geometry(30.0, 4.0)
    assert geometry["sim_length_m"] == 4.0
    assert geometry["sim_width_m"] == 30.0
    assert geometry["road_slope_pct"] == 4.0
    assert geometry["road_target_area_m2"] == 120.0


def test_native_dimensions_retain_tiny_positive_upstream_and_area(tmp_path):
    width = 503.9946300554462
    lengths = [0.0000001, 4.0, 10.0, 26.62741689796953]
    path = tmp_path / "strip.slp"
    area = _unrutted.write_slope(path, width, lengths, [0.1, 0.04, 0.1, 0.1])
    assert abs(area - width * sum(lengths)) <= 1e-6
    assert float(path.read_text().splitlines()[3].split()[1]) > 0


def test_disconnected_crossings_do_not_merge():
    rows = [{"geometry": LineString([(x, 0), (x+1, 0)]), "signature": "same", "source": str(x)} for x in (0, 3)]
    assert len(_unrutted.crossings(rows)) == 2


def test_branch_and_reversed_feature_keep_geometry_key():
    lines = [LineString([(0, 0), (1, 0)]), LineString([(1, 0), (2, 0)]), LineString([(1, 0), (1, 1)])]
    rows = [{"geometry": g, "signature": "same", "source": str(i)} for i, g in enumerate(lines)]
    a = _unrutted.crossings(rows)
    assert len(a) == 1
    for row in rows:
        row["geometry"] = LineString(list(row["geometry"].coords)[::-1])
    assert a[0]["key"] == _unrutted.crossings(rows)[0]["key"]


@pytest.mark.parametrize("value", [float('inf'), float('nan'), 0.0, -1.0])
def test_transverse_geometry_rejects_nonfinite_or_nonpositive(value):
    with pytest.raises(ValueError):
        _unrutted.road_geometry(value, 4.0)


def test_grid_connectivity_is_noded_then_traversed_once():
    # Small intersecting upload used to take >25s in repeated component scans.
    count = 24
    lines = [LineString([(i, 0), (i, count-1)]) for i in range(count)]
    lines += [LineString([(0, i), (count-1, i)]) for i in range(count)]
    rows = [{"geometry": g, "signature": "same", "source": str(i)} for i, g in enumerate(lines)]
    result = _unrutted.crossings(rows)
    assert len(result) == 1
    assert result[0]["geometry"].length == 2 * count * (count-1)
    assert len(result[0]["sources"]) == 2*count


def test_finite_dimensions_with_overflow_area_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="finite"):
        _unrutted.road_geometry(1e308, 100.)
    path = tmp_path / 'overflow.slp'
    path.write_text('97.3\n1\n180 1e308\n2 100\n0,.1 1,.1\n')
    with pytest.raises(ValueError, match="finite"):
        _unrutted.slope_area(path)


def test_manifest_detail_associates_shared_sources(tmp_path):
    import json
    from types import SimpleNamespace
    from wepppy.nodb.mods.roads import Roads
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps([{'segment_id': 'a', 'source_segment_ids': ['a', 'b'],
                                'segment_run_id': 900001, 'status': 'completed'}]))
    records = Roads._load_segment_execution_manifest(SimpleNamespace(roads_segment_pass_manifest_path=str(path)))
    assert records['a']['segment_run_id'] == records['b']['segment_run_id'] == 900001
