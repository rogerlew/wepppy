"""Interchange test loading must preserve modules already used by other tests."""
import sys

import pytest

from .module_loader import cleanup_import_state, load_module

pytestmark = pytest.mark.unit


def test_existing_native_module_and_parent_packages_survive_cleanup():
    from wepppy.wepp.interchange import _rust_interchange

    names = ('wepppy', 'wepppy.wepp', 'wepppy.wepp.interchange._rust_interchange')
    originals = {name: sys.modules[name] for name in names}
    loaded = load_module('wepppy.wepp.interchange._rust_interchange',
                         'wepppy/wepp/interchange/_rust_interchange.py')
    cleanup_import_state()
    assert loaded is _rust_interchange
    assert all(sys.modules[name] is module for name, module in originals.items())
