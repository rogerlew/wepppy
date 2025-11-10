from __future__ import annotations

import pytest

import tests.profile_recorder.stubdeps as stubdeps


@pytest.fixture(scope="session", autouse=True)
def _profile_recorder_stubs():
    """Install profile-recorder stubs for this session only."""

    stubdeps.ensure_profile_test_stubs()
    yield
    stubdeps.restore_profile_test_stubs()
