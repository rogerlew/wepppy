"""DM-02 local acceptance, disposable projects only; execute via wctl exec."""
from pathlib import Path
from html.parser import HTMLParser
import csv
import hashlib
import io
import json
import os
import shutil
import time

from flask import render_template, session
from flask_login import UserMixin
from flask_wtf.csrf import generate_csrf
from wepppy.nodb.core import Ron
from wepppy.nodb.core.ron import RonViewModel
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.unitizer import Unitizer, precisions
from wepppy.weppcloud.app import app

EVIDENCE = Path('/workdir/wepppy/docs/work-packages/20261029_extended_landsoil_developer_panel/artifacts')
SOURCE = Path('/wc1/runs/sa/sa-anisotropy-validation')
ROOT = Path('/wc1/runs/d2/d2-landsoil-base')
LEGACY = ROOT.with_name('d2-landsoil-legacy')
DEVELOPER = ROOT.with_name('d2-landsoil-developer')
for destination in (ROOT, LEGACY, DEVELOPER):
    if destination.exists():
        raise RuntimeError(f'Inspect existing acceptance evidence before retrying: {destination}')


def files(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and (p.suffix in {'.csv', '.sol', '.nodb'})}


original = files(SOURCE)
shutil.copytree(SOURCE, ROOT)
(ROOT / 'READONLY').unlink(missing_ok=True)
(ROOT / 'PUBLIC').touch()
ron = Ron.getInstance(str(ROOT))
assert not ron.developer_mode
config = ron.config_stem
disturbed = Disturbed.getInstance(str(ROOT))
disturbed.active_lookup_variant = 'base'
Path(disturbed.extended_lookup_fn).unlink(missing_ok=True)


class Principal(UserMixin):
    id = 'dm2-validation'
    roles = []
    def has_role(self, role):
        return role in self.roles


class Controls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.actions = []
        self.editors = []
        self.radios = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'data-disturbed-action' in attrs:
            self.actions.append(attrs['data-disturbed-action'])
        if 'data-disturbed-modify-link' in attrs:
            self.editors.append(attrs['data-disturbed-modify-link'])
        if 'data-disturbed-lookup-variant' in attrs:
            self.radios.append(attrs.get('value'))


principal = Principal()
old_loader = app.login_manager._request_callback
app.login_manager.request_loader(lambda request: principal if request.method == "POST" else None)
client = app.test_client()
with client.session_transaction() as state:
    state['csrf_token'] = 'dm2-local-acceptance'
    state['cap_verified_at'] = time.time()
with app.test_request_context():
    session['csrf_token'] = 'dm2-local-acceptance'
    token = generate_csrf()
headers = {'X-CSRFToken': token}
receipt = {'config': config, 'uid': os.getuid(), 'gid': os.getgid(), 'groups': os.getgroups(),
           'identity': 'scoped synthetic principal, real authorization/CSRF; no account or role mutation',
           'projects': [p.name for p in (ROOT, LEGACY, DEVELOPER)], 'layouts': {}, 'operations': []}


def url(root, suffix):
    return f'/runs/{root.name}/{config}/{suffix}'


def post(root, suffix, payload=None, extra_headers=None, expected=200):
    response = client.post(url(root, suffix), json={} if payload is None else payload,
                           headers={**headers, **(extra_headers or {})})
    assert response.status_code == expected, (suffix, response.status_code, response.get_data(as_text=True)[:500])
    receipt['operations'].append({'project': root.name, 'operation': suffix, 'status': response.status_code, 'roles': list(principal.roles)})
    return response


