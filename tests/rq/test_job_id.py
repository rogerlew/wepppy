from __future__ import annotations

from uuid import UUID

import pytest

from wepppy.rq.job_id import new_rq_job_id

pytestmark = pytest.mark.unit


def test_new_rq_job_id_uses_canonical_hyphenated_uuid4() -> None:
    job_id = new_rq_job_id()

    parsed = UUID(job_id)
    assert parsed.version == 4
    assert str(parsed) == job_id
    assert len(job_id) == 36
    assert job_id.count("-") == 4
