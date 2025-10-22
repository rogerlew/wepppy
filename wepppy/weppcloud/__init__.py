from __future__ import annotations

import importlib
from typing import Any, List

__all__ = ["combined_watershed_viewer_generator"]


def __getattr__(name: str) -> Any:
    if name == "combined_watershed_viewer_generator":
        module = importlib.import_module(
            ".combined_watershed_viewer_generator", __name__
        )
        value = module.combined_watershed_viewer_generator
        globals()[name] = value
        return value
    if name == "routes":
        module = importlib.import_module(".routes", __name__)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> List[str]:
    return sorted(set(globals()) | set(__all__) | {"routes"})
