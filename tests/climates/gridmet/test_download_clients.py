from __future__ import annotations

import json
import stat
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import netCDF4
import numpy as np
import pytest
import requests

from wepppy.climates.gridmet import acquisition
from wepppy.climates.gridmet import client as grid_client
from wepppy.climates.gridmet import gridmet_singlelocation_client as point_client

pytestmark = pytest.mark.unit
_ONE_DAY_RANGE = {"start_date": date(2025, 1, 1), "end_date": date(2025, 1, 1)}


class _Response:
    def __init__(
        self,
        status: int,
        *,
        payload: Any = None,
        body: bytes = b"",
        json_error: ValueError | None = None,
        headers: dict[str, str] | None = None,
        stream_error: BaseException | None = None,
    ) -> None:
        self.status_code = status
        self._payload = payload
        self._body = body or (json.dumps(payload).encode() if payload is not None else b"")
        self._json_error = json_error
        self.headers = headers or {}
        self._stream_error = stream_error
        self.closed = False

    def json(self) -> Any:
        if self._json_error is not None:
            raise self._json_error
        return self._payload

    def iter_content(self, *, chunk_size: int) -> Iterator[bytes]:
        assert chunk_size > 0
        if self._stream_error is not None:
            raise self._stream_error
        yield self._body

    def close(self) -> None:
        self.closed = True


def _netcdf_bytes(
    tmp_path: Path,
    *,
    variable_name: str = "precipitation_amount",
    days: int = 365,
    latitudes: int = 1,
) -> bytes:
    path = tmp_path / f"source-{variable_name}.nc"
    with netCDF4.Dataset(path, "w", format="NETCDF3_CLASSIC") as dataset:
        dataset.createDimension("day", days)
        dataset.createDimension("lat", latitudes)
        dataset.createDimension("lon", 1)
        dataset.createVariable("day", "i4", ("day",))[:] = np.arange(days)
        dataset.createVariable("lat", "f4", ("lat",))[:] = np.linspace(46.0, 46.5, latitudes)
        dataset.createVariable("lon", "f4", ("lon",))[:] = [-116.0]
        variable = dataset.createVariable(variable_name, "f4", ("day", "lat", "lon"))
        variable.description = "test GridMET variable"
        variable.units = "mm"
        variable[:] = np.full((days, latitudes, 1), 1.25, dtype=np.float32)
    return path.read_bytes()


def test_single_location_retries_transient_status_then_returns_valid_payload() -> None:
    responses = iter(
        [
            _Response(502),
            _Response(503),
            _Response(200, payload={"data": [{"yyyy-mm-dd": ["2025-01-01"], "pr(mm)": [1.0]}]}),
        ]
    )
    delays: list[float] = []

    data = acquisition.request_single_location_json(
        "https://example.invalid/gridmet",
        required_series=("pr(mm)",),
        **_ONE_DAY_RANGE,
        get=lambda *_args, **_kwargs: next(responses),
        sleep=delays.append,
    )

    assert data["pr(mm)"] == [1.0]
    assert delays == [5.0, 10.0]


