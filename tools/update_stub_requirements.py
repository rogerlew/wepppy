#!/usr/bin/env python3
"""Generate or update the stub requirements list based on mypy diagnostics."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

DEFAULT_REQUIREMENTS_PATH = Path("docker/requirements-stubs-uv.txt")
DEFAULT_COMMAND: Sequence[str] = ("python", "-m", "mypy", "--config-file", "mypy.ini", "wepppy")

HINT_PATTERN = re.compile(r'Hint:\s*"python3 -m pip install ([^"]+)"')
LIB_STUB_PATTERN = re.compile(
    r'(?:Library stubs not installed for|Cannot find implementation or library stub for module named)\s+"([^"]+)"'
)
SKIP_PATTERN = re.compile(
    r'Skipping analyzing "([^"]+)": module is installed, but missing library stubs or py\.typed marker'
)

STUB_PACKAGE_MAP = {
    "authlib": "types-Authlib",
    "deprecated": "types-Deprecated",
    "flask": "types-Flask",
    "matplotlib": "matplotlib-stubs",
    "matplotlib.pyplot": "matplotlib-stubs",
    "pandas": "pandas-stubs",
    "pyproj": "",
    "requests": "types-requests",
    "redis": "types-redis",
    "shapely": "types-shapely",
    "yaml": "types-PyYAML",
    "pyyaml": "types-PyYAML",
}

BASE_STUB_PACKAGES: Set[str] = {
    "types-Authlib",
    "types-Deprecated",
    "types-Flask",
    "matplotlib-stubs",
    "types-redis",
    "types-requests",
    "types-shapely",
    "types-PyYAML",
    "pandas-stubs",
}

FALLBACK_TYPES_MODULES = {
    "cattrs",
    "jinja2",
    "markupsafe",
    "sqlalchemy",
}

IGNORE_MODULE_PREFIXES = {
    "osgeo",
    "jsonpickle",
    "rosetta",
    "pyarrow",
    "netCDF4",
    "utm",
    "rasterio",
}


@dataclass(frozen=True)
class StubUpdateResult:
    added: Set[str]
    skipped: Set[str]
    command_exit_code: int


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyse mypy output and update docker/requirements-stubs-uv.txt with missing stub packages."
    )
    parser.add_argument(
        "--requirements",
        type=Path,
        default=DEFAULT_REQUIREMENTS_PATH,
        help="Path to the stub requirements file (default: %(default)s).",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Do not verify stub packages against PyPI before adding them.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to execute for diagnostics (defaults to `python -m mypy --config-file mypy.ini`).",
    )
    return parser.parse_args(argv)


def build_command(args: argparse.Namespace) -> Sequence[str]:
    if not args.command:
        return DEFAULT_COMMAND
    if args.command[0] == "--":
        return tuple(args.command[1:]) if len(args.command) > 1 else DEFAULT_COMMAND
    return tuple(args.command)


def run_command(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True)


def candidate_stub_packages(output: str) -> Set[str]:
    candidates: Set[str] = set()
    for match in HINT_PATTERN.finditer(output):
        candidates.add(match.group(1).strip())

    modules: Set[str] = set()
    for pattern in (LIB_STUB_PATTERN, SKIP_PATTERN):
        for match in pattern.finditer(output):
            modules.add(match.group(1).strip())

    for module in modules:
        base = module.split(".")[0]
        if any(module.startswith(prefix) for prefix in IGNORE_MODULE_PREFIXES):
            continue

        mapping_keys = (module, base)
        mapped = False
        for key in mapping_keys:
            if key in STUB_PACKAGE_MAP:
                pkg = STUB_PACKAGE_MAP[key]
                if pkg:
                    candidates.add(pkg)
                mapped = True
                break
        if mapped:
            continue

        if base in FALLBACK_TYPES_MODULES:
            candidates.add(f"types-{base}")

    return candidates


def verify_package_exists(package: str) -> bool:
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        with urlopen(url) as response:  # noqa: S310
            return 200 <= response.status < 300
    except (HTTPError, URLError):
        return False


def update_requirements_file(
    requirements_path: Path, packages: Iterable[str], verify: bool = True
) -> Set[str]:
    requirements_path.parent.mkdir(parents=True, exist_ok=True)
    existing: Set[str] = set()
    if requirements_path.exists():
        for raw in requirements_path.read_text(encoding="utf-8").splitlines():
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            existing.add(stripped)

    to_add: Set[str] = set()
    for package in packages:
        normalized = package.strip()
        if not normalized or normalized in existing:
            continue
        if verify and not verify_package_exists(normalized):
            print(f"[stub-update] Skipping unknown package {normalized!r}", file=sys.stderr)
            continue
        to_add.add(normalized)

    if not to_add:
        return set()

    combined = sorted(existing | to_add)
    header = "# Auto-generated by tools/update_stub_requirements.py\n"
    body = "\n".join(combined)
    requirements_path.write_text(header + body + ("\n" if body else ""), encoding="utf-8")
    return to_add


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_arguments(argv)
    command = build_command(args)

    result = run_command(command)
    output = f"{result.stdout}\n{result.stderr}"

    packages = candidate_stub_packages(output) | BASE_STUB_PACKAGES
    if not packages:
        print("No stub packages detected; requirements file unchanged.", file=sys.stderr)
        return result.returncode

    added = update_requirements_file(args.requirements, packages, verify=not args.no_verify)
    skipped = packages - added

    if added:
        print(f"Added stub packages: {', '.join(sorted(added))}")
    else:
        print("No new stub packages added.")

    if skipped:
        print(f"Skipped packages (already present or resolution failed): {', '.join(sorted(skipped))}", file=sys.stderr)

    if result.returncode != 0:
        print(
            f"Underlying command exited with {result.returncode}; inspect diagnostics for additional issues.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
