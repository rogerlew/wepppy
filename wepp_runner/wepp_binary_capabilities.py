"""Installed release capabilities shared by Builder and run-time selection."""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path

from .wepp_runner import (
    _collect_binary_identity,
    get_linux_wepp_bin_opts,
    get_linux_wepp_bin_role_paths,
)

__all__ = ['read_binary_capabilities', 'get_binary_capabilities', 'get_compatible_wepp_bin_opts', 'binary_selection_revision']
FEATURES = ('mofe_supported', 'single_user_defined_inputs_supported')


def read_binary_capabilities(watershed_path: str, hillslope_path: str) -> dict[str, bool]:
    """Validate fresh role sidecars; absent optional declarations mean unknown."""
    declarations = []
    releases = []
    for role, executable in (('watershed', watershed_path), ('hillslope', hillslope_path)):
        if not Path(executable).is_file() or not os.access(executable, os.X_OK):
            raise ValueError(f'WEPP {role} executable is unavailable: {executable}')
        sidecar = Path(str(executable) + '.json')
        try:
            raw = sidecar.read_text(encoding='utf-8')
        except FileNotFoundError:
            declarations.append(dict.fromkeys(FEATURES))
            releases.append(None)
            continue
        except OSError as exc:
            raise ValueError(f'Cannot read WEPP {role} release capabilities: {sidecar}') from exc
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise ValueError(f'Invalid WEPP {role} release metadata: {sidecar}') from exc
        if not isinstance(payload, dict) or payload.get('schema') != 'wepp-binary-release-metadata-v1':
            raise ValueError(f'Invalid WEPP {role} release metadata schema: {sidecar}')
        if payload.get('binary_role') != role:
            raise ValueError(f'WEPP release sidecar has incorrect binary_role: {sidecar}')
        if payload.get('binary_name') != Path(executable).resolve().name:
            raise ValueError(f'WEPP release sidecar has incorrect binary_name: {sidecar}')
        release = tuple(payload.get(key) for key in ('release_tag', 'source_repo', 'source_branch', 'source_commit'))
        releases.append(release)
        features = payload.get('features')
        if not isinstance(features, dict):
            raise ValueError(f'WEPP release sidecar features must be an object: {sidecar}')
        identity = _collect_binary_identity(executable)
        if identity['binary_identity_status'] != 'ok' or payload.get('sha256') != identity['binary_sha256']:
            raise ValueError(f'WEPP release sidecar sha256 does not match executable: {sidecar}')
        selected = {key: features.get(key) for key in FEATURES}
        if any(key in features and type(features[key]) is not bool for key in FEATURES):
            raise ValueError(f'WEPP release capability declarations must be boolean: {sidecar}')
        if any(value is True for value in selected.values()) and not all(isinstance(value, str) and value for value in release):
            raise ValueError(f'WEPP declared capabilities require release/source identity: {sidecar}')
        declarations.append(selected)
    if declarations[0] != declarations[1]:
        raise ValueError('WEPP watershed and hillslope release capability declarations disagree.')
    if all(release is not None for release in releases) and releases[0] != releases[1]:
        raise ValueError('WEPP watershed and hillslope release/source identities disagree.')
    return {key: value is True for key, value in declarations[0].items()}


def get_binary_capabilities(binary_id: str) -> dict[str, bool]:
    """Resolve only exact installed provider IDs, never user-supplied paths."""
    if binary_id not in get_linux_wepp_bin_opts():
        raise ValueError(f'WEPP executable is not installed: {binary_id!r}')
    return read_binary_capabilities(*get_linux_wepp_bin_role_paths(binary_id))


def get_compatible_wepp_bin_opts(*, multi_ofe: bool = False,
                                single_user_defined_inputs: bool = False) -> tuple[str, ...]:
    """Return current provider choices satisfying the requested input capabilities."""
    choices = []
    for binary_id in dict.fromkeys(get_linux_wepp_bin_opts()):
        capabilities = get_binary_capabilities(binary_id)
        if multi_ofe and not capabilities['mofe_supported']:
            continue
        if single_user_defined_inputs and not capabilities['single_user_defined_inputs_supported']:
            continue
        choices.append(binary_id)
    return tuple(choices)


def binary_selection_revision(binary_ids: tuple[str, ...]) -> str:
    """Bind effective choice metadata to current executable role bytes."""
    payload = {
        binary_id: {
            'features': get_binary_capabilities(binary_id),
            'roles': [_collect_binary_identity(path)['binary_sha256']
                      for path in get_linux_wepp_bin_role_paths(binary_id)],
        }
        for binary_id in binary_ids
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()
