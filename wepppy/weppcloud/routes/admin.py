"""Admin-related routes blueprint extracted from app.py."""

from datetime import datetime
from glob import glob

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

from wepppy.nodb.core import Ron
from wepppy.weppcloud.utils.helpers import error_factory, get_wd, handle_with_exception_factory

from ._common import *  # noqa: F401,F403

# Blueprint for administrative tasks and support

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/runs/<string:runid>/<config>/access-log')
@login_required
@roles_required('Admin', 'Root')
@handle_with_exception_factory
def view_access_log(runid, config):
    wd = get_wd(runid)
    access_fn = wd.replace(runid, f'.{runid}').rstrip('/')

    contents = '<i>no access data available</i>'
    if _exists(access_fn):
        with open(access_fn) as fp:
            contents = fp.read()

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
        wds = [wd for wd in wds if name in Ron.getInstance(wd).name]

    return jsonify([_join('weppcloud/runs', _split(wd)[-1], Ron.getInstance(wd).config_stem) for wd in wds])
  

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
    from wepppy.weppcloud.app import get_all_runs
    user_runs = [run.meta for run in get_all_runs()]
    user_runs = [meta for meta in user_runs if meta is not None]
    user_runs.sort(key=lambda meta: meta.get('last_modified') or datetime.min, reverse=True)
    return render_template('user/runs2.html', 
                            user=current_user, 
                            user_runs=user_runs, 
                            show_owner=True)

@admin_bp.route('/tasks/usermod/', methods=['POST'])
@roles_required('Root')
@handle_with_exception_factory
def task_usermod():
    from sqlalchemy import func
    from wepppy.weppcloud.app import db, user_datastore, User
    user_id = request.json.get('user_id')
    user_email = request.json.get('user_email')
    role = request.json.get('role')
    role_state = request.json.get('role_state')

    user = None
    if user_id is not None:
        user = User.query.filter(User.id == user_id).first()
    else:
        user = User.query.filter(func.lower(User.email) == user_email.lower()).first()

    if user is None:
        return error_factory("user not found")

    if user.has_role(role) == role_state:
        return error_factory(f'{user.email} role {role} already is {role_state}')

    if role_state:
        user_datastore.add_role_to_user(user, role)
    else:
        user_datastore.remove_role_from_user(user, role)

    db.session.commit()
    return success_factory()
