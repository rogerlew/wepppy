"""Admin-related routes blueprint extracted from app.py."""

from glob import glob

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

from wepppy.nodb import Ron
from wepppy.weppcloud.utils.helpers import error_factory, get_wd

from ._common import *  # noqa: F401,F403


admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/runs/<string:runid>/<config>/access-log')
@admin_bp.route('/runs/<string:runid>/<config>/access-log/')
@login_required
def view_access_log(runid, config):
    if current_user.has_role('Admin'):
        should_abort = False

    if should_abort:
        abort(403)

    wd = get_wd(runid)
    access_fn = wd.replace(runid, f'.{runid}').rstrip('/')

    contents = '<i>no access data available</i>'
    if _exists(access_fn):
        with open(access_fn) as fp:
            contents = fp.read()

    return f'<!DOCTYPE html><html><pre>{contents}</pre></html>'


@admin_bp.route('/dev/runid_query/')
def runid_query():
    if current_user.has_role('Root') or \
       current_user.has_role('Admin') or \
       current_user.has_role('Dev'):

        wc = request.args.get('wc', '')
        name = request.args.get('name', None)

        wds = glob(_join('/geodata/weppcloud_runs', '{}*'.format(wc)))

        wds = [wd for wd in wds if _exists(_join(wd, 'ron.nodb'))]

        if name is not None:
            wds = [wd for wd in wds if name in Ron.getInstance(wd).name]

        return jsonify([_join('weppcloud/runs', _split(wd)[-1], Ron.getInstance(wd).config_stem) for wd in wds])
    else:
        return error_factory('not authorized')


@admin_bp.route('/usermod', strict_slashes=False)
@roles_required('Root')
def usermod():
    try:
        return render_template('user/usermod.html', user=current_user)
    except:
        return exception_factory()


@admin_bp.route('/allruns')
@admin_bp.route('/allruns/')
@roles_required('Admin')
def allruns():
    try:
        user_runs = [run.meta for run in _get_all_runs()]
        user_runs = [meta for meta in user_runs if meta is not None]
        user_runs.sort(key=lambda meta: meta['last_modified'], reverse=True)

        return render_template('user/runs.html', 
                               user=current_user, 
                               user_runs=user_runs, 
                               show_owner=True)
    except:
        return exception_factory()


@admin_bp.route('/tasks/usermod/', methods=['POST'])
@roles_required('Root')
def task_usermod():
    try:
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
            return error_factory('{} role {} already is {}'
                                 .format(user.email, role, role_state))

        if role_state:
            user_datastore.add_role_to_user(user, role)
        else:
            user_datastore.remove_role_from_user(user, role)

        db.session.commit()
        return success_factory()
    except:
        return exception_factory()

