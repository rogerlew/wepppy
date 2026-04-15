from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd


class GenevaArtifactIO:
    """Read/write helper for run-scoped Geneva artifacts."""

    def __init__(self, root_dir_name: str = "geneva") -> None:
        self._root_dir_name = root_dir_name

    def root_dir(self, wd: str) -> Path:
        root = Path(wd) / self._root_dir_name
        root.mkdir(parents=True, exist_ok=True)
        return root

    def resolve_path(self, wd: str, relpath: str) -> Path:
        normalized_relpath = self._normalize_relpath(relpath)
        root = self.root_dir(wd).resolve()
        candidate = (root / normalized_relpath).resolve()

        root_prefix = os.path.commonpath([str(root), str(candidate)])
        if root_prefix != str(root):
            raise ValueError(f"Artifact path escapes Geneva root: {relpath}")
        return candidate

    def exists(self, wd: str, relpath: str) -> bool:
        return self.resolve_path(wd, relpath).exists()

    def write_json(self, wd: str, relpath: str, payload: Mapping[str, Any] | list[Any]) -> str:
        path = self.resolve_path(wd, relpath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        return relpath

    def read_json(self, wd: str, relpath: str) -> dict[str, Any]:
        path = self.resolve_path(wd, relpath)
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object for {relpath}")
        return data

    def write_text(self, wd: str, relpath: str, content: str) -> str:
        path = self.resolve_path(wd, relpath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return relpath

    def write_records_parquet(
        self,
        wd: str,
        relpath: str,
        records: Iterable[Mapping[str, Any]],
        *,
        columns: list[str] | None = None,
    ) -> str:
        path = self.resolve_path(wd, relpath)
        path.parent.mkdir(parents=True, exist_ok=True)

        frame = pd.DataFrame(list(records))
        if columns is not None:
            frame = frame.reindex(columns=columns)
        frame.to_parquet(path, index=False)
        return relpath

    def read_records_parquet(self, wd: str, relpath: str) -> list[dict[str, Any]]:
        path = self.resolve_path(wd, relpath)
        frame = pd.read_parquet(path)
        return frame.to_dict(orient="records")

    def sha256(self, wd: str, relpath: str) -> str:
        path = self.resolve_path(wd, relpath)
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _normalize_relpath(self, relpath: str) -> str:
        value = str(relpath).strip()
        if not value:
            raise ValueError("Artifact relpath must not be empty")
        path = Path(value)
        if path.is_absolute():
            raise ValueError("Artifact relpath must be relative")

        normalized = Path(*path.parts)
        for segment in normalized.parts:
            if segment in {"", ".", ".."}:
                raise ValueError(f"Artifact relpath contains invalid segment: {relpath}")
        return normalized.as_posix()


__all__ = ["GenevaArtifactIO"]
