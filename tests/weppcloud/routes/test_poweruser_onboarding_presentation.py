"""Role and empty-state rendering for the PowerUser acquisition journey."""
from types import SimpleNamespace

import pytest
from tests.weppcloud.routes.test_pure_controls_render import jinja_env

pytestmark = pytest.mark.routes


def viewer(role=None):
    return SimpleNamespace(is_authenticated=role != 'anonymous',
                           roles=[role] if role else [], has_role=lambda name: name == role)


def access(*, role=False, accepted=False, memberships=(), error=None):
    return dict(error_id=error, poweruser=dict(has_role=role, accepted=accepted),
                poweruser_version='v1', poweruser_statement='Responsibilities',
                memberships=list(memberships), acknowledged=False, statement='Internal', version='v1')


@pytest.mark.parametrize('role,visible', [(None, True), ('Dev', True), ('PowerUser', False),
                                         ('Admin', False), ('Root', False), ('anonymous', False)])
def test_runs_notice_uses_viewer_not_catalog_owner(jinja_env, role, visible):
    html = jinja_env.get_template('user/runs2.html').render(
        current_user=viewer(role), user=viewer('PowerUser'), user_runs=[],
        selected_alias='different-owner', show_owner=False)
    assert ('id="advanced-features-heading"' in html) is visible
    if visible:
        assert html.index('advanced-features-heading') < html.index('id="runs-table-view"')
        assert '#poweruser-access-heading' in html


@pytest.mark.parametrize('role', ['Admin', 'Root'])
def test_operational_roles_do_not_acquire_literal_poweruser(jinja_env, role):
    html = jinja_env.get_template('user/_poweruser_access.html').render(
        user=viewer(role), internal_access=access())
    assert 'already provides these tools' in html
    assert 'data-feature-access-form' not in html
    assert 'PowerUser access is active.' not in html
    assert 'Open Config Builder' in html


def test_legacy_poweruser_needs_no_new_acceptance(jinja_env):
    html = jinja_env.get_template('user/_poweruser_access.html').render(
        user=viewer('PowerUser'), internal_access=access(role=True))
    assert 'No action is required' in html
    assert 'Go to Runs' in html
    assert 'data-feature-access-form' not in html


@pytest.mark.parametrize('role', [None, 'Admin', 'PowerUser'])
def test_unavailable_access_is_not_empty_or_active(jinja_env, role):
    html = jinja_env.get_template('user/_poweruser_access.html').render(
        user=viewer(role), internal_access=access(error='test-error'))
    assert 'temporarily unavailable' in html
    assert 'data-feature-access-form' not in html
    assert 'Open Config Builder' not in html


@pytest.mark.parametrize('memberships,open_details', [([], False),
    ([dict(label='Example', key='example', active=True, unexpired=True)], True),
    ([dict(label='Expired', key='example', active=True, unexpired=False)], True)])
def test_internal_statement_remains_reachable_without_grant(jinja_env, memberships, open_details):
    html = jinja_env.get_template('user/_internal_access.html').render(
        user=viewer(), internal_access=access(memberships=memberships))
    assert ('<details open>' in html) is open_details
    assert 'data-feature-access-form="acknowledgment"' in html
    assert 'Accept internal access statement' in html


@pytest.mark.parametrize('role,visible', [(None, False), ('anonymous', False), ('Dev', False),
                                         ('PowerUser', True), ('Admin', True), ('Root', True)])
def test_report_trigger_matches_guarded_panel(jinja_env, role, visible):
    html = jinja_env.get_template('reports/_base_report.htm').render(
        user=viewer(role), current_user=viewer(role))
    assert ('data-modal-open="puModal"' in html) is visible
    assert ('id="puModal"' in html) is visible
