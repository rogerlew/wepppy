from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STUBS_READY = False


def _ensure_package_module(name: str) -> ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = ModuleType(name)
        module.__path__ = []  # type: ignore[attr-defined]
        sys.modules[name] = module
    return module


def _install_stubs() -> None:
    if "flask" not in sys.modules:
        flask_stub = ModuleType("flask")
        flask_stub.current_app = SimpleNamespace(config={})
        flask_stub.g = SimpleNamespace()

        def _noop(*args: Any, **kwargs: Any) -> None:
            return None

        flask_stub.jsonify = _noop
        flask_stub.make_response = _noop
        flask_stub.render_template = _noop
        flask_stub.url_for = _noop
        sys.modules["flask"] = flask_stub

    if "werkzeug" not in sys.modules:
        werkzeug_stub = ModuleType("werkzeug")
        exceptions_stub = ModuleType("werkzeug.exceptions")

        class _HTTPException(Exception):
            pass

        exceptions_stub.HTTPException = _HTTPException
        werkzeug_stub.exceptions = exceptions_stub
        sys.modules["werkzeug"] = werkzeug_stub
        sys.modules["werkzeug.exceptions"] = exceptions_stub

    if "redis" not in sys.modules:
        redis_stub = ModuleType("redis")

        class _ConnectionError(Exception):
            pass

        class _ConnectionPool:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.args = args
                self.kwargs = kwargs

        class _StrictRedis:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self._store: dict[str, str] = {}

            def ping(self) -> bool:
                return True

            def get(self, key: str) -> str | None:
                return self._store.get(key)

            def set(self, key: str, value: str, ex: int | None = None) -> None:
                self._store[key] = value

        redis_stub.ConnectionPool = _ConnectionPool
        redis_stub.StrictRedis = _StrictRedis
        redis_stub.exceptions = SimpleNamespace(ConnectionError=_ConnectionError)
        sys.modules["redis"] = redis_stub

    if "jsonpickle" not in sys.modules:
        jsonpickle_stub = ModuleType("jsonpickle")

        def _passthrough(value: Any, *args: Any, **kwargs: Any) -> Any:
            return value

        jsonpickle_stub.encode = _passthrough
        jsonpickle_stub.decode = _passthrough
        sys.modules["jsonpickle"] = jsonpickle_stub

    if "utm" not in sys.modules:
        utm_stub = ModuleType("utm")

        def _utm_from_latlon(*args: Any, **kwargs: Any) -> tuple[int, int, int, str]:
            return (0, 0, 0, "N")

        def _utm_to_latlon(*args: Any, **kwargs: Any) -> tuple[float, float]:
            return (0.0, 0.0)

        utm_stub.from_latlon = _utm_from_latlon
        utm_stub.to_latlon = _utm_to_latlon
        sys.modules["utm"] = utm_stub

    if "deprecated" not in sys.modules:
        deprecated_stub = ModuleType("deprecated")

        def _deprecated(_reason: Any | None = None, **_kwargs: Any):
            def decorator(func: Any) -> Any:
                return func

            return decorator

        deprecated_stub.deprecated = _deprecated
        sys.modules["deprecated"] = deprecated_stub

    if "wepppy.all_your_base.geo" not in sys.modules:
        geo_stub = ModuleType("wepppy.all_your_base.geo")

        class _RasterDatasetInterpolator:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.args = args
                self.kwargs = kwargs

        class _GeoTransformer:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.args = args
                self.kwargs = kwargs

        class _RDIOutOfBoundsException(Exception):
            pass

        def _geo_noop(*args: Any, **kwargs: Any) -> Any:
            return None

        geo_stub.RasterDatasetInterpolator = _RasterDatasetInterpolator
        geo_stub.GeoTransformer = _GeoTransformer
        geo_stub.RDIOutOfBoundsException = _RDIOutOfBoundsException
        geo_stub.read_raster = _geo_noop
        geo_stub.raster_stacker = _geo_noop
        geo_stub.validate_srs = _geo_noop
        geo_stub.wgs84_proj4 = "EPSG:4326"
        geo_stub.utm_srid = _geo_noop
        geo_stub.haversine = lambda *args, **kwargs: 0.0  # type: ignore[assignment]
        geo_stub.get_utm_zone = lambda *args, **kwargs: 12  # type: ignore[assignment]
        geo_stub.utm_raster_transform = _geo_noop

        def _geo_getattr(name: str) -> Any:
            return _geo_noop

        geo_stub.__getattr__ = _geo_getattr  # type: ignore[attr-defined]
        sys.modules["wepppy.all_your_base.geo"] = geo_stub

    if "wepppy.all_your_base.geo.webclients" not in sys.modules:
        webclients_stub = ModuleType("wepppy.all_your_base.geo.webclients")

        def _webclient_stub(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return {}

        webclients_stub.wmesque_retrieve = _webclient_stub
        sys.modules["wepppy.all_your_base.geo.webclients"] = webclients_stub

    import wepppy  # noqa: WPS433

    nodb_pkg = _ensure_package_module("wepppy.nodb")
    setattr(wepppy, "nodb", nodb_pkg)
    core_pkg = _ensure_package_module("wepppy.nodb.core")
    mods_pkg = _ensure_package_module("wepppy.nodb.mods")
    nodb_pkg.core = core_pkg  # type: ignore[attr-defined]
    nodb_pkg.mods = mods_pkg  # type: ignore[attr-defined]

    if "wepppy.nodb.base" not in sys.modules:
        nodb_base_stub = ModuleType("wepppy.nodb.base")

        def _clear_locks(*args: Any, **kwargs: Any) -> list[str]:
            return []

        def _get_config_dir() -> str:
            return "/tmp"

        def _get_default_config_path() -> str:
            return "/tmp/_defaults.toml"

        nodb_base_stub.clear_locks = _clear_locks  # type: ignore[attr-defined]
        nodb_base_stub.get_config_dir = _get_config_dir  # type: ignore[attr-defined]
        nodb_base_stub.get_default_config_path = _get_default_config_path  # type: ignore[attr-defined]
        sys.modules["wepppy.nodb.base"] = nodb_base_stub
        nodb_pkg.base = nodb_base_stub  # type: ignore[attr-defined]

    if "wepppy.nodb.core.ron" not in sys.modules:
        ron_stub = ModuleType("wepppy.nodb.core.ron")

        class _Ron:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            @classmethod
            def getInstance(cls, *args: Any, **kwargs: Any) -> "_Ron":
                return cls()

        ron_stub.Ron = _Ron  # type: ignore[attr-defined]
        sys.modules["wepppy.nodb.core.ron"] = ron_stub
        core_pkg.ron = ron_stub  # type: ignore[attr-defined]


def ensure_profile_test_stubs() -> None:
    global _STUBS_READY
    if _STUBS_READY:
        return
    _install_stubs()
    _STUBS_READY = True


def load_profile_module(relative_path: str, module_name: str, *, package: str | None = None) -> ModuleType:
    ensure_profile_test_stubs()
    path = _PROJECT_ROOT / "wepppy" / "profile_recorder" / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    if package:
        module.__package__ = package
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module
