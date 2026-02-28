from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.mods.omni.omni as omni_module
import wepppy.nodb.mods.omni.omni_mode_build_services as mode_services_module
from wepppy.nodb.mods.omni.omni_mode_build_services import OmniModeBuildServices

pytestmark = pytest.mark.unit


class _DummyOmni:
    def __init__(self, tmp_path: Path) -> None:
        self.wd = str(tmp_path / "run")
        Path(self.wd).mkdir(parents=True, exist_ok=True)
        self.runid = "demo"
        self.logger = logging.getLogger("tests.omni.mode_services")
        self._has_sbs = True

    @property
    def has_sbs(self) -> bool:
        return self._has_sbs

    @property
    def base_scenario(self):
        return omni_module.OmniScenario.Undisturbed

    @property
    def rq_job_pool_max_worker_per_scenario_task(self) -> int:
        return 2

    @contextmanager
    def timed(self, _label: str):
        yield


def test_build_contrasts_for_selection_mode_dispatches() -> None:
    service = OmniModeBuildServices()

    class DummyOmni:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def _build_contrasts_user_defined_areas(self) -> None:
            self.calls.append("areas")

        def _build_contrasts_user_defined_hillslope_groups(self) -> None:
            self.calls.append("groups")

        def _build_contrasts_stream_order(self) -> None:
            self.calls.append("stream")

    omni = DummyOmni()

    assert service.build_contrasts_for_selection_mode(omni, "user_defined_areas") is True
    assert service.build_contrasts_for_selection_mode(omni, "user_defined_hillslope_groups") is True
    assert service.build_contrasts_for_selection_mode(omni, "stream_order") is True
    assert service.build_contrasts_for_selection_mode(omni, "cumulative") is False
    assert omni.calls == ["areas", "groups", "stream"]


def test_build_contrasts_stream_order_mapping_helper_preserves_name_labels(tmp_path: Path) -> None:
    service = OmniModeBuildServices()
    omni = _DummyOmni(tmp_path)
    top2wepp = {"10": "1", "20": "2"}

    contrast_name, contrast = service.build_contrast_mapping(
        omni,
        top2wepp=top2wepp,
        selected_topaz_ids={"10"},
        control_scenario=None,
        contrast_scenario="mulch",
        contrast_id=3,
        control_label="uniform_low",
        contrast_label="mulch",
    )

    assert contrast_name == "uniform_low,3__to__mulch"
    assert contrast["10"].endswith("/_pups/omni/scenarios/mulch/wepp/output/H1")
    assert contrast["20"].endswith("/wepp/output/H2")


def test_build_contrasts_user_defined_areas_mapping_helper_uses_base_default_target(tmp_path: Path) -> None:
    service = OmniModeBuildServices()
    omni = _DummyOmni(tmp_path)
    top2wepp = {"10": "1", "20": "2"}

    contrast_name, contrast = service.build_contrast_mapping(
        omni,
        top2wepp=top2wepp,
        selected_topaz_ids={"20"},
        control_scenario="uniform_low",
        contrast_scenario=None,
        contrast_id=20,
    )

    assert contrast_name == "uniform_low,20__to__undisturbed"
    assert contrast["10"].endswith("/_pups/omni/scenarios/uniform_low/wepp/output/H1")
    assert contrast["20"].endswith("/wepp/output/H2")


