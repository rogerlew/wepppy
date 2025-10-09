"""Query engine utilities for schema activation and lightweight querying."""

__all__ = ["activate_query_engine", "resolve_run_context", "run_query"]


def activate_query_engine(*args, **kwargs):
    from .activate import activate_query_engine as _impl

    return _impl(*args, **kwargs)


def resolve_run_context(*args, **kwargs):
    from .context import resolve_run_context as _impl

    return _impl(*args, **kwargs)


def run_query(*args, **kwargs):
    from .core import run_query as _impl

    return _impl(*args, **kwargs)
