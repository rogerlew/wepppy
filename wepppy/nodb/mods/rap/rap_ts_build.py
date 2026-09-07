"""RAP time-series collection and explicit derived-state finalization."""

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from wepppy.nodb._derived_build import file_signature, finalize, publish_files, require_output_directory

__all__ = ["acquire", "analyze"]


def _years(start, end) -> tuple[int, int]:
    values = []
    for value in (start, end):
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise ValueError("RAP start and end years must be integer years")
        values.append(int(value))
    if values[1] < values[0]:
        raise ValueError("RAP end year must be greater than or equal to start year")
    return tuple(values)


def _inputs(controller, *, analysis=False) -> dict[str, Any]:
    """Copy settings plus (year, (resolved path, mtime_ns, size)) raster inputs."""
    from . import rap_ts as module

    map_obj = module.Ron.getInstance(controller.wd).map
    require_output_directory(controller.rap_dir, controller.wd)
    inputs = {
        "years": (controller.rap_start_year, controller.rap_end_year),
        "extent": tuple(map_obj.extent), "cellsize": map_obj.cellsize,
        "rap_dir": str(Path(controller.rap_dir).resolve()),
    }
    if analysis:
        start, end = _years(*inputs["years"])
        manager = controller._rap_mgr
        if manager is None:
            raise RuntimeError("RAP rasters must be acquired before analysis")
        watershed = module.Watershed.getInstance(controller.wd)
        multi = controller.multi_ofe
        inputs.update(
            multi_ofe=multi, subwta=file_signature(watershed.subwta),
            mofe_map=file_signature(watershed.mofe_map) if multi else None,
            bands=(module.RAP_Band.ANNUAL_FORB_AND_GRASS, module.RAP_Band.BARE_GROUND,
                   module.RAP_Band.LITTER, module.RAP_Band.PERENNIAL_FORB_AND_GRASS,
                   module.RAP_Band.SHRUB, module.RAP_Band.TREE),
            manager=(str(Path(manager.wd).resolve()), tuple(manager.bbox),
                     manager.cellsize, manager.version),
        )
        rasters = []
        for year in range(start, end + 1):
            filename = manager.ds.get(str(year), manager.ds.get(year))
            if filename is None:
                raise FileNotFoundError(f"RAP raster for {year} is missing; acquire rasters first")
            path = Path(filename).resolve()
            if not path.is_relative_to(inputs["rap_dir"]):
                raise ValueError(f"RAP raster for {year} is outside the run RAP directory")
            rasters.append((year, file_signature(path)))
        inputs["rasters"] = tuple(rasters)
    return inputs


def _check_inputs(controller, snapshot, *, analysis=False):
    try:
        current = _inputs(controller, analysis=analysis)
    except (ValueError, TypeError, FileNotFoundError) as exc:
        raise RuntimeError("RAP build superseded by changed or malformed inputs") from exc
    if snapshot != current:
        raise RuntimeError("RAP build superseded by changed inputs")


def _completed(futures, logger):
    pending = set(futures)
    count = 0
    while pending:
        done, pending = wait(pending, timeout=60, return_when=FIRST_COMPLETED)
        if not done:
            logger.warning("RAP work still running after 60 seconds; continuing to wait")
        for future in done:
            try:
                result = future.result()
            except Exception:  # broad-except: cancel peer futures and propagate backend task failure
                # Worker boundary: remote/raster tasks can raise backend-specific errors.
                for remaining in pending:
                    remaining.cancel()
                logger.exception("RAP collection failed: %s", futures[future])
                raise
            count += 1
            logger.info("RAP %s complete (%s/%s)", futures[future], count, len(futures))
            yield result


