"""Explicit Run M3 source delivery, without blessing unrelated input changes."""
from copy import deepcopy
from pathlib import Path

from . import rainfall_io as io
from .soil_inputs import META, prepared_sources, _json_snapshot


def _project_inputs(wd, snapshot):
    """Exclude only the module's prepared pointer and immutable receipt assets."""
    result = deepcopy(snapshot)
    inventory = result['selections']['soil_inputs']
    inventory.pop('prepared_sha256')
    root = Path(wd).absolute()
    inventory['dependencies'] = {
        path: value for path, value in inventory['dependencies'].items()
        if Path(path) != root/META
        and not Path(path).is_relative_to(root/'postfire_debris_flow/source_preparation')}
    return result


def prepare_for_run(wd, identity, expected, paths):
    """Acquire only absent metadata; rebase this attempt after verified promotion."""
    from . import production as p, source_acquisition
    from .production_soils import activate_sources

    if prepared_sources(wd)['metadata'] is not None:
        return paths, expected
    frequency = expected['frequency']

    def check_attempt(state):
        attempt = state['run_attempt']
        if (not attempt or attempt['id'] != identity or attempt.get('model') != 'M3'
                or attempt['phase'] != 'running' or attempt['snapshot'] != expected
                or state['model'] != 'M3' or state['frequency_source'] != frequency):
            raise p.WorkflowError('superseded', 'M3 source preparation was superseded. Run again.', 409)

    def verify():
        check_attempt(p.state_at(wd))
        if not p._current_authority(wd, frequency, 'M3', expected['inputs']):
            raise p.WorkflowError('superseded', 'Project inputs changed during source preparation. Run again.', 409)

    verify()
    receipt = source_acquisition.acquire_sources(wd, paths['dem'], paths['mask'])
    record, receipt_hash = _json_snapshot(receipt)
    promoted = activate_sources(wd, receipt, expected_sha256=receipt_hash, verify_project=verify)
    rebased = None
    current_paths = None

    def rebase(state):
        nonlocal rebased, current_paths
        check_attempt(state)
        eligible, readonly, checks, current_paths, snapshot = p.sources(wd,frequency=frequency,model='M3')
        if (not eligible or readonly
                or not all(v for k,v in checks.items() if k != 'noaa' or frequency == 'noaa')
                or not p._worker_source_snapshots_current(wd, _project_inputs(wd,expected['inputs']), _project_inputs(wd,snapshot))
                or io.digest(Path(wd)/META,io.MAX_TEXT) != record['candidate_sha256']):
            raise p.WorkflowError('superseded', 'Project inputs changed after source preparation. Run again.', 409)
        rebased = dict(inputs=snapshot,dnbr=None,frequency=frequency)
        state['run_attempt'].update(snapshot=rebased,source_preparation={
            'receipt': str(Path(receipt).relative_to(Path(wd))),
            'receipt_sha256': receipt_hash, 'promotion': promoted})

    p.mutable(wd).change(rebase)
    return current_paths, rebased
