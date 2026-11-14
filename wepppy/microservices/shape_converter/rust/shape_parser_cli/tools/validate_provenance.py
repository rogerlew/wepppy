#!/usr/bin/env python3
"""Validate shape_parser_cli against its adjacent JSON provenance sidecar."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "shape-parser-binary-provenance-v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(binary: Path, sidecar: Path) -> dict[str, object]:
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    binary_data = payload.get("binary")
    source_data = payload.get("source")
    build_data = payload.get("build")
    if payload.get("schema") != SCHEMA:
        raise ValueError("invalid provenance schema")
    if not isinstance(binary_data, dict) or not isinstance(source_data, dict) or not isinstance(build_data, dict):
        raise ValueError("incomplete provenance document")
    if binary_data.get("name") != binary.name:
        raise ValueError("binary name mismatch")
    if binary_data.get("size_bytes") != binary.stat().st_size:
        raise ValueError("binary size mismatch")
    if binary_data.get("sha256") != _sha256(binary):
        raise ValueError("binary SHA-256 mismatch")
    files = source_data.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("source manifest missing")
    if not isinstance(build_data.get("cargo_lock_sha256"), str):
        raise ValueError("Cargo lock provenance missing")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--sidecar", required=True, type=Path)
    args = parser.parse_args()
    validate(args.binary.resolve(), args.sidecar.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