def check_layout(root, label, full):
    before = files(root)
    response = client.get(url(root, '?skip_migration_check=true'))
    assert response.status_code == 200, response.get_data(as_text=True)[:500]
    html = response.get_data(as_text=True)
    controller = Ron.getInstance(str(root))
    with app.test_request_context(url(root, 'report/dm2-shell')):
        # Real shared report shell and context processors, intentionally no Disturbed variable.
        report = render_template('reports/_base_report.htm', ron=controller,
            current_ron=RonViewModel(controller), runid=root.name, config=config,
            user=principal, unitizer_nodb=Unitizer.getInstance(str(root)), precisions=precisions)
    result = {}
    for kind, content in [('run', html), ('report_shell', report)]:
        controls = Controls(); controls.feed(content)
        assert set(controls.actions) == ({'reset-lookup', 'load-extended-lookup', 'delete-extended-lookup', 'sync-base-to-extended-lookup'} if full else {'reset-lookup'})
        assert set(controls.editors) == ({'base', 'extended'} if full else {'base'})
        assert set(controls.radios) == ({'base', 'extended'} if full else set())
        result[kind] = {'actions': controls.actions, 'editors': controls.editors, 'radios': controls.radios}
    assert files(root) == before, f'{label}: rendering changed NoDb/CSV/soil files'
    receipt['layouts'][label] = result


def edit(root, variant):
    response = client.get(url(root, f'api/disturbed/lookup_snapshot?lookup={variant}'))
    assert response.status_code == 200
    snapshot = response.json['Content']
    rows = list(csv.DictReader(io.StringIO(snapshot['csv_text'])))
    index = next(i for i, row in enumerate(rows) if row['avke'].strip())
    rows[index]['avke'] = str(float(rows[index]['avke']) + 1)
    post(root, f'tasks/modify_disturbed?lookup={variant}', {'rows': rows},
         {'X-If-Match-Sha256': snapshot['lookup_sha256']})
    response = client.get(url(root, f'api/disturbed/lookup_snapshot?lookup={variant}'))
    saved = list(csv.DictReader(io.StringIO(response.json['Content']['csv_text'])))
    assert float(saved[index]['avke']) == float(rows[index]['avke'])
    assert len(saved) == len(rows)
    receipt[f'{variant}_edit'] = {'rows': len(rows), 'value_readback': saved[index]['avke'], 'sha256': response.json['Content']['lookup_sha256']}


try:
    check_layout(ROOT, 'normal_base', False)
    edit(ROOT, 'base')
    post(ROOT, 'tasks/reset_disturbed')
    assert Path(disturbed.lookup_fn).read_bytes() == Path(disturbed.default_land_soil_lookup_fn).read_bytes()
    receipt['base_reset_matches_defaults'] = True
    before = files(ROOT)
    denied = client.post(url(ROOT, 'tasks/reset_disturbed'), json={})
    assert denied.status_code == 400
    assert files(ROOT) == before
    receipt['csrf_denial_unchanged'] = True
    # Extended operations remain available to ordinary authorized callers in normal mode.
    post(ROOT, 'tasks/load_extended_land_soil_lookup')
    check_layout(ROOT, 'normal_explicit_base_with_file', False)
    post(ROOT, 'tasks/set_lookup_variant', {'lookup_variant': 'extended'})
    check_layout(ROOT, 'normal_extended', True)
    edit(ROOT, 'extended')
    shutil.copytree(ROOT, LEGACY)
    legacy = Disturbed.getInstance(str(LEGACY))
    with legacy.locked():
        del legacy._active_lookup_variant
    check_layout(LEGACY, 'legacy_no_selector', True)
    post(ROOT, 'tasks/set_lookup_variant', {'lookup_variant': 'base'})
    check_layout(ROOT, 'normal_returned_to_base', False)
    post(ROOT, 'tasks/delete_extended_land_soil_lookup')
    check_layout(ROOT, 'normal_deleted_extended', False)
    shutil.copytree(ROOT, DEVELOPER)
    before = files(DEVELOPER)
    principal.roles = ['Dev']
    post(DEVELOPER, 'tasks/enable_developer_mode')
    principal.roles = []
    after = files(DEVELOPER)
    assert {k:v for k,v in before.items() if k != 'ron.nodb'} == {k:v for k,v in after.items() if k != 'ron.nodb'}
    assert not Path(Disturbed.getInstance(str(DEVELOPER)).extended_lookup_fn).exists()
    check_layout(DEVELOPER, 'developer_base', True)
    receipt['activation_only_changed_ron'] = True
finally:
    app.login_manager._request_callback = old_loader
assert files(SOURCE) == original
receipt['source_unchanged'] = True
receipt['final_hashes'] = {p.name: files(p) for p in (ROOT, LEGACY, DEVELOPER)}
(EVIDENCE/'runtime.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt, indent=2))
