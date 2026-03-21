"""Manifest helpers for RUSLE K-factor artifacts."""

from __future__ import annotations

import json
from os.path import exists as _exists
from typing import Any


__all__ = ["load_manifest", "write_manifest", "update_k_manifest"]


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


def update_k_manifest(path: str, k_payload: dict[str, Any]) -> dict[str, Any]:
    """Update the `k` section in a RUSLE manifest and persist it."""
    manifest = load_manifest(path)
    manifest["k"] = k_payload
    write_manifest(path, manifest)
    return manifest
