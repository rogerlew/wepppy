from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.config.secrets import get_secret, require_secret

pytestmark = pytest.mark.unit


def test_get_secret_prefers_file_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    secret_path = tmp_path / "secret"
    secret_path.write_text("file-secret\n", encoding="utf-8")

    monkeypatch.setenv("UNIT_TEST_SECRET", "env-secret")
    monkeypatch.setenv("UNIT_TEST_SECRET_FILE", str(secret_path))

    assert get_secret("UNIT_TEST_SECRET") == "file-secret"


def test_get_secret_falls_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UNIT_TEST_SECRET", "  env-secret  ")
    monkeypatch.delenv("UNIT_TEST_SECRET_FILE", raising=False)

    assert get_secret("UNIT_TEST_SECRET") == "env-secret"


def test_get_secret_missing_file_raises_and_does_not_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing_path = tmp_path / "missing"
    monkeypatch.setenv("UNIT_TEST_SECRET", "env-secret")
    monkeypatch.setenv("UNIT_TEST_SECRET_FILE", str(missing_path))

    with pytest.raises(RuntimeError, match=r"Unable to read UNIT_TEST_SECRET_FILE"):
        get_secret("UNIT_TEST_SECRET")


def test_get_secret_empty_file_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    secret_path = tmp_path / "secret"
    secret_path.write_text("\n", encoding="utf-8")
    monkeypatch.setenv("UNIT_TEST_SECRET_FILE", str(secret_path))
    monkeypatch.delenv("UNIT_TEST_SECRET", raising=False)

    with pytest.raises(RuntimeError, match=r"UNIT_TEST_SECRET_FILE .* is empty"):
        get_secret("UNIT_TEST_SECRET")


def test_require_secret_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UNIT_TEST_SECRET", raising=False)
    monkeypatch.delenv("UNIT_TEST_SECRET_FILE", raising=False)

    with pytest.raises(RuntimeError, match=r"UNIT_TEST_SECRET .* must be configured"):
        require_secret("UNIT_TEST_SECRET")


def test_malformed_secret_encoding_has_safe_configuration_message(monkeypatch, tmp_path):
    from wepppy.config.secrets import SecretConfigurationError
    secret = tmp_path / 'private-location'
    secret.write_bytes(b'\xff')
    monkeypatch.setenv('UNIT_TEST_SECRET_FILE', str(secret))
    with pytest.raises(SecretConfigurationError) as failure:
        get_secret('UNIT_TEST_SECRET')
    assert 'UNIT_TEST_SECRET_FILE could not be read' in failure.value.public_message
    assert str(secret) not in failure.value.public_message


def test_secret_error_survives_process_exception_serialization(monkeypatch, tmp_path):
    import pickle
    from wepppy.config.secrets import SecretConfigurationError
    private_path = tmp_path / 'private-secret-location'
    monkeypatch.setenv('UNIT_TEST_SECRET_FILE', str(private_path))
    with pytest.raises(SecretConfigurationError) as failure:
        get_secret('UNIT_TEST_SECRET')
    restored = pickle.loads(pickle.dumps(failure.value))
    assert type(restored) is SecretConfigurationError
    assert restored.args == failure.value.args
    assert restored.public_message == failure.value.public_message
    assert str(private_path) not in restored.public_message
