#!/usr/bin/env python3
"""Fail-closed receiver activation preflight for vector uploads."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path

import redis
import requests

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs


def main() -> int:
    filesystem_id = os.getenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "").strip()
    configured_root = os.getenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", "").strip()
    converter_url = os.getenv("VECTOR_UPLOAD_SHAPE_CONVERTER_URL", "").strip()
    if not filesystem_id or not configured_root:
        raise SystemExit("vector upload filesystem ID/root is not configured")
    root = Path(configured_root).resolve(strict=True)
    if not root.is_mount():
        raise SystemExit(f"configured vector upload root is not a mount point: {root}")

    descriptor, probe_name = tempfile.mkstemp(prefix=".vector-upload-preflight-", dir=root)
    try:
        os.write(descriptor, b"receiver-preflight")
        os.fsync(descriptor)
        mode = stat.S_IMODE(os.fstat(descriptor).st_mode)
    finally:
        os.close(descriptor)
        Path(probe_name).unlink(missing_ok=True)
    if mode & 0o077:
        raise SystemExit(f"vector upload root identity creates non-private files: mode={mode:o}")

    connection = redis.Redis(**redis_connection_kwargs(RedisDB.LOCK, decode_responses=True))
    connection.ping()
    totals = connection.hgetall(f"vector-upload-retention:{filesystem_id}:totals")

    binary_enabled = os.getenv("VECTOR_UPLOAD_BINARY_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    readiness: dict[str, object] | None = None
    if binary_enabled:
        if not converter_url.endswith("/v1/convert"):
            raise SystemExit("shape-converter URL must end in /v1/convert")
        ready_url = converter_url.removesuffix("/v1/convert") + "/health/ready"
        response = requests.get(ready_url, timeout=(3.0, 10.0), allow_redirects=False)
        response.raise_for_status()
        readiness = response.json()
        if readiness.get("status") != "ready" or readiness.get("geoparquet_parser") != "ready":
            raise SystemExit("shape-converter readiness does not prove the GeoParquet parser")

    print(json.dumps({
        "binary_enabled": binary_enabled,
        "converter_readiness": readiness,
        "filesystem_id": filesystem_id,
        "filesystem_root": os.fspath(root),
        "ledger_totals": totals,
        "status": "ready",
    }, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
