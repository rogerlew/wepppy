"""Shared constants for PATH Cost-Effective scenarios and treatments."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, TypedDict

PATH_CE_BASELINE_SCENARIO = "sbs_map"
PATH_CE_REFERENCE_SCENARIO = "undisturbed"


class _MulchPreset(TypedDict):
    key: str
    label: str
    ground_cover_increase: int


PATH_CE_MULCH_PRESETS: Iterable[_MulchPreset] = (
    {
        "key": "mulch_15_sbs_map",
        "label": "Mulch 0.5 tons/acre (15% cover)",
        "ground_cover_increase": 15,
    },
    {
        "key": "mulch_30_sbs_map",
        "label": "Mulch 1.0 tons/acre (30% cover)",
        "ground_cover_increase": 30,
    },
    {
        "key": "mulch_60_sbs_map",
        "label": "Mulch 2.0 tons/acre (60% cover)",
        "ground_cover_increase": 60,
    },
)


def default_mulch_costs() -> Dict[str, float]:
    """Return a fresh mulch cost mapping keyed by scenario name."""

    return {preset["key"]: 0.0 for preset in PATH_CE_MULCH_PRESETS}


def build_treatment_options(costs: Mapping[str, Any]) -> List[Dict[str, float]]:
    """Build solver-facing treatment option payloads from a cost map."""

    options: List[Dict[str, float]] = []
    for preset in PATH_CE_MULCH_PRESETS:
        key = preset["key"]
        raw_cost = costs.get(key, 0.0) if isinstance(costs, Mapping) else 0.0
        try:
            unit_cost = float(raw_cost or 0.0)
        except (TypeError, ValueError):
            unit_cost = 0.0
        options.append(
            {
                "label": preset["label"],
                "scenario": key,
                "quantity": 1.0,
                "unit_cost": unit_cost,
                "fixed_cost": 0.0,
            }
        )
    return options


def build_path_omni_scenarios(base_scenario: str) -> List[Dict[str, Any]]:
    """Return the deterministic Omni scenario defs required for PATH."""

    scenarios: List[Dict[str, Any]] = [
        {"type": PATH_CE_REFERENCE_SCENARIO},
    ]
    for preset in PATH_CE_MULCH_PRESETS:
        scenarios.append(
            {
                "type": "mulch",
                "ground_cover_increase": preset["ground_cover_increase"],
                "base_scenario": base_scenario,
            }
        )
    return scenarios


__all__ = [
    "PATH_CE_BASELINE_SCENARIO",
    "PATH_CE_REFERENCE_SCENARIO",
    "PATH_CE_MULCH_PRESETS",
    "default_mulch_costs",
    "build_treatment_options",
    "build_path_omni_scenarios",
]
