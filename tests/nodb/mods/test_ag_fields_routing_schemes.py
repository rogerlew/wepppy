from __future__ import annotations

import pytest

from wepppy.nodb.mods.ag_fields.routing_schemes import (
    AgFieldsRoutingScheme,
    MAX_WATERSHED_WORKERS,
    RUN_ALL_ORDER,
    expand_routing_scheme_request,
    is_watershed_scheme_active_status,
    parse_routing_scheme,
    routing_scheme_slug,
    validate_watershed_max_workers,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, AgFieldsRoutingScheme.CONCEPT_2),
        ("", AgFieldsRoutingScheme.CONCEPT_2),
        ("concept_1", AgFieldsRoutingScheme.CONCEPT_1),
        ("concept_2", AgFieldsRoutingScheme.CONCEPT_2),
        ("hybrid", AgFieldsRoutingScheme.HYBRID),
    ],
)
def test_parse_routing_scheme_uses_exact_identifiers(
    value: str | None,
    expected: AgFieldsRoutingScheme,
) -> None:
    assert parse_routing_scheme(value) is expected


@pytest.mark.parametrize("value", ["all", "concept-1", "Concept_1", " concept_2 "])
def test_parse_routing_scheme_rejects_request_only_or_inexact_values(value: str) -> None:
    with pytest.raises(ValueError, match="Unsupported AgFields routing scheme"):
        parse_routing_scheme(value)


def test_expand_run_all_uses_frozen_serial_order() -> None:
    assert expand_routing_scheme_request("all") == RUN_ALL_ORDER
    assert RUN_ALL_ORDER == (
        AgFieldsRoutingScheme.CONCEPT_1,
        AgFieldsRoutingScheme.CONCEPT_2,
        AgFieldsRoutingScheme.HYBRID,
    )


def test_scheme_slugs_are_fixed_and_not_request_input() -> None:
    assert routing_scheme_slug(AgFieldsRoutingScheme.CONCEPT_1) == "concept-1"
    assert routing_scheme_slug(AgFieldsRoutingScheme.CONCEPT_2) == "concept-2"
    assert routing_scheme_slug(AgFieldsRoutingScheme.HYBRID) == "hybrid"


def test_watershed_worker_bound_is_explicit_and_not_silently_clamped() -> None:
    assert validate_watershed_max_workers(None) is None
    assert validate_watershed_max_workers(1) == 1
    assert validate_watershed_max_workers(MAX_WATERSHED_WORKERS) == 16
    for invalid in (True, 1.5, "2"):
        with pytest.raises(ValueError, match="must be an integer"):
            validate_watershed_max_workers(invalid)
    with pytest.raises(ValueError, match="between 1 and 16"):
        validate_watershed_max_workers(17)


@pytest.mark.parametrize("status", ["running", "running:preflight", "clearing"])
def test_active_scheme_statuses_own_the_artifact_root(status: str) -> None:
    assert is_watershed_scheme_active_status(status) is True


@pytest.mark.parametrize("status", ["not_run", "completed", "failed"])
def test_terminal_scheme_statuses_do_not_own_the_artifact_root(status: str) -> None:
    assert is_watershed_scheme_active_status(status) is False
