"""Omni scenario parsing, execution and controller state tests."""

import logging
from pathlib import Path

import pytest

from tests.nodb.mods._omni_test_support import _noop_lock, omni_module as omni_module


pytestmark = pytest.mark.unit


def test_reset_for_fork_restores_complete_fresh_omni_state(omni_module, monkeypatch):
    fresh = omni_module.Omni.__new__(omni_module.Omni)
    fresh._reset_omni_owned_state()

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = "/runs/destination"
    omni.locked = _noop_lock
    omni._scenarios = [{"type": "thinning"}]
    omni._contrast_names = ["copied"]
    omni._contrast_labels = {"copied": "Copied"}
    omni._contrast_pairs = [{"control": "a", "contrast": "b"}]
    omni._scenario_dependency_tree = {"copied": {}}
    omni._contrast_dependency_tree = {"copied": {}}
    omni._scenario_run_state = [{"scenario": "copied"}]
    omni._use_rq_job_pool_concurrency = False
    omni._scenario_legacy_optional = "remove"
    durable = omni_module.Omni.__new__(omni_module.Omni)
    durable.__dict__.update(omni.__dict__)
    monkeypatch.setattr(omni_module.Omni, "load_detached", lambda wd: durable)

    omni.reset_for_fork()

    for key, value in fresh.__dict__.items():
        assert omni.__dict__[key] == value
    assert "_use_rq_job_pool_concurrency" not in omni.__dict__
    assert "_scenario_legacy_optional" not in omni.__dict__


def test_omni_scenario_parse_roundtrip(omni_module):
    scenario = omni_module.OmniScenario.parse("mulch")
    assert scenario is omni_module.OmniScenario.Mulch
    assert str(scenario) == "mulch"


def test_omni_scenario_parse_rejects_invalid(omni_module):
    with pytest.raises(KeyError):
        omni_module.OmniScenario.parse("unknown_scenario")


def test_omni_scenario_equality_supports_int_and_str(omni_module):
    thinning = omni_module.OmniScenario.Thinning
    assert thinning == thinning.value
    assert thinning == "thinning"
    assert thinning != "mulch"
    assert thinning != 999


