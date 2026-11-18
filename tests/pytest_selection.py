"""Explicit opt-in for the expensive Disturbed native simulation matrix."""
from __future__ import annotations

from pathlib import Path

import pytest

MATRIX_PATH = Path(__file__).resolve().parent / "disturbed/test_disturbed_matrix.py"


def pytest_addoption(parser):
    parser.addoption(
        "--run-disturbed-matrix", action="store_true", default=False,
        help="Include the Disturbed native simulation matrix and dependent summaries.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "disturbed_matrix: Native Disturbed matrix; requires --run-disturbed-matrix",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    # Selection policy stays outside the source-pinned scientific producer.
    # Only this exact module owns native matrix cases and dependent summaries.
    for item in items:
        if item.path.name == MATRIX_PATH.name and item.path.resolve() == MATRIX_PATH:
            item.add_marker("disturbed_matrix")
    if config.getoption("--run-disturbed-matrix"):
        return
    deselected = [item for item in items if item.get_closest_marker("disturbed_matrix")]
    if deselected:
        items[:] = [item for item in items if not item.get_closest_marker("disturbed_matrix")]
        config.hook.pytest_deselected(items=deselected)
