from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path

import pytest

from wepppy.climates.cligen import binary_provenance
from wepppy.climates.cligen.binary_provenance import (
    CligenProvenanceError,
    collect_cligen_binary_identity,
    write_cligen_binary_identity,
)
import wepppy.climates.cligen.cligen as cligen_module
import wepppy.climates.cligen.single_storm as single_storm_module
from tools import vendor_cligen_release


pytestmark = pytest.mark.unit


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_release_pair(
    directory: Path,
    *,
    binary_bytes: bytes = b"#!/bin/sh\necho child-output\n",
    binary_name: str = "cligen532",
    dirty: bool = False,
    role: str = "optimized",
) -> tuple[Path, Path]:
    binary = directory / binary_name
    binary.write_bytes(binary_bytes)
    binary.chmod(0o755)
    manifest = [
        {
            "path": "cligen532/cligen.f",
            "sha256": "a" * 64,
            "size_bytes": 1,
        }
    ]
    manifest_digest = _sha256(
        json.dumps(
            manifest,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    sidecar = Path(f"{binary}.json")
    sidecar.write_text(
        json.dumps(
            {
                "schema": "cligen-binary-provenance-v1",
                "release_label": "test-release",
                "binary": {
                    "name": binary_name,
                    "role": role,
                    "sha256": _sha256(binary_bytes),
                    "size_bytes": len(binary_bytes),
                    "cligen_version": "5.32300",
                },
                "source": {
                    "commit": "b" * 40,
                    "git_tree": "c" * 40,
                    "dirty": dirty,
                    "dirty_entries": [],
                    "manifest_sha256": manifest_digest,
                    "files": manifest,
                },
                "build": {},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return binary, sidecar


def test_collect_verified_identity_and_write_stable_log(tmp_path):
    binary, sidecar = _write_release_pair(tmp_path)
    log = io.StringIO()

    identity = write_cligen_binary_identity(
        log, runner="unit_runner", binary_path=binary
    )

    assert identity.binary_identity_status == "verified"
    assert identity.binary_sha256 == _sha256(binary.read_bytes())
    assert identity.sidecar_sha256 == _sha256(sidecar.read_bytes())
    assert identity.cligen_version == "5.32300"
    assert identity.release_label == "test-release"
    assert identity.source_commit == "b" * 40
    line = log.getvalue()
    assert line.startswith("[unit_runner] binary_identity ")
    assert "binary_identity_status=verified" in line
    assert 'cligen_version="5.32300"' in line
    assert f"sidecar_sha256={identity.sidecar_sha256}" in line


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing", "required sidecar is missing"),
        ("binary", "binary SHA-256 mismatch"),
        ("dirty", "source.dirty must be false"),
        ("role", "binary.role must be optimized"),
        ("manifest", "source manifest SHA-256 mismatch"),
    ],
)
def test_strict_identity_rejects_invalid_release_states(tmp_path, mutation, message):
    binary, sidecar = _write_release_pair(tmp_path)
    if mutation == "missing":
        sidecar.unlink()
    elif mutation == "binary":
        binary.write_bytes(binary.read_bytes() + b"tampered")
    else:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        if mutation == "dirty":
            payload["source"]["dirty"] = True
        elif mutation == "role":
            payload["binary"]["role"] = "backtrace"
        elif mutation == "manifest":
            payload["source"]["files"][0]["size_bytes"] = 2
        sidecar.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CligenProvenanceError, match=message):
        collect_cligen_binary_identity(binary)


def test_legacy_binary_without_sidecar_is_explicitly_unverified(tmp_path):
    binary = tmp_path / "cligen53"
    binary.write_bytes(b"legacy")

    identity = collect_cligen_binary_identity(binary)

    assert identity.binary_identity_status == "legacy_unverified"
    assert identity.binary_sha256 == _sha256(b"legacy")
    assert identity.sidecar_path == ""
    assert identity.cligen_version == "unknown"


def test_legacy_binary_ignores_unsupported_adjacent_sidecar(tmp_path):
    binary = tmp_path / "cligen53"
    binary.write_bytes(b"legacy")
    Path(f"{binary}.json").write_text("not-json", encoding="utf-8")

    identity = collect_cligen_binary_identity(binary)

    assert identity.binary_identity_status == "legacy_unverified"


def test_strict_identity_rejects_malformed_sidecar(tmp_path):
    binary, sidecar = _write_release_pair(tmp_path)
    sidecar.write_text("not-json", encoding="utf-8")

    with pytest.raises(CligenProvenanceError, match="Cannot read CLIGEN sidecar"):
        collect_cligen_binary_identity(binary)


def test_identity_rehashes_binary_after_in_place_change(tmp_path):
    binary, sidecar = _write_release_pair(tmp_path)
    first = collect_cligen_binary_identity(binary)
    replacement_bytes = b"replacement binary"
    binary.write_bytes(replacement_bytes)
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    payload["binary"]["sha256"] = _sha256(replacement_bytes)
    payload["binary"]["size_bytes"] = len(replacement_bytes)
    sidecar.write_text(json.dumps(payload), encoding="utf-8")

    second = collect_cligen_binary_identity(binary)

    assert first.binary_sha256 != second.binary_sha256
    assert second.binary_sha256 == _sha256(replacement_bytes)


def test_run_cligen_posix_logs_verified_identity_before_child_output(tmp_path):
    binary, _ = _write_release_pair(tmp_path)
    clinp = tmp_path / "cligen.inp"
    clinp.write_text("", encoding="ascii")
    log = io.StringIO()

    stdout, stderr = cligen_module._run_cligen_posix(
        [str(binary)], str(clinp), timeout_sec=2, log_fp=log
    )

    assert stdout.strip() == "child-output"
    assert stderr == ""
    text = log.getvalue()
    assert text.index("binary_identity_status=verified") < text.index("CLIGEN OK")


def test_run_cligen_posix_does_not_start_child_when_sidecar_is_missing(
    tmp_path, monkeypatch
):
    binary, sidecar = _write_release_pair(tmp_path)
    sidecar.unlink()
    clinp = tmp_path / "cligen.inp"
    clinp.write_text("", encoding="ascii")
    popen_calls = []
    monkeypatch.setattr(
        cligen_module,
        "Popen",
        lambda *_args, **_kwargs: popen_calls.append((_args, _kwargs)),
    )

    with pytest.raises(CligenProvenanceError, match="required sidecar is missing"):
        cligen_module._run_cligen_posix(
            [str(binary)], str(clinp), timeout_sec=2, log_fp=io.StringIO()
        )

    assert popen_calls == []


def test_single_storm_launcher_logs_verified_identity(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_release_pair(bin_dir)
    clinp = tmp_path / "storm.inp"
    clinp.write_text("input\n", encoding="ascii")
    monkeypatch.setattr(single_storm_module, "_bin_dir", str(bin_dir))
    monkeypatch.setattr(
        single_storm_module.subprocess,
        "run",
        lambda *_args, **_kwargs: None,
    )

    single_storm_module._run_cligen(
        tmpdir=tmp_path,
        cliver="5.3.2",
        par_fn="station.par",
        clinp_path=clinp,
        timeout=2,
        randseed=99999,
    )

    log_text = (tmp_path / "cligen.log").read_text(encoding="utf-8")
    assert "[single_storm] binary_identity" in log_text
    assert "binary_identity_status=verified" in log_text
    assert "cmd:" in log_text
    assert "-r99999" in log_text


def test_install_release_pair_replaces_both_files_with_validated_pair(tmp_path):
    source_dir = tmp_path / "source"
    destination_dir = tmp_path / "destination"
    source_dir.mkdir()
    destination_dir.mkdir()
    source_binary, source_sidecar = _write_release_pair(source_dir)
    destination = destination_dir / "cligen532"
    destination.write_bytes(b"old binary")

    identity = vendor_cligen_release.install_release_pair(
        source_binary=source_binary,
        destination=destination,
    )

    assert identity.binary_identity_status == "verified"
    assert destination.read_bytes() == source_binary.read_bytes()
    assert Path(f"{destination}.json").read_bytes() == source_sidecar.read_bytes()
    assert destination.stat().st_mode & 0o777 == 0o755
    assert Path(f"{destination}.json").stat().st_mode & 0o777 == 0o644


def test_install_release_pair_rolls_back_both_files_on_second_replace_failure(
    tmp_path, monkeypatch
):
    source_dir = tmp_path / "source"
    destination_dir = tmp_path / "destination"
    source_dir.mkdir()
    destination_dir.mkdir()
    source_binary, _ = _write_release_pair(source_dir, binary_bytes=b"new binary")
    destination, destination_sidecar = _write_release_pair(
        destination_dir, binary_bytes=b"old binary"
    )
    old_binary = destination.read_bytes()
    old_sidecar = destination_sidecar.read_bytes()
    real_replace = vendor_cligen_release.os.replace
    failed = False

    def fail_once(source, target):
        nonlocal failed
        if Path(target) == destination and not failed:
            failed = True
            raise OSError("simulated binary replacement failure")
        return real_replace(source, target)

    monkeypatch.setattr(vendor_cligen_release.os, "replace", fail_once)

    with pytest.raises(OSError, match="simulated binary replacement failure"):
        vendor_cligen_release.install_release_pair(
            source_binary=source_binary,
            destination=destination,
        )

    assert destination.read_bytes() == old_binary
    assert destination_sidecar.read_bytes() == old_sidecar
    assert collect_cligen_binary_identity(destination).binary_identity_status == "verified"


def test_manifest_paths_reject_parent_traversal(tmp_path):
    binary, sidecar = _write_release_pair(tmp_path)
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    payload["source"]["files"][0]["path"] = "../cligen.f"
    manifest = payload["source"]["files"]
    payload["source"]["manifest_sha256"] = _sha256(
        json.dumps(
            manifest,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    sidecar.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CligenProvenanceError, match="traversal-free"):
        collect_cligen_binary_identity(binary)


def test_format_escapes_runner_control_characters(tmp_path):
    binary, _ = _write_release_pair(tmp_path)
    identity = collect_cligen_binary_identity(binary)

    line = binary_provenance.format_cligen_binary_identity(
        runner='bad"runner\nnext', identity=identity
    )

    assert "\n" not in line
    assert "\\n" in line
