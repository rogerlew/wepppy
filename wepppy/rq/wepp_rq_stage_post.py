from __future__ import annotations

import inspect
import logging
import os
import shutil
import time
from glob import glob
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from pathlib import Path
from typing import Optional

from rq import get_current_job

from wepppy.export.prep_details import (
    export_channels_prep_details,
    export_hillslopes_prep_details,
)
from wepppy.io_wait import wait_for_path, wait_for_paths
from wepppy.nodb.core import Climate, ClimateMode, Wepp
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.query_engine.activate import activate_query_engine
from wepppy.wepp.interchange import (
    cleanup_hillslope_sources_for_completed_interchange,
    generate_interchange_documentation,
    run_wepp_hillslope_interchange,
    run_wepp_watershed_interchange,
    run_wepp_watershed_tc_out_interchange,
)
from wepppy.wepp.interchange.dss_dates import parse_dss_date
from wepppy.weppcloud.utils.helpers import get_wd

from . import wepp_rq_dss as _dss_helpers

_cleanup_dss_export_dir = _dss_helpers._cleanup_dss_export_dir
_copy_dss_readme = _dss_helpers._copy_dss_readme
_write_dss_channel_geojson = _dss_helpers._write_dss_channel_geojson
_LOGGER = logging.getLogger(__name__)


def _delete_after_interchange_enabled(*, wepp: object, climate: object) -> bool:
    value = getattr(wepp, "delete_after_interchange", None)
    if value is None:
        value = getattr(climate, "delete_after_interchange", False)
    return bool(value)


