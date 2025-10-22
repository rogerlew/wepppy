from __future__ import annotations

import importlib
from types import ModuleType
from typing import Dict, Iterable

__all__ = [
    "climate_bp",
    "debris_flow_bp",
    "disturbed_bp",
    "landuse_bp",
    "interchange_bp",
    "observed_bp",
    "omni_bp",
    "project_bp",
    "rangeland_bp",
    "rangeland_cover_bp",
    "rhem_bp",
    "soils_bp",
    "treatments_bp",
    "unitizer_bp",
    "watar_bp",
    "watershed_bp",
    "wepp_bp",
]

_module_cache: Dict[str, ModuleType] = {}


def _load(name: str) -> ModuleType:
    module = _module_cache.get(name)
    if module is None:
        module = importlib.import_module(f".{name}", __name__)
        _module_cache[name] = module
        globals()[name] = module
    return module


def __getattr__(name: str) -> ModuleType:
    if name in __all__:
        return _load(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> Iterable[str]:
    return sorted(set(__all__) | set(globals().keys()))
