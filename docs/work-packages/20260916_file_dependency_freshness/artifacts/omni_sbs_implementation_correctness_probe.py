"""S01 disposable native-byte/orchestration and actual NoDb admission probes.

Actual Omni persistence, Redis lock, clone/reset, receipt/copy and GDAL reads run.
Full landuse/soil/WEPP execution and RQ transport are explicit seams. No named run
is read/written; all records and retained native files are under a unique root.
"""
from copy import deepcopy
import errno
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
from osgeo import gdal
import pytest

from wepppy.nodb.mods.omni import omni as module
from wepppy.nodb.mods.omni import omni_sbs_freshness as fresh
from wepppy.nodb.mods.omni.omni import Omni, OmniScenario
from wepppy.rq import omni_rq
from wepppy.rq import exception_logging

ROOT = Path('/wc1/batch') / ('qa-omni-correctness-' + uuid4().hex[:12])
ROOT.mkdir()
RECORDS = {}
MODULE_HASHES = {str(Path(item.__file__)): hashlib.sha256(Path(item.__file__).read_bytes()).hexdigest()
                 for item in (module, fresh, omni_rq)}


def record(name, value):
    RECORDS[name] = value
    value = {'root': str(ROOT), 'cases': RECORDS, 'module_hashes': MODULE_HASHES,
             'modules_unchanged': all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
                                      for path, digest in MODULE_HASHES.items())}
    (ROOT / 'probe-manifest.json').write_text(json.dumps(value, indent=2) + '\n')
    Path(__file__).with_suffix('.json').write_text(json.dumps(value, indent=2) + '\n')
    print('OMNI_CORRECTNESS', name, json.dumps(RECORDS[name], sort_keys=True))


