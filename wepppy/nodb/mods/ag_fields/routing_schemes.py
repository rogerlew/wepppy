"""Canonical identifiers and filesystem slugs for AgFields routing schemes."""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType


class AgFieldsRoutingScheme(str, Enum):
    """One independently runnable AgFields watershed routing scheme."""

    CONCEPT_1 = "concept_1"
    CONCEPT_2 = "concept_2"
    HYBRID = "hybrid"


DEFAULT_ROUTING_SCHEME = AgFieldsRoutingScheme.CONCEPT_2
RUN_ALL_REQUEST = "all"
RUN_ALL_ORDER = (
    AgFieldsRoutingScheme.CONCEPT_1,
    AgFieldsRoutingScheme.CONCEPT_2,
    AgFieldsRoutingScheme.HYBRID,
)
ROUTING_SCHEME_SLUGS = MappingProxyType(
    {
        AgFieldsRoutingScheme.CONCEPT_1: "concept-1",
        AgFieldsRoutingScheme.CONCEPT_2: "concept-2",
        AgFieldsRoutingScheme.HYBRID: "hybrid",
    }
)
MAX_WATERSHED_WORKERS = 16


def parse_routing_scheme(value: str | None) -> AgFieldsRoutingScheme:
    """Parse an exact identifier, defaulting omitted or empty input to Concept 2."""
    if value is None or value == "":
        return DEFAULT_ROUTING_SCHEME
    try:
        return AgFieldsRoutingScheme(value)
    except ValueError as exc:
        raise ValueError(f"Unsupported AgFields routing scheme: {value!r}.") from exc


def expand_routing_scheme_request(value: str | None) -> tuple[AgFieldsRoutingScheme, ...]:
    """Expand one exact request identifier into its serial execution order."""
    if value == RUN_ALL_REQUEST:
        return RUN_ALL_ORDER
    return (parse_routing_scheme(value),)


def routing_scheme_slug(scheme: AgFieldsRoutingScheme) -> str:
    """Return the fixed filesystem slug for a parsed routing scheme."""
    return ROUTING_SCHEME_SLUGS[scheme]


def validate_watershed_max_workers(value: object | None) -> int | None:
    """Validate the explicit integration worker bound without silently clamping it."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("max_workers must be an integer when provided.")
    workers = value
    if not 1 <= workers <= MAX_WATERSHED_WORKERS:
        raise ValueError(
            f"max_workers must be between 1 and {MAX_WATERSHED_WORKERS} when provided."
        )
    return workers


__all__ = [
    "AgFieldsRoutingScheme",
    "DEFAULT_ROUTING_SCHEME",
    "MAX_WATERSHED_WORKERS",
    "ROUTING_SCHEME_SLUGS",
    "RUN_ALL_ORDER",
    "RUN_ALL_REQUEST",
    "expand_routing_scheme_request",
    "parse_routing_scheme",
    "routing_scheme_slug",
    "validate_watershed_max_workers",
]
