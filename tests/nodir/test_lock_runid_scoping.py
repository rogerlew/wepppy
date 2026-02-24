from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_nodir_lock_runid_uses_parent_for_pup_workspaces() -> None:
    wd = Path("/tmp/victoria-ca-2026-sbs/_pups/omni/scenarios/undisturbed")

    import wepppy.nodir.materialize as materialize_mod
    import wepppy.nodir.projections as projections_mod
    import wepppy.nodir.thaw_freeze as thaw_freeze_mod

    expected = "victoria-ca-2026-sbs"
    assert thaw_freeze_mod._runid_from_wd(wd) == expected
    assert projections_mod._runid_from_wd(wd) == expected
    assert materialize_mod._runid_from_wd(wd) == expected
