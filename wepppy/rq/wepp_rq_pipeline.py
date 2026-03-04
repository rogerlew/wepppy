from __future__ import annotations

from typing import Any, Callable, Optional

from rq import Queue
from rq.job import Job


def _delete_after_interchange_enabled(*, wepp: Any, climate: Any) -> bool:
    value = getattr(wepp, "delete_after_interchange", None)
    if value is None:
        value = getattr(climate, "delete_after_interchange", False)
    return bool(value)


def _record_enqueue(parent_job: Job, key: str, child_job: Job) -> Job:
    parent_job.meta[key] = child_job.id
    parent_job.save()
    return child_job


def _enqueue(
    q: Queue,
    parent_job: Job,
    *,
    key: str,
    func: Any,
    args: tuple[Any, ...] | list[Any] = (),
    kwargs: Optional[dict[str, Any]] = None,
    timeout: Any = None,
    depends_on: Any = None,
) -> Job:
    child_job = q.enqueue_call(
        func=func,
        args=args,
        kwargs=kwargs,
        timeout=timeout,
        depends_on=depends_on,
    )
    return _record_enqueue(parent_job, key, child_job)


def enqueue_log_complete(
    q: Queue,
    parent_job: Job,
    runid: str,
    *,
    tasks: Any,
    kwargs: Optional[dict[str, Any]] = None,
    depends_on: Any = None,
) -> Job:
    return _enqueue(
        q,
        parent_job,
        key="jobs:6,func:_log_complete_rq",
        func=tasks._log_complete_rq,
        args=(runid,),
        kwargs=kwargs,
        depends_on=depends_on,
    )


def enqueue_log_prep_complete(
    q: Queue,
    parent_job: Job,
    runid: str,
    *,
    tasks: Any,
    kwargs: Optional[dict[str, Any]] = None,
    depends_on: Any = None,
) -> Job:
    return _enqueue(
        q,
        parent_job,
        key="jobs:6,func:_log_prep_complete_rq",
        func=tasks._log_prep_complete_rq,
        args=(runid,),
        kwargs=kwargs,
        depends_on=depends_on,
    )


