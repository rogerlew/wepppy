import importlib
import inspect

import pytest

pytestmark = pytest.mark.unit


def _reload_f_esri_module():
    import wepppy.f_esri as f_esri

    return importlib.reload(f_esri)


@pytest.fixture(autouse=True)
def _reset_f_esri_timeout_env(monkeypatch):
    monkeypatch.delenv("F_ESRI_COMMAND_TIMEOUT", raising=False)
    _reload_f_esri_module()
    yield
    monkeypatch.delenv("F_ESRI_COMMAND_TIMEOUT", raising=False)
    _reload_f_esri_module()


def test_f_esri_default_timeout_is_1800_when_env_unset(monkeypatch):
    monkeypatch.delenv("F_ESRI_COMMAND_TIMEOUT", raising=False)
    f_esri = _reload_f_esri_module()

    assert f_esri.DEFAULT_TIMEOUT == 1800
    assert inspect.signature(f_esri.c2c_gpkg_to_gdb).parameters["timeout"].default == 1800
    assert inspect.signature(f_esri.gpkg_to_gdb).parameters["timeout"].default == 1800


def test_f_esri_timeout_honors_env_override(monkeypatch):
    monkeypatch.setenv("F_ESRI_COMMAND_TIMEOUT", "2400")
    f_esri = _reload_f_esri_module()

    assert f_esri.DEFAULT_TIMEOUT == 2400
    assert inspect.signature(f_esri.c2c_gpkg_to_gdb).parameters["timeout"].default == 2400
    assert inspect.signature(f_esri.gpkg_to_gdb).parameters["timeout"].default == 2400