def _post_run_cleanup_out_rq(runid: str) -> None:
    """Move WEPP .out files into output directories once runs finish."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')

        climate = Climate.getInstance(wd)
        wepp = Wepp.getInstance(wd)
        if climate.climate_mode == ClimateMode.SingleStormBatch:
            for d in climate.ss_batch_storms:
                ss_batch_key = d['ss_batch_key']

                wepp.logger.info('    moving .out files...')
                for fn in glob(_join(wepp.runs_dir, '*.out')):
                    dst_path = _join(wepp.output_dir, ss_batch_key, _split(fn)[1])
                    shutil.move(fn, dst_path)

        else:
            wepp.logger.info('    moving .out files...')
            for fn in glob(_join(wepp.runs_dir, '*.out')):
                dst_path = _join(wepp.output_dir, _split(fn)[1])
                shutil.move(fn, dst_path)

        tc_src = _join(wepp.runs_dir, 'tc_out.txt')
        if _exists(tc_src):
            tc_dst = _join(wepp.output_dir, 'tc_out.txt')
            wepp.logger.info('    moving tc_out.txt...')
            shutil.move(tc_src, tc_dst)
            if _exists(tc_dst):
                run_wepp_watershed_tc_out_interchange(
                    wepp.output_dir,
                    delete_after_interchange=wepp.delete_after_interchange,
                )

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq_stage_post.py:81", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _analyze_return_periods_rq(runid: str) -> None:
    """Generate return period summaries for the completed hillslope runs."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        output_dir = Path(wepp.output_dir)
        interchange_dir = output_dir / "interchange"
        ebe_path = interchange_dir / "ebe_pw0.parquet"
        alt_ebe = output_dir / "ebe_pw0.parquet"
        if not ebe_path.exists() and alt_ebe.exists():
            ebe_path = alt_ebe
        tot_path = interchange_dir / "totalwatsed3.parquet"
        wait_for_paths(
            [ebe_path, tot_path],
            timeout_s=60.0,
            require_stable_size=True,
            logger=wepp.logger,
        )
        wepp.export_return_periods_tsv_summary(meoization=True)
        wepp.export_return_periods_tsv_summary(meoization=True, extraneous=True)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq_stage_post.py:111", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _build_hillslope_interchange_rq(runid: str) -> None:
    """Create hillslope interchange parquet artifacts for downstream tools."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        climate = Climate.getInstance(wd)
        wepp = Wepp.getInstance(wd)
        delete_after_interchange = _delete_after_interchange_enabled(
            wepp=wepp,
            climate=climate,
        )
        # Watershed routing may still need H*.dat files. Defer deletion until
        # post-watershed interchange when watershed runs are enabled.
        if bool(getattr(wepp, "run_wepp_watershed", False)):
            delete_after_interchange = False
        start_year = climate.calendar_start_year
        is_single_storm = climate.is_single_storm
        # Single storm runs don't produce .loss.dat, .soil.dat, or .wat.dat files
        run_wepp_hillslope_interchange(
            _join(wd, 'wepp/output'),
            start_year=start_year,
            run_loss_interchange=not is_single_storm,
            run_soil_interchange=not is_single_storm,
            run_wat_interchange=not is_single_storm,
            delete_after_interchange=delete_after_interchange,
        )
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq_stage_post.py:138", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _build_totalwatsed3_rq(runid: str) -> None:
    """Generate the aggregate watershed TotWatSed interchange dataset."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        interchange_dir = Path(wepp.output_dir) / "interchange"
        wait_for_paths(
            [interchange_dir / "H.pass.parquet", interchange_dir / "H.wat.parquet"],
            timeout_s=60.0,
            require_stable_size=True,
            logger=wepp.logger,
        )
        wepp._build_totalwatsed3()
        totalwatsed3_path = interchange_dir / "totalwatsed3.parquet"
        wait_for_path(
            totalwatsed3_path,
            timeout_s=60.0,
            require_stable_size=True,
            logger=wepp.logger,
        )
        # Refresh README after totalwatsed3 is materialized so documentation always
        # reflects the latest derived dataset set.
        generate_interchange_documentation(interchange_dir)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq_stage_post.py:161", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _run_hillslope_watbal_rq(runid: str) -> None:
    """Compute water balance metrics once hillslope interchange data exists."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wat_file = _join(wd, 'wepp/output/interchange/H.wat.parquet')
        wait_for_path(wat_file, timeout_s=60.0, require_stable_size=True)
        wepp = Wepp.getInstance(wd)
        wepp._run_hillslope_watbal()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq_stage_post.py:179", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _post_prep_details_rq(runid: str) -> None:
    """Export prep detail CSVs/Parquets after runs complete."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        export_channels_prep_details(wd)
        export_hillslopes_prep_details(wd)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq_stage_post.py:195", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _post_watershed_interchange_rq(runid: str) -> None:
    """Generate watershed interchange artifacts and documentation."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        climate = Climate.getInstance(wd)
        wepp = Wepp.getInstance(wd)
        delete_after_interchange = _delete_after_interchange_enabled(
            wepp=wepp,
            climate=climate,
        )
        start_year = climate.calendar_start_year
        run_soil_interchange = not climate.is_single_storm
        run_chnwb_interchange = not climate.is_single_storm
        output_dir = Path(wepp.output_dir)
        timeout_s = 60.0
        poll_s = 0.5

        def _wait_for_output(filename: str, *, allow_gzip: bool = False) -> Path:
            path = output_dir / filename
            gz_path = path.with_suffix(path.suffix + ".gz") if allow_gzip else None
            deadline = time.monotonic() + timeout_s
            while True:
                if path.exists():
                    wait_for_path(
                        path,
                        timeout_s=timeout_s,
                        poll_s=poll_s,
                        require_stable_size=True,
                        logger=wepp.logger,
                    )
                    return path
                if allow_gzip and gz_path is not None and gz_path.exists():
                    wait_for_path(
                        gz_path,
                        timeout_s=timeout_s,
                        poll_s=poll_s,
                        require_stable_size=True,
                        logger=wepp.logger,
                    )
                    return gz_path
                if time.monotonic() >= deadline:
                    if allow_gzip and gz_path is not None:
                        raise FileNotFoundError(
                            f"Expected file {path} (or {gz_path}) to be available within {timeout_s:.2f}s"
                        )
                    raise FileNotFoundError(
                        f"Expected file {path} to be available within {timeout_s:.2f}s"
                    )
                time.sleep(poll_s)

        _wait_for_output("pass_pw0.txt", allow_gzip=True)
        _wait_for_output("ebe_pw0.txt")
        _wait_for_output("loss_pw0.txt")
        _wait_for_output("chan.out")
        _wait_for_output("chanwb.out")
        if run_chnwb_interchange:
            _wait_for_output("chnwb.txt")
        if run_soil_interchange:
            _wait_for_output("soil_pw0.txt", allow_gzip=True)
        run_wepp_watershed_interchange(
            output_dir,
            start_year=start_year,
            run_soil_interchange=run_soil_interchange,
            run_chnwb_interchange=run_chnwb_interchange,
            delete_after_interchange=delete_after_interchange,
        )
        if delete_after_interchange:
            cleanup_hillslope_sources_for_completed_interchange(
                output_dir,
                run_loss_interchange=not climate.is_single_storm,
                run_soil_interchange=run_soil_interchange,
                run_wat_interchange=not climate.is_single_storm,
            )
        generate_interchange_documentation(_join(wd, 'wepp/output/interchange'))
        activate_query_engine(wd, run_interchange=False, force_refresh=True)
        StatusMessenger.publish(status_channel, f'rq:{job.id} ACTIVATED query_engine({runid})')
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq_stage_post.py:271", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _post_legacy_arc_export_rq(runid: str) -> None:
    """Rebuild the legacy Arc-compatible export bundle when requested."""
    try:
        from wepppy.export import legacy_arc_export

        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        legacy_arc_export(wd)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq_stage_post.py:288", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _post_gpkg_export_rq(runid: str) -> None:
    """Rebuild the GeoPackage export bundle when requested."""
    try:
        from wepppy.export.gpkg_export import gpkg_export

        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        gpkg_export(wd)
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq_stage_post.py:305", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def post_dss_export_rq(runid: str) -> None:
    """Build DSS exports once hillslope interchange data is ready."""
    try:
        from wepppy.wepp.interchange import (
            archive_dss_export_zip,
            chanout_dss_export,
            totalwatsed_partitioned_dss_export,
        )

        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:dss_export'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        export_channel_ids = wepp.dss_export_channel_ids
        channel_filter: Optional[list[int]] = export_channel_ids if export_channel_ids else None
        start_date = parse_dss_date(wepp.dss_start_date)
        end_date = parse_dss_date(wepp.dss_end_date)
        dss_export_dir = Path(wd) / "export" / "dss"

        StatusMessenger.publish(status_channel, 'cleaning up previous DSS export directory...')
        _cleanup_dss_export_dir(wd)
        dss_export_zip = _join(wd, 'export/dss.zip')
        if _exists(dss_export_zip):
            if status_channel is not None:
                StatusMessenger.publish(status_channel, 'removing export/dss.zip\n')
            os.remove(dss_export_zip)

        StatusMessenger.publish(status_channel, 'writing DSS channel geojson + boundary GMLs...')
        _write_dss_channel_geojson(wd, channel_filter)

        dss_channels_path = dss_export_dir / "dss_channels.geojson"
        if dss_channels_path.exists():
            wait_for_path(
                dss_channels_path,
                timeout_s=60.0,
                require_stable_size=True,
                logger=wepp.logger,
            )
        StatusMessenger.publish(status_channel, 'generating partitioned DSS export...')
        totalwatsed_partitioned_dss_export(
            wd,
            channel_filter,
            status_channel=status_channel,
            start_date=start_date,
            end_date=end_date,
        )
        totalwatsed_exports = sorted(dss_export_dir.glob("totalwatsed3_chan_*.dss"))
        if totalwatsed_exports:
            wait_for_paths(
                totalwatsed_exports,
                timeout_s=60.0,
                require_stable_size=True,
                logger=wepp.logger,
            )
        StatusMessenger.publish(status_channel, 'generating channel outlet DSS export...')
        chanout_dss_export(
            wd,
            status_channel=status_channel,
            start_date=start_date,
            end_date=end_date,
        )
        chanout_exports = sorted(dss_export_dir.glob("peak_chan_*.dss"))
        if chanout_exports:
            wait_for_paths(
                chanout_exports,
                timeout_s=60.0,
                require_stable_size=True,
                logger=wepp.logger,
            )
        _copy_dss_readme(wd, status_channel=status_channel)
        readme_path = dss_export_dir / "README.dss_export.md"
        if readme_path.exists():
            wait_for_path(
                readme_path,
                timeout_s=60.0,
                require_stable_size=True,
                logger=wepp.logger,
            )
        StatusMessenger.publish(status_channel, 'archiving DSS export zip...')
        archive_dss_export_zip(wd, status_channel=status_channel)
        dss_export_zip = Path(wd) / "export" / "dss.zip"
        wait_for_path(
            dss_export_zip,
            timeout_s=60.0,
            require_stable_size=True,
            logger=wepp.logger,
        )

        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')

        try:
            prep = RedisPrep.getInstance(wd)
            prep.timestamp(TaskEnum.dss_export)
        except FileNotFoundError:
            _LOGGER.info(
                "Skipping dss_export prep timestamp for %s: RedisPrep is unavailable",
                runid,
            )

        StatusMessenger.publish(status_channel, f'rq:{job.id} TRIGGER   dss_export DSS_EXPORT_TASK_COMPLETED')

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq_stage_post.py:413", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise


def _post_make_loss_grid_rq(runid: str) -> None:
    """Generate raster loss grids once watershed outputs are available."""
    try:
        job = get_current_job()
        wd = get_wd(runid)
        func_name = inspect.currentframe().f_code.co_name
        status_channel = f'{runid}:wepp'
        StatusMessenger.publish(status_channel, f'rq:{job.id} STARTED {func_name}({runid})')
        wepp = Wepp.getInstance(wd)
        wepp.make_loss_grid()
        StatusMessenger.publish(status_channel, f'rq:{job.id} COMPLETED {func_name}({runid})')
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/rq/wepp_rq_stage_post.py:429", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        StatusMessenger.publish(status_channel, f'rq:{job.id} EXCEPTION {func_name}({runid})')
        raise
