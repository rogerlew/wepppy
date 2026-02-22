from __future__ import annotations

import hashlib
import logging
import sys
import types
from contextlib import contextmanager
from enum import IntEnum
from pathlib import Path

import pytest

from wepppy.nodb.base import NoDbAlreadyLockedError
from wepppy.nodb.mods.omni.omni_run_orchestration_service import OmniRunOrchestrationService

pytestmark = pytest.mark.unit


def _install_omni_module_stub(
    monkeypatch: pytest.MonkeyPatch,
    *,
    run_contrast,
) -> None:
    module = types.ModuleType("wepppy.nodb.mods.omni.omni")

    class OmniScenario(IntEnum):
        UniformLow = 1
        Thinning = 4
        Mulch = 5
        Undisturbed = 9
        PrescribedFire = 10

        @staticmethod
        def parse(value):
            lookup = {
                "uniform_low": OmniScenario.UniformLow,
                "thinning": OmniScenario.Thinning,
                "mulch": OmniScenario.Mulch,
                "undisturbed": OmniScenario.Undisturbed,
                "prescribed_fire": OmniScenario.PrescribedFire,
            }
            return lookup[str(value)]

    def _hash_file_sha1(path: str | None):
        if not path:
            return None
        p = Path(path)
        if not p.exists():
            return None
        h = hashlib.sha1()
        h.update(p.read_bytes())
        return h.hexdigest()

    def _scenario_name_from_scenario_definition(scenario_def):
        scenario_type = str(scenario_def.get("type"))
        if scenario_type == "mulch":
            inc = scenario_def.get("ground_cover_increase")
            base = scenario_def.get("base_scenario")
            return f"mulch_{inc}_{base}".replace("%", "")
        return scenario_type

    module.OMNI_REL_DIR = "_pups/omni"
    module.OmniScenario = OmniScenario
    module.ScenarioDependency = dict
    module._hash_file_sha1 = _hash_file_sha1
    module._scenario_name_from_scenario_definition = _scenario_name_from_scenario_definition
    module._run_contrast = run_contrast

    monkeypatch.setitem(sys.modules, "wepppy.nodb.mods.omni.omni", module)


class _ScenarioOmniStub:
    def __init__(self, wd: Path) -> None:
        self.wd = str(wd)
        self.logger = logging.getLogger("tests.omni.run_orchestration.scenarios")
        self.base_scenario = "undisturbed"
        self.scenarios = [
            {"type": "uniform_low"},
            {
                "type": "mulch",
                "ground_cover_increase": "30",
                "base_scenario": "uniform_low",
            },
        ]
        self.scenario_dependency_tree = {}
        self.scenario_run_state = []
        self.run_calls: list[str] = []
        self.post_calls: list[str] = []
        self.compiles = {"hillslope": 0, "channel": 0, "report": 0}

    def _scenario_dependency_target(self, _scenario_enum, scenario_def):
        if scenario_def.get("type") == "mulch":
            return scenario_def.get("base_scenario")
        return str(self.base_scenario)

    def _loss_pw0_path_for_scenario(self, _dependency_target):
        return str(Path(self.wd) / "dep" / "loss_pw0.out.parquet")

    def _scenario_signature(self, scenario_def):
        return f"sig:{scenario_def.get('type')}"

    def _year_set_for_scenario(self, _scenario_name):
        return {2020}

    def _normalize_scenario_key(self, name):
        return str(name)

    def run_omni_scenario(self, scenario_def):
        scenario_name = scenario_def["type"]
        if scenario_name == "mulch":
            scenario_name = "mulch_30_uniform_low"
        self.run_calls.append(scenario_name)
        return str(Path(self.wd) / "_pups" / "omni" / "scenarios" / scenario_name), scenario_name

    def _post_omni_run(self, omni_wd, scenario_name):
        self.post_calls.append(f"{omni_wd}:{scenario_name}")

    def compile_hillslope_summaries(self):
        self.compiles["hillslope"] += 1

    def compile_channel_summaries(self):
        self.compiles["channel"] += 1

    def scenarios_report(self):
        self.compiles["report"] += 1