def test_apply_scenario_mode_uniform_runs_expected_build_steps(tmp_path: Path) -> None:
    service = OmniModeBuildServices()
    omni = _DummyOmni(tmp_path)

    class DisturbedStub:
        def __init__(self) -> None:
            self.uniform_calls: list[int] = []
            self.validate_calls: list[tuple[str, int, int]] = []

        def build_uniform_sbs(self, severity: int) -> str:
            self.uniform_calls.append(severity)
            return f"uniform-{severity}.tif"

        def validate(self, sbs_fn: str, mode: int, uniform_severity: int | None = None) -> None:
            self.validate_calls.append((sbs_fn, mode, int(uniform_severity or 0)))

    class LanduseStub:
        def __init__(self) -> None:
            self.build_calls = 0

        def build(self) -> None:
            self.build_calls += 1

    class SoilsStub:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def build(self, max_workers: int | None = None) -> None:
            self.calls.append(int(max_workers or 0))

    disturbed = DisturbedStub()
    landuse = LanduseStub()
    soils = SoilsStub()

    service.apply_scenario_mode(
        omni,
        scenario_name="uniform_low",
        scenario=omni_module.OmniScenario.UniformLow,
        scenario_def={"type": "uniform_low"},
        new_wd=omni.wd,
        disturbed=disturbed,
        landuse=landuse,
        soils=soils,
        omni_base_scenario_name=None,
    )

    assert disturbed.uniform_calls == [1]
    assert disturbed.validate_calls == [("uniform-1.tif", 1, 1)]
    assert landuse.build_calls == 1
    assert soils.calls == [2]


def test_apply_scenario_mode_uniform_runs_without_mutation_wrapper(tmp_path: Path) -> None:
    service = OmniModeBuildServices()
    omni = _DummyOmni(tmp_path)

    class DisturbedStub:
        def build_uniform_sbs(self, severity: int) -> str:
            return f"uniform-{severity}.tif"

        def validate(self, sbs_fn: str, mode: int, uniform_severity: int | None = None) -> None:
            return None

    class LanduseStub:
        def __init__(self) -> None:
            self.calls = 0

        def build(self) -> None:
            self.calls += 1

    class SoilsStub:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def build(self, max_workers: int | None = None) -> None:
            self.calls.append(int(max_workers or 0))

    landuse = LanduseStub()
    soils = SoilsStub()

    service.apply_scenario_mode(
        omni,
        scenario_name="uniform_low",
        scenario=omni_module.OmniScenario.UniformLow,
        scenario_def={"type": "uniform_low"},
        new_wd=omni.wd,
        disturbed=DisturbedStub(),
        landuse=landuse,
        soils=soils,
        omni_base_scenario_name=None,
    )

    assert landuse.calls == 1
    assert soils.calls == [2]


def test_apply_scenario_mode_uniform_rejects_archive_form_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniModeBuildServices()
    omni = _DummyOmni(tmp_path)
    monkeypatch.setattr(
        mode_services_module,
        "nodir_resolve",
        lambda _wd, _root, view="effective": SimpleNamespace(form="archive"),
    )

    class DisturbedStub:
        def build_uniform_sbs(self, severity: int) -> str:
            return f"uniform-{severity}.tif"

        def validate(self, sbs_fn: str, mode: int, uniform_severity: int | None = None) -> None:
            return None

    class LanduseStub:
        def build(self) -> None:
            raise AssertionError("landuse.build should not be called")

    class SoilsStub:
        def build(self, max_workers: int | None = None) -> None:
            raise AssertionError("soils.build should not be called")

    with pytest.raises(mode_services_module.NoDirError) as exc_info:
        service.apply_scenario_mode(
            omni,
            scenario_name="uniform_low",
            scenario=omni_module.OmniScenario.UniformLow,
            scenario_def={"type": "uniform_low"},
            new_wd=omni.wd,
            disturbed=DisturbedStub(),
            landuse=LanduseStub(),
            soils=SoilsStub(),
            omni_base_scenario_name=None,
        )

    assert exc_info.value.code == "NODIR_ARCHIVE_ACTIVE"


