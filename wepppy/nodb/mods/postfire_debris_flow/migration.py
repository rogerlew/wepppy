"""Explicit, audited migration of legacy hidden Staley attempt records."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid

from .observability import record_attempts, write_json
from .postfire_debris_flow import PostfireDebrisFlow
from . import production as p

__all__ = ['migrate_attempts']

# Exact pre-observability source set at 4305972a6. Only storage changed.
LEGACY_ENGINE = {
  "integration.py": "17accb77a6eb42eff0795026e57394b440f9477f540a0e0d68b77957b6bad1cb",
  "m1_inputs.py": "6d0ed44714bdb177829fef979c5e9f9c77cab8418c6d66a2532b33f46e18e085",
  "staley2017.py": "7967994f9ff68088a7f2585b58043e2b9575bee888d42ff2a7c4e77a3629cab0",
  "dnbr.py": "6639c0b4f1b734875a04f64d6b5356158467887bff157416ca61be452fa74ffc",
  "encoding.py": "aed2572df051f9e8418166030e57ca28db0b2ac3147c8cbeaf718aebf2aaef29",
  "rainfall.py": "fd1da7a6ec7ce21268f7089b90d083ebfade9f66f49937396a59230531efa3da",
  "rainfall_io.py": "f6f981d99062677fdf4d1fa44ec3edf609cf6562c7df8ba1178aa5028b83843e",
  "results.py": "1fe9101f5821e294bbedb1befd47a4aacb0bfb085f0d71324600112424b25d68",
  "production.py": "0e163fb8068b93e024d80c52ea337919367f883d37503657ebcf312b260337bd"
}

TARGET_ENGINE = {**LEGACY_ENGINE,
    'production.py': '7229ff6d2438b118fdb7374a6672d994f674cf91872dbe0f372b3ae780e0f269',
    'dnbr.py': '7c6de76ea53053f3ec6dbb5df8ad60d2e382c8db0c43ed391f82e43152a375e5',
}


def _json(path):
    return json.loads(Path(path).read_text())


def _visible(rel):
    parts = Path(rel).parts
    if not parts or parts[0] != '.staging' or '..' in parts:
        raise ValueError('Invalid legacy artifact path.')
    return str(Path('attempts', *(('legacy_' + part[1:]) if part.startswith('.') else part for part in parts[1:])))


def _rewrite(value, paths, hashes):
    if isinstance(value, str):
        if value in hashes:
            return hashes[value]
        for old, new in paths:
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [_rewrite(item, paths, hashes) for item in value]
    if isinstance(value, dict):
        return {_rewrite(key, paths, {}): _rewrite(item, paths, hashes) for key, item in value.items()}
    return value


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)


def _jobs_idle(state, runid, connection):
    from rq import Queue
    from rq.job import Job
    from rq.utils import as_text
    from rq.exceptions import NoSuchJobError
    from rq.registry import StartedJobRegistry, DeferredJobRegistry, ScheduledJobRegistry
    terminal = {'finished', 'failed', 'stopped', 'canceled'}
    for kind in ('upload_attempt', 'run_attempt'):
        record = state[kind]
        if not record:
            continue
        if record['phase'] in p.ACTIVE:
            raise ValueError('Cannot migrate an active postfire attempt.')
        if record.get('job_id'):
            try:
                job = Job.fetch(record['job_id'], connection=connection)
            except NoSuchJobError:
                continue  # Already-terminal records can outlive RQ retention.
            if job.get_status(refresh=True) not in terminal:
                raise ValueError('Postfire job is not terminal.')
    ids = set(Queue('default', connection=connection).get_job_ids())
    for cls in (StartedJobRegistry, DeferredJobRegistry, ScheduledJobRegistry):
        registry = cls('default', connection=connection)
        # Read membership directly: this RQ version's get_job_ids cleans up jobs.
        ids.update(as_text(identity) for identity in connection.zrange(registry.key, 0, -1))
    for identity in ids:
        try:
            job = Job.fetch(identity, connection=connection)
        except NoSuchJobError:
            continue
        if ('postfire_debris_flow' in job.func_name and runid in job.args
                and job.get_status(refresh=True) not in terminal):
            raise ValueError('An earlier postfire job is still active.')


@contextmanager
def _admission(controller):
    import redis
    from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
    from wepppy.rq.submission_recovery import rq_submission_lock
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
        with rq_submission_lock(connection, f'{controller.runid}:postfire-admission',
                                lifecycle_key=controller.runid) as lease:
            controller.lock()
            try:
                PostfireDebrisFlow.getInstance(controller.wd)
                _jobs_idle(controller.state, controller.runid, connection)
                yield lease
            finally:
                controller.unlock()


def _validate_accepted(wd, state):
    for key in ('active_dnbr', 'last_successful_run'):
        record = state[key]
        if record and not p.artifacts_current(wd, record):
            raise ValueError('Accepted artifacts changed; migration cannot establish trust.')
    result = state['last_successful_run']
    if result and result.get('predictor_artifacts'):
        if not p.artifacts_current(wd, {'artifacts': result['predictor_artifacts']}):
            raise ValueError('Accepted predictor artifacts changed.')


def _path_map(root, inventory):
    paths = []
    for rel, info in inventory.items():
        paths.extend(((str(root/rel), str(root/info['target'])),
                      ('postfire_debris_flow/'+rel, 'postfire_debris_flow/'+info['target'])))
    paths.extend(((str(root/'.staging'), str(root/'attempts')),
                  ('postfire_debris_flow/.staging', 'postfire_debris_flow/attempts')))
    return sorted(paths, key=lambda pair: len(pair[0]), reverse=True)


def _reject_constant(text):
    raise ValueError(text)


def _render(groups, paths):
    hashes = {}
    rendered = {}
    while groups:
        progressed = False
        for old, (raw, value) in list(groups.items()):
            if any(token in groups for token in _strings(value)):
                continue
            updated = _rewrite(value, paths, hashes)
            data = raw if updated == value else (json.dumps(updated, indent=2, allow_nan=False)+'\n').encode()
            hashes[old] = hashlib.sha256(data).hexdigest()
            rendered[old] = data
            del groups[old]
            progressed = True
        if not progressed:
            raise ValueError('Cyclic JSON provenance requires inspection.')
    return hashes, rendered


def _validate_plan(wd, controller, root, audit, report):
    backup = p.safe(wd, audit/'original_metadata'/controller.filename)
    if p.digest(backup) != report['original_nodb_sha256']:
        raise ValueError('Migration NoDb backup changed.')
    raw_state = _json(backup).get('py/state', {}).get('_state')
    if raw_state != report['original_state']:
        raise ValueError('Original migration state does not match the NoDb backup; inspect serialization.')
    if _json(p.safe(wd, audit/'original_metadata'/'state.json')) != report['original_state']:
        raise ValueError('Migration original state changed.')
    inventory = report['inventory']
    for rel, info in inventory.items():
        if info['target'] != _visible(rel):
            raise ValueError('Invalid migration target.')
        p.safe(wd, root/rel, exists=False)
        p.safe(wd, root/info['target'], exists=False)
    for key in ('active_dnbr', 'last_successful_run'):
        record = report['original_state'][key]
        if not record:
            continue
        for field in ('artifacts', 'predictor_artifacts'):
            for rel, sig in record.get(field, {}).items():
                prefix = 'postfire_debris_flow/'
                if rel.startswith(prefix+'.staging/'):
                    info = inventory.get(rel[len(prefix):])
                    if (info is None or len(sig) != 5 or info['sha256'] != sig[4]
                            or info['size'] != sig[1] or sig[0] != rel):
                        raise ValueError('Accepted migration inventory changed.')
    paths = _path_map(root, inventory)
    if [list(pair) for pair in paths] != [list(pair) for pair in report['paths']]:
        raise ValueError('Migration path plan changed.')
    groups = {}
    for info in inventory.values():
        if not info['target'].endswith('.json'):
            if 'rebased_sha256' in info:
                raise ValueError('Binary payload cannot be rebased.')
            continue
        original = p.safe(wd, audit/'original_metadata'/info['target'])
        if p.digest(original) != info['sha256']:
            raise ValueError('Original migration metadata changed.')
        raw = original.read_bytes()
        try:
            value = json.loads(raw, parse_constant=_reject_constant)
        except (ValueError, UnicodeDecodeError):
            if 'rebased_sha256' in info:
                raise ValueError('Malformed original metadata cannot be rebased.')
            continue
        groups.setdefault(info['sha256'], (raw, value))
    hashes, rendered = _render(groups, paths)
    if hashes != report['hashes']:
        raise ValueError('Migration hash plan changed.')
    for info in inventory.values():
        if info['sha256'] in rendered and info['target'].endswith('.json'):
            planned = p.safe(wd, audit/'rebased_metadata'/info['target'])
            if (planned.read_bytes() != rendered[info['sha256']]
                    or hashes[info['sha256']] != info.get('rebased_sha256')):
                raise ValueError('Migration metadata plan changed.')


def _relocated_path(wd, target, rel):
    # A stopped nested-name conversion can leave any prefix already converted.
    path = target
    for part in Path(rel).parts[1:]:
        renamed = 'legacy_'+part[1:] if part.startswith('.') else part
        choices = [path/part] if renamed == part else [path/part, path/renamed]
        found = [item for item in choices if item.exists() or item.is_symlink()]
        if len(found) != 1:
            raise ValueError('Missing or conflicting relocated artifact.')
        path = p.safe(wd, found[0], exists=False)
    return path


def _prepare(wd, controller, root):
    state = controller.state
    _validate_accepted(wd, state)
    legacy = root/'.staging'
    if (root/'attempts').exists():
        raise ValueError('Both legacy and visible attempt trees exist; inspect before migration.')
    entries = sorted(legacy.rglob('*'))
    targets = set()
    inventory = {}
    for path in entries:
        if path.is_symlink():
            raise ValueError('Legacy artifacts must not use symlinks.')
        rel = str(path.relative_to(root))
        target = _visible(rel)
        if target in targets:
            raise ValueError('Visible legacy artifact names conflict.')
        targets.add(target)
        if path.is_file():
            inventory[rel] = {'target': target, 'sha256': p.digest(path), 'size': path.stat().st_size}
        elif not path.is_dir():
            raise ValueError('Legacy artifact is not a regular file or directory.')
    # All accepted and filesystem checks precede migration writes.
    folder = p.safe(wd, root/'migrations', exists=False)
    folder.mkdir(exist_ok=True)
    audit = folder/uuid.uuid4().hex
    audit.mkdir()
    write_json(audit/'status.json', {'status': 'preparing', 'recovery': 'No project mutation until migration.json exists.'})
    backup = audit/'original_metadata'
    backup.mkdir()
    shutil.copyfile(Path(wd)/controller.filename, backup/controller.filename)
    write_json(backup/'state.json', state)
    paths = _path_map(root, inventory)
    groups = {}
    for rel, info in inventory.items():
        if not rel.endswith('.json'):
            continue
        raw = (root/rel).read_bytes()
        dest = backup/info['target']
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        try:
            value = json.loads(raw, parse_constant=_reject_constant)
        except (ValueError, UnicodeDecodeError):
            continue  # Preserve malformed historical diagnostics verbatim.
        groups.setdefault(info['sha256'], (raw, value))
    hashes, rendered = _render(groups, paths)
    planned = audit/'rebased_metadata'
    for rel, info in inventory.items():
        if rel.endswith('.json') and info['sha256'] in rendered:
            dest = planned/info['target']
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(rendered[info['sha256']])
            info['rebased_sha256'] = hashes[info['sha256']]
    report = {'schema_version': 1, 'status': 'prepared', 'base_revision': '4305972a6',
              'inventory': inventory, 'paths': paths, 'hashes': hashes,
              'original_state': state, 'planned_state': None,
              'original_nodb_sha256': p.digest(backup/controller.filename)}
    write_json(audit/'migration.json', report)
    return audit, report


def _updated_state(wd, report):
    inventory = report['inventory']
    updated = _rewrite(report['original_state'], report['paths'], report['hashes'])
    upgrades = []
    for key in ('run_attempt', 'last_successful_run'):
        record = updated[key]
        if record:
            selections = record.get('snapshot', {}).get('inputs', {}).get('selections', {})
            if selections.get('engine_sha256') == LEGACY_ENGINE and p.engine_identity() == TARGET_ENGINE:
                selections['engine_sha256'] = p.engine_identity()
                upgrades.append(key)
    for key in ('active_dnbr', 'last_successful_run'):
        record = updated[key]
        if record:
            for field in ('artifacts', 'predictor_artifacts'):
                if field in record:
                    signatures = {}
                    migrated = {'postfire_debris_flow/'+info['target'] for info in inventory.values()}
                    for rel, sig in record[field].items():
                        if rel not in migrated:
                            if not p.artifacts_current(wd, {'artifacts': {rel: sig}}):
                                raise ValueError('Unmigrated input changed during migration.')
                            signatures[rel] = sig
                        else:
                            signatures[rel] = p.signature(wd, Path(wd)/rel, strong=len(sig)==5)
                    record[field] = signatures
    return updated, upgrades


def _install(wd, controller, root, audit, report, lease):
    _validate_plan(wd, controller, root, audit, report)
    state = controller.state
    if state != report['original_state']:
        expected, _ = _updated_state(wd, report)
        if state != expected:
            raise ValueError('Project state changed since migration started.')
    inventory = report['inventory']
    legacy, target = root/'.staging', root/'attempts'
    if legacy.exists() and target.exists():
        raise ValueError('Conflicting migration trees.')
    # Resume accepts only original or planned metadata; binary changes always fail.
    for rel, info in inventory.items():
        path = root/rel if legacy.exists() else _relocated_path(wd, target, rel)
        path = p.safe(wd, path)
        if p.digest(path) not in {info['sha256'], info.get('rebased_sha256')}:
            raise ValueError('Artifact changed during migration; original evidence retained.')
    lease.checkpoint()
    if legacy.exists():
        os.rename(legacy, target)
    # Resume nested-name conversion even if root relocation already completed.
    for path in sorted(target.rglob('*'), key=lambda pth: len(pth.parts), reverse=True):
        if path.name.startswith('.'):
            p.safe(wd, path, exists=False)
            destination = path.with_name('legacy_'+path.name[1:])
            if destination.exists() or destination.is_symlink():
                raise ValueError('Conflicting visible artifact.')
            path.rename(destination)
    report['status'] = 'relocated'
    write_json(audit/'migration.json', report)
    for rel, info in inventory.items():
        if 'rebased_sha256' not in info:
            continue
        src = p.safe(wd, audit/'rebased_metadata'/info['target'])
        if p.digest(src) != info['rebased_sha256']:
            raise ValueError('Migration metadata plan changed.')
        dst = p.safe(wd, root/info['target'])
        pending = p.safe(wd, dst.with_name(dst.name+'.migration-pending'), exists=False)
        shutil.copyfile(src, pending)
        os.replace(pending, dst)
    updated, upgrades = _updated_state(wd, report)
    report.update(planned_state=updated, upgraded_engine_records=upgrades,
                  new_engine=p.engine_identity(), status='metadata_ready')
    write_json(audit/'migration.json', report)
    lease.checkpoint()
    controller._assert_lock_owned_for_dump()
    controller._state = deepcopy(updated)
    controller.dump()
    record_attempts(wd, updated)
    for attempt in target.iterdir():
        if attempt.is_dir() and not (attempt/'status.json').exists():
            write_json(attempt/'status.json', {'schema_version': 1, 'kind': 'historical_unknown',
                       'attempt': {'id': attempt.name, 'phase': 'historical_unknown',
                                   'reason': 'No durable attempt receipt survives.'}})
    report['status'] = 'state_committed'
    write_json(audit/'migration.json', report)


def migrate_attempts(wd, *, resume=None):
    """Migrate once, or explicitly resume a retained migration UUID after failure."""
    wd = Path(wd).absolute()
    controller = PostfireDebrisFlow.tryGetInstance(str(wd))
    if controller is None:
        return {'status': 'absent'}
    root = p.safe(wd, wd/'postfire_debris_flow', exists=False)
    audit = None
    with _admission(controller) as lease:
        if resume is not None:
            if not p.ID.fullmatch(resume):
                raise ValueError('Invalid migration ID.')
            audit = p.safe(wd, root/'migrations'/resume, exists=False)
            report = _json(p.safe(wd, audit/'migration.json'))
            if report['status'] == 'complete':
                return report
        elif not (root/'.staging').exists():
            for path in (root/'migrations').glob('*/migration.json'):
                if _json(path)['status'] != 'complete':
                    raise ValueError('Incomplete migration; explicitly resume its ID.')
            return {'status': 'already_visible'}
        else:
            p.safe(wd, root/'.staging', exists=False)
            audit, report = _prepare(wd, controller, root)
        _install(wd, controller, root, audit, report, lease)
    from .publication import publish_outputs
    from .preflight import notify
    publish_outputs(wd)
    notify(wd)
    report['status'] = 'complete'
    write_json(audit/'migration.json', report)
    write_json(audit/'status.json', {'status': 'complete'})
    return report
