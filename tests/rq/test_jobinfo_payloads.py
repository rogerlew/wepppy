import pytest

from wepppy.rq.jobinfo_payloads import extract_job_ids, normalize_job_id_inputs


pytestmark = pytest.mark.unit


def test_normalize_job_id_inputs_none_returns_empty() -> None:
    assert normalize_job_id_inputs(None) == []


def test_normalize_job_id_inputs_strips_and_keeps_single_value() -> None:
    assert normalize_job_id_inputs(" abc ") == ["abc"]


def test_normalize_job_id_inputs_splits_commas_in_order() -> None:
    assert normalize_job_id_inputs("a,b, c") == ["a", "b", "c"]


def test_normalize_job_id_inputs_dedupes_and_trims_lists() -> None:
    assert normalize_job_id_inputs(["a", "a", " b "]) == ["a", "b"]


def test_normalize_job_id_inputs_flattens_dict_values() -> None:
    payload = {"x": "a", "y": ["b", "c"]}
    assert normalize_job_id_inputs(payload) == ["a", "b", "c"]


def test_normalize_job_id_inputs_coerces_non_string_values() -> None:
    assert normalize_job_id_inputs(42) == ["42"]


def test_extract_job_ids_prefers_job_ids_key() -> None:
    payload = {"job_ids": ["a", "b"], "x": "c"}
    assert extract_job_ids(payload=payload) == ["a", "b"]


def test_extract_job_ids_uses_payload_values_when_no_ids_key() -> None:
    payload = {"x": "a", "y": ["b", "c"]}
    assert extract_job_ids(payload=payload) == ["a", "b", "c"]


def test_extract_job_ids_accepts_payload_string() -> None:
    assert extract_job_ids(payload=" abc ") == ["abc"]


@pytest.mark.parametrize(
    ("query_args", "expected"),
    [
        ({"job_id": "job-1"}, ["job-1"]),
        ({"job_ids": ["job-2", "job-3"]}, ["job-2", "job-3"]),
    ],
)
def test_extract_job_ids_uses_query_args_when_payload_empty(query_args, expected) -> None:
    assert extract_job_ids(payload={}, query_args=query_args) == expected


def test_extract_job_ids_supports_list_query_args() -> None:
    query_args = [("job_id", "a"), ("job_id", "b")]
    assert extract_job_ids(payload=None, query_args=query_args) == ["a", "b"]
