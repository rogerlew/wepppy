"""Numerical provenance for Ash water inputs; historical files remain readable."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import uuid
import re

import numpy as np

ALGORITHM = "mofe-water-v2"
POST_PROOF = "water_accounting.json"


def _signature(path: Path) -> tuple[int, int, int, int, int]:
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def fingerprint(path: Path) -> str:
    before = _signature(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    if before != _signature(path):
        raise ValueError(f"Ash water source changed while hashing: {path}")
    return digest.hexdigest()


def _write(path: Path, payload: dict) -> None:
    # Small visible sidecar, atomically published beside its model/post artifact.
    name = str(path.with_name(path.name + '.' + uuid.uuid4().hex))
    descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    if path.exists():
        os.fchmod(descriptor, path.stat().st_mode & 0o777)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(payload, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def bind_model_source(frame, cache: dict) -> None:
    """Require one pre-read WAT generation across parent-loaded hills."""
    source = Path(frame.attrs['source_path'])
    expected = tuple(frame.attrs['source_signature'])
    identity = (str(source), expected)
    if _signature(source) != expected:
        raise ValueError('Ash WAT source changed since daily loading')
    if cache and cache['identity'] != identity:
        raise ValueError('Ash WAT source changed between hillslope loads')
    digest = frame.attrs.get('water_source_sha256')
    if not digest:
        raise ValueError('Ash requires a WAT fingerprint captured before daily loading')
    if cache and cache['digest'] != digest:
        raise ValueError('Ash WAT source changed between hillslope loads')
    if not cache:
        cache.update(identity=identity, digest=digest)


def model_input_proof(frame) -> dict | None:
    required = ['P', 'RM', 'Q', 'Total-Soil Water', 'Snow-Water']
    if not np.isfinite(frame[required].to_numpy(dtype=np.float64)).all():
        raise ValueError('Ash requires finite daily water inputs, including physical terminal Q')
    if frame.attrs.get('water_aggregation') != ALGORITHM:
        return None  # Custom in-memory model callers cannot claim verified WAT lineage.
    source = Path(frame.attrs['source_path'])
    expected = tuple(frame.attrs['source_signature'])
    if _signature(source) != expected:
        raise ValueError('Ash WAT source changed since daily loading')
    digest = frame.attrs.get('water_source_sha256')
    if not digest:
        raise ValueError('Ash requires a WAT fingerprint captured before daily loading')
    if _signature(source) != expected:
        raise ValueError('Ash WAT source changed during input verification')
    return {'algorithm': ALGORITHM, 'wat_sha256': digest}


def write_model_proof(output, proof) -> None:
    path = Path(str(output) + '.water.json')
    if proof is None:
        # A prior sidecar must never survive an unverified overwrite.
        path.unlink(missing_ok=True)
        return
    _write(path, {**proof, 'model_sha256': fingerprint(Path(output))})


def post_inputs(root: Path, manifest, mapping) -> dict:
    interchange = root / 'wepp/output/interchange'
    sources = {name: fingerprint(interchange / name) for name in
               ('H.wat.parquet', 'H.pass.parquet', 'totalwatsed3.parquet')}
    models = {}
    for relative, *_ in manifest:
        path = root / relative
        try:
            proof = json.loads(Path(str(path) + '.water.json').read_text())
        except FileNotFoundError as exc:
            raise ValueError('Historical Ash model inputs are unverified; regenerate the model before postprocessing') from exc
        digest = fingerprint(path)
        if (not isinstance(proof, dict) or proof.get('algorithm') != ALGORITHM or
                proof.get('wat_sha256') != sources['H.wat.parquet'] or
                proof.get('model_sha256') != digest):
            raise ValueError('Stale Ash model water inputs; regenerate the model before postprocessing')
        models[relative] = digest
    return {'algorithm': ALGORITHM, 'sources': sources, 'models': models, 'mapping': mapping}


def publish_post_proof(root: Path, proof: dict) -> None:
    outputs = {path.name: fingerprint(path) for path in sorted((root/'ash/post').glob('*.parquet'))}
    _write(root/'ash/post'/POST_PROOF, {**proof, 'outputs': outputs})


def historical_warning(root: Path, mapping=None) -> str | None:
    post = root/'ash/post'
    if not any(post.glob('*.parquet')) and not any(post.glob('*.pkl')):
        return None
    warning = 'Historical ash results: physical water accounting is unverified or stale. Regenerate the ash model to refresh these results.'
    try:
        proof = json.loads((post/POST_PROOF).read_text())
        if not isinstance(proof, dict) or proof.get('algorithm') != ALGORITHM or proof.get('mapping') != mapping:
            return warning
        if not all(isinstance(proof.get(key), dict) for key in ('sources', 'models', 'outputs')):
            return warning
        if not isinstance(mapping, dict) or not isinstance(mapping.get('manifest'), list):
            return warning
        if set(proof['models']) != {entry[0] for entry in mapping['manifest']}:
            return warning
        actual_outputs = {path.name for path in post.glob('*.parquet')}
        if not actual_outputs or set(proof['outputs']) != actual_outputs:
            return warning
        if set(proof['sources']) != {'H.wat.parquet', 'H.pass.parquet', 'totalwatsed3.parquet'}:
            return warning
        for name, digest in proof['sources'].items():
            if fingerprint(root/'wepp/output/interchange'/name) != digest:
                return warning
        for name, digest in proof['models'].items():
            if not re.fullmatch(r'ash/H[0-9]+_ash\.parquet', name):
                return warning
            if not (root/name).resolve().is_relative_to(root.resolve()):
                return warning
            if fingerprint(root/name) != digest:
                return warning
        for name, digest in proof['outputs'].items():
            if Path(name).name != name or not name.endswith('.parquet'):
                return warning
            if not (post/name).resolve().is_relative_to(root.resolve()):
                return warning
            if fingerprint(post/name) != digest:
                return warning
    except (OSError, ValueError, KeyError, TypeError):
        # Historical read boundary: preserve downloads, never claim freshness.
        return warning
    return None
