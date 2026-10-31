"""Actual optional-controller initialization/persistence at Flask request boundaries."""
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest
from flask import Flask
from wepppy.nodb.core import Ron, Watershed
from wepppy.nodb.mods.path_ce import PathCostEffective
from wepppy.nodb.mods.geneva import Geneva
from wepppy.weppcloud.routes.nodb_api import path_ce_bp as path_routes, geneva_bp as geneva_routes
from wepppy.weppcloud.utils import helpers

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('kind', ['path', 'geneva'])
def test_optional_controller_absence_and_real_persistence(tmp_path, monkeypatch, kind):
    wd = tmp_path / ('mrs-' + uuid.uuid4().hex); wd.mkdir()
    cfg = 'canada-wbt-mofe'
    Ron(str(wd), cfg+'.cfg', initialize_components=False)
    Watershed(str(wd), cfg+'.cfg')
    module, controller, blueprint, endpoint = (
        (path_routes, PathCostEffective, path_routes.path_ce_bp, 'api/path_ce/config') if kind == 'path' else
        (geneva_routes, Geneva, geneva_routes.geneva_bp, 'api/geneva/config'))
    monkeypatch.setattr(helpers, 'authorize', lambda *a, **k: None)
    if hasattr(module, 'authorize'):
        monkeypatch.setattr(module, 'authorize', lambda *a, **k: None)
    monkeypatch.setattr(module, 'load_run_context', lambda *a: SimpleNamespace(active_root=wd))
    if kind == 'path':
        monkeypatch.setattr(module, 'require_feature', lambda *a, **k: None)
    app = Flask(__name__); app.config['TESTING'] = True; app.register_blueprint(blueprint)
    nodb = wd / controller.filename
    url = f'/runs/test/{cfg}/{endpoint}'
    with app.test_client() as client:
        before = {p.relative_to(wd):p.read_bytes() for p in wd.rglob('*') if p.is_file()}
        response = client.post(url, data='{', content_type='application/json')
        assert response.status_code == 400
        assert not nodb.exists()
        assert not (wd / kind).exists()
        assert {p.relative_to(wd):p.read_bytes() for p in wd.rglob('*') if p.is_file()} == before
        valid = {'sddc_threshold':12} if kind == 'path' else {'schema_version':1}
        response = client.post(url, json=valid)
        assert response.status_code == 200, response.text
        assert nodb.exists()
        before = {p.relative_to(wd):p.read_bytes() for p in wd.rglob('*') if p.is_file()}
        bad = {'sddc_threshold':'bad'} if kind == 'path' else {'enabled':True, 'schema_version':'bad'}
        response = client.post(url, json=bad)
        assert response.status_code == 400
        assert {p.relative_to(wd):p.read_bytes() for p in wd.rglob('*') if p.is_file()} == before
        assert controller.getInstance(str(wd)).wd == controller.load_detached(str(wd)).wd
        assert client.post(url, json=valid).status_code == 200
        assert controller.load_detached(str(wd)) is not None


@pytest.mark.parametrize('field,value', [('reservoir_capacity','garbage'), ('reservoir_storage','NaN'), ('low','garbage')])
def test_watar_numeric_rejection_preserves_real_ash(tmp_path, monkeypatch, field, value):
    from wepppy.nodb.mods.ash_transport import Ash
    from wepppy.weppcloud.routes.nodb_api import watar_bp as routes
    wd = tmp_path / ('mrs-' + uuid.uuid4().hex); wd.mkdir()
    cfg = 'disturbed9002.cfg'
    Ron(str(wd), cfg, initialize_components=False)
    Ash(str(wd), cfg)
    ash = Ash.getInstance(str(wd))
    contaminant = next(iter(ash.low_contaminant_concentrations))
    field = f'low_{contaminant}' if field == 'low' else field
    monkeypatch.setattr(helpers, 'authorize', lambda *a, **k: None)
    monkeypatch.setattr(routes, 'get_wd', lambda *a: str(wd))
    monkeypatch.setattr(routes.Climate, 'getInstance', lambda *a: SimpleNamespace(years=[2000]))
    monkeypatch.setattr(routes.AshPost, 'getInstance', lambda *a: SimpleNamespace(
        recurrence_intervals=[], burn_class_return_periods={}, return_periods=[], pw0_stats={}))
    monkeypatch.setattr(routes, 'parse_rec_intervals', lambda *a: [])
    monkeypatch.setattr(routes, 'resolve_unitizer_presentation', lambda *a: None)
    monkeypatch.setattr(routes, 'render_template', lambda *a, **k: 'report')
    app = Flask(__name__); app.config['TESTING'] = True; app.register_blueprint(routes.watar_bp)
    before = (wd / Ash.filename).read_bytes()
    with app.test_client() as client:
        url = '/runs/test/cfg/report/ash_contaminant'
        data = {f'low_{contaminant}':'12', field:value}
        response = client.post(url, data=data)
        assert response.status_code == 400, response.text
        assert (wd / Ash.filename).read_bytes() == before
        assert Ash.getInstance(str(wd)).low_contaminant_concentrations == Ash.load_detached(str(wd)).low_contaminant_concentrations
        response = client.post(url, data={f'low_{contaminant}':'12', 'reservoir_capacity':'0'})
        assert response.status_code == 200, response.text
        assert Ash.load_detached(str(wd)).low_contaminant_concentrations[contaminant] == 12
