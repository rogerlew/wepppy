"""DM-02 project/report presentation uses real persisted lookup selection."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.weppcloud.routes.test_pure_controls_render import jinja_env
from wepppy.nodb.core.ron import Ron
from wepppy.nodb.mods.disturbed import Disturbed

pytestmark = [pytest.mark.routes, pytest.mark.integration]


@pytest.mark.parametrize('template_name', ['controls/disturbed_modal.htm', 'reports/_base_report.htm'])
@pytest.mark.parametrize('developer,stored_variant,file_content,full', [
    (False, 'base', None, False),
    (False, 'base', 'legacy extended', False),
    (False, 'extended', 'legacy extended', True),
    (False, 'extended', '', True),
    (False, 'extended', None, True),
    (False, None, 'legacy extended', True),
    (False, 'legacy-invalid', 'legacy extended', True),
    (False, None, None, False),
    (True, 'base', None, True),
])
def test_disturbed_panel_uses_existing_state_without_template_context(
    jinja_env, tmp_path, template_name, developer, stored_variant, file_content, full,
):
    from wepppy.weppcloud._context_processors import _disturbed_lookup_variant

    ron = Ron(str(tmp_path), 'disturbed9002.cfg', initialize_components=False)
    disturbed = Disturbed(str(tmp_path), 'disturbed9002.cfg')
    with disturbed.locked():
        disturbed._active_lookup_variant = stored_variant
    if file_content is not None:
        Path(disturbed.extended_lookup_fn).write_text(file_content)
    if developer:
        ron.enable_developer_mode()
    # Read from the actual page controller's root, not a separate runid lookup.
    with ron.locked():
        ron._mods = ['disturbed']
    before = {str(p.relative_to(tmp_path)): p.read_bytes()
              for p in tmp_path.rglob('*') if p.is_file()}
    jinja_env.globals['disturbed_lookup_variant'] = _disturbed_lookup_variant
    user = SimpleNamespace(has_role=lambda role: False, roles=[], is_authenticated=True)
    html = jinja_env.get_template(template_name).render(ron=ron, user=user, current_user=user)
    assert 'data-disturbed-action="reset-lookup"' in html
    assert 'data-disturbed-modify-link="base"' in html
    assert ('data-disturbed-action="load-extended-lookup"' in html) is full
    assert ('data-disturbed-action="delete-extended-lookup"' in html) is full
    assert ('data-disturbed-action="sync-base-to-extended-lookup"' in html) is full
    assert ('data-disturbed-modify-link="extended"' in html) is full
    assert ('id="disturbed_lookup_variant_extended"' in html) is full
    after = {str(p.relative_to(tmp_path)): p.read_bytes()
             for p in tmp_path.rglob('*') if p.is_file()}
    assert after == before


def test_missing_disturbed_is_not_created_and_dev_role_alone_is_not_policy(jinja_env, tmp_path):
    from wepppy.weppcloud._context_processors import _disturbed_lookup_variant

    ron = Ron(str(tmp_path), 'disturbed9002.cfg', initialize_components=False)
    with ron.locked():
        ron._mods = ['disturbed']
    jinja_env.globals['disturbed_lookup_variant'] = _disturbed_lookup_variant
    user = SimpleNamespace(has_role=lambda role: role == 'Dev', roles=['Dev'], is_authenticated=True)
    html = jinja_env.get_template('reports/_base_report.htm').render(ron=ron, user=user, current_user=user)
    assert 'data-disturbed-action="reset-lookup"' in html
    assert 'data-disturbed-action="load-extended-lookup"' not in html
    assert not (tmp_path / 'disturbed.nodb').exists()


def test_supplied_disturbed_context_needs_no_additional_read(jinja_env):
    def unexpected_read(_wd):
        raise AssertionError('existing page context must be reused')
    jinja_env.globals['disturbed_lookup_variant'] = unexpected_read
    ron = SimpleNamespace(developer_mode=False, mods=['disturbed'], runid='r', config_stem='c')
    html = jinja_env.get_template('controls/disturbed_modal.htm').render(
        ron=ron, disturbed=SimpleNamespace(active_lookup_variant='extended'))
    assert 'data-disturbed-action="load-extended-lookup"' in html


def test_corrupt_disturbed_state_is_not_treated_as_base(tmp_path):
    from wepppy.weppcloud._context_processors import _disturbed_lookup_variant

    Ron(str(tmp_path), 'disturbed9002.cfg', initialize_components=False)
    path = tmp_path / 'disturbed.nodb'
    path.write_text('{}')
    with pytest.raises(TypeError, match='Decoded object type'):
        _disturbed_lookup_variant(str(tmp_path))
    assert path.read_text() == '{}'


def test_disabled_module_does_not_resolve_disturbed(jinja_env):
    def unexpected_read(_wd):
        raise AssertionError('disabled module must not load state')
    jinja_env.globals['disturbed_lookup_variant'] = unexpected_read
    html = jinja_env.get_template('controls/disturbed_modal.htm').render(
        ron=SimpleNamespace(mods=[], developer_mode=False))
    assert 'id="disturbedModal"' not in html
