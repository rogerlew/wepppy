"""Actual copied RAP 39-year analysis, complete input set and finalization lock.

Named inputs receive ordinary read/copy only. Real NoDb hydration, native median
calls, lock, validation, parquet publication and persistence operate on a unique
retained disposable run. Transparent wrappers measure existing boundaries.
This small cropped single-OFE sample is not a universal workload/closure proof.
"""
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import threading
from time import perf_counter
from unittest.mock import patch
from uuid import uuid4

import pandas as pd
from osgeo import gdal
from wepppy.nodb.mods.rap import rap_ts, rap_ts_build
from wepppy.nodb import _derived_build
from wepppy.nodb.core import Ron, Watershed, Wepp

ARTIFACTS = Path(__file__).parent
SOURCE = Path('/wc1/runs/ol/old-fluorosis')
ROOT = Path('/wc1/batch') / ('qa-derived-rap-' + uuid4().hex[:12])
OUTPUT = ARTIFACTS / 'derived_rap_complete_set_probe.json'
ROOT.mkdir()
result = {'scope': __doc__, 'root': str(ROOT), 'uid': os.getuid(), 'gid': os.getgid(),
          'named_inputs': {}, 'module_hashes': {}, 'input_set': [], 'signatures': [],
          'native_calls': [], 'lock_seconds': [], 'validation_seconds': [],
          'cache_note': 'Ordinary copies prime filesystem pages; no cold-storage claim.',
          'success': False}


def named(value):
    return isinstance(value, (str, bytes, os.PathLike)) and str(Path(os.fsdecode(value)).absolute()).startswith('/wc1/runs/')


