"""Explicit opt-in full-site acceptance; portable matrix needs no local run."""
import os
from pathlib import Path
import pytest

from tests.roads.roads_project import DESIGNS, validate_project, verify_negative

pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.fixture
def source_site():
    source = os.environ.get("ROADS_VALIDATION_SOURCE")
    if not source:
        pytest.skip("Set ROADS_VALIDATION_SOURCE to the pinned clogging-starch fixture")
    return Path(source).resolve(strict=True)


@pytest.mark.parametrize("design", DESIGNS)
def test_design_project(source_site, tmp_path, design):
    validate_project(source_site, tmp_path / design, design,
                     exclude_infeasible_unrutted=design == "outslope_unrutted")


def test_full_upload_unrutted_rejection(source_site, tmp_path):
    root = tmp_path / "unrutted_negative"
    with pytest.raises(RuntimeError, match="segment execution failed for 2 segment"):
        validate_project(source_site, root, "outslope_unrutted")
    verify_negative(source_site, root)
