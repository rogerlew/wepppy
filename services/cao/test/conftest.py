from __future__ import annotations

from _pytest.nodes import Collector
from _pytest.python import Function


def pytest_pycollect_makeitem(collector: Collector, name: str, obj: object):
    if name == "collection_error" and callable(obj):
        return [Function.from_parent(collector, name=name, callobj=obj)]
    return None