def test_single_location_permanent_http_error_is_not_retried() -> None:
    calls = 0

    def _get(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return _Response(400)

    with pytest.raises(acquisition.GridMetAcquisitionError, match="non-retryable HTTP 400"):
        acquisition.request_single_location_json(
            "https://example.invalid/gridmet",
            required_series=("pr(mm)",),
            **_ONE_DAY_RANGE,
            get=_get,
            sleep=lambda _delay: None,
        )

    assert calls == 1


def test_single_location_redirect_is_rejected_without_following() -> None:
    observed: list[dict[str, Any]] = []

    def _get(*_args, **kwargs):
        observed.append(kwargs)
        return _Response(302, headers={"Location": "http://127.0.0.1/internal"})

    with pytest.raises(acquisition.GridMetAcquisitionError, match="non-retryable HTTP 302"):
        acquisition.request_single_location_json(
            "https://example.invalid/gridmet",
            required_series=("pr(mm)",),
            **_ONE_DAY_RANGE,
            get=_get,
            sleep=lambda _delay: None,
        )

    assert len(observed) == 1
    assert observed[0]["allow_redirects"] is False


def test_single_location_invalid_schema_exhausts_without_response_body() -> None:
    secret_marker = "upstream-body-must-not-be-logged"

    with pytest.raises(acquisition.GridMetAcquisitionError) as caught:
        acquisition.request_single_location_json(
            "https://example.invalid/gridmet",
            required_series=("pr(mm)",),
            **_ONE_DAY_RANGE,
            get=lambda *_args, **_kwargs: _Response(
                200,
                payload={"error": secret_marker},
            ),
            sleep=lambda _delay: None,
        )

    assert secret_marker not in str(caught.value)


def test_single_location_invalid_json_retries_to_exhaustion() -> None:
    calls = 0

    def _get(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return _Response(200, body=b"not JSON")

    with pytest.raises(acquisition.GridMetAcquisitionError, match="invalid JSON response"):
        acquisition.request_single_location_json(
            "https://example.invalid/gridmet",
            required_series=("pr(mm)",),
            **_ONE_DAY_RANGE,
            get=_get,
            sleep=lambda _delay: None,
        )

    assert calls == 3


def test_single_location_timeout_retries_and_closes_valid_response() -> None:
    valid = _Response(200, payload={"data": [{"yyyy-mm-dd": ["2025-01-01"], "pr(mm)": [1.0]}]})
    responses: Iterator[Any] = iter([requests.exceptions.Timeout("idle"), valid])
    observed_kwargs: list[dict[str, Any]] = []

    def _get(*_args, **kwargs):
        observed_kwargs.append(kwargs)
        item = next(responses)
        if isinstance(item, BaseException):
            raise item
        return item

    result = acquisition.request_single_location_json(
        "https://example.invalid/gridmet",
        required_series=("pr(mm)",),
        **_ONE_DAY_RANGE,
        get=_get,
        sleep=lambda _delay: None,
    )

    assert result["pr(mm)"] == [1.0]
    assert valid.closed is True
    assert observed_kwargs[0]["timeout"] == acquisition.SINGLE_LOCATION_TIMEOUT
    assert observed_kwargs[0]["stream"] is True
    assert observed_kwargs[0]["allow_redirects"] is False


def test_single_location_streamed_byte_limit_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(acquisition, "MAX_SINGLE_LOCATION_BYTES", 8)
    with pytest.raises(acquisition.GridMetAcquisitionError, match="byte limit"):
        acquisition.request_single_location_json(
            "https://example.invalid/gridmet",
            required_series=("pr(mm)",),
            **_ONE_DAY_RANGE,
            get=lambda *_args, **_kwargs: _Response(200, body=b"123456789"),
            sleep=lambda _delay: None,
        )


def test_single_location_rejects_non_numeric_series() -> None:
    with pytest.raises(acquisition.GridMetAcquisitionError, match="contains a non-numeric value"):
        acquisition.request_single_location_json(
            "https://example.invalid/gridmet",
            required_series=("pr(mm)",),
            **_ONE_DAY_RANGE,
            get=lambda *_args, **_kwargs: _Response(
                200,
                payload={"data": [{"yyyy-mm-dd": ["2025-01-01"], "pr(mm)": ["bad"]}]},
            ),
            sleep=lambda _delay: None,
        )


@pytest.mark.parametrize(
    "dates",
    [
        ["2025-01-01", "2025-01-02"],
        ["2025-01-01", "2025-01-03"],
        ["2025-01-01", "2025-01-02", "2025-01-02"],
        ["2025-01-02", "2025-01-01", "2025-01-03"],
    ],
    ids=("missing-tail", "gap", "duplicate", "out-of-order"),
)
def test_single_location_rejects_incomplete_or_noncontiguous_dates(dates: list[str]) -> None:
    with pytest.raises(acquisition.GridMetAcquisitionError, match="does not exactly cover"):
        acquisition.request_single_location_json(
            "https://example.invalid/gridmet",
            required_series=("pr(mm)",),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 3),
            get=lambda *_args, **_kwargs: _Response(
                200,
                payload={"data": [{"yyyy-mm-dd": dates, "pr(mm)": [1.0] * len(dates)}]},
            ),
            sleep=lambda _delay: None,
        )


def test_single_location_public_precip_path_preserves_dataframe_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = [
        (date(2025, 1, 1) + timedelta(days=offset)).isoformat()
        for offset in range(365)
    ]
    payload = {
        "data": [
            {
                "yyyy-mm-dd": dates,
                "pr(mm)": ["1.5"] * 365,
            }
        ]
    }
    monkeypatch.setattr(acquisition.requests, "get", lambda *_args, **_kwargs: _Response(200, payload=payload))

    result = point_client.retrieve_historical_precip(-116.0, 46.0, 2025, 2025)

    assert list(result.columns) == ["pr(mm/day)"]
    assert result["pr(mm/day)"].tolist() == [1.5] * 365
    assert result.index.strftime("%Y-%m-%d").tolist() == dates


def test_single_location_public_wind_and_full_timeseries_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = [
        (date(2025, 1, 1) + timedelta(days=offset)).isoformat()
        for offset in range(365)
    ]
    record = {
        "yyyy-mm-dd": dates,
        "pr(mm)": [1.5] * 365,
        "srad(Wm-2)": [100.0] * 365,
        "tmmx(K)": [293.15] * 365,
        "tmmn(K)": [283.15] * 365,
        "vs(m/s)": [2.5] * 365,
        "th(DegreesClockwisefromnorth)": [180.0] * 365,
        "rmin(%)": [40.0] * 365,
        "rmax(%)": [60.0] * 365,
    }
    monkeypatch.setattr(
        acquisition.requests,
        "get",
        lambda *_args, **_kwargs: _Response(200, payload={"data": [record]}),
    )

    wind = point_client.retrieve_historical_wind(-116.0, 46.0, 2025, 2025)
    full = point_client.retrieve_historical_timeseries(-116.0, 46.0, 2025, 2025)

    assert wind.to_dict("list") == {
        "vs(m/s)": [2.5] * 365,
        "th(DegreesClockwisefromnorth)": [180.0] * 365,
    }
    assert full.loc["2025-01-01", "tmmx(degc)"] == pytest.approx(20.0)
    assert full.loc["2025-01-01", "tmmn(degc)"] == pytest.approx(10.0)
    assert full.loc["2025-01-01", "srad(l/day)"] == pytest.approx(206.45)
    assert full.loc["2025-01-01", "tdew(degc)"] <= 10.0


def test_grid_retries_html_then_atomically_publishes_valid_netcdf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = _netcdf_bytes(tmp_path)
    responses = iter([_Response(503, body=b"<html>unavailable</html>"), _Response(200, body=valid)])
    delays: list[float] = []
    monkeypatch.setattr(grid_client.requests, "get", lambda *_args, **_kwargs: next(responses))
    monkeypatch.setattr(grid_client.time, "sleep", delays.append)

    result = grid_client.retrieve_nc(
        grid_client.GridMetVariable.Precipitation,
        [-117.0, 47.0, -116.0, 46.0],
        2025,
        str(tmp_path),
        _id="grid",
    )

    assert result == "grid"
    assert delays == [5.0]
    with netCDF4.Dataset(tmp_path / "grid.nc") as dataset:
        assert dataset.variables["precipitation_amount"].shape == (365, 1, 1)
    values, abbreviation, units = grid_client.read_nc(
        tmp_path / "grid.nc",
        grid_client.GridMetVariable.Precipitation,
    )
    assert values.shape == (365, 1, 1)
    assert abbreviation == "pr"
    assert units == "mm"
    assert stat.S_IMODE((tmp_path / "grid.nc").stat().st_mode) == 0o644
    assert list(tmp_path.glob(".grid.*.nc.part")) == []


def test_grid_validator_accepts_completed_leap_year_and_current_prefix(tmp_path: Path) -> None:
    leap_path = tmp_path / "leap.nc"
    leap_path.write_bytes(_netcdf_bytes(tmp_path, days=366))
    grid_client._validate_gridmet_netcdf(
        leap_path,
        "precipitation_amount",
        bbox=[-117.0, 47.0, -116.0, 46.0],
        year=2024,
    )

    current_path = tmp_path / "current.nc"
    current_path.write_bytes(_netcdf_bytes(tmp_path, days=1))
    grid_client._validate_gridmet_netcdf(
        current_path,
        "precipitation_amount",
        bbox=[-117.0, 47.0, -116.0, 46.0],
        year=date.today().year,
    )


def test_grid_invalid_payload_exhaustion_preserves_existing_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "grid.nc"
    destination.write_bytes(_netcdf_bytes(tmp_path))
    before = destination.read_bytes()
    monkeypatch.setattr(
        grid_client.requests,
        "get",
        lambda *_args, **_kwargs: _Response(200, body=b"<html>not netcdf</html>"),
    )
    monkeypatch.setattr(grid_client.time, "sleep", lambda _delay: None)

    with pytest.raises(acquisition.GridMetAcquisitionError, match="after 3 attempts"):
        grid_client.retrieve_nc(
            grid_client.GridMetVariable.Precipitation,
            [-117.0, 47.0, -116.0, 46.0],
            2025,
            str(tmp_path),
            _id="grid",
        )

    assert destination.read_bytes() == before
    assert list(tmp_path.glob(".grid.*.nc.part")) == []


def test_grid_missing_requested_variable_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wrong = _netcdf_bytes(tmp_path, variable_name="air_temperature")
    monkeypatch.setattr(grid_client.requests, "get", lambda *_args, **_kwargs: _Response(200, body=wrong))
    monkeypatch.setattr(grid_client.time, "sleep", lambda _delay: None)

    with pytest.raises(acquisition.GridMetAcquisitionError, match="missing required variables"):
        grid_client.retrieve_nc(
            grid_client.GridMetVariable.Precipitation,
            [-117.0, 47.0, -116.0, 46.0],
            2025,
            str(tmp_path),
            _id="grid",
        )


def test_grid_truncated_netcdf_is_retried_and_not_published(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        grid_client.requests,
        "get",
        lambda *_args, **_kwargs: _Response(200, body=b"CDF\x01\x00\x00"),
    )
    monkeypatch.setattr(grid_client.time, "sleep", lambda _delay: None)

    with pytest.raises(acquisition.GridMetAcquisitionError, match="complete NetCDF3"):
        grid_client.retrieve_nc(
            grid_client.GridMetVariable.Precipitation,
            [-117.0, 47.0, -116.0, 46.0],
            2025,
            str(tmp_path),
            _id="truncated",
        )

    assert not (tmp_path / "truncated.nc").exists()
    assert list(tmp_path.glob(".truncated.*.nc.part")) == []


def test_grid_valid_header_tail_truncation_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    complete = _netcdf_bytes(tmp_path)
    truncated = complete[:-400]
    # This is the dangerous case: netCDF4 accepts the header and shape even
    # though record data at the tail is absent.
    with netCDF4.Dataset("memory", memory=truncated) as dataset:
        assert dataset.variables["precipitation_amount"].shape == (365, 1, 1)

    monkeypatch.setattr(
        grid_client.requests,
        "get",
        lambda *_args, **_kwargs: _Response(200, body=truncated),
    )
    monkeypatch.setattr(grid_client.time, "sleep", lambda _delay: None)

    with pytest.raises(acquisition.GridMetAcquisitionError, match="complete NetCDF3"):
        grid_client.retrieve_nc(
            grid_client.GridMetVariable.Precipitation,
            [-117.0, 47.0, -116.0, 46.0],
            2025,
            str(tmp_path),
            _id="tail-truncated",
        )

    assert not (tmp_path / "tail-truncated.nc").exists()


def test_grid_declared_content_length_mismatch_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    complete = _netcdf_bytes(tmp_path)
    monkeypatch.setattr(
        grid_client.requests,
        "get",
        lambda *_args, **_kwargs: _Response(
            200,
            body=complete[:-100],
            headers={"Content-Length": str(len(complete))},
        ),
    )
    monkeypatch.setattr(grid_client.time, "sleep", lambda _delay: None)

    with pytest.raises(acquisition.GridMetAcquisitionError, match="does not match declared"):
        grid_client.retrieve_nc(
            grid_client.GridMetVariable.Precipitation,
            [-117.0, 47.0, -116.0, 46.0],
            2025,
            str(tmp_path),
            _id="short-response",
        )


def test_grid_content_decoding_failure_retries_and_closes_responses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses: list[_Response] = []

    def _get(*_args, **kwargs):
        assert kwargs["timeout"] == acquisition.GRID_TIMEOUT
        assert kwargs["stream"] is True
        assert kwargs["allow_redirects"] is False
        response = _Response(
            200,
            stream_error=requests.exceptions.ContentDecodingError("invalid gzip"),
        )
        responses.append(response)
        return response

    monkeypatch.setattr(grid_client.requests, "get", _get)
    monkeypatch.setattr(grid_client.time, "sleep", lambda _delay: None)

    with pytest.raises(acquisition.GridMetAcquisitionError, match="ContentDecodingError"):
        grid_client.retrieve_nc(
            grid_client.GridMetVariable.Precipitation,
            [-117.0, 47.0, -116.0, 46.0],
            2025,
            str(tmp_path),
            _id="encoded",
        )

    assert len(responses) == 3
    assert all(response.closed for response in responses)
    assert list(tmp_path.glob(".encoded.*.nc.part")) == []


def test_grid_chunked_byte_limit_and_spatial_dimension_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized_shape = _netcdf_bytes(tmp_path, latitudes=30)
    monkeypatch.setattr(grid_client.time, "sleep", lambda _delay: None)
    monkeypatch.setattr(grid_client, "MAX_GRID_BYTES", 8)
    monkeypatch.setattr(
        grid_client.requests,
        "get",
        lambda *_args, **_kwargs: _Response(200, body=oversized_shape),
    )
    with pytest.raises(acquisition.GridMetAcquisitionError, match="byte limit"):
        grid_client.retrieve_nc(
            grid_client.GridMetVariable.Precipitation,
            [-116.1, 46.1, -116.0, 46.0],
            2025,
            str(tmp_path),
            _id="oversized-bytes",
        )

    monkeypatch.setattr(grid_client, "MAX_GRID_BYTES", acquisition.MAX_GRID_BYTES)
    with pytest.raises(acquisition.GridMetAcquisitionError, match="spatial dimensions"):
        grid_client.retrieve_nc(
            grid_client.GridMetVariable.Precipitation,
            [-116.1, 46.1, -116.0, 46.0],
            2025,
            str(tmp_path),
            _id="oversized-shape",
        )


def test_grid_permanent_http_error_is_not_retried(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def _get(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return _Response(404)

    monkeypatch.setattr(grid_client.requests, "get", _get)

    with pytest.raises(acquisition.GridMetAcquisitionError, match="non-retryable HTTP 404"):
        grid_client.retrieve_nc(
            grid_client.GridMetVariable.Precipitation,
            [-117.0, 47.0, -116.0, 46.0],
            2025,
            str(tmp_path),
            _id="grid",
        )

    assert calls == 1


def test_grid_rejects_path_like_download_id_before_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        grid_client.requests,
        "get",
        lambda *_args, **_kwargs: pytest.fail("request must not be attempted"),
    )

    with pytest.raises(ValueError, match="filename component"):
        grid_client.retrieve_nc(
            grid_client.GridMetVariable.Precipitation,
            [-117.0, 47.0, -116.0, 46.0],
            2025,
            str(tmp_path),
            _id="../outside",
        )
