from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _required_nfs_root() -> Path:
    raw_root = os.environ.get("WEPPPY_NFS_TEST_ROOT")
    if not raw_root:
        pytest.skip("WEPPPY_NFS_TEST_ROOT is required for explicit NFS parity")
    root = Path(raw_root)
    root.mkdir(parents=True, exist_ok=True)
    filesystem = subprocess.check_output(
        ["findmnt", "-n", "-T", str(root), "-o", "FSTYPE"],
        text=True,
    ).strip()
    if not filesystem.startswith("nfs"):
        pytest.fail(f"NFS parity root is not NFS-backed: {root} ({filesystem})")
    return root


def test_omni_quarantine_capture_restore_and_collision_on_nfs() -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    nfs_root = _required_nfs_root()
    workspace = Path(tempfile.mkdtemp(prefix="surf04a-", dir=nfs_root))
    action_dir = workspace / "action"
    quarantine_dir = workspace / "quarantine"
    action_dir.mkdir()
    quarantine_dir.mkdir(mode=0o700)
    action_fd = os.open(action_dir, os.O_RDONLY | os.O_DIRECTORY)
    quarantine_fd = os.open(quarantine_dir, os.O_RDONLY | os.O_DIRECTORY)
    try:
        raw_target = "/wc1/runs/deleted-ancestor/wepp/runs/p1.cli"
        os.symlink(raw_target, "p1.cli", dir_fd=action_fd)
        original = os.stat("p1.cli", dir_fd=action_fd, follow_symlinks=False)

        fork_helpers._capture_to_quarantine(
            action_fd, "p1.cli", quarantine_fd, "captured"
        )
        with pytest.raises(FileNotFoundError):
            os.stat("p1.cli", dir_fd=action_fd, follow_symlinks=False)
        captured = os.stat("captured", dir_fd=quarantine_fd, follow_symlinks=False)
        assert (captured.st_dev, captured.st_ino) == (original.st_dev, original.st_ino)
        assert os.readlink("captured", dir_fd=quarantine_fd) == raw_target

        fork_helpers._restore_quarantined_link(
            quarantine_fd,
            "captured",
            action_fd,
            "p1.cli",
            expected_device=original.st_dev,
            expected_inode=original.st_ino,
            expected_link=raw_target,
        )
        restored = os.stat("p1.cli", dir_fd=action_fd, follow_symlinks=False)
        assert (restored.st_dev, restored.st_ino) == (original.st_dev, original.st_ino)
        assert os.readlink("p1.cli", dir_fd=action_fd) == raw_target
        with pytest.raises(FileNotFoundError):
            os.stat("captured", dir_fd=quarantine_fd, follow_symlinks=False)

        fork_helpers._capture_to_quarantine(
            action_fd, "p1.cli", quarantine_fd, "collision-source"
        )
        foreign_bytes = b"do not overwrite"
        (action_dir / "p1.cli").write_bytes(foreign_bytes)
        with pytest.raises(FileExistsError):
            fork_helpers._restore_quarantined_link(
                quarantine_fd,
                "collision-source",
                action_fd,
                "p1.cli",
                expected_device=original.st_dev,
                expected_inode=original.st_ino,
                expected_link=raw_target,
            )
        assert (action_dir / "p1.cli").read_bytes() == foreign_bytes
        assert os.readlink("collision-source", dir_fd=quarantine_fd) == raw_target
    finally:
        os.close(quarantine_fd)
        os.close(action_fd)
        shutil.rmtree(workspace)


@pytest.mark.parametrize("replacement_type", ["regular", "directory"])
def test_omni_pre_capture_leaf_swaps_on_nfs(
    monkeypatch: pytest.MonkeyPatch,
    replacement_type: str,
) -> None:
    import wepppy.rq.project_rq_fork as fork_helpers

    nfs_root = _required_nfs_root()
    workspace = Path(tempfile.mkdtemp(prefix="surf04a-", dir=nfs_root))
    destination = workspace / "destination"
    contrast_runs = destination / "_pups" / "omni" / "contrasts" / "1" / "wepp" / "runs"
    contrast_runs.mkdir(parents=True)
    candidate = contrast_runs / "p1.cli"
    candidate.symlink_to("/wc1/runs/deleted-ancestor/wepp/runs/p1.cli")
    original_capture = fork_helpers._capture_to_quarantine
    raced = False

    def _swap_before_capture(
        source_fd: int, src: str, destination_fd: int, dst: str
    ) -> None:
        nonlocal raced
        if src == "p1.cli" and not raced:
            raced = True
            os.unlink(src, dir_fd=source_fd)
            if replacement_type == "regular":
                fd = os.open(
                    src,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=source_fd,
                )
                try:
                    os.write(fd, b"foreign regular bytes")
                finally:
                    os.close(fd)
            else:
                os.mkdir(src, dir_fd=source_fd)
        original_capture(source_fd, src, destination_fd, dst)

    monkeypatch.setattr(fork_helpers, "_capture_to_quarantine", _swap_before_capture)
    try:
        if replacement_type == "regular":
            with pytest.raises(RuntimeError, match="changed before quarantine"):
                fork_helpers._normalize_fork_omni_links(
                    str(destination), skip_wepp_runs_output=True
                )
            assert candidate.read_bytes() == b"foreign regular bytes"
            assert not list(destination.glob(".fork-omni-quarantine-*"))
        else:
            with pytest.raises(RuntimeError, match="rollback failed"):
                fork_helpers._normalize_fork_omni_links(
                    str(destination), skip_wepp_runs_output=True
                )
            assert not candidate.exists()
            quarantine_dirs = list(destination.glob(".fork-omni-quarantine-*"))
            assert len(quarantine_dirs) == 1
            captured = list(quarantine_dirs[0].iterdir())
            assert len(captured) == 1
            assert captured[0].is_dir()
    finally:
        shutil.rmtree(workspace)
