"""Real multipart routes preserve accepted NoDb/source state across rejection."""
from pathlib import Path
from types import SimpleNamespace
import pytest
import uuid
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis.client import Redis

from tests.rq.test_rq212_lifecycle import lifecycle  # noqa: F401
from tests.microservices.test_single_input_uploads import multipart
from wepppy.nodb.core import Ron, Landuse, Soils, Watershed
from wepppy.nodb.single_input_sources import accept_source, read_source
from wepppy.microservices.rq_engine import landuse_routes, soils_routes
from wepppy.rq import single_input_admission, submission_recovery

pytestmark = [pytest.mark.integration, pytest.mark.slow]
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('kind,controller_type,module,filename,field,flag', [
    ('landuse', Landuse, landuse_routes, 'wepppy/wepp/management/data/GeoWEPP/grass.man', 'input_upload_single_landuse', 'burn_shrubs'),
    ('soils', Soils, soils_routes, 'tests/data/single_input_soils/2006.sol', 'input_upload_single_soil', 'clear_ssurgo_cache_on_rebuild'),
])
@pytest.mark.parametrize('invalid', ['flag', 'truncated', 'duplicate', 'content'])
def test_multipart_rejection_and_valid_followup(tmp_path, monkeypatch, lifecycle,
        kind, controller_type, module, filename, field, flag, invalid):
    wd = tmp_path / ('mrs-' + uuid.uuid4().hex); wd.mkdir()
    cfg = 'canada-wbt-mofe.cfg'
    Ron(str(wd), cfg, initialize_components=False)
    Watershed(str(wd), cfg)
    controller = controller_type(str(wd), cfg, run_group='batch', group_name='mrs')
    original_get = controller_type.config_get_str
    monkeypatch.setattr(controller_type, 'config_get_str', lambda self, section, key, default=None:
        'True' if key == 'single_user_defined_uploads' else original_get(self, section, key, default))
    with controller.locked():
        controller._mods = []
        controller._mode = 5
    controller = controller_type.getInstance(str(wd))
    raw = (ROOT / filename).read_bytes()
    accept_source(controller, kind, raw, 'accepted.' + ('man' if kind == 'landuse' else 'sol'))
    before = {p.relative_to(wd): p.read_bytes() for p in wd.rglob('*') if p.is_file() and (p.suffix == '.nodb' or 'single-user-defined' in p.parts)}
    effects = []
    prep = SimpleNamespace(get_rq_job_ids=lambda: {}, get_archive_job_id=lambda: None,
                           remove_timestamp=lambda task: effects.append(task))
    monkeypatch.setattr(module, 'require_jwt', lambda *a, **k: {})
    monkeypatch.setattr(module, 'authorize_run_access', lambda *a, **k: None)
    if kind == 'landuse':
        monkeypatch.setattr(module, 'require_token_class', lambda *a, **k: None)
        monkeypatch.setattr(module, '_run_authority', lambda c: (None, None))
    else:
        monkeypatch.setattr(module, '_config_mismatch_response', lambda *a: None)
        monkeypatch.setattr(module, '_soil_modes_or_error', lambda c: (None, None))
    monkeypatch.setattr(module, 'get_wd', lambda *a, **k: str(wd))
    monkeypatch.setattr(module.RedisPrep, 'getInstance', lambda wd: prep)
    monkeypatch.setattr(single_input_admission, 'redis', SimpleNamespace(Redis=lambda **k: Redis(connection_pool=lifecycle.connection.connection_pool)))
    monkeypatch.setattr(submission_recovery, '_LIFECYCLE_LOCK_DIR', str(tmp_path / 'leases'))
    parts = [(field, 'replacement.' + ('man' if kind == 'landuse' else 'sol'), raw), ('initial_sat', None, b'0.4')]
    if invalid == 'flag': parts.append((flag, None, b'invalid'))
    if invalid == 'duplicate': parts.append(parts[0])
    if invalid == 'content': parts[0] = (field, parts[0][1], b'invalid source')
    app = FastAPI(); app.include_router(module.router)
    url = f'/runs/test/cfg/build-{kind}'
    with TestClient(app) as client:
        response = client.post(url, content=multipart(parts, finished=invalid != 'truncated'), headers={'Content-Type':'multipart/form-data; boundary=source-test'})
        assert response.status_code == 400, response.text
        after = {p.relative_to(wd): p.read_bytes() for p in wd.rglob('*') if p.is_file() and (p.suffix == '.nodb' or 'single-user-defined' in p.parts)}
        assert after == before
        assert effects == []
        assert read_source(controller_type.load_detached(str(wd)), kind)[0]
        response = client.post(url, data={'initial_sat':'0.4'}, files={field: ('followup.' + ('man' if kind == 'landuse' else 'sol'), raw)})
        assert response.status_code == 200, response.text
        assert controller_type.load_detached(str(wd)).single_user_defined_filename.startswith('followup.')
        assert controller_type.getInstance(str(wd)).single_user_defined_filename.startswith('followup.')
