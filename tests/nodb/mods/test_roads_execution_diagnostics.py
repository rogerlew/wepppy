"""Security and continuation contracts for Roads execution diagnostics."""

import logging
from types import SimpleNamespace

import pytest

from wepppy.nodb.mods.roads import _unrutted_execution
from wepppy.observability import safe_logging
from wepppy.observability.safe_traceback import SecretSourceProfile, SecretSourceSpec


pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def test_candidate_status_continues_with_bounded_sanitized_warning(monkeypatch, caplog):
    canary = "roads-test-secret-9e84cf98"
    monkeypatch.setenv("ROADS_DIAGNOSTIC_TEST_SECRET", canary)
    profile = SecretSourceProfile(
        "roads-diagnostic-test",
        (SecretSourceSpec("ROADS_DIAGNOSTIC_TEST_SECRET"),),
    )
    monkeypatch.setattr(safe_logging, "_PROFILE", profile)
    segment_id = canary + "-crossing-" + "x" * 300

    class FailingMembership(list):
        def remove(self, value):
            raise ValueError(f"Cannot remove {canary}: " + "y" * 600)

    candidate = {"segment_hillslope_id": segment_id, "topaz_id_hill": 11}
    included = FailingMembership([segment_id])
    excluded = ["previous-exclusion"]
    records = {11: {"segment_ids_included": included, "segment_ids_excluded": excluded}}
    results = SimpleNamespace(outslope_unrutted_candidate_status={segment_id: {"status": "included"}})

    with caplog.at_level(logging.WARNING, logger=_unrutted_execution.__name__):
        _unrutted_execution._move_candidate_to_status(results, candidate, records, "failed_input")

    assert results.outslope_unrutted_candidate_status[segment_id]["status"] == "failed_input"
    assert included == [segment_id]
    assert excluded == ["previous-exclusion", segment_id]
    warning = next(record for record in caplog.records if record.name == _unrutted_execution.__name__)
    message = warning.getMessage()
    assert canary not in message
    assert "[REDACTED]" in message
    assert "candidate=" in message and "error=" in message
    assert len(message) <= 500
    assert warning.exc_info is None


def test_candidate_status_updates_valid_membership_without_warning(caplog):
    segment_id = "roads-seg-000001::h11"
    candidate = {"segment_hillslope_id": segment_id, "topaz_id_hill": 11}
    included = [segment_id, "other-crossing", segment_id]
    excluded = ["previous-exclusion"]
    records = {11: {"segment_ids_included": included, "segment_ids_excluded": excluded}}
    results = SimpleNamespace(outslope_unrutted_candidate_status={segment_id: {"status": "included"}})

    with caplog.at_level(logging.WARNING, logger=_unrutted_execution.__name__):
        _unrutted_execution._move_candidate_to_status(results, candidate, records, "failed_input")

    assert results.outslope_unrutted_candidate_status[segment_id]["status"] == "failed_input"
    assert included == ["other-crossing"]
    assert excluded == ["previous-exclusion", segment_id]
    assert not [record for record in caplog.records if record.name == _unrutted_execution.__name__]
