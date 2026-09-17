"""Actual observed-path changes must stay explicit rather than authorize reuse."""
import errno
import json
from pathlib import Path

import pytest

from raster_implementation_security_probe import raster
from wepppy.all_your_base import raster_freshness as freshness


@pytest.mark.parametrize("kind", ["source_removed", "parent_renamed", "parent_denied"])
def test_observed_members_become_unavailable(tmp_path, monkeypatch, kind):
    directory = tmp_path / "source"
    directory.mkdir()
    path = directory / "source.tif"
    raster(path)
    original = freshness.sha256_file
    changed = False

    def hash_then_change(selected):
        nonlocal changed
        digest = original(selected)
        if not changed:
            changed = True
            if kind == "source_removed":
                path.unlink()
            elif kind == "parent_renamed":
                directory.rename(tmp_path / "moved")
            else:
                directory.chmod(0)
        return digest

    monkeypatch.setattr(freshness, "sha256_file", hash_then_change)
    try:
        with pytest.raises(OSError) as caught:
            freshness.raster_dependency_signature(path)
        record = {"case": kind, "error": type(caught.value).__name__,
                  "errno": caught.value.errno, "message": str(caught.value),
                  "source_change_errno": caught.value.errno == errno.ESTALE}
        Path(__file__).with_name(f"raster_observation_error_{kind}_revision2.json").write_text(json.dumps(record, indent=2)+"\n")
        print("OBSERVATION_ERROR " + json.dumps(record))
        # Record rejection independently from exact source-change translation.
        assert changed
        assert caught.value.errno == errno.ESTALE
    finally:
        if kind == "parent_denied":
            directory.chmod(0o755)
