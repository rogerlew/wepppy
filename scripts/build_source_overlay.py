#!/usr/bin/env python3
"""Build a manifest-bound source overlay on an exact local batch image.

Used only by deploy-production.sh --targeted-batch --source-overlay-manifest.
No registry, dependency installer, arbitrary recipe, or container patching path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from typing import Any

APP_ROOT = "/workdir/wepppy"
APP_FILES = frozenset({
    "wepppy/rq/query_catalog_rq.py",
    "wepppy/rq/_query_catalog_inventory.py",
    "wepppy/rq/_query_catalog_admission.py",
    "wepppy/rq/_query_catalog_pilot.py",
    "tools/query_catalog_pilot.py",
})
PROVENANCE = "/opt/wepppy-source-overlay/manifest.json"
CONFIG_FIELDS = (
    "User", "Env", "WorkingDir", "Entrypoint", "Cmd", "Volumes",
    "ExposedPorts", "Healthcheck", "StopSignal", "Shell", "Labels", "OnBuild",
)
PROBE = r'''
import hashlib, importlib.metadata, importlib.util, json, stat
from pathlib import Path
files = json.loads(__import__('sys').argv[1])
packages = sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions())
native_spec = importlib.util.find_spec('wepppyo3')
if native_spec is None or not native_spec.origin:
    raise RuntimeError('Required native package is absent')
native_root = Path(native_spec.origin).resolve().parent
native = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted(native_root.rglob('*.so')) if p.is_file()}
if not native or not any('wepp_interchange_rust' in p for p in native):
    raise RuntimeError('Required native scanner fingerprint is absent')
print(json.dumps({'distributions': hashlib.sha256(json.dumps(packages).encode()).hexdigest(),
                  'distribution_count': len(packages), 'native': native,
                  'source_metadata': {p: [stat.S_IMODE(s.st_mode), s.st_uid, s.st_gid]
                                      if (s := Path('/workdir/wepppy', p).stat() if Path('/workdir/wepppy', p).is_file() else None) else None for p in files},
                  'sources': {p: hashlib.sha256(Path('/workdir/wepppy', p).read_bytes()).hexdigest()
                              if Path('/workdir/wepppy', p).is_file() else None for p in files}}))
'''
BASE_CHECK = r'''
import json, stat
from pathlib import Path
targets = ['/workdir/wepppy/' + n for n in json.loads(__import__('sys').argv[1])]
targets.append('/opt/wepppy-source-overlay/manifest.json')
for target in targets:
    path = Path('/')
    for part in Path(target).parts[1:]:
        path = path / part
        if path.is_symlink():
            raise RuntimeError('Overlay destination contains a symlink')
    if path.exists() and not stat.S_ISREG(path.stat().st_mode):
        raise RuntimeError('Overlay destination is not a regular file')
'''
COMPILE = r'''
import json, os, py_compile, stat
from pathlib import Path
manifest = json.loads(Path('/opt/wepppy-source-overlay/manifest.json').read_text())
for name in manifest['files']:
    path = Path('/workdir/wepppy', name)
    cache = path.parent / '__pycache__'
    if cache.is_symlink():
        raise RuntimeError('Overlay bytecode directory contains a symlink')
    if cache.exists():
        for old in cache.glob(path.stem + '.*.pyc'):
            old.unlink()
    if not cache.exists():
        cache.mkdir(mode=stat.S_IMODE(path.parent.stat().st_mode))
        os.chown(cache, path.parent.stat().st_uid, path.parent.stat().st_gid)
        cache.chmod(stat.S_IMODE(path.parent.stat().st_mode))
    bytecode = py_compile.compile(str(path), doraise=True)
    source_stat = path.stat()
    os.chown(bytecode, source_stat.st_uid, source_stat.st_gid)
    os.chmod(bytecode, stat.S_IMODE(source_stat.st_mode))
'''


def docker(*arguments: str) -> str:
    return subprocess.run(["docker", *arguments], check=True, text=True,
                          capture_output=True).stdout.strip()


def inspect_image(reference: str) -> dict[str, Any]:
    records = json.loads(docker("image", "inspect", reference))
    if len(records) != 1:
        raise ValueError("Expected one local image")
    return records[0]


def read_sources(root: Path, manifest: dict[str, Any]) -> dict[str, bytes]:
    if set(manifest) != {"version", "base_image_id", "files"} or manifest["version"] != 1:
        raise ValueError("Unsupported source-overlay manifest")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", manifest["base_image_id"]):
        raise ValueError("An immutable local base image ID is required")
    if not isinstance(manifest["files"], dict) or set(manifest["files"]) != APP_FILES:
        raise ValueError("Source-overlay manifest must name exactly the approved five files")
    root = root.resolve(strict=True)
    contents = {}
    for name, expected in manifest["files"].items():
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Invalid source digest")
        path = root
        for part in name.split("/"):
            path = path / part
            if path.is_symlink():
                raise ValueError("Source-overlay input contains a symlink")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError("Source-overlay input must be a regular file")
            content = source.read()
        if path.resolve(strict=True) != root / name or hashlib.sha256(content).hexdigest() != expected:
            raise ValueError("Source-overlay path or content changed")
        contents[name] = content
    return contents


def fingerprint(reference: str) -> dict[str, Any]:
    return json.loads(docker("run", "--rm", "--network", "none", "--entrypoint",
                             "/opt/venv/bin/python", reference, "-B", "-c", PROBE,
                             json.dumps(sorted(APP_FILES))))


def build_overlay(root: Path, manifest: dict[str, Any], image: str,
                  container: str) -> dict[str, Any]:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_./:@-]*", image):
        raise ValueError("Invalid service image reference")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", container):
        raise ValueError("Invalid batch container reference")
    contents = read_sources(root, manifest)
    base = inspect_image(manifest["base_image_id"])
    running = json.loads(docker("inspect", container))
    if (len(running) != 1 or running[0]["Image"] != base["Id"]
            or not running[0]["State"]["Running"]):
        raise ValueError("Running batch image differs from the approved immutable base")
    if inspect_image(image)["Id"] != base["Id"]:
        raise ValueError("Service image tag differs from the running baseline")
    config = base["Config"]
    if config.get("OnBuild"):
        raise ValueError("Base image ONBUILD instructions are not permitted")
    for volume in config.get("Volumes") or {}:
        if any(Path(p).is_relative_to(volume)
               for p in [PROVENANCE, *(APP_ROOT + '/' + name for name in APP_FILES)]):
            raise ValueError("Base image volume overlaps source/provenance destinations")
    user = config.get("User") or ""
    if user and not re.fullmatch(r"[a-zA-Z0-9_.:-]+", user):
        raise ValueError("Unsupported base image user syntax")
    before = fingerprint(base["Id"])
    reference_metadata = before['source_metadata'].get('wepppy/rq/query_catalog_rq.py')
    if not reference_metadata:
        raise ValueError("Baseline catalog source metadata is absent")
    metadata = {name: before['source_metadata'].get(name) or reference_metadata
                for name in APP_FILES}
    token = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    rollback = "wepppy-source-base:" + base["Id"].split(":")[1]
    candidate = "wepppy-source-candidate:" + token
    docker("image", "tag", base["Id"], rollback)
    with tempfile.TemporaryDirectory(prefix="wepppy-source-overlay-") as directory:
        context = Path(directory)
        for name, content in contents.items():
            destination = context / "overlay" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            destination.chmod(0o644)
        (context / "manifest.json").write_text(json.dumps(manifest, sort_keys=True))
        recipe = ["FROM " + rollback]
        if user:
            recipe.append("USER 0")
        recipe += [
            "RUN " + json.dumps(["/opt/venv/bin/python", "-B", "-c", BASE_CHECK,
                                 json.dumps(sorted(APP_FILES))]),
            *('COPY --chown=' + str(metadata[name][1]) + ':' + str(metadata[name][2])
              + ' --chmod=' + format(metadata[name][0], '04o') + ' '
              + json.dumps(['overlay/' + name, APP_ROOT + '/' + name])
              for name in sorted(APP_FILES)),
            'COPY manifest.json /opt/wepppy-source-overlay/manifest.json',
            "RUN " + json.dumps(["/opt/venv/bin/python", "-B", "-c", COMPILE]),
        ]
        if user:
            recipe.append("USER " + user)
        (context / "Dockerfile").write_text("\n".join(recipe) + "\n")
        docker("build", "--pull=false", "--network=none", "--tag", candidate, str(context))
    built = inspect_image(candidate)
    if any(config.get(field) != built["Config"].get(field) for field in CONFIG_FIELDS):
        raise ValueError("Candidate runtime configuration differs from the baseline")
    after = fingerprint(built["Id"])
    if any(before[key] != after[key] for key in ("distributions", "distribution_count", "native")):
        raise ValueError("Candidate dependency/native fingerprint differs from the baseline")
    if after["source_metadata"] != metadata:
        raise ValueError("Candidate source permissions/ownership differ from baseline")
    if after["sources"] != manifest["files"]:
        raise ValueError("Candidate source does not match the manifest")
    if inspect_image(image)["Id"] != base["Id"]:
        raise ValueError("Service image tag changed during candidate build")
    return {"base_image_id": base["Id"], "candidate_image_id": built["Id"],
            "rollback_reference": rollback, "candidate_reference": candidate,
            "target_image": image,
            "source_manifest_sha256": token, "runtime_configuration_matches": True,
            "before": before, "after": after}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    if args.result.exists():
        parser.error("Result evidence already exists; use a fresh destination")
    manifest = json.loads(args.manifest.read_text())
    result = build_overlay(args.source_root, manifest, args.image, args.container)
    with args.result.open("x") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    # Durable rollback evidence precedes the only mutation of the service tag.
    if inspect_image(args.image)["Id"] != result["base_image_id"]:
        raise ValueError("Service image tag changed before promotion")
    running = json.loads(docker("inspect", args.container))
    if (len(running) != 1 or running[0]["Image"] != result["base_image_id"]
            or not running[0]["State"]["Running"]):
        raise ValueError("Batch container changed before promotion")
    docker("image", "tag", result["candidate_image_id"], args.image)
    print(json.dumps({key: value for key, value in result.items() if key not in {"before", "after"}}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        # CLI boundary: retain trusted recipe/probe diagnostics and fail visibly.
        print(error.stderr or "Docker operation failed", file=sys.stderr)
        raise SystemExit(error.returncode) from error