def enqueue_wepp_pipeline(
    q: Queue,
    parent_job: Job,
    runid: str,
    *,
    wepp: Any,
    climate: Any,
    tasks: Any,
    timeout: int,
) -> Job:
    jobs0_hillslopes_prep: list[Job] = []

    if wepp.multi_ofe:
        job_prep_soils = _enqueue(
            q,
            parent_job,
            key="jobs:0,func:_prep_multi_ofe_rq",
            func=tasks._prep_multi_ofe_rq,
            args=(runid,),
            timeout="4h",
        )
        jobs0_hillslopes_prep.append(job_prep_soils)
    else:
        jobs0_hillslopes_prep.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:0,func:_prep_slopes_rq",
                func=tasks._prep_slopes_rq,
                args=(runid,),
                timeout="4h",
            )
        )
        jobs0_hillslopes_prep.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:0,func:_prep_managements_rq",
                func=tasks._prep_managements_rq,
                args=(runid,),
                timeout="4h",
            )
        )
        job_prep_soils = _enqueue(
            q,
            parent_job,
            key="jobs:0,func:_prep_soils_rq",
            func=tasks._prep_soils_rq,
            args=(runid,),
            timeout="4h",
        )
        jobs0_hillslopes_prep.append(job_prep_soils)

    jobs0_hillslopes_prep.append(
        _enqueue(
            q,
            parent_job,
            key="jobs:0,func:_prep_climates_rq",
            func=tasks._prep_climates_rq,
            args=(runid,),
            timeout="4h",
        )
    )

    job_prep_remaining = _enqueue(
        q,
        parent_job,
        key="jobs:0,func:_prep_remaining_rq",
        func=tasks._prep_remaining_rq,
        args=(runid,),
        timeout="4h",
        depends_on=jobs0_hillslopes_prep,
    )

    jobs1_hillslopes = _enqueue(
        q,
        parent_job,
        key="jobs:1,func:run_hillslopes_rq",
        func=tasks._run_hillslopes_rq,
        args=(runid,),
        timeout=timeout,
        depends_on=job_prep_remaining,
    )

    run_watershed = bool(wepp.run_wepp_watershed)
    job2_watershed_prep: Job | None = None
    if run_watershed:
        job2_watershed_prep = _enqueue(
            q,
            parent_job,
            key="jobs:2,func:_prep_watershed_rq",
            func=tasks._prep_watershed_rq,
            args=(runid,),
            timeout=timeout,
            depends_on=jobs1_hillslopes,
        )

    job2_totalwatsed3: Job | None = None
    job2_hillslope_interchange: Job | None = None
    job2_post_dss_export: Job | None = None
    job_post_run_cleanup_out: Job | None = None
    swat_job_build: Job | None = None
    swat_job_run: Job | None = None

    delete_after_interchange = _delete_after_interchange_enabled(wepp=wepp, climate=climate)
    swat_before_interchange = bool(
        wepp.mods
        and "swat" in wepp.mods
        and delete_after_interchange
    )
    if swat_before_interchange:
        swat_dependencies = [jobs1_hillslopes]
        if job2_watershed_prep is not None:
            swat_dependencies.append(job2_watershed_prep)
        swat_job_build = _enqueue(
            q,
            parent_job,
            key="jobs:2,func:_build_swat_inputs_rq",
            func=tasks._build_swat_inputs_rq,
            args=(runid,),
            timeout=timeout,
            depends_on=swat_dependencies,
        )
        swat_job_run = _enqueue(
            q,
            parent_job,
            key="jobs:3,func:_run_swat_rq",
            func=tasks._run_swat_rq,
            args=(runid,),
            timeout=timeout,
            depends_on=swat_job_build,
        )

    interchange_dependencies: list[Job] = [jobs1_hillslopes]
    if swat_job_build is not None:
        interchange_dependencies.append(swat_job_build)
    job2_hillslope_interchange = _enqueue(
        q,
        parent_job,
        key="jobs:2,func:_build_hillslope_interchange_rq",
        func=tasks._build_hillslope_interchange_rq,
        args=(runid,),
        timeout=timeout,
        depends_on=interchange_dependencies,
    )

    if not climate.is_single_storm:
        job2_totalwatsed3 = _enqueue(
            q,
            parent_job,
            key="jobs:2,func:_build_totalwatsed3_rq",
            func=tasks._build_totalwatsed3_rq,
            args=(runid,),
            timeout=timeout,
            depends_on=job2_hillslope_interchange,
        )

    jobs2_flowpaths: Job | None = None
    if wepp.run_flowpaths:
        jobs2_flowpaths = _enqueue(
            q,
            parent_job,
            key="jobs:2,func:run_flowpaths_rq",
            func=tasks._run_flowpaths_rq,
            args=(runid,),
            timeout=timeout,
            depends_on=job_prep_remaining,
        )

    if wepp.mods and "swat" in wepp.mods and swat_job_build is None:
        swat_dependencies = [job2_hillslope_interchange]
        if job2_watershed_prep is not None:
            swat_dependencies.append(job2_watershed_prep)
        swat_job_build = _enqueue(
            q,
            parent_job,
            key="jobs:2,func:_build_swat_inputs_rq",
            func=tasks._build_swat_inputs_rq,
            args=(runid,),
            timeout=timeout,
            depends_on=swat_dependencies,
        )
        swat_job_run = _enqueue(
            q,
            parent_job,
            key="jobs:3,func:_run_swat_rq",
            func=tasks._run_swat_rq,
            args=(runid,),
            timeout=timeout,
            depends_on=swat_job_build,
        )

    jobs4_post: list[Job] = []
    if run_watershed:
        jobs3_watersheds: list[Job] = []
        if climate.climate_mode == tasks.ClimateMode.SingleStormBatch:
            for storm in climate.ss_batch_storms:
                ss_batch_id = storm["ss_batch_id"]
                jobs3_watersheds.append(
                    _enqueue(
                        q,
                        parent_job,
                        key=f"jobs:3,func:run_ss_batch_watershed_rq,ss_batch_id:{ss_batch_id}",
                        func=tasks.run_ss_batch_watershed_rq,
                        args=[runid],
                        kwargs={"wepp_bin": wepp.wepp_bin, "ss_batch_id": ss_batch_id},
                        timeout=timeout,
                        depends_on=job2_watershed_prep,
                    )
                )
        else:
            jobs3_watersheds.append(
                _enqueue(
                    q,
                    parent_job,
                    key="jobs:3,func:run_watershed_rq",
                    func=tasks.run_watershed_rq,
                    args=[runid],
                    kwargs={"wepp_bin": wepp.wepp_bin},
                    timeout=timeout,
                    depends_on=job2_watershed_prep,
                )
            )

        post_dependencies = jobs3_watersheds or [job2_watershed_prep]
        job_post_run_cleanup_out = _enqueue(
            q,
            parent_job,
            key="jobs:4,func:_post_run_cleanup_out_rq",
            func=tasks._post_run_cleanup_out_rq,
            args=(runid,),
            timeout=timeout,
            depends_on=post_dependencies,
        )
        jobs4_post.append(job_post_run_cleanup_out)

        if wepp.prep_details_on_run_completion:
            jobs4_post.append(
                _enqueue(
                    q,
                    parent_job,
                    key="jobs:4,func:_post_prep_details_rq",
                    func=tasks._post_prep_details_rq,
                    args=(runid,),
                    timeout=timeout,
                    depends_on=post_dependencies,
                )
            )

        if not climate.is_single_storm:
            watbal_dependencies = list(post_dependencies)
            if job2_hillslope_interchange is not None:
                watbal_dependencies.append(job2_hillslope_interchange)
            jobs4_post.append(
                _enqueue(
                    q,
                    parent_job,
                    key="jobs:4,func:_run_hillslope_watbal_rq",
                    func=tasks._run_hillslope_watbal_rq,
                    args=(runid,),
                    timeout=timeout,
                    depends_on=watbal_dependencies,
                )
            )

        if not wepp.multi_ofe:
            jobs4_post.append(
                _enqueue(
                    q,
                    parent_job,
                    key="jobs:4,func:_post_make_loss_grid_rq",
                    func=tasks._post_make_loss_grid_rq,
                    args=(runid,),
                    timeout=timeout,
                    depends_on=post_dependencies,
                )
            )

        job_post_watershed_interchange = _enqueue(
            q,
            parent_job,
            key="jobs:4,func:_post_watershed_interchange_rq",
            func=tasks._post_watershed_interchange_rq,
            args=(runid,),
            timeout=timeout,
            depends_on=job_post_run_cleanup_out,
        )
        jobs4_post.append(job_post_watershed_interchange)

        if not climate.is_single_storm and job2_totalwatsed3 is not None:
            jobs4_post.append(
                _enqueue(
                    q,
                    parent_job,
                    key="jobs:4,func:_analyze_return_periods_rq",
                    func=tasks._analyze_return_periods_rq,
                    args=(runid,),
                    timeout=timeout,
                    depends_on=[job_post_watershed_interchange, job2_totalwatsed3],
                )
            )

    if run_watershed and not climate.is_single_storm and wepp.dss_export_on_run_completion:
        dss_dependencies: list[Job] = [job2_hillslope_interchange]
        if job_post_run_cleanup_out is not None:
            dss_dependencies.append(job_post_run_cleanup_out)
        job2_post_dss_export = _enqueue(
            q,
            parent_job,
            key="jobs:2,func:_post_dss_export_rq",
            func=tasks.post_dss_export_rq,
            args=(runid,),
            timeout=timeout,
            depends_on=dss_dependencies,
        )

    jobs5_post: list[Job] = []
    if run_watershed and wepp.legacy_arc_export_on_run_completion:
        jobs5_post.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:5,func:_post_legacy_arc_export_rq",
                func=tasks._post_legacy_arc_export_rq,
                args=(runid,),
                timeout=timeout,
                depends_on=jobs4_post,
            )
        )

    if run_watershed and wepp.arc_export_on_run_completion:
        jobs5_post.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:5,func:_post_gpkg_export_rq",
                func=tasks._post_gpkg_export_rq,
                args=(runid,),
                timeout=timeout,
                depends_on=jobs4_post,
            )
        )

    if job2_hillslope_interchange is not None:
        jobs5_post.append(job2_hillslope_interchange)
    if job2_totalwatsed3 is not None:
        jobs5_post.append(job2_totalwatsed3)
    if job2_post_dss_export is not None:
        jobs5_post.append(job2_post_dss_export)
    if jobs2_flowpaths is not None:
        jobs5_post.append(jobs2_flowpaths)
    if swat_job_run is not None:
        jobs5_post.append(swat_job_run)

    final_dependencies = jobs4_post + jobs5_post
    return enqueue_log_complete(
        q,
        parent_job,
        runid,
        tasks=tasks,
        kwargs={
            "auto_commit_inputs": True,
            "commit_stage": "WEPP pipeline",
        },
        depends_on=final_dependencies,
    )


