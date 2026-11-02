"""Reproduce the audited kslast branch using its actual source AST.

This is a source-function probe, NOT an end-to-end MOFE or native WEPP test.
It imports no WEPPpy application dependencies and writes no run artifacts.
Run from any directory with Python 3; optionally pass --repo /path/to/wepppy.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[4])
    args = parser.parse_args()
    source = args.repo / "wepppy/wepp/soils/utils/wepp_soil_util.py"
    raw = source.read_bytes()
    tree = ast.parse(raw, filename=str(source))
    soil_class = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                      and node.name == "WeppSoilUtil")
    function = next(node for node in soil_class.body if isinstance(node, ast.FunctionDef)
                    and node.name == "modify_kslast")
    namespace = {"Optional": Optional, "Dict": Dict, "Any": Any}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
    results = []
    for names in (("developed high", "forest"), ("forest", "developed high")):
        soil = SimpleNamespace(obj={
            "header": [],
            "ofes": [{"luse": name, "res_lyr": {"kslast": float(i + 1)}}
                     for i, name in enumerate(names)],
            "res_lyr": {"kslast": 2.0},
        })
        namespace["modify_kslast"](soil, 99.0)
        results.append({"ofe_landuses": names, "before": [1.0, 2.0],
                        "override": 99.0,
                        "after": [ofe["res_lyr"]["kslast"] for ofe in soil.obj["ofes"]]})
    print(json.dumps({
        "scope": "AST-extracted source-function probe; not end-to-end",
        "source": str(source), "source_sha256": hashlib.sha256(raw).hexdigest(),
        "kslast_cases": results,
        "string_ofe_sort_demonstration": sorted(str(i) for i in range(1, 13)),
        "sort_scope": "Python sort demonstration; RAP writer not executed",
    }, indent=2))


if __name__ == "__main__":
    main()
