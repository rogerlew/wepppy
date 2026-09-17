from __future__ import annotations

import pytest

# Load the real package boundary before optional stubs, matching production.
# Otherwise standalone collection stubs Flask before package __init__ imports
# its real Flask helpers; combined suites only passed by import-order accident.
import wepppy.profile_recorder  # noqa: F401
import tests.profile_recorder.stubdeps as stubdeps


@pytest.fixture(scope="session", autouse=True)
def _profile_recorder_stubs():
    """Install profile-recorder stubs for this session only."""

    stubdeps.ensure_profile_test_stubs()
    yield
    stubdeps.restore_profile_test_stubs()
