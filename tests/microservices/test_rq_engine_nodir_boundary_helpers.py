from __future__ import annotations

import json

import pytest

from wepppy.microservices.rq_engine import (
    ash_routes,
    climate_routes,
    debris_flow_routes,
    export_routes,
    landuse_routes,
    omni_routes,
    soils_routes,
    treatments_routes,
    upload_climate_routes,
    watershed_routes,
)
from wepppy.runtime_paths.errors import NoDirError

pytestmark = pytest.mark.microservice


class _AttrShapedError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("attr-shaped runtime error")
        self.http_status = 409
        self.code = "ATTR_SHAPED"
        self.message = "attr-shaped"


_ROUTES_WITH_HELPER = [
    ash_routes,
    climate_routes,
    debris_flow_routes,
    export_routes,
    landuse_routes,
    omni_routes,
    soils_routes,
    treatments_routes,
    upload_climate_routes,
    watershed_routes,
]


@pytest.mark.parametrize("route_module", _ROUTES_WITH_HELPER)
def test_maybe_nodir_error_response_ignores_attr_shaped_runtime_exceptions(route_module) -> None:
    response = route_module._maybe_nodir_error_response(_AttrShapedError())
    assert response is None


@pytest.mark.parametrize("route_module", _ROUTES_WITH_HELPER)
def test_maybe_nodir_error_response_maps_nodir_errors(route_module) -> None:
    response = route_module._maybe_nodir_error_response(
        NoDirError(http_status=409, code="NODIR_ARCHIVE_ACTIVE", message="archive-backed")
    )

    assert response is not None
    assert response.status_code == 409

    payload = json.loads(response.body.decode("utf-8"))
    assert payload["error"]["code"] == "NODIR_ARCHIVE_ACTIVE"
    assert payload["error"]["message"] == "archive-backed"
