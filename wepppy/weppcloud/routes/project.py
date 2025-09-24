"""Routes for project blueprint extracted from app.py."""

from datetime import datetime
from subprocess import PIPE, Popen

from ._common import *  # noqa: F401,F403

from sqlalchemy import func

from wepppy.nodb import Ron
from wepppy.nodb.watershed import Watershed

from wepppy.weppcloud.utils.helpers import get_run_owners_lazy, get_user_models, authorize

project_bp = Blueprint('project', __name__)


@project_bp.route('/runs/<string:runid>/<config>/tasks/clear_locks')
def clear_locks(runid, config):
    """
    Clear the nodb locks
    """
    authorize(runid, config)
    wd = get_wd(runid)
    try:
        from wepppy.nodb import clear_locks
        clear_locks(runid)
        return success_factory()
    except:
        return exception_factory('Error Clearing Locks', runid=runid)


@project_bp.route('/runs/<string:runid>/<config>/tasks/delete', methods=['POST'])
@project_bp.route('/runs/<string:runid>/<config>/tasks/delete/', methods=['POST'])
@login_required
def delete_run(runid, config):
    authorize(runid, config)
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    if ron.readonly:
        return error_factory('cannot delete readonly project')

    try:
        shutil.rmtree(wd)
    except:
        return exception_factory('Error removing project folder', runid=runid)

    try:
        Run, User, user_datastore = get_user_models()
        run = Run.query.filter(Run.runid == runid).first()
        user_datastore.delete_run(run)
    except:
        return exception_factory('Error removing run from database', runid=runid)

    return success_factory()


@project_bp.route('/runs/<string:runid>/<config>/meta/subcatchments.WGS.json')
@project_bp.route('/runs/<string:runid>/<config>/meta/subcatchments.WGS.json/')
def meta_subcatchmets_wgs(runid, config):
    from wepppy.export import arc_export

    # get working dir of original directory
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:
        arc_export(wd)

        if not request.args.get('no_retrieve', None) is not None:
            sub_fn = _join(wd, ron.export_dir, 'arcmap', 'subcatchments.WGS.json')
            return send_file(sub_fn)
        else:
            return success_factory()

    except Exception:
        return exception_factory('Error running arc_export', runid=runid)



@project_bp.route('/runs/<string:runid>/<config>/tasks/adduser/', methods=['POST'])
@login_required
def task_adduser(runid, config):
    authorize(runid, config)
    owners = get_run_owners_lazy(runid)
    try:
        Run, User, user_datastore = get_user_models()

        email = request.form.get('adduser-email')
        user = User.query.filter(func.lower(User.email) == email.lower()).first()

        if user is None:
            return error_factory('{} does not have a WeppCloud account.'
                                 .format(email))

        run = Run.query.filter(Run.runid == runid).first()

        if run is None:
            run = user_datastore.create_run(runid, config, user)

        assert user not in owners
        assert run is not None

        if not run in user.runs:
            user_datastore.add_run_to_user(user, run)

        return success_factory()
    except:
        return exception_factory(f'Error adding user: {email}', runid=runid)


@project_bp.route('/runs/<string:runid>/<config>/tasks/removeuser/', methods=['POST'])
@login_required
def task_removeuser(runid, config):
    authorize(runid, config)
    owners = get_run_owners_lazy(runid)
    try:
        Run, User, user_datastore = get_user_models()

        user_id = request.json.get('user_id')
        user = User.query.filter(User.id == user_id).first()
        run = Run.query.filter(Run.runid == runid).first()

        assert user is not None, user
        assert user in owners, user
        assert run is not None, run

        user_datastore.remove_run_to_user(user, run)

        return success_factory()
    except:
        return exception_factory(f'Error removing user: {user_id}', runid=runid)


@project_bp.route('/runs/<string:runid>/<config>/report/users/')
@login_required
def report_users(runid, config):
    authorize(runid, config)
    owners = get_run_owners_lazy(runid)
    return render_template('reports/users.htm', runid=runid, config=config, owners=owners)


# noinspection PyBroadException
@project_bp.route('/runs/<string:runid>/<config>/resources/netful.json')
def resources_netful_geojson(runid, config):
    try:
        wd = get_wd(runid)
        watershed = Watershed.getInstance(wd)
        fn = watershed.netful_shp
        return send_file(fn, mimetype='application/json')
    except Exception:
        return exception_factory(runid=runid)


# noinspection PyBroadException
@project_bp.route('/runs/<string:runid>/<config>/resources/subcatchments.json')
def resources_subcatchments_geojson(runid, config):
    try:
        wd = get_wd(runid)
        watershed = Watershed.getInstance(wd)
        fn = watershed.subwta_shp

        js = json.load(open(fn))
        ron = Ron.getInstance(wd)
        name = ron.name

        if name.strip() == '':
            js['name'] = runid
        else:
            js['name'] = name

        return jsonify(js)
    except Exception:
        return exception_factory(runid=runid)

@project_bp.route('/runs/<string:runid>/<config>/resources/bound.json')
def resources_bounds_geojson(runid, config, simplify=False):
    try:
        wd = get_wd(runid)
        watershed = Watershed.getInstance(wd)
        fn = watershed.bound_shp

        if 0:  #  disable simplify branch
            fn2 = fn.split('.')
            fn2.insert(-1, 'opt')
            fn2 = '.'.join(fn2)
            if _exists(fn2):
                return send_file(fn2)
            
            cmd = ['ogr2ogr', fn2, fn, '-simplify', '0.002']

            p = Popen(cmd, stdout=PIPE, stderr=PIPE)
            p.wait()
        else:
            fn2 = fn

        js = json.load(open(fn2))
        ron = Ron.getInstance(wd)
        name = ron.name

        js['features'] = [js['features'][0]]

        if name.strip() == '':
            js['name'] = runid
        else:
            js['name'] = name

        with open(fn2, 'w') as fp:
            json.dump(js, fp)

        return jsonify(js)
    except Exception:
        return exception_factory(runid=runid)


@project_bp.route('/runs/<string:runid>/<config>/tasks/setname/', methods=['POST'])
def task_setname(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    ron.name = request.form.get('name', 'Untitled')
    return success_factory()


@project_bp.route('/runs/<string:runid>/<config>/tasks/setscenario/', methods=['POST'])
def task_setscenario(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    ron.scenario = request.form.get('scenario', '')
    return success_factory()


@project_bp.route('/runs/<string:runid>/<config>/tasks/set_public', methods=['POST'])
@project_bp.route('/runs/<string:runid>/<config>/tasks/set_public/', methods=['POST'])
@login_required
def task_set_public(runid, config):
    authorize()
    try:
        state = request.json.get('public', None)
    except Exception:
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        ron.public = state
    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()


@project_bp.route('/runs/<string:runid>/<config>/tasks/set_readonly', methods=['POST'])
@project_bp.route('/runs/<string:runid>/<config>/tasks/set_readonly/', methods=['POST'])
@login_required
def task_set_readonly(runid, config):
    authorize(runid, config)

    try:
        state = request.json.get('readonly', None)
    except Exception:
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        ron.readonly = state
    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()
