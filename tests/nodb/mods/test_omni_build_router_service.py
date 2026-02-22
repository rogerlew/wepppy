from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

import wepppy.nodb.mods.omni.omni as omni_module
import wepppy.nodb.mods.omni.omni_build_router as omni_build_router_module
from wepppy.nodb.mods.omni.omni_build_router import OmniBuildRouter

pytestmark = pytest.mark.unit


class _BuildOmniStub:
    def __init__(self, selection_mode: str = "cumulative") -> None:
        self._contrast_selection_mode = selection_mode
        self._contrast_pairs = []
        self._build_calls = 0
        self._geojson_calls = 0
        self.events: list[str] = []

    @contextmanager
    def locked(self):
        self.events.append("lock-enter")
        yield
        self.events.append("lock-exit")

    def _normalize_contrast_pairs(self, value):
        return [{"control_scenario": "uniform_low", "contrast_scenario": "mulch"}] if value else []

    def _build_contrasts(self) -> None:
        self._build_calls += 1

    def _build_contrast_ids_geojson(self) -> str:
        self._geojson_calls += 1
        return "contrast_ids.geojson"

    class logger:
        @staticmethod
        def info(*_args, **_kwargs):
            return None


def test_build_router_sets_contrast_inputs_inside_lock_scope() -> None:
    router = OmniBuildRouter()
    omni = _BuildOmniStub(selection_mode="cumulative")

    router.build_contrasts(
        omni,
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

    assert omni.events == ["lock-enter", "lock-exit"]
    assert omni._control_scenario == omni_module._scenario_name_from_scenario_definition({"type": "uniform_low"})
    assert omni._contrast_scenario == omni_module._scenario_name_from_scenario_definition({"type": "mulch"})
    assert omni._contrast_object_param == "Runoff_mm"
    assert omni._contrast_cumulative_obj_param_threshold_fraction == 0.7
    assert omni._contrast_hillslope_limit == 5
    assert omni._contrast_hill_min_slope == 0.2
    assert omni._contrast_hill_max_slope == 0.3
    assert omni._contrast_select_burn_severities == [2]
    assert omni._contrast_select_topaz_ids == [12]
    assert omni._contrast_pairs == [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
    ]
    assert omni._build_calls == 1
    assert omni._geojson_calls == 1


def test_build_router_requires_control_and_contrast_for_cumulative_mode() -> None:
    router = OmniBuildRouter()
    omni = _BuildOmniStub(selection_mode="cumulative")

    with pytest.raises(ValueError, match="control_scenario_def and contrast_scenario_def are required"):
        router.build_contrasts(
            omni,
            control_scenario_def=None,
            contrast_scenario_def=None,
            obj_param="Runoff_mm",
            contrast_cumulative_obj_param_threshold_fraction=0.8,
            contrast_hillslope_limit=None,
            hill_min_slope=None,
            hill_max_slope=None,
            select_burn_severities=None,
            select_topaz_ids=None,
            contrast_pairs=None,
        )


def test_build_router_allows_selection_modes_without_scenario_defs() -> None:
    router = OmniBuildRouter()
    omni = _BuildOmniStub(selection_mode="stream_order")

    router.build_contrasts(
        omni,
        control_scenario_def=None,
        contrast_scenario_def=None,
        obj_param="Runoff_mm",
        contrast_cumulative_obj_param_threshold_fraction=0.8,
        contrast_hillslope_limit=None,
        hill_min_slope=None,
        hill_max_slope=None,
        select_burn_severities=None,
        select_topaz_ids=None,
        contrast_pairs=[{"control_scenario": "uniform_low", "contrast_scenario": "mulch"}],
    )

    assert omni._control_scenario is None
    assert omni._contrast_scenario is None
    assert omni._build_calls == 1
    assert omni._geojson_calls == 1


def test_build_router_uses_scaling_singleton_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = OmniBuildRouter()
    omni = _BuildOmniStub(selection_mode="cumulative")
    seen_modes: list[str | None] = []

    def _normalize(value):
        seen_modes.append(value)
        return "stream_order"

    monkeypatch.setattr(omni_module._OMNI_SCALING_SERVICE, "normalize_selection_mode", _normalize)

    router.build_contrasts(
        omni,
        control_scenario_def=None,
        contrast_scenario_def=None,
        obj_param="Runoff_mm",
        contrast_cumulative_obj_param_threshold_fraction=0.8,
        contrast_hillslope_limit=None,
        hill_min_slope=None,
        hill_max_slope=None,
        select_burn_severities=None,
        select_topaz_ids=None,
        contrast_pairs=[{"control_scenario": "uniform_low", "contrast_scenario": "mulch"}],
    )

    assert seen_modes == ["cumulative"]
    assert omni._build_calls == 1
    assert omni._geojson_calls == 1


class _StatusOmniStub:
    def __init__(
        self,
        *,
        selection_mode: str,
        contrast_names: list[str | None],
        build_report: list[dict],
        run_status_map: dict[int, str] | None = None,
        skip_reason_map: dict[int, str] | None = None,
        control_scenario: str | None = None,
        contrast_scenario: str | None = None,
        contrast_labels: dict[int, str] | None = None,
    ) -> None:
        self._contrast_selection_mode = selection_mode
        self.contrast_names = contrast_names
        self._build_report = build_report
        self._run_status_map = run_status_map or {}
        self._skip_reason_map = skip_reason_map or {}
        self._control_scenario = control_scenario
        self._contrast_scenario = contrast_scenario
        self._contrast_labels = contrast_labels or {}

    def _load_contrast_build_report(self):
        return list(self._build_report)

    def _normalize_scenario_key(self, value):
        if value in (None, "None"):
            return str(omni_module.OmniScenario.Undisturbed)
        return str(value)

    def _contrast_landuse_skip_reason(self, contrast_id, _contrast_name, *, landuse_cache=None):
        return self._skip_reason_map.get(int(contrast_id))

    def _contrast_run_status(self, contrast_id, _contrast_name):
        return self._run_status_map.get(int(contrast_id), "needs_run")


def test_contrast_status_report_cumulative_payload_shape() -> None:
    router = OmniBuildRouter()
    omni = _StatusOmniStub(
        selection_mode="cumulative",
        contrast_names=["uniform_low,10__to__mulch", None],
        build_report=[],
        run_status_map={1: "up_to_date"},
    )

    payload = router.contrast_status_report(omni)

    assert payload["selection_mode"] == "cumulative"
    assert payload["items"][0]["contrast_id"] == 1
    assert payload["items"][0]["topaz_id"] == "10"
    assert payload["items"][0]["run_status"] == "up_to_date"
    assert payload["items"][1]["run_status"] == "skipped"
    assert payload["items"][1]["skip_status"]["reason"] == "no_hillslopes"


def test_contrast_status_report_user_defined_areas_payload_shape() -> None:
    router = OmniBuildRouter()
    omni = _StatusOmniStub(
        selection_mode="user_defined_areas",
        contrast_names=[None, "undisturbed,2__to__mulch"],
        build_report=[
            {
                "selection_mode": "user_defined_areas",
                "contrast_id": 1,
                "control_scenario": "undisturbed",
                "contrast_scenario": "mulch",
                "area_label": "A1",
                "n_hillslopes": 0,
                "status": "skipped",
            },
            {
                "selection_mode": "user_defined_areas",
                "contrast_id": 2,
                "control_scenario": "undisturbed",
                "contrast_scenario": "mulch",
                "area_label": "A2",
                "n_hillslopes": 3,
            },
        ],
        run_status_map={2: "needs_run"},
        skip_reason_map={2: "landuse_unchanged"},
        control_scenario="undisturbed",
        contrast_scenario="mulch",
    )

    payload = router.contrast_status_report(omni)

    assert payload["selection_mode"] == "user_defined_areas"
    assert payload["items"][0]["area_label"] == "A1"
    assert payload["items"][0]["run_status"] == "skipped"
    assert payload["items"][0]["skip_status"]["reason"] == "no_hillslopes"
    assert payload["items"][1]["area_label"] == "A2"
    assert payload["items"][1]["run_status"] == "skipped"
    assert payload["items"][1]["skip_status"]["reason"] == "landuse_unchanged"


def test_contrast_status_report_user_defined_hillslope_groups_payload_shape() -> None:
    router = OmniBuildRouter()
    omni = _StatusOmniStub(
        selection_mode="user-defined-hillslope-group",
        contrast_names=["undisturbed,1__to__mulch"],
        build_report=[
            {
                "selection_mode": "user_defined_hillslope_groups",
                "contrast_id": 1,
                "control_scenario": "undisturbed",
                "contrast_scenario": "mulch",
                "group_index": 7,
                "n_hillslopes": 2,
            }
        ],
        run_status_map={1: "needs_run"},
    )

    payload = router.contrast_status_report(omni)

    assert payload["selection_mode"] == "user_defined_hillslope_groups"
    assert payload["items"] == [
        {
            "contrast_id": 1,
            "control_scenario": "undisturbed",
            "contrast_scenario": "mulch",
            "group_index": 7,
            "n_hillslopes": 2,
            "skip_status": {"skipped": False, "reason": None},
            "run_status": "needs_run",
        }
    ]


def test_contrast_status_report_stream_order_payload_shape() -> None:
    router = OmniBuildRouter()
    omni = _StatusOmniStub(
        selection_mode="stream_order",
        contrast_names=["uniform_low,1__to__mulch", None],
        build_report=[
            {
                "selection_mode": "stream_order",
                "contrast_id": 1,
                "control_scenario": "uniform_low",
                "contrast_scenario": "mulch",
                "subcatchments_group": 10,
                "n_hillslopes": 4,
            },
            {
                "selection_mode": "stream_order",
                "contrast_id": 2,
                "control_scenario": "uniform_low",
                "contrast_scenario": "mulch",
                "subcatchments_group": 20,
                "n_hillslopes": 0,
                "status": "skipped",
            },
        ],
        run_status_map={1: "up_to_date"},
    )

    payload = router.contrast_status_report(omni)

    assert payload["selection_mode"] == "stream_order"
    assert payload["items"][0]["subcatchments_group"] == 10
    assert payload["items"][0]["run_status"] == "up_to_date"
    assert payload["items"][1]["run_status"] == "skipped"
    assert payload["items"][1]["skip_status"]["reason"] == "no_hillslopes"


def test_contrast_status_report_raises_for_unknown_selection_mode() -> None:
    router = OmniBuildRouter()
    omni = _StatusOmniStub(
        selection_mode="unknown_mode",
        contrast_names=[],
        build_report=[],
    )

    with pytest.raises(ValueError, match='Contrast selection mode "unknown_mode" is not implemented yet.'):
        router.contrast_status_report(omni)


def test_contrast_status_report_stream_order_coerces_string_contrast_id() -> None:
    router = OmniBuildRouter()
    omni = _StatusOmniStub(
        selection_mode="stream_order",
        contrast_names=["uniform_low,1__to__mulch"],
        build_report=[
            {
                "selection_mode": "stream_order",
                "contrast_id": "1",
                "control_scenario": "uniform_low",
                "contrast_scenario": "mulch",
                "subcatchments_group": 10,
                "n_hillslopes": 4,
            }
        ],
        run_status_map={1: "up_to_date"},
    )

    payload = router.contrast_status_report(omni)

    assert payload["items"][0]["contrast_id"] == 1
    assert payload["items"][0]["run_status"] == "up_to_date"


def test_contrast_status_report_user_defined_area_uses_topaz_id_count_fallback() -> None:
    router = OmniBuildRouter()
    omni = _StatusOmniStub(
        selection_mode="user_defined_areas",
        contrast_names=["undisturbed,2__to__mulch"],
        build_report=[
            {
                "selection_mode": "user_defined_areas",
                "contrast_id": 1,
                "control_scenario": "undisturbed",
                "contrast_scenario": "mulch",
                "n_hillslopes": None,
                "topaz_ids": [2, 4, 6],
            }
        ],
        run_status_map={1: "up_to_date"},
        control_scenario="undisturbed",
        contrast_scenario="mulch",
    )

    payload = router.contrast_status_report(omni)

    assert payload["items"][0]["n_hillslopes"] == 3
    assert payload["items"][0]["run_status"] == "up_to_date"
    assert payload["items"][0]["skip_status"] == {"skipped": False, "reason": None}


def test_contrast_status_report_user_defined_area_uses_contrast_labels_fallback() -> None:
    router = OmniBuildRouter()
    omni = _StatusOmniStub(
        selection_mode="user_defined_areas",
        contrast_names=["undisturbed,2__to__mulch"],
        build_report=[
            {
                "selection_mode": "user_defined_areas",
                "contrast_id": 1,
                "control_scenario": "undisturbed",
                "contrast_scenario": "mulch",
                "n_hillslopes": 1,
            }
        ],
        run_status_map={1: "up_to_date"},
        control_scenario="undisturbed",
        contrast_scenario="mulch",
        contrast_labels={1: "Area 1"},
    )

    payload = router.contrast_status_report(omni)

    assert payload["items"][0]["area_label"] == "Area 1"


def test_contrast_status_report_user_defined_group_uses_contrast_labels_fallback() -> None:
    router = OmniBuildRouter()
    omni = _StatusOmniStub(
        selection_mode="user_defined_hillslope_groups",
        contrast_names=["undisturbed,1__to__mulch"],
        build_report=[
            {
                "selection_mode": "user_defined_hillslope_groups",
                "contrast_id": 1,
                "control_scenario": "undisturbed",
                "contrast_scenario": "mulch",
                "group_index": None,
                "n_hillslopes": 2,
            }
        ],
        run_status_map={1: "needs_run"},
        contrast_labels={1: "G-1"},
    )

    payload = router.contrast_status_report(omni)

    assert payload["items"][0]["group_index"] == "G-1"


def test_contrast_status_report_stream_order_backfills_both_scenarios_from_name() -> None:
    router = OmniBuildRouter()
    omni = _StatusOmniStub(
        selection_mode="stream_order",
        contrast_names=["uniform_low,1__to__mulch"],
        build_report=[
            {
                "selection_mode": "stream_order",
                "contrast_id": 1,
                "control_scenario": "report_value_should_be_replaced",
                "contrast_scenario": None,
                "subcatchments_group": 10,
                "n_hillslopes": 3,
            }
        ],
        run_status_map={1: "needs_run"},
    )

    payload = router.contrast_status_report(omni)

    assert payload["items"][0]["control_scenario"] == "uniform_low"
    assert payload["items"][0]["contrast_scenario"] == "mulch"


def test_build_router_status_report_delegates_to_status_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = OmniBuildRouter()
    omni = object()

    monkeypatch.setattr(
        omni_build_router_module._OMNI_CONTRAST_STATUS_REPORT_SERVICE,
        "contrast_status_report",
        lambda instance: {"selection_mode": "cumulative", "items": [{"instance": instance}]},
    )

    assert router.contrast_status_report(omni) == {
        "selection_mode": "cumulative",
        "items": [{"instance": omni}],
    }


def test_build_router_dry_run_report_normalizes_selection_mode_alias_with_underscore() -> None:
    router = OmniBuildRouter()
    omni = _StatusOmniStub(
        selection_mode="stream_order_pruning",
        contrast_names=["uniform_low,1__to__mulch"],
        build_report=[
            {
                "selection_mode": "stream_order",
                "contrast_id": 1,
                "control_scenario": "uniform_low",
                "contrast_scenario": "mulch",
                "subcatchments_group": 10,
                "n_hillslopes": 1,
            }
        ],
        run_status_map={1: "needs_run"},
    )
    omni.events = []

    @contextmanager
    def _locked():
        omni.events.append("lock-enter")
        yield
        omni.events.append("lock-exit")

    omni.locked = _locked
    omni.logger = type("Logger", (), {"info": staticmethod(lambda *_args, **_kwargs: None)})()
    omni._normalize_contrast_pairs = lambda value: value
    omni._build_contrasts = lambda: None
    omni._build_contrast_ids_geojson = lambda: "contrast_ids.geojson"
    omni.build_contrasts = lambda **kwargs: router.build_contrasts(omni, **kwargs)

    payload = router.build_contrasts_dry_run_report(
        omni,
        control_scenario_def=None,
        contrast_scenario_def=None,
        obj_param="Runoff_mm",
        contrast_cumulative_obj_param_threshold_fraction=0.8,
        contrast_hillslope_limit=None,
        hill_min_slope=None,
        hill_max_slope=None,
        select_burn_severities=None,
        select_topaz_ids=None,
        contrast_pairs=[{"control_scenario": "uniform_low", "contrast_scenario": "mulch"}],
    )

    assert omni.events == ["lock-enter", "lock-exit"]
    assert payload["selection_mode"] == "stream_order"
    assert payload["items"][0]["contrast_id"] == 1
    assert payload["items"][0]["subcatchments_group"] == 10
    assert payload["items"][0]["run_status"] == "needs_run"


def test_build_router_dry_run_report_normalizes_selection_mode_alias() -> None:
    router = OmniBuildRouter()
    omni = _StatusOmniStub(
        selection_mode="stream-order-pruning",
        contrast_names=["uniform_low,1__to__mulch"],
        build_report=[
            {
                "selection_mode": "stream_order",
                "contrast_id": 1,
                "control_scenario": "uniform_low",
                "contrast_scenario": "mulch",
                "subcatchments_group": 10,
                "n_hillslopes": 1,
            }
        ],
        run_status_map={1: "needs_run"},
    )
    omni.events = []

    @contextmanager
    def _locked():
        omni.events.append("lock-enter")
        yield
        omni.events.append("lock-exit")

    omni.locked = _locked
    omni.logger = type("Logger", (), {"info": staticmethod(lambda *_args, **_kwargs: None)})()
    omni._normalize_contrast_pairs = lambda value: value
    omni._build_contrasts = lambda: None
    omni._build_contrast_ids_geojson = lambda: "contrast_ids.geojson"
    omni.build_contrasts = lambda **kwargs: router.build_contrasts(omni, **kwargs)

    payload = router.build_contrasts_dry_run_report(
        omni,
        control_scenario_def=None,
        contrast_scenario_def=None,
        obj_param="Runoff_mm",
        contrast_cumulative_obj_param_threshold_fraction=0.8,
        contrast_hillslope_limit=None,
        hill_min_slope=None,
        hill_max_slope=None,
        select_burn_severities=None,
        select_topaz_ids=None,
        contrast_pairs=[{"control_scenario": "uniform_low", "contrast_scenario": "mulch"}],
    )

    assert omni.events == ["lock-enter", "lock-exit"]
    assert payload["selection_mode"] == "stream_order"
    assert payload["items"][0]["contrast_id"] == 1
    assert payload["items"][0]["subcatchments_group"] == 10
    assert payload["items"][0]["run_status"] == "needs_run"


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
