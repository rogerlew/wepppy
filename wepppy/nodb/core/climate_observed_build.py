"""Bounded finalization for observed Daymet, GridMET, and PRISM revision."""

from concurrent.futures import ThreadPoolExecutor
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any

from wepppy.nodb._derived_build import file_signature, finalize, publish_files, require_output_directory
from wepppy.nodb.core.climate_multiple_build import capture_multiple_build_inputs

__all__ = ["run_observed_daymet_build", "run_observed_gridmet_build", "run_prism_revision_build"]


def _require_climate_directory(climate):
    path = Path(climate.cli_dir)
    require_output_directory(path, climate.wd)
    if path.is_symlink():
        roots = [Path(climate.wd).resolve() / ".nodir" / layer / "climate"
                 for layer in ("lower", "upper")]
        if not any(path.resolve().is_relative_to(root) for root in roots):
            raise ValueError("Unmanaged climate directory symlink; rebuild through Climate.build")


def _spatial_inputs(climate, *, prism=False) -> dict[str, Any]:
    """Copy coordinates/settings; source is (resolved path, mtime_ns, size, sha256)."""
    watershed = climate.watershed_instance
    inputs = {"centroid": tuple(watershed.require_centroid())}
    if prism:
        map_obj = climate.ron_instance.map
        inputs.update(
            extent=tuple(map_obj.extent), cellsize=map_obj.cellsize,
            hillslopes=tuple(
                (topaz_id, tuple(watershed.hillslope_centroid_lnglat(topaz_id)))
                for topaz_id, _ in watershed.centroid_hillslope_iter()
            ),
            wmesque_version=climate.wmesque_version,
            wmesque_endpoint=climate.wmesque_endpoint,
            source=file_signature(climate.cli_path),
            climate_mode=climate.climate_mode,
            climate_spatialmode=climate.climate_spatialmode,
        )
    if prism:
        from wepppy.nodb.core.climate import ClimateMode
        if climate.climate_mode == ClimateMode.Prism800m:
            inputs["raw_prism"] = file_signature(Path(climate.cli_dir) / "prism800m-source-ws.parquet")
    return inputs


def _check_inputs(climate, climate_inputs, spatial, *, prism=False):
    try:
        current = capture_multiple_build_inputs(climate)
        current_spatial = _spatial_inputs(climate, prism=prism)
    except (ValueError, TypeError, FileNotFoundError) as exc:
        raise RuntimeError("Climate build superseded by changed or malformed inputs") from exc
    if climate_inputs != current or spatial != current_spatial:
        raise RuntimeError("Climate build superseded by changed inputs")



