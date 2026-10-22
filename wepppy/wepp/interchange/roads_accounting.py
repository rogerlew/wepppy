"""Roads modeled-area ledger, native composition, and corrected report lineage."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import stat
import uuid

import pyarrow.parquet as pq

from ._rust_interchange import require_wepppyo3_interchange
from .versioning import INTERCHANGE_VERSION

POLICY = 'roads_modeled_area_v1'
LEDGER = Path('wepp/roads/segments/roads.accounting.json')
OUTPUT = Path('wepp/roads/output')


def _hash(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _path(root: Path, relative: str) -> Path:
    path = root / relative
    if Path(relative).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Roads accounting source escapes run: {relative}')
    return path


def _destination(root: Path, relative: Path) -> Path:
    """Reject destination directory aliases before any unlink or publication."""
    path = root / relative
    expected = root.resolve() / relative
    if path.parent.resolve() != expected.parent or path.is_symlink():
        raise ValueError(f'Roads destination alias: {relative}')
    if not expected.is_relative_to(root.resolve() / 'wepp/roads'):
        raise ValueError(f'Not a Roads destination: {relative}')
    return path


def validate_destinations(root: Path) -> None:
    _destination(root, LEDGER)
    folder = _destination(root, OUTPUT / 'interchange/.publication-check').parent
    if folder.exists():
        for path in folder.iterdir():
            if path.is_symlink():
                raise ValueError(f'Roads interchange destination alias: {path.name}')


def has_accounting(root: Path) -> bool:
    """A retained corrected artifact must never silently downgrade to raw water."""
    if (root / LEDGER).exists() or (root / LEDGER).is_symlink():
        return True
    folder = root / OUTPUT / 'interchange'
    if (folder / 'H.accounting.wat.parquet').exists():
        return True
    total = folder / 'totalwatsed3.parquet'
    return total.exists() and b'roads_accounting_policy' in (pq.read_schema(total).metadata or {})


def _save(root: Path, ledger: dict) -> None:
    target = _destination(root, LEDGER)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f'.roads-accounting-{uuid.uuid4().hex}'
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            if target.exists():
                os.fchmod(stream.fileno(), stat.S_IMODE(target.stat().st_mode))
            json.dump(ledger, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _allocation_digest(ledger: dict) -> str:
    allocation = {key: ledger[key] for key in ('policy', 'area_basis', 'sources', 'targets', 'inputs')}
    return hashlib.sha256(json.dumps(allocation, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _verify_inputs(root: Path, inputs: dict) -> None:
    for relative, digest in inputs.items():
        if _hash(_path(root, relative)) != digest:
            raise ValueError(f'Roads accounting source changed: {relative}')


def compose(root: Path, canonical_ids: list[int], records: list[dict], *, single_storm: bool) -> dict:
    """Persist allocation, then reconstruct canonical PASS from original sources.

    Caller has converted continuous contributor WAT/SOIL/ELEMENT before entry.
    This function performs orchestration only; native kernels own model numerics.
    """
    root = Path(root)
    validate_destinations(root)
    native = require_wepppyo3_interchange('Roads accounting', 'roads_wat_geometry',
                                          'roads_pass_geometry', 'combine_weighted_hillslope_pass_files')
    if len(set(canonical_ids)) != len(canonical_ids) or not canonical_ids:
        raise ValueError('Roads canonical IDs must be nonempty and unique')
    grouped: dict[int, list[dict]] = {i: [] for i in canonical_ids}
    identities = set(canonical_ids)
    for record in records:
        if record.get('status') == 'skipped':
            continue
        if record.get('status') != 'completed':
            raise ValueError('Roads accounting requires completed or intentionally skipped records')
        source_id, target = int(record['segment_run_id']), int(record['target_hillslope_wepp_id'])
        if source_id in identities:
            raise ValueError(f'Roads native ID collision: {source_id}')
        identities.add(source_id)
        if target not in grouped:
            raise ValueError(f'Unknown Roads target: {target}')
        if record['segment_pass_relpath'] != str(OUTPUT / f'H{source_id}.pass.dat'):
            raise ValueError('Roads contributor PASS identity/path mismatch')
        grouped[target].append(record)
    ledger = {'policy': POLICY, 'area_basis': 'pass' if single_storm else 'wat',
              'state': 'allocated', 'sources': [], 'targets': [], 'inputs': {}, 'canonical_pass': {}}
    geometry = {}
    observations = {}

    def observe(relative):
        if relative not in observations:
            observations[relative] = _hash(_path(root, relative))

    if not single_storm:
        for rel, ids in [(Path('wepp/output/interchange/H.wat.parquet'), canonical_ids),
                         (OUTPUT / 'interchange/H.wat.parquet', sorted(identities - set(canonical_ids)))]:
            if ids:
                observe(str(rel))
                geometry[str(rel)] = dict(native.roads_wat_geometry(str(_path(root, str(rel))), ids))

    def source(native_id: int, target: int, pass_rel: str, baseline: bool) -> dict:
        pass_path = _path(root, pass_rel)
        observe(pass_rel)
        area, climate = native.roads_pass_geometry(str(pass_path))
        folder = Path('wepp/output/interchange') if baseline else OUTPUT / 'interchange'
        wat = str(folder / 'H.wat.parquet')
        ofes = [] if single_storm else geometry[wat][native_id]
        modeled = area if single_storm else math.fsum(a for _, a in ofes)
        row = {'source_id': f'{"baseline" if baseline else "roads"}:{native_id}',
               'native_id': native_id, 'target_id': target, 'pass': pass_rel,
               'pass_area_m2': area, 'climate_token': climate, 'modeled_area_m2': modeled,
               'represented_area_m2': modeled, 'ofes': ofes,
               'role': 'baseline' if baseline else 'contributor'}
        if not single_storm:
            row['wat'] = wat
            for family in ('soil', 'element'):
                relative = str(folder / f'H.{family}.parquet')
                row[family] = relative if _path(root, relative).exists() else None
        return row

    for target in canonical_ids:
        base = source(target, target, f'wepp/output/H{target}.pass.dat', True)
        contributors = grouped[target]
        replacements = [r for r in contributors if r.get('routing_mode') == 'outslope_unrutted_replacement']
        active = replacements or contributors
        rows = [source(int(r['segment_run_id']), target, r['segment_pass_relpath'], False) for r in active]
        total = math.fsum(r['modeled_area_m2'] for r in rows)
        if replacements:
            for row in rows:
                row['role'] = 'replacement'
        else:
            base['represented_area_m2'] = max(base['modeled_area_m2'] - total, 0.)
            rows.insert(0, base)
        target_area = math.fsum(r['represented_area_m2'] for r in rows)
        ledger['targets'].append({'id': target, 'baseline_area_m2': base['modeled_area_m2'],
                                  'area_m2': target_area, 'area_change_m2': target_area - base['modeled_area_m2'],
                                  'mode': 'replacement' if replacements else 'additive' if active else 'unchanged'})
        for row in rows:
            row['pass_scale'] = row['represented_area_m2'] / row['pass_area_m2']
            row['water_scale'] = row['represented_area_m2'] / row['modeled_area_m2']
            for key in ('pass', 'wat', 'soil', 'element'):
                if row.get(key) and row[key] not in ledger['inputs']:
                    observe(row[key])
                    ledger['inputs'][row[key]] = observations[row[key]]
        ledger['sources'].extend(rows)
    _verify_inputs(root, ledger['inputs'])
    _save(root, ledger)
    for target in ledger['targets']:
        target_id = target['id']
        rows = [s for s in ledger['sources'] if s['target_id'] == target_id]
        output = _destination(root, OUTPUT / f'H{target_id}.pass.dat')
        # Staged baseline links must be removed before composition/copying.
        if output.exists() or output.is_symlink():
            output.unlink()
        if target['mode'] == 'unchanged':
            import shutil
            shutil.copyfile(_path(root, rows[0]['pass']), output)
        else:
            receipt = native.combine_weighted_hillslope_pass_files(
                [(s['source_id'], str(_path(root, s['pass'])), s['represented_area_m2']) for s in rows],
                str(output), target['area_m2'], rows[0]['climate_token'], strategy=POLICY)
            target['pass_receipt'] = {k: v for k, v in receipt.items() if k != 'events'}
        ledger['canonical_pass'][str(output.relative_to(root))] = _hash(output)
    _verify_inputs(root, ledger['inputs'])
    ledger['composition_allocation_sha256'] = _allocation_digest(ledger)
    ledger['state'] = 'composed'
    _save(root, ledger)
    return ledger


def load(root: Path) -> dict:
    ledger = json.loads(_destination(root, LEDGER).read_text())
    if ledger.get('policy') != POLICY or ledger.get('state') not in ('composed', 'routed', 'ready'):
        raise ValueError('Roads accounting ledger is incomplete or unsupported')
    if ledger.get('composition_allocation_sha256') != _allocation_digest(ledger):
        raise ValueError('Roads allocation differs from composed PASS')
    if ledger['state'] in ('routed', 'ready') and ledger.get('routed_allocation_sha256') != _allocation_digest(ledger):
        raise ValueError('Roads allocation differs from routed PASS')
    if ledger['state'] == 'ready' and ledger.get('products_allocation_sha256') != _allocation_digest(ledger):
        raise ValueError('Roads allocation differs from report products')
    _verify_inputs(root, {**ledger['inputs'], **ledger['canonical_pass']})
    return ledger


def mark_routed(root: Path) -> None:
    ledger = load(root)
    ledger['routed_allocation_sha256'] = _allocation_digest(ledger)
    ledger['state'] = 'routed'
    _save(root, ledger)


def regenerate(root: Path, baseflow_opts) -> Path:
    from .totalwatsed3 import _pandas_schema_metadata
    ledger = load(root)
    if ledger['state'] not in ('routed', 'ready'):
        raise ValueError('Corrected Roads reports require fresh watershed routing')
    native = require_wepppyo3_interchange('Roads water accounting', 'roads_water_to_parquet')
    folder = _destination(root, OUTPUT / 'interchange/totalwatsed3.parquet').parent
    _destination(root, OUTPUT / 'interchange/H.accounting.wat.parquet')
    inputs = [(str(_path(root, s['wat'])), s['native_id'], s['target_id'], s['represented_area_m2'],
               str(_path(root, s['soil'])) if s['soil'] else None,
               str(_path(root, s['element'])) if s['element'] else None) for s in ledger['sources']]
    native.roads_water_to_parquet(str(folder / 'H.pass.parquet'), inputs,
        str(folder / 'totalwatsed3.parquet'), str(folder / 'H.accounting.wat.parquet'),
        float(baseflow_opts.gwstorage), float(baseflow_opts.bfcoeff), float(baseflow_opts.dscoeff),
        INTERCHANGE_VERSION.major, INTERCHANGE_VERSION.minor, pandas_metadata=_pandas_schema_metadata())
    _verify_inputs(root, {**ledger['inputs'], **ledger['canonical_pass']})
    if _allocation_digest(load(root)) != _allocation_digest(ledger):
        raise ValueError('Roads allocation changed during regeneration')
    ledger['products_allocation_sha256'] = _allocation_digest(ledger)
    ledger['products'] = {str(p.relative_to(root)): _hash(p) for p in
                          (folder / 'H.pass.parquet', folder / 'totalwatsed3.parquet', folder / 'H.accounting.wat.parquet')}
    # These Roads-only derived tables may predate the newly routed composition.
    for name in ('return_period_events.parquet', 'return_period_event_ranks.parquet'):
        _destination(root, OUTPUT / 'interchange' / name).unlink(missing_ok=True)
    ledger['state'] = 'ready'
    _save(root, ledger)
    return folder / 'totalwatsed3.parquet'


def accounting_source(root: Path) -> Path:
    ledger = load(root)
    if ledger['state'] != 'ready':
        raise ValueError('Roads accounting reports are not ready')
    for relative, digest in ledger['products'].items():
        if _hash(_path(root, relative)) != digest:
            raise ValueError(f'Roads accounting product changed: {relative}')
    source = root / OUTPUT / 'interchange/H.accounting.wat.parquet'
    for path in (source, source.parent / 'totalwatsed3.parquet'):
        if (pq.read_schema(path).metadata or {}).get(b'roads_accounting_policy') != POLICY.encode():
            raise ValueError(f'Missing Roads accounting marker: {path}')
    return source
