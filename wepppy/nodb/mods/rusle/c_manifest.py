"""Manifest helpers for RUSLE C-factor artifacts."""

from __future__ import annotations

import json
from os.path import exists as _exists
from typing import Any


__all__ = ["load_manifest", "write_manifest", "update_c_manifest"]


def load_manifest(path: str) -> dict[str, Any]:
    """Load an existing manifest file or return an empty payload."""

    if not _exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def write_manifest(path: str, payload: dict[str, Any]) -> None:
    """Write the manifest payload with stable formatting."""

    with open(path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)


def update_c_manifest(path: str, c_payload: dict[str, Any]) -> dict[str, Any]:
    """Update the `c` section in a RUSLE manifest and persist it."""

    manifest = load_manifest(path)
    manifest["c"] = c_payload
    write_manifest(path, manifest)
    return manifest

