"""Maintenance polling must not decode serialized RQ job payloads."""
from datetime import datetime, timezone

import pytest

from wepppy.rq import job_info
from wepppy.rq.query_catalog_disclosure import (
    DESCRIPTION, PREFIX, get_query_catalog_job_details,
)

pytestmark = pytest.mark.unit
IDENTIFIER = PREFIX + "00000000-0000-4000-8000-000000000001"
CANARY = "/private/project/secret-stacktrace"


class HashConnection:
    def __init__(self, fields=None):
        self.fields = fields
        self.requested = []

    def hmget(self, key, *fields):
        assert key == f"rq:job:{IDENTIFIER}"
        self.requested.extend(fields)
        return [self.fields.get(field) if self.fields else None for field in fields]

    def exists(self, key):
        return self.fields is not None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def connection(monkeypatch):
    conn = HashConnection({
        "status": b"finished", "started_at": b"2026-10-23T20:00:00Z",
        "ended_at": b"2026-10-23T20:01:00Z",
        "data": b"not a pickle", "meta": CANARY, "result": CANARY,
        "description": CANARY, "exc_info": CANARY,
    })
    monkeypatch.setattr(job_info.redis, "Redis", lambda **kwargs: conn)
    monkeypatch.setattr(job_info.Job, "fetch", lambda *args, **kwargs: pytest.fail("Job.fetch must not run"))
    return conn


def test_single_info_never_fetches_or_deserializes(connection):
    details = job_info.get_wepppy_rq_job_info(IDENTIFIER)
    assert details == {
        "job_id": IDENTIFIER, "status": "finished", "description": DESCRIPTION,
        "started_at": "2026-10-23 20:00:00+00:00", "ended_at": "2026-10-23 20:01:00+00:00",
        "runid": None, "result": None, "exc_info": None, "auth_actor": None, "children": {},
    }
    assert connection.requested == ["status", "started_at", "ended_at"]
    assert CANARY not in str(details)


def test_batch_info_never_fetches_or_deserializes(connection):
    details = job_info.get_wepppy_rq_jobs_info([IDENTIFIER, IDENTIFIER])
    assert list(details) == [IDENTIFIER]
    assert details[IDENTIFIER]["status"] == "finished"
    assert CANARY not in str(details)


def test_jobstatus_keeps_summary_shape(connection):
    details = job_info.get_wepppy_rq_job_status(IDENTIFIER)
    assert set(details) == {"job_id", "runid", "status", "started_at", "ended_at", "progress"}
    assert details["progress"]["percent"] == 100.0
    assert details["status"] == "finished"


@pytest.mark.parametrize("state", [b"failed", b"stopped", b"canceled", b"abandoned", CANARY.encode(), None])
def test_failed_and_malformed_status_never_leaks(connection, state):
    connection.fields["status"] = state
    details = job_info.get_wepppy_rq_job_info(IDENTIFIER)
    assert details["error"]["code"] == "query_catalog_refresh_failed"
    assert details["exc_info"] is None
    assert CANARY not in str(details)
    summary = job_info.get_wepppy_rq_job_status(IDENTIFIER)
    assert summary["error"]["code"] == "query_catalog_refresh_failed"
    assert "result" not in summary


def test_malformed_timestamp_fails_closed(connection):
    connection.fields["started_at"] = CANARY.encode()
    details = get_query_catalog_job_details(IDENTIFIER, connection)
    assert details["status"] == "failed"
    assert details["started_at"] is None
    assert CANARY not in str(details)


def test_unknown_or_expired_id(connection):
    connection.fields = None
    assert job_info.get_wepppy_rq_job_info(IDENTIFIER) == {"job_id": IDENTIFIER, "status": "not_found"}
    assert job_info.get_wepppy_rq_job_status(IDENTIFIER) == {"job_id": IDENTIFIER, "status": "not_found"}


def test_corrupt_retained_hash_is_failure_not_missing(connection):
    connection.fields = {"data": CANARY}
    assert get_query_catalog_job_details(IDENTIFIER, connection)["status"] == "failed"


def test_connection_failure_is_sanitized(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError(CANARY)
    monkeypatch.setattr(job_info.redis, "Redis", fail)
    details = job_info.get_wepppy_rq_job_info(IDENTIFIER)
    assert details["error"]["code"] == "query_catalog_refresh_failed"
    assert CANARY not in str(details)


def test_recursive_child_never_fetches_serialized_payload(connection):
    class Parent:
        id = "ordinary-parent"
        meta = {"jobs:0": IDENTIFIER}
        args = ()
        result = None
        started_at = None
        ended_at = None
        description = "ordinary parent"
        exc_info = None
        def get_status(self):
            return "finished"

    details = job_info.recursive_get_job_details(Parent(), connection, datetime.now(timezone.utc))
    child = details["children"]["0"][0]
    assert child["description"] == DESCRIPTION
    assert child["status"] == "finished"
    assert CANARY not in str(details)
