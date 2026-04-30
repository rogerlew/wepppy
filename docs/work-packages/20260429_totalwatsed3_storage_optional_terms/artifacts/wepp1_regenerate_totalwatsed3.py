#!/usr/bin/env python3
"""Regenerate uncapped-spectacular totalwatsed3 on wepp1 without service restart."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

from wepppy.nodb.core import Wepp
from wepppy.wepp.interchange import run_totalwatsed3


RUN_DIR = Path("/wc1/runs/un/uncapped-spectacular")
INTERCHANGE_DIR = RUN_DIR / "wepp" / "output" / "interchange"
OUTPUT = INTERCHANGE_DIR / "totalwatsed3.parquet"


def main() -> int:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = OUTPUT.with_suffix(f".parquet.bak.{timestamp}")
    if OUTPUT.exists():
        shutil.copy2(OUTPUT, backup)

    wepp = Wepp.getInstance(str(RUN_DIR))
    generated = run_totalwatsed3(INTERCHANGE_DIR, baseflow_opts=wepp.baseflow_opts)
    schema = pq.read_schema(generated)
    result = {
        "timestamp_utc": timestamp,
        "run_dir": str(RUN_DIR),
        "interchange_dir": str(INTERCHANGE_DIR),
        "output": str(generated),
        "backup": str(backup) if backup.exists() else None,
        "output_size_bytes": generated.stat().st_size,
        "schema_columns": schema.names,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
