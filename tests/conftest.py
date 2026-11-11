import importlib
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.factories.fixtures import rq_environment, rq_recorder  # noqa: F401


# Preserve only source metadata; real-Redis tests explicitly opt in below.
_RUNTIME_REDIS_PASSWORD_FILE = os.environ.get("REDIS_PASSWORD_FILE")

def pytest_configure(config) -> None:
    """Register custom markers used across the suite."""
    config.addinivalue_line("markers", "unit: Fast, isolated unit tests")
    config.addinivalue_line("markers", "integration: Cross-module integration tests")
    config.addinivalue_line("markers", "microservice: Exercises external microservices")
    config.addinivalue_line("markers", "routes: Flask/HTTP route tests")
    config.addinivalue_line("markers", "nodb: NoDb controller and locking tests")
    config.addinivalue_line("markers", "slow: Tests with timing dependencies (>2s)")
    config.addinivalue_line("markers", "requires_network: Tests that reach external services")
    config.addinivalue_line(
        "markers", "requires_docker: Tests that require Docker or Docker Compose tooling"
    )


@pytest.fixture(autouse=True)
def _clear_secret_file_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate host secrets and deployment catalog modes from test configuration."""

    for key in (
        "WEPPPY_PROJECT_COMMIT_MODE",
        "WEPPCLOUD_RUN_CATALOG_WRITE_MODE",
        "WEPPCLOUD_RUN_CATALOG_READ_MODE",
        "WEPPCLOUD_RUN_CATALOG_SWEEP_ENABLED",
        "ADMIN_PASSWORD_FILE",
        "AGENT_JWT_SECRET_FILE",
        "CAP_SECRET_FILE",
        "CLIMATE_ENGINE_API_KEY_FILE",
        "DTALE_INTERNAL_TOKEN_FILE",
        "OAUTH_GITHUB_CLIENT_SECRET_FILE",
        "OAUTH_GOOGLE_CLIENT_SECRET_FILE",
        "OAUTH_ORCID_CLIENT_SECRET_FILE",
        "OPENET_API_KEY_FILE",
        "OPENTOPOGRAPHY_API_KEY_FILE",
        "POSTGRES_PASSWORD_FILE",
        "REDIS_PASSWORD_FILE",
        "SECRET_KEY_FILE",
        "SECURITY_PASSWORD_SALT_FILE",
        "WC_TOKEN_FILE",
        "WEPP_AUTH_JWT_SECRET_FILE",
        "WEPP_AUTH_JWT_SECRETS_FILE",
        "WEPP_MCP_JWT_SECRET_FILE",
        "ZOHO_NOREPLY_EMAIL_PASSWORD_FILE",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def runtime_redis_credentials(monkeypatch: pytest.MonkeyPatch, _clear_secret_file_env: None) -> None:
    """Restore the configured credential source only for explicit real-Redis tests."""
    if _RUNTIME_REDIS_PASSWORD_FILE:
        monkeypatch.setenv("REDIS_PASSWORD_FILE", _RUNTIME_REDIS_PASSWORD_FILE)


@pytest.fixture(scope="session")
def _test_required_secret_files(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Create deterministic secret files for tests that import WEPPcloud config."""

    root = tmp_path_factory.mktemp("secrets")
    secret_key_path = root / "flask_secret_key"
    salt_path = root / "flask_security_password_salt"

    secret_key_path.write_text("pytest-secret-key\n", encoding="utf-8")
    salt_path.write_text("pytest-security-password-salt\n", encoding="utf-8")

    return {
        "SECRET_KEY_FILE": secret_key_path,
        "SECURITY_PASSWORD_SALT_FILE": salt_path,
    }


@pytest.fixture(autouse=True)
def _install_test_required_secrets(
    monkeypatch: pytest.MonkeyPatch,
    _clear_secret_file_env: None,
    _test_required_secret_files: dict[str, Path],
) -> None:
    """Ensure required runtime secrets exist even when host env files are scrubbed."""

    for key, path in _test_required_secret_files.items():
        monkeypatch.setenv(key, str(path))

    # RQ-engine routes call into auth_tokens.get_jwt_config() for scope parsing.
    # Provide a deterministic dummy secret, and let tests that need the
    # misconfiguration path `delenv()` it explicitly.
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "pytest-jwt-secret")


@pytest.fixture(scope="session", autouse=True)
def _ensure_all_your_base() -> None:
    module = importlib.import_module("wepppy.all_your_base")
    sys.modules["wepppy.all_your_base"] = module