def test_apply_scenario_mode_prescribed_fire_rejects_archive_form_soils_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniModeBuildServices()
    omni = _DummyOmni(tmp_path)
    monkeypatch.setattr(
        mode_services_module,
        "nodir_resolve",
        lambda _wd, _root, view="effective": SimpleNamespace(form="archive"),
    )

    class DisturbedStub:
        has_sbs = False

    class LanduseStub:
        domlc_d = {}
        managements = {}

    class SoilsStub:
        def build(self, max_workers: int | None = None) -> None:
            raise AssertionError("soils.build should not be called")

    with pytest.raises(mode_services_module.NoDirError) as exc_info:
        service.apply_scenario_mode(
            omni,
            scenario_name="prescribed_fire",
            scenario=omni_module.OmniScenario.PrescribedFire,
            scenario_def={"type": "prescribed_fire"},
            new_wd=omni.wd,
            disturbed=DisturbedStub(),
            landuse=LanduseStub(),
            soils=SoilsStub(),
            omni_base_scenario_name=None,
        )

    assert exc_info.value.code == "NODIR_ARCHIVE_ACTIVE"


def test_apply_scenario_mode_undisturbed_enforces_sbs_guard(tmp_path: Path) -> None:
    service = OmniModeBuildServices()
    omni = _DummyOmni(tmp_path)
    omni._has_sbs = False

    class DisturbedStub:
        def remove_sbs(self) -> None:
            return None

    class LanduseStub:
        def build(self) -> None:
            return None

    class SoilsStub:
        def build(self, max_workers: int | None = None) -> None:
            return None

    with pytest.raises(Exception, match="Undisturbed scenario requires a base scenario with sbs"):
        service.apply_scenario_mode(
            omni,
            scenario_name="undisturbed",
            scenario=omni_module.OmniScenario.Undisturbed,
            scenario_def={"type": "undisturbed"},
            new_wd=omni.wd,
            disturbed=DisturbedStub(),
            landuse=LanduseStub(),
            soils=SoilsStub(),
            omni_base_scenario_name=None,
        )


def test_apply_scenario_mode_undisturbed_allows_base_context_without_sbs(tmp_path: Path) -> None:
    service = OmniModeBuildServices()
    omni = _DummyOmni(tmp_path)
    omni._has_sbs = False
    omni.wd = str(tmp_path / "_base")
    Path(omni.wd).mkdir(parents=True, exist_ok=True)

    class DisturbedStub:
        def __init__(self) -> None:
            self.remove_calls = 0

        def remove_sbs(self) -> None:
            self.remove_calls += 1

    class LanduseStub:
        def __init__(self) -> None:
            self.build_calls = 0

        def build(self) -> None:
            self.build_calls += 1

    class SoilsStub:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def build(self, max_workers: int | None = None) -> None:
            self.calls.append(int(max_workers or 0))

    disturbed = DisturbedStub()
    landuse = LanduseStub()
    soils = SoilsStub()

    service.apply_scenario_mode(
        omni,
        scenario_name="undisturbed",
        scenario=omni_module.OmniScenario.Undisturbed,
        scenario_def={"type": "undisturbed"},
        new_wd=omni.wd,
        disturbed=disturbed,
        landuse=landuse,
        soils=soils,
        omni_base_scenario_name=None,
    )

    assert disturbed.remove_calls == 1
    assert landuse.build_calls == 1
    assert soils.calls == [2]


def test_apply_scenario_mode_mulch_maps_fire_landuse_to_treatment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniModeBuildServices()
    omni = _DummyOmni(tmp_path)

    class DisturbedStub:
        pass

    class LanduseStub:
        domlc_d = {101: "A", 102: "B", 104: "C"}
        managements = {
            "A": type("Summary", (), {"disturbed_class": "fire low"})(),
            "B": type("Summary", (), {"disturbed_class": "forest mature"})(),
            "C": type("Summary", (), {"disturbed_class": "fire high"})(),
        }

    class SoilsStub:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def build(self, max_workers: int | None = None) -> None:
            self.calls.append(int(max_workers or 0))

    class TreatmentsStub:
        def __init__(self) -> None:
            self.treatments_lookup = {"mulch_30": "M30"}
            self.treatments_domlc_d = {}
            self.build_calls = 0

        def build_treatments(self) -> None:
            self.build_calls += 1

    treatments = TreatmentsStub()
    monkeypatch.setattr(
        "wepppy.nodb.mods.treatments.Treatments.getInstance",
        lambda wd: treatments,
    )

    soils = SoilsStub()
    service.apply_scenario_mode(
        omni,
        scenario_name="mulch_30_uniform_low",
        scenario=omni_module.OmniScenario.Mulch,
        scenario_def={
            "type": "mulch",
            "ground_cover_increase": "30%",
            "base_scenario": "uniform_low",
        },
        new_wd=omni.wd,
        disturbed=DisturbedStub(),
        landuse=LanduseStub(),
        soils=soils,
        omni_base_scenario_name="uniform_low",
    )

    assert treatments.treatments_domlc_d == {101: "M30"}
    assert treatments.build_calls == 1
    assert soils.calls == [2]


