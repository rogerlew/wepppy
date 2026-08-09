"""Typed study-manifest loading and security validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import content_hash, resolve_within, sha256_file, tree_hash

SCHEMA_VERSION = "1.0.0"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


@dataclass(frozen=True)
class Scenario:
    name: str
    authority: Path
    input_tree_sha256: str


@dataclass(frozen=True)
class MutationFamily:
    name: str
    directions: tuple[str, ...]
    minus: float
    plus: float


@dataclass(frozen=True)
class StudyManifest:
    raw: dict[str, Any]
    manifest_path: Path
    site: str
    scenarios: tuple[Scenario, ...]
    evidence_root: Path
    executable: Path
    executable_sha256: str
    run_dir: str
    file_prefix: str
    run_suffix: str
    selected_hillslopes: tuple[int, ...] | None
    mutation_families: tuple[MutationFamily, ...]
    population_exception: str | None
    study_id: str


def _safe_name(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SAFE_NAME_RE.fullmatch(value):
        raise ValueError(f"{field} must be a safe nonempty identifier")
    return value


def load_study_manifest(path: Path) -> StudyManifest:
    manifest_path = path.resolve(strict=True)
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported study manifest schema: {raw.get('schema_version')}")
    site = _safe_name(raw.get("site"), "site")
    evidence_root = Path(raw["evidence_root"]).resolve(strict=False)
    if not evidence_root.is_absolute():
        raise ValueError("evidence_root must be absolute")
    executable = Path(raw["executable"]["path"]).resolve(strict=False)
    expected_executable_hash = raw["executable"]["sha256"]
    if not SHA256_RE.fullmatch(expected_executable_hash):
        raise ValueError("executable SHA-256 is invalid")
    if executable.exists() and (not executable.is_file() or sha256_file(executable) != expected_executable_hash):
        raise ValueError("executable SHA-256 mismatch")

    discovery = raw["hillslope_discovery"]
    run_dir = discovery.get("run_dir", "runs")
    file_prefix = discovery.get("file_prefix", "p")
    run_suffix = discovery.get("run_suffix", ".run")
    if Path(run_dir).is_absolute() or ".." in Path(run_dir).parts:
        raise ValueError("hillslope run_dir must be relative")
    _safe_name(file_prefix, "hillslope file_prefix")
    if not re.fullmatch(r"\.[A-Za-z0-9]+", run_suffix):
        raise ValueError("run_suffix must be a simple extension")

    scenarios: list[Scenario] = []
    for item in raw.get("scenarios", []):
        name = _safe_name(item.get("name"), "scenario name")
        authority = Path(item["authority"]).resolve(strict=True)
        resolve_within(authority, authority / run_dir)
        authority_hash = item["input_tree_sha256"]
        if not SHA256_RE.fullmatch(authority_hash):
            raise ValueError(f"invalid input tree SHA-256 for {name}")
        run_root = authority / run_dir
        inputs = [candidate for candidate in run_root.iterdir()
                  if candidate.is_file() and candidate.name.startswith(file_prefix)]
        if tree_hash(inputs, run_root) != authority_hash:
            raise ValueError(f"input tree SHA-256 mismatch for {name}")
        scenarios.append(Scenario(name, authority, authority_hash))
    if not scenarios or len({item.name for item in scenarios}) != len(scenarios):
        raise ValueError("scenarios must be a nonempty list with unique names")

    families: list[MutationFamily] = []
    for item in raw.get("mutation_families", []):
        name = _safe_name(item.get("name"), "mutation family")
        directions = tuple(item.get("directions", []))
        if directions != ("minus", "plus"):
            raise ValueError(f"{name} must declare directions ['minus', 'plus']")
        families.append(MutationFamily(name, directions, float(item["minus"]), float(item["plus"])))
    if {item.name for item in families} != {"ksat", "cover"}:
        raise ValueError("mutation families must be exactly ksat and cover")

    selected = raw.get("selected_hillslopes")
    selected_ids = None if selected is None else tuple(int(value) for value in selected)
    if selected_ids is not None and (not selected_ids or len(set(selected_ids)) != len(selected_ids)):
        raise ValueError("selected_hillslopes must be unique and nonempty")

    return StudyManifest(
        raw=raw,
        manifest_path=manifest_path,
        site=site,
        scenarios=tuple(scenarios),
        evidence_root=evidence_root,
        executable=executable,
        executable_sha256=expected_executable_hash,
        run_dir=run_dir,
        file_prefix=file_prefix,
        run_suffix=run_suffix,
        selected_hillslopes=selected_ids,
        mutation_families=tuple(families),
        population_exception=raw.get("population_exception"),
        study_id=content_hash(raw),
    )
