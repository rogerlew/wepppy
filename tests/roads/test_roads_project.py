"""Explicit opt-in full-site acceptance; portable matrix needs no local run."""
import os
from pathlib import Path
import pytest

from tests.roads.roads_project import validate_project
from tests.roads.unrutted_project import validate_unrutted_project

pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.fixture
def source_site():
    source = os.environ.get("ROADS_VALIDATION_SOURCE")
    if not source:
        pytest.skip("Set ROADS_VALIDATION_SOURCE to the pinned clogging-starch fixture")
    return Path(source).resolve(strict=True)


@pytest.mark.parametrize("design", ("inslope_bd", "inslope_rd", "outslope_rutted"))
def test_design_project(source_site, tmp_path, design):
    validate_project(source_site, tmp_path / design, design)


@pytest.fixture
def unrutted_source_site():
    source = os.environ.get("ROADS_UNRUTTED_VALIDATION_SOURCE")
    if not source:
        pytest.skip("Set ROADS_UNRUTTED_VALIDATION_SOURCE to the pinned misty-eyed-divorcee fixture")
    return Path(source).resolve(strict=True)


def test_full_upload_unrutted_top_placement(unrutted_source_site, tmp_path):
    result = validate_unrutted_project(unrutted_source_site, tmp_path / "unrutted_positive", fill_length_m=5.)
    assert result["status"] == "completed"


def test_full_upload_unrutted_oversized_geometry(unrutted_source_site, tmp_path):
    result = validate_unrutted_project(unrutted_source_site, tmp_path / "unrutted_negative", fill_length_m=30.)
    assert result["status"] == "failed" and result["readback"]["current_receipt_absent"]