class _ContrastOmniStub:
    def __init__(self, wd: Path) -> None:
        self.wd = str(wd)
        self.runid = "run-123"
        self.logger = logging.getLogger("tests.omni.run_orchestration.contrasts")
        self._contrast_names = ["uniform_low,1__to__mulch"]
        self._contrast_dependency_tree = {}
        self.status_calls: list[tuple[int, str, str, str | None, str | None]] = []
        self.updated_dependency: tuple[str, dict] | None = None

    @property
    def contrast_names(self):
        return self._contrast_names

    @property
    def contrast_dependency_tree(self):
        return self._contrast_dependency_tree

    def _contrast_landuse_skip_reason(self, *_args, **_kwargs):
        return None

    def _clean_contrast_run(self, _contrast_id):
        return None

    def _remove_contrast_dependency_entry(self, _contrast_name):
        return None

    def _clear_contrast_run_status(self, _contrast_id):
        return None

    def _load_contrast_sidecar(self, _contrast_id):
        return {"10": "/tmp/H10"}

    def _contrast_scenario_keys(self, _contrast_name):
        return "uniform_low", "mulch"

    def contrast_output_options(self):
        return {"ebe_pw0": True}

    def _write_contrast_run_status(self, contrast_id, contrast_name, status, *, job_id=None, error=None):
        self.status_calls.append((contrast_id, contrast_name, status, job_id, error))

    def _post_omni_run(self, _omni_wd, _contrast_name):
        return None

    def _contrast_dependency_entry(self, _contrast_id, _contrast_name):
        return {"signature": "abc"}

    def _update_contrast_dependency_tree(self, contrast_name, dependency_entry):
        self.updated_dependency = (contrast_name, dependency_entry)


class _BulkContrastOmniStub:
    def __init__(self, wd: Path) -> None:
        self.wd = str(wd)
        self.runid = "run-123"
        self.logger = logging.getLogger("tests.omni.run_orchestration.bulk")
        self._contrast_names = ["uniform_low,1__to__mulch"]
        self._contrast_dependency_tree = {
            "uniform_low,1__to__mulch": {"signature": "stale"},
            "stale,99__to__mulch": {"signature": "old"},
        }
        self._lock_calls = 0
        self._fail_first_lock = True
        self.clean_stale_args: list[list[int]] = []

    @property
    def contrast_names(self):
        return self._contrast_names

    @property
    def contrast_dependency_tree(self):
        return self._contrast_dependency_tree

    @contextmanager
    def locked(self):
        self._lock_calls += 1
        if self._fail_first_lock:
            self._fail_first_lock = False
            raise NoDbAlreadyLockedError("lock busy")
        yield

    def contrast_output_options(self):
        return {"ebe_pw0": True}

    def _contrast_landuse_skip_reason(self, *_args, **_kwargs):
        return None

    def _clean_contrast_run(self, _contrast_id):
        return None

    def _contrast_run_status(self, _contrast_id, _contrast_name):
        return "needs_run"

    def _load_contrast_sidecar(self, _contrast_id):
        return {"10": "/tmp/H10"}

    def _contrast_scenario_keys(self, _contrast_name):
        return "uniform_low", "mulch"

    def _post_omni_run(self, _omni_wd, _contrast_name):
        return None

    def _contrast_dependency_entry(self, _contrast_id, _contrast_name):
        return {"signature": "new"}

    def _clean_stale_contrast_runs(self, active_ids):
        self.clean_stale_args.append(list(active_ids))


def test_run_omni_scenarios_skip_and_execute_persist_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniRunOrchestrationService()
    dep_path = tmp_path / "dep" / "loss_pw0.out.parquet"
    dep_path.parent.mkdir(parents=True)
    dep_path.write_text("ok", encoding="ascii")

    def _unused_run(*_args, **_kwargs):
        return str(tmp_path / "unused")

    _install_omni_module_stub(monkeypatch, run_contrast=_unused_run)

    omni = _ScenarioOmniStub(tmp_path)
    dep_sha = hashlib.sha1(dep_path.read_bytes()).hexdigest()
    omni.scenario_dependency_tree = {
        "uniform_low": {
            "dependency_sha1": dep_sha,
            "signature": "sig:uniform_low",
        }
    }

    service.run_omni_scenarios(omni)

    states = {entry["scenario"]: entry for entry in omni.scenario_run_state}
    assert states["uniform_low"]["status"] == "skipped"
    assert states["uniform_low"]["reason"] == "dependency_unchanged"
    assert states["mulch_30_uniform_low"]["status"] == "executed"
    assert states["mulch_30_uniform_low"]["reason"] == "dependency_changed"
    assert omni.run_calls == ["mulch_30_uniform_low"]
    assert omni.compiles == {"hillslope": 1, "channel": 1, "report": 1}


