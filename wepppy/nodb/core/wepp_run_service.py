from __future__ import annotations

import inspect
import os
import shutil
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import ExitStack
from glob import glob
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from subprocess import PIPE, Popen
from typing import TYPE_CHECKING, Optional

from wepp_runner.wepp_runner import (
    make_flowpath_run,
    run_flowpath,
    run_hillslope,
    run_ss_batch_hillslope,
    run_ss_batch_watershed,
)

from wepppyo3.wepp_viz import make_soil_loss_grid_fps

from wepppy.all_your_base import NCPU
from wepppy.all_your_base.geo import wgs84_proj4
from wepppy.nodb.redis_prep import TaskEnum

if TYPE_CHECKING:
    from wepppy.nodb.core.wepp import Wepp


class WeppRunService:
    def prep_and_run_flowpaths(self, wepp: "Wepp", clean_after_run: bool = True) -> None:
        from wepppy.nodb.core.wepp import extract_slps_fn
        from wepppy.nodb.core import wepp as wepp_module

        wepp.logger.info("  Prepping _prep_flowpaths... ")

        fp_slps_rels = wepp_module.glob_input_files(
            wepp.wd,
            "watershed/slope_files/flowpaths/*.slps",
            tolerate_mixed=True,
            mixed_prefer="archive",
        )

        flowpath_workers = 10
        if os.getenv("WEPPPY_NCPU"):
            flowpath_workers = min(flowpath_workers, NCPU)

        futures = []
        with ExitStack() as input_paths:
            fp_slps_fns = [
                input_paths.enter_context(
                    wepp_module.with_input_file_path(
                        wepp.wd,
                        rel,
                        purpose="wepp-prep-flowpath-slps",
                        tolerate_mixed=True,
                        mixed_prefer="archive",
                        allow_materialize_fallback=True,
                    )
                )
                for rel in fp_slps_rels
            ]

            with ThreadPoolExecutor(max_workers=flowpath_workers) as pool:
                for fp_slps_fn in fp_slps_fns:
                    futures.append(pool.submit(extract_slps_fn, fp_slps_fn, wepp.fp_runs_dir))

                futures_n = len(futures)
                count = 0
                pending = set(futures)
                while pending:
                    done, pending = wait(pending, timeout=5, return_when=FIRST_COMPLETED)

                    if not done:
                        wepp.logger.error("  Flowpath slope extraction still running after 5 seconds.")
                        continue

                    for future in done:
                        try:
                            future.result()
                            count += 1
                            wepp.logger.info(f"  ({count}/{futures_n}) flowpath slopes prep complete")
                        except Exception as exc:
                            for remaining in pending:
                                remaining.cancel()
                            wepp.logger.error(
                                f"  Flowpath slope extraction failed with an error: {exc}"
                            )
                            raise

        watershed = wepp.watershed_instance
        translator = watershed.translator_factory()
        sim_years = wepp.climate_instance.input_years

        fps_summary = watershed.fps_summary

        futures = []
        with ThreadPoolExecutor(max_workers=flowpath_workers) as pool:
            for topaz_id in fps_summary:
                wepp_id = translator.wepp(top=int(topaz_id))
                for fp_enum in fps_summary[topaz_id]:
                    fp_id = f"fp_{wepp_id}_{fp_enum}"
                    wepp.logger.info(f"  Creating {fp_id}.run... ")
                    futures.append(pool.submit(make_flowpath_run, fp_id, wepp_id, sim_years, wepp.fp_runs_dir))

            futures_n = len(futures)
            count = 0
            pending = set(futures)
            while pending:
                done, pending = wait(pending, timeout=5, return_when=FIRST_COMPLETED)

                if not done:
                    wepp.logger.error("  Flowpath runfile creation still running after 5 seconds.")
                    continue

                for future in done:
                    try:
                        future.result()
                        count += 1
                        wepp.logger.info(f"  ({count}/{futures_n}) flowpath run files complete")
                    except Exception as exc:
                        for remaining in pending:
                            remaining.cancel()
                        wepp.logger.error(f"  Flowpath runfile creation failed with an error: {exc}")
                        raise

        wepp.logger.info("  Running _run_flowpaths... ")

        futures = []
        with ThreadPoolExecutor(max_workers=flowpath_workers) as pool:
            for topaz_id in fps_summary:
                wepp_id = translator.wepp(top=int(topaz_id))
                for fp_enum in fps_summary[topaz_id]:
                    fp_id = f"fp_{wepp_id}_{fp_enum}"
                    wepp.logger.info(f"  Running {fp_id}... ")
                    futures.append(
                        pool.submit(run_flowpath, fp_id, wepp_id, wepp.runs_dir, wepp.fp_runs_dir, wepp.wepp_bin)
                    )

            futures_n = len(futures)
            count = 0
            pending = set(futures)
            while pending:
                done, pending = wait(pending, timeout=60, return_when=FIRST_COMPLETED)

                if not done:
                    wepp.logger.warning(
                        "  Flowpath simulation still running after 60 seconds; continuing to wait."
                    )
                    continue

                for future in done:
                    try:
                        future.result()
                        count += 1
                        wepp.logger.info(f"  ({count}/{futures_n}) flowpaths ran")
                    except Exception as exc:
                        for remaining in pending:
                            remaining.cancel()
                        wepp.logger.error(f"  Flowpath simulation failed with an error: {exc}")
                        raise

        with wepp.timed("  Generating flowpath loss grid"):
            loss_grid_path = _join(wepp.plot_dir, "flowpaths_loss.tif")

            if _exists(loss_grid_path):
                os.remove(loss_grid_path)
                time.sleep(1)

            make_soil_loss_grid_fps(watershed.discha, wepp.fp_runs_dir, loss_grid_path)

            assert _exists(loss_grid_path)

            loss_grid_wgs = _join(wepp.plot_dir, "flowpaths_loss.WGS.tif")

            if _exists(loss_grid_wgs):
                os.remove(loss_grid_wgs)
                time.sleep(1)

            cmd = [
                "gdalwarp",
                "-t_srs",
                wgs84_proj4,
                "-srcnodata",
                "-9999",
                "-dstnodata",
                "-9999",
                "-r",
                "near",
                loss_grid_path,
                loss_grid_wgs,
            ]
            p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            p.wait()

            assert _exists(loss_grid_wgs)

        if clean_after_run:
            wepp.logger.info("  Cleaning up flowpath run files... ")
            shutil.rmtree(wepp.fp_runs_dir)
            shutil.rmtree(wepp.fp_output_dir)

            os.makedirs(wepp.fp_runs_dir)
            os.makedirs(wepp.fp_output_dir)

    def run_hillslopes(
        self,
        wepp: "Wepp",
        man_relpath: str = "",
        cli_relpath: str = "",
        slp_relpath: str = "",
        sol_relpath: str = "",
        max_workers: Optional[int] = None,
    ) -> None:
        from wepppy.nodb.core import wepp as wepp_module

        func_name = inspect.currentframe().f_code.co_name  # type: ignore[union-attr]
        wepp.logger.info(f"{wepp.class_name}.{func_name}()")

        cpu_count = os.cpu_count() or 1
        ncpu_override = os.getenv("WEPPPY_NCPU")
        if max_workers is None:
            max_workers = NCPU if ncpu_override else cpu_count
        if max_workers < 1:
            max_workers = 1
        if ncpu_override:
            if max_workers > NCPU:
                max_workers = NCPU
        elif max_workers > max(cpu_count, 16):
            max_workers = max(cpu_count, 16)

        wepp.logger.info(f"Running Hillslopes with max_workers={max_workers}")
        watershed = wepp.watershed_instance
        translator = watershed.translator_factory()
        climate = wepp.climate_instance
        landuse = wepp.landuse_instance
        runs_dir = os.path.abspath(wepp.runs_dir)
        wepp_bin = wepp.wepp_bin

        wepp.logger.info(f"    wepp_bin:{wepp_bin}")

        sub_n = watershed.sub_n

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = []
            if climate.climate_mode == wepp_module.ClimateMode.SingleStormBatch:
                wepp.logger.info(f"  Submitting {sub_n} hillslope runs to ThreadPoolExecutor - SS batch")
                for i, topaz_id in enumerate(watershed._subs_summary):
                    wepp.logger.info(f"  submitting {topaz_id} to executor")

                    dom = landuse.domlc_d[topaz_id]
                    man = landuse.managements[dom]
                    if man.disturbed_class in ["agriculture crops"]:
                        wepp_bin = "wepp_dcc52a6"
                    wepp.logger.info(f"  using {wepp_bin} for {topaz_id} ({man.disturbed_class})")

                    for d in climate.ss_batch_storms:
                        ss_batch_id = d["ss_batch_id"]
                        wepp_id = translator.wepp(top=int(topaz_id))
                        futures.append(
                            pool.submit(
                                run_ss_batch_hillslope,
                                wepp_id=wepp_id,
                                runs_dir=runs_dir,
                                wepp_bin=wepp_bin,
                                ss_batch_id=ss_batch_id,
                                man_relpath=man_relpath,
                                cli_relpath=cli_relpath,
                                slp_relpath=slp_relpath,
                                sol_relpath=sol_relpath,
                            )
                        )

            else:
                wepp.logger.info(f"  Submitting {sub_n} hillslope runs to ThreadPoolExecutor - no SS batch")
                for i, topaz_id in enumerate(watershed._subs_summary):
                    wepp.logger.info(f"  submitting {topaz_id} to executor")

                    dom = landuse.domlc_d[topaz_id]
                    man = landuse.managements[dom]
                    if man.disturbed_class in ["agriculture crops"]:
                        wepp_bin = "wepp_dcc52a6"
                    wepp.logger.info(f"  using {wepp_bin} for {topaz_id} ({man.disturbed_class})")

                    wepp_id = translator.wepp(top=int(topaz_id))
                    futures.append(
                        pool.submit(
                            run_hillslope,
                            wepp_id=wepp_id,
                            runs_dir=runs_dir,
                            wepp_bin=wepp_bin,
                            man_relpath=man_relpath,
                            cli_relpath=cli_relpath,
                            slp_relpath=slp_relpath,
                            sol_relpath=sol_relpath,
                        )
                    )

            futures_n = len(futures)
            count = 0
            pending = set(futures)
            while pending:
                done, pending = wait(pending, timeout=30, return_when=FIRST_COMPLETED)

                if not done:
                    wepp.logger.warning(
                        "  Hillslope simulations still running after 30 seconds; continuing to wait."
                    )
                    continue

                for future in done:
                    try:
                        status, _id, elapsed_time = future.result()
                        count += 1
                        wepp.logger.info(
                            f"  ({count}/{futures_n})  wepp hillslope {_id} completed in {elapsed_time}s with status={status}"
                        )
                    except Exception as exc:
                        for remaining in pending:
                            remaining.cancel()
                        wepp.logger.error(f"  Hillslope simulation failed with an error: {exc}")
                        raise

        try:
            prep = wepp_module.RedisPrep.getInstance(wepp.wd)
            prep.timestamp(TaskEnum.run_wepp_hillslopes)
        except FileNotFoundError:
            pass

    def run_watershed(self, wepp: "Wepp") -> None:
        from wepppy.export.prep_details import (
            export_channels_prep_details,
            export_hillslopes_prep_details,
        )

        from wepppy.nodb.core import wepp as wepp_module

        if not wepp.run_wepp_watershed:
            wepp.logger.info("Skipping WEPP watershed run (wepp.run_wepp_watershed=False)")
            return
        wd = wepp.wd
        climate = wepp.climate_instance
        wepp_bin = wepp.wepp_bin

        if "wepp_50k" in wepp_bin:
            wepp_bin = "wepp_dcc52a6"

        wepp.logger.info(f"Running Watershed wepp_bin:{wepp.wepp_bin}")
        wepp.logger.info(f"    climate_mode:{climate.climate_mode.name}")
        wepp.logger.info(f"    output_dir:{wepp.output_dir}")
        wepp.logger.info(f"    runs_dir:{wepp.runs_dir}")

        runs_dir = wepp.runs_dir

        if climate.climate_mode == wepp_module.ClimateMode.SingleStormBatch:
            with wepp.timed("  Running watershed ss batch runs"):
                for d in climate.ss_batch_storms:
                    ss_batch_key = d["ss_batch_key"]
                    ss_batch_id = d["ss_batch_id"]
                    run_ss_batch_watershed(runs_dir, wepp_bin, ss_batch_id)

                    wepp.logger.info("    moving .out files...")
                    for fn in glob(_join(wepp.runs_dir, "*.out")):
                        dst_path = _join(wepp.output_dir, ss_batch_key, _split(fn)[1])
                        shutil.move(fn, dst_path)

        else:
            with wepp.timed("  Running watershed run"):
                assert wepp_module.run_watershed(
                    runs_dir, wepp_bin=wepp_bin, status_channel=wepp._status_channel
                )

                wepp.logger.info("    moving .out files...")
                for fn in glob(_join(wepp.runs_dir, "*.out")):
                    dst_path = _join(wepp.output_dir, _split(fn)[1])
                    shutil.move(fn, dst_path)

        if not wepp.is_omni_contrasts_run:
            wepp.logger.info("  Not omni contrasts run, running post processing... ")

            if wepp.prep_details_on_run_completion:
                with wepp.timed("  Exporting prep details"):
                    export_channels_prep_details(wd)
                    export_hillslopes_prep_details(wd)

            climate = wepp.climate_instance

            if not climate.is_single_storm:
                with wepp.timed("  running totalwatsed3"):
                    wepp._build_totalwatsed3()

                with wepp.timed("  running hillslope_watbal"):
                    wepp._run_hillslope_watbal()

                if wepp.legacy_arc_export_on_run_completion:
                    with wepp.timed("  running legacy_arc_export"):
                        from wepppy.export import legacy_arc_export

                        legacy_arc_export(wepp.wd)

            with wepp.timed("  generating loss report"):
                _ = wepp.loss_report

            if wepp.arc_export_on_run_completion:
                with wepp.timed("  running gpkg_export"):
                    from wepppy.export.gpkg_export import gpkg_export

                    gpkg_export(wepp.wd)

                    wepp.make_loss_grid()

        wepp.logger.info("Watershed Run Complete")

        try:
            prep = wepp_module.RedisPrep.getInstance(wepp.wd)
            prep.timestamp(TaskEnum.run_wepp_watershed)
        except FileNotFoundError:
            pass

        from wepppy.wepp.interchange.interchange_documentation import (
            generate_interchange_documentation,
        )
        from wepppy.wepp.interchange.watershed_interchange import run_wepp_watershed_interchange

        climate = wepp.climate_instance.getInstance(wepp.wd)
        start_year = climate.calendar_start_year
        is_single_storm = climate.is_single_storm

        output_options = getattr(wepp, "_contrast_output_options", None)
        if wepp.is_omni_contrasts_run and isinstance(output_options, dict):
            run_ebe_interchange = bool(output_options.get("ebe_pw0", True))
            run_chan_out_interchange = bool(output_options.get("chan_out", False))
            run_chnwb_interchange = bool(output_options.get("chnwb", False)) and not is_single_storm
            run_soil_interchange = bool(output_options.get("soil_pw0", False)) and not is_single_storm
        else:
            run_ebe_interchange = True
            run_chan_out_interchange = True
            run_chnwb_interchange = not is_single_storm
            run_soil_interchange = not is_single_storm

        run_wepp_watershed_interchange(
            wepp.output_dir,
            start_year=start_year,
            run_ebe_interchange=run_ebe_interchange,
            run_chan_out_interchange=run_chan_out_interchange,
            run_soil_interchange=run_soil_interchange,
            run_chnwb_interchange=run_chnwb_interchange,
            delete_after_interchange=wepp.delete_after_interchange,
        )
        generate_interchange_documentation(wepp.wepp_interchange_dir)
