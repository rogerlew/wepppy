from typing import Iterator

import pytest

from .module_loader import cleanup_import_state


@pytest.fixture(autouse=True)
def _cleanup_interchange_test_imports() -> Iterator[None]:
    """Remove only test-loader injections; preserve real modules and callers."""
    yield
    cleanup_import_state()
