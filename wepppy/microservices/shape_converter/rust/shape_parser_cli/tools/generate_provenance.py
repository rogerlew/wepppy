#!/usr/bin/env python3
"""Generate an adjacent provenance sidecar for shape_parser_cli."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = "shape-parser-binary-provenance-v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_text(args: list[str]) -> str:
    try:
        result = subprocess.run(args, check=False, capture_output=True, text=True)
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _source_inputs(source_root: Path) -> list[Path]:
    paths = [source_root / "Cargo.toml", source_root / "Cargo.lock"]
    paths.extend(sorted((source_root / "src").rglob("*.rs")))
    if not all(path.is_file() for path in paths):
        raise ValueError("shape parser source manifest is incomplete")
    return paths


def _manifest(paths: list[Path], source_root: Path) -> list[dict[str, object]]:
    return [
        {
            "path": path.relative_to(source_root).as_posix(),
            "sha256": _sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in paths
    ]


def _manifest_sha256(manifest: list[dict[str, object]]) -> str:
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def _elf_metadata(binary: Path) -> tuple[str, str]:
    notes = _run_text(["readelf", "-n", str(binary)]) if shutil.which("readelf") else ""
    headers = _run_text(["readelf", "-l", str(binary)]) if shutil.which("readelf") else ""
    build_id_match = re.search(r"Build ID:\s*(\S+)", notes)
    interpreter_match = re.search(r"Requesting program interpreter:\s*([^\]]+)", headers)
    return (
        build_id_match.group(1) if build_id_match else "",
        interpreter_match.group(1) if interpreter_match else "",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-revision", default="unknown")
    parser.add_argument("--release-label", default="development")
    parser.add_argument("--built-utc")
    parser.add_argument("--rustc", default="rustc")
    args = parser.parse_args()

    binary = args.binary.resolve()
    source_root = args.source_root.resolve()
    rustc_value = shutil.which(args.rustc) if "/" not in args.rustc else args.rustc
    rustc = Path(rustc_value).absolute() if rustc_value else Path()
    rustup = shutil.which("rustup") if args.rustc == "rustc" else None
    selected_rustc = _run_text([rustup, "which", "rustc"]) if rustup else ""
    compiler = Path(selected_rustc) if selected_rustc else rustc.resolve()
    if not binary.is_file() or not rustc.is_file() or not compiler.is_file():
        raise FileNotFoundError("binary or rustc not found")

    source_manifest = _manifest(_source_inputs(source_root), source_root)
    build_id, interpreter = _elf_metadata(binary)
    version = _run_text([str(binary), "--version"])
    built_utc = args.built_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "schema": SCHEMA,
        "release_label": args.release_label,
        "binary": {
            "name": binary.name,
            "role": "shape-converter-hostile-input-parser",
            "version": version,
            "sha256": _sha256(binary),
            "size_bytes": binary.stat().st_size,
            "format": _run_text(["file", "-b", str(binary)]) if shutil.which("file") else "unknown",
            "elf_build_id": build_id,
            "elf_interpreter": interpreter,
        },
        "source": {
            "repository": "https://github.com/rogerlew/wepppy",
            "revision": args.source_revision,
            "manifest_sha256": _manifest_sha256(source_manifest),
            "files": source_manifest,
        },
        "build": {
            "built_utc": built_utc,
            "command": "cargo build --release --locked",
            "rustc_path": str(rustc),
            "rustc_executable": str(compiler),
            "rustc_sha256": _sha256(compiler),
            "rustc_version": _run_text([str(rustc), "--version"]),
            "target": _run_text([str(rustc), "-vV"]),
            "cargo_lock_sha256": _sha256(source_root / "Cargo.lock"),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
