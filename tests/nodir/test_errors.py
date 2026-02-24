from __future__ import annotations

from contextlib import contextmanager

import pytest

from wepppy.nodir.errors import NoDirError, nodir_locked

pytestmark = pytest.mark.unit


@contextmanager
def _generator_context():
    yield


def test_nodir_error_survives_generator_contextmanager_throw() -> None:
    with pytest.raises(NoDirError) as exc:
        with _generator_context():
            raise nodir_locked("lock is held")

    assert exc.value.http_status == 503
    assert exc.value.code == "NODIR_LOCKED"
