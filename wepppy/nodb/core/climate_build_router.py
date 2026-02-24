from __future__ import annotations

import os
import shutil
from os.path import exists as _exists
from typing import TYPE_CHECKING, Any

from wepppy.nodb.base import TriggerEvents
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

from wepppy.nodb.core.climate_artifact_export_service import ClimateArtifactExportService
from wepppy.nodb.core.climate_mode_build_services import ClimateModeBuildServices
from wepppy.nodb.core.climate_scaling_service import ClimateScalingService

if TYPE_CHECKING:
    from wepppy.nodb.core.climate import Climate


def _clear_directory_preserving_symlink_mount(path: str) -> None:
    if not os.path.lexists(path):
        return

    if os.path.islink(path):
        resolved = os.path.realpath(path)
        if not os.path.isdir(resolved):
            raise NotADirectoryError(f"Expected climate root symlink target to be a directory: {path}")
        run_root = os.path.dirname(os.path.abspath(path))
        managed_projection_roots = (
            os.path.join(run_root, ".nodir", "lower", "climate"),
            os.path.join(run_root, ".nodir", "upper", "climate"),
        )

        def _is_managed_projection_target() -> bool:
            for managed_root in managed_projection_roots:
                managed_abs = os.path.abspath(managed_root)
                try:
                    if os.path.commonpath([resolved, managed_abs]) == managed_abs:
                        return True
                except ValueError:
                    continue
            return False

        if not _is_managed_projection_target():
            # Unmanaged symlink: drop only the link and preserve target contents.
            os.unlink(path)
            return

        for name in os.listdir(resolved):
            candidate = os.path.join(resolved, name)
            if os.path.isdir(candidate) and not os.path.islink(candidate):
                shutil.rmtree(candidate)
            else:
                os.unlink(candidate)
        return

    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.unlink(path)


class ClimateBuildRouter:
    """Coordinate full climate builds while keeping ``Climate`` facade stable."""

    def __init__(
        self,
        *,
        mode_build_services: ClimateModeBuildServices | None = None,
        scaling_service: ClimateScalingService | None = None,
        artifact_export_service: ClimateArtifactExportService | None = None,
    ) -> None:
        self._mode_build_services = mode_build_services or ClimateModeBuildServices()
        self._scaling_service = scaling_service or ClimateScalingService()
        self._artifact_export_service = artifact_export_service or ClimateArtifactExportService()

    def build(
        self,
        climate: "Climate",
        *,
        verbose: bool = False,
        attrs: dict[str, Any] | None = None,
    ) -> None:
        from wepppy.nodb.core.climate import ClimateMode, ClimateModeIsUndefinedError, _assert_supported_climate_mode
        from wepppy.nodb.core.watershed import WatershedNotAbstractedError

        climate.logger.info("Build Climates")
        climate.logger.info("  assert not self.islocked()")
        assert not climate.islocked()

        with climate.locked():
            climate.cli_fn = None
            climate.par_fn = None
            climate.sub_cli_fns = None
            climate.sub_par_fns = None

        watershed = climate.watershed_instance
        if not watershed.is_abstracted:
            climate.logger.info("  watershed is not abstracted, raising error")
            raise WatershedNotAbstractedError()

        if climate.climatestation is None and climate.orig_cli_fn is None:
            climate.logger.info("  no climate station selected, assigning closest station")
            climate.find_closest_stations()

        cli_dir = climate.cli_dir
        if _exists(cli_dir) or os.path.lexists(cli_dir):
            climate.logger.info("  cli_dir exists, attempting to clear")
            try:
                _clear_directory_preserving_symlink_mount(cli_dir)
            # Cleanup boundary: stale files should not block a rebuild.
            except OSError:
                climate.logger.warning(
                    "  failed to clear existing cli_dir; continuing rebuild",
                    extra={"cli_dir": cli_dir},
                    exc_info=True,
                )

        if not _exists(cli_dir):
            climate.logger.info("  cli_dir does not exist, creating")
        os.makedirs(cli_dir, exist_ok=True)

        climate_mode = climate.climate_mode
        climate.logger.info(f"  climate_mode: {climate_mode}")
        _assert_supported_climate_mode(climate_mode)

        if climate_mode == ClimateMode.Undefined:
            climate.logger.info("  climate_mode is Undefined, raising error")
            raise ClimateModeIsUndefinedError()

        self._scaling_service.validate_scaling_inputs(climate)
        self._mode_build_services.validate_mode_spatial_compatibility(climate)

        climate.logger.info("  routing by climate_mode")
        self._mode_build_services.build_for_mode(climate, verbose=verbose, attrs=attrs)

        self._scaling_service.apply_scaling(climate)
        self._artifact_export_service.export_post_build_artifacts(climate)

        try:
            climate.logger.info("  timestamping build_climate task")
            prep = RedisPrep.getInstance(climate.wd)
            prep.timestamp(TaskEnum.build_climate)
        except FileNotFoundError:
            climate.logger.info("  RedisPrep not found, skipping timestamp")

        climate.logger.info("Climate Build Successful.")
        climate.trigger(TriggerEvents.CLIMATE_BUILD_COMPLETE)
