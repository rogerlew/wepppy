"""Give this diagnostic rerun unique run basenames without touching shared locks."""
import uuid
import pytest

@pytest.fixture
def tmp_path(tmp_path_factory):
    return tmp_path_factory.mktemp('mrs-' + uuid.uuid4().hex)


def pytest_collection_modifyitems(config, items):
    import os
    pivot = os.environ.get('MRS_CONTINUE_FROM')
    if not pivot:
        return
    matches = [index for index, item in enumerate(items) if item.nodeid == pivot]
    if len(matches) != 1:
        raise pytest.UsageError('Expected exactly one retained full-suite continuation node')
    before = items[:matches[0]]
    items[:] = items[matches[0]:]
    config.hook.pytest_deselected(items=before)
