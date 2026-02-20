from __future__ import annotations

from contextlib import contextmanager

import pytest

from wepppy.nodb.mods.omni.omni import OmniScenario
from wepppy.nodb.mods.omni.omni_input_parser import OmniInputParsingService

pytestmark = pytest.mark.unit


class _DummyOmni:
    def __init__(self) -> None:
        self.events: list[str] = []

        self._scenarios = [{"type": "stale"}]
        self._control_scenario = None
        self._contrast_scenario = None
        self._contrast_pairs = []
        self._contrast_output_chan_out = False
        self._contrast_output_tcr_out = False
        self._contrast_output_chnwb = False
        self._contrast_output_soil_pw0 = False
        self._contrast_output_plot_pw0 = False
        self._contrast_output_ebe_pw0 = True

    @contextmanager
    def locked(self):
        self.events.append("lock-enter")
        yield
        self.events.append("lock-exit")

    def _normalize_scenario_key(self, value):
        token = str(value)
        if token in {"None", "none", ""}:
            return str(OmniScenario.Undisturbed)
        return token


def test_parse_inputs_sets_contract_fields_and_normalizes_booleans() -> None:
    parser = OmniInputParsingService()
    omni = _DummyOmni()

    parser.parse_inputs(
        omni,
        {
            "omni_control_scenario": OmniScenario.UniformModerate,
            "omni_contrast_scenario": "mulch",
            "omni_contrast_pairs": [
                {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
                {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
            ],
            "omni_contrast_output_chan_out": "true",
            "omni_contrast_output_tcr_out": "0",
            "omni_contrast_output_chnwb": "unknown",
            "omni_contrast_output_soil_pw0": 1,
            "omni_contrast_output_plot_pw0": 0,
            "omni_contrast_output_ebe_pw0": "",
        },
    )

    assert omni._control_scenario == "uniform_moderate"
    assert omni._contrast_scenario == "mulch"
    assert omni._contrast_pairs == [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
    ]
    assert omni._contrast_output_chan_out is True
    assert omni._contrast_output_tcr_out is False
    assert omni._contrast_output_chnwb is False
    assert omni._contrast_output_soil_pw0 is True
    assert omni._contrast_output_plot_pw0 is False
    assert omni._contrast_output_ebe_pw0 is True


def test_parse_inputs_keeps_mutations_inside_single_lock_scope() -> None:
    parser = OmniInputParsingService()
    omni = _DummyOmni()

    parser.parse_inputs(omni, {"omni_control_scenario": "uniform_low"})

    assert omni.events == ["lock-enter", "lock-exit"]


def test_parse_scenarios_resets_existing_and_requires_mode_specific_fields() -> None:
    parser = OmniInputParsingService()
    omni = _DummyOmni()

    parser.parse_scenarios(
        omni,
        [
            ("uniform_low", {"type": "uniform_low"}),
            (
                "thinning",
                {"type": "thinning", "canopy_cover": "70", "ground_cover": "40"},
            ),
            (
                "mulch",
                {
                    "type": "mulch",
                    "ground_cover_increase": "30",
                    "base_scenario": "uniform_low",
                },
            ),
        ],
    )

    assert omni._scenarios == [
        {"type": "uniform_low"},
        {"type": "thinning", "canopy_cover": "70", "ground_cover": "40"},
        {
            "type": "mulch",
            "ground_cover_increase": "30",
            "base_scenario": "uniform_low",
        },
    ]

    with pytest.raises(ValueError, match="Thinning requires canopy_cover and ground_cover"):
        parser.parse_scenarios(omni, [("thinning", {"type": "thinning"})])


def test_normalize_contrast_pairs_coerces_and_deduplicates_entries() -> None:
    parser = OmniInputParsingService()
    omni = _DummyOmni()

    pairs = parser.normalize_contrast_pairs(
        omni,
        [
            {"control_scenario": "None", "contrast_scenario": "mulch"},
            {"control_scenario": "None", "contrast_scenario": "mulch"},
            {"control_scenario": "", "contrast_scenario": "mulch"},
            {"control_scenario": "uniform_low", "contrast_scenario": "thinning"},
        ],
    )

    assert pairs == [
        {
            "control_scenario": str(OmniScenario.Undisturbed),
            "contrast_scenario": "mulch",
        },
        {
            "control_scenario": "uniform_low",
            "contrast_scenario": "thinning",
        },
    ]


def test_normalize_scenario_value_handles_enum_and_integer_edges() -> None:
    parser = OmniInputParsingService()

    assert parser._normalize_scenario_value(OmniScenario.UniformLow) == "uniform_low"
    assert parser._normalize_scenario_value(OmniScenario.Mulch.value) == "mulch"
    assert parser._normalize_scenario_value(999) == "999"
    assert parser._normalize_scenario_value(None) is None


def test_normalize_bool_returns_none_for_invalid_tokens() -> None:
    parser = OmniInputParsingService()

    assert parser._normalize_bool("definitely-not-bool") is None
    assert parser._normalize_bool("TRUE") is True
    assert parser._normalize_bool("off") is False