def test_run_omni_scenarios_executes_year_set_mismatch_when_dependency_up_to_date(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniRunOrchestrationService()
    dep_path = tmp_path / "dep" / "loss_pw0.out.parquet"
    dep_path.parent.mkdir(parents=True)
    dep_path.write_text("ok", encoding="ascii")

    def _unused_run(*_args, **_kwargs):
        return str(tmp_path / "unused")

    _install_omni_module_stub(monkeypatch, run_contrast=_unused_run)

    class _ScenarioOmniYearMismatchStub(_ScenarioOmniStub):
        def _year_set_for_scenario(self, scenario_name):
            scenario_key = str(scenario_name)
            if scenario_key == str(self.base_scenario):
                return {2020}
            if scenario_key == "uniform_low":
                return {2021}
            return {2020}

    omni = _ScenarioOmniYearMismatchStub(tmp_path)
    omni.scenarios = [{"type": "uniform_low"}]

    dep_sha = hashlib.sha1(dep_path.read_bytes()).hexdigest()
    omni.scenario_dependency_tree = {
        "uniform_low": {
            "dependency_sha1": dep_sha,
            "signature": "sig:uniform_low",
        }
    }

    service.run_omni_scenarios(omni)

    states = {entry["scenario"]: entry for entry in omni.scenario_run_state}
    assert states["uniform_low"]["status"] == "executed"
    assert states["uniform_low"]["reason"] == "year_set_mismatch"
    assert omni.run_calls == ["uniform_low"]
    assert omni.compiles == {"hillslope": 1, "channel": 1, "report": 1}


def test_run_omni_contrast_writes_started_completed_and_updates_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniRunOrchestrationService()

    def _run_contrast(*_args, **_kwargs):
        return str(tmp_path / "_pups" / "omni" / "contrasts" / "1")

    _install_omni_module_stub(monkeypatch, run_contrast=_run_contrast)

    omni = _ContrastOmniStub(tmp_path)
    result = service.run_omni_contrast(omni, 1, rq_job_id="job-1")

    assert result.endswith("/_pups/omni/contrasts/1")
    assert [status for _, _, status, _, _ in omni.status_calls] == ["started", "completed"]
    assert omni.updated_dependency == ("uniform_low,1__to__mulch", {"signature": "abc"})


def test_run_omni_contrast_writes_failed_status_and_reraises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniRunOrchestrationService()

    def _run_contrast(*_args, **_kwargs):
        raise ValueError("boom")

    _install_omni_module_stub(monkeypatch, run_contrast=_run_contrast)

    omni = _ContrastOmniStub(tmp_path)
    with pytest.raises(ValueError, match="boom"):
        service.run_omni_contrast(omni, 1, rq_job_id="job-2")

    statuses = [status for _, _, status, _, _ in omni.status_calls]
    assert statuses == ["started", "failed"]
    assert omni.status_calls[-1][4] == "boom"


def test_run_omni_contrasts_retries_lock_and_cleans_stale_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniRunOrchestrationService()

    def _run_contrast(*_args, **_kwargs):
        return str(tmp_path / "_pups" / "omni" / "contrasts" / "1")

    _install_omni_module_stub(monkeypatch, run_contrast=_run_contrast)
    monkeypatch.setattr(
        "wepppy.nodb.mods.omni.omni_run_orchestration_service.time.sleep",
        lambda *_args, **_kwargs: None,
    )

    omni = _BulkContrastOmniStub(tmp_path)
    service.run_omni_contrasts(omni)

    assert omni._lock_calls >= 2
    assert omni._contrast_dependency_tree == {"uniform_low,1__to__mulch": {"signature": "new"}}
    assert omni.clean_stale_args == [[1]]
