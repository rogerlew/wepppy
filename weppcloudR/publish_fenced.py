#!/usr/bin/env python3
"""Atomically publish a DEVAL artifact without following run-tree symlinks."""

from __future__ import annotations

import fcntl
import hashlib
import os
import re
import stat
import sys
from typing import NoReturn


def fail(message: str) -> NoReturn:
    raise SystemExit(message)


def open_directory(parent_fd: int, name: str) -> int:
    return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)


def main() -> None:
    if len(sys.argv) != 5:
        fail("expected active root, run ID, generation, and temporary basename")
    active_root, runid, generation_text, temporary_name = sys.argv[1:]
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,245}", runid):
        fail("invalid run ID")
    if temporary_name != "-" and not re.fullmatch(
        r"\.deval_[A-Za-z0-9_.-]+\.tmp[.]htm", temporary_name
    ):
        fail("invalid temporary artifact name")
    try:
        generation = int(generation_text)
    except ValueError:
        fail("invalid fencing generation")
    if generation < 1:
        fail("invalid fencing generation")

    active_root = os.path.normpath(active_root)
    configured = os.environ.get(
        "WEPPCLOUDR_RUN_ROOTS",
        "/wc1/runs:/geodata/weppcloud_runs:/wc1/batch:/wc1/culverts",
    ).split(os.pathsep)
    matches = [
        os.path.normpath(root)
        for root in configured
        if active_root != os.path.normpath(root)
        and os.path.commonpath((active_root, os.path.normpath(root)))
        == os.path.normpath(root)
    ]
    if len(matches) != 1:
        fail("active root has no unique approved root")

    opened: list[int] = []
    output_fd: int | None = None
    destination_name: str | None = None
    destination_created = False
    try:
        current_fd = os.open(matches[0], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        opened.append(current_fd)
        for component in os.path.relpath(active_root, matches[0]).split(os.sep):
            current_fd = open_directory(current_fd, component)
            opened.append(current_fd)
        export_fd = open_directory(current_fd, "export")
        opened.append(export_fd)
        output_fd = open_directory(export_fd, "WEPPcloudR")
        opened.append(output_fd)
        locks_fd = open_directory(current_fd, "_locks")
        opened.append(locks_fd)
        fence_dir_fd = open_directory(locks_fd, "weppcloudr")
        opened.append(fence_dir_fd)

        lock_fd = os.open(
            f"deval_{runid}.fence.publish.lock",
            os.O_RDWR | os.O_NOFOLLOW,
            dir_fd=fence_dir_fd,
        )
        opened.append(lock_fd)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        fence_fd = os.open(
            f"deval_{runid}.fence", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fence_dir_fd
        )
        opened.append(fence_fd)
        if not stat.S_ISREG(os.fstat(fence_fd).st_mode):
            fail("fencing record is not regular")
        current_generation = os.read(fence_fd, 64).decode("ascii").strip()
        if current_generation != str(generation):
            fail("render fencing generation is stale")

        final_name = f"deval_{runid}.htm"
        if temporary_name == "-":
            temporary_fd = os.open(
                final_name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=output_fd
            )
            opened.append(temporary_fd)
            destination_name = None
        else:
            staging_fd = os.open("/tmp", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            opened.append(staging_fd)
            temporary_fd = os.open(
                temporary_name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=staging_fd
            )
            opened.append(temporary_fd)
            destination_name = f".{temporary_name}.publishing"
            destination_fd = os.open(
                destination_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o644,
                dir_fd=output_fd,
            )
            destination_created = True
            opened.append(destination_fd)
            os.fchmod(destination_fd, 0o644)
        if not stat.S_ISREG(os.fstat(temporary_fd).st_mode):
            fail("artifact source is not regular")
        digest = hashlib.sha256()
        size = 0
        while chunk := os.read(temporary_fd, 1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
            if destination_name is not None:
                remaining = memoryview(chunk)
                while remaining:
                    remaining = remaining[os.write(destination_fd, remaining) :]
        if destination_name is not None:
            os.fsync(destination_fd)
        try:
            final_stat = os.stat(final_name, dir_fd=output_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            if not stat.S_ISREG(final_stat.st_mode):
                fail("final artifact is not a regular file")
        if destination_name is not None:
            os.rename(destination_name, final_name, src_dir_fd=output_fd, dst_dir_fd=output_fd)
            os.fsync(output_fd)
        print(f"{digest.hexdigest()} {size}")
    finally:
        if output_fd is not None and destination_name is not None and destination_created:
            try:
                os.unlink(destination_name, dir_fd=output_fd)
            except FileNotFoundError:
                pass
        for descriptor in reversed(opened):
            os.close(descriptor)


if __name__ == "__main__":
    main()
