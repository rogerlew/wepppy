from __future__ import annotations

import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.api as rq_api_module


pytestmark = pytest.mark.routes


@pytest.fixture()
def rq_landuse_and_soils_client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(rq_api_module.rq_api_bp)

    with app.test_client() as client:
        yield client


def test_landuse_and_soils_requires_extent(rq_landuse_and_soils_client):
    response = rq_landuse_and_soils_client.post("/rq/api/landuse_and_soils", json={})

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["message"] == "Expecting extent"
