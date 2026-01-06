from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
from typing import Any

from rq import get_current_job

from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.nodb.status_messenger import StatusMessenger

TIMEOUT: int = 43_200


def run_culvert_batch_rq(culvert_batch_uuid: str) -> None:
    """Entrypoint for culvert batch processing."""
    job = get_current_job()
    job_id = job.id if job is not None else "N/A"
    func_name = inspect.currentframe().f_code.co_name
    status_channel = f"{culvert_batch_uuid}:culvert_batch"

    if job is not None:
        job.meta["culvert_batch_uuid"] = culvert_batch_uuid
        job.save()

    StatusMessenger.publish(
        status_channel, f"rq:{job_id} STARTED {func_name}({culvert_batch_uuid})"
    )

    try:
        batch_root = _resolve_batch_root(culvert_batch_uuid)
        if not batch_root.is_dir():
            raise FileNotFoundError(
                f"Culvert batch root does not exist: {batch_root}"
            )

        payload_metadata = _load_payload_json(batch_root / "metadata.json")
        model_parameters = _load_payload_json(
            batch_root / "model-parameters.json"
        )

        runner = CulvertsRunner.getInstance(
            str(batch_root), allow_nonexistent=True
        )
        if runner is None:
            runner = CulvertsRunner(str(batch_root), "culvert.cfg")

        runner.run(
            culvert_batch_uuid,
            str(batch_root),
            payload_metadata,
            model_parameters=model_parameters,
        )

        StatusMessenger.publish(
            status_channel, f"rq:{job_id} COMPLETED {func_name}({culvert_batch_uuid})"
        )
    except Exception:
        StatusMessenger.publish(
            status_channel, f"rq:{job_id} EXCEPTION {func_name}({culvert_batch_uuid})"
        )
        raise


def _resolve_batch_root(culvert_batch_uuid: str) -> Path:
    culverts_root = Path(os.getenv("CULVERTS_ROOT", "/wc1/culverts")).resolve()
    return culverts_root / culvert_batch_uuid


def _load_payload_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Missing payload file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Payload JSON must be an object: {path}")
    return payload


__all__ = ["TIMEOUT", "run_culvert_batch_rq"]
