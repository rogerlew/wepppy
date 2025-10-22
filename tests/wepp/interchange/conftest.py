import os
import sys
from typing import Iterator

import pytest


@pytest.fixture(scope="session", autouse=True)
def _force_serial_interchange() -> Iterator[None]:
    prev = os.environ.get("WEPP_INTERCHANGE_FORCE_SERIAL")
    os.environ["WEPP_INTERCHANGE_FORCE_SERIAL"] = "1"
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop("WEPP_INTERCHANGE_FORCE_SERIAL", None)
        else:
            os.environ["WEPP_INTERCHANGE_FORCE_SERIAL"] = prev


@pytest.fixture(autouse=True)
def _purge_interchange_modules() -> Iterator[None]:
    """
    Interchange tests monkeypatch ``sys.modules`` with lightweight package stubs.
    Ensure those stubs do not leak into subsequent test modules by purging the
    injected entries after each module finishes.
    """
    yield

    for name in list(sys.modules):
        if name.startswith("wepppy.wepp.interchange"):
            sys.modules.pop(name, None)

    # If the test introduced lightweight stubs for the parent packages, drop them
    # so later imports load the real package implementations.
    sys.modules.pop("wepppy.wepp", None)
    sys.modules.pop("wepppy", None)

    # Reload the public package so downstream tests interact with the real module.
    import importlib
    importlib.import_module("wepppy")
    importlib.import_module("wepppy.all_your_base")