@pytest.fixture(scope="session", autouse=True)
def _install_redis_stub():
    try:
        redis_module = importlib.import_module("redis")
    except Exception:  # pragma: no cover - redis may be unavailable
        redis_module = None  # type: ignore[assignment]

    if not redis_module:
        yield
        return

    original_cls: Any = getattr(redis_module, "Redis", None)

    class RecordingRedis:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = dict(kwargs)
            self.store = {}
            self.hashes = {}
            self.published = []

        def set(self, key, value, *args, **kwargs):
            self.store[key] = value
            return True

        def get(self, key):
            return self.store.get(key)

        def exists(self, key):
            return int(key in self.store)

        def delete(self, key):
            self.store.pop(key, None)

        def hset(self, name, key=None, value=None, mapping=None):
            bucket = self.hashes.setdefault(name, {})
            fields = dict(mapping or {})
            if key is not None:
                fields[key] = value
            bucket.update(fields)
            return len(fields)

        def hget(self, name, key):
            return self.hashes.get(name, {}).get(key)

        def hgetall(self, name):
            return dict(self.hashes.get(name, {}))

        def hdel(self, name, *keys):
            bucket = self.hashes.get(name, {})
            removed = 0
            for key in keys:
                if key in bucket:
                    del bucket[key]
                    removed += 1
            return removed

        def pipeline(self):
            # Recording-only transaction surface. Concurrency proofs use real Redis.
            client = self
            class RecordingPipeline:
                def __init__(self):
                    self.commands = []
                    self.watching = False
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
                def watch(self, *keys):
                    self.watching = True
                def multi(self):
                    self.watching = False
                def hgetall(self, key):
                    return client.hgetall(key)
                def hset(self, *args, **kwargs):
                    self.commands.append(('hset', args, kwargs))
                    return self
                def hdel(self, *args, **kwargs):
                    self.commands.append(('hdel', args, kwargs))
                    return self
                def execute(self):
                    result = [getattr(client, method)(*args, **kwargs)
                              for method, args, kwargs in self.commands]
                    self.commands.clear()
                    return result
            return RecordingPipeline()

        def publish(self, channel, message):
            self.published.append((channel, message))
            return 1

        def lock(self, name, **kwargs):
            class RecordingLock:
                def acquire(self, **acquire_kwargs):
                    return True

                def extend(self, additional_time, **extend_kwargs):
                    return True

                def release(self):
                    return None

            return RecordingLock()

        def close(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    redis_module.Redis = RecordingRedis
    # Request middleware/auth capture constructors during collection, before
    # this session fixture runs. Stub those aliases too so auth tests cannot
    # accidentally contact deployment Redis based on import order.
    captured_clients = []
    for module_name, attribute in (
        ("wepppy.microservices.rq_engine", "_LIFECYCLE_REDIS_CLIENT"),
        ("wepppy.microservices.rq_engine.auth", "_AUTH_REDIS_CLIENT"),
    ):
        module = sys.modules.get(module_name)
        if module is not None and hasattr(module, attribute):
            captured_clients.append((module, attribute, getattr(module, attribute)))
            setattr(module, attribute, RecordingRedis)

    try:
        redis_settings = importlib.import_module("wepppy.config.redis_settings")
        if getattr(redis_settings, "redis", None):
            redis_settings.redis.Redis = RecordingRedis  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - import safety
        pass

    yield

    for module, attribute, original in captured_clients:
        setattr(module, attribute, original)

    if original_cls is not None:
        redis_module.Redis = original_cls
        try:
            redis_settings = importlib.import_module("wepppy.config.redis_settings")
            if getattr(redis_settings, "redis", None):
                redis_settings.redis.Redis = original_cls  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - import safety
            pass


@pytest.fixture(scope="session", autouse=True)
def _import_nodb_base() -> None:
    try:
        base_module = importlib.import_module("wepppy.nodb.base")
        nodb_pkg = importlib.import_module("wepppy.nodb")
        root_pkg = importlib.import_module("wepppy")
        setattr(root_pkg, "nodb", nodb_pkg)
        setattr(nodb_pkg, "base", base_module)
    except Exception:
        pass

    try:
        profile_pkg = importlib.import_module("wepppy.profile_recorder")
        root_pkg = importlib.import_module("wepppy")
        setattr(root_pkg, "profile_recorder", profile_pkg)
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def _ensure_wepppy_namespace() -> None:
    """Ensure key subpackages are attached to the root wepppy module."""
    root_pkg = importlib.import_module("wepppy")
    for name in ("locales", "weppcloud", "rq"):
        try:
            submod = importlib.import_module(f"wepppy.{name}")
            setattr(root_pkg, name, submod)
        except Exception:
            continue
