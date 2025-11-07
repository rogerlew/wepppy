"""Dynamic import facade for optional NoDb controller mods.

This package exposes dozens of optional NoDb controllers (for example BAER,
Disturbed, RRED). Rather than importing every module eagerly, it lazily resolves
attributes on demand so projects only pay for the dependencies they use. The
resolver scans the ``wepppy.nodb`` tree to build a legacy redirect map which
preserves older dotted-paths for jsonpickle payloads.

Consumers typically write ``from wepppy.nodb import mods`` and access controller
classes as attributes (``mods.Disturbed``). The ``__getattr__`` hook below
performs the lookup and caches the result.
"""

import importlib
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

MODS_DIR = os.path.dirname(__file__)


def _normalize_path(value: str) -> str:
    return os.path.abspath(os.path.expanduser(value))


def _resolve_extended_mods_data() -> str:
    """
    Determine where heavy weight location bundles live.

    Priority:
    1. ``EXTENDED_MODS_DATA`` environment variable (always honored)
    2. Default bind mounts such as ``/wc1/geodata/extended_mods_data`` or
       ``/geodata/extended_mods_data`` when present
    3. Legacy fallback under ``wepppy/nodb/mods/locations`` to preserve
       backwards-compatible behavior when the external repo is absent.
    """

    env_override = os.environ.get('EXTENDED_MODS_DATA')
    if env_override:
        return _normalize_path(env_override)

    for candidate in ('/wc1/geodata/extended_mods_data', '/geodata/extended_mods_data'):
        if candidate and os.path.exists(candidate):
            return _normalize_path(candidate)

    legacy_fallback = os.path.join(MODS_DIR, 'locations')
    return _normalize_path(legacy_fallback)


EXTENDED_MODS_DATA = _resolve_extended_mods_data()

try:
    from wepppy.nodb.base import _LEGACY_MODULE_REDIRECTS
except Exception:  # pragma: no cover - fallback during partial imports
    _LEGACY_MODULE_REDIRECTS = {}

if not _LEGACY_MODULE_REDIRECTS:  # pragma: no cover - defensive rebuild
    def _discover_legacy_module_redirects():
        nodb_dir = Path(__file__).resolve().parent.parent
        redirects = {}

        def register(stem, module_path):
            if stem in ('', '__init__'):
                return
            redirects.setdefault(stem, module_path)

        for init_path in nodb_dir.rglob('__init__.py'):
            rel = init_path.relative_to(nodb_dir)
            parts = rel.with_suffix('').parts[:-1]
            if not parts:
                continue
            module_path = 'wepppy.nodb.' + '.'.join(parts)
            register(init_path.parent.name, module_path)

        for py_path in nodb_dir.rglob('*.py'):
            if py_path.name == '__init__.py':
                continue
            rel = py_path.relative_to(nodb_dir)
            module_path = 'wepppy.nodb.' + '.'.join(rel.with_suffix('').parts)
            register(py_path.stem, module_path)

        return redirects

    _LEGACY_MODULE_REDIRECTS = _discover_legacy_module_redirects()


def _camel_to_snake(name: str) -> str:
    parts = name.split('_')
    snake_parts = []
    for part in parts:
        if not part:
            continue
        if part.isupper():
            snake_parts.append(part.lower())
        else:
            converted = re.sub(r'(?<!^)(?=[A-Z0-9])', '_', part).lower()
            snake_parts.append(converted)
    return '_'.join(snake_parts)


def _candidate_stems(name: str):
    snake = _camel_to_snake(name)
    stems = {name, name.lower(), snake, snake.replace('_', '')}
    return [stem for stem in stems if stem]


@lru_cache(maxsize=None)
def _load_mod_attribute(name: str):
    for stem in _candidate_stems(name):
        module_path = _LEGACY_MODULE_REDIRECTS.get(stem)
        if not module_path or '.mods.' not in module_path:
            continue

        module = importlib.import_module(module_path)
        if hasattr(module, name):
            return getattr(module, name)

    for stem, module_path in _LEGACY_MODULE_REDIRECTS.items():
        if '.mods.' not in module_path:
            continue
        module = importlib.import_module(module_path)
        exported = getattr(module, '__all__', ())
        try:
            iterator = iter(exported)
        except TypeError:
            continue
        for item in iterator:
            if isinstance(item, str) and item == name:
                if hasattr(module, name):
                    return getattr(module, name)
                break

    raise AttributeError(f"module 'wepppy.nodb.mods' has no attribute '{name}'")


def __getattr__(name: str):
    value = _load_mod_attribute(name)
    globals()[name] = value
    return value


def __dir__():  # pragma: no cover - used for introspection
    exported = {
        name
        for name in globals()
        if not name.startswith('_')
    }

    for stem, module_path in _LEGACY_MODULE_REDIRECTS.items():
        if '.mods.' not in module_path:
            continue
        module = importlib.import_module(module_path)
        exported.update(
            name
            for name in getattr(module, '__all__', ())
            if isinstance(name, str)
        )
    return sorted(exported)


__all__ = ['MODS_DIR', 'EXTENDED_MODS_DATA']
