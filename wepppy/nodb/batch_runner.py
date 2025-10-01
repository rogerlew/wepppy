"""NoDb scaffolding for the Batch Runner feature (Phase 0).

Provides a minimal manifest container so subsequent phases can persist
batch metadata using the existing NoDb infrastructure without yet
implementing orchestration logic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import os
import shutil
from typing import Any, Dict, List, Optional

from .base import NoDbBase


@dataclass
class BatchRunnerManifest:
    """Lightweight manifest for batch runner state."""

    version: int = 1
    batch_name: Optional[str] = None
    config: Optional[str] = None
    created_at: Optional[str] = None
    created_by: Optional[str] = None
    runid_template: Optional[str] = None
    selected_tasks: List[str] = field(default_factory=list)
    force_rebuild: bool = False
    runs: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)
    control_hashes: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return asdict(self)


class BatchRunner(NoDbBase):
    """NoDb stub for the batch runner controller."""

    __name__ = "BatchRunner"
    filename = "batch_runner.nodb"

    def __init__(self, wd: str, 
                 batch_config: str,
                 base_config: str):
        super().__init__(wd, batch_config)
        with self.locked():
            if not hasattr(self, "_manifest") or self._manifest is None:
                self._manifest = BatchRunnerManifest()
            self._base_config = base_config

        self._init_base_project()

        os.makedirs(self.batch_runs_dir, exist_ok=True)
        os.makedirs(self.resources_dir, exist_ok=True)

    def _init_base_project(self) -> None:
        from wepppy.nodb.ron import Ron
        if os.path.exists(self._base_wd):
            shutil.rmtree(self._base_wd)
        os.makedirs(self._base_wd)
        Ron(self._base_wd, self.base_config)

    @property
    def _base_wd(self) -> str:
        """Return the base working directory."""
        return os.path.join(self.wd, "_base")

    @property
    def base_config(self) -> str:
        """Return the base config for create _base"""
        return self._base_config

    @property
    def batch_runs_dir(self) -> str:
        """Return the directory where batch runs are stored."""
        return os.path.join(self.wd, "runs")
    
    @property
    def resources_dir(self) -> str:
        """Return the directory where resources are stored."""
        return os.path.join(self.wd, "resources")

    #
    # manifest properties and methods, managed primarily by codex
    #
    @property
    def manifest(self) -> BatchRunnerManifest:
        """Return the in-memory manifest object."""
        return self._manifest

    def manifest_dict(self) -> Dict[str, Any]:
        """Return the manifest as a primitive dictionary."""
        return self._manifest.to_dict()

    def reset_manifest(self) -> BatchRunnerManifest:
        """Reset the manifest back to default values."""
        with self.locked():
            self._manifest = BatchRunnerManifest()
            return self._manifest

    def update_manifest(self, **updates: Any) -> BatchRunnerManifest:
        """Apply shallow updates to the manifest (Phase 0 placeholder)."""
        if not updates:
            return self._manifest

        with self.locked():
            for key, value in updates.items():
                if hasattr(self._manifest, key):
                    setattr(self._manifest, key, value)
                else:
                    self._manifest.metadata[key] = value
            return self._manifest

    @classmethod
    def default_manifest(cls) -> BatchRunnerManifest:
        """Convenience helper for creating a detached default manifest."""
        return BatchRunnerManifest()


__all__ = ["BatchRunner", "BatchRunnerManifest"]
