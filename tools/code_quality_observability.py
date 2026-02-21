#!/usr/bin/env python3
"""Generate observe-only code-quality telemetry for reviews and CI summaries.

The report is intentionally non-blocking. It highlights hotspots and changed-file
quality deltas without failing builds on threshold breaches.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any
import warnings

try:
    from radon.complexity import cc_visit  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    cc_visit = None


REPO_ROOT = Path(__file__).resolve().parents[1]

PYTHON_INCLUDE_PREFIXES = (
    "wepppy/",
    "tools/",
    "services/",
    "wctl/",
    "tests/",
    "docker/",
)

PYTHON_EXCLUDED_PATHS = {
    "wepppy/all_your_base/geo/ogrmerge.py",
}

JS_INCLUDE_PREFIXES = (
    "wepppy/weppcloud/controllers_js/",
    "wepppy/weppcloud/static-src/",
    "wepppy/weppcloud/static/js/gl-dashboard/",
    "tools/",
)

JS_EXCLUDED_SUBSTRINGS = (
    "/node_modules/",
    "/dist/",
    "/vendor/",
    "/vendor-sources/",
    "/playwright-report/",
    "/test-results/",
    "/.venv/",
    "/.docker-data/",
)

THRESHOLDS: dict[str, dict[str, float]] = {
    "python_file_sloc": {"yellow": 650, "red": 1200},
    "python_function_len": {"yellow": 80, "red": 150},
    "python_cc": {"yellow": 15, "red": 30},
    "js_file_sloc": {"yellow": 1500, "red": 2500},
    "js_cc": {"yellow": 15, "red": 30},
}

SEVERITY_ORDER = {"green": 0, "yellow": 1, "red": 2, "unknown": -1, "n/a": -1}
COMPLEXITY_RE = re.compile(r"complexity of (\d+)")


@dataclass(frozen=True)
class ChangedPath:
    path: str
    base_path: str
    status: str


def _run_git(args: list[str], *, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def git_ls_files(pattern: str) -> list[str]:
    out = _run_git(["ls-files", "-z", "--", pattern])
    if not out:
        return []
    return [entry for entry in out.split("\0") if entry]


def is_python_scope(path: str) -> bool:
    if path in PYTHON_EXCLUDED_PATHS:
        return False
    return path.endswith(".py") and any(path.startswith(prefix) for prefix in PYTHON_INCLUDE_PREFIXES)


def is_js_scope(path: str) -> bool:
    if not path.endswith(".js"):
        return False
    if not any(path.startswith(prefix) for prefix in JS_INCLUDE_PREFIXES):
        return False
    normalized = f"/{path}"
    return not any(excluded in normalized for excluded in JS_EXCLUDED_SUBSTRINGS)


def classify_severity(metric_key: str, value: float | None) -> str:
    if value is None:
        return "unknown"
    bands = THRESHOLDS[metric_key]
    if value >= bands["red"]:
        return "red"
    if value >= bands["yellow"]:
        return "yellow"
    return "green"


def trend_from_values(base: float | None, current: float | None) -> str:
    if base is None and current is None:
        return "n/a"
    if base is None:
        return "new"
    if current is None:
        return "removed"
    if current < base:
        return "improved"
    if current > base:
        return "worsened"
    return "unchanged"


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = (len(sorted_vals) - 1) * (p / 100.0)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


def summarize_distribution(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "p50": 0.0, "p75": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
    return {
        "count": float(len(values)),
        "p50": round(percentile(values, 50), 2),
        "p75": round(percentile(values, 75), 2),
        "p90": round(percentile(values, 90), 2),
        "p95": round(percentile(values, 95), 2),
        "p99": round(percentile(values, 99), 2),
        "max": round(max(values), 2),
    }


def read_file(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


def read_blob(ref: str, path: str) -> str | None:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def count_sloc(text: str, language: str) -> int:
    count = 0
    in_block_comment = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if language == "python":
            if line.startswith("#"):
                continue
            count += 1
            continue
        if language == "javascript":
            if in_block_comment:
                if "*/" in line:
                    in_block_comment = False
                continue
            if line.startswith("//"):
                continue
            if line.startswith("/*"):
                if "*/" not in line:
                    in_block_comment = True
                continue
            count += 1
            continue
        count += 1
    return count


def analyze_python_text(text: str) -> dict[str, float | None]:
    metrics: dict[str, float | None] = {
        "python_file_sloc": float(count_sloc(text, "python")),
        "python_function_len": None,
        "python_cc": None,
    }

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(text)
    except Exception:
        tree = None

    if tree is not None:
        lengths: list[float] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and getattr(node, "end_lineno", None):
                lengths.append(float(node.end_lineno - node.lineno + 1))
        if lengths:
            metrics["python_function_len"] = max(lengths)

    if cc_visit is not None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                blocks = cc_visit(text)
        except Exception:
            blocks = []
        if blocks:
            metrics["python_cc"] = float(max(block.complexity for block in blocks))
    return metrics


def analyze_js_text(text: str) -> dict[str, float | None]:
    return {"js_file_sloc": float(count_sloc(text, "javascript")), "js_cc": None}


def _normalize_eslint_path(raw: str, repo_root: Path) -> str:
    path = Path(raw)
    if path.is_absolute():
        try:
            return str(path.resolve().relative_to(repo_root))
        except Exception:
            return str(path)
    return raw


def _parse_eslint_json(stdout: str, repo_root: Path) -> tuple[dict[str, float | None], list[str]]:
    parsed: dict[str, float | None] = {}
    fatal_paths: list[str] = []
    if not stdout.strip():
        return parsed, fatal_paths

    try:
        entries = json.loads(stdout)
    except Exception:
        return parsed, fatal_paths

    for entry in entries:
        file_path = _normalize_eslint_path(str(entry.get("filePath", "")), repo_root)
        messages = entry.get("messages") or []
        complexity_values: list[float] = []
        has_fatal = False
        for message in messages:
            if message.get("fatal"):
                has_fatal = True
                continue
            if message.get("ruleId") != "complexity":
                continue
            match = COMPLEXITY_RE.search(str(message.get("message", "")))
            if match:
                complexity_values.append(float(match.group(1)))
        if has_fatal:
            parsed[file_path] = None
            fatal_paths.append(file_path)
            continue
        parsed[file_path] = max(complexity_values) if complexity_values else 1.0
    return parsed, fatal_paths


def run_eslint_complexity(paths: list[str], repo_root: Path) -> tuple[dict[str, float | None], list[str]]:
    if not paths:
        return {}, []
    if shutil.which("eslint") is None:
        return ({path: None for path in paths}, [])

    cmd = [
        "eslint",
        "--no-eslintrc",
        "--format",
        "json",
        "--rule",
        "complexity:[1,1]",
        "--env",
        "browser",
        "--env",
        "node",
        "--parser-options",
        '{"ecmaVersion":2022,"sourceType":"module"}',
        *paths,
    ]
    module_run = subprocess.run(cmd, cwd=str(repo_root), text=True, capture_output=True, check=False)
    parsed, fatal_paths = _parse_eslint_json(module_run.stdout, repo_root)

    for path in paths:
        parsed.setdefault(path, None)

    if fatal_paths:
        for fatal_path in fatal_paths:
            fallback = run_eslint_complexity_for_content(fatal_path, read_file(repo_root / fatal_path) or "")
            if fallback is not None:
                parsed[fatal_path] = fallback
    return parsed, fatal_paths


def run_eslint_complexity_for_content(filename: str, content: str) -> float | None:
    if shutil.which("eslint") is None:
        return None
    if not content:
        return None

    for source_type in ("module", "script"):
        cmd = [
            "eslint",
            "--no-eslintrc",
            "--format",
            "json",
            "--rule",
            "complexity:[1,1]",
            "--env",
            "browser",
            "--env",
            "node",
            "--parser-options",
            json.dumps({"ecmaVersion": 2022, "sourceType": source_type}),
            "--stdin",
            "--stdin-filename",
            filename,
        ]
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, input=content, capture_output=True, check=False)
        parsed, fatal = _parse_eslint_json(proc.stdout, REPO_ROOT)
        if fatal:
            continue
        value = parsed.get(filename)
        if value is not None:
            return value
    return None


def collect_changed_files(base_ref: str) -> list[ChangedPath]:
    out = _run_git(["diff", "--name-status", "--find-renames", f"{base_ref}...HEAD"], check=False)
    changed: list[ChangedPath] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith(("R", "C")) and len(parts) >= 3:
            changed.append(ChangedPath(path=parts[2], base_path=parts[1], status=status))
            continue
        if len(parts) >= 2:
            changed.append(ChangedPath(path=parts[1], base_path=parts[1], status=status))
    return changed


def highest_severity(values: list[str]) -> str:
    best = "unknown"
    best_score = -1
    for value in values:
        score = SEVERITY_ORDER.get(value, -1)
        if score > best_score:
            best = value
            best_score = score
    return best


def build_report(base_ref: str | None) -> dict[str, Any]:
    python_files = [path for path in git_ls_files("**/*.py") if is_python_scope(path)]
    js_files = [path for path in git_ls_files("**/*.js") if is_js_scope(path)]

    python_snapshot: dict[str, dict[str, float | None]] = {}
    python_prod_file_sloc: list[float] = []
    python_prod_cc: list[float] = []
    python_prod_func_len: list[float] = []
    python_hotspots_cc: list[dict[str, Any]] = []
    python_hotspots_func_len: list[dict[str, Any]] = []
    python_hotspots_file_sloc: list[dict[str, Any]] = []

    for rel_path in python_files:
        text = read_file(REPO_ROOT / rel_path)
        if text is None:
            continue
        metrics = analyze_python_text(text)
        python_snapshot[rel_path] = metrics
        python_hotspots_file_sloc.append({"path": rel_path, "value": metrics["python_file_sloc"]})
        python_hotspots_cc.append({"path": rel_path, "value": metrics["python_cc"]})
        python_hotspots_func_len.append({"path": rel_path, "value": metrics["python_function_len"]})
        if rel_path.startswith("tests/"):
            continue
        if metrics["python_file_sloc"] is not None:
            python_prod_file_sloc.append(metrics["python_file_sloc"])
        if metrics["python_cc"] is not None:
            python_prod_cc.append(metrics["python_cc"])
        if metrics["python_function_len"] is not None:
            python_prod_func_len.append(metrics["python_function_len"])

    js_snapshot: dict[str, dict[str, float | None]] = {}
    for rel_path in js_files:
        text = read_file(REPO_ROOT / rel_path)
        if text is None:
            continue
        js_snapshot[rel_path] = analyze_js_text(text)

    eslint_available = shutil.which("eslint") is not None
    js_cc_map: dict[str, float | None] = {}
    if eslint_available:
        js_cc_map, _fatal = run_eslint_complexity(js_files, REPO_ROOT)
        for rel_path, cc_value in js_cc_map.items():
            if rel_path in js_snapshot:
                js_snapshot[rel_path]["js_cc"] = cc_value

    js_source_sloc_values: list[float] = [
        metrics["js_file_sloc"] for metrics in js_snapshot.values() if metrics["js_file_sloc"] is not None
    ]
    js_source_cc_values: list[float] = [value for value in js_cc_map.values() if value is not None]

    changed_report: list[dict[str, Any]] = []
    if base_ref:
        for changed in collect_changed_files(base_ref):
            is_python = is_python_scope(changed.path) or is_python_scope(changed.base_path)
            is_js = is_js_scope(changed.path) or is_js_scope(changed.base_path)
            if not (is_python or is_js):
                continue

            current_text = read_file(REPO_ROOT / changed.path) if (REPO_ROOT / changed.path).exists() else None
            base_text = read_blob(base_ref, changed.base_path)
            entry: dict[str, Any] = {
                "path": changed.path,
                "base_path": changed.base_path,
                "status": changed.status,
                "language": "python" if is_python else "javascript",
                "metrics": [],
            }

            if is_python:
                base_metrics = analyze_python_text(base_text) if base_text is not None else {}
                current_metrics = analyze_python_text(current_text) if current_text is not None else {}
                for key in ("python_file_sloc", "python_function_len", "python_cc"):
                    base_value = base_metrics.get(key)
                    current_value = current_metrics.get(key)
                    metric = {
                        "name": key,
                        "base": base_value,
                        "current": current_value,
                        "trend": trend_from_values(base_value, current_value),
                        "severity": classify_severity(key, current_value if current_value is not None else None),
                    }
                    entry["metrics"].append(metric)
            else:
                base_metrics = analyze_js_text(base_text) if base_text is not None else {}
                current_metrics = analyze_js_text(current_text) if current_text is not None else {}

                base_cc = run_eslint_complexity_for_content(changed.base_path, base_text or "")
                current_cc = run_eslint_complexity_for_content(changed.path, current_text or "")

                for key, base_value, current_value in (
                    ("js_file_sloc", base_metrics.get("js_file_sloc"), current_metrics.get("js_file_sloc")),
                    ("js_cc", base_cc, current_cc),
                ):
                    metric = {
                        "name": key,
                        "base": base_value,
                        "current": current_value,
                        "trend": trend_from_values(base_value, current_value),
                        "severity": classify_severity(key, current_value if current_value is not None else None),
                    }
                    entry["metrics"].append(metric)

            entry["highest_severity"] = highest_severity([metric["severity"] for metric in entry["metrics"]])
            changed_report.append(entry)

    python_hotspots_file_sloc = sorted(
        [item for item in python_hotspots_file_sloc if item["value"] is not None],
        key=lambda item: float(item["value"]),
        reverse=True,
    )
    python_hotspots_cc = sorted(
        [item for item in python_hotspots_cc if item["value"] is not None],
        key=lambda item: float(item["value"]),
        reverse=True,
    )
    python_hotspots_func_len = sorted(
        [item for item in python_hotspots_func_len if item["value"] is not None],
        key=lambda item: float(item["value"]),
        reverse=True,
    )
    js_hotspots_file_sloc = sorted(
        [dict(path=path, value=metrics["js_file_sloc"]) for path, metrics in js_snapshot.items() if metrics["js_file_sloc"] is not None],
        key=lambda item: float(item["value"]),
        reverse=True,
    )
    js_hotspots_cc = sorted(
        [dict(path=path, value=value) for path, value in js_cc_map.items() if value is not None],
        key=lambda item: float(item["value"]),
        reverse=True,
    )

    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "observe-only",
        "base_ref": base_ref,
        "thresholds": THRESHOLDS,
        "tooling": {
            "radon_available": cc_visit is not None,
            "eslint_available": eslint_available,
            "python_version": _python_version(),
        },
        "overall": {
            "python_prod_file_sloc": summarize_distribution(python_prod_file_sloc),
            "python_prod_max_function_len": summarize_distribution(python_prod_func_len),
            "python_prod_max_cc": summarize_distribution(python_prod_cc),
            "js_source_file_sloc": summarize_distribution(js_source_sloc_values),
            "js_source_max_cc": summarize_distribution(js_source_cc_values),
        },
        "hotspots": {
            "python_file_sloc_top20": python_hotspots_file_sloc[:20],
            "python_max_function_len_top20": python_hotspots_func_len[:20],
            "python_max_cc_top20": python_hotspots_cc[:20],
            "js_file_sloc_top20": js_hotspots_file_sloc[:20],
            "js_max_cc_top20": js_hotspots_cc[:20],
        },
        "changed_files": changed_report,
    }


def _python_version() -> str:
    proc = subprocess.run(["python3", "--version"], text=True, capture_output=True, check=False)
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    return proc.stderr.strip() or "unknown"


def _format_number(value: float | None) -> str:
    if value is None:
        return "n/a"
    if abs(value - int(value)) < 1e-9:
        return str(int(value))
    return f"{value:.2f}"


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Code Quality Observability Report")
    lines.append("")
    lines.append(f"- Mode: `{report['mode']}` (non-blocking)")
    lines.append(f"- Generated (UTC): `{report['generated_at_utc']}`")
    base_ref = report.get("base_ref")
    lines.append(f"- Base ref: `{base_ref}`" if base_ref else "- Base ref: _not provided_")
    lines.append("")
    lines.append("## Threshold Bands")
    lines.append("")
    lines.append("| Metric | Yellow | Red |")
    lines.append("| --- | ---: | ---: |")
    for key, bands in report["thresholds"].items():
        lines.append(f"| `{key}` | {int(bands['yellow'])} | {int(bands['red'])} |")
    lines.append("")
    lines.append("## Tooling")
    lines.append("")
    lines.append(f"- `radon` available: `{report['tooling']['radon_available']}`")
    lines.append(f"- `eslint` available: `{report['tooling']['eslint_available']}`")
    lines.append(f"- Python runtime: `{report['tooling']['python_version']}`")
    lines.append("")
    lines.append("## Overall Baseline")
    lines.append("")
    lines.append("| Distribution | Count | p50 | p75 | p90 | p95 | p99 | Max |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for metric_name, summary in report["overall"].items():
        lines.append(
            f"| `{metric_name}` | {int(summary['count'])} | {summary['p50']} | {summary['p75']} | "
            f"{summary['p90']} | {summary['p95']} | {summary['p99']} | {summary['max']} |"
        )

    changed_files: list[dict[str, Any]] = report.get("changed_files") or []
    lines.append("")
    lines.append("## Changed Files")
    lines.append("")
    if not changed_files:
        lines.append("_No changed-file analysis available (base ref missing or no analyzable files changed)._")
    else:
        red_count = sum(1 for entry in changed_files if entry.get("highest_severity") == "red")
        yellow_count = sum(1 for entry in changed_files if entry.get("highest_severity") == "yellow")
        worsened_count = sum(
            1 for entry in changed_files for metric in entry["metrics"] if metric.get("trend") == "worsened"
        )
        lines.append(
            f"- Files analyzed: `{len(changed_files)}`; highest severity red: `{red_count}`, "
            f"yellow: `{yellow_count}`; worsened metric entries: `{worsened_count}`"
        )
        lines.append("")
        lines.append("| File | Lang | Highest | Key Metric Deltas |")
        lines.append("| --- | --- | --- | --- |")
        for entry in changed_files:
            metric_bits: list[str] = []
            for metric in entry["metrics"]:
                metric_bits.append(
                    f"{metric['name']} {_format_number(metric['base'])}->{_format_number(metric['current'])} "
                    f"({metric['trend']}, {metric['severity']})"
                )
            delta_text = "<br>".join(metric_bits) if metric_bits else "n/a"
            lines.append(
                f"| `{entry['path']}` | `{entry['language']}` | `{entry['highest_severity']}` | {delta_text} |"
            )

    lines.append("")
    lines.append("## Hotspots (Current Tree)")
    lines.append("")
    for section_name, items in report["hotspots"].items():
        lines.append(f"### `{section_name}`")
        if not items:
            lines.append("")
            lines.append("_No entries._")
            lines.append("")
            continue
        lines.append("")
        lines.append("| Path | Value |")
        lines.append("| --- | ---: |")
        for item in items[:10]:
            lines.append(f"| `{item['path']}` | {_format_number(item['value'])} |")
        lines.append("")

    lines.append("## Review Guidance")
    lines.append("")
    lines.append("- This report is observe-only: it does not block merges.")
    lines.append("- Use changed-file deltas to spot opportunistic cleanup candidates.")
    lines.append("- Prefer incremental reductions when touching hotspot files.")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate non-blocking code-quality observability telemetry.")
    parser.add_argument("--base-ref", default=None, help="Optional git base ref for changed-file delta analysis.")
    parser.add_argument("--json-out", default="code-quality-report.json", help="Path to write JSON report.")
    parser.add_argument("--md-out", default="code-quality-summary.md", help="Path to write Markdown summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.base_ref)
    json_path = Path(args.json_out)
    md_path = Path(args.md_out)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote JSON report to {json_path}")
    print(f"Wrote Markdown summary to {md_path}")
    print("Observe-only mode: no threshold-based failure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
