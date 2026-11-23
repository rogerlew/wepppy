"""The maintenance CLI must not rewrite assets during import discovery."""
import json
from pathlib import Path
import runpy
import shutil

import pytest

pytestmark = pytest.mark.unit


def test_sidecar_generator_writes_only_when_explicitly_executed(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[3]
    data = root / 'wepppy/wepp/management/data'
    script = data / 'UnDisturbed/dump_to_json.py'
    shutil.copyfile(data / 'GeoWEPP/grass.man', tmp_path / 'input.man')
    monkeypatch.chdir(tmp_path)

    runpy.run_path(str(script), run_name='sidecar_import_probe')
    assert not (tmp_path / 'input.man.json').exists()

    runpy.run_path(str(script), run_name='__main__')
    output = json.loads((tmp_path / 'input.man.json').read_text())
    assert output['nofe'] == 1
    assert output['plants']['py/seq'][0]['name'] == 'bromegr1'
