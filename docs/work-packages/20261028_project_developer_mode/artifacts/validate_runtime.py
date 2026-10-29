"""Bounded DM-01 acceptance on an isolated forest project; run via wctl exec."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import importlib
import json
import os
import shutil
import uuid

import redis
from rq import Queue
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Ron, Wepp
from wepppy.nodb.core.soil_anisotropy import effective_anisotropy
from wepppy.nodb.core.wepp import prep_multi_ofe_hillslope
from wepp_runner.wepp_runner import run_hillslope

REPO = Path('/workdir/wepppy')
EVIDENCE = REPO / 'docs/work-packages/20261028_project_developer_mode/artifacts'
ROOT = Path('/wc1/runs/dm/dm-anisotropy-validation')
if ROOT.exists():
    raise RuntimeError('Acceptance project already exists; inspect evidence before retrying')
shutil.copytree('/wc1/runs/sa/sa-anisotropy-validation', ROOT)
(ROOT / 'READONLY').unlink(missing_ok=True)
(ROOT / 'PUBLIC').touch()
# Inherited source is the earlier ordinary-mode validation fixture.
ron = Ron.getInstance(str(ROOT))
assert ron.developer_mode is False
wepp = Wepp.getInstance(str(ROOT))
with wepp.locked():
    wepp._multi_ofe = True
    wepp._run_wepp_ui = True

# Use the actual Flask activation route and CSRF; scoped synthetic identity,
# not account mutation. Ordinary project authorization still executes.
from wepppy.weppcloud.app import app
from flask_wtf.csrf import generate_csrf
from flask_login import UserMixin
class Principal(UserMixin):
    id = 'dm-validation-identity'
    roles = ['Dev']
    def has_role(self, role):
        return role in self.roles
principal = Principal()
original_loader = app.login_manager._request_callback
app.login_manager.request_loader(lambda request: principal)
client = app.test_client()
url = f'/runs/{ROOT.name}/{ron.config_stem}/tasks/enable_developer_mode'
with client.session_transaction() as session:
    session['csrf_token'] = 'dm-validation-session'
with app.test_request_context():
    from flask import session
    session['csrf_token'] = 'dm-validation-session'
    csrf = generate_csrf()
try:
    response = client.post(url, json={}, headers={'X-CSRFToken': csrf})
    assert response.status_code == 200, (response.status_code, response.get_data(as_text=True)[:200])
    assert response.json == {'Content': {'developer_mode': True}}
    principal.roles = []
    assert client.post(url, json={}, headers={'X-CSRFToken': csrf}).status_code == 403
    # This actor has no Dev role; Wepp's parser resolves only Ron project policy.
    wepp.parse_inputs({'soil_anisotropy_upper': 101, 'soil_anisotropy_lower': 11})
finally:
    app.login_manager._request_callback = original_loader
ron = Ron.getInstance(str(ROOT))
wepp = Wepp.getInstance(str(ROOT))
overrides = effective_anisotropy(wepp, developer_mode=ron.developer_mode)
assert overrides == (101, 11)
runs = ROOT / 'wepp/runs'
for old in runs.glob('*'):
    if old.is_file():
        old.unlink()
output = ROOT / 'wepp/output'
output.mkdir(exist_ok=True)
for old in output.glob('*'):
    if old.is_file():
        old.unlink()
fixture = REPO / 'tests/wepp_runner/fixtures/hillslope_smoke/runs'
for name in ['p1.cli', 'wepp_ui.txt', 'snow.txt', 'pmetpara.txt', 'gwcoeff.txt', 'chan.inp', 'chntyp.txt']:
    shutil.copy2(fixture/name, runs/name)
template = (REPO/'tests/disturbed/data/hillslope_graph.template').read_text()
(runs/'p1.run').write_text(template.format(wepp_id=1,sim_years=1,man_relpath='',slp_relpath='',cli_relpath='',sol_relpath=''))
source = ROOT/'soils/hill_101.mofe.sol'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
args = ('101', 1, str(ROOT), str(runs), 1, None, .4, False, 300, False, 1000, False, 1000,
        None, False, False, overrides, ron.developer_mode)
with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
    queue = Queue('default', connection=connection)
    prep = queue.enqueue_call(prep_multi_ofe_hillslope, args=(args,), timeout=120,
        result_ttl=86400, job_id='dm-prep-'+uuid.uuid4().hex, meta={'runid': ROOT.name})
    model = queue.enqueue_call(run_hillslope, args=(1,str(runs)),
        kwargs={'wepp_bin':'wepp_261026','timeout':60,'timeout_retries':0},
        depends_on=prep,timeout=120,result_ttl=86400,job_id='dm-model-'+uuid.uuid4().hex,
        meta={'runid':ROOT.name})
receipt = {'runid':ROOT.name,'config':ron.config_stem,'root':str(ROOT),'source_sha256':source_hash,
    'prep_job':prep.id,'model_job':model.id,'overrides':overrides,
    'activation':'actual Flask route and CSRF, synthetic Dev request principal; no account mutation',
    'submission':'ordinary no-Dev principal context; real Wepp parser/persistence',
    'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups()}
(EVIDENCE/'runtime.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
