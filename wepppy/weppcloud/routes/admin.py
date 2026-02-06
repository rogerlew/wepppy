"""Admin-related routes blueprint extracted from app.py."""
import html
from glob import glob

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

from wepppy.nodb.core import Ron
from wepppy.weppcloud.utils.helpers import error_factory, get_wd, handle_with_exception_factory

from ._common import *  # noqa: F401,F403

# Blueprint for administrative tasks and support

admin_bp = Blueprint('admin', __name__)

_USERMOD_ALLOWED_ROLES = {"PowerUser", "Admin", "Dev", "Root"}

@admin_bp.route('/runs/<string:runid>/<config>/access-log')
@login_required
@roles_required('Admin', 'Root')
@handle_with_exception_factory
def view_access_log(runid, config):
    wd = get_wd(runid)
    access_fn = wd.replace(runid, f'.{runid}').rstrip('/')

    if not _exists(access_fn):
        return '<!DOCTYPE html><html><i>no access data available</i></html>'

    with open(access_fn) as fp:
        contents = html.escape(fp.read())

    return f'<!DOCTYPE html><html><pre>{contents}</pre></html>'


@admin_bp.route('/dev/runid_query')
@roles_required('Admin', 'Root')
@handle_with_exception_factory
def runid_query():
    wc = request.args.get('wc', '')
    name = request.args.get('name', None)

    wds = glob(_join('/geodata/weppcloud_runs', '{}*'.format(wc)))

    wds = [wd for wd in wds if _exists(_join(wd, 'ron.nodb'))]

    if name is not None:
        wds = [wd for wd in wds if name in Ron.load_detached(wd).name]

    return jsonify([_join('weppcloud/runs', _split(wd)[-1], Ron.load_detached(wd).config_stem) for wd in wds])
  

@admin_bp.route('/usermod', strict_slashes=False)
@roles_required('Admin', 'Root')
@handle_with_exception_factory
def usermod():
    return render_template('user/usermod.html', user=current_user)


@admin_bp.route('/allruns')
@admin_bp.route('/allruns/')
@roles_required('Admin')
@handle_with_exception_factory
def allruns():
    from wepppy.weppcloud.routes.user import _normalize_direction, _normalize_sort_param

    per_page = request.args.get('per_page', 25, type=int)
    if per_page <= 0:
        per_page = 25

    sort_param = _normalize_sort_param(request.args.get('sort'))
    direction_param = _normalize_direction(request.args.get('direction') or request.args.get('order'))

    return render_template(
        'user/runs2.html',
        user=current_user,
        user_runs=[],
        show_owner=True,
        sort=sort_param,
        direction=direction_param,
        per_page=per_page,
        runs_sort_endpoint='admin.allruns',
    )

@admin_bp.route('/tasks/usermod/', methods=['POST'])
@roles_required('Root')
@handle_with_exception_factory
def task_usermod():
    from sqlalchemy import func
    from wepppy.weppcloud.app import db, user_datastore, Role, User
    user_id = request.json.get('user_id')
    user_email = request.json.get('user_email')
    role = request.json.get('role')
    role_state = request.json.get('role_state')

    if role not in _USERMOD_ALLOWED_ROLES:
        return error_factory(f"unsupported role '{role}'")

    user = None
    if user_id is not None:
        user = User.query.filter(User.id == user_id).first()
    else:
        if not user_email:
            return error_factory("user_id or user_email required")
        user = User.query.filter(func.lower(User.email) == user_email.lower()).first()

    if user is None:
        return error_factory("user not found")

    if user.has_role(role) == role_state:
        return error_factory(f'{user.email} role {role} already is {role_state}')

    if role_state:
        role_obj = Role.query.filter(Role.name == role).first()
        if role_obj is None:
            current_app.logger.warning("Role %s missing; creating on-demand via usermod.", role)
            role_obj = Role(name=role, description=f"Auto-created role {role}.")
            db.session.add(role_obj)
            db.session.flush()
        user_datastore.add_role_to_user(user, role_obj)
    else:
        user_datastore.remove_role_from_user(user, role)

    db.session.commit()
    return success_factory()