def test_apply_scenario_mode_thinning_maps_mature_forest_landuse_to_treatment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniModeBuildServices()
    omni = _DummyOmni(tmp_path)

    class DisturbedStub:
        has_sbs = False

    class LanduseStub:
        domlc_d = {201: "A", 202: "B", 204: "C"}
        managements = {
            "A": type("Summary", (), {"disturbed_class": "forest mature"})(),
            "B": type("Summary", (), {"disturbed_class": "forest young"})(),
            "C": type("Summary", (), {"disturbed_class": "forest mature"})(),
        }

    class SoilsStub:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def build(self, max_workers: int | None = None) -> None:
            self.calls.append(int(max_workers or 0))

    class TreatmentsStub:
        def __init__(self) -> None:
            self.treatments_lookup = {"thinning_70_40": "THIN"}
            self.treatments_domlc_d = {}
            self.build_calls = 0

        def build_treatments(self) -> None:
            self.build_calls += 1

    treatments = TreatmentsStub()
    monkeypatch.setattr(
        "wepppy.nodb.mods.treatments.Treatments.getInstance",
        lambda wd: treatments,
    )

    soils = SoilsStub()
    service.apply_scenario_mode(
        omni,
        scenario_name="thinning_70_40",
        scenario=omni_module.OmniScenario.Thinning,
        scenario_def={"type": "thinning", "canopy_cover": "70", "ground_cover": "40"},
        new_wd=omni.wd,
        disturbed=DisturbedStub(),
        landuse=LanduseStub(),
        soils=soils,
        omni_base_scenario_name=None,
    )

    assert treatments.treatments_domlc_d == {201: "THIN"}
    assert treatments.build_calls == 1
    assert soils.calls == [2]


def test_apply_scenario_mode_prescribed_fire_requires_treatment_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniModeBuildServices()
    omni = _DummyOmni(tmp_path)

    class DisturbedStub:
        has_sbs = False

    class LanduseStub:
        domlc_d = {10: "A"}
        managements = {"A": type("Summary", (), {"disturbed_class": "forest mature"})()}

    class SoilsStub:
        def build(self, max_workers: int | None = None) -> None:
            return None

    class TreatmentsStub:
        treatments_lookup = {}

    monkeypatch.setattr(
        "wepppy.nodb.mods.treatments.Treatments.getInstance",
        lambda wd: TreatmentsStub(),
    )

    with pytest.raises(ValueError, match="Prescribed fire scenario requires a treatment mapping"):
        service.apply_scenario_mode(
            omni,
            scenario_name="prescribed_fire",
            scenario=omni_module.OmniScenario.PrescribedFire,
            scenario_def={"type": "prescribed_fire"},
            new_wd=omni.wd,
            disturbed=DisturbedStub(),
            landuse=LanduseStub(),
            soils=SoilsStub(),
            omni_base_scenario_name=None,
        )


