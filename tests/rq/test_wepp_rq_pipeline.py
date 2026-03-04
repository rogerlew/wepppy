from __future__ import annotations

from types import SimpleNamespace

import pytest

import wepppy.rq.wepp_rq_pipeline as pipeline

pytestmark = pytest.mark.unit


class _DummyQueue:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def enqueue_call(
        self,
        func,
        args=(),
        kwargs=None,
        timeout=None,
        depends_on=None,
    ):
        job = SimpleNamespace(id=f"job-{len(self.calls) + 1}")
        self.calls.append(
            {
                "func": func,
                "args": args,
                "kwargs": kwargs,
                "timeout": timeout,
                "depends_on": depends_on,
                "job": job,
            }
        )
        return job


def _make_parent_job() -> SimpleNamespace:
    parent_job = SimpleNamespace(meta={}, saves=0)

    def _save() -> None:
        parent_job.saves += 1

    parent_job.save = _save  # type: ignore[attr-defined]
    return parent_job


def test_enqueue_log_complete_tracks_meta_and_kwargs() -> None:
    q = _DummyQueue()
    parent_job = _make_parent_job()
    tasks = SimpleNamespace(_log_complete_rq=object())

    final_job = pipeline.enqueue_log_complete(
        q,
        parent_job,
        "run-1",
        tasks=tasks,
        kwargs={"auto_commit_inputs": True},
    )

    assert final_job.id == "job-1"
    assert parent_job.meta["jobs:6,func:_log_complete_rq"] == "job-1"
    assert parent_job.saves == 1
    assert q.calls[0]["func"] is tasks._log_complete_rq
    assert q.calls[0]["args"] == ("run-1",)
    assert q.calls[0]["kwargs"] == {"auto_commit_inputs": True}


def test_enqueue_watershed_noprep_pipeline_skips_loss_grid_without_hillslope_outputs() -> None:
    q = _DummyQueue()
    parent_job = _make_parent_job()
    status_messages: list[str] = []
    climate_mode = SimpleNamespace(SingleStormBatch="single_storm_batch")
    tasks = SimpleNamespace(
        ClimateMode=climate_mode,
        run_ss_batch_watershed_rq=object(),
        run_watershed_rq=object(),
        _post_run_cleanup_out_rq=object(),
        _post_prep_details_rq=object(),
        _post_make_loss_grid_rq=object(),
        _post_watershed_interchange_rq=object(),
        _post_legacy_arc_export_rq=object(),
        _log_complete_rq=object(),
    )
    wepp = SimpleNamespace(
        wepp_bin="wepp_bin",
        prep_details_on_run_completion=False,
        multi_ofe=False,
        legacy_arc_export_on_run_completion=False,
    )
    climate = SimpleNamespace(
        climate_mode="continuous",
        ss_batch_storms=[],
    )

    final_job = pipeline.enqueue_watershed_noprep_pipeline(
        q,
        parent_job,
        "run-2",
        wepp=wepp,
        climate=climate,
        tasks=tasks,
        timeout=43_200,
        has_hillslope_outputs=False,
        publish_status=status_messages.append,
    )

    call_funcs = [call["func"] for call in q.calls]
    assert tasks._post_make_loss_grid_rq not in call_funcs
    assert status_messages == ["Skipping loss grid: hillslope outputs (H*) not found in wepp/output"]
    assert final_job.id == q.calls[-1]["job"].id
    assert "jobs:4,func:_post_make_loss_grid_rq" not in parent_job.meta
    assert parent_job.meta["jobs:6,func:_log_complete_rq"] == final_job.id


