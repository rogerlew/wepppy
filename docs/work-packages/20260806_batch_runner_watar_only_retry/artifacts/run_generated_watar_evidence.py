"""Run WATAR-only evidence against an explicitly prepared disposable leaf.

This is an operator evidence script, not production code. The caller must copy
the local source batch leaf into ``EVIDENCE_ROOT`` before invoking it. The
script never deletes either source or evidence data.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from types import SimpleNamespace

from wepppy.nodb import batch_runner as batch_runner_module
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.nodb.core import Landuse
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum


EVIDENCE_ROOT = Path("/wc1/batch/codex-watar-retry-evidence-20260806")
EVIDENCE_LEAF = EVIDENCE_ROOT / "runs" / "evidence"
EVIDENCE_RUNID = "batch;;codex-watar-retry-evidence-20260806;;evidence"


def _state(document: dict) -> dict:
    return document.get("py/state", document)


def _rewrite_working_directories() -> None:
    for path in EVIDENCE_LEAF.rglob("*.nodb"):
        document = json.loads(path.read_text(encoding="utf-8"))
        state = _state(document)
        if "wd" in state:
            state["wd"] = str(EVIDENCE_LEAF)
        path.write_text(json.dumps(document), encoding="utf-8")

    base_climate_path = EVIDENCE_ROOT / "_base" / "climate.nodb"
    base_document = json.loads(base_climate_path.read_text(encoding="utf-8"))
    base_state = _state(base_document)
    base_state["wd"] = str(EVIDENCE_ROOT / "_base")
    base_state["_climatestation"] = None
    base_state["_climatestation_mode"] = {
        "py/reduce": [
            {"py/type": "wepppy.nodb.core.climate.ClimateStationMode"},
            {"py/tuple": [-1]},
        ]
    }
    base_climate_path.write_text(json.dumps(base_document), encoding="utf-8")

    leaf_climate_path = EVIDENCE_LEAF / "climate.nodb"
    leaf_document = json.loads(leaf_climate_path.read_text(encoding="utf-8"))
    leaf_state = _state(leaf_document)
    leaf_state["_climatestation"] = "wa450872"
    leaf_state["_climatestation_mode"] = {
        "py/reduce": [
            {"py/type": "wepppy.nodb.core.climate.ClimateStationMode"},
            {"py/tuple": [0]},
        ]
    }
    leaf_climate_path.write_text(json.dumps(leaf_document), encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not EVIDENCE_LEAF.is_dir():
        raise FileNotFoundError(f"prepared evidence leaf is missing: {EVIDENCE_LEAF}")

    _rewrite_working_directories()
    NoDbBase.cleanup_run_instances(str(EVIDENCE_LEAF))

    evidence_paths = [
        EVIDENCE_LEAF / "climate.nodb",
        EVIDENCE_LEAF / "climate" / "wepp.cli",
        EVIDENCE_LEAF / "wepp" / "output" / "interchange" / "H.pass.parquet",
        EVIDENCE_LEAF / "wepp" / "output" / "interchange" / "H.wat.parquet",
        EVIDENCE_LEAF / "wepp" / "output" / "interchange" / "totalwatsed3.parquet",
    ]
    missing = [str(path) for path in evidence_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing evidence inputs: " + ", ".join(missing))
    before = {
        str(path.relative_to(EVIDENCE_LEAF)): _sha256(path)
        for path in evidence_paths
    }

    prep = RedisPrep.getInstance(str(EVIDENCE_LEAF))
    prep.remove_all_timestamp()
    prep.timestamp(TaskEnum.build_climate)
    prep.timestamp(TaskEnum.run_wepp_hillslopes)
    prep.timestamp(TaskEnum.run_wepp_watershed)
    timestamps_before = {
        task.value: prep[task]
        for task in (
            TaskEnum.build_climate,
            TaskEnum.run_wepp_hillslopes,
            TaskEnum.run_wepp_watershed,
            TaskEnum.run_watar,
        )
    }

    runner = BatchRunner.__new__(BatchRunner)
    runner.wd = str(EVIDENCE_ROOT)
    runner._rq_job_ids = {}
    runner._run_directives = {
        task: task is TaskEnum.run_watar for task in BatchRunner.DEFAULT_TASKS
    }
    runner._get_run_logger = lambda _runid: logging.getLogger("watar-evidence")

    batch_runner_module.get_wd = lambda _runid: str(EVIDENCE_LEAF)
    # The copied leaf already contains checksum-verified interchange files.
    # Avoid regeneration because its configured WEPP binary is not vendored in
    # this development checkout; _run_watar_stage still verifies all required
    # files immediately after these helpers return.
    batch_runner_module.ensure_hillslope_interchange = lambda *_args, **_kwargs: None
    batch_runner_module.ensure_totalwatsed3 = lambda *_args, **_kwargs: None
    batch_runner_module.ensure_watershed_interchange = lambda *_args, **_kwargs: None
    original_identify_burn_class = Landuse.identify_burn_class
    Landuse.identify_burn_class = lambda _self, _topaz_id: "Low"
    try:
        runner.run_batch_project(SimpleNamespace(runid="evidence"))
    finally:
        Landuse.identify_burn_class = original_identify_burn_class

    after = {
        str(path.relative_to(EVIDENCE_LEAF)): _sha256(path)
        for path in evidence_paths
    }
    timestamps_after = {
        task.value: prep[task]
        for task in (
            TaskEnum.build_climate,
            TaskEnum.run_wepp_hillslopes,
            TaskEnum.run_wepp_watershed,
            TaskEnum.run_watar,
        )
    }
    ash_outputs = sorted(
        str(path.relative_to(EVIDENCE_LEAF))
        for path in (EVIDENCE_LEAF / "ash").glob("H*_ash.parquet")
    )
    ashpost_outputs = sorted(
        str(path.relative_to(EVIDENCE_LEAF))
        for path in (EVIDENCE_LEAF / "ash" / "post").glob("*.parquet")
    )

    assert after == before
    for prerequisite in (
        TaskEnum.build_climate,
        TaskEnum.run_wepp_hillslopes,
        TaskEnum.run_wepp_watershed,
    ):
        assert timestamps_after[prerequisite.value] == timestamps_before[prerequisite.value]
    assert timestamps_before[TaskEnum.run_watar.value] is None
    assert timestamps_after[TaskEnum.run_watar.value] is not None
    assert ash_outputs
    assert ashpost_outputs

    print(
        json.dumps(
            {
                "runid": EVIDENCE_RUNID,
                "unchanged_input_sha256": after,
                "timestamps_before": timestamps_before,
                "timestamps_after": timestamps_after,
                "ash_outputs": ash_outputs,
                "ashpost_outputs": ashpost_outputs,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
