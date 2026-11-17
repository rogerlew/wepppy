"""Reproduce Roads review metrics without importing production controllers."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import textwrap

import radon
from radon.complexity import cc_visit


ROOT = Path(__file__).resolve().parents[5]
BASE = "96555f2f95326350d2d7007c19327378ea831ab0"
MODULES = (
    "roads", "_constants", "_inputs", "_prepare", "_soil_inputs",
    "_management_inputs", "_slope_inputs", "_spatial", "_queries",
    "_parameterization_support", "_pass_routing", "_native_runner",
    "_reporting", "_execution", "_point_source", "_unrutted_execution",
    "_unrutted_planning", "_unrutted_native",
)


def git(*arguments):
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True)


def analyze(source):
    tree = ast.parse(source)
    metrics = analyzer.analyze_python_text(source)
    functions = [node for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    longest = max(functions, key=lambda node: node.end_lineno - node.lineno + 1, default=None)
    metrics["longest_function"] = None if longest is None else longest.name
    metrics["broad_exception_handlers"] = sum(
        node.type is None or any(isinstance(part, ast.Name) and part.id in {"Exception", "BaseException"}
                                 for part in ast.walk(node.type))
        for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)
    )
    return metrics


spec = importlib.util.spec_from_file_location("quality_observability", ROOT / "tools/code_quality_observability.py")
analyzer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = analyzer
spec.loader.exec_module(analyzer)
rows = []
for module in MODULES:
    relative = f"wepppy/nodb/mods/roads/{module}.py"
    source = (ROOT / relative).read_text()
    exists = subprocess.run(["git", "cat-file", "-e", f"{BASE}:{relative}"], cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    rows.append(dict(path=relative, sha256=hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
                     baseline=analyze(git("show", f"{BASE}:{relative}")) if exists else None,
                     candidate=analyze(source)))

baseline_source = git("show", f"{BASE}:wepppy/nodb/mods/roads/roads.py")
baseline_class = next(node for node in ast.parse(baseline_source).body
                      if isinstance(node, ast.ClassDef) and node.name == "Roads")
before_methods = {node.name: node for node in baseline_class.body if isinstance(node, ast.FunctionDef)}
hotspots = []
for module, name in (("_inputs", "_validated_params_payload"),
                     ("_queries", "query_segment_detail"),
                     ("_queries", "_last_parameterization_readback"),
                     ("_reporting", "_regenerate_roads_report_resources")):
    source = (ROOT / f"wepppy/nodb/mods/roads/{module}.py").read_text()
    current = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == name)
    previous = before_methods[name]
    before_cc = cc_visit(textwrap.dedent(ast.get_source_segment(baseline_source, previous)))[0].complexity
    after_cc = cc_visit(ast.get_source_segment(source, current))[0].complexity
    hotspots.append(dict(module=module, function=name, baseline_complexity=before_cc,
                         candidate_complexity=after_cc,
                         body_ast_identical=ast.dump(ast.Module(body=previous.body, type_ignores=[]))
                         == ast.dump(ast.Module(body=current.body, type_ignores=[]))))

print(json.dumps(dict(
    measured_at_utc=datetime.now(timezone.utc).isoformat(),
    baseline=BASE,
    candidate_head=git("rev-parse", "HEAD").strip(),
    interpreter=sys.executable,
    python_version=sys.version,
    radon_version=radon.__version__,
    radon_module=radon.__file__,
    analyzer_sha256=hashlib.sha256((ROOT / "tools/code_quality_observability.py").read_bytes()).hexdigest(),
    note="Null baseline means new path; its code was extracted from roads.py, not newly created behavior. Root metrics are observe-only.",
    files=rows,
    aggregate_baseline_sloc=rows[0]["baseline"]["python_file_sloc"],
    aggregate_candidate_sloc=sum(row["candidate"]["python_file_sloc"] for row in rows),
    residual_hotspot_equivalence=hotspots,
), indent=2))