def acquire(controller, start_year=None, end_year=None) -> None:
    from . import rap_ts as module

    snapshot = _inputs(controller)
    start, end = _years(
        start_year if start_year is not None else snapshot["years"][0],
        end_year if end_year is not None else snapshot["years"][1],
    )
    with TemporaryDirectory(prefix=".rap-acquire-", dir=controller.rap_dir) as stage:
        manager = module.RangelandAnalysisPlatformV3(
            wd=stage, bbox=snapshot["extent"], cellsize=snapshot["cellsize"]
        )

        def retrieve(year):
            controller.logger.info("RAP retrieving year %s", year)
            retries = manager.retrieve([year])
            if retries:
                controller.logger.info("RAP year %s retrieval retries: %s", year, retries)
            return retries

        with ThreadPoolExecutor() as pool:
            futures = {pool.submit(retrieve, year): f"acquisition year {year}"
                       for year in range(start, end + 1)}
            for _ in _completed(futures, controller.logger):
                pass
        # Normalize legacy integer dataset keys and retain manager georeferencing.
        datasets = {}
        for year in range(start, end + 1):
            filename = manager.ds.get(str(year), manager.ds.get(year))
            if filename is None or not Path(filename).is_file():
                raise FileNotFoundError(f"RAP retrieval did not produce a raster for {year}")
            if Path(filename).resolve().parent != Path(stage).resolve():
                raise ValueError("RAP retrieval returned an artifact outside its staging directory")
            datasets[str(year)] = str(Path(controller.rap_dir) / Path(filename).name)
        with finalize(controller) as publications:
            _check_inputs(controller, snapshot)
            publications.enter_context(publish_files(stage, controller.rap_dir, controller))
            manager.wd = controller.rap_dir
            manager.ds = datasets
            controller._rap_start_year = start
            controller._rap_end_year = end
            controller._rap_mgr = manager
    module.update_catalog_entry(controller.wd, controller.rap_dir)


def analyze(controller, *, verbose=False) -> None:
    from . import rap_ts as module

    snapshot = _inputs(controller, analysis=True)

    def analyze_band_year(year, signature, band):
        if verbose:
            print(year, band)
        controller.logger.info("RAP analyzing year %s band %s", year, band.name)
        kwargs = dict(key_fn=snapshot["subwta"][0], parameter_fn=signature[0], band_indx=band.value)
        if snapshot["multi_ofe"]:
            values = module.identify_median_intersecting_raster_keys(
                key2_fn=snapshot["mofe_map"][0], **kwargs
            )
        else:
            values = module.identify_median_single_raster_key(**kwargs)
        return year, band, values

    data = {}
    with ThreadPoolExecutor() as pool:
        futures = {pool.submit(analyze_band_year, year, signature, band):
                   f"analysis year {year} band {band.name}"
                   for year, signature in snapshot["rasters"] for band in snapshot["bands"]}
        for year, band, values in _completed(futures, controller.logger):
            data.setdefault(band, {})[year] = values

    records = []
    for band, years in data.items():
        for year, values in years.items():
            for topaz_id, value in values.items():
                ofes = value.items() if snapshot["multi_ofe"] else [(-1, value)]
                for mofe_id, cover in ofes:
                    records.append((band.value, int(year), int(topaz_id), int(mofe_id), cover))
    frame = module.pd.DataFrame(records, columns=["band", "year", "topaz_id", "mofe_id", "value"])
    # An empty valid summary replaces old data with a typed empty parquet.
    if frame.empty:
        frame = frame.astype({"band": "int64", "year": "int64", "topaz_id": "int64",
                              "mofe_id": "int64", "value": "float64"})
    with TemporaryDirectory(prefix=".rap-analysis-", dir=controller.rap_dir) as stage:
        frame.to_parquet(Path(stage) / "rap_ts.parquet")
        with finalize(controller) as publications:
            _check_inputs(controller, snapshot, analysis=True)
            publications.enter_context(publish_files(stage, controller.rap_dir, controller))
            controller.data = data
    module.update_catalog_entry(controller.wd, "rap/rap_ts.parquet")
    controller.logger.info("analysis complete...")
    try:
        prep = module.RedisPrep.getInstance(controller.wd)
        prep.timestamp(module.TaskEnum.fetch_rap_ts)
    except FileNotFoundError:
        pass
