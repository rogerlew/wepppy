"""Resume the ordered broad gate after a known mid-run source-reload mismatch."""

import os


def pytest_collection_modifyitems(config, items):
    boundary = os.environ.get('ROADS_RESUME_NODE', 'tests/query_engine/test_mcp_router.py::test_create_mcp_app')
    index = next(i for i, item in enumerate(items) if item.nodeid == boundary)
    deselected = items[:index]
    items[:] = items[index:]
    config.hook.pytest_deselected(items=deselected)
