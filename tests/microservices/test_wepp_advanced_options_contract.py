from __future__ import annotations

import re
from pathlib import Path

import pytest

from wepppy.microservices.rq_engine.wepp_run_payload import SUPPORTED_WEPP_RUN_FORM_FIELDS

pytestmark = pytest.mark.microservice

_FIELD_CALL_PATTERN = re.compile(
    r'ui\.(?:checkbox_field|numeric_field|text_field|select_field)\(\s*"([a-zA-Z0-9_]+)"'
)
_ADVANCED_OPTIONS_DIR = (
    Path(__file__).resolve().parents[2]
    / "wepppy"
    / "weppcloud"
    / "templates"
    / "controls"
    / "wepp_pure_advanced_options"
)


def _collect_advanced_option_form_fields() -> set[str]:
    fields: set[str] = set()
    for template_path in sorted(_ADVANCED_OPTIONS_DIR.glob("*.htm")):
        text = template_path.read_text(encoding="utf-8")
        fields.update(_FIELD_CALL_PATTERN.findall(text))
    return fields


def test_wepp_advanced_options_template_fields_are_supported_by_rq_engine_payload_parser() -> None:
    template_fields = _collect_advanced_option_form_fields()
    unsupported_fields = sorted(template_fields - SUPPORTED_WEPP_RUN_FORM_FIELDS)

    assert not unsupported_fields, (
        "WEPP advanced option fields are missing rq-engine payload handling: "
        + ", ".join(unsupported_fields)
    )