def raster(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    target = gdal.GetDriverByName('GTiff').Create(str(path), 2, 2, 1, gdal.GDT_Byte)
    target.SetGeoTransform((500000, 30, 0, 4400000, 0, -30))
    target.GetRasterBand(1).WriteArray(np.full((2, 2), value, dtype=np.uint8))
    target = None


def pixels(path):
    data = gdal.Open(str(path))
    result = data.ReadAsArray().tolist()
    data = None
    return result


@pytest.fixture
def owner(monkeypatch, request):
    wd = ROOT / 'runs' / (request.node.name[:70] + '-' + uuid4().hex[:6])
    wd.mkdir(parents=True)
    omni = Omni(str(wd), '0.cfg', run_group='batch', group_name=ROOT.name)
    assert ROOT.name in omni.runid
    source = Path(omni.omni_dir) / '_limbo/0/same.tif'
    definition = {'type': 'sbs_map', 'sbs_file_path': str(source)}
    raster(source, 1)
    omni.scenarios = [definition]
    loss = wd / 'base-loss.txt'
    loss.write_bytes(b'unchanged-base-loss')
    monkeypatch.setattr(Omni, 'base_scenario', property(lambda _: OmniScenario.Undisturbed))
    monkeypatch.setattr(Omni, '_loss_pw0_path_for_scenario', lambda self, _: str(Path(self.wd) / 'base-loss.txt'))
    monkeypatch.setattr(Omni, '_year_set_for_scenario', lambda self, _: {2020})
    monkeypatch.setattr(Omni, '_post_omni_run', lambda *args: None)
    monkeypatch.setattr(Omni, 'compile_hillslope_summaries', lambda *args: None)
    monkeypatch.setattr(Omni, 'compile_channel_summaries', lambda *args: None)
    monkeypatch.setattr(Omni, 'scenarios_report', lambda *args: None)
    return omni, source, definition, loss


def prior_entry(omni, definition, loss, *, legacy=False):
    name = module._scenario_name_from_scenario_definition(definition)
    signature = fresh.definition_json(definition) if legacy else omni._scenario_signature(definition)
    entry = {'dependency_target': 'undisturbed', 'dependency_path': str(loss),
             'dependency_sha1': hashlib.sha1(loss.read_bytes()).hexdigest(),
             'signature': signature, 'timestamp': 1}
    omni.scenario_dependency_tree = {name: entry}
    return name, entry


def executor(monkeypatch, observed, *, after_native=None, fail_after_reset=False):
    def run(self, definition, *, _sbs_execution=None):
        name = module._scenario_name_from_scenario_definition(definition)
        if not fresh.is_sbs(definition):
            observed.append((name, None))
            return str(Path(self.wd) / '_pups/omni/scenarios' / name), name
        assert _sbs_execution is not None
        _sbs_execution.before_reset(self)
        target_root = Path(module._omni_clone(definition, self.wd, self.runid,
            before_reset=lambda: fresh.invalidate_sbs_association(self, _sbs_execution)))
        if fail_after_reset:
            (target_root / 'native-partial.txt').write_text('retained failed work')
            raise RuntimeError('probe native failure after reset')
        target = target_root / 'disturbed' / Path(definition['sbs_file_path']).name
        target.parent.mkdir(exist_ok=True)
        _sbs_execution.copy_to(target)
        observed.append((name, pixels(target)))
        if after_native is not None:
            after_native(self, _sbs_execution, target)
        _sbs_execution.validate_admission(self)
        return str(target_root), name
    monkeypatch.setattr(Omni, 'run_omni_scenario', run)


def test_legacy_invalidated_between_skip_decision_and_admission_is_not_resurrected(owner):
    omni, source, definition, loss = owner
    name, entry = prior_entry(omni, definition, loss, legacy=True)
    source.unlink()
    guard = fresh.SbsReuse.capture(omni, definition, entry['signature'])
    concurrent = Omni.load_detached(omni.wd)
    with concurrent.locked():
        concurrent._scenario_dependency_tree = {}
    error = None
    try:
        fresh.admit_sbs_association(omni, guard, name, entry, {'scenario': name, 'status': 'skipped'})
    except OSError as exc:
        error = exc.errno
    durable = Omni.load_detached(omni.wd)
    result = {'error': error, 'association_resurrected': name in durable.scenario_dependency_tree,
              'states': durable.scenario_run_state}
    record('legacy_invalidated', result)
    assert error == errno.ESTALE
    assert not result['association_resurrected']


def test_direct_native_upload_change_consumed_reuse_and_touch(owner, monkeypatch):
    omni, source, definition, _ = owner
    observed = []
    executor(monkeypatch, observed)
    states = []
    omni.run_omni_scenarios()
    states.append(omni.scenario_run_state[0]['status'])
    omni.run_omni_scenarios()
    states.append(omni.scenario_run_state[0]['status'])
    raster(source, 3)
    omni.run_omni_scenarios()
    states.append(omni.scenario_run_state[0]['status'])
    target = fresh.child_source(omni, definition)
    target.touch()
    omni.run_omni_scenarios()
    states.append(omni.scenario_run_state[0]['status'])
    record('direct_generations', {'states': states, 'native_pixels': observed,
                                 'final_pixels': pixels(target), 'source_consumed': not source.exists()})
    assert states == ['executed', 'skipped', 'executed', 'skipped']
    assert [value for _, value in observed] == [[[1, 1], [1, 1]], [[3, 3], [3, 3]]]


def test_direct_native_admission_preserves_concurrent_unrelated_fields(owner, monkeypatch):
    omni, _, _, _ = owner
    observed = []

    def concurrent_update(self, execution, target):
        fresh_owner = Omni.load_detached(self.wd)
        with fresh_owner.locked():
            fresh_owner._review_unrelated = 'concurrent-durable-value'
            fresh_owner._scenario_run_state = [{'scenario': 'other', 'status': 'executed'}]

    executor(monkeypatch, observed, after_native=concurrent_update)
    omni.run_omni_scenarios()
    durable = Omni.load_detached(omni.wd)
    record('durable_fields', {'unrelated': durable._review_unrelated, 'states': durable.scenario_run_state})
    assert durable._review_unrelated == 'concurrent-durable-value'
    assert [row['scenario'] for row in durable.scenario_run_state][0] == 'other'
    assert len(durable.scenario_run_state) == 2


def test_mixed_direct_order_remains_sbs_uniform_then_mulch(owner, monkeypatch):
    omni, _, definition, _ = owner
    mulch = {'type': 'mulch', 'base_scenario': 'uniform_low', 'ground_cover_increase': '30'}
    omni.scenarios = [mulch, definition, {'type': 'uniform_low'}]
    observed = []
    executor(monkeypatch, observed)
    omni.run_omni_scenarios()
    names = [row['scenario'] for row in omni.scenario_run_state]
    record('direct_order', {'states': names, 'executions': [name for name, _ in observed]})
    assert names == [module._scenario_name_from_scenario_definition(definition), 'uniform_low', 'mulch_30_uniform_low']
    assert len(names) == 3


def test_failed_destructive_rerun_keeps_partial_without_old_association(owner, monkeypatch):
    omni, _, definition, loss = owner
    name, _ = prior_entry(omni, definition, loss, legacy=True)
    child = fresh.child_source(omni, definition)
    child.parent.mkdir(parents=True)
    child.write_bytes(b'old accepted generation')
    executor(monkeypatch, [], fail_after_reset=True)
    with pytest.raises(RuntimeError, match='after reset'):
        omni.run_omni_scenarios()
    durable = Omni.load_detached(omni.wd)
    partial = child.parent.parent / 'native-partial.txt'
    record('failed_reset', {'association_present': name in durable.scenario_dependency_tree,
                            'partial_retained': partial.exists(), 'old_child_present': child.exists()})
    assert name not in durable.scenario_dependency_tree and partial.exists() and not child.exists()


def test_rq_worker_queued_drift_rejects_before_clone_and_preserves_prior(owner, monkeypatch):
    omni, source, definition, loss = owner
    name, entry = prior_entry(omni, definition, loss)
    child = fresh.child_source(omni, definition)
    child.parent.mkdir(parents=True)
    child.write_bytes(b'prior accepted child')
    before_tree = deepcopy(omni.scenario_dependency_tree)
    source.write_bytes(b'new queued bytes')
    observed = []
    executor(monkeypatch, observed)
    job = SimpleNamespace(id='independent-disposable-worker')
    monkeypatch.setattr(omni_rq, 'get_current_job', lambda: job)
    monkeypatch.setattr(omni_rq, 'get_wd', lambda runid: omni.wd if runid == omni.runid else None)
    monkeypatch.setattr(exception_logging, 'get_wd', lambda runid: omni.wd if runid == omni.runid else None)
    monkeypatch.setattr(omni_rq.StatusMessenger, 'publish', lambda *args: None)
    with pytest.raises(OSError) as error:
        omni_rq.run_omni_scenario_rq(omni.runid, definition, dependency_target='undisturbed',
                                    dependency_path=str(loss), signature=entry['signature'])
    durable = Omni.load_detached(omni.wd)
    record('queued_drift', {'error': error.value.errno, 'no_native': not observed,
                            'prior_tree_preserved': durable.scenario_dependency_tree == before_tree,
                            'prior_child_preserved': child.read_bytes() == b'prior accepted child'})
    assert error.value.errno == errno.ESTALE and not observed
    assert durable.scenario_dependency_tree == before_tree
    assert child.read_bytes() == b'prior accepted child'


def test_legacy_consumed_source_needed_for_year_rerun_keeps_missing_error(owner, monkeypatch):
    omni, source, definition, loss = owner
    _, entry = prior_entry(omni, definition, loss, legacy=True)
    source.unlink()
    before = deepcopy(omni.scenario_dependency_tree)
    monkeypatch.setattr(Omni, '_year_set_for_scenario',
                        lambda self, name: {2020} if name == 'undisturbed' else {2021})
    observed = []
    executor(monkeypatch, observed)
    error = None
    try:
        omni.run_omni_scenarios()
    except (OSError, ValueError) as exc:
        error = exc
    durable = Omni.load_detached(omni.wd)
    record('legacy_year_rerun', {'error_type': type(error).__name__, 'message': str(error),
                                'prior_association_preserved': durable.scenario_dependency_tree == before,
                                'no_native': not observed})
    assert isinstance(error, FileNotFoundError)
    assert not observed and durable.scenario_dependency_tree == before


@pytest.mark.parametrize('selected_type', ['sbs_map', 8, OmniScenario.SBSmap], ids=['string', 'integer', 'enum'])
def test_actual_dispatcher_worker_and_consumed_skip(owner, monkeypatch, selected_type):
    omni, source, definition, _ = owner
    definition['type'] = selected_type
    with omni.locked():
        omni._scenarios = [definition]
        omni._use_rq_job_pool_concurrency = True
    observed = []
    executor(monkeypatch, observed)
    job = SimpleNamespace(id='independent-dispatcher', meta={}, save=lambda: None)
    monkeypatch.setattr(omni_rq, 'get_current_job', lambda: job)
    monkeypatch.setattr(omni_rq, 'get_wd', lambda runid: omni.wd if runid == omni.runid else None)
    monkeypatch.setattr(exception_logging, 'get_wd', lambda runid: omni.wd if runid == omni.runid else None)
    monkeypatch.setattr(omni_rq.StatusMessenger, 'publish', lambda *args: None)
    queued = []

    class Queue:
        def __init__(self, name, connection):
            assert name == 'batch'

        def enqueue_call(self, func, args=(), kwargs=None, **options):
            child = SimpleNamespace(id='disposable-job-' + str(len(queued)))
            queued.append((func, args, kwargs or {}, options, child))
            return child

    monkeypatch.setattr(omni_rq, 'Queue', Queue)
    omni_rq.run_omni_scenarios_rq(omni.runid)
    assert len(queued) == 3
    function, args, kwargs, _, _ = queued[0]
    assert function is omni_rq.run_omni_scenario_rq
    assert fresh.receipt_from_signature(kwargs['signature'])['sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    error = None
    try:
        function(*args, **kwargs)
    except OSError as exc:
        error = exc.errno
    if error is not None:
        record('rq_type_' + type(selected_type).__name__, {'error': error, 'native_calls': observed,
                                                'source_preserved': source.exists()})
        pytest.fail('Supported scenario type rejected after dispatcher normalization: ' + str(error))
    assert not source.exists()
    queued.clear()
    omni_rq.run_omni_scenarios_rq(omni.runid)
    durable = Omni.load_detached(omni.wd)
    result = {'error': None, 'native_calls': observed, 'states': durable.scenario_run_state,
              'second_queued_functions': [function.__name__ for function, *_ in queued]}
    record('rq_type_' + type(selected_type).__name__, result)
    assert len(observed) == 1 and observed[0][1] == [[1, 1], [1, 1]]
    assert len(queued) == 2
    assert [row['status'] for row in durable.scenario_run_state] == ['skipped']
