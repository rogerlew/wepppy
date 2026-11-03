"""Retain full collection order and resume the bounded broad validation segment."""
from pathlib import Path
import json
import pytest

START = 'tests/weppcloud/test_run_catalog_postgres.py::test_compare_unreadable_is_inconclusive'

@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    ids = [item.nodeid for item in items]
    assert ids.count(START) == 1, 'Resume anchor missing or duplicated'
    index = ids.index(START)
    before, remaining = items[:index], items[index:]
    Path('/wc1/holdouts/mipa-native-r7-20261103/python-continuation-selection-v3.json').write_text(
        json.dumps({'anchor':START,'collected':len(ids),'deselected_before':ids[:index],
                    'selected':ids[index:]},indent=2)+'\n')
    config.hook.pytest_deselected(items=before)
    items[:] = remaining
