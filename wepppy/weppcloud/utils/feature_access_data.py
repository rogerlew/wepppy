"""Finite FA-01 contrast artifact classification for delivery and copying.

Call this on the logical path AND its resolved filesystem source. Classification
does not authorize filesystem traversal; existing path guards remain mandatory.
"""
from pathlib import Path, PurePosixPath
import fnmatch
import json
import zipfile

_FILES = frozenset({
    "omni/contrasts.out.parquet", "omni/README.contrasts.md", "omni/contrast_id_definitions.psv",
    "omni.nodb", "path_ce.nodb", "path/selection.parquet", "path/hillslope_sdyd.parquet",
    "path/sweep.parquet", "path/sweep_manifest.json",
})
_TREES = ("omni/contrasts", "_pups/omni/contrasts", "path/report")
_PATTERNS = ("path/path_ce_*", "path/untreatable*.parquet")


def protected_path(path):
    parts = PurePosixPath(str(path).replace("\\", "/")).parts
    # Match every suffix because grouped roots and archive members may prepend
    # a run directory, and a resolved child path may sit outside its alias root.
    for offset in range(len(parts)):
        relative = "/".join(parts[offset:])
        if relative in _FILES or any(relative == tree or relative.startswith(tree + "/") for tree in _TREES):
            return True
        if any(fnmatch.fnmatchcase(relative, pattern) for pattern in _PATTERNS):
            return True
    return False


def protected_source(path):
    path = Path(path)
    if protected_path(path) or protected_path(path.resolve()):
        return True
    resolved = path.resolve()
    if resolved.as_posix().endswith("/_query_engine/catalog.json") and resolved.is_file():
        catalog = json.loads(resolved.read_text(encoding="utf-8"))
        if protected_catalog(catalog):
            return True
        root = resolved.parents[1]
        for entry in catalog.get("files", []):
            source = (root / (entry.get("fs_path") or entry["path"])).resolve()
            # Catalog datasets are tabular sources, not nested catalogs.
            if source.suffix.lower() != ".json" and protected_source(source):
                return True
    if resolved.as_posix().endswith("/export/features/cache/index.json") and resolved.is_file():
        index = json.loads(resolved.read_text(encoding="utf-8"))
        root = resolved.parents[3]
        for entry in index.get("entries", {}).values():
            if protected_export(entry):
                return True
            manifest = entry.get("manifest_relpath")
            if isinstance(manifest, str):
                source = (root / manifest).resolve()
                source.relative_to(root)
                if source.name != "manifest.json":
                    raise ValueError("Invalid export manifest reference")
                if source.is_file() and protected_export(json.loads(source.read_text(encoding="utf-8"))):
                    return True
    # Existing features-export sidecars classify renamed/generated outputs.
    # Limit lookup to that owned tree; unrelated manifest.json files are not
    # silently assigned scientific semantics.
    for parent in (resolved, *resolved.parents):
        if "export/features" not in parent.as_posix():
            break
        manifest = parent / "manifest.json" if parent.is_dir() else None
        if manifest is not None and manifest.is_file():
            if protected_export(json.loads(manifest.read_text(encoding="utf-8"))):
                return True
    return False


def protected_catalog(value):
    return isinstance(value, dict) and any(
        protected_path(entry.get("path", "")) or protected_path(entry.get("fs_path") or "")
        for entry in value.get("files", []) if isinstance(entry, dict)
    )


def protected_export(value):
    """Existing request/plan/manifest vocabulary, not arbitrary payload taint."""
    if not isinstance(value, dict):
        return False
    if value.get("contrast_ids") or value.get("contrast_id") or value.get("context") == "contrast":
        return True
    for key in ("layer_id", "family", "profile"):
        if str(value.get(key, "")).startswith("omni.contrasts"):
            return True
    layers = value.get("layers", value.get("layer_outputs", []))
    if isinstance(layers, list) and any(
        protected_export(layer) if isinstance(layer, dict) else str(layer).startswith("omni.contrasts")
        for layer in layers
    ):
        return True
    return any(protected_export(value.get(key)) for key in ("request", "resolved"))


def protected_bundle(path):
    """Inspect existing ZIP membership without decompressing protected content."""
    if not zipfile.is_zipfile(path):
        return False
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            if protected_path(member.filename):
                return True
            if PurePosixPath(member.filename).name == "manifest.json":
                # Existing export manifests are small; refuse ambiguous oversized
                # metadata rather than decompress an unbounded archive entry.
                if member.file_size > 4 * 1024 * 1024:
                    return True
                if protected_export(json.loads(archive.read(member))):
                    return True
            if member.filename.endswith("_query_engine/catalog.json"):
                if member.file_size > 4 * 1024 * 1024:
                    return True
                if protected_catalog(json.loads(archive.read(member))):
                    return True
        return False


def contains_protected(path):
    """Check copied/exported trees and indivisible files before delivery."""
    root = Path(path)
    if protected_source(root):
        return True
    if root.is_file():
        return protected_bundle(root)
    if root.is_dir():
        for child in root.rglob("*"):
            if protected_source(child) or (child.is_file() and protected_bundle(child)):
                return True
    return False