def enqueue_wepp_prep_only_pipeline(
    q: Queue,
    parent_job: Job,
    runid: str,
    *,
    wepp: Any,
    tasks: Any,
    timeout: int,
) -> Job:
    jobs0_hillslopes_prep: list[Job] = []

    if wepp.multi_ofe:
        jobs0_hillslopes_prep.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:0,func:_prep_multi_ofe_rq",
                func=tasks._prep_multi_ofe_rq,
                args=(runid,),
                timeout="4h",
            )
        )
    else:
        jobs0_hillslopes_prep.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:0,func:_prep_slopes_rq",
                func=tasks._prep_slopes_rq,
                args=(runid,),
                timeout="4h",
            )
        )
        jobs0_hillslopes_prep.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:0,func:_prep_managements_rq",
                func=tasks._prep_managements_rq,
                args=(runid,),
                timeout="4h",
            )
        )
        jobs0_hillslopes_prep.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:0,func:_prep_soils_rq",
                func=tasks._prep_soils_rq,
                args=(runid,),
                timeout="4h",
            )
        )

    jobs0_hillslopes_prep.append(
        _enqueue(
            q,
            parent_job,
            key="jobs:0,func:_prep_climates_rq",
            func=tasks._prep_climates_rq,
            args=(runid,),
            timeout="4h",
        )
    )

    job_prep_remaining = _enqueue(
        q,
        parent_job,
        key="jobs:0,func:_prep_remaining_rq",
        func=tasks._prep_remaining_rq,
        args=(runid,),
        timeout="4h",
        depends_on=jobs0_hillslopes_prep,
    )

    job_watershed_prep = _enqueue(
        q,
        parent_job,
        key="jobs:2,func:_prep_watershed_rq",
        func=tasks._prep_watershed_rq,
        args=(runid,),
        timeout=timeout,
        depends_on=job_prep_remaining,
    )

    return enqueue_log_prep_complete(
        q,
        parent_job,
        runid,
        tasks=tasks,
        kwargs={
            "auto_commit_inputs": True,
            "commit_stage": "WEPP prep-only pipeline",
        },
        depends_on=job_watershed_prep,
    )


