"""Bounded finalization for observed GridMET and PRISM hillslope revision."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any

from wepppy.nodb._derived_build import file_signature, finalize, publish_files, require_output_directory
from wepppy.nodb.core.climate_multiple_build import capture_multiple_build_inputs

__all__ = ["run_observed_gridmet_build", "run_prism_revision_build"]


def _require_climate_directory(climate):
    path = Path(climate.cli_dir)
    require_output_directory(path, climate.wd)
    if path.is_symlink():
        roots = [Path(climate.wd).resolve() / ".nodir" / layer / "climate"
                 for layer in ("lower", "upper")]
        if not any(path.resolve().is_relative_to(root) for root in roots):
            raise ValueError("Unmanaged climate directory symlink; rebuild through Climate.build")


def _spatial_inputs(climate, *, prism=False) -> dict[str, Any]:
    """Copy coordinates/settings; source is (resolved path, mtime_ns, size)."""
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
    return inputs


def _check_inputs(climate, climate_inputs, spatial, *, prism=False):
    try:
        current = capture_multiple_build_inputs(climate)
        current_spatial = _spatial_inputs(climate, prism=prism)
    except (ValueError, TypeError, FileNotFoundError) as exc:
        raise RuntimeError("Climate build superseded by changed or malformed inputs") from exc
    if climate_inputs != current or spatial != current_spatial:
        raise RuntimeError("Climate build superseded by changed inputs")


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
    with TemporaryDirectory(prefix=".prism-build-", dir=cli_dir) as stage:
        ppt, tmin, tmax = (str(Path(stage) / name) for name in ("ppt.tif", "tmin.tif", "tmax.tif"))
        helpers._retrieve_prism_revision_tiles(worker, map_obj, ppt, tmin, tmax)
        ppts, tmins, tmaxs = helpers._collect_prism_revision_monthlies(watershed, ppt, tmin, tmax)
        cli = helpers.ClimateFile(snapshot["source"][0])
        with ThreadPoolExecutor(max_workers=helpers.NCPU) as executor:
            futures, par_fns, cli_fns = helpers._submit_prism_revision_futures(
                worker, executor, watershed, cli, stage, ppts, tmaxs, tmins, ppt, tmin, tmax
            )
            helpers._wait_for_prism_revision_futures(worker, futures)
        with finalize(climate) as publications:
            _check_inputs(climate, climate_inputs, snapshot, prism=True)
            publications.enter_context(publish_files(stage, cli_dir, climate))
            climate.sub_par_fns = par_fns
            climate.sub_cli_fns = cli_fns
    helpers.update_catalog_entry(climate.wd, "climate")
