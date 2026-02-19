from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
pytest.importorskip("flask_security")
from wtforms.validators import ValidationError

import wepppy.weppcloud.app as app_module


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("field_label", "value"),
    [
        ("First Name", "http://example.com"),
        ("First Name", "Jane/Doe"),
        ("Last Name", "Doe:Admin"),
    ],
)
def test_reject_url_like_name_raises_validation_error(field_label: str, value: str) -> None:
    field = SimpleNamespace(data=value, label=SimpleNamespace(text=field_label))

    with pytest.raises(ValidationError, match=r"cannot contain ':' or '/'"):
        app_module._reject_url_like_name(None, field)


def test_reject_url_like_name_allows_plain_names() -> None:
    first_name_field = SimpleNamespace(data="Anne-Marie", label=SimpleNamespace(text="First Name"))
    last_name_field = SimpleNamespace(data="O'Neil", label=SimpleNamespace(text="Last Name"))

    app_module._reject_url_like_name(None, first_name_field)
    app_module._reject_url_like_name(None, last_name_field)
