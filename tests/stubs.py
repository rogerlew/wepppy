from __future__ import annotations

import importlib.util
import sys
import types


def ensure_geopandas_stub() -> None:
    if "geopandas" in sys.modules:
        return
    if importlib.util.find_spec("geopandas") is not None:
        return

    geopandas_module = types.ModuleType("geopandas")
    geopandas_module.__wepppy_stub__ = True
    geopandas_module.GeoDataFrame = object  # pragma: no cover - stub
    sys.modules["geopandas"] = geopandas_module
