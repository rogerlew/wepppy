from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path
from typing import List

os.environ.setdefault("WEPP_INTERCHANGE_FORCE_SERIAL", "1")

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_OUTPUT = REPO_ROOT / "tests" / "wepp" / "interchange" / "test_project" / "output"
_CLEANUP_TARGETS: List[str] = []


def load_module(full_name: str, relative_path: str):
    parts = full_name.split(".")
    for idx in range(1, len(parts)):
        pkg = ".".join(parts[:idx])
        if pkg not in sys.modules:
            module = types.ModuleType(pkg)
            package_path = REPO_ROOT.joinpath(*pkg.split("."))
            if package_path.exists():
                module.__path__ = [str(package_path)]
            else:
                module.__path__ = []
            sys.modules[pkg] = module
            _CLEANUP_TARGETS.append(pkg)

    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(full_name, module_path)
    if spec and module_path.name == "__init__.py":
        spec.submodule_search_locations = [str(module_path.parent)]
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    _CLEANUP_TARGETS.append(full_name)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def cleanup_import_state() -> None:
    while _CLEANUP_TARGETS:
        name = _CLEANUP_TARGETS.pop()
        sys.modules.pop(name, None)

    sys.modules.pop("wepppy.wepp", None)
    sys.modules.pop("wepppy", None)
