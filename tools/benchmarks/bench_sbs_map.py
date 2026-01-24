#!/usr/bin/env python
"""Benchmark hot paths in wepppy.nodb.mods.baer.sbs_map."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
import time

from wepppy.nodb.mods.baer import sbs_map as sbs_map_module
from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap

DEFAULT_FIXTURES = [
    "/wc1/runs/sh/short-order-slickness/disturbed/prediction_wgs84_merged.tif",
    "/wc1/runs/de/decimal-pleasing/disturbed/Rattlesnake.tif",
]


def _sanitize_result(result):
    if result is None:
        return None
    if isinstance(result, (str, int, float, bool)):
        return result
    if isinstance(result, tuple) and len(result) == 2:
        left, right = result
        if isinstance(left, (str, int, float, bool)) and isinstance(right, (str, int, float, bool)):
            return (left, right)
    return None


def _time_call(label: str, func) -> dict:
    start = time.perf_counter()
    try:
        result = func()
        elapsed = time.perf_counter() - start
        return {"label": label, "seconds": elapsed, "error": None, "result": _sanitize_result(result)}
    except Exception as exc:  # pragma: no cover - bench helper
        elapsed = time.perf_counter() - start
        return {"label": label, "seconds": elapsed, "error": str(exc), "result": None}


def benchmark(path: str, run_data: bool, run_export: bool) -> dict:
    output: dict = {"path": path, "basename": os.path.basename(path), "steps": []}

    output["steps"].append(
        _time_call("sbs_map_sanity_check", lambda: sbs_map_module.sbs_map_sanity_check(path))
    )

    output["steps"].append(
        _time_call("get_sbs_color_table", lambda: sbs_map_module.get_sbs_color_table(path))
    )

    sbs_container = {"instance": None}

    def _init_sbs():
        sbs_container["instance"] = SoilBurnSeverityMap(path)
        return "ok"

    output["steps"].append(_time_call("SoilBurnSeverityMap.__init__", _init_sbs))

    def _get_instance():
        if sbs_container["instance"] is None:
            sbs_container["instance"] = SoilBurnSeverityMap(path)
        return sbs_container["instance"]

    output["steps"].append(
        _time_call("SoilBurnSeverityMap.class_map", lambda: _get_instance().class_map)
    )
    output["steps"].append(
        _time_call("SoilBurnSeverityMap.class_pixel_map", lambda: _get_instance().class_pixel_map)
    )

    if run_data:
        output["steps"].append(
            _time_call("SoilBurnSeverityMap.data", lambda: _get_instance().data)
        )

    if run_export:
        with tempfile.TemporaryDirectory(prefix="sbs-bench-") as tmpdir:
            dst_path = Path(tmpdir) / f"{Path(path).stem}.4class.tif"
            output["steps"].append(
                _time_call(
                    "SoilBurnSeverityMap.export_4class_map",
                    lambda: _get_instance().export_4class_map(str(dst_path)),
                )
            )
            output["export_path"] = str(dst_path)
            output["export_size_bytes"] = dst_path.stat().st_size if dst_path.exists() else None

    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", default=DEFAULT_FIXTURES)
    parser.add_argument("--skip-data", action="store_true")
    parser.add_argument("--skip-export", action="store_true")
    parser.add_argument("--json", dest="json_path")
    args = parser.parse_args()

    results = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "paths": args.paths,
        "skip_data": bool(args.skip_data),
        "skip_export": bool(args.skip_export),
        "benchmarks": [benchmark(path, not args.skip_data, not args.skip_export) for path in args.paths],
    }

    payload = json.dumps(results, indent=2)
    if args.json_path:
        Path(args.json_path).write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
