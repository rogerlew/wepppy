import importlib
from pathlib import Path


_CAO_SHIM_PATH = (
    Path(__file__).resolve().parent.parent / "services" / "cao" / "wepppy"
)
if _CAO_SHIM_PATH.is_dir():
    __path__.append(str(_CAO_SHIM_PATH))


_LAZY_SUBMODULES = {"rq", "climates", "mcp"}


def __getattr__(name):
    if name in _LAZY_SUBMODULES:
        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
