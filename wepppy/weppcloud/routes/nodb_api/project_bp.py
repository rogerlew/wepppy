"""Routes for project blueprint extracted from app.py."""

from datetime import datetime
from subprocess import PIPE, Popen
import redis
from rq import Queue

from .._common import *  # noqa: F401,F403

from sqlalchemy import func

from wepppy.nodb.core import Ron
from wepppy.nodb.base import clear_nodb_file_cache
from wepppy.nodb.core import Watershed

from wepppy.weppcloud.utils.helpers import (
    success_factory, error_factory, exception_factory,
    get_run_owners_lazy, get_user_models, authorize, 
    authorize_and_handle_with_exception_factory
) 


project_bp = Blueprint('project', __name__)


@project_bp.route('/runs/<string:runid>/<config>/tasks/clear_locks')
@authorize_and_handle_with_exception_factory
def clear_locks(runid, config):
    """
    Clear the nodb locks
    """
    load_run_context(runid, config)
    from wepppy.nodb.base import clear_locks
    clear_locks(runid)
    return success_factory()


@project_bp.route('/runs/<string:runid>/<config>/tasks/clear_nodb_cache')
@authorize_and_handle_with_exception_factory
def clear_nodb_cache(runid, config):
    """Clear cached NoDb payloads for the active run."""
    load_run_context(runid, config)
    try:
        cleared = clear_nodb_file_cache(runid)
    except FileNotFoundError as exc:
        return error_factory(str(exc)), 404
    except RuntimeError as exc:
        return error_factory(str(exc)), 503
    cleared_entries = [str(path) for path in cleared]
    return success_factory({'cleared_entries': cleared_entries})


@project_bp.route('/runs/<string:runid>/<config>/tasks/delete', methods=['POST'])
@project_bp.route('/runs/<string:runid>/<config>/tasks/delete/', methods=['POST'])
@login_required
def delete_run(runid, config):
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
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
@authorize_and_handle_with_exception_factory
def meta_subcatchmets_wgs(runid, config):
    from wepppy.export import arc_export
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)
    arc_export(wd)

    if not request.args.get('no_retrieve', None) is not None:
        sub_fn = _join(wd, ron.export_dir, 'arcmap', 'subcatchments.WGS.json')
        return send_file(sub_fn)
    else:
        return success_factory()


@project_bp.route('/runs/<string:runid>/<config>/tasks/adduser/', methods=['POST'])
@login_required
def task_adduser(runid, config):
    authorize(runid, config)
    load_run_context(runid, config)
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
    load_run_context(runid, config)
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
    load_run_context(runid, config)
    owners = get_run_owners_lazy(runid)
    return render_template('reports/users.htm', runid=runid, config=config, owners=owners)


# noinspection PyBroadException
@project_bp.route('/runs/<string:runid>/<config>/resources/netful.json')
@authorize_and_handle_with_exception_factory
def resources_netful_geojson(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    watershed = Watershed.getInstance(wd)
    fn = watershed.netful_shp
    return send_file(fn, mimetype='application/json')


# noinspection PyBroadException
@project_bp.route('/runs/<string:runid>/<config>/resources/subcatchments.json')
@authorize_and_handle_with_exception_factory
def resources_subcatchments_geojson(runid, config):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
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

@project_bp.route('/runs/<string:runid>/<config>/resources/bound.json')
@authorize_and_handle_with_exception_factory
def resources_bounds_geojson(runid, config, simplify=False):
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
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


@project_bp.route('/runs/<string:runid>/<config>/tasks/setname/', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_setname(runid, config):
    ctx = load_run_context(runid, config)
    ron = Ron.getInstance(str(ctx.active_root))
    ron.name = request.form.get('name', 'Untitled')
    return success_factory()


@project_bp.route('/runs/<string:runid>/<config>/tasks/setscenario/', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_setscenario(runid, config):
    ctx = load_run_context(runid, config)
    ron = Ron.getInstance(str(ctx.active_root))
    ron.scenario = request.form.get('scenario', '')
    return success_factory()


@project_bp.route('/runs/<string:runid>/<config>/tasks/set_public', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_set_public(runid, config):
    try:
        state = request.json.get('public', None)
    except Exception:
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        ctx = load_run_context(runid, config)
        Ron.getInstance(str(ctx.active_root)).public = bool(state)
    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()


@project_bp.route('/runs/<string:runid>/<config>/tasks/set_readonly', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_set_readonly(runid, config):
    from wepppy.rq.project_rq import (
        set_run_readonly_rq,
        REDIS_HOST,
        RQ_DB,
        TIMEOUT,
    )

    try:
        state = request.json.get('readonly', None)
    except Exception:
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        load_run_context(runid, config)
        desired_state = bool(state)

        with redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB) as redis_conn:
            queue = Queue(connection=redis_conn)
            job = queue.enqueue_call(set_run_readonly_rq, (runid, desired_state), timeout=TIMEOUT)
    except Exception:
        return exception_factory('Error queuing readonly task', runid=runid)

    return jsonify({'Success': True, 'job_id': job.id})
