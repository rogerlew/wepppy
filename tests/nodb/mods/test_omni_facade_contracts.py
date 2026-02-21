from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path

import pytest

import wepppy.nodb.mods.omni.omni as omni_module

pytestmark = pytest.mark.unit


@contextmanager
def _noop_lock():
    yield


def _new_detached_omni(tmp_path: Path, logger_name: str) -> omni_module.Omni:
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger(logger_name)
    omni._logger = omni.logger
    omni.locked = _noop_lock
    return omni


def test_parse_inputs_normalizes_scenarios_pairs_and_booleans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = _new_detached_omni(tmp_path, "tests.omni.facade.parse_inputs")
    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    payload = {
        "omni_control_scenario": omni_module.OmniScenario.UniformLow,
        "omni_contrast_scenario": 5,
        "omni_contrast_pairs": [
            {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
            {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
            {"control_scenario": "", "contrast_scenario": "mulch"},
        ],
        "omni_contrast_output_chan_out": "true",
        "omni_contrast_output_tcr_out": "0",
        "omni_contrast_output_chnwb": "bad-token",
        "omni_contrast_output_ebe_pw0": "",
    }

    omni.parse_inputs(payload)

    assert omni.control_scenario == "uniform_low"
    assert omni.contrast_scenario == "mulch"
    assert omni.contrast_pairs == [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
    ]
    assert omni.contrast_output_chan_out is True
    assert omni.contrast_output_tcr_out is False
    assert omni.contrast_output_chnwb is False
    assert omni.contrast_output_ebe_pw0 is True


def test_parse_inputs_delegates_to_input_parser_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = _new_detached_omni(tmp_path, "tests.omni.facade.parse_inputs.delegate")
    captured: dict[str, object] = {}

    def _fake_parse(instance: omni_module.Omni, kwds: dict[str, object]) -> None:
        captured["instance"] = instance
        captured["kwds"] = kwds

    monkeypatch.setattr(omni_module._OMNI_INPUT_PARSER, "parse_inputs", _fake_parse)
    payload = {"omni_control_scenario": "uniform_low"}

    omni.parse_inputs(payload)

    assert captured == {"instance": omni, "kwds": payload}


def test_parse_scenarios_resets_existing_state_and_keeps_expected_shapes(tmp_path: Path) -> None:
    omni = _new_detached_omni(tmp_path, "tests.omni.facade.parse_scenarios")
    omni._scenarios = [{"type": "stale"}]

    omni.parse_scenarios(
        [
            (omni_module.OmniScenario.UniformHigh, {"type": "uniform_high"}),
            (
                omni_module.OmniScenario.Thinning,
                {"type": "thinning", "canopy_cover": "70", "ground_cover": "40"},
            ),
            (
                omni_module.OmniScenario.Mulch,
                {
                    "type": "mulch",
                    "ground_cover_increase": "30",
                    "base_scenario": "uniform_low",
                },
            ),
        ]
    )

    assert omni.scenarios == [
        {"type": "uniform_high"},
        {"type": "thinning", "canopy_cover": "70", "ground_cover": "40"},
        {
            "type": "mulch",
            "ground_cover_increase": "30",
            "base_scenario": "uniform_low",
        },
    ]


def test_parse_scenarios_delegates_to_input_parser_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = _new_detached_omni(tmp_path, "tests.omni.facade.parse_scenarios.delegate")
    captured: dict[str, object] = {}

    def _fake_parse(instance: omni_module.Omni, parsed_inputs) -> None:
        captured["instance"] = instance
        captured["parsed_inputs"] = list(parsed_inputs)

    monkeypatch.setattr(omni_module._OMNI_INPUT_PARSER, "parse_scenarios", _fake_parse)
    payload = [(omni_module.OmniScenario.UniformLow, {"type": "uniform_low"})]

    omni.parse_scenarios(payload)

    assert captured["instance"] is omni
    assert captured["parsed_inputs"] == payload


def test_parse_scenarios_rejects_missing_required_fields(tmp_path: Path) -> None:
    omni = _new_detached_omni(tmp_path, "tests.omni.facade.parse_scenarios.errors")

    with pytest.raises(ValueError, match="Thinning requires canopy_cover and ground_cover"):
        omni.parse_scenarios([(omni_module.OmniScenario.Thinning, {"type": "thinning"})])

    with pytest.raises(ValueError, match="Mulching requires ground_cover_increase and base_scenario"):
        omni.parse_scenarios([(omni_module.OmniScenario.Mulch, {"type": "mulch"})])


def test_delete_scenarios_prunes_state_and_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = _new_detached_omni(tmp_path, "tests.omni.facade.delete")
    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    omni._scenarios = [
        {"type": "uniform_low"},
        {"type": "mulch", "ground_cover_increase": "30", "base_scenario": "uniform_low"},
    ]
    omni._scenario_dependency_tree = {
        "uniform_low": {"sha1": "a"},
        "mulch_30_uniform_low": {"sha1": "b"},
    }
    omni._scenario_run_state = [
        {"scenario": "uniform_low", "status": "executed"},
        {"scenario": "mulch_30_uniform_low", "status": "executed"},
    ]

    scenario_dir = tmp_path / "_pups" / "omni" / "scenarios" / "uniform_low"
    scenario_dir.mkdir(parents=True)
    summary_path = tmp_path / "omni" / "scenarios.out.parquet"
    summary_path.parent.mkdir(parents=True)
    summary_path.write_text("x", encoding="ascii")

    cache_calls: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        omni_module,
        "_clear_nodb_cache_and_locks",
        lambda runid, pup_relpath=None: cache_calls.append((runid, pup_relpath)),
    )
    refreshed: list[str] = []
    monkeypatch.setattr(omni, "_refresh_catalog", lambda rel_path=None: refreshed.append(str(rel_path)))

    result = omni.delete_scenarios(["uniform_low", "missing", "uniform_low"])

    assert result == {"removed": ["uniform_low"], "missing": ["missing", "missing"]}
    assert [entry["type"] for entry in omni.scenarios] == ["mulch"]
    assert omni.scenario_dependency_tree == {"mulch_30_uniform_low": {"sha1": "b"}}
    assert omni.scenario_run_state == [{"scenario": "mulch_30_uniform_low", "status": "executed"}]
    assert not scenario_dir.exists()
    assert not summary_path.exists()
    assert cache_calls and isinstance(cache_calls[0][0], str)
    assert refreshed == [omni_module.OMNI_REL_DIR]


def test_delete_scenarios_propagates_non_oserror_cleanup_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = _new_detached_omni(tmp_path, "tests.omni.facade.delete.non_oserror")
    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    omni._scenarios = [{"type": "uniform_low"}]
    omni._scenario_dependency_tree = {"uniform_low": {"sha1": "a"}}
    omni._scenario_run_state = [{"scenario": "uniform_low", "status": "executed"}]

    scenario_dir = tmp_path / "_pups" / "omni" / "scenarios" / "uniform_low"
    scenario_dir.mkdir(parents=True)

    monkeypatch.setattr(
        omni_module.shutil,
        "rmtree",
        lambda path: (_ for _ in ()).throw(ValueError("simulated-rmtree-error")),
    )

    with pytest.raises(ValueError, match="simulated-rmtree-error"):
        omni.delete_scenarios(["uniform_low"])


def test_scenario_run_markers_always_include_base_scenario(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = _new_detached_omni(tmp_path, "tests.omni.facade.run_markers")
    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    omni._scenarios = [{"type": "uniform_low"}]

    scenario_marker = (
        tmp_path
        / omni_module.OMNI_REL_DIR
        / "scenarios"
        / "uniform_low"
        / "wepp"
        / "output"
        / "interchange"
        / "README.md"
    )
    scenario_marker.parent.mkdir(parents=True)
    scenario_marker.write_text("ok", encoding="ascii")

    markers = omni.scenario_run_markers()

    assert markers["uniform_low"] is True
    assert markers[str(omni_module.OmniScenario.Undisturbed)] is False


def test_run_omni_scenario_delegates_to_run_orchestration_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = _new_detached_omni(tmp_path, "tests.omni.facade.run_omni_scenario.delegate")
    captured: dict[str, object] = {}
    payload = {"type": "uniform_low"}
    expected = (str(tmp_path / "_pups" / "omni" / "scenarios" / "uniform_low"), "uniform_low")

    def _fake_run(instance: omni_module.Omni, scenario_def: dict[str, object]) -> tuple[str, str]:
        captured["instance"] = instance
        captured["scenario_def"] = scenario_def
        return expected

    monkeypatch.setattr(omni_module._OMNI_RUN_ORCHESTRATION_SERVICE, "run_omni_scenario", _fake_run)

    result = omni.run_omni_scenario(payload)

    assert captured["instance"] is omni
    assert captured["scenario_def"] is payload
    assert result == expected


def test_run_omni_scenario_raises_type_error_for_non_enum_parse_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = _new_detached_omni(tmp_path, "tests.omni.facade.run_omni_scenario.invalid")

    monkeypatch.setattr(
        omni_module.OmniScenario,
        "parse",
        staticmethod(lambda value: object()),
    )

    with pytest.raises(TypeError, match="Invalid omni scenario type"):
        omni.run_omni_scenario({"type": "uniform_low"})


def test_run_completion_properties_and_output_options(tmp_path: Path) -> None:
    omni = _new_detached_omni(tmp_path, "tests.omni.facade.flags")
    omni._scenarios = [{"type": "uniform_low"}]
    omni._contrast_output_chan_out = 1
    omni._contrast_output_tcr_out = 0
    omni._contrast_output_chnwb = False
    omni._contrast_output_soil_pw0 = "yes"
    omni._contrast_output_plot_pw0 = ""
    omni._contrast_output_ebe_pw0 = None

    scenario_output = (
        tmp_path
        / omni_module.OMNI_REL_DIR
        / "scenarios"
        / "uniform_low"
        / "wepp"
        / "output"
        / "interchange"
        / "loss_pw0.out.parquet"
    )
    scenario_output.parent.mkdir(parents=True)
    scenario_output.write_text("x", encoding="ascii")

    contrast_output = (
        tmp_path
        / omni_module.OMNI_REL_DIR
        / "contrasts"
        / "1"
        / "wepp"
        / "output"
        / "interchange"
        / "loss_pw0.out.parquet"
    )
    contrast_output.parent.mkdir(parents=True)
    contrast_output.write_text("x", encoding="ascii")

    assert omni.has_ran_scenarios is True
    assert omni.has_ran_contrasts is True
    assert omni.contrast_output_options() == {
        "chan_out": True,
        "tcr_out": False,
        "chnwb": False,
        "soil_pw0": True,
        "plot_pw0": False,
        "ebe_pw0": True,
    }


def test_contrast_batch_size_defaults_and_invalid_values(tmp_path: Path) -> None:
    omni = _new_detached_omni(tmp_path, "tests.omni.facade.batch_size")
    omni.config_get_int = lambda section, key, default: 0

    omni._contrast_batch_size = None
    assert omni.contrast_batch_size == 1

    omni._contrast_batch_size = "abc"
    assert omni.contrast_batch_size == 6

    omni._contrast_batch_size = 9
    assert omni.contrast_batch_size == 9
