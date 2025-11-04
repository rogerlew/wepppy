import importlib
import pytest


@pytest.fixture(scope="session", autouse=True)
def _ensure_wepppy_nodb_namespace() -> None:
    """Expose `wepppy.nodb` when running the CAO test slice in isolation.

    The top-level test suite config (tests/conftest.py) already performs this
    wiring, but tests under services/cao execute without that fixture.  Import
    the real NoDb package and attach it to the root module so monkeypatch.setattr
    on dotted paths such as ``wepppy.nodb.base.redis_lock_client`` works
    consistently.
    """
    root_pkg = importlib.import_module("wepppy")
    if hasattr(root_pkg, "nodb"):
        return

    nodb_pkg = importlib.import_module("wepppy.nodb")
    setattr(root_pkg, "nodb", nodb_pkg)

    try:
        base_module = importlib.import_module("wepppy.nodb.base")
    except ModuleNotFoundError:
        return
    setattr(nodb_pkg, "base", base_module)
