import importlib


def __getattr__(name):
    if name == "rq":
        module = importlib.import_module(f"{__name__}.rq")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
