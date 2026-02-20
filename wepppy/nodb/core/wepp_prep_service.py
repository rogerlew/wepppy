from __future__ import annotations

import inspect
import os
import shutil
import time
from concurrent.futures import FIRST_COMPLETED, wait
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from wepp_runner.wepp_runner import (
    make_hillslope_run,
    make_ss_batch_hillslope_run,
    make_ss_hillslope_run,
)

from wepppy.all_your_base import NCPU, isfloat
from wepppy.all_your_base.geo import RDIOutOfBoundsException, RasterDatasetInterpolator
from wepppy.nodb.base import TriggerEvents, createProcessPoolExecutor

if TYPE_CHECKING:
    from wepppy.nodb.core.wepp import Wepp


class WeppPrepService:
    def prep_hillslopes(
        self,
        wepp: "Wepp",
        frost: Optional[bool] = None,
        baseflow: Optional[bool] = None,
        wepp_ui: Optional[bool] = None,
        pmet: Optional[bool] = None,
        snow: Optional[bool] = None,
        man_relpath: str = "",
        cli_relpath: str = "",
        slp_relpath: str = "",
        sol_relpath: str = "",
        max_workers: Optional[int] = None,
    ) -> None:
        from wepppy.nodb.core import wepp as wepp_module

        func_name = inspect.currentframe().f_code.co_name  # type: ignore[union-attr]
        wepp.logger.info(
            f"{wepp.class_name}.{func_name}(frost={frost}, baseflow={baseflow}, "
            f"wepp_ui={wepp_ui}, pmet={pmet}, snow={snow}, man_relpath={man_relpath}, "
            f"cli_relpath={cli_relpath}, slp_relpath={slp_relpath}, sol_relpath={sol_relpath})"
        )

        watershed = wepp.watershed_instance
        translator = watershed.translator_factory()

        reveg = False
        disturbed = wepp_module.Disturbed.getInstance(wepp.wd, allow_nonexistent=True)
        if disturbed is not None:
            if disturbed.sol_ver == 9005.0:
                reveg = True

        if wepp.multi_ofe:
            wepp._prep_multi_ofe(translator)
        else:
            if slp_relpath == "":
                wepp._prep_slopes(translator, watershed.clip_hillslopes, watershed.clip_hillslope_length)
            wepp._prep_managements(translator)
            wepp._prep_soils(translator, max_workers=max_workers)

        if cli_relpath == "":
            wepp._prep_climates(translator)

        wepp._make_hillslope_runs(
            translator,
            reveg=reveg,
            man_relpath=man_relpath,
            cli_relpath=cli_relpath,
            slp_relpath=slp_relpath,
            sol_relpath=sol_relpath,
        )

        if (frost is None and wepp.run_frost) or frost:
            wepp._prep_frost()
        else:
            wepp._remove_frost()

        wepp._check_and_set_phosphorus_map()
        wepp._prep_phosphorus()

        if (baseflow is None and wepp.run_baseflow) or baseflow:
            wepp._check_and_set_baseflow_map()
            wepp._prep_baseflow()
        else:
            wepp._remove_baseflow()

        if (wepp_ui is None and wepp.run_wepp_ui) or wepp_ui:
            wepp._prep_wepp_ui()
        else:
            wepp._remove_wepp_ui()

        if (pmet is None and wepp.run_pmet) or pmet:
            wepp._prep_pmet()
        else:
            wepp._remove_pmet()

        if (snow is None and wepp.run_snow) or snow:
            wepp._prep_snow()
        else:
            wepp._remove_snow()

        if reveg:
            wepp._prep_revegetation()

    def prep_managements(self, wepp: "Wepp", translator: Any) -> None:
        from wepppy.nodb.core import wepp as wepp_module

        wepp.logger.info("    _prep_managements... ")
        from wepppy.nodb.mods import RAP_TS

        wd = wepp.wd

        landuse = wepp.landuse_instance
        hillslope_cancovs = landuse.hillslope_cancovs

        climate = wepp.climate_instance
        soils = wepp.soils_instance
        disturbed = wepp_module.Disturbed.tryGetInstance(wd)
        if disturbed is not None:
            _land_soil_replacements_d = disturbed.land_soil_replacements_d
        else:
            _land_soil_replacements_d = None

        rap_ts = RAP_TS.tryGetInstance(wd)

        years = climate.input_years
        year0 = climate.year0

        runs_dir = wepp.runs_dir
        bd_d = soils.bd_d

        build_d = {}
        soil_texture_d = {}

        for i, (topaz_id, mukey) in enumerate(soils.domsoil_d.items()):
            if (int(topaz_id) - 4) % 10 == 0:
                continue
            dom = landuse.domlc_d[topaz_id]

            wepp.logger.info(f"    _prep_managements:{topaz_id}:{mukey} - {dom}... ")

            man_summary = landuse.managements[dom]

            wepp_id = translator.wepp(top=int(topaz_id))
            dst_fn = os.path.join(runs_dir, "p%i.man" % wepp_id)

            meoization_key = (mukey, dom)
            if disturbed:
                disturbed_class = man_summary.disturbed_class
                meoization_key = (mukey, dom, disturbed_class)

            if rap_ts is not None:
                meoization_key = (topaz_id, mukey, dom)

            if meoization_key in build_d:
                shutil.copyfile(build_d[meoization_key], dst_fn)

                wepp.logger.info(f"     copying build_d['{meoization_key}'] -> {dst_fn}")

            else:
                management = None
                if hasattr(man_summary, "get_management"):
                    try:
                        management = man_summary.get_management()
                    except FileNotFoundError:
                        management = None

                if management is None and all(
                    hasattr(man_summary, attr) for attr in ("man_fn", "key", "desc", "color")
                ):
                    man_src = wepp_module.materialize_input_file(
                        wd,
                        f"landuse/{man_summary.man_fn}",
                        purpose="wepp-prep-managements",
                    )
                    management = wepp_module.Management.load(
                        key=man_summary.key,
                        man_fn=Path(man_src).name,
                        man_dir=str(Path(man_src).parent),
                        desc=man_summary.desc,
                        color=man_summary.color,
                    )

                    cancov_override = getattr(man_summary, "cancov_override", None)
                    inrcov_override = getattr(man_summary, "inrcov_override", None)
                    rilcov_override = getattr(man_summary, "rilcov_override", None)

                    if (
                        cancov_override is not None
                        or inrcov_override is not None
                        or rilcov_override is not None
                    ):
                        for ini in getattr(management, "inis", []):
                            if getattr(ini, "landuse", None) != 1:
                                continue
                            data = getattr(ini, "data", None)
                            if data is None:
                                continue

                            if cancov_override is not None and hasattr(data, "cancov"):
                                data.cancov = cancov_override
                            if inrcov_override is not None and hasattr(data, "inrcov"):
                                data.inrcov = inrcov_override
                            if rilcov_override is not None and hasattr(data, "rilcov"):
                                data.rilcov = rilcov_override

                        if cancov_override is not None:
                            for plant in getattr(management, "plants", []):
                                plant_data = getattr(plant, "data", None)
                                if plant_data is not None and hasattr(plant_data, "xmxlai"):
                                    plant_data.xmxlai *= cancov_override

                if management is None:
                    raise AttributeError(
                        "Management summary must expose get_management() or "
                        "man_fn/key/desc/color attributes"
                    )

                sol_key = soils.domsoil_d[topaz_id]
                management.set_bdtill(bd_d[sol_key])

                if disturbed is not None:
                    disturbed_class_str = disturbed_class if isinstance(disturbed_class, str) else ""
                    if isinstance(disturbed_class, str):
                        if "mulch" in disturbed_class:
                            disturbed_class = "mulch"
                        elif "thinning" in disturbed_class:
                            disturbed_class = "thinning"
                        disturbed_class_str = disturbed_class

                    if (
                        hillslope_cancovs is not None
                        and "mulch" not in disturbed_class_str
                        and "thinning" not in disturbed_class_str
                    ):
                        assert rap_ts is None, "project has rap and rap_ts"
                        management.set_cancov(hillslope_cancovs[str(topaz_id)])

                    if mukey in soil_texture_d:
                        clay, sand = soil_texture_d[mukey]
                    else:
                        clay = None
                        sand = None
                        _soil = soils.soils.get(mukey)

                        soil_fname = getattr(_soil, "fname", None) if _soil is not None else None
                        if isinstance(soil_fname, str) and soil_fname:
                            try:
                                soil_src = wepp_module.materialize_input_file(
                                    wd,
                                    f"soils/{soil_fname}",
                                    purpose="wepp-prep-managements-soil-texture",
                                )
                                soilu = wepp_module.WeppSoilUtil(soil_src)
                                clay = soilu.clay
                                sand = soilu.sand
                            except Exception as exc:
                                wepp.logger.debug(
                                    "     _prep_managements: archive soil texture read failed for mukey=%s, fname=%s: %s",
                                    mukey,
                                    soil_fname,
                                    exc,
                                    exc_info=True,
                                )

                        if not (isfloat(clay) and isfloat(sand)) and _soil is not None:
                            try:
                                clay = _soil.clay
                                sand = _soil.sand
                            except Exception as exc:
                                wepp.logger.warning(
                                    "     _prep_managements: unable to resolve soil texture for mukey=%s; "
                                    "skipping texture-based disturbed overrides (%s)",
                                    mukey,
                                    exc,
                                )
                                clay = None
                                sand = None

                        soil_texture_d[mukey] = (clay, sand)

                    texid = None
                    replacements = None
                    if isfloat(clay) and isfloat(sand):
                        texid = wepp_module.simple_texture(clay=clay, sand=sand)
                        key = (texid, disturbed_class)
                        replacements = _land_soil_replacements_d.get(key)

                    if replacements is None:
                        wepp.logger.info(
                            f"     _prep_managements: {texid}:{disturbed_class} not in replacements_d"
                        )

                    if disturbed_class is None or disturbed_class == "" or ("developed" in disturbed_class_str):
                        rdmax = None
                        xmxlai = None
                    elif replacements is None:
                        rdmax = None
                        xmxlai = None
                    else:
                        rdmax = replacements.get("rdmax", None)
                        if man_summary.cancov_override is None:
                            xmxlai = replacements.get("xmxlai", None)
                        else:
                            rdmax = None
                            xmxlai = None

                    if isfloat(rdmax):
                        management.set_rdmax(float(rdmax))

                    if isfloat(xmxlai):
                        management.set_xmxlai(float(xmxlai))

                    if replacements is not None:
                        wepp_module.apply_disturbed_management_overrides(
                            management,
                            replacements,
                        )

                    meoization_key = (mukey, dom, disturbed_class)

                if rap_ts is not None:
                    apply_rap_ts_cover = True
                    if disturbed is not None:
                        disturbed_class_lc = (
                            disturbed_class.lower().strip() if isinstance(disturbed_class, str) else ""
                        )
                        apply_rap_ts_cover = disturbed_class_lc in {"forest", "shrub", "tall grass"}

                    if apply_rap_ts_cover and year0 >= rap_ts.rap_start_year and year0 <= rap_ts.rap_end_year:
                        cover = rap_ts.get_cover(topaz_id, year0, fallback=True)
                        management.set_cancov(cover)

                multi = management.build_multiple_year_man(years)

                fn_contents = str(multi)

                with open(dst_fn, "w") as fp:
                    fp.write(fn_contents)

                build_d[meoization_key] = dst_fn
                wepp.logger.info(f"     meoization_key: {meoization_key} -> {dst_fn}")

        if "emapr_ts" in wepp.mods:
            wepp.logger.info("    _prep_managements:emapr_ts.analyze... ")
            from wepppy.nodb.mods import OSUeMapR_TS

            assert climate.observed_start_year is not None
            assert climate.observed_end_year is not None

            emapr_ts = OSUeMapR_TS.getInstance(wd)
            emapr_ts.acquire_rasters(
                start_year=climate.observed_start_year,
                end_year=climate.observed_end_year,
            )
            emapr_ts.analyze()

    def prep_soils(self, wepp: "Wepp", translator: Any, max_workers: Optional[int] = None) -> None:
        from wepppy.nodb.core.wepp import prep_soil
        from wepppy.nodb.core import wepp as wepp_module

        func_name = inspect.currentframe().f_code.co_name  # type: ignore[union-attr]
        wepp.logger.info(f"{wepp.class_name}.{func_name}(translator={translator})")

        cpu_count = os.cpu_count() or 1
        ncpu_override = os.getenv("WEPPPY_NCPU")
        if max_workers is None:
            max_workers = NCPU if ncpu_override else cpu_count

        if max_workers < 1:
            max_workers = 1
        if ncpu_override:
            if max_workers > NCPU:
                max_workers = NCPU
        elif max_workers > max(cpu_count, 20):
            max_workers = max(cpu_count, 20)

        wepp.logger.info(f"  Using max_workers={max_workers} for soil prep")

        soils = wepp.soils_instance
        watershed = wepp.watershed_instance
        runs_dir = wepp.runs_dir
        kslast = wepp.kslast
        clip_soils = soils.clip_soils
        clip_soils_depth = soils.clip_soils_depth
        initial_sat = soils.initial_sat

        kslast_map_fn = wepp.kslast_map
        kslast_map = RasterDatasetInterpolator(kslast_map_fn) if kslast_map_fn is not None else None

        task_args_list = []
        for topaz_id, soil in soils.sub_iter():
            wepp_id = translator.wepp(top=int(topaz_id))
            src_fn = wepp_module.materialize_input_file(
                wepp.wd,
                f"soils/{soil.fname}",
                purpose="wepp-prep-soils",
            )
            dst_fn = os.path.join(runs_dir, f"p{wepp_id}.sol")

            _kslast = None
            modify_kslast_pars = None

            if kslast_map is not None:
                lng, lat = watershed.hillslope_centroid_lnglat(topaz_id)
                try:
                    sampled_kslast = kslast_map.get_location_info(lng, lat, method="nearest")
                except RDIOutOfBoundsException:
                    sampled_kslast = None

                if isfloat(sampled_kslast) and float(sampled_kslast) > 0.0:
                    _kslast = float(sampled_kslast)
                    modify_kslast_pars = dict(
                        map_fn=kslast_map_fn,
                        lng=lng,
                        lat=lat,
                        map_value=_kslast,
                    )
                elif kslast is not None:
                    _kslast = kslast
            elif kslast is not None:
                _kslast = kslast

            task_args_list.append(
                (
                    topaz_id,
                    src_fn,
                    dst_fn,
                    _kslast,
                    modify_kslast_pars,
                    initial_sat,
                    clip_soils,
                    clip_soils_depth,
                )
            )

        if not task_args_list:
            wepp.logger.info("  No soils require preparation.")
            return

        run_concurrent = 1

        def _run_soil_prep_pool(prefer_spawn: bool):
            try:
                with createProcessPoolExecutor(
                    max_workers=max_workers,
                    logger=wepp.logger,
                    prefer_spawn=prefer_spawn,
                ) as executor:
                    futures = [executor.submit(prep_soil, args) for args in task_args_list]

                    futures_n = len(futures)
                    count = 0
                    pending_futures = set(futures)
                    last_progress_time = time.time()

                    while pending_futures:
                        done, pending_futures = wait(
                            pending_futures, timeout=5, return_when=FIRST_COMPLETED
                        )

                        if not done:
                            since_progress = time.time() - last_progress_time
                            pending_count = len(pending_futures)

                            if since_progress >= 60:
                                wepp.logger.error(
                                    "  Soil prep tasks still pending after %.1fs; %s tasks waiting.",
                                    round(since_progress, 1),
                                    pending_count,
                                )
                            else:
                                wepp.logger.info(
                                    "  Waiting on soil prep tasks (pending=%s, %.1fs since last completion).",
                                    pending_count,
                                    round(since_progress, 1),
                                )
                            continue

                        for future in done:
                            try:
                                topaz_id, elapsed_time = future.result()
                                count += 1
                                wepp.logger.info(
                                    f"  ({count}/{futures_n}) Completed soil prep for {topaz_id} in {elapsed_time}s"
                                )
                                last_progress_time = time.time()
                            except BrokenProcessPool as exc:
                                wepp.logger.error(
                                    "  Soil prep process pool terminated unexpectedly: %s", exc
                                )
                                for pending_future in pending_futures:
                                    pending_future.cancel()
                                return False, exc
                            except Exception as exc:
                                wepp.logger.error(f"  A soil prep task failed with an error: {exc}")
                                for pending_future in pending_futures:
                                    pending_future.cancel()
                                return False, exc

                    return True, None
            except BrokenProcessPool as exc:
                wepp.logger.error("  Failed to initialize soil prep process pool: %s", exc)
                return False, exc
            except Exception as exc:
                wepp.logger.error("  Unexpected error during soil prep pool execution: %s", exc)
                return False, exc

        def _run_soil_prep_sequential():
            total = len(task_args_list)
            wepp.logger.warning("  Running soil prep sequentially")
            for idx, task_args in enumerate(task_args_list, start=1):
                topaz_id, elapsed_time = prep_soil(task_args)
                wepp.logger.info(
                    f"  ({idx}/{total}) Completed soil prep for {topaz_id} in {elapsed_time}s [sequential]"
                )

        wepp.logger.info(f"  run_concurrent={run_concurrent}")
        if run_concurrent:
            wepp.logger.info("  Submitting soils for `prep_soil` to ProcessPoolExecutor")
            success, failure_exc = _run_soil_prep_pool(prefer_spawn=True)

            if not success and isinstance(failure_exc, BrokenProcessPool):
                wepp.logger.warning("  Retrying soil prep with fork-based executor after spawn failure")
                success, failure_exc = _run_soil_prep_pool(prefer_spawn=False)

            if not success:
                if isinstance(failure_exc, BrokenProcessPool):
                    wepp.logger.warning(
                        "  Falling back to sequential soil prep after process pool failures"
                    )
                    _run_soil_prep_sequential()
                else:
                    raise failure_exc
        else:
            _run_soil_prep_sequential()

    def prep_climates(self, wepp: "Wepp", translator: Any) -> None:
        from wepppy.nodb.core import wepp as wepp_module

        func_name = inspect.currentframe().f_code.co_name  # type: ignore[union-attr]
        wepp.logger.info(f"{wepp.class_name}.{func_name}(translator={translator})")

        climate = wepp.climate_instance
        if climate.climate_mode == wepp_module.ClimateMode.SingleStormBatch:
            wepp.logger.info("    _prep_climates_ss_batch... ")
            return self.prep_climates_ss_batch(wepp, translator)

        if not climate.has_climate:
            started = time.time()
            last_log_time = 0.0

            unlocked_grace_seconds = 30.0
            locked_wait_seconds = 30.0 * 60.0

            while True:
                climate = wepp.climate_instance
                if climate.has_climate:
                    break

                now = time.time()
                locked = False
                try:
                    locked = climate.islocked()
                except Exception:
                    locked = False

                waited = now - started
                if locked:
                    if waited > locked_wait_seconds:
                        break
                else:
                    if waited > unlocked_grace_seconds:
                        break

                if now - last_log_time > 15.0:
                    wepp.logger.info(
                        "    Waiting for climate build to complete (locked=%s, waited=%.0fs)",
                        locked,
                        waited,
                    )
                    last_log_time = now

                time.sleep(2)

            if not climate.has_climate:
                raise ValueError(
                    "Climate inputs are not ready. Build/upload climate (and wait for it to finish) "
                    "before running WEPP."
                )

        watershed = wepp.watershed_instance
        runs_dir = wepp.runs_dir

        sub_n = watershed.sub_n
        count = 0
        for topaz_id in watershed._subs_summary:
            wepp_id = translator.wepp(top=int(topaz_id))
            dst_fn = os.path.join(runs_dir, "p%i.cli" % wepp_id)

            cli_summary = climate.sub_summary(topaz_id)
            if cli_summary is None or cli_summary.get("cli_fn") in (None, ""):
                raise ValueError(
                    f"Climate inputs are missing for topaz_id={topaz_id}. "
                    "Build/upload climate (and wait for it to finish) before running WEPP."
                )
            src_rel = f"climate/{cli_summary['cli_fn']}"
            wepp_module.copy_input_file(wepp.wd, src_rel, dst_fn)
            count += 1
            wepp.logger.info(f" ({count}/{sub_n}) topaz_id: {topaz_id} | {src_rel} -> {dst_fn}")

    def prep_climates_ss_batch(self, wepp: "Wepp", translator: Any) -> None:
        from wepppy.nodb.core import wepp as wepp_module

        climate = wepp.climate_instance

        wepp.logger.info("    _prep_climates_ss_batch... ")
        watershed = wepp.watershed_instance
        runs_dir = wepp.runs_dir

        for d in climate.ss_batch_storms:
            ss_batch_id = d["ss_batch_id"]
            ss_batch_key = d["ss_batch_key"]
            cli_fn = d["cli_fn"]

            for topaz_id in watershed._subs_summary:
                wepp.logger.info(f"    _prep_climates:{topaz_id}... ")

                wepp_id = translator.wepp(top=int(topaz_id))
                dst_fn = os.path.join(runs_dir, f"p{wepp_id}.{ss_batch_id}.cli")

                src_rel = f"climate/{cli_fn}"
                wepp_module.copy_input_file(wepp.wd, src_rel, dst_fn)

            dst_fn = os.path.join(runs_dir, f"pw0.{ss_batch_id}.cli")
            src_rel = f"climate/{cli_fn}"
            wepp_module.copy_input_file(wepp.wd, src_rel, dst_fn)

    def make_hillslope_runs(
        self,
        wepp: "Wepp",
        translator: Any,
        reveg: bool = False,
        man_relpath: str = "",
        cli_relpath: str = "",
        slp_relpath: str = "",
        sol_relpath: str = "",
    ) -> None:
        from wepppy.nodb.core import wepp as wepp_module

        wepp.logger.info("    Prepping _make_hillslope_runs... ")
        watershed = wepp.watershed_instance
        runs_dir = wepp.runs_dir
        climate = wepp.climate_instance
        years = climate.input_years

        if climate.climate_mode in [
            wepp_module.ClimateMode.SingleStorm,
            wepp_module.ClimateMode.UserDefinedSingleStorm,
        ]:
            for topaz_id in watershed._subs_summary:
                wepp_id = translator.wepp(top=int(topaz_id))

                make_ss_hillslope_run(
                    wepp_id,
                    runs_dir,
                    man_relpath=man_relpath,
                    cli_relpath=cli_relpath,
                    slp_relpath=slp_relpath,
                    sol_relpath=sol_relpath,
                )

        elif climate.climate_mode == wepp_module.ClimateMode.SingleStormBatch:
            for topaz_id in watershed._subs_summary:
                wepp_id = translator.wepp(top=int(topaz_id))

                for d in climate.ss_batch_storms:
                    ss_batch_id = d["ss_batch_id"]
                    ss_batch_key = d["ss_batch_key"]
                    make_ss_batch_hillslope_run(
                        wepp_id,
                        runs_dir,
                        ss_batch_id=ss_batch_id,
                        ss_batch_key=ss_batch_key,
                        man_relpath=man_relpath,
                        cli_relpath=cli_relpath,
                        slp_relpath=slp_relpath,
                        sol_relpath=sol_relpath,
                    )
        else:
            for topaz_id in watershed._subs_summary:
                wepp_id = translator.wepp(top=int(topaz_id))
                make_hillslope_run(
                    wepp_id,
                    years,
                    runs_dir,
                    reveg=reveg,
                    man_relpath=man_relpath,
                    cli_relpath=cli_relpath,
                    slp_relpath=slp_relpath,
                    sol_relpath=sol_relpath,
                )

    def prep_watershed(
        self,
        wepp: "Wepp",
        erodibility: Optional[float] = None,
        critical_shear: Optional[float] = None,
        tcr: Optional[bool] = None,
        avke: Optional[float] = None,
        channel_manning_roughness_coefficient_bare: Optional[float] = None,
        channel_manning_roughness_coefficient_veg: Optional[float] = None,
    ) -> None:
        wepp.logger.info("Prepping Watershed... ")

        watershed = wepp.watershed_instance
        translator = watershed.translator_factory()

        if critical_shear is None:
            crit_shear_map = getattr(wepp, "channel_critical_shear_map", None)

            if crit_shear_map is not None:
                lng, lat = watershed.centroid
                rdi = RasterDatasetInterpolator(crit_shear_map)
                critical_shear = rdi.get_location_info(lng, lat, method="nearest")
                wepp.logger.info(
                    f"critical_shear from map {crit_shear_map} at {watershed.centroid} ={critical_shear}... "
                )

        if critical_shear is None:
            critical_shear = wepp.channel_critical_shear

        wepp._prep_structure(translator)
        wepp._prep_channel_slopes()
        wepp._prep_channel_chn(
            translator,
            erodibility,
            critical_shear,
            channel_manning_roughness_coefficient_bare=channel_manning_roughness_coefficient_bare,
            channel_manning_roughness_coefficient_veg=channel_manning_roughness_coefficient_veg,
        )
        wepp._prep_impoundment()
        wepp._prep_channel_soils(translator, erodibility, critical_shear, avke)
        wepp._prep_channel_climate(translator)
        wepp._prep_channel_input()
        wepp._prep_tc()

        if (tcr is None and wepp.run_tcr) or tcr:
            wepp._prep_tcr()

        wepp._prep_watershed_managements(translator)
        wepp._make_watershed_run(translator)

        wepp.trigger(TriggerEvents.WEPP_PREP_WATERSHED_COMPLETE)
