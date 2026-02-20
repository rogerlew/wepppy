from __future__ import annotations

from pathlib import Path

import pytest

import wepppy.nodb.mods.omni.omni as omni_module
from wepppy.nodb.mods.omni.omni_build_router import OmniBuildRouter

pytestmark = pytest.mark.unit


def test_build_router_calls_contrast_build_implementation() -> None:
    router = OmniBuildRouter()

    class DummyOmni:
        def __init__(self) -> None:
            self.calls: list[tuple[str, object]] = []

        def _build_contrasts_router_impl(self, **kwargs) -> None:
            self.calls.append(("build", kwargs))

    omni = DummyOmni()

    router.build_contrasts(
        omni,
        control_scenario_def={"type": "uniform_low"},
        contrast_scenario_def={"type": "mulch"},
        obj_param="Runoff_mm",
        contrast_cumulative_obj_param_threshold_fraction=0.8,
        contrast_hillslope_limit=25,
        hill_min_slope=0.1,
        hill_max_slope=0.5,
        select_burn_severities=[1, 2],
        select_topaz_ids=[10],
        contrast_pairs=[{"control_scenario": "uniform_low", "contrast_scenario": "mulch"}],
    )

    assert omni.calls and omni.calls[0][0] == "build"
    payload = omni.calls[0][1]
    assert payload["obj_param"] == "Runoff_mm"
    assert payload["contrast_hillslope_limit"] == 25


def test_build_router_routes_dry_run_and_status_calls() -> None:
    router = OmniBuildRouter()

    class DummyOmni:
        def _build_contrasts_dry_run_report_impl(self, **kwargs):
            return {"selection_mode": "cumulative", "kwargs": kwargs}

        def _contrast_status_report_impl(self):
            return {"selection_mode": "cumulative", "items": []}

    omni = DummyOmni()

    report = router.build_contrasts_dry_run_report(
        omni,
        control_scenario_def={"type": "uniform_low"},
        contrast_scenario_def={"type": "mulch"},
        obj_param="Runoff_mm",
        contrast_cumulative_obj_param_threshold_fraction=0.8,
        contrast_hillslope_limit=None,
        hill_min_slope=None,
        hill_max_slope=None,
        select_burn_severities=None,
        select_topaz_ids=None,
        contrast_pairs=None,
    )

    assert report["selection_mode"] == "cumulative"
    assert report["kwargs"]["obj_param"] == "Runoff_mm"
    assert router.contrast_status_report(omni) == {"selection_mode": "cumulative", "items": []}


def _new_detached_omni(tmp_path: Path) -> omni_module.Omni:
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    return omni


def test_facade_build_contrasts_delegates_to_router(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = _new_detached_omni(tmp_path)
    captured: dict[str, object] = {}

    def _fake_build(instance, **kwargs):
        captured["instance"] = instance
        captured["kwargs"] = kwargs

    monkeypatch.setattr(omni_module._OMNI_BUILD_ROUTER, "build_contrasts", _fake_build)

    omni.build_contrasts(
        control_scenario_def={"type": "uniform_low"},
        contrast_scenario_def={"type": "mulch"},
        obj_param="Runoff_mm",
        contrast_cumulative_obj_param_threshold_fraction=0.7,
        contrast_hillslope_limit=5,
        hill_min_slope=0.2,
        hill_max_slope=0.3,
        select_burn_severities=[2],
        select_topaz_ids=[12],
        contrast_pairs=[{"control_scenario": "uniform_low", "contrast_scenario": "mulch"}],
    )

    assert captured["instance"] is omni
    assert captured["kwargs"]["obj_param"] == "Runoff_mm"
    assert captured["kwargs"]["contrast_hillslope_limit"] == 5


def test_facade_dry_run_and_status_delegate_to_router(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = _new_detached_omni(tmp_path)

    monkeypatch.setattr(
        omni_module._OMNI_BUILD_ROUTER,
        "build_contrasts_dry_run_report",
        lambda instance, **kwargs: {"selection_mode": "cumulative", "items": [{"contrast_id": 1}]},
    )
    monkeypatch.setattr(
        omni_module._OMNI_BUILD_ROUTER,
        "contrast_status_report",
        lambda instance: {"selection_mode": "cumulative", "items": [{"contrast_id": 2}]},
    )

    report = omni.build_contrasts_dry_run_report(
        control_scenario_def={"type": "uniform_low"},
        contrast_scenario_def={"type": "mulch"},
    )

    assert report == {"selection_mode": "cumulative", "items": [{"contrast_id": 1}]}
    assert omni.contrast_status_report() == {
        "selection_mode": "cumulative",
        "items": [{"contrast_id": 2}],
    }
