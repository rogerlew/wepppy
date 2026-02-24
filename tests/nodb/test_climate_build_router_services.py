from __future__ import annotations

import logging
import shutil
from contextlib import contextmanager
from pathlib import Path

import pytest

from wepppy.nodb.core.climate import ClimateMode, ClimateSpatialMode
from wepppy.nodb.core.climate_build_router import ClimateBuildRouter
from wepppy.nodb.core.climate_mode_build_services import ClimateModeBuildServices

pytestmark = pytest.mark.unit


class _DummyWatershed:
    def __init__(self, is_abstracted: bool = True) -> None:
        self.is_abstracted = is_abstracted
        self.centroid = (-116.2, 43.6)


class _DummyClimate:
    def __init__(self, tmp_path: Path) -> None:
        self.wd = str(tmp_path)
        self.logger = logging.getLogger("tests.nodb.climate.router")
        self._locked = False
        self.cli_dir = str(tmp_path / "cli")
        Path(self.cli_dir).mkdir(parents=True, exist_ok=True)
        (Path(self.cli_dir) / "stale.txt").write_text("old")

        self.cli_fn = "old.cli"
        self.par_fn = "old.par"
        self.sub_cli_fns = {"1": "a.cli"}
        self.sub_par_fns = {"1": "a.par"}

        self.watershed_instance = _DummyWatershed(is_abstracted=True)
        self.climatestation = "STA-1"
        self.orig_cli_fn = None
        self.climate_mode = ClimateMode.PRISM
        self.climate_spatialmode = ClimateSpatialMode.Single

        self.closest_calls = 0
        self.triggers: list[object] = []

    def islocked(self):
        return self._locked

    @contextmanager
    def locked(self):
        assert not self._locked
        self._locked = True
        yield
        self._locked = False

    def find_closest_stations(self):
        self.closest_calls += 1
        self.climatestation = "AUTO"

    def trigger(self, event):
        self.triggers.append(event)


class _DummyModeService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def validate_mode_spatial_compatibility(self, climate):
        self.calls.append(("validate_mode", climate.climate_mode))

    def build_for_mode(self, climate, *, verbose=False, attrs=None):
        self.calls.append(("build_mode", climate.climate_mode, verbose, attrs))
        assert climate.cli_fn is None
        assert climate.par_fn is None


class _DummyScalingService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def validate_scaling_inputs(self, climate):
        self.calls.append("validate")

    def apply_scaling(self, climate):
        self.calls.append("apply")


class _DummyArtifactService:
    def __init__(self) -> None:
        self.calls = 0

    def export_post_build_artifacts(self, climate):
        self.calls += 1


def test_build_router_runs_orchestration_and_timestamps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _DummyClimate(tmp_path)
    mode_service = _DummyModeService()
    scaling_service = _DummyScalingService()
    artifact_service = _DummyArtifactService()

    class _Prep:
        def __init__(self) -> None:
            self.calls = 0

        def timestamp(self, _task) -> None:
            self.calls += 1

    prep = _Prep()
    monkeypatch.setattr(
        "wepppy.nodb.core.climate_build_router.RedisPrep.getInstance",
        lambda _wd: prep,
    )

    router = ClimateBuildRouter(
        mode_build_services=mode_service,
        scaling_service=scaling_service,
        artifact_export_service=artifact_service,
    )

    router.build(climate, verbose=True, attrs={"k": "v"})

    assert not (Path(climate.cli_dir) / "stale.txt").exists()
    assert mode_service.calls[0] == ("validate_mode", ClimateMode.PRISM)
    assert mode_service.calls[1] == ("build_mode", ClimateMode.PRISM, True, {"k": "v"})
    assert scaling_service.calls == ["validate", "apply"]
    assert artifact_service.calls == 1
    assert prep.calls == 1
    assert climate.triggers, "expected CLIMATE_BUILD_COMPLETE trigger"


def test_build_router_raises_for_undefined_mode(tmp_path: Path) -> None:
    climate = _DummyClimate(tmp_path)
    climate.climate_mode = ClimateMode.Undefined

    router = ClimateBuildRouter(
        mode_build_services=_DummyModeService(),
        scaling_service=_DummyScalingService(),
        artifact_export_service=_DummyArtifactService(),
    )

    with pytest.raises(Exception):
        router.build(climate)


