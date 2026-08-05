from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile

import pytest

from wepppy.project_config_sanitization import (
    ConfigMaterializationError,
    assert_materialization_safe,
    scan_archive,
    scan_config_text,
    scan_manifest_text,
    scan_path,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("key", ["api_key", "redis_password", "access-token", "client_secret"])
def test_config_scan_rejects_secret_option_names_without_echoing_values(key: str) -> None:
    secret = "do-not-echo-this-value"
    violations = scan_config_text(f"[general]\n{key} = {secret}\n")

    assert [item.rule for item in violations] == ["secret-bearing option name"]
    assert secret not in violations[0].describe()


@pytest.mark.parametrize(
    ("key", "value", "rule"),
    [
        ("redis_host", "redis", "runtime-host-bound option name"),
        ("ordinary", "${LIVE_SECRET}", "environment-variable reference"),
        ("ordinary", "/run/secrets/service_token", "runtime secret-file path"),
        ("ordinary", "https://user:pass@example.test/data", "credential-bearing URI"),
    ],
)
def test_config_scan_rejects_runtime_bound_forms(key: str, value: str, rule: str) -> None:
    assert rule in {item.rule for item in scan_config_text(f"[general]\n{key} = {value}\n")}


def test_safe_runtime_configuration_passes() -> None:
    config = "[general]\ndem_db = ned1/2024\nlocales = [us]\n\n[watershed]\ncsa = 10\n"
    manifest = json.dumps({"schema_version": 1, "config": {"filename": "config.cfg", "sha256": "abc"}})

    assert_materialization_safe(config, manifest)


def test_manifest_scan_is_recursive_and_redacted() -> None:
    secret = "manifest-secret-value"
    violations = scan_manifest_text(json.dumps({"selections": {"api_token": secret}}))

    assert [item.rule for item in violations] == ["secret-bearing option name"]
    assert secret not in violations[0].describe()


def test_assertion_fails_before_materialization() -> None:
    with pytest.raises(ConfigMaterializationError, match="secret-bearing option name"):
        assert_materialization_safe("[general]\napi_key = unsafe\n")


def test_directory_scans_shared_and_legacy_sources(tmp_path: Path) -> None:
    (tmp_path / "legacy").mkdir()
    (tmp_path / "safe.cfg").write_text("[general]\ncellsize = 30\n", encoding="utf-8")
    (tmp_path / "legacy" / "unsafe.toml").write_text("[general]\npassword = stale\n", encoding="utf-8")

    violations = scan_path(tmp_path)

    assert len(violations) == 1
    assert violations[0].key == "password"


def test_tracked_shared_configuration_corpus_is_sanitized() -> None:
    assert scan_path(REPO_ROOT / "wepppy" / "nodb" / "configs") == ()


def test_cli_fails_redacted_for_unsafe_artifact(tmp_path: Path) -> None:
    secret = "cli-must-not-echo-this"
    config_path = tmp_path / "config.cfg"
    config_path.write_text(f"[general]\napi_key = {secret}\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "check_project_config_secrets.py"), str(config_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "secret-bearing option name" in result.stdout
    assert secret not in result.stdout


@pytest.mark.parametrize("archive_kind", ["zip", "tar"])
def test_archive_scan_rejects_secret_bearing_project_config(tmp_path: Path, archive_kind: str) -> None:
    payload = b"[general]\napi_key = archived\n"
    archive_path = tmp_path / f"run.{archive_kind}"
    if archive_kind == "zip":
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("run/config.cfg", payload)
    else:
        with tarfile.open(archive_path, "w") as archive:
            info = tarfile.TarInfo("run/config.cfg")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))

    violations = scan_archive(archive_path)

    assert len(violations) == 1
    assert violations[0].rule == "secret-bearing option name"
