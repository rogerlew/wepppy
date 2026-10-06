"""Serialize and inspect disposable WRT-02 RQ graphs without executing them."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import redis
from rq import Queue
from rq.job import Dependency, Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.job_info import get_wepppy_rq_job_info
from wepppy.rq.omni_rq import (
    TIMEOUT,
    _compile_hillslope_summaries_rq,
    _finalize_omni_contrasts_rq,
    _finalize_omni_scenarios_rq,
    run_omni_contrast_rq,
    run_omni_contrasts_rq,
    run_omni_scenario_rq,
    run_omni_scenarios_rq,
)
from wepppy.rq.watershed_timeout import watershed_timeout_options


def _snapshot(job: Job) -> dict[str, object]:
    return {
        "id": job.id,
        "func": job.func_name,
        "timeout": job.timeout,
        "meta": job.meta,
        "dependencies": [dependency.id for dependency in job.fetch_dependencies()],
    }


def main() -> None:
    connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
    queue = Queue(f"wrt02-validation-{uuid4().hex}", connection=connection)
    job_ids: list[str] = []
    evidence: dict[str, object] = {
        "queue": queue.name,
        "source_revision": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "uid": os.getuid(),
        "gid": os.getgid(),
        "graphs_executed": False,
        "cases": [],
    }
    options = watershed_timeout_options(
        SimpleNamespace(
            wepp_bin="wepp_dcc52a6",
            watershed_instance=SimpleNamespace(sub_n=1908),
        ),
        SimpleNamespace(is_single_storm=False, input_years=500),
        TIMEOUT,
    )
    assert options["timeout"] == 50_400

    try:
        scenario_parent = queue.enqueue_call(
            run_omni_scenarios_rq,
            args=("wrt02-validation",),
            timeout=TIMEOUT,
        )
        job_ids.append(scenario_parent.id)
        scenario_first = queue.enqueue_call(
            run_omni_scenario_rq,
            args=("wrt02-validation", {"type": 9}),
            **options,
        )
        job_ids.append(scenario_first.id)
        scenario_second = queue.enqueue_call(
            run_omni_scenario_rq,
            args=("wrt02-validation", {"type": 1}),
            **options,
            depends_on=scenario_first,
        )
        job_ids.append(scenario_second.id)
        scenario_compile = queue.enqueue_call(
            _compile_hillslope_summaries_rq,
            args=("wrt02-validation",),
            timeout=TIMEOUT,
            depends_on=scenario_second,
        )
        job_ids.append(scenario_compile.id)
        scenario_final = queue.enqueue_call(
            _finalize_omni_scenarios_rq,
            args=("wrt02-validation",),
            timeout=TIMEOUT,
            depends_on=scenario_compile,
        )
        job_ids.append(scenario_final.id)
        scenario_parent.meta.update({
            "jobs:0,scenario:undisturbed": scenario_first.id,
            "jobs:1,scenario:uniform_low": scenario_second.id,
            "jobs:2,func:_compile_hillslope_summaries_rq": scenario_compile.id,
            "jobs:3,func:_finalize_omni_scenarios_rq": scenario_final.id,
        })
        scenario_parent.save()

        contrast_parent = queue.enqueue_call(
            run_omni_contrasts_rq,
            args=("wrt02-validation",),
            timeout=TIMEOUT,
        )
        job_ids.append(contrast_parent.id)
        contrast_first = queue.enqueue_call(
            run_omni_contrast_rq,
            args=("wrt02-validation", 1),
            **options,
        )
        job_ids.append(contrast_first.id)
        contrast_second = queue.enqueue_call(
            run_omni_contrast_rq,
            args=("wrt02-validation", 2),
            **options,
            depends_on=Dependency(jobs=[contrast_first], allow_failure=True),
        )
        job_ids.append(contrast_second.id)
        contrast_final = queue.enqueue_call(
            _finalize_omni_contrasts_rq,
            args=("wrt02-validation",),
            timeout=TIMEOUT,
            depends_on=Dependency(jobs=[contrast_second], allow_failure=True),
        )
        job_ids.append(contrast_final.id)
        contrast_parent.meta.update({
            "jobs:contrast:1": contrast_first.id,
            "jobs:contrast:2": contrast_second.id,
            "jobs:finalize:_finalize_omni_contrasts_rq": contrast_final.id,
        })
        contrast_parent.save()

        jobs = [Job.fetch(job_id, connection=connection) for job_id in job_ids]
        dynamic_leaves = [
            job for job in jobs
            if job.func_name.endswith((".run_omni_scenario_rq", ".run_omni_contrast_rq"))
        ]
        fixed_nonleaves = [
            job for job in jobs
            if job.func_name.endswith((
                "._compile_hillslope_summaries_rq",
                "._finalize_omni_scenarios_rq",
                "._finalize_omni_contrasts_rq",
            ))
        ]
        assert len(dynamic_leaves) == 4
        assert all(job.timeout == 50_400 for job in dynamic_leaves)
        assert all(job.meta["watershed_timeout"]["policy"] == "WRT-01" for job in dynamic_leaves)
        assert all(job.meta["watershed_timeout"]["years"] == 500 for job in dynamic_leaves)
        assert all(job.meta["watershed_timeout"]["hillslopes"] == 1908 for job in dynamic_leaves)
        assert all(job.timeout == TIMEOUT and "watershed_timeout" not in job.meta
                   for job in fixed_nonleaves)
        assert [job.id for job in scenario_second.fetch_dependencies()] == [scenario_first.id]
        assert [job.id for job in scenario_compile.fetch_dependencies()] == [scenario_second.id]
        assert [job.id for job in scenario_final.fetch_dependencies()] == [scenario_compile.id]
        assert [job.id for job in contrast_second.fetch_dependencies()] == [contrast_first.id]
        assert [job.id for job in contrast_final.fetch_dependencies()] == [contrast_second.id]

        evidence["cases"] = [
            {
                "workflow": "scenarios",
                "jobs": [_snapshot(job) for job in jobs[:5]],
                "job_info": get_wepppy_rq_job_info(scenario_parent.id),
            },
            {
                "workflow": "contrasts",
                "jobs": [_snapshot(job) for job in jobs[5:]],
                "job_info": get_wepppy_rq_job_info(contrast_parent.id),
            },
        ]
    finally:
        for job_id in reversed(job_ids):
            if connection.exists(Job.key_for(job_id)):
                Job.fetch(job_id, connection=connection).delete(
                    remove_from_queue=True,
                    delete_dependents=False,
                )
        queue.delete(delete_jobs=False)

    evidence["cleanup_verified"] = (
        all(not connection.exists(Job.key_for(job_id)) for job_id in job_ids)
        and not connection.exists(queue.key)
    )
    assert evidence["cleanup_verified"]
    output_path = Path(__file__).with_name("live_rq.json")
    output_path.write_text(json.dumps(evidence, indent=2, default=str) + "\n")
    print(f"Validated two live graphs; removed {len(job_ids)} disposable jobs.")


if __name__ == "__main__":
    main()
