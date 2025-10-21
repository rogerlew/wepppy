from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Set

import pytest

pytest.importorskip("flask")


def _discover_blueprint_names() -> Set[str]:
    """
    Discover blueprint names exported from wepppy.weppcloud.routes.*

    We assume blueprints follow the convention of exposing a Flask Blueprint
    instance whose attribute name ends with `_bp`. (Existing modules such as
    `disturbed_bp`, `interchange_bp`, etc. follow this pattern.)
    """
    discovered: Set[str] = set()

    package = importlib.import_module("wepppy.weppcloud.routes")
    for _, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        if is_pkg:
            continue
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            # Optional dependencies (rasterio, etc.) may be absent locally; skip those modules.
            continue
        for attr_name, attr_value in vars(module).items():
            if not attr_name.endswith("_bp"):
                continue
            if getattr(attr_value, "name", None):
                discovered.add(attr_value.name)
    return discovered


def _registered_blueprint_names() -> Set[str]:
    module = importlib.import_module("wepppy.weppcloud._blueprints_context")
    register_fn = getattr(module, "register_blueprints")
    assert inspect.isfunction(register_fn), "register_blueprints must be a function"

    seen: Set[str] = set()

    class DummyApp:
        def register_blueprint(self, blueprint):
            name = getattr(blueprint, "name", None)
            if name:
                seen.add(name)

    dummy = DummyApp()
    register_fn(dummy)
    return seen


def test_all_blueprints_registered():
    discovered = _discover_blueprint_names()
    registered = _registered_blueprint_names()

    # Some blueprints are intentionally not auto-registered (e.g. security bits),
    # so allow a small expected difference list if needed. For now we expect
    # exact parity; update this assertion if exceptions arise.
    missing = discovered - registered
    assert not missing, f"Blueprints missing from register_blueprints: {sorted(missing)}"
