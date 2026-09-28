from __future__ import annotations

from types import SimpleNamespace

import pytest

import wepppy.rq.wepp_rq_pipeline as pipeline
from rq.job import Dependency, JobStatus

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _deterministic_job_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = iter(range(1, 100))
    monkeypatch.setattr(pipeline, "new_rq_job_id", lambda: f"job-{next(counter)}")


class _DummyQueue:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def enqueue_call(
        self,
        func,
        args=(),
        kwargs=None,
        timeout=None,
        meta=None,
        on_failure=None,
        depends_on=None,
        job_id=None,
    ):
        job = SimpleNamespace(id=job_id or f"job-{len(self.calls) + 1}", get_status=lambda refresh=True: JobStatus.QUEUED)
        self.calls.append(
            {
                "func": func,
                "args": args,
                "kwargs": kwargs,
                "timeout": timeout,
                "meta": meta,
                "on_failure": on_failure,
                "depends_on": depends_on,
                "job_id": job_id,
                "job": job,
            }
        )
        return job



def _wepp(tmp_path, **overrides):
    from wepp_runner.wepp_runner import make_watershed_run
    make_watershed_run(100, [1, 2], str(tmp_path), wepp_bin="wepp_260803")
    values = dict(runs_dir=str(tmp_path), watershed_instance=SimpleNamespace(sub_n=2))
    values.update(overrides)
    return SimpleNamespace(**values)


def _climate(**overrides):
    values = dict(input_years=100, is_single_storm=False)
    values.update(overrides)
    return SimpleNamespace(**values)


def _assert_depends_on(call: dict, expected_ids: list[str]) -> None:
    """Every WEPP pipeline edge is strict over the expected job ids."""
    dependency = call["depends_on"]
    if isinstance(dependency, Dependency):
        assert dependency.allow_failure is False
        actual_ids = dependency.dependencies
    elif isinstance(dependency, (list, tuple)):
        actual_ids = [job.id for job in dependency]
    else:
        actual_ids = [dependency.id]
    assert actual_ids == expected_ids


def _make_parent_job() -> SimpleNamespace:
    parent_job = SimpleNamespace(meta={}, saves=0)

    def _save() -> None:
        parent_job.saves += 1

    parent_job.save = _save  # type: ignore[attr-defined]
    return parent_job


def test_parent_lineage_is_saved_before_child_enqueue() -> None:
    q = _DummyQueue()
    parent_job = SimpleNamespace(meta={})

    def fail_save() -> None:
        assert parent_job.meta["jobs:6,func:_log_complete_rq"] == "job-1"
        raise OSError("save failed")

    parent_job.save = fail_save
    with pytest.raises(OSError, match="save failed"):
        pipeline.enqueue_log_complete(
            q,
            parent_job,
            "run-1",
            tasks=SimpleNamespace(_log_complete_rq=object()),
        )
    assert q.calls == []


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


