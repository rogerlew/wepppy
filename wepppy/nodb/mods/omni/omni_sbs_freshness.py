"""Main-file SBS receipts; native companion closure is deliberately not claimed."""
from __future__ import annotations

from dataclasses import dataclass
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import shutil
import copy

from wepppy.all_your_base.file_digest import sha256_file


_RECEIPT = '_sbs_content'


def _changed():
    return OSError(errno.ESTALE, 'Omni SBS input changed during scenario execution')


def is_sbs(definition):
    from .omni import OmniScenario
    selected = definition.get('type')
    if isinstance(selected, OmniScenario):
        return selected is OmniScenario.SBSmap
    return selected in ('sbs_map', 8)


def definition_json(definition):
    from .omni import OmniScenario
    return json.dumps({key: str(value) if key == 'type' and isinstance(value, OmniScenario) else value
                       for key, value in definition.items()
                       if key != _RECEIPT or not is_sbs(definition)}, sort_keys=True, default=str)


def _selected_definition(definition):
    payload = json.loads(definition_json(definition))
    # RQ already normalizes integer scenario types before dispatch; selection
    # guards compare that same meaning without rewriting persisted definitions.
    if is_sbs(definition):
        payload['type'] = 'sbs_map'
    return payload


def _version(path):
    info = Path(path).stat()
    return (str(Path(path).resolve()), info.st_dev, info.st_ino, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _fd_version(stream, path):
    info = os.fstat(stream.fileno())
    return (str(Path(path).resolve()), info.st_dev, info.st_ino, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _receipt(definition):
    source = os.fspath(definition['sbs_file_path'])
    return {'version': 1, 'source_path': source, 'sha256': sha256_file(source)}


def receipt_from_signature(signature):
    payload = json.loads(signature)
    if not isinstance(payload, dict):
        raise ValueError('Invalid Omni scenario signature')
    receipt = payload.get(_RECEIPT)
    if _RECEIPT not in payload:
        return None
    if (not isinstance(receipt, dict) or set(receipt) != {'version', 'source_path', 'sha256'}
            or type(receipt['version']) is not int or receipt['version'] != 1
            or not isinstance(receipt['source_path'], str)
            or not isinstance(receipt['sha256'], str) or len(receipt['sha256']) != 64
            or any(character not in '0123456789abcdef' for character in receipt['sha256'])):
        raise ValueError('Invalid Omni SBS content receipt')
    return receipt


def child_source(omni, definition):
    from .omni import OMNI_REL_DIR, _scenario_name_from_scenario_definition
    return (Path(omni.wd) / OMNI_REL_DIR / 'scenarios' /
            _scenario_name_from_scenario_definition(definition) / 'disturbed' /
            Path(definition['sbs_file_path']).name)


def scenario_signature(omni, definition):
    base = definition_json(definition)
    if not is_sbs(definition):
        return base
    try:
        receipt = _receipt(definition)
    except FileNotFoundError:
        from .omni import _scenario_name_from_scenario_definition
        previous = omni.scenario_dependency_tree.get(_scenario_name_from_scenario_definition(definition), {})
        prior_signature = previous.get('signature')
        if prior_signature is None:
            return base
        receipt = receipt_from_signature(prior_signature)
        if receipt is None:
            return base  # Historical consumed upload remains explicitly unverified.
        previous_definition = json.loads(prior_signature)
        previous_definition.pop(_RECEIPT)
        if previous_definition != json.loads(base):
            return base
        if receipt['source_path'] != os.fspath(definition['sbs_file_path']):
            raise ValueError('Omni SBS receipt selects a different upload')
        if sha256_file(child_source(omni, definition)) != receipt['sha256']:
            raise _changed()
    payload = json.loads(base)
    payload[_RECEIPT] = receipt
    return json.dumps(payload, sort_keys=True, default=str)


@dataclass
class SbsExecution:
    definition: dict
    receipt: dict
    require_selection: bool = False
    copied_path: Path | None = None
    copied_version: tuple | None = None

    @classmethod
    def capture(cls, definition, signature=None, *, require_selection=False):
        receipt = _receipt(definition) if signature is None else receipt_from_signature(signature)
        if signature is not None:
            original = json.loads(signature)
            original.pop(_RECEIPT, None)
            if original != json.loads(definition_json(definition)):
                raise _changed()
        if receipt is None:
            # Preserve the existing missing-upload error when legacy reuse is
            # ineligible; never infer a queued receipt after dispatch.
            _receipt(definition)
            raise ValueError('Omni SBS execution requires an uploaded-source receipt')
        if receipt['source_path'] != os.fspath(definition['sbs_file_path']):
            raise ValueError('Omni SBS execution requires an uploaded-source receipt')
        return cls(json.loads(definition_json(definition)), receipt, require_selection)

    def validate_selection(self, omni):
        if self.require_selection and not any(
                _selected_definition(item) == _selected_definition(self.definition) for item in omni.scenarios):
            raise _changed()

    def before_reset(self, omni):
        self.validate_selection(omni)
        if _receipt(self.definition) != self.receipt:
            raise _changed()

    def copy_to(self, target):
        source = Path(self.receipt['source_path'])
        target = Path(target)
        digest = hashlib.sha256()
        with source.open('rb') as incoming:
            before = _fd_version(incoming, source)
            info = os.fstat(incoming.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ValueError('Omni SBS upload must be an ordinary file')
            # Open without truncating: aliases must fail with the same protection
            # as the previous shutil.copyfile, including hardlinked uploads.
            target_fd = os.open(target, os.O_WRONLY | os.O_CREAT, 0o666)
            with os.fdopen(target_fd, 'wb') as outgoing:
                target_info = os.fstat(outgoing.fileno())
                if (info.st_dev, info.st_ino) == (target_info.st_dev, target_info.st_ino):
                    raise shutil.SameFileError(f'{source!r} and {target!r} are the same file')
                outgoing.truncate(0)
                remaining = info.st_size + 1
                length = 0
                while remaining:
                    chunk = incoming.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    digest.update(chunk)
                    outgoing.write(chunk)
                    length += len(chunk)
                    remaining -= len(chunk)
                if (length != info.st_size or _fd_version(incoming, source) != before
                        or _version(source) != before or digest.hexdigest() != self.receipt['sha256']):
                    raise _changed()
        if sha256_file(target) != self.receipt['sha256']:
            raise _changed()
        self.copied_path = target
        self.copied_version = _version(target)
        # Existing upload/copy has no conditional-unlink lock. Reject observable
        # replacements; a writer after this final check remains outside isolation.
        if (_version(source) != before or sha256_file(source) != self.receipt['sha256']
                or _version(source) != before):
            raise _changed()
        source.unlink()

    def validate_admission(self, omni):
        self.validate_selection(omni)
        if self.copied_path is None or self.copied_version is None:
            raise ValueError('Omni SBS copy has not completed')
        try:
            if (_version(self.copied_path) != self.copied_version
                    or sha256_file(self.copied_path) != self.receipt['sha256']
                    or _version(self.copied_path) != self.copied_version):
                raise _changed()
            try:
                current = _receipt(self.definition)
            except FileNotFoundError:
                current = self.receipt
            if (current != self.receipt
                    or _version(self.copied_path) != self.copied_version):
                raise _changed()
        except OSError as exc:
            if exc.errno in (errno.ENOENT, errno.ENOTDIR, errno.EACCES, errno.EPERM, errno.ESTALE):
                raise _changed() from exc
            raise


__all__ = ['SbsExecution', 'child_source', 'definition_json', 'is_sbs',
           'receipt_from_signature', 'scenario_signature']


def _refresh_locked(omni):
    durable = type(omni).load_detached(omni.wd)
    if durable is None:
        raise FileNotFoundError(omni._nodb)
    # The canonical local lock token is stored outside __dict__ on this instance.
    omni.__dict__.clear()
    omni.__dict__.update(durable.__dict__)
    omni._init_logging()


def invalidate_sbs_association(omni, execution):
    from .omni import _scenario_name_from_scenario_definition
    with omni.locked():
        _refresh_locked(omni)
        execution.before_reset(omni)
        tree = dict(omni.scenario_dependency_tree)
        tree.pop(_scenario_name_from_scenario_definition(execution.definition), None)
        omni._scenario_dependency_tree = tree


def admit_sbs_association(omni, execution, scenario_name, entry, state):
    with omni.locked():
        _refresh_locked(omni)
        execution.validate_admission(omni)
        tree = dict(omni.scenario_dependency_tree)
        tree[scenario_name] = entry
        states = list(omni.scenario_run_state)
        states.append(state)
        omni._scenario_dependency_tree = tree
        omni._scenario_run_state = states


__all__ += ['invalidate_sbs_association', 'admit_sbs_association']


@dataclass
class SbsReuse:
    definition: dict
    signature: str
    path: Path | None
    version: tuple | None
    association: dict

    @classmethod
    def capture(cls, omni, definition, signature):
        receipt = receipt_from_signature(signature)
        selected = None
        version = None
        if receipt is not None:
            selected = Path(definition['sbs_file_path'])
            try:
                version = _version(selected)
            except FileNotFoundError:
                selected = child_source(omni, definition)
                version = _version(selected)
            if sha256_file(selected) != receipt['sha256'] or _version(selected) != version:
                raise _changed()
        from .omni import _scenario_name_from_scenario_definition
        association = copy.deepcopy(omni.scenario_dependency_tree.get(
            _scenario_name_from_scenario_definition(definition)))
        if association is None or association.get('signature') != signature:
            raise _changed()
        return cls(json.loads(definition_json(definition)), signature, selected, version, association)

    def validate_admission(self, omni):
        from .omni import _scenario_name_from_scenario_definition
        if omni.scenario_dependency_tree.get(
                _scenario_name_from_scenario_definition(self.definition)) != self.association:
            raise _changed()
        if not any(_selected_definition(item) == _selected_definition(self.definition) for item in omni.scenarios):
            raise _changed()
        try:
            if scenario_signature(omni, self.definition) != self.signature:
                raise _changed()
            if self.path is not None and _version(self.path) != self.version:
                raise _changed()
        except OSError as exc:
            if exc.errno in (errno.ENOENT, errno.ENOTDIR, errno.EACCES, errno.EPERM, errno.ESTALE):
                raise _changed() from exc
            raise


def prune_sbs_dependency_state(omni):
    """Retain the existing stale-scenario cleanup using the durable selection."""
    from .omni import _scenario_name_from_scenario_definition
    with omni.locked():
        _refresh_locked(omni)
        active = {_scenario_name_from_scenario_definition(item) for item in omni.scenarios}
        omni._scenario_dependency_tree = {
            name: entry for name, entry in omni.scenario_dependency_tree.items() if name in active}


__all__ += ['SbsReuse', 'prune_sbs_dependency_state']
