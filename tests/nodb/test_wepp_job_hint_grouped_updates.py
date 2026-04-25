from __future__ import annotations

from contextlib import contextmanager

import pytest

from wepppy.nodb.core.wepp import Wepp


pytestmark = pytest.mark.unit


class _LockRecorder:
    def __init__(self) -> None:
        self.calls = 0
        self.enters = 0
        self.exits = 0

    def locked(self):
        self.calls += 1

        @contextmanager
        def _scope():
            self.enters += 1
            try:
                yield
            finally:
                self.exits += 1

        return _scope()


def test_persist_job_hint_noop_skips_lock_and_mutation() -> None:
    wepp = object.__new__(Wepp)
    wepp._job_id = "existing-job"
    wepp._job_key = "existing-key"

    lock = _LockRecorder()
    wepp.locked = lock.locked

    wepp.persist_job_hint()

    assert lock.calls == 0
    assert wepp._job_id == "existing-job"
    assert wepp._job_key == "existing-key"


def test_persist_job_hint_uses_one_lock_and_normalizes_values() -> None:
    wepp = object.__new__(Wepp)
    wepp._job_id = None
    wepp._job_key = None

    lock = _LockRecorder()
    wepp.locked = lock.locked

    wepp.persist_job_hint(job_id="  job-501  ", job_key="  run_wepp_rq ")

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert wepp._job_id == "job-501"
    assert wepp._job_key == "run_wepp_rq"
    assert wepp.job_id == "job-501"
    assert wepp.job_key == "run_wepp_rq"


def test_persist_job_hint_job_id_only_preserves_existing_job_key() -> None:
    wepp = object.__new__(Wepp)
    wepp._job_id = "existing-job"
    wepp._job_key = "existing-key"

    lock = _LockRecorder()
    wepp.locked = lock.locked

    wepp.persist_job_hint(job_id="  updated-job  ")

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert wepp._job_id == "updated-job"
    assert wepp._job_key == "existing-key"
    assert wepp.job_id == "updated-job"
    assert wepp.job_key == "existing-key"


def test_persist_job_hint_job_key_only_preserves_existing_job_id() -> None:
    wepp = object.__new__(Wepp)
    wepp._job_id = "existing-job"
    wepp._job_key = "existing-key"

    lock = _LockRecorder()
    wepp.locked = lock.locked

    wepp.persist_job_hint(job_key="  updated-key  ")

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert wepp._job_id == "existing-job"
    assert wepp._job_key == "updated-key"
    assert wepp.job_id == "existing-job"
    assert wepp.job_key == "updated-key"


def test_persist_job_hint_explicit_clear_normalizes_to_none() -> None:
    wepp = object.__new__(Wepp)
    wepp._job_id = "existing-job"
    wepp._job_key = "existing-key"

    lock = _LockRecorder()
    wepp.locked = lock.locked

    wepp.persist_job_hint(job_id="   ", job_key=None)

    assert lock.calls == 1
    assert lock.enters == 1
    assert lock.exits == 1
    assert wepp._job_id is None
    assert wepp._job_key is None
    assert wepp.job_id is None
    assert wepp.job_key is None