def test_enqueue_wepp_pipeline_defers_swat_until_after_hillslope_interchange() -> None:
    q = _DummyQueue()
    parent_job = _make_parent_job()
    tasks = SimpleNamespace(
        _prep_multi_ofe_rq=object(),
        _prep_slopes_rq=object(),
        _prep_managements_rq=object(),
        _prep_soils_rq=object(),
        _prep_climates_rq=object(),
        _prep_remaining_rq=object(),
        _run_hillslopes_rq=object(),
        _prep_watershed_rq=object(),
        _build_swat_inputs_rq=object(),
        _run_swat_rq=object(),
        _build_hillslope_interchange_rq=object(),
        _build_totalwatsed3_rq=object(),
        _run_flowpaths_rq=object(),
        run_ss_batch_watershed_rq=object(),
        run_watershed_rq=object(),
        _post_run_cleanup_out_rq=object(),
        _post_prep_details_rq=object(),
        _run_hillslope_watbal_rq=object(),
        _post_make_loss_grid_rq=object(),
        _post_watershed_interchange_rq=object(),
        _analyze_return_periods_rq=object(),
        post_dss_export_rq=object(),
        _post_legacy_arc_export_rq=object(),
        _post_gpkg_export_rq=object(),
        _log_complete_rq=object(),
        ClimateMode=SimpleNamespace(SingleStormBatch="single_storm_batch"),
    )
    wepp = SimpleNamespace(
        multi_ofe=True,
        run_wepp_watershed=False,
        mods=["swat"],
        delete_after_interchange=False,  # should control queue wiring, not climate.delete_after_interchange
        run_flowpaths=False,
        wepp_bin="wepp_bin",
        prep_details_on_run_completion=False,
        dss_export_on_run_completion=False,
        legacy_arc_export_on_run_completion=False,
        arc_export_on_run_completion=False,
    )
    climate = SimpleNamespace(
        delete_after_interchange=True,  # intentionally opposite of wepp.delete_after_interchange
        is_single_storm=False,
        climate_mode="continuous",
        ss_batch_storms=[],
    )

    pipeline.enqueue_wepp_pipeline(
        q,
        parent_job,
        "run-3",
        wepp=wepp,
        climate=climate,
        tasks=tasks,
        timeout=43_200,
    )

    hillslope_interchange_call = next(
        call for call in q.calls if call["func"] is tasks._build_hillslope_interchange_rq
    )
    swat_build_call = next(call for call in q.calls if call["func"] is tasks._build_swat_inputs_rq)
    swat_run_call = next(call for call in q.calls if call["func"] is tasks._run_swat_rq)

    swat_build_dependencies = swat_build_call["depends_on"]
    assert isinstance(swat_build_dependencies, list)
    assert len(swat_build_dependencies) == 1
    assert swat_build_dependencies[0].id == hillslope_interchange_call["job"].id
    assert swat_run_call["depends_on"].id == swat_build_call["job"].id


def test_enqueue_wepp_pipeline_runs_swat_before_interchange_when_wepp_delete_enabled() -> None:
    q = _DummyQueue()
    parent_job = _make_parent_job()
    tasks = SimpleNamespace(
        _prep_multi_ofe_rq=object(),
        _prep_slopes_rq=object(),
        _prep_managements_rq=object(),
        _prep_soils_rq=object(),
        _prep_climates_rq=object(),
        _prep_remaining_rq=object(),
        _run_hillslopes_rq=object(),
        _prep_watershed_rq=object(),
        _build_swat_inputs_rq=object(),
        _run_swat_rq=object(),
        _build_hillslope_interchange_rq=object(),
        _build_totalwatsed3_rq=object(),
        _run_flowpaths_rq=object(),
        run_ss_batch_watershed_rq=object(),
        run_watershed_rq=object(),
        _post_run_cleanup_out_rq=object(),
        _post_prep_details_rq=object(),
        _run_hillslope_watbal_rq=object(),
        _post_make_loss_grid_rq=object(),
        _post_watershed_interchange_rq=object(),
        _analyze_return_periods_rq=object(),
        post_dss_export_rq=object(),
        _post_legacy_arc_export_rq=object(),
        _post_gpkg_export_rq=object(),
        _log_complete_rq=object(),
        ClimateMode=SimpleNamespace(SingleStormBatch="single_storm_batch"),
    )
    wepp = SimpleNamespace(
        multi_ofe=True,
        run_wepp_watershed=False,
        mods=["swat"],
        delete_after_interchange=True,  # should force SWAT build before hillslope interchange
        run_flowpaths=False,
        wepp_bin="wepp_bin",
        prep_details_on_run_completion=False,
        dss_export_on_run_completion=False,
        legacy_arc_export_on_run_completion=False,
        arc_export_on_run_completion=False,
    )
    climate = SimpleNamespace(
        delete_after_interchange=False,  # intentionally opposite of wepp.delete_after_interchange
        is_single_storm=False,
        climate_mode="continuous",
        ss_batch_storms=[],
    )

    pipeline.enqueue_wepp_pipeline(
        q,
        parent_job,
        "run-3",
        wepp=wepp,
        climate=climate,
        tasks=tasks,
        timeout=43_200,
    )

    run_hillslopes_call = next(call for call in q.calls if call["func"] is tasks._run_hillslopes_rq)
    swat_build_call = next(call for call in q.calls if call["func"] is tasks._build_swat_inputs_rq)
    hillslope_interchange_call = next(
        call for call in q.calls if call["func"] is tasks._build_hillslope_interchange_rq
    )

    swat_build_dependencies = swat_build_call["depends_on"]
    assert isinstance(swat_build_dependencies, list)
    assert len(swat_build_dependencies) == 1
    assert swat_build_dependencies[0].id == run_hillslopes_call["job"].id

    interchange_dependencies = hillslope_interchange_call["depends_on"]
    assert isinstance(interchange_dependencies, list)
    assert len(interchange_dependencies) == 2
    assert interchange_dependencies[0].id == run_hillslopes_call["job"].id
    assert interchange_dependencies[1].id == swat_build_call["job"].id