def test_run_omni_scenario_delegates_mode_specific_branch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = omni_module.Omni.__new__(omni_module.Omni)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    scenario_dir = run_dir / "_pups" / "omni" / "scenarios" / "uniform_low"
    scenario_dir.mkdir(parents=True)
    (run_dir / "wepp" / "runs").mkdir(parents=True)
    (scenario_dir / "wepp" / "runs").mkdir(parents=True)
    (scenario_dir / "wepp" / "output").mkdir(parents=True)

    omni.wd = str(run_dir)
    omni.logger = logging.getLogger("tests.omni.mode_services.delegate")

    monkeypatch.setattr(omni_module, "_omni_clone", lambda *args, **kwargs: str(scenario_dir))
    monkeypatch.setattr(omni_module, "_post_watershed_run_cleanup", lambda *args, **kwargs: None)
    monkeypatch.setattr(omni_module, "run_wepp_hillslope_interchange", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        omni_module.Omni,
        "delete_after_interchange",
        property(lambda self: False),
        raising=False,
    )

    class DisturbedStub:
        has_sbs = False

    class LanduseStub:
        def build_managements(self) -> None:
            return None

    class SoilsStub:
        pass

    class WeppStub:
        def __init__(self, wd: str) -> None:
            self.runs_dir = str(Path(wd) / "wepp" / "runs")
            self.output_dir = str(Path(wd) / "wepp" / "output")

        def prep_hillslopes(self, **kwargs) -> None:
            return None

        def run_hillslopes(self, **kwargs) -> None:
            return None

        def prep_watershed(self) -> None:
            return None

        def run_watershed(self) -> None:
            return None

    class ClimateStub:
        observed_start_year = None
        future_start_year = None

    import wepppy.nodb.core as nodb_core
    import wepppy.nodb.mods.disturbed as disturbed_mod

    monkeypatch.setattr(disturbed_mod.Disturbed, "getInstance", lambda wd: DisturbedStub())
    monkeypatch.setattr(nodb_core.Landuse, "getInstance", lambda wd: LanduseStub())
    monkeypatch.setattr(nodb_core.Soils, "getInstance", lambda wd: SoilsStub())
    monkeypatch.setattr(nodb_core.Wepp, "getInstance", lambda wd: WeppStub(wd))
    monkeypatch.setattr(nodb_core.Climate, "getInstance", lambda wd: ClimateStub())

    captured: dict[str, object] = {}

    def _fake_apply(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(omni_module._OMNI_MODE_BUILD_SERVICES, "apply_scenario_mode", _fake_apply)

    scenario_wd, scenario_name = omni.run_omni_scenario({"type": "uniform_low"})

    assert scenario_wd == str(scenario_dir)
    assert scenario_name == "uniform_low"
    assert captured["scenario_name"] == "uniform_low"
    assert captured["new_wd"] == str(scenario_dir)


def test_run_with_directory_roots_lock_sorts_order_and_rechecks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolve_calls: list[tuple[str, str]] = []
    lock_events: list[tuple[str, str, str]] = []

    def _resolve(_wd: str, root: str, view: str = "effective"):
        resolve_calls.append((root, view))
        return SimpleNamespace(form="dir")

    @contextmanager
    def _lock(_wd: str, root: str, *, purpose: str):
        lock_events.append(("enter", root, purpose))
        yield
        lock_events.append(("exit", root, purpose))

    monkeypatch.setattr(mode_services_module, "nodir_resolve", _resolve)
    monkeypatch.setattr(mode_services_module, "nodir_maintenance_lock", _lock)

    callback_calls: list[str] = []
    result = mode_services_module._run_with_directory_roots_lock(
        "/tmp/run",
        ("soils", "landuse", "soils"),
        lambda: callback_calls.append("called") or "ok",
        purpose="omni-unit",
    )

    assert result == "ok"
    assert callback_calls == ["called"]
    assert resolve_calls == [
        ("landuse", "effective"),
        ("soils", "effective"),
        ("landuse", "effective"),
        ("soils", "effective"),
    ]
    assert lock_events == [
        ("enter", "landuse", "omni-unit/landuse"),
        ("enter", "soils", "omni-unit/soils"),
        ("exit", "soils", "omni-unit/soils"),
        ("exit", "landuse", "omni-unit/landuse"),
    ]
