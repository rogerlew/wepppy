"""MACA request identity and exact selection validation."""
from datetime import datetime
from urllib.parse import parse_qs, urlparse
from types import SimpleNamespace

import pytest

from wepppy.climates import downscaled_nmme_client as client
from wepppy.climates.maca_catalog import PROJECTION_OPTIONS, MacaSelectionError, parse_projection

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('projection', [value for value, _ in PROJECTION_OPTIONS])
def test_supported_projection_requests_provider_member(monkeypatch, projection):
    model, scenario = parse_projection(projection)
    urls = []

    def get(url, **kwargs):
        urls.append(url)
        return SimpleNamespace(status_code=200, json=lambda: {'data': [{
            'yyyy-mm-dd': ['2030-01-01', '2030-01-02'], 'pr(mm)': [4., 0.],
        }]})

    monkeypatch.setattr(client.requests, 'Session', lambda: SimpleNamespace(get=get))
    actual = client._retrieve(-116, 47, datetime(2030, 1, 1), datetime(2030, 1, 2), model, scenario, 'pr')
    member = 'r6i1p1' if model == 'CCSM4' else 'r1i1p1'
    query = parse_qs(urlparse(urls[0]).query)
    assert query['data-path'] == [f'PATH_TO_DODS/agg_macav2metdata_pr_{model}_{member}_{scenario}_CONUS_daily.nc']
    assert list(actual['pr(mm)']) == [4., 0.]


def test_unknown_model_fails_before_network(monkeypatch):
    def unexpected():
        pytest.fail('Invalid model attempted network access')
    monkeypatch.setattr(client.requests, 'Session', unexpected)
    with pytest.raises(MacaSelectionError):
        client._retrieve(-116, 47, '2030-01-01', '2030-01-02', '../CCSM4', 'rcp45_2006_2099', 'pr')
