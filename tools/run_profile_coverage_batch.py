#!/usr/bin/env python3
"""
Batch runner that executes profile playback runs with coverage enabled and
collects the resulting `.coverage` files.

Usage:
    python tools/run_profile_coverage_batch.py \
        --service-url http://127.0.0.1:8070 \
        --base-url https://wc.bearhive.duckdns.org/weppcloud

Expectations:
    * ENABLE_PROFILE_COVERAGE must be set on the `weppcloud` container.
    * `wctl` must be on PATH (the script shells out to `wctl run-test-profile`).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - PyYAML is a dev dep
    yaml = None

PROFILE_ROOT_DEFAULT = Path("/workdir/wepppy-test-engine-data/profiles")
SHARDS_ROOT_DEFAULT = Path("/workdir/wepppy-test-engine-data/coverage")
ARTIFACTS_DIR_DEFAULT = Path("docs/work-packages/20251109_profile_playback_coverage/artifacts").resolve()
COVERAGE_DIR_DEFAULT = SHARDS_ROOT_DEFAULT
COVERAGE_CONFIG_DEFAULT = Path(__file__).resolve().parents[1] / "wepppy" / "weppcloud" / "coverage.profile-playback.ini"
PROFILES_FILE_DEFAULT = Path(".github/forest_workflows/playback-profiles.yml")


def _run(cmd: List[str], cwd: Path | None = None, env: dict | None = None) -> None:
    """Run a command, streaming output, and raise if it fails."""
    subprocess.run(cmd, check=True, cwd=cwd, env=env)


def _run_wctl(cmd: List[str], cwd: Path, env: dict) -> subprocess.CompletedProcess:
    """Run a wctl command, echo output, and return the completed process."""
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc


_ERROR_PATTERNS = (
    re.compile(r"Playback error", re.IGNORECASE),
    re.compile(r"status failed", re.IGNORECASE),
    re.compile(r"Traceback", re.IGNORECASE),
)


def _has_playback_error(output: str) -> bool:
    return any(p.search(output) for p in _ERROR_PATTERNS)


def _matches(slug: str, include: List[str], exclude: List[str]) -> bool:
    if include and slug not in include:
        return False
    if exclude and slug in exclude:
        return False
    return True


def _glob_profiles(root: Path) -> Iterable[str]:
    for entry in sorted(root.iterdir()):
        if entry.is_dir():
            yield entry.name


def _load_profiles_from_file(path: Path) -> Sequence[str]:
    if not path.exists():
        raise FileNotFoundError(f"profiles file not found: {path}")
    if yaml is None:
        raise RuntimeError("PyYAML is required to parse profiles file but is not installed.")
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, list):
        raise ValueError(f"profiles file {path} must contain a list of entries")
    slugs: list[str] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        slug = entry.get("profile_slug")
        if isinstance(slug, str):
            slugs.append(slug)
    return slugs


def _has_capture(root: Path, slug: str) -> bool:
    capture_file = root / slug / "capture" / "events.jsonl"
    return capture_file.exists()


def _remove_existing_shards(slug: str, shards_root: Path) -> None:
    pattern = f"{slug}.coverage."
    for shard in shards_root.glob(f"{pattern}*"):
        shard.unlink(missing_ok=True)


def _combine_coverage(slug: str, shards_root: Path) -> Path:
    """Combine coverage shards for `slug` and return the merged file path."""
    # Coverage writes one file per process when data_suffix is in effect; some runs
    # will only produce a single `<slug>.coverage` when only one process traced.
    shard_list = list(shards_root.glob(f"{slug}.coverage.*"))
    if shard_list:
        # Run coverage combine inside weppcloud container where coverage.py is installed
        cmd = [
            "docker",
            "exec",
            "weppcloud",
            "bash",
            "-c",
            f"cd {shards_root} && /opt/venv/bin/python -m coverage combine "
            + " ".join(shard.name for shard in shard_list),
        ]
        _run(cmd, cwd=None)  # cwd is handled inside the container
        combined = shards_root / ".coverage"
        if not combined.exists():
            raise RuntimeError(f"coverage combine did not emit {combined}")
        return combined

    base_file = shards_root / f"{slug}.coverage"
    if base_file.exists():
        return base_file

    raise RuntimeError(
        f"No coverage data found for {slug} in {shards_root}. "
        "Verify ENABLE_PROFILE_COVERAGE is set and the run completed."
    )


def _capture_profile(
    slug: str,
    args: argparse.Namespace,
) -> Path:
    """Run playback for a profile and return the path to the merged coverage file."""
    COVERAGE_DIR_DEFAULT.mkdir(parents=True, exist_ok=True)
    # Clean stale shards so combine doesn't include previous runs.
    _remove_existing_shards(slug, args.coverage_shards)
    cmd = [
        args.wctl_binary,
        "run-test-profile",
        slug,
        "--trace-code",
        "--coverage-dir",
        str(args.coverage_dir),
        "--coverage-config",
        str(args.coverage_config),
        "--service-url",
        args.service_url,
        "--base-url",
        args.base_url,
    ]
    if args.cookie:
        cmd.extend(["--cookie", args.cookie])
    elif args.cookie_file:
        cmd.extend(["--cookie-file", args.cookie_file])
    last_error: str | None = None
    for attempt in range(1, args.retries + 1):
        print(f"[attempt {attempt}/{args.retries}] {slug}")
        proc = _run_wctl(cmd, cwd=args.repo_root, env=args.exec_env)
        if proc.returncode != 0 or _has_playback_error(proc.stdout or "") or _has_playback_error(proc.stderr or ""):
            last_error = proc.stdout + proc.stderr
            if attempt < args.retries:
                print(f"[retry] {slug} due to playback error/exit code")
                continue
            raise RuntimeError(f"Playback failed for {slug} after {args.retries} attempts:\n{last_error}")

        try:
            combined = _combine_coverage(slug, args.coverage_shards)
        except Exception as exc:  # pragma: no cover - combine diagnostics
            last_error = str(exc)
            if attempt < args.retries:
                print(f"[retry] {slug} due to coverage combine error: {exc}")
                continue
            raise

        target = args.artifacts_dir / f"{slug}.coverage"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(combined), target)
        return target

    raise RuntimeError(f"Unhandled failure for {slug}: {last_error or 'unknown error'}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profiles-root",
        type=Path,
        default=PROFILE_ROOT_DEFAULT,
        help=f"Directory containing profile captures (default: {PROFILE_ROOT_DEFAULT})",
    )
    parser.add_argument(
        "--profiles-file",
        type=Path,
        default=PROFILES_FILE_DEFAULT,
        help="YAML file listing playback profiles (default: .github/forest_workflows/playback-profiles.yml). "
        "When set and readable, profile_slugs from this file are used instead of directory globbing.",
    )
    parser.add_argument(
        "--coverage-shards",
        type=Path,
        default=SHARDS_ROOT_DEFAULT,
        help=f"Directory where coverage shards are written (default: {SHARDS_ROOT_DEFAULT})",
    )
    parser.add_argument(
        "--coverage-dir",
        type=Path,
        default=COVERAGE_DIR_DEFAULT,
        help="Directory passed to wctl/Playback for temporary coverage output (default: /tmp/profile-coverage)",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=ARTIFACTS_DIR_DEFAULT,
        help=f"Destination for merged .coverage files (default: {ARTIFACTS_DIR_DEFAULT})",
    )
    parser.add_argument(
        "--include",
        nargs="*",
        default=[],
        help="Specific profile slugs to run (default: all directories under profiles-root)",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Profile slugs to skip even if present in --include.",
    )
    parser.add_argument(
        "--service-url",
        default="http://127.0.0.1:8070",
        help="Profile playback FastAPI URL.",
    )
    parser.add_argument(
        "--base-url",
        default="https://wc.bearhive.duckdns.org/weppcloud",
        help="WEPPcloud base URL.",
    )
    parser.add_argument("--cookie", help="Raw Cookie header for WEPPcloud.")
    parser.add_argument("--cookie-file", help="Path to file containing Cookie header.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root used as cwd for wctl (default: project root).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip profiles that already have a merged artifact.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print wctl commands instead of executing them.",
    )
    parser.add_argument(
        "--coverage-config",
        type=Path,
        default=COVERAGE_CONFIG_DEFAULT,
        help=f"Path to coverage.profile-playback.ini (default: {COVERAGE_CONFIG_DEFAULT})",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Number of attempts per profile before giving up (default: 3).",
    )
    parser.add_argument(
        "--wctl-binary",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "wctl" / "wctl.sh"),
        help="Path to the wctl launcher (default: project wctl/wctl.sh).",
    )
    return parser.parse_args()


def _execute_batch(args: argparse.Namespace) -> None:
    args.coverage_shards.mkdir(parents=True, exist_ok=True)
    args.exec_env = {
        "ENABLE_PROFILE_COVERAGE": "1",
        "PROFILE_COVERAGE_DIR": str(args.coverage_shards),
        "PROFILE_COVERAGE_EXPORT_DIR": str(args.coverage_shards),
        "PROFILE_COVERAGE_CONFIG": str(args.coverage_config),
        "PROFILE_PLAYBACK_BASE_URL": args.base_url,
        "PROFILE_PLAYBACK_URL": args.service_url,
    }

    profiles: list[str] = []
    try:
        if args.profiles_file and args.profiles_file.exists():
            profiles = list(_load_profiles_from_file(args.profiles_file))
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"[warn] unable to load profiles from {args.profiles_file}: {exc}", file=sys.stderr)
    if not profiles:
        profiles = list(_glob_profiles(args.profiles_root))
    if not profiles:
        print(f"No profiles found under {args.profiles_root}", file=sys.stderr)
        sys.exit(1)

    for slug in profiles:
        if not _matches(slug, args.include, args.exclude):
            continue
        if not _has_capture(args.profiles_root, slug):
            print(f"[skip] {slug} (no capture/events.jsonl)")
            continue
        artifact_path = args.artifacts_dir / f"{slug}.coverage"
        if args.skip_existing and artifact_path.exists():
            print(f"[skip] {slug} (coverage artifact already exists)")
            continue

        print(f"[run] {slug}")
        if args.dry_run:
            continue

        try:
            output_path = _capture_profile(slug, args)
        except subprocess.CalledProcessError as exc:
            print(f"[error] Command failed for {slug}: {exc}", file=sys.stderr)
            continue
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[error] {slug}: {exc}", file=sys.stderr)
            continue

        print(f"[ok] {slug} → {output_path}")


def run_batch(
    profiles_root: Path = PROFILE_ROOT_DEFAULT,
    coverage_shards: Path = SHARDS_ROOT_DEFAULT,
    coverage_dir: Path = COVERAGE_DIR_DEFAULT,
    artifacts_dir: Path = ARTIFACTS_DIR_DEFAULT,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    service_url: str = "http://127.0.0.1:8070",
    base_url: str = "https://wc.bearhive.duckdns.org/weppcloud",
    cookie: str | None = None,
    cookie_file: str | None = None,
    skip_existing: bool = False,
    dry_run: bool = False,
    repo_root: Path = Path(__file__).resolve().parents[1],
    coverage_config: Path = COVERAGE_CONFIG_DEFAULT,
) -> None:
    args = argparse.Namespace(
        profiles_root=profiles_root,
        coverage_shards=coverage_shards,
        coverage_dir=coverage_dir,
        artifacts_dir=artifacts_dir,
        include=include or [],
        exclude=exclude or [],
        service_url=service_url,
        base_url=base_url,
        cookie=cookie,
        cookie_file=cookie_file,
        skip_existing=skip_existing,
        dry_run=dry_run,
        repo_root=repo_root,
        coverage_config=coverage_config,
    )
    _execute_batch(args)


def main() -> None:
    args = _parse_args()
    _execute_batch(args)


if __name__ == "__main__":
    main()
