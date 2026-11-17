from __future__ import annotations

from types import SimpleNamespace

import pytest
from requests.exceptions import SSLError, Timeout

from wepppy.soils.ssurgo import ssurgo

pytestmark = pytest.mark.unit


def test_make_sda_post_request_ssl_error_raises_user_message(monkeypatch) -> None:
    def _raise_ssl_error(*args, **kwargs):
        raise SSLError("certificate verify failed")

    monkeypatch.setattr(ssurgo.requests, "post", _raise_ssl_error)

    with pytest.raises(ssurgo.SsurgoRequestError) as excinfo:
        ssurgo._make_sda_post_request("select 1")

    assert str(excinfo.value) == ssurgo._SSURGO_UNAVAILABLE_MESSAGE


def test_make_sda_post_request_timeout_retries_raise_user_message(monkeypatch) -> None:
    def _raise_timeout(*args, **kwargs):
        raise Timeout("request timed out")

    monkeypatch.setattr(ssurgo, "_SSURGO_MAX_RETRIES", 1)
    monkeypatch.setattr(ssurgo.requests, "post", _raise_timeout)

    with pytest.raises(ssurgo.SsurgoRequestError) as excinfo:
        ssurgo._make_sda_post_request("select 1")

    assert str(excinfo.value) == ssurgo._SSURGO_UNAVAILABLE_MESSAGE


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_make_sda_post_request_server_error_raises_user_message(monkeypatch, caplog, status):
    response = SimpleNamespace(status_code=status, content=b"<html>Bad Gateway</html>")
    monkeypatch.setattr(ssurgo.requests, "post", lambda *args, **kwargs: response)

    with pytest.raises(ssurgo.SsurgoRequestError) as excinfo:
        ssurgo._make_sda_post_request("select 1")

    assert str(excinfo.value) == ssurgo._SSURGO_UNAVAILABLE_MESSAGE
    assert f"HTTP {status}" in caplog.text


def test_make_sda_post_request_client_error_preserves_diagnostics(monkeypatch):
    response = SimpleNamespace(status_code=400, content=b"Invalid query")
    monkeypatch.setattr(ssurgo.requests, "post", lambda *args, **kwargs: response)

    with pytest.raises(ssurgo.SsurgoRequestError) as excinfo:
        ssurgo._make_sda_post_request("invalid sql")

    assert excinfo.value.args == ((b"Invalid query", "invalid sql"),)


def test_make_sda_post_request_success_preserves_response(monkeypatch):
    response = SimpleNamespace(status_code=200, content=b"<Table />")
    monkeypatch.setattr(ssurgo.requests, "post", lambda *args, **kwargs: response)

    assert ssurgo._make_sda_post_request("select 1") == response.content