def test_build_router_preserves_managed_projection_cli_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _DummyClimate(tmp_path)
    cli_root = tmp_path / "cli"
    if cli_root.is_symlink():
        cli_root.unlink()
    elif cli_root.exists():
        shutil.rmtree(cli_root)
    managed_target = tmp_path / ".nodir" / "upper" / "climate" / "token" / "data"
    managed_target.mkdir(parents=True, exist_ok=True)
    (managed_target / "stale.cli").write_text("old")
    cli_root.symlink_to(managed_target, target_is_directory=True)

    monkeypatch.setattr(
        "wepppy.nodb.core.climate_build_router.RedisPrep.getInstance",
        lambda _wd: (_ for _ in ()).throw(FileNotFoundError()),
    )

    router = ClimateBuildRouter(
        mode_build_services=_DummyModeService(),
        scaling_service=_DummyScalingService(),
        artifact_export_service=_DummyArtifactService(),
    )
    router.build(climate)

    assert cli_root.is_symlink()
    assert managed_target.is_dir()
    assert list(managed_target.iterdir()) == []


def test_build_router_unlinks_unmanaged_cli_symlink_without_deleting_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    climate = _DummyClimate(tmp_path)
    cli_root = tmp_path / "cli"
    if cli_root.is_symlink():
        cli_root.unlink()
    elif cli_root.exists():
        shutil.rmtree(cli_root)
    external_target = tmp_path / "external-cli"
    external_target.mkdir(parents=True, exist_ok=True)
    external_file = external_target / "stale.cli"
    external_file.write_text("old")
    cli_root.symlink_to(external_target, target_is_directory=True)

    monkeypatch.setattr(
        "wepppy.nodb.core.climate_build_router.RedisPrep.getInstance",
        lambda _wd: (_ for _ in ()).throw(FileNotFoundError()),
    )

    router = ClimateBuildRouter(
        mode_build_services=_DummyModeService(),
        scaling_service=_DummyScalingService(),
        artifact_export_service=_DummyArtifactService(),
    )
    router.build(climate)

    assert not cli_root.is_symlink()
    assert cli_root.is_dir()
    assert external_file.exists()


def _mode_service_climate(mode: ClimateMode, spatial_mode: ClimateSpatialMode):
    class _ModeClimate:
        def __init__(self):
            self.climate_mode = mode
            self.climate_spatialmode = spatial_mode
            self.orig_cli_fn = "/tmp/orig.cli"
            self.calls: list[str] = []

        def _build_climate_vanilla(self, **_kwargs):
            self.calls.append("vanilla")

        def _build_climate_observed_daymet(self, **_kwargs):
            self.calls.append("observed_daymet")

        def _build_climate_observed_daymet_multiple(self, **_kwargs):
            self.calls.append("observed_daymet_multiple")

        def _build_climate_future(self, **_kwargs):
            self.calls.append("future")

        def _build_climate_single_storm(self, **_kwargs):
            self.calls.append("single")

        def _build_climate_single_storm_batch(self, **_kwargs):
            self.calls.append("single_batch")

        def _build_climate_prism(self, **_kwargs):
            self.calls.append("prism")

        def _build_climate_depnexrad(self, **_kwargs):
            self.calls.append("depnexrad")

        def _post_defined_climate(self, **_kwargs):
            self.calls.append("post_defined")

        def _build_climate_mod(self, mod_function, **_kwargs):
            self.calls.append(f"mod:{mod_function.__name__}")

        def _build_climate_observed_gridmet(self, **_kwargs):
            self.calls.append("gridmet")

        def _build_climate_observed_gridmet_multiple(self, **_kwargs):
            self.calls.append("gridmet_multiple")

        def _prism_revision(self, **_kwargs):
            self.calls.append("prism_revision")

    return _ModeClimate()


@pytest.mark.parametrize(
    "mode,spatial_mode,expected",
    [
        (ClimateMode.Vanilla, ClimateSpatialMode.Single, ["vanilla"]),
        (ClimateMode.PRISM, ClimateSpatialMode.Multiple, ["prism", "prism_revision"]),
        (
            ClimateMode.ObservedPRISM,
            ClimateSpatialMode.MultipleInterpolated,
            ["observed_daymet_multiple"],
        ),
        (ClimateMode.GridMetPRISM, ClimateSpatialMode.Single, ["gridmet"]),
    ],
)
def test_mode_build_services_route_expected_builders(
    mode: ClimateMode,
    spatial_mode: ClimateSpatialMode,
    expected: list[str],
) -> None:
    service = ClimateModeBuildServices()
    climate = _mode_service_climate(mode, spatial_mode)

    service.validate_mode_spatial_compatibility(climate)
    service.build_for_mode(climate)

    assert climate.calls == expected


def test_mode_build_services_reject_unsupported_multiple_interpolated_mode() -> None:
    service = ClimateModeBuildServices()
    climate = _mode_service_climate(ClimateMode.PRISM, ClimateSpatialMode.MultipleInterpolated)

    with pytest.raises(ValueError):
        service.validate_mode_spatial_compatibility(climate)