def audit(event, args):
    if event == 'open' and named(args[0]):
        access, flags = args[1], args[2]
        if (access and any(c in access for c in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            raise PermissionError('No named-run writes in RAP correctness probe')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime', 'os.rename', 'os.link', 'os.symlink'}:
        if any(named(value) for value in args[:2]):
            raise PermissionError('No named-run mutation in RAP correctness probe')


sys.addaudithook(audit)


def version(path):
    info = path.stat()
    return tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        while block := handle.read(1024 * 1024):
            h.update(block)
    return h.hexdigest()


def flush():
    content = json.dumps(result, indent=2) + '\n'
    OUTPUT.write_text(content)
    (ROOT / 'benchmark-manifest.json').write_text(content)


def copy_named(source):
    destination = ROOT / source.relative_to(SOURCE)
    result['named_inputs'][str(source)] = {'version': version(source), 'sha256': digest(source)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    assert digest(destination) == result['named_inputs'][str(source)]['sha256']
    return destination


for module in (_derived_build, rap_ts_build, rap_ts):
    path = Path(module.__file__)
    result['module_hashes'][str(path)] = digest(path)
    (ROOT / path.name).write_bytes(path.read_bytes())

try:
    for filename in ('ron.nodb', 'watershed.nodb', 'wepp.nodb', 'rap_ts.nodb'):
        destination = copy_named(SOURCE / filename)
        # Fixture relocation changes only the disposable copy's persisted paths.
        text = destination.read_text().replace(str(SOURCE), str(ROOT))
        destination.write_text(text)
    for filename in ('config.cfg', 'wepppy.version', 'version.json'):
        if (SOURCE / filename).is_file():
            copy_named(SOURCE / filename)
    for source in (SOURCE / 'rap').iterdir():
        if source.is_file() and (source.name.startswith('_rap_v3_') or source.name == 'rap_ts.parquet'):
            copy_named(source)

    watershed = Watershed.getInstance(str(ROOT))
    required_keys = [Path(watershed.subwta)]
    wepp = Wepp.getInstance(str(ROOT))
    if wepp._multi_ofe:
        required_keys.append(Path(watershed.mofe_map))
    for destination in required_keys:
        source = SOURCE / destination.relative_to(ROOT)
        copy_named(source)
        # Copy possible existing local companions before native inspection.
        for peer in source.parent.iterdir():
            if peer.is_file() and peer != source and (peer.name.lower().startswith(source.name.lower() + '.')
                    or peer.stem.lower() == source.stem.lower()):
                copy_named(peer)

    controller = rap_ts.RAP_TS.getInstance(str(ROOT))
    assert controller.runid == ROOT.name
    assert controller.wd == str(ROOT)
    initial = rap_ts_build._inputs(controller, analysis=True)
    signatures = [initial['subwta']]
    if initial['mofe_map'] is not None:
        signatures.append(initial['mofe_map'])
    signatures.extend(signature for _, signature in initial['rasters'])
    result['years'] = initial['years']
    result['multi_ofe'] = initial['multi_ofe']
    result['bands'] = [band.name for band in initial['bands']]
    result['input_bytes'] = sum(signature[2] for signature in signatures)
    for signature in signatures:
        path = Path(signature[0])
        assert path.is_relative_to(ROOT)
        ds = gdal.Open(str(path), gdal.GA_ReadOnly)
        members = ds.GetFileList()
        result['input_set'].append({'path': str(path), 'bytes': signature[2],
                                    'native_driver': ds.GetDriver().ShortName,
                                    'shape': [ds.RasterYSize, ds.RasterXSize, ds.RasterCount],
                                    'immediate_native_members': members})
        ds = None
    prior_output = ROOT / 'rap/rap_ts.parquet'
    prior = pd.read_parquet(prior_output) if prior_output.exists() else None
    flush()

    real_signature = rap_ts_build.file_signature
    real_check = rap_ts_build._check_inputs
    real_lock, real_unlock = rap_ts.RAP_TS.lock, rap_ts.RAP_TS.unlock
    real_native = rap_ts.identify_median_single_raster_key
    locked = {}
    recorder_lock = threading.Lock()

    def timed_signature(path):
        start = perf_counter()
        value = real_signature(path)
        result['signatures'].append({'path': str(path), 'seconds': perf_counter() - start,
                                     'bytes': value[2], 'under_finalization_lock': bool(locked)})
        return value

    def timed_check(*args, **kwargs):
        start = perf_counter()
        try:
            return real_check(*args, **kwargs)
        finally:
            result['validation_seconds'].append(perf_counter() - start)

    def timed_lock(instance, *args, **kwargs):
        value = real_lock(instance, *args, **kwargs)
        locked[id(instance)] = perf_counter()
        return value

    def timed_unlock(instance, *args, **kwargs):
        try:
            return real_unlock(instance, *args, **kwargs)
        finally:
            started = locked.pop(id(instance), None)
            if started is not None:
                result['lock_seconds'].append(perf_counter() - started)

    def observed_native(**kwargs):
        for key in ('key_fn', 'parameter_fn'):
            assert Path(kwargs[key]).is_relative_to(ROOT), kwargs
        start = perf_counter()
        value = real_native(**kwargs)
        with recorder_lock:
            result['native_calls'].append(dict(kwargs, seconds=perf_counter() - start,
                                                output_keys=len(value)))
        return value

    assert not initial['multi_ofe'], 'This retained actual fixture is single-OFE'
    start = perf_counter()
    with patch.object(rap_ts_build, 'file_signature', timed_signature), \
         patch.object(rap_ts_build, '_check_inputs', timed_check), \
         patch.object(rap_ts.RAP_TS, 'lock', timed_lock), \
         patch.object(rap_ts.RAP_TS, 'unlock', timed_unlock), \
         patch.object(rap_ts, 'identify_median_single_raster_key', observed_native):
        controller.analyze()
    result['whole_analysis_seconds'] = perf_counter() - start
    after = pd.read_parquet(prior_output)
    result['published_rows'] = len(after)
    keys = ['band', 'year', 'topaz_id', 'mofe_id']
    result['prior_output_rows'] = None if prior is None else len(prior)
    result['numerical_parity_with_prior'] = None if prior is None else after.sort_values(keys).reset_index(drop=True).equals(prior.sort_values(keys).reset_index(drop=True))
    result['finalizer_hash_seconds'] = sum(row['seconds'] for row in result['signatures'] if row['under_finalization_lock'])
    result['finalizer_hash_budget_seconds'] = 10.0
    result['finalizer_hash_budget_pass'] = result['finalizer_hash_seconds'] <= 10.0
    result['exact_two_signature_passes'] = len(result['signatures']) == 2 * len(signatures)
    result['expected_native_calls'] = len(initial['rasters']) * len(initial['bands'])
    assert len(result['native_calls']) == result['expected_native_calls']
    assert result['exact_two_signature_passes'] and result['finalizer_hash_budget_pass']
    assert result['lock_seconds'] and after.shape[0] > 0
    result['success'] = True
except BaseException as exc:
    # Probe boundary: retain failure including native extension panic evidence.
    result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    raise
finally:
    result['named_inputs_unchanged'] = all(version(Path(path)) == tuple(proof['version']) and digest(Path(path)) == proof['sha256']
                                           for path, proof in result['named_inputs'].items())
    result['modules_unchanged'] = all(digest(Path(path)) == expected for path, expected in result['module_hashes'].items())
    flush()
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ('named_inputs', 'input_set', 'signatures', 'native_calls')}, indent=2))
