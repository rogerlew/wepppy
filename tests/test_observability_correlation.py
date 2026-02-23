from __future__ import annotations

import logging
import re

import pytest

from wepppy.observability import correlation

pytestmark = pytest.mark.unit

_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _make_record(message: str) -> logging.LogRecord:
    logger = logging.getLogger("tests.test_observability_correlation")
    return logger.makeRecord(
        logger.name,
        logging.INFO,
        __file__,
        1,
        message,
        (),
        None,
    )


def test_normalize_correlation_id_accepts_valid_value() -> None:
    assert correlation.normalize_correlation_id("cid-valid_01:stage") == "cid-valid_01:stage"


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "  ",
        "invalid with spaces",
        "!invalid",
        "x" * 129,
    ],
)
def test_normalize_correlation_id_rejects_invalid_values(raw: str | None) -> None:
    assert correlation.normalize_correlation_id(raw) is None


def test_bind_correlation_id_generates_when_missing() -> None:
    correlation_id, token = correlation.bind_correlation_id(None)
    try:
        assert _CORRELATION_ID_PATTERN.match(correlation_id)
        assert correlation.current_correlation_id() == correlation_id
    finally:
        correlation.reset_correlation_id(token)


def test_bind_correlation_id_uses_valid_inbound_value() -> None:
    correlation_id, token = correlation.bind_correlation_id("cid-inbound-01")
    try:
        assert correlation_id == "cid-inbound-01"
        assert correlation.current_correlation_id() == "cid-inbound-01"
    finally:
        correlation.reset_correlation_id(token)


def test_select_inbound_correlation_id_prefers_header_by_default() -> None:
    token = correlation.set_correlation_id("cid-current-01")
    try:
        inbound = correlation.select_inbound_correlation_id("cid-header-01")
    finally:
        correlation.reset_correlation_id(token)

    assert inbound == "cid-header-01"


def test_select_inbound_correlation_id_can_prefer_current_context() -> None:
    token = correlation.set_correlation_id("cid-current-02")
    try:
        inbound = correlation.select_inbound_correlation_id(
            "cid-header-02",
            prefer_current_context=True,
        )
    finally:
        correlation.reset_correlation_id(token)

    assert inbound == "cid-current-02"


def test_log_record_factory_injects_default_fields() -> None:
    correlation.install_correlation_log_record_factory()
    token = correlation.set_correlation_id(None)
    try:
        record = _make_record("no correlation context")
    finally:
        correlation.reset_correlation_id(token)
    assert record.correlation_id == "-"
    assert record.trace_id == "-"


def test_log_record_factory_uses_active_correlation_id() -> None:
    correlation.install_correlation_log_record_factory()
    token = correlation.set_correlation_id("cid-log-context-01")
    try:
        record = _make_record("with correlation context")
    finally:
        correlation.reset_correlation_id(token)
    assert record.correlation_id == "cid-log-context-01"
    assert record.trace_id == "cid-log-context-01"


def test_log_record_factory_allows_extra_correlation_fields() -> None:
    correlation.install_correlation_log_record_factory()
    logger = logging.getLogger("tests.test_observability_correlation")

    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        __file__,
        1,
        "with explicit extra fields",
        (),
        None,
        extra={"correlation_id": "cid-extra-01", "trace_id": "tid-extra-01"},
    )

    assert record.correlation_id == "cid-extra-01"
    assert record.trace_id == "tid-extra-01"


def test_log_record_factory_survives_logrecord_factory_swap() -> None:
    correlation.install_correlation_log_record_factory()
    base_factory = logging.getLogRecordFactory()

    def _custom_factory(*args, **kwargs):
        record = base_factory(*args, **kwargs)
        record.custom_factory_marker = "custom"
        return record

    logging.setLogRecordFactory(_custom_factory)
    token = correlation.set_correlation_id("cid-after-factory-swap")
    try:
        record = _make_record("factory swap")
    finally:
        correlation.reset_correlation_id(token)
        logging.setLogRecordFactory(base_factory)

    assert record.correlation_id == "cid-after-factory-swap"
    assert record.trace_id == "cid-after-factory-swap"
    assert record.custom_factory_marker == "custom"