def _write_attempt_status(stage, kind, snapshot, state):
    """Keep a visible, bounded description of working or failed computation."""
    status = {
        "kind": kind, "state": state,
        "observed_start_year": snapshot.observed_start_year,
        "observed_end_year": snapshot.observed_end_year,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    temporary = Path(stage) / "build-status.json.tmp"
    temporary.write_text(json.dumps(status, sort_keys=True) + "\n")
    temporary.replace(Path(stage) / "build-status.json")


def _publish_retained_attempt(publications, stage, destination, climate, *, remove=()):
    # publish_files consumes its staging files. Publish redundant copies so a
    # precommit rollback cannot destroy the only inspectable attempted output.
    publish_stage = publications.enter_context(TemporaryDirectory(
        prefix=".climate-publish-", dir=destination,
    ))
    for source in Path(stage).iterdir():
        if source.name != "build-status.json":
            shutil.copy2(source, Path(publish_stage) / source.name, follow_symlinks=False)
    publications.enter_context(publish_files(publish_stage, destination, climate, remove=remove))

def run_observed_daymet_build(climate, *, verbose=False, attrs=None, replace_existing=False) -> None:
    from wepppy.nodb.core import climate as module

    climate.set_attrs(attrs)
    snapshot = capture_multiple_build_inputs(climate)
    assert snapshot.observed_end_year <= climate.daymet_last_available_year, snapshot.observed_end_year
    spatial = _spatial_inputs(climate)
    _require_climate_directory(climate)
    Path(snapshot.cli_dir).mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="daymet-build-", dir=snapshot.cli_dir, delete=False) as stage:
        completed = False
        try:
            _write_attempt_status(stage, "daymet", snapshot, "working")
            station = module.CligenStationsManager(version=snapshot.cligen_db).get_station_fromid(
                snapshot.climatestation
            )
            cligen = module.Cligen(station, wd=stage)
            lng, lat = spatial["centroid"]
            module.build_observed_daymet(
                cligen, lng, lat, snapshot.observed_start_year, snapshot.observed_end_year,
                stage, "ws.prn", "wepp.cli",
                gridmet_wind=snapshot.use_gridmet_wind_when_applicable,
                adjust_mx_pt5=snapshot.adjust_mx_pt5,
                silent_pass_observed_quality_guard=snapshot.silent_pass_observed_quality_guard,
                randseed=snapshot.cligen_seed,
            )
            monthlies = module.ClimateFile(str(Path(stage) / "wepp.cli")).calc_monthlies()
            bypassed = bool(getattr(cligen, "_last_observed_quality_guard_bypassed", False))
            with finalize(climate) as publications:
                _check_inputs(climate, snapshot, spatial)
                obsolete = [path.name for path in Path(snapshot.cli_dir).iterdir()
                            if replace_existing and path.is_file() and not path.name.startswith(".")]
                _publish_retained_attempt(publications, stage, snapshot.cli_dir, climate, remove=obsolete)
                climate._observed_start_year = snapshot.observed_start_year
                climate._observed_end_year = snapshot.observed_end_year
                climate._input_years = snapshot.observed_end_year - snapshot.observed_start_year + 1
                climate.monthlies = monthlies
                climate.cli_fn = "wepp.cli"
                climate.par_fn = station.par
                if replace_existing:
                    climate.sub_cli_fns = None
                    climate.sub_par_fns = None
                    climate._observed_quality_guard_summary_warning = None
                climate._publish_quality_guard_bypass_warning_if_needed(quality_guard_bypassed=bypassed)
            completed = True
        finally:
            if completed:
                shutil.rmtree(stage)
            else:
                try:
                    _write_attempt_status(stage, "daymet", snapshot, "failed")
                except OSError:
                    climate.logger.exception("Unable to update retained Daymet attempt status at %s", stage)
                climate.logger.error("Daymet build failed; artifacts retained at %s", stage)


def run_observed_gridmet_build(climate, *, verbose=False, attrs=None) -> None:
    from wepppy.nodb.core import climate as module

    climate.set_attrs(attrs)
    snapshot = capture_multiple_build_inputs(climate)
    spatial = _spatial_inputs(climate)
    _require_climate_directory(climate)
    Path(snapshot.cli_dir).mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".gridmet-build-", dir=snapshot.cli_dir) as stage:
        station = module.CligenStationsManager(version=snapshot.cligen_db).get_station_fromid(
            snapshot.climatestation
        )
        cligen = module.Cligen(station, wd=stage)
        lng, lat = spatial["centroid"]
        module.build_observed_gridmet(
            cligen, lng, lat, snapshot.observed_start_year, snapshot.observed_end_year,
            stage, "ws.prn", "wepp.cli", adjust_mx_pt5=snapshot.adjust_mx_pt5,
            silent_pass_observed_quality_guard=snapshot.silent_pass_observed_quality_guard,
            randseed=snapshot.cligen_seed,
        )
        monthlies = module.ClimateFile(str(Path(stage) / "wepp.cli")).calc_monthlies()
        bypassed = bool(getattr(cligen, "_last_observed_quality_guard_bypassed", False))
        with finalize(climate) as publications:
            _check_inputs(climate, snapshot, spatial)
            obsolete = [path.name for path in Path(snapshot.cli_dir).iterdir()
                        if path.is_file() and not path.name.startswith(".")]
            publications.enter_context(publish_files(stage, snapshot.cli_dir, climate, remove=obsolete))
            climate._observed_start_year = snapshot.observed_start_year
            climate._observed_end_year = snapshot.observed_end_year
            climate._input_years = snapshot.observed_end_year - snapshot.observed_start_year + 1
            climate.monthlies = monthlies
            climate.cli_fn = "wepp.cli"
            climate.par_fn = station.par
            climate.sub_cli_fns = None
            climate.sub_par_fns = None
            climate._observed_quality_guard_summary_warning = None
            climate._publish_quality_guard_bypass_warning_if_needed(quality_guard_bypassed=bypassed)


