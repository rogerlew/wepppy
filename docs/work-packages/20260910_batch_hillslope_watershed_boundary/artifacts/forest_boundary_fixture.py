"""Prepare a bounded real-controller Forest fixture; no scientific tasks enabled.

Run in the normal weppcloud container. The caller supplies a unique batch name.
This script never deletes a project and never submits jobs implicitly.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import os

from wepppy.nodb.batch_runner import BatchRunner
from wepppy.nodb.redis_prep import TaskEnum
from wepppy.topo.watershed_collection import WatershedCollection
from wepppy.weppcloud.utils.helpers import get_batch_root_dir


def prepare(name: str) -> None:
    if not name.startswith("codex-boundary-20260911-") or "/" in name or "\\" in name:
        raise ValueError("Use a unique codex-boundary-20260911- identifier")
    wd = Path(get_batch_root_dir()) / name
    wd.mkdir(exist_ok=False)
    runner = BatchRunner(str(wd), "batch/default_batch.cfg", "0.cfg")
    resource = Path(runner.resources_dir) / "fixture.geojson"
    resource.write_text(json.dumps({"type": "FeatureCollection", "features": [{
        "type": "Feature", "id": "leaf", "properties": {},
        "geometry": {"type": "Polygon", "coordinates": [[
            [-116.91, 46.73], [-116.90, 46.73], [-116.90, 46.74],
            [-116.91, 46.74], [-116.91, 46.73],
        ]]},
    }]}))
    collection = WatershedCollection(str(resource))
    runner.register_geojson(collection)
    validation = collection.validate_template("{'leaf'}")
    assert validation["summary"]["is_valid"]
    runner.runid_template_state = {**validation, "status": "ok"}
    runner.update_run_directives({task.value: task == TaskEnum.if_exists_rmtree for task in runner.DEFAULT_TASKS})
    print(json.dumps({"batch_name": name, "workspace": str(wd),
                      "uid": os.getuid(), "gid": os.getgid(),
                      "enabled_directives": [task.value for task in runner.DEFAULT_TASKS if runner.is_task_enabled(task)],
                      "leaf_ids": [feature.runid for feature in runner.get_watershed_features_lpt()]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("batch_name")
    prepare(parser.parse_args().batch_name)