def test_enqueue_watershed_noprep_pipeline_skips_loss_grid_without_hillslope_outputs(tmp_path) -> None:
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
    wepp = _wepp(tmp_path,
        wepp_bin="wepp_bin",
        prep_details_on_run_completion=False,
        multi_ofe=False,
        legacy_arc_export_on_run_completion=False,
    )
    climate = _climate(
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


def test_enqueue_wepp_pipeline_defers_swat_until_after_hillslope_interchange(tmp_path) -> None:
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
    wepp = _wepp(tmp_path,
        multi_ofe=True,
        run_wepp_watershed=False,
        mods=["swat"],
        delete_after_interchange=False,  # should control queue wiring, not climate.delete_after_interchange
        wepp_bin="wepp_bin",
        prep_details_on_run_completion=False,
        dss_export_on_run_completion=False,
        legacy_arc_export_on_run_completion=False,
        arc_export_on_run_completion=False,
    )
    climate = _climate(
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

    _assert_depends_on(swat_build_call, [hillslope_interchange_call["job"].id])
    _assert_depends_on(swat_run_call, [swat_build_call["job"].id])


def test_enqueue_wepp_pipeline_runs_swat_before_interchange_when_wepp_delete_enabled(tmp_path) -> None:
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
    wepp = _wepp(tmp_path,
        multi_ofe=True,
        run_wepp_watershed=False,
        mods=["swat"],
        delete_after_interchange=True,  # should force SWAT build before hillslope interchange
        wepp_bin="wepp_bin",
        prep_details_on_run_completion=False,
        dss_export_on_run_completion=False,
        legacy_arc_export_on_run_completion=False,
        arc_export_on_run_completion=False,
    )
    climate = _climate(
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

    _assert_depends_on(swat_build_call, [run_hillslopes_call["job"].id])
    _assert_depends_on(
        hillslope_interchange_call,
        [run_hillslopes_call["job"].id, swat_build_call["job"].id],
    )


def test_enqueue_wepp_pipeline_post_watershed_interchange_waits_for_cleanup_and_hillslope(tmp_path) -> None:
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
    wepp = _wepp(tmp_path,
        multi_ofe=True,
        run_wepp_watershed=True,
        mods=[],
        delete_after_interchange=False,
        wepp_bin="wepp_bin",
        prep_details_on_run_completion=False,
        dss_export_on_run_completion=False,
        legacy_arc_export_on_run_completion=False,
        arc_export_on_run_completion=False,
    )
    climate = _climate(
        is_single_storm=False,
        climate_mode="continuous",
        ss_batch_storms=[],
    )

    pipeline.enqueue_wepp_pipeline(
        q,
        parent_job,
        "run-4",
        wepp=wepp,
        climate=climate,
        tasks=tasks,
        timeout=43_200,
    )

    cleanup_call = next(call for call in q.calls if call["func"] is tasks._post_run_cleanup_out_rq)
    hillslope_interchange_call = next(
        call for call in q.calls if call["func"] is tasks._build_hillslope_interchange_rq
    )
    post_watershed_interchange_call = next(
        call for call in q.calls if call["func"] is tasks._post_watershed_interchange_rq
    )

    _assert_depends_on(
        post_watershed_interchange_call,
        [cleanup_call["job"].id, hillslope_interchange_call["job"].id],
    )


def test_enqueue_watershed_pipeline_post_watershed_interchange_waits_for_cleanup(tmp_path) -> None:
    q = _DummyQueue()
    parent_job = _make_parent_job()
    tasks = SimpleNamespace(
        ClimateMode=SimpleNamespace(SingleStormBatch="single_storm_batch"),
        run_ss_batch_watershed_rq=object(),
        run_watershed_rq=object(),
        _post_run_cleanup_out_rq=object(),
        _post_prep_details_rq=object(),
        _post_make_loss_grid_rq=object(),
        _post_watershed_interchange_rq=object(),
        _post_legacy_arc_export_rq=object(),
        _log_complete_rq=object(),
        _prep_watershed_rq=object(),
    )
    wepp = _wepp(tmp_path,
        wepp_bin="wepp_bin",
        prep_details_on_run_completion=False,
        multi_ofe=True,
        legacy_arc_export_on_run_completion=False,
    )
    climate = _climate(
        climate_mode="continuous",
        ss_batch_storms=[],
    )

    pipeline.enqueue_watershed_pipeline(
        q,
        parent_job,
        "run-5",
        wepp=wepp,
        climate=climate,
        tasks=tasks,
        timeout=43_200,
        has_hillslope_outputs=False,
    )

    cleanup_call = next(call for call in q.calls if call["func"] is tasks._post_run_cleanup_out_rq)
    post_watershed_interchange_call = next(
        call for call in q.calls if call["func"] is tasks._post_watershed_interchange_rq
    )

    _assert_depends_on(post_watershed_interchange_call, [cleanup_call["job"].id])


def test_enqueue_wepp_noprep_pipeline_post_watershed_interchange_waits_for_cleanup_and_hillslope(tmp_path) -> None:
    q = _DummyQueue()
    parent_job = _make_parent_job()
    tasks = SimpleNamespace(
        _run_hillslopes_rq=object(),
        _build_hillslope_interchange_rq=object(),
        _build_totalwatsed3_rq=object(),
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
    wepp = _wepp(tmp_path,
        run_wepp_watershed=True,
        multi_ofe=True,
        wepp_bin="wepp_bin",
        prep_details_on_run_completion=False,
        dss_export_on_run_completion=False,
        legacy_arc_export_on_run_completion=False,
        arc_export_on_run_completion=False,
    )
    climate = _climate(
        is_single_storm=False,
        climate_mode="continuous",
        ss_batch_storms=[],
    )

    pipeline.enqueue_wepp_noprep_pipeline(
        q,
        parent_job,
        "run-5",
        wepp=wepp,
        climate=climate,
        tasks=tasks,
        timeout=43_200,
    )

    cleanup_call = next(call for call in q.calls if call["func"] is tasks._post_run_cleanup_out_rq)
    hillslope_interchange_call = next(
        call for call in q.calls if call["func"] is tasks._build_hillslope_interchange_rq
    )
    post_watershed_interchange_call = next(
        call for call in q.calls if call["func"] is tasks._post_watershed_interchange_rq
    )

    _assert_depends_on(
        post_watershed_interchange_call,
        [cleanup_call["job"].id, hillslope_interchange_call["job"].id],
    )


def test_enqueue_watershed_noprep_pipeline_post_watershed_interchange_waits_for_cleanup(tmp_path) -> None:
    q = _DummyQueue()
    parent_job = _make_parent_job()
    tasks = SimpleNamespace(
        ClimateMode=SimpleNamespace(SingleStormBatch="single_storm_batch"),
        run_ss_batch_watershed_rq=object(),
        run_watershed_rq=object(),
        _post_run_cleanup_out_rq=object(),
        _post_prep_details_rq=object(),
        _post_make_loss_grid_rq=object(),
        _post_watershed_interchange_rq=object(),
        _post_legacy_arc_export_rq=object(),
        _log_complete_rq=object(),
    )
    wepp = _wepp(tmp_path,
        wepp_bin="wepp_bin",
        prep_details_on_run_completion=False,
        multi_ofe=True,
        legacy_arc_export_on_run_completion=False,
    )
    climate = _climate(
        climate_mode="continuous",
        ss_batch_storms=[],
    )

    pipeline.enqueue_watershed_noprep_pipeline(
        q,
        parent_job,
        "run-6",
        wepp=wepp,
        climate=climate,
        tasks=tasks,
        timeout=43_200,
        has_hillslope_outputs=False,
    )

    cleanup_call = next(call for call in q.calls if call["func"] is tasks._post_run_cleanup_out_rq)
    post_watershed_interchange_call = next(
        call for call in q.calls if call["func"] is tasks._post_watershed_interchange_rq
    )

    _assert_depends_on(post_watershed_interchange_call, [cleanup_call["job"].id])


def test_enqueue_wepp_prep_only_pipeline_skips_run_and_postrun_jobs() -> None:
    q = _DummyQueue()
    parent_job = _make_parent_job()
    tasks = SimpleNamespace(
        _prep_multi_ofe_rq=object(),
        _prep_slopes_rq=object(),
        _prep_managements_rq=object(),
        _prep_soils_rq=object(),
        _prep_climates_rq=object(),
        _prep_remaining_rq=object(),
        _prep_watershed_rq=object(),
        _run_hillslopes_rq=object(),
        run_watershed_rq=object(),
        run_ss_batch_watershed_rq=object(),
        _post_run_cleanup_out_rq=object(),
        _post_watershed_interchange_rq=object(),
        _post_make_loss_grid_rq=object(),
        _log_complete_rq=object(),
        _log_prep_complete_rq=object(),
    )
    wepp = SimpleNamespace(multi_ofe=False)

    final_job = pipeline.enqueue_wepp_prep_only_pipeline(
        q,
        parent_job,
        "run-4",
        wepp=wepp,
        tasks=tasks,
        timeout=43_200,
    )

    call_funcs = [call["func"] for call in q.calls]
    assert tasks._prep_slopes_rq in call_funcs
    assert tasks._prep_managements_rq in call_funcs
    assert tasks._prep_soils_rq in call_funcs
    assert tasks._prep_climates_rq in call_funcs
    assert tasks._prep_remaining_rq in call_funcs
    assert tasks._prep_watershed_rq in call_funcs
    assert tasks._run_hillslopes_rq not in call_funcs
    assert tasks.run_watershed_rq not in call_funcs
    assert tasks.run_ss_batch_watershed_rq not in call_funcs
    assert tasks._post_run_cleanup_out_rq not in call_funcs
    assert tasks._post_watershed_interchange_rq not in call_funcs
    assert tasks._post_make_loss_grid_rq not in call_funcs
    assert tasks._log_complete_rq not in call_funcs

    assert q.calls[-1]["func"] is tasks._log_prep_complete_rq
    assert q.calls[-1]["kwargs"] == {
        "auto_commit_inputs": True,
        "commit_stage": "WEPP prep-only pipeline",
    }
    assert parent_job.meta["jobs:6,func:_log_prep_complete_rq"] == final_job.id


def _timeout_pipeline_inputs(tmp_path, *, single_storm=False, run_watershed=True):
    from wepppy.rq import wepp_rq as tasks
    from wepp_runner.wepp_runner import make_watershed_run
    wepp = _wepp(tmp_path, wepp_bin='wepp_260803', multi_ofe=False,
                 run_wepp_watershed=run_watershed, mods=[],
                 prep_details_on_run_completion=False, dss_export_on_run_completion=False,
                 legacy_arc_export_on_run_completion=False, arc_export_on_run_completion=False)
    wepp.watershed_instance.sub_n = 1908
    climate = _climate(input_years=1000, is_single_storm=single_storm,
                       climate_mode=tasks.ClimateMode.SingleStorm if single_storm else tasks.ClimateMode.Vanilla,
                       ss_batch_storms=[])
    make_watershed_run(1000, list(range(1, 1909)), str(tmp_path), wepp_bin='wepp_260803')
    return wepp, climate, tasks


def _call_timeout_pipeline(name, q, parent, wepp, climate, tasks):
    extra = {'has_hillslope_outputs': True} if name.startswith('enqueue_watershed') else {}
    return getattr(pipeline, name)(q, parent, 'timeout-test', wepp=wepp, climate=climate,
                                  tasks=tasks, timeout=43200, **extra)


_TIMEOUT_PATHS = ['enqueue_wepp_pipeline', 'enqueue_wepp_noprep_pipeline',
                  'enqueue_watershed_pipeline', 'enqueue_watershed_noprep_pipeline']


@pytest.mark.parametrize('name', _TIMEOUT_PATHS)
@pytest.mark.parametrize('single_storm', [False, True])
def test_all_paths_scale_only_continuous_watershed_leaf(tmp_path, name, single_storm):
    wepp, climate, tasks = _timeout_pipeline_inputs(tmp_path, single_storm=single_storm)
    if 'noprep' in name:
        # A checkout can differ from durable settings; never resize or rewrite its inputs.
        climate.input_years = 1
        wepp.watershed_instance.sub_n = 1
    before = (tmp_path / 'pw0.run').read_bytes()
    q = _DummyQueue(); parent = _make_parent_job()
    _call_timeout_pipeline(name, q, parent, wepp, climate, tasks)
    leaf = next(c for c in q.calls if c['func'] is tasks.run_watershed_rq)
    assert leaf['timeout'] == (43200 if single_storm else 97200)
    if single_storm:
        assert leaf['meta'] is None
    else:
        budget = leaf['meta']['watershed_timeout']
        assert (budget['years'], budget['hillslopes']) == (1000, 1908)
        assert budget['workload_source'] == ('prepared_run_file' if 'noprep' in name else 'controllers')
    assert all(c['timeout'] in (None, '4h', 43200) for c in q.calls if c is not leaf)
    assert (tmp_path / 'pw0.run').read_bytes() == before


@pytest.mark.parametrize('name', _TIMEOUT_PATHS)
def test_invalid_workload_fails_before_any_child_or_parent_mutation(tmp_path, name):
    wepp, climate, tasks = _timeout_pipeline_inputs(tmp_path)
    if 'noprep' in name:
        (tmp_path / 'pw0.run').unlink()
    else:
        climate.input_years = 0
    q = _DummyQueue(); parent = _make_parent_job()
    with pytest.raises((ValueError, FileNotFoundError)):
        _call_timeout_pipeline(name, q, parent, wepp, climate, tasks)
    assert q.calls == [] and parent.meta == {} and parent.saves == 0


def test_timeout_metadata_preserves_fork_lineage_and_callback(tmp_path):
    from wepppy.rq.fork_failure import report_fork_failure
    wepp, climate, tasks = _timeout_pipeline_inputs(tmp_path)
    q = _DummyQueue(); parent = _make_parent_job()
    lineage = {'target_runid': 'timeout-test', 'source_runid': 'source-test'}
    parent.meta['fork_failure'] = lineage.copy()
    _call_timeout_pipeline('enqueue_watershed_pipeline', q, parent, wepp, climate, tasks)
    leaf = next(c for c in q.calls if c['func'] is tasks.run_watershed_rq)
    assert leaf['meta']['watershed_timeout']['timeout_seconds'] == 97200
    assert leaf['meta']['fork_failure'] == lineage
    assert leaf['on_failure'] is report_fork_failure
    assert parent.meta['fork_failure'] == lineage


@pytest.mark.parametrize('name', ['enqueue_wepp_pipeline', 'enqueue_wepp_noprep_pipeline'])
def test_hillslope_only_ignores_absent_continuous_workload(tmp_path, name):
    wepp, climate, tasks = _timeout_pipeline_inputs(tmp_path, run_watershed=False)
    del climate.input_years
    del wepp.watershed_instance
    (tmp_path / 'pw0.run').unlink()
    q = _DummyQueue()
    _call_timeout_pipeline(name, q, _make_parent_job(), wepp, climate, tasks)
    assert all(c['func'] is not tasks.run_watershed_rq for c in q.calls)


@pytest.mark.parametrize('name', _TIMEOUT_PATHS)
def test_batch_single_storm_preserves_timeout_without_continuous_inputs(tmp_path, name):
    wepp, climate, tasks = _timeout_pipeline_inputs(tmp_path, single_storm=True)
    climate.climate_mode = tasks.ClimateMode.SingleStormBatch
    climate.ss_batch_storms = [{'ss_batch_id': 'storm-a'}]
    del climate.input_years
    del wepp.watershed_instance
    (tmp_path / 'pw0.run').unlink()
    q = _DummyQueue()
    _call_timeout_pipeline(name, q, _make_parent_job(), wepp, climate, tasks)
    leaf = next(c for c in q.calls if c['func'] is tasks.run_ss_batch_watershed_rq)
    assert leaf['timeout'] == 43200 and leaf['meta'] is None
    assert all(c['func'] is not tasks.run_watershed_rq for c in q.calls)