def enqueue_wepp_noprep_pipeline(
    q: Queue,
    parent_job: Job,
    runid: str,
    *,
    wepp: Any,
    climate: Any,
    tasks: Any,
    timeout: int,
) -> Job:
    jobs1_hillslopes = _enqueue(
        q,
        parent_job,
        key="jobs:1,func:_run_hillslopes_rq",
        func=tasks._run_hillslopes_rq,
        args=(runid,),
        timeout=timeout,
    )

    job2_hillslope_interchange = _enqueue(
        q,
        parent_job,
        key="jobs:2,func:_build_hillslope_interchange_rq",
        func=tasks._build_hillslope_interchange_rq,
        args=(runid,),
        timeout=timeout,
        depends_on=[jobs1_hillslopes],
    )

    job2_totalwatsed3: Job | None = None
    if not climate.is_single_storm:
        job2_totalwatsed3 = _enqueue(
            q,
            parent_job,
            key="jobs:2,func:_build_totalwatsed3_rq",
            func=tasks._build_totalwatsed3_rq,
            args=(runid,),
            timeout=timeout,
            depends_on=job2_hillslope_interchange,
        )

    run_watershed = bool(wepp.run_wepp_watershed)
    jobs4_post: list[Job] = []
    job_post_run_cleanup_out: Job | None = None
    job2_post_dss_export: Job | None = None

    if run_watershed:
        jobs3_watersheds: list[Job] = []
        if climate.climate_mode == tasks.ClimateMode.SingleStormBatch:
            for storm in climate.ss_batch_storms:
                ss_batch_id = storm["ss_batch_id"]
                jobs3_watersheds.append(
                    _enqueue(
                        q,
                        parent_job,
                        key=f"jobs:3,func:run_ss_batch_watershed_rq,ss_batch_id:{ss_batch_id}",
                        func=tasks.run_ss_batch_watershed_rq,
                        args=[runid],
                        kwargs={"wepp_bin": wepp.wepp_bin, "ss_batch_id": ss_batch_id},
                        timeout=timeout,
                        depends_on=jobs1_hillslopes,
                    )
                )
        else:
            jobs3_watersheds.append(
                _enqueue(
                    q,
                    parent_job,
                    key="jobs:3,func:run_watershed_rq",
                    func=tasks.run_watershed_rq,
                    args=[runid],
                    kwargs={"wepp_bin": wepp.wepp_bin},
                    timeout=timeout,
                    depends_on=jobs1_hillslopes,
                )
            )

        post_dependencies = jobs3_watersheds or [jobs1_hillslopes]
        job_post_run_cleanup_out = _enqueue(
            q,
            parent_job,
            key="jobs:4,func:_post_run_cleanup_out_rq",
            func=tasks._post_run_cleanup_out_rq,
            args=(runid,),
            timeout=timeout,
            depends_on=post_dependencies,
        )
        jobs4_post.append(job_post_run_cleanup_out)

        if wepp.prep_details_on_run_completion:
            jobs4_post.append(
                _enqueue(
                    q,
                    parent_job,
                    key="jobs:4,func:_post_prep_details_rq",
                    func=tasks._post_prep_details_rq,
                    args=(runid,),
                    timeout=timeout,
                    depends_on=post_dependencies,
                )
            )

        if not climate.is_single_storm:
            watbal_dependencies = list(post_dependencies)
            watbal_dependencies.append(job2_hillslope_interchange)
            jobs4_post.append(
                _enqueue(
                    q,
                    parent_job,
                    key="jobs:4,func:_run_hillslope_watbal_rq",
                    func=tasks._run_hillslope_watbal_rq,
                    args=(runid,),
                    timeout=timeout,
                    depends_on=watbal_dependencies,
                )
            )

        if not wepp.multi_ofe:
            jobs4_post.append(
                _enqueue(
                    q,
                    parent_job,
                    key="jobs:4,func:_post_make_loss_grid_rq",
                    func=tasks._post_make_loss_grid_rq,
                    args=(runid,),
                    timeout=timeout,
                    depends_on=post_dependencies,
                )
            )

        job_post_watershed_interchange = _enqueue(
            q,
            parent_job,
            key="jobs:4,func:_post_watershed_interchange_rq",
            func=tasks._post_watershed_interchange_rq,
            args=(runid,),
            timeout=timeout,
            depends_on=job_post_run_cleanup_out,
        )
        jobs4_post.append(job_post_watershed_interchange)

        if not climate.is_single_storm and job2_totalwatsed3 is not None:
            jobs4_post.append(
                _enqueue(
                    q,
                    parent_job,
                    key="jobs:4,func:_analyze_return_periods_rq",
                    func=tasks._analyze_return_periods_rq,
                    args=(runid,),
                    timeout=timeout,
                    depends_on=[job_post_watershed_interchange, job2_totalwatsed3],
                )
            )

        if not climate.is_single_storm and wepp.dss_export_on_run_completion:
            dss_dependencies: list[Job] = [job2_hillslope_interchange]
            if job_post_run_cleanup_out is not None:
                dss_dependencies.append(job_post_run_cleanup_out)
            job2_post_dss_export = _enqueue(
                q,
                parent_job,
                key="jobs:2,func:_post_dss_export_rq",
                func=tasks.post_dss_export_rq,
                args=(runid,),
                timeout=timeout,
                depends_on=dss_dependencies,
            )

    jobs5_post: list[Job] = []
    if run_watershed and wepp.legacy_arc_export_on_run_completion:
        jobs5_post.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:5,func:_post_legacy_arc_export_rq",
                func=tasks._post_legacy_arc_export_rq,
                args=(runid,),
                timeout=timeout,
                depends_on=jobs4_post,
            )
        )

    if run_watershed and wepp.arc_export_on_run_completion:
        jobs5_post.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:5,func:_post_gpkg_export_rq",
                func=tasks._post_gpkg_export_rq,
                args=(runid,),
                timeout=timeout,
                depends_on=jobs4_post,
            )
        )

    jobs5_post.append(job2_hillslope_interchange)
    if job2_totalwatsed3 is not None:
        jobs5_post.append(job2_totalwatsed3)
    if job2_post_dss_export is not None:
        jobs5_post.append(job2_post_dss_export)

    final_dependencies = jobs4_post + jobs5_post
    return enqueue_log_complete(
        q,
        parent_job,
        runid,
        tasks=tasks,
        depends_on=final_dependencies,
    )


