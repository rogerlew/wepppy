"""Executable 516-case Roads matrix; outputs retained under pytest basetemp."""
import pytest
from tests.roads.roads_matrix import CASES, initialize, prepare, execute

pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.fixture(scope="module")
def matrix_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("roads_matrix")
    initialize(root)
    return root


@pytest.mark.parametrize("identifier,case", enumerate(CASES, 1), ids=[c.name for c in CASES])
def test_profile(matrix_root, identifier, case):
    from wepppy.nodb.mods.roads import Roads
    roads = (Roads.getInstance(str(matrix_root)) if (matrix_root / "roads.nodb").exists()
             else Roads(str(matrix_root), "disturbed9002-wbt-mofe.cfg"))
    execute(matrix_root, prepare(roads, matrix_root, case, identifier))
