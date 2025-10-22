import importlib
import sys

import pytest


@pytest.fixture(scope="session", autouse=True)
def _ensure_all_your_base() -> None:
    module = importlib.import_module("wepppy.all_your_base")
    sys.modules["wepppy.all_your_base"] = module
