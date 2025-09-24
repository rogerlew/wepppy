import pytest

from wepppy.nodb import Wepp

WD = '/wc1/runs/ca/calculable-clang/omni/scenarios/undisturbed'

@pytest.fixture()
def ron():
    instance = Wepp.getInstance(WD)
    instance.unlock()
    yield instance
    instance.unlock()

def test_is_omni_run_true(ron):
    assert ron.is_omni_run is True

def test_runid_matches_expected(ron):
    assert ron.runid == 'calculable-clang'

def test_relpath_to_parent(ron):
    assert ron._relpath_to_parent == 'omni/scenarios/undisturbed'

def test_unlock_sets_unlocked(ron):
    ron.unlock()
    assert ron.islocked() is False

def test_lock_sets_locked(ron):
    ron.unlock()
    ron.lock()
    assert ron.islocked() is True

def test_unlock_after_lock_clears_lock(ron):
    ron.unlock()
    ron.lock()
    ron.unlock()
    assert ron.islocked() is False