def run_prism_revision_build(climate, *, verbose=False) -> None:
    from wepppy.nodb.core import climate_build_helpers as helpers
    from wepppy.nodb.core.climate import ClimateMode

    retain_attempt = climate.climate_mode in (ClimateMode.Observed, ClimateMode.ObservedPRISM, ClimateMode.Prism800m)

    snapshot = _spatial_inputs(climate, prism=True)
    climate_inputs = capture_multiple_build_inputs(climate)
    cli_dir = climate.cli_dir
    _require_climate_directory(climate)
    # The existing numeric helpers consume a read-only view of captured inputs.
    worker = SimpleNamespace(
        logger=climate.logger, wmesque_version=snapshot["wmesque_version"],
        wmesque_endpoint=snapshot["wmesque_endpoint"],
    )
    hillslopes = dict(snapshot["hillslopes"])
    watershed = SimpleNamespace(
        centroid=snapshot["centroid"],
        centroid_hillslope_iter=lambda: iter(snapshot["hillslopes"]),
        hillslope_centroid_lnglat=hillslopes.__getitem__,
    )
    map_obj = SimpleNamespace(extent=snapshot["extent"], cellsize=snapshot["cellsize"])
    with TemporaryDirectory(
        prefix=("prism800m-build-revision-" if climate.climate_mode == ClimateMode.Prism800m
                else "prism-build-" if retain_attempt else ".prism-build-"),
        dir=cli_dir, delete=not retain_attempt,
    ) as stage:
        completed = False
        try:
            if retain_attempt:
                _write_attempt_status(stage, "prism", climate_inputs, "working")
            ppt, tmin, tmax = (str(Path(stage) / name) for name in ("ppt.tif", "tmin.tif", "tmax.tif"))
            helpers._retrieve_prism_revision_tiles(worker, map_obj, ppt, tmin, tmax)
            ppts, tmins, tmaxs = helpers._collect_prism_revision_monthlies(watershed, ppt, tmin, tmax)
            cli = helpers.ClimateFile(snapshot["source"][0])
            with ThreadPoolExecutor(max_workers=helpers.NCPU) as executor:
                futures, par_fns, cli_fns = helpers._submit_prism_revision_futures(
                    worker, executor, watershed, cli, stage, ppts, tmaxs, tmins, ppt, tmin, tmax
                )
                helpers._wait_for_prism_revision_futures(worker, futures)
            if climate.climate_mode == ClimateMode.Prism800m:
                import pandas as pd
                from wepppy.climates.prism.wepp_adapter import floor_dewpoint
                shutil.copy2(snapshot["raw_prism"][0], Path(stage) / "prism800m-source-ws.parquet")
                raw = pd.read_parquet(Path(stage) / "prism800m-source-ws.parquet")
                for filename in cli_fns.values():
                    floor_dewpoint(Path(stage) / filename, raw.tdmean,
                                   Path(stage) / (filename + "-dewpoint.csv"))
            with finalize(climate) as publications:
                _check_inputs(climate, climate_inputs, snapshot, prism=True)
                if retain_attempt:
                    _publish_retained_attempt(publications, stage, cli_dir, climate)
                else:
                    publications.enter_context(publish_files(stage, cli_dir, climate))
                climate.sub_par_fns = par_fns
                climate.sub_cli_fns = cli_fns
            completed = True
        finally:
            if retain_attempt:
                if completed:
                    if climate.climate_mode == ClimateMode.Prism800m:
                        try:
                            _write_attempt_status(stage, "prism800m-revision", climate_inputs, "complete")
                        except OSError:
                            climate.logger.exception("Unable to record completed PRISM revision: %s", stage)
                    else:
                        shutil.rmtree(stage)
                else:
                    try:
                        _write_attempt_status(stage, "prism", climate_inputs, "failed")
                    except OSError:
                        climate.logger.exception("Unable to update retained PRISM attempt status at %s", stage)
                    climate.logger.error("PRISM revision failed; artifacts retained at %s", stage)
    helpers.update_catalog_entry(climate.wd, "climate")
