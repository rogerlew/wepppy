from __future__ import annotations

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
