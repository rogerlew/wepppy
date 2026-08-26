"""Canonical RQ job identifier generation."""

from uuid import uuid4


def new_rq_job_id() -> str:
    """Return a canonical hyphenated UUID string for an RQ job."""
    return str(uuid4())


__all__ = ["new_rq_job_id"]
