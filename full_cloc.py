#!/usr/bin/env python3
"""Aggregate cloc metrics across the WEPP stack."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    path: Path
    cloc_args: Sequence[str] = field(default_factory=tuple)


BASE_CLOC_ARGS: Tuple[str, ...] = (
    "--json",
    "--quiet",
    "--fullpath",
    "--timeout=0",
    "--not-match-d=node_modules",
)

VENDOR_ASSET_REGEX = r".*vendor/.*\.(css|js)$"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run cloc across multiple repositories and summarize results."
    )
    parser.add_argument(
        "--telemetry-json",
        type=Path,
        help="Write aggregated metrics to the given JSON file.",
    )
    parser.add_argument(
        "--projects",
        nargs="+",
        choices=[
            "wepppy",
            "wepppy2",
            "peridot",
            "wepppyo3",
            "fswepp2",
            "markdown-extract",
            "rosetta",
            "WEPPcloudR",
            "wepp-forest",
            "wepp-forest-revegetation",
            "weppcloud-wbt",
        ],
        help="Optional subset of projects to include.",
    )
    parser.add_argument(
        "--cloc-bin",
        default="cloc",
        help="Path to the cloc binary (defaults to %(default)s).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Per-project timeout in seconds (defaults to %(default)s).",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("/workdir"),
        help="Root directory containing the projects (defaults to %(default)s).",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Skip projects whose directories are missing instead of failing.",
    )
    return parser.parse_args()


def ensure_cloc_available(cloc_bin: str) -> None:
    if shutil.which(cloc_bin):
        return
    raise FileNotFoundError(
        f"Unable to locate '{cloc_bin}'. Ensure cloc is installed and on PATH."
    )


def build_project_configs(base_dir: Path) -> Mapping[str, ProjectConfig]:
    return {
        "wepppy": ProjectConfig(
            "wepppy",
            base_dir / "wepppy",
            cloc_args=(f"--not-match-f={VENDOR_ASSET_REGEX}",),
        ),
        "wepppy2": ProjectConfig("wepppy2", base_dir / "wepppy2"),
        "peridot": ProjectConfig("peridot", base_dir / "peridot"),
        "wepppyo3": ProjectConfig("wepppyo3", base_dir / "wepppyo3"),
        "fswepp2": ProjectConfig(
            "fswepp2",
            base_dir / "fswepp2",
            cloc_args=(f"--not-match-f={VENDOR_ASSET_REGEX}",),
        ),
        "markdown-extract": ProjectConfig(
            "markdown-extract", base_dir / "markdown-extract"
        ),
        "rosetta": ProjectConfig("rosetta", base_dir / "rosetta"),
        "WEPPcloudR": ProjectConfig("WEPPcloudR", base_dir / "WEPPcloudR"),
        "wepp-forest": ProjectConfig("wepp-forest", base_dir / "wepp-forest"),
        "wepp-forest-revegetation": ProjectConfig(
            "wepp-forest-revegetation", base_dir / "wepp-forest-revegetation"
        ),
        "weppcloud-wbt": ProjectConfig(
            "weppcloud-wbt", base_dir / "weppcloud-wbt"
        ),
    }


def run_cloc(
    config: ProjectConfig,
    cloc_bin: str,
    timeout: int,
) -> Dict[str, Dict[str, int]]:
    cmd: List[str] = [cloc_bin, "."]
    cmd.extend(BASE_CLOC_ARGS)
    cmd.extend(config.cloc_args)
    cmd.append("--vcs=git")
    print(f"[cloc] {config.name}", file=sys.stderr)
    result = subprocess.run(
        cmd,
        cwd=config.path,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    if not result.stdout:
        raise RuntimeError(
            f"cloc produced no output for {config.name!r} (exit code {result.returncode})."
        )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as err:
        raise RuntimeError(
            f"Failed to parse cloc output for {config.name!r}: {err}\nOutput:\n{result.stdout}"
        ) from err
    if "SUM" not in data:
        raise RuntimeError(
            f"cloc output for {config.name!r} missing SUM block: {result.stdout}"
        )
    return data


def accumulate_language_totals(
    language_totals: MutableMapping[str, Dict[str, int]],
    languages: Mapping[str, Mapping[str, int]],
) -> None:
    for lang, metrics in languages.items():
        if lang in ("header", "SUM"):
            continue
        target = language_totals.setdefault(
            lang, {"nFiles": 0, "blank": 0, "comment": 0, "code": 0}
        )
        target["nFiles"] += int(metrics.get("nFiles", 0))
        target["blank"] += int(metrics.get("blank", 0))
        target["comment"] += int(metrics.get("comment", 0))
        target["code"] += int(metrics.get("code", 0))


def accumulate_summary(
    total_summary: MutableMapping[str, int], summary: Mapping[str, int]
) -> None:
    for key in ("nFiles", "blank", "comment", "code"):
        total_summary[key] += int(summary.get(key, 0))


def format_number(value: int) -> str:
    return f"{value:,}"


def print_project_breakdown(
    name: str,
    summary: Mapping[str, int],
    languages: Mapping[str, Mapping[str, int]],
) -> None:
    print(name)
    print(f"  Files   : {format_number(int(summary.get('nFiles', 0)))}")
    print(f"  Code    : {format_number(int(summary.get('code', 0)))}")
    print(f"  Comment : {format_number(int(summary.get('comment', 0)))}")
    print(f"  Blank   : {format_number(int(summary.get('blank', 0)))}")
    filtered = {
        lang: metrics
        for lang, metrics in languages.items()
        if lang not in ("header", "SUM")
    }
    if not filtered:
        print("  Languages: (none)")
        print()
        return
    print("  Languages:")
    max_lang = max(len(lang) for lang in filtered)
    sorted_langs = sorted(
        filtered.items(), key=lambda item: int(item[1].get("code", 0)), reverse=True
    )
    for lang, metrics in sorted_langs:
        files = format_number(int(metrics.get("nFiles", 0)))
        code = format_number(int(metrics.get("code", 0)))
        comment = format_number(int(metrics.get("comment", 0)))
        blank = format_number(int(metrics.get("blank", 0)))
        print(
            f"    {lang:<{max_lang}}  files={files:>8}  code={code:>10}  "
            f"comment={comment:>8}  blank={blank:>8}"
        )
    print()


def print_language_totals_table(
    language_totals: Mapping[str, Mapping[str, int]],
) -> None:
    if not language_totals:
        print("No language totals collected.")
        return
    rows: List[Tuple[str, int, int, int, int]] = [
        (
            lang,
            int(metrics.get("nFiles", 0)),
            int(metrics.get("blank", 0)),
            int(metrics.get("comment", 0)),
            int(metrics.get("code", 0)),
        )
        for lang, metrics in language_totals.items()
    ]
    rows.sort(key=lambda item: item[-1], reverse=True)
    headers = ("Language", "Files", "Blank", "Comment", "Code")
    widths = []
    for idx, header in enumerate(headers):
        values = [header]
        for row in rows:
            value = row[idx]
            values.append(f"{value:,}" if isinstance(value, int) else str(value))
        widths.append(max(len(v) for v in values))
    header_line = "  ".join(
        header.ljust(widths[idx]) if idx == 0 else header.rjust(widths[idx])
        for idx, header in enumerate(headers)
    )
    print("Language Totals")
    print(header_line)
    print("-" * len(header_line))
    for row in rows:
        formatted = []
        for idx, value in enumerate(row):
            text = f"{value:,}" if isinstance(value, int) else str(value)
            if idx == 0:
                formatted.append(text.ljust(widths[idx]))
            else:
                formatted.append(text.rjust(widths[idx]))
        print("  ".join(formatted))


def build_telemetry_payload(
    projects_payload: Sequence[Mapping[str, object]],
    language_totals: Mapping[str, Mapping[str, int]],
    overall_summary: Mapping[str, int],
) -> Dict[str, object]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "projects": list(projects_payload),
        "language_totals": [
            {
                "name": lang,
                "nFiles": int(metrics.get("nFiles", 0)),
                "blank": int(metrics.get("blank", 0)),
                "comment": int(metrics.get("comment", 0)),
                "code": int(metrics.get("code", 0)),
            }
            for lang, metrics in sorted(
                language_totals.items(),
                key=lambda item: int(item[1].get("code", 0)),
                reverse=True,
            )
        ],
        "overall_summary": {
            key: int(overall_summary.get(key, 0))
            for key in ("nFiles", "blank", "comment", "code")
        },
    }


def main() -> None:
    args = parse_args()
    ensure_cloc_available(args.cloc_bin)
    configs = build_project_configs(args.base_dir)
    selected_names = args.projects or list(configs.keys())
    projects_payload: List[Mapping[str, object]] = []
    language_totals: Dict[str, Dict[str, int]] = {}
    overall_summary: Dict[str, int] = {"nFiles": 0, "blank": 0, "comment": 0, "code": 0}
    for name in selected_names:
        if name not in configs:
            raise ValueError(f"Unknown project {name!r}.")
        config = configs[name]
        if not config.path.exists():
            if args.allow_missing:
                print(
                    f"[skip] Project path missing for {name}: {config.path}",
                    file=sys.stderr,
                )
                continue
            raise FileNotFoundError(f"Project path does not exist: {config.path}")
        data = run_cloc(config, args.cloc_bin, args.timeout)
        summary = data.get("SUM", {})
        print_project_breakdown(name, summary, data)
        accumulate_language_totals(language_totals, data)
        accumulate_summary(overall_summary, summary)
        project_languages = [
            {
                "name": lang,
                "nFiles": int(metrics.get("nFiles", 0)),
                "blank": int(metrics.get("blank", 0)),
                "comment": int(metrics.get("comment", 0)),
                "code": int(metrics.get("code", 0)),
            }
            for lang, metrics in sorted(
                data.items(),
                key=lambda item: int(item[1].get("code", 0))
                if isinstance(item[1], Mapping)
                and item[0] not in ("header", "SUM")
                else -1,
                reverse=True,
            )
            if isinstance(metrics, Mapping) and lang not in ("header", "SUM")
        ]
        projects_payload.append(
            {
                "name": name,
                "path": str(config.path),
                "summary": {
                    key: int(summary.get(key, 0))
                    for key in ("nFiles", "blank", "comment", "code")
                },
                "languages": project_languages,
            }
        )
    print_language_totals_table(language_totals)
    print()
    print(
        "Overall Summary: files={files} blank={blank} comment={comment} code={code}".format(
            files=format_number(overall_summary["nFiles"]),
            blank=format_number(overall_summary["blank"]),
            comment=format_number(overall_summary["comment"]),
            code=format_number(overall_summary["code"]),
        )
    )
    if args.telemetry_json:
        payload = build_telemetry_payload(projects_payload, language_totals, overall_summary)
        args.telemetry_json.parent.mkdir(parents=True, exist_ok=True)
        args.telemetry_json.write_text(json.dumps(payload, indent=2))
        print(f"Wrote telemetry JSON to {args.telemetry_json}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Aborted via Ctrl+C")
