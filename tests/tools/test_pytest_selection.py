"""Exercise selection through real pytest sessions without native simulations."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("opt_in", [False, True])
def test_disturbed_matrix_selection_preserves_lightweight_contracts(tmp_path, opt_in):
    (tmp_path / 'test_sample.py').write_text('''
from pathlib import Path
import pytest

def test_contract():
    Path('contract-ran').touch()

@pytest.mark.disturbed_matrix
class TestNativeMatrix:
    def test_simulation(self):
        Path('native-ran').touch()
    def test_summary(self):
        assert Path('native-ran').exists()
''')
    environment = dict(os.environ, PYTHONPATH=str(ROOT), PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    environment.pop('PYTEST_ADDOPTS', None)
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', '-p', 'tests.pytest_selection', '-q',
         *(['--run-disturbed-matrix'] if opt_in else [])],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / 'contract-ran').exists()
    assert (tmp_path / 'native-ran').exists() is opt_in
    assert ('3 passed' if opt_in else '1 passed, 2 deselected') in result.stdout
