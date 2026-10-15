"""Immutable WMesque releases and one-way catalog replication.

See docs/schemas/wmesque-catalog-contract.md. No live data is deleted or rewritten.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*(/[A-Za-z0-9_][A-Za-z0-9_.-]*)*\Z")
_REMOTE = re.compile(r"(?:[A-Za-z0-9_.-]+@)?[A-Za-z0-9][A-Za-z0-9.-]*:/[A-Za-z0-9_./-]+\Z")
_MAX_JSON = 16 * 1024 * 1024


def dataset_id(value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError("Invalid dataset identifier")
    return value


def revision_id(value: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ValueError("Invalid dataset revision")
    return value


def _json_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _read_json(path: Path):
    with path.open("rb") as stream:
        raw = stream.read(_MAX_JSON + 1)
    if len(raw) > _MAX_JSON:
        raise ValueError(f"Manifest exceeds size limit: {path.name}")
    return json.loads(raw)


def _atomic_json(path: Path, value) -> None:
    fd, name = tempfile.mkstemp(prefix=".publish-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(_json_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _state(root: Path) -> Path:
    state = root / ".wmesque"
    if state.is_symlink():
        raise ValueError("WMesque state directory cannot be a symlink")
    state.mkdir(parents=True, exist_ok=True)
    return state


@contextmanager
def _lock(path: Path, *, blocking: bool = True):
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        yield
    finally:
        os.close(fd)


def read_catalog(root: str | Path) -> dict:
    path = _contained(Path(root), ".wmesque/catalog.json")
    if not path.exists():
        return {"schema_version": 1, "datasets": {}}
    value = _read_json(path)
    if not isinstance(value, dict) or value.get("schema_version") != 1 or not isinstance(value.get("datasets"), dict):
        raise ValueError("Invalid WMesque catalog")
    for name, revision in value["datasets"].items():
        dataset_id(name)
        revision_id(revision)
    return value


def _contained(root: Path, relative: str) -> Path:
    part = PurePosixPath(relative)
    if not relative or part.is_absolute() or ".." in part.parts or "\\" in relative:
        raise ValueError("Invalid release file path")
    target = root.joinpath(*part.parts)
    for parent in (target, *target.parents):
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError("Symlinks are forbidden in releases")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Release file escapes root")
    return target


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_vrt(path: Path) -> bool:
    # GDAL recognizes VRT by content, not suffix; inspect before any GDAL open.
    with path.open("rb") as stream:
        prefix = stream.read(4096)
    return path.name == ".vrt" or path.suffix.lower() == ".vrt" or b"<VRTDataset" in prefix


def _vrt_sources(path: Path, root: Path):
    tree = ET.parse(path)
    if tree.getroot().tag != "VRTDataset":
        raise ValueError("Expected VRTDataset")
    # A raster snapshot must not carry executable derived-band code or opaque sources.
    if any(node.tag in {"PixelFunctionCode", "PixelFunctionType", "SourceDataset"} for node in tree.iter()):
        raise ValueError("Only file-backed VRT sources can be published")
    sources = []
    for node in tree.iter("SourceFilename"):
        raw = node.text or ""
        if not raw or raw.startswith("/vsi") or ":" in raw:
            raise ValueError("Materialize virtual/network VRT sources before publication")
        source = Path(raw)
        if not source.is_absolute():
            if node.get("relativeToVRT") != "1":
                raise ValueError("Relative VRT source must use relativeToVRT=1")
            source = path.parent / source
        source = source.resolve(strict=True)
        if not source.is_relative_to(root.resolve()):
            raise ValueError("VRT source escapes publication root")
        sources.append((node, source))
    if not sources:
        raise ValueError("VRT must reference a raster source")
    return tree, sources


def read_manifest(release: Path, *, dataset: str | None = None, revision: str | None = None) -> dict:
    value = _read_json(_contained(release, "manifest.json"))
    if not isinstance(value, dict) or set(value) != {"schema_version", "dataset", "entrypoint", "files", "revision"}:
        raise ValueError("Invalid release manifest fields")
    if value["schema_version"] != 1 or not isinstance(value["files"], list):
        raise ValueError("Unsupported release manifest")
    dataset_id(value["dataset"])
    revision_id(value["revision"])
    if dataset is not None and value["dataset"] != dataset:
        raise ValueError("Manifest dataset mismatch")
    if revision is not None and value["revision"] != revision:
        raise ValueError("Manifest revision mismatch")
    body = {key: val for key, val in value.items() if key != "revision"}
    if hashlib.sha256(_json_bytes(body)).hexdigest() != value["revision"]:
        raise ValueError("Manifest digest mismatch")
    if value["entrypoint"] != f'data/{value["dataset"]}/.vrt':
        raise ValueError("Invalid entrypoint")
    paths = []
    for item in value["files"]:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256"}:
            raise ValueError("Invalid file inventory")
        _contained(release, item["path"])
        revision_id(item["sha256"])
        if type(item["size"]) is not int or item["size"] < 0:
            raise ValueError("Invalid file size")
        paths.append(item["path"])
    if paths != sorted(set(paths)) or value["entrypoint"] not in paths:
        raise ValueError("Invalid file ordering or missing entrypoint")
    return value


def verify_release(release: Path, *, dataset: str | None = None, revision: str | None = None) -> dict:
    manifest = read_manifest(release, dataset=dataset, revision=revision)
    inventory = {item["path"] for item in manifest["files"]}
    actual = set()
    for path in release.rglob("*"):
        if path.is_symlink():
            raise ValueError("Symlinks are forbidden in releases")
        if path.is_file() and path != release / "manifest.json":
            actual.add(path.relative_to(release).as_posix())
    if actual != inventory:
        raise ValueError("Release inventory differs from files")
    for item in manifest["files"]:
        path = _contained(release, item["path"])
        if not path.is_file() or path.stat().st_size != item["size"] or _hash(path) != item["sha256"]:
            raise ValueError(f'File integrity mismatch: {item["path"]}')
        if _is_vrt(path):
            _, sources = _vrt_sources(path, release)
            for node, source in sources:
                if Path(node.text).is_absolute() or source.relative_to(release.resolve()).as_posix() not in inventory:
                    raise ValueError("VRT dependency is not in release inventory")
    # Only open GDAL after all paths, dependency references, and hashes are checked.
    from osgeo import gdal
    raster = gdal.Open(str(_contained(release, manifest["entrypoint"])))
    if raster is None or raster.RasterCount < 1 or raster.RasterXSize < 1 or raster.RasterYSize < 1:
        raise ValueError("Published raster is unreadable")
    if raster.ReadRaster(0, 0, 1, 1) is None:
        raise ValueError("Published raster pixels are unreadable")
    return manifest


def _merge_catalog(root: Path, updates: dict) -> None:
    state = _state(root)
    with _lock(state / "catalog.lock"):
        catalog = read_catalog(root)
        catalog["datasets"].update(updates)
        _atomic_json(state / "catalog.json", catalog)


def _install_release(root: Path, staged: Path, manifest: dict) -> None:
    releases = _state(root) / "releases"
    if releases.is_symlink():
        raise ValueError("Release store cannot be a symlink")
    releases.mkdir(exist_ok=True)
    target = releases / manifest["revision"]
    with _lock(root / ".wmesque" / "catalog.lock"):
        if target.exists():
            verify_release(target, dataset=manifest["dataset"], revision=manifest["revision"])
        else:
            os.rename(staged, target)


def publish_dataset(geodata_dir: str | Path, dataset: str) -> dict:
    """Snapshot a local dependency closure; leave original datasets untouched."""
    dataset_id(dataset)
    root = Path(geodata_dir).resolve(strict=True)
    entry = (root / dataset / ".vrt").resolve(strict=True)
    if not entry.is_relative_to(root):
        raise ValueError("Dataset escapes geodata root")
    state = _state(root)
    with tempfile.TemporaryDirectory(prefix="publish-", dir=state) as temporary:
        stage = Path(temporary) / "release"
        stage.mkdir()
        visited = {}
        def copy_source(source: Path):
            if source in visited:
                return
            before = _hash(source)
            visited[source] = before
            relative = Path("data") / source.relative_to(root)
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if _is_vrt(source):
                tree, sources = _vrt_sources(source, root)
                for node, dependency in sources:
                    copy_source(dependency)
                    node.text = os.path.relpath(stage / "data" / dependency.relative_to(root), destination.parent)
                    node.set("relativeToVRT", "1")
                tree.write(destination, encoding="utf-8", xml_declaration=True)
            else:
                shutil.copyfile(source, destination)
                if _hash(destination) != before:
                    raise ValueError("Source changed while copying")
                for suffix in (".aux.xml", ".ovr", ".msk"):
                    sidecar = Path(str(source) + suffix)
                    if sidecar.exists():
                        resolved = sidecar.resolve(strict=True)
                        if not resolved.is_relative_to(root):
                            raise ValueError("Raster sidecar escapes geodata root")
                        copy_source(resolved)
        copy_source(entry)
        metadata = entry.parent / "metadata.json"
        if metadata.exists():
            resolved = metadata.resolve(strict=True)
            if not resolved.is_relative_to(root):
                raise ValueError("Metadata escapes geodata root")
            copy_source(resolved)
        if any(_hash(source) != digest for source, digest in visited.items()):
            raise ValueError("Source changed during publication")
        files = [{"path": path.relative_to(stage).as_posix(), "size": path.stat().st_size, "sha256": _hash(path)}
                 for path in sorted(stage.rglob("*")) if path.is_file()]
        manifest = {"schema_version": 1, "dataset": dataset,
                    "entrypoint": f"data/{dataset}/.vrt", "files": files}
        # A symlinked legacy entrypoint cannot change the logical layout.
        if not (stage / manifest["entrypoint"]).is_file():
            raise ValueError("Entrypoint must reside at its logical dataset path")
        manifest["revision"] = hashlib.sha256(_json_bytes(manifest)).hexdigest()
        _atomic_json(stage / "manifest.json", manifest)
        verify_release(stage)
        _install_release(root, stage, manifest)
        _merge_catalog(root, {dataset: manifest["revision"]})
    return manifest


def resolve_dataset(root: str | Path, dataset: str) -> tuple[Path, str | None]:
    dataset_id(dataset)
    root = Path(root).resolve()
    revision = read_catalog(root)["datasets"].get(dataset)
    if revision is None:
        path = (root / dataset / ".vrt").resolve()
        if not path.is_relative_to(root):
            raise ValueError("Dataset escapes geodata root")
        return path, None
    release = _contained(root, f".wmesque/releases/{revision}")
    manifest = read_manifest(release, dataset=dataset, revision=revision)
    return _contained(release, manifest["entrypoint"]), revision


def _copy(source: str, relative: str, target: Path) -> None:
    if source.startswith("/"):
        base = Path(source).resolve(strict=True)
        origin = _contained(base, relative)
        if origin.is_dir():
            shutil.copytree(origin, target, symlinks=True)
        else:
            shutil.copyfile(origin, target)
        return
    if not _REMOTE.fullmatch(source) or ".." in source.split(":", 1)[1].split("/"):
        raise ValueError("Source must be an absolute local root or user@tailnet-host:/absolute/root")
    if not re.fullmatch(r"[A-Za-z0-9_.][A-Za-z0-9_./-]*", relative) or ".." in relative.split("/"):
        raise ValueError("Invalid remote transfer path")
    remote = source.rstrip("/") + "/" + relative
    # rrsync must inspect paths, so secluded arguments (-s) are incompatible.
    # Both remote path components are shell-safe; disable inherited -s as well.
    args = ["rsync", "-rt", "--links", "--no-protect-args", "--timeout=300", "-e",
            "ssh -oBatchMode=yes -oStrictHostKeyChecking=yes -oConnectTimeout=30", "--"]
    if relative.endswith("/"):
        target.mkdir()
    subprocess.run(args + [remote, str(target)], check=True, timeout=330)


def sync_catalog(source: str, destination: str | Path, *, dry_run: bool = False) -> dict:
    """Pull managed resources; catalog changes are committed only after verification."""
    root = Path(destination).resolve(strict=True)
    state = _state(root)
    with _lock(state / "sync.lock", blocking=False):
        status_path = state / "sync-status.json"
        previous = _read_json(status_path) if status_path.exists() else {}
        result = {"started_at": datetime.now(timezone.utc).isoformat(), "dry_run": dry_run,
                  "last_success": previous.get("last_success"), "status": "running"}
        _atomic_json(status_path, result)
        completed = False
        try:
            with tempfile.TemporaryDirectory(prefix="sync-", dir=state) as temporary:
                temp = Path(temporary)
                (temp / ".wmesque").mkdir()
                _copy(source, ".wmesque/catalog.json", temp / ".wmesque/catalog.json")
                master = read_catalog(temp)["datasets"]
                local = read_catalog(root)["datasets"]
                result["updates"] = {key: val for key, val in master.items() if local.get(key) != val}
                if not dry_run:
                    for dataset, revision in master.items():
                        target = _contained(root, f".wmesque/releases/{revision}")
                        if target.exists():
                            verify_release(target, dataset=dataset, revision=revision)
                            continue
                        stage = temp / revision
                        _copy(source, f".wmesque/releases/{revision}/", stage)
                        manifest = verify_release(stage, dataset=dataset, revision=revision)
                        _install_release(root, stage, manifest)
                    _merge_catalog(root, master)
                    result["last_success"] = datetime.now(timezone.utc).isoformat()
                result["status"] = "dry_run" if dry_run else "success"
                completed = True
                return result
        finally:
            # Deliberate telemetry boundary: retain failure status without swallowing errors.
            if not completed:
                result["status"] = "failed"
            result["finished_at"] = datetime.now(timezone.utc).isoformat()
            _atomic_json(status_path, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    publish = commands.add_parser("publish")
    publish.add_argument("root")
    publish.add_argument("dataset")
    sync = commands.add_parser("sync")
    sync.add_argument("source")
    sync.add_argument("destination")
    sync.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = publish_dataset(args.root, args.dataset) if args.command == "publish" else sync_catalog(args.source, args.destination, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
