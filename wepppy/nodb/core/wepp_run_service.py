from __future__ import annotations

import inspect
import os
from pathlib import Path
import shutil
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from glob import glob
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from wepp_runner.wepp_runner import (
    run_hillslope,
    run_ss_batch_hillslope,
    run_ss_batch_watershed,
)

from wepppy.all_your_base import NCPU
from wepppy.nodb.redis_prep import TaskEnum

if TYPE_CHECKING:
    from wepppy.nodb.core.wepp import Wepp


_CONTINUOUS_HILLSLOPE_TIMEOUT_S = 60
_MOFE_CONTINUOUS_HILLSLOPE_TIMEOUT_S = 300


def _continuous_hillslope_timeout_s(*, multi_ofe: bool) -> int:
    if multi_ofe:
        return _MOFE_CONTINUOUS_HILLSLOPE_TIMEOUT_S

    return _CONTINUOUS_HILLSLOPE_TIMEOUT_S


class WeppRunService:
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

        watershed = wepp.watershed_instance
        translator = watershed.translator_factory()
        climate = wepp.climate_instance
        landuse = wepp.landuse_instance
        runs_dir = os.path.abspath(wepp.runs_dir)
        # Preserve the configured binary for the entire run; do not mutate it per hillslope.
        configured_wepp_bin = wepp.wepp_bin

        wepp.logger.info(f"    wepp_bin:{configured_wepp_bin}")

        sub_n = watershed.sub_n
        multi_ofe = bool(getattr(wepp, "multi_ofe", False))
        hillslope_timeout_s = _continuous_hillslope_timeout_s(multi_ofe=multi_ofe)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = []
            if climate.climate_mode == wepp_module.ClimateMode.SingleStormBatch:
                wepp.logger.info(f"Running Hillslopes with max_workers={max_workers}")
                wepp.logger.info(f"  Submitting {sub_n} hillslope runs to ThreadPoolExecutor - SS batch")
                for i, topaz_id in enumerate(watershed._subs_summary):
                    wepp.logger.info(f"  submitting {topaz_id} to executor")

                    dom = landuse.domlc_d[topaz_id]
                    man = landuse.managements[dom]
                    wepp.logger.info(
                        f"  using {configured_wepp_bin} for {topaz_id} ({man.disturbed_class})"
                    )

                    for d in climate.ss_batch_storms:
                        ss_batch_id = d["ss_batch_id"]
                        wepp_id = translator.wepp(top=int(topaz_id))
                        futures.append(
                            pool.submit(
                                run_ss_batch_hillslope,
                                wepp_id=wepp_id,
                                runs_dir=runs_dir,
                                wepp_bin=configured_wepp_bin,
                                ss_batch_id=ss_batch_id,
                                man_relpath=man_relpath,
                                cli_relpath=cli_relpath,
                                slp_relpath=slp_relpath,
                                sol_relpath=sol_relpath,
                            )
                        )

            else:
                wepp.logger.info(
                    f"Running Hillslopes with max_workers={max_workers}, timeout={hillslope_timeout_s}s"
                )
                wepp.logger.info(f"  Submitting {sub_n} hillslope runs to ThreadPoolExecutor - no SS batch")
                for i, topaz_id in enumerate(watershed._subs_summary):
                    wepp.logger.info(f"  submitting {topaz_id} to executor")

                    dom = landuse.domlc_d[topaz_id]
                    man = landuse.managements[dom]
                    wepp.logger.info(
                        f"  using {configured_wepp_bin} for {topaz_id} ({man.disturbed_class})"
                    )

                    wepp_id = translator.wepp(top=int(topaz_id))
                    futures.append(
                        pool.submit(
                            run_hillslope,
                            wepp_id=wepp_id,
                            runs_dir=runs_dir,
                            wepp_bin=configured_wepp_bin,
                            man_relpath=man_relpath,
                            cli_relpath=cli_relpath,
                            slp_relpath=slp_relpath,
                            sol_relpath=sol_relpath,
                            timeout=hillslope_timeout_s,
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
        from wepppy.nodb.core import wepp as wepp_module
        from wepppy.nodb.mods.features_export.service import (
            execute_features_export,
            publish_profile_execution_artifacts,
            resolve_published_profile_request,
        )

        def _run_published_features_export_profile(
            profile: str,
            *,
            format_override: str | None = None,
        ) -> dict[str, object]:
            canonical_profile, payload = resolve_published_profile_request(
                profile,
                format_override=format_override,
            )
            runid_token = str(getattr(wepp, "runid", Path(wd).name))
            config_token = str(getattr(wepp, "config", "run_completion"))
            job_id = f"sync-{canonical_profile}-{uuid4().hex}"
            result = execute_features_export(
                wd,
                runid=runid_token,
                config=config_token,
                payload=payload,
                job_id=job_id,
            )
            publish_profile_execution_artifacts(
                wd,
                requested_profile=canonical_profile,
                job_id=job_id,
                job_result=result,
            )
            return result

        if not wepp.run_wepp_watershed:
            wepp.logger.info("Skipping WEPP watershed run (wepp.run_wepp_watershed=False)")
            return
        wd = wepp.wd
        climate = wepp.climate_instance
        configured_wepp_bin = wepp.wepp_bin

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
                    run_ss_batch_watershed(runs_dir, configured_wepp_bin, ss_batch_id)

                    wepp.logger.info("    moving .out files...")
                    for fn in glob(_join(wepp.runs_dir, "*.out")):
                        dst_path = _join(wepp.output_dir, ss_batch_key, _split(fn)[1])
                        shutil.move(fn, dst_path)

        else:
            with wepp.timed("  Running watershed run"):
                assert wepp_module.run_watershed(
                    runs_dir, wepp_bin=configured_wepp_bin, status_channel=wepp._status_channel
                )

                wepp.logger.info("    moving .out files...")
                for fn in glob(_join(wepp.runs_dir, "*.out")):
                    dst_path = _join(wepp.output_dir, _split(fn)[1])
                    shutil.move(fn, dst_path)

        if not wepp.is_omni_contrasts_run:
            wepp.logger.info("  Not omni contrasts run, running post processing... ")

            if wepp.prep_details_on_run_completion:
                with wepp.timed("  Exporting prep details"):
                    _run_published_features_export_profile("prep-details")

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
                with wepp.timed("  running features_export prep-wepp-gpkg-gdb profile"):
                    _run_published_features_export_profile("prep-wepp-gpkg-gdb")

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
            pass_family=wepp.pass_family,
            start_year=start_year,
            run_ebe_interchange=run_ebe_interchange,
            run_chan_out_interchange=run_chan_out_interchange,
            run_soil_interchange=run_soil_interchange,
            run_chnwb_interchange=run_chnwb_interchange,
            delete_after_interchange=wepp.delete_after_interchange,
        )
        generate_interchange_documentation(wepp.wepp_interchange_dir)
