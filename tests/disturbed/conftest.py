"""
Pytest fixtures for the disturbed WEPP test matrix.
"""

import shutil
from pathlib import Path

import pytest

# Directory containing this conftest.py
TEST_DIR = Path(__file__).parent
DATA_DIR = TEST_DIR / "data"


@pytest.fixture(scope="session")
def canonical_slope_path() -> Path:
    """Path to the canonical 200m slope profile."""
    path = DATA_DIR / "canonical_slope.slp"
    assert path.exists(), f"Canonical slope file not found: {path}"
    return path


@pytest.fixture(scope="session")
def test_climate_path() -> Path:
    """Path to the 100-year test climate file."""
    path = DATA_DIR / "test_climate.cli"
    assert path.exists(), f"Test climate file not found: {path}"
    return path


@pytest.fixture(scope="session")
def hillslope_template_path() -> Path:
    """Path to the hillslope template with graphics enabled."""
    path = DATA_DIR / "hillslope_graph.template"
    assert path.exists(), f"Hillslope template not found: {path}"
    return path


@pytest.fixture(scope="session")
def wepppy_root() -> Path:
    """Path to the wepppy package root."""
    # Go up from tests/disturbed to wepppy root
    return TEST_DIR.parent.parent


@pytest.fixture(scope="session")
def forest_soils_dir(wepppy_root: Path) -> Path:
    """Path to the Forest soils directory."""
    path = wepppy_root / "wepppy" / "wepp" / "soils" / "soilsdb" / "data" / "Forest"
    assert path.exists(), f"Forest soils directory not found: {path}"
    return path


@pytest.fixture(scope="session")
def management_data_dir(wepppy_root: Path) -> Path:
    """Path to the management data directory."""
    path = wepppy_root / "wepppy" / "wepp" / "management" / "data"
    assert path.exists(), f"Management data directory not found: {path}"
    return path


@pytest.fixture(scope="session")
def disturbed_lookup_path(wepppy_root: Path) -> Path:
    """Path to the disturbed land-soil lookup CSV."""
    path = wepppy_root / "wepppy" / "nodb" / "mods" / "disturbed" / "data" / "disturbed_land_soil_lookup.csv"
    assert path.exists(), f"Disturbed lookup CSV not found: {path}"
    return path


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory) -> Path:
    """Create a temporary run directory for test outputs.

    Structure matches WEPP template expectations:
        run_dir/
        ├── runs/     <- WEPP input files (.slp, .man, .sol, .cli, .run)
        └── output/   <- WEPP output files (../output/ from runs/)
    """
    run_dir = tmp_path_factory.mktemp("disturbed_matrix")
    runs_dir = run_dir / "runs"
    output_dir = run_dir / "output"  # At same level as runs/, not inside
    runs_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


@pytest.fixture(scope="module")
def runs_dir(run_dir: Path) -> Path:
    """Path to the runs subdirectory (WEPP input files)."""
    return run_dir / "runs"


@pytest.fixture(scope="module")
def output_dir(run_dir: Path) -> Path:
    """Path to the output subdirectory (WEPP output files)."""
    return run_dir / "output"