def enqueue_watershed_pipeline(
    q: Queue,
    parent_job: Job,
    runid: str,
    *,
    wepp: Any,
    climate: Any,
    tasks: Any,
    timeout: int,
    has_hillslope_outputs: bool,
    publish_status: Callable[[str], None] | None = None,
) -> Job:
    job2_watershed_prep = _enqueue(
        q,
        parent_job,
        key="jobs:2,func:_prep_watershed_rq",
        func=tasks._prep_watershed_rq,
        args=(runid,),
        timeout=timeout,
    )

    jobs3_watersheds: list[Job] = []
    if climate.climate_mode == tasks.ClimateMode.SingleStormBatch:
        for storm in climate.ss_batch_storms:
            ss_batch_id = storm["ss_batch_id"]
            jobs3_watersheds.append(
                _enqueue(
                    q,
                    parent_job,
                    key=f"jobs:3,func:run_ss_batch_watershed_rq,ss_batch_id:{ss_batch_id}",
                    func=tasks.run_ss_batch_watershed_rq,
                    args=[runid],
                    kwargs={"wepp_bin": wepp.wepp_bin, "ss_batch_id": ss_batch_id},
                    timeout=timeout,
                    depends_on=job2_watershed_prep,
                )
            )
    else:
        jobs3_watersheds.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:3,func:run_watershed_rq",
                func=tasks.run_watershed_rq,
                args=[runid],
                kwargs={"wepp_bin": wepp.wepp_bin},
                timeout=timeout,
                depends_on=job2_watershed_prep,
            )
        )

    post_dependencies = jobs3_watersheds or [job2_watershed_prep]
    jobs4_post: list[Job] = []
    job_post_run_cleanup_out = _enqueue(
        q,
        parent_job,
        key="jobs:4,func:_post_run_cleanup_out_rq",
        func=tasks._post_run_cleanup_out_rq,
        args=(runid,),
        timeout=timeout,
        depends_on=post_dependencies,
    )
    jobs4_post.append(job_post_run_cleanup_out)

    if wepp.prep_details_on_run_completion:
        jobs4_post.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:4,func:_post_prep_details_rq",
                func=tasks._post_prep_details_rq,
                args=(runid,),
                timeout=timeout,
                depends_on=post_dependencies,
            )
        )

    if not wepp.multi_ofe:
        if has_hillslope_outputs:
            jobs4_post.append(
                _enqueue(
                    q,
                    parent_job,
                    key="jobs:4,func:_post_make_loss_grid_rq",
                    func=tasks._post_make_loss_grid_rq,
                    args=(runid,),
                    timeout=timeout,
                    depends_on=post_dependencies,
                )
            )
        elif publish_status is not None:
            publish_status("Skipping loss grid: hillslope outputs (H*) not found in wepp/output")

    job_post_watershed_interchange = _enqueue(
        q,
        parent_job,
        key="jobs:4,func:_post_watershed_interchange_rq",
        func=tasks._post_watershed_interchange_rq,
        args=(runid,),
        timeout=timeout,
        depends_on=job_post_run_cleanup_out,
    )
    jobs4_post.append(job_post_watershed_interchange)

    jobs5_post: list[Job] = []
    if wepp.legacy_arc_export_on_run_completion:
        jobs5_post.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:5,func:_post_legacy_arc_export_rq",
                func=tasks._post_legacy_arc_export_rq,
                args=(runid,),
                timeout=timeout,
                depends_on=jobs4_post,
            )
        )

    final_dependencies = jobs4_post + jobs5_post
    return enqueue_log_complete(
        q,
        parent_job,
        runid,
        tasks=tasks,
        kwargs={
            "auto_commit_inputs": True,
            "commit_stage": "WEPP watershed pipeline",
        },
        depends_on=final_dependencies,
    )


