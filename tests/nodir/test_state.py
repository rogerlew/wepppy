from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.nodir.state import (
    archive_fingerprint_from_path,
    is_transitioning_locked,
    read_state,
    state_path,
    thaw_temp_path,
    validate_state_payload,
    write_state,
)

pytestmark = pytest.mark.unit

_OP_UUID = "00000000-0000-4000-8000-000000000001"


def _valid_payload() -> dict:
    return {
        "schema_version": 1,
        "root": "watershed",
        "state": "archived",
        "op_id": _OP_UUID,
        "host": "node-a",
        "pid": 99,
        "lock_owner": "node-a:99",
        "dir_path": "watershed",
        "archive_path": "watershed.nodir",
        "dirty": False,
        "archive_fingerprint": {"mtime_ns": 1, "size_bytes": 2},
        "updated_at": "2026-02-16T00:00:00Z",
    }


def test_write_state_round_trip_contains_required_fields(tmp_path: Path) -> None:
    wd = tmp_path
    archive = wd / "watershed.nodir"
    archive.write_bytes(b"archive-bytes")
    fp = archive_fingerprint_from_path(archive)

    payload = write_state(
        wd,
        "watershed",
        state="thawed",
        op_id=_OP_UUID,
        dirty=True,
        archive_fingerprint=fp,
    )

    persisted = read_state(wd, "watershed")
    assert persisted is not None
    assert persisted == payload

    required = {
        "schema_version",
        "root",
        "state",
        "op_id",
        "host",
        "pid",
        "lock_owner",
        "dir_path",
        "archive_path",
        "dirty",
        "archive_fingerprint",
        "updated_at",
    }
    assert required.issubset(payload.keys())


def test_validate_state_payload_rejects_invalid_lock_owner() -> None:
    payload = _valid_payload()
    payload["lock_owner"] = "node-b:99"

    with pytest.raises(ValueError, match="lock_owner"):
        validate_state_payload(payload, root="watershed")


def test_validate_state_payload_rejects_non_uuid4_op_id() -> None:
    payload = _valid_payload()
    payload["op_id"] = "not-a-uuid"

    with pytest.raises(ValueError, match="UUID4"):
        validate_state_payload(payload, root="watershed")


@pytest.mark.parametrize(
    ("field", "value", "expected_match"),
    [
        ("schema_version", True, "schema_version"),
        ("pid", False, "pid"),
        ("archive_fingerprint", {"mtime_ns": True, "size_bytes": 1}, "mtime_ns"),
        ("archive_fingerprint", {"mtime_ns": 1, "size_bytes": False}, "size_bytes"),
    ],
)
def test_validate_state_payload_rejects_bool_integer_fields(
    field: str,
    value: object,
    expected_match: str,
) -> None:
    payload = _valid_payload()
    payload[field] = value

    with pytest.raises(ValueError, match=expected_match):
        validate_state_payload(payload, root="watershed")


def test_write_state_uses_atomic_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import wepppy.nodir.state as state_mod

    wd = tmp_path
    archive = wd / "watershed.nodir"
    archive.write_bytes(b"archive")
    fp = archive_fingerprint_from_path(archive)

    replace_calls: list[tuple[Path, Path]] = []
    real_replace = state_mod.os.replace

    def _record_replace(src: str | Path, dst: str | Path) -> None:
        replace_calls.append((Path(src), Path(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(state_mod.os, "replace", _record_replace)

    write_state(
        wd,
        "watershed",
        state="archived",
        op_id="00000000-0000-4000-8000-000000000002",
        dirty=False,
        archive_fingerprint=fp,
    )

    assert len(replace_calls) == 1
    src, dst = replace_calls[0]
    assert dst == state_path(wd, "watershed")
    assert src != dst
    assert src.name.startswith("watershed.json.tmp.")
    assert not src.exists()


def test_write_state_rejects_bool_pid(tmp_path: Path) -> None:
    wd = tmp_path
    archive = wd / "watershed.nodir"
    archive.write_bytes(b"archive")

    with pytest.raises(ValueError, match="pid"):
        write_state(
            wd,
            "watershed",
            state="archived",
            op_id="00000000-0000-4000-8000-000000000004",
            dirty=False,
            pid=True,
            archive_fingerprint=archive_fingerprint_from_path(archive),
        )


def test_missing_state_with_temp_sentinel_is_locked(tmp_path: Path) -> None:
    wd = tmp_path
    thaw_tmp_path = thaw_temp_path(wd, "watershed")
    thaw_tmp_path.mkdir(parents=True, exist_ok=False)

    assert not state_path(wd, "watershed").exists()
    assert is_transitioning_locked(wd, "watershed") is True
