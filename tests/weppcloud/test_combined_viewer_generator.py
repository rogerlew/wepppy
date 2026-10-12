from types import SimpleNamespace
from urllib.parse import urlsplit, parse_qs
import json


def test_generator_bounds_encoding_and_does_not_mutate_metadata(monkeypatch):
    import wepppy.weppcloud.combined_watershed_viewer_generator as module
    extents = [[0, 0, 1, 1], [-5, -3, 7, 9]]
    runs = {name: SimpleNamespace(map=SimpleNamespace(extent=extent, zoom=10), config_stem='actual')
            for name, extent in zip(['a', 'b'], extents)}
    monkeypatch.setattr(module, 'get_wd', lambda run: run)
    monkeypatch.setattr(module, 'Ron', SimpleNamespace(getInstance=lambda run: runs[run]))
    monkeypatch.setattr(module, 'Wepp', SimpleNamespace(getInstance=lambda run: SimpleNamespace(phosphorus_opts=SimpleNamespace(isvalid=True))))
    title = 'A & B # <script> title'
    url = module.combined_watershed_viewer_generator(['a','b','a'], title)
    parsed = parse_qs(urlsplit(url).query)
    assert json.loads(parsed['center'][0]) == [3, 1]
    assert parsed['title'] == [title]
    assert len(json.loads(parsed['ws'][0])) == 2
    assert extents[0] == [0, 0, 1, 1]


def test_undelineated_run_has_explicit_readiness_failure(monkeypatch):
    import pytest
    import wepppy.weppcloud.combined_watershed_viewer_generator as module
    monkeypatch.setattr(module, 'get_wd', lambda run: run)
    monkeypatch.setattr(module, 'Ron', SimpleNamespace(getInstance=lambda run: SimpleNamespace(map=None)))
    with pytest.raises(ValueError, match='not ready'):
        module.collection_metadata(['unfinished'])