def enqueue_watershed_noprep_pipeline(
    q: Queue,
    parent_job: Job,
    runid: str,
    *,
    wepp: Any,
    climate: Any,
    tasks: Any,
    timeout: int,
    has_hillslope_outputs: bool,
    publish_status: Callable[[str], None] | None = None,
) -> Job:
    jobs3_watersheds: list[Job] = []
    if climate.climate_mode == tasks.ClimateMode.SingleStormBatch:
        for storm in climate.ss_batch_storms:
            ss_batch_id = storm["ss_batch_id"]
            jobs3_watersheds.append(
                _enqueue(
                    q,
                    parent_job,
                    key=f"jobs:3,func:run_ss_batch_watershed_rq,ss_batch_id:{ss_batch_id}",
                    func=tasks.run_ss_batch_watershed_rq,
                    args=[runid],
                    kwargs={"wepp_bin": wepp.wepp_bin, "ss_batch_id": ss_batch_id},
                    timeout=timeout,
                )
            )
    else:
        jobs3_watersheds.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:3,func:run_watershed_rq",
                func=tasks.run_watershed_rq,
                args=[runid],
                kwargs={"wepp_bin": wepp.wepp_bin},
                timeout=timeout,
            )
        )

    post_dependencies = jobs3_watersheds
    jobs4_post: list[Job] = []
    job_post_run_cleanup_out = _enqueue(
        q,
        parent_job,
        key="jobs:4,func:_post_run_cleanup_out_rq",
        func=tasks._post_run_cleanup_out_rq,
        args=(runid,),
        timeout=timeout,
        depends_on=post_dependencies,
    )
    jobs4_post.append(job_post_run_cleanup_out)

    if wepp.prep_details_on_run_completion:
        jobs4_post.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:4,func:_post_prep_details_rq",
                func=tasks._post_prep_details_rq,
                args=(runid,),
                timeout=timeout,
                depends_on=post_dependencies,
            )
        )

    if not wepp.multi_ofe:
        if has_hillslope_outputs:
            jobs4_post.append(
                _enqueue(
                    q,
                    parent_job,
                    key="jobs:4,func:_post_make_loss_grid_rq",
                    func=tasks._post_make_loss_grid_rq,
                    args=(runid,),
                    timeout=timeout,
                    depends_on=post_dependencies,
                )
            )
        elif publish_status is not None:
            publish_status("Skipping loss grid: hillslope outputs (H*) not found in wepp/output")

    job_post_watershed_interchange = _enqueue(
        q,
        parent_job,
        key="jobs:4,func:_post_watershed_interchange_rq",
        func=tasks._post_watershed_interchange_rq,
        args=(runid,),
        timeout=timeout,
        depends_on=job_post_run_cleanup_out,
    )
    jobs4_post.append(job_post_watershed_interchange)

    jobs5_post: list[Job] = []
    if wepp.legacy_arc_export_on_run_completion:
        jobs5_post.append(
            _enqueue(
                q,
                parent_job,
                key="jobs:5,func:_post_legacy_arc_export_rq",
                func=tasks._post_legacy_arc_export_rq,
                args=(runid,),
                timeout=timeout,
                depends_on=jobs4_post,
            )
        )

    final_dependencies = jobs4_post + jobs5_post
    return enqueue_log_complete(
        q,
        parent_job,
        runid,
        tasks=tasks,
        depends_on=final_dependencies,
    )
