"""Shared constants for PATH Cost-Effective scenarios and treatments.

Treatment-vector contract (PATH-CE v2): each treatment carries
``label`` / ``scenario`` / ``unit_cost`` / ``quantity`` / ``fixed_cost``.

- ``label`` is load-bearing: prepared-frame columns are keyed
  ``"Sdyd post-treat {label}"`` etc., and data_prep derives labels from
  scenario names (``mulch_{n}_sbs_map`` -> ``{n/30:g} tons/acre``). Labels
  here must match that derivation exactly.
- ``unit_cost`` is $/acre (D4: Jackson's native convention; the UI renders
  English/SI via unitizer). ``quantity`` is the application rate in tons/acre;
  the solver's per-site cost is ``area(ac) * unit_cost * quantity``.
- Defaults are Jackson's report defaults (4e3b4a6).
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, TypedDict

PATH_CE_BASELINE_SCENARIO = "sbs_map"
PATH_CE_REFERENCE_SCENARIO = "undisturbed"

_MULCH_SCENARIO_RE = re.compile(r"^mulch_(\d+)_sbs_map$")


def label_for_scenario(scenario: str) -> Optional[str]:
    """Derive the load-bearing treatment label from a mulch scenario name.

    Mirrors data_prep's ``_scenario_rate_label`` (``mulch_{n}_sbs_map`` ->
    ``{n/30:g} tons/acre``). Returns None for non-mulch scenarios.
    """
    match = _MULCH_SCENARIO_RE.match(str(scenario))
    if not match:
        return None
    return f"{int(match.group(1)) / 30.0:g} tons/acre"


class TreatmentVector(TypedDict):
    label: str
    scenario: str
    unit_cost: float
    quantity: float
    fixed_cost: float


PATH_CE_DEFAULT_TREATMENTS: Tuple[TreatmentVector, ...] = (
    {
        "label": "0.5 tons/acre",
        "scenario": "mulch_15_sbs_map",
        "unit_cost": 2475.0,
        "quantity": 0.5,
        "fixed_cost": 500.0,
    },
    {
        "label": "1 tons/acre",
        "scenario": "mulch_30_sbs_map",
        "unit_cost": 2475.0,
        "quantity": 1.0,
        "fixed_cost": 1000.0,
    },
    {
        "label": "2 tons/acre",
        "scenario": "mulch_60_sbs_map",
        "unit_cost": 2475.0,
        "quantity": 2.0,
        "fixed_cost": 1500.0,
    },
)


def default_treatments() -> List[Dict[str, Any]]:
    """Return a fresh mutable copy of the default treatment vectors."""

    return [dict(t) for t in PATH_CE_DEFAULT_TREATMENTS]


def normalize_treatment(value: Mapping[str, Any]) -> Dict[str, Any]:
    """Coerce a treatment mapping to the vector contract with typed fields."""

    if not isinstance(value, Mapping):
        raise TypeError("treatment must be a mapping")

    def _text(key: str) -> str:
        raw = value.get(key)
        if raw is None or isinstance(raw, float):
            raise ValueError(f"treatment requires a non-empty string {key!r}, got {raw!r}")
        text = str(raw).strip()
        if not text:
            raise ValueError(f"treatment requires a non-empty string {key!r}, got {raw!r}")
        return text

    label = _text("label")
    scenario = _text("scenario")

    # The label is load-bearing (prepared-frame columns are keyed by it, and
    # data_prep derives it from the scenario name) — a mismatched pair would
    # pass validation but silently solve with another treatment's effects.
    derived = label_for_scenario(scenario)
    if derived is None:
        raise ValueError(
            f"unsupported treatment scenario {scenario!r}: the PATH-CE pipeline "
            f"currently derives treatments from 'mulch_<n>_sbs_map' Omni scenarios"
        )
    if label != derived:
        raise ValueError(
            f"treatment label {label!r} does not match scenario {scenario!r} "
            f"(expected {derived!r}; labels key the prepared-frame columns)"
        )

    def _num(key: str, default: float = 0.0) -> float:
        raw = value.get(key, default)
        try:
            out = float(raw if raw is not None else default)
        except (TypeError, ValueError):
            raise ValueError(f"treatment field {key!r} must be numeric, got {raw!r}")
        if not math.isfinite(out):
            raise ValueError(f"treatment field {key!r} must be finite, got {raw!r}")
        if out < 0:
            raise ValueError(f"treatment field {key!r} must be non-negative, got {out!r}")
        return out

    return {
        "label": label,
        "scenario": scenario,
        "unit_cost": _num("unit_cost"),
        "quantity": _num("quantity"),
        "fixed_cost": _num("fixed_cost"),
    }


def solver_vectors(
    treatments: Sequence[Mapping[str, Any]],
) -> Tuple[List[str], List[float], List[float], List[float]]:
    """Unpack treatment vectors into the parallel lists ce_select_sites_flexible takes.

    Returns (labels, unit_costs, quantities, fixed_costs).
    """

    normalized = [normalize_treatment(t) for t in treatments]
    if not normalized:
        raise ValueError("at least one treatment is required")
    labels = [t["label"] for t in normalized]
    if len(set(labels)) != len(labels):
        raise ValueError("treatment labels must be unique")
    return (
        labels,
        [t["unit_cost"] for t in normalized],
        [t["quantity"] for t in normalized],
        [t["fixed_cost"] for t in normalized],
    )


__all__ = [
    "PATH_CE_BASELINE_SCENARIO",
    "PATH_CE_REFERENCE_SCENARIO",
    "PATH_CE_DEFAULT_TREATMENTS",
    "TreatmentVector",
    "default_treatments",
    "label_for_scenario",
    "normalize_treatment",
    "solver_vectors",
]