def test_run_omni_scenario_prescribed_fire_requires_treatment_key(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    run_dir = tmp_path / "run-omni-prescribed-fire"
    run_dir.mkdir()
    omni.wd = str(run_dir)
    omni.logger = logging.getLogger("tests.omni.prescribed_fire")

    scenario_dir = tmp_path / "_pups" / "omni" / "scenarios" / "prescribed_fire"
    scenario_dir.mkdir(parents=True)

    monkeypatch.setattr(omni_module, "_omni_clone", lambda *args, **kwargs: str(scenario_dir))
    monkeypatch.setattr(omni_module.NoDbBase, "has_sbs", property(lambda self: False), raising=False)

    class DummyDisturbed:
        has_sbs = False

    class DummyLanduse:
        pass

    class DummySoils:
        def build(self, max_workers=None):
            return None

    class DummyTreatments:
        @property
        def treatments_lookup(self):
            return {}

    import wepppy.nodb.core as nodb_core
    import wepppy.nodb.mods.disturbed as disturbed_mod
    import wepppy.nodb.mods.treatments as treatments_mod

    monkeypatch.setattr(disturbed_mod.Disturbed, "getInstance", lambda wd: DummyDisturbed())
    monkeypatch.setattr(nodb_core.Landuse, "getInstance", lambda wd: DummyLanduse())
    monkeypatch.setattr(nodb_core.Soils, "getInstance", lambda wd: DummySoils())
    monkeypatch.setattr(treatments_mod.Treatments, "getInstance", lambda wd: DummyTreatments())

    with pytest.raises(ValueError, match="prescribed_fire"):
        omni.run_omni_scenario({"type": "prescribed_fire"})


def test_run_omni_scenario_undisturbed_allows_base_without_sbs(
    tmp_path,
    monkeypatch,
    omni_module,
):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    run_dir = tmp_path / "_base"
    run_dir.mkdir()
    scenario_dir = run_dir / "_pups" / "omni" / "scenarios" / "undisturbed"
    scenario_dir.mkdir(parents=True)
    (run_dir / "wepp" / "runs").mkdir(parents=True, exist_ok=True)
    (scenario_dir / "wepp" / "runs").mkdir(parents=True, exist_ok=True)
    (scenario_dir / "wepp" / "output").mkdir(parents=True, exist_ok=True)

    omni.wd = str(run_dir)
    omni.logger = logging.getLogger("tests.omni.undisturbed_base")

    monkeypatch.setattr(omni_module, "_omni_clone", lambda *args, **kwargs: str(scenario_dir))
    monkeypatch.setattr(omni_module, "run_wepp_hillslope_interchange", lambda *args, **kwargs: None)
    monkeypatch.setattr(omni_module, "_post_watershed_run_cleanup", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        omni_module.Omni,
        "delete_after_interchange",
        property(lambda self: False),
        raising=False,
    )
    monkeypatch.setattr(omni_module.NoDbBase, "has_sbs", property(lambda self: False), raising=False)

    remove_calls = {"count": 0}

    class DummyDisturbed:
        has_sbs = False

        def remove_sbs(self) -> None:
            remove_calls["count"] += 1

    class DummyLanduse:
        def build(self) -> None:
            return None

        def build_managements(self) -> None:
            return None

    class DummySoils:
        def build(self, max_workers=None) -> None:
            return None

    class DummyWepp:
        def __init__(self, wd: str) -> None:
            self.runs_dir = str(Path(wd) / "wepp" / "runs")
            self.output_dir = str(Path(wd) / "wepp" / "output")
            self.pass_family = "legacy_ascii"
            self.run_wepp_watershed = True

        def prep_hillslopes(self, **kwargs) -> None:
            return None

        def run_hillslopes(self, **kwargs) -> None:
            return None

        def prep_watershed(self) -> None:
            return None

        def run_watershed(self) -> None:
            return None

    class DummyClimate:
        observed_start_year = None
        future_start_year = None

    import wepppy.nodb.core as nodb_core
    import wepppy.nodb.mods.disturbed as disturbed_mod

    monkeypatch.setattr(disturbed_mod.Disturbed, "getInstance", lambda wd: DummyDisturbed())
    monkeypatch.setattr(nodb_core.Landuse, "getInstance", lambda wd: DummyLanduse())
    monkeypatch.setattr(nodb_core.Soils, "getInstance", lambda wd: DummySoils())
    monkeypatch.setattr(nodb_core.Wepp, "getInstance", lambda wd: DummyWepp(wd))
    monkeypatch.setattr(nodb_core.Climate, "getInstance", lambda wd: DummyClimate())

    scenario_wd, scenario_name = omni.run_omni_scenario({"type": "undisturbed"})

    assert Path(scenario_wd) == scenario_dir
    assert scenario_name == "undisturbed"
    assert remove_calls["count"] == 1


def test_run_omni_scenario_undisturbed_requires_sbs_outside_base(
    tmp_path,
    monkeypatch,
    omni_module,
):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    run_dir = tmp_path / "run-omni-undisturbed"
    run_dir.mkdir()
    scenario_dir = run_dir / "_pups" / "omni" / "scenarios" / "undisturbed"
    scenario_dir.mkdir(parents=True)

    omni.wd = str(run_dir)
    omni.logger = logging.getLogger("tests.omni.undisturbed_requires_sbs")

    monkeypatch.setattr(omni_module, "_omni_clone", lambda *args, **kwargs: str(scenario_dir))
    monkeypatch.setattr(omni_module.NoDbBase, "has_sbs", property(lambda self: False), raising=False)

    class DummyDisturbed:
        has_sbs = False

        def remove_sbs(self) -> None:
            return None

    class DummyLanduse:
        def build(self) -> None:
            return None

        def build_managements(self) -> None:
            return None

    class DummySoils:
        def build(self, max_workers=None) -> None:
            return None

    import wepppy.nodb.core as nodb_core
    import wepppy.nodb.mods.disturbed as disturbed_mod

    monkeypatch.setattr(disturbed_mod.Disturbed, "getInstance", lambda wd: DummyDisturbed())
    monkeypatch.setattr(nodb_core.Landuse, "getInstance", lambda wd: DummyLanduse())
    monkeypatch.setattr(nodb_core.Soils, "getInstance", lambda wd: DummySoils())

    with pytest.raises(Exception, match="Undisturbed scenario requires a base scenario with sbs"):
        omni.run_omni_scenario({"type": "undisturbed"})


def test_clear_cache_and_locks_invokes_dependencies(monkeypatch, omni_module):
    calls = []

    def fake_clear_cache(runid, pup_relpath=None):
        calls.append(("cache", runid, pup_relpath))
        return ["entry"]

    def fake_clear_locks(runid, pup_relpath=None):
        calls.append(("locks", runid, pup_relpath))

    test_logger = logging.getLogger("tests.omni.cache_calls")

    monkeypatch.setattr(omni_module, "clear_nodb_file_cache", fake_clear_cache)
    monkeypatch.setattr(omni_module, "clear_locks", fake_clear_locks)
    monkeypatch.setattr(omni_module, "LOGGER", test_logger)

    omni_module._clear_nodb_cache_and_locks("run-123", pup_relpath="scope")

    assert calls == [
        ("cache", "run-123", "scope"),
        ("locks", "run-123", "scope"),
    ]


def test_clear_cache_and_locks_handles_runtime_errors(monkeypatch, omni_module, caplog):
    def fake_clear_cache(runid, pup_relpath=None):
        raise RuntimeError("Redis NoDb cache client is unavailable")

    def fake_clear_locks(runid, pup_relpath=None):
        raise RuntimeError("Redis lock client is unavailable")

    test_logger = logging.getLogger("tests.omni.cache_errors")

    monkeypatch.setattr(omni_module, "clear_nodb_file_cache", fake_clear_cache)
    monkeypatch.setattr(omni_module, "clear_locks", fake_clear_locks)
    monkeypatch.setattr(omni_module, "LOGGER", test_logger)

    with caplog.at_level(logging.DEBUG, logger=test_logger.name):
        omni_module._clear_nodb_cache_and_locks("run-456", pup_relpath="scope")

    assert "Redis NoDb cache unavailable" in caplog.text
    assert "Redis lock client unavailable" in caplog.text


def test_run_omni_scenarios_delegates_to_run_orchestration_service(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    captured: dict[str, object] = {}

    def _fake_run(instance):
        captured["instance"] = instance

    monkeypatch.setattr(omni_module._OMNI_RUN_ORCHESTRATION_SERVICE, "run_omni_scenarios", _fake_run)

    omni.run_omni_scenarios()

    assert captured["instance"] is omni


def test_run_omni_scenarios_raises_runtime_error_when_no_scenarios(tmp_path, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.run_scenarios.empty")
    omni._scenarios = []

    with pytest.raises(RuntimeError, match="No scenarios to run"):
        omni.run_omni_scenarios()
