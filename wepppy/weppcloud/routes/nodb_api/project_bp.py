"""Routes for project blueprint extracted from app.py."""

from datetime import datetime
from subprocess import PIPE, Popen
import redis
from rq import Queue
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
)

from .._common import *  # noqa: F401,F403

from sqlalchemy import func

from wepppy.nodb.core import Ron
from wepppy.nodb.base import clear_nodb_file_cache, iter_nodb_mods_subclasses
from wepppy.nodb.core import Watershed

from wepppy.weppcloud.utils.helpers import (
    success_factory, error_factory, exception_factory,
    get_run_owners_lazy, get_user_models, authorize, 
    authorize_and_handle_with_exception_factory
) 


project_bp = Blueprint('project', __name__)

MOD_DISPLAY_NAMES = {
    'rap_ts': 'RAP Time Series',
    'ash': 'Ash Transport',
    'treatments': 'Treatments',
    'observed': 'Observed Data',
    'debris_flow': 'Debris Flow',
    'dss_export': 'DSS Export',
    'omni': 'Omni',
    'path_ce': 'Path CE',
}

MOD_DEPENDENCIES = {
    'omni': ['treatments'],
}

MOD_DISABLE_GUARDS = {
    'treatments': ['omni'],
}


def _append_mod(ron: Ron, mod_name: str) -> bool:
    """Ensure ``mod_name`` is recorded on the project. Returns True when added."""
    current_mods = list(ron.mods or [])
    if mod_name in current_mods:
        return False

    with ron.locked():
        mods = ron.mods
        if mods is None:
            ron._mods = [mod_name]
        elif mod_name not in mods:
            ron._mods.append(mod_name)
            current_mods = ron._mods

    return mod_name in (ron.mods or [])


def _instantiate_mod_if_available(wd: str, cfg_fn: str, mod_name: str) -> bool:
    """Instantiate the NoDb controller when a matching subclass exists."""
    registry = {name: cls for name, cls in iter_nodb_mods_subclasses()}
    cls = registry.get(mod_name)
    if cls is None:
        return False
    cls(wd, cfg_fn)
    return True


def _enable_mod_for_run(ron: Ron, wd: str, cfg_fn: str, mod_name: str) -> bool:
    """Add the mod (and dependencies) then materialize their controllers."""
    changed = _append_mod(ron, mod_name)

    for dependency in MOD_DEPENDENCIES.get(mod_name, []):
        dependency_added = _append_mod(ron, dependency)
        if dependency_added:
            _instantiate_mod_if_available(wd, cfg_fn, dependency)

    _instantiate_mod_if_available(wd, cfg_fn, mod_name)
    return changed


def _disable_mod_for_run(ron: Ron, mod_name: str) -> bool:
    """Remove a mod when doing so will not violate dependency guards."""
    active_mods = set(ron.mods or [])
    blockers = [
        blocker for blocker in MOD_DISABLE_GUARDS.get(mod_name, [])
        if blocker in active_mods
    ]
    if blockers:
        pretty = ", ".join(sorted(MOD_DISPLAY_NAMES.get(b, b) for b in blockers))
        label = MOD_DISPLAY_NAMES.get(mod_name, mod_name)
        raise ValueError(f"Disable {pretty} before removing {label}.")

    if mod_name not in active_mods:
        return False

    ron.remove_mod(mod_name)
    return True


def set_project_mod_state(runid: str, config: str, mod_name: str, enabled: bool) -> dict:
    """Toggle a project mod and return the updated state payload."""
    if mod_name not in MOD_DISPLAY_NAMES:
        raise ValueError(f"Unknown module '{mod_name}'.")

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)
    cfg_fn = f"{config}.cfg"

    if enabled:
        changed = _enable_mod_for_run(ron, wd, cfg_fn, mod_name)
    else:
        changed = _disable_mod_for_run(ron, mod_name)

    return {
        "mod": mod_name,
        "enabled": enabled,
        "changed": bool(changed),
        "mods": list(ron.mods or []),
        "label": MOD_DISPLAY_NAMES.get(mod_name, mod_name),
    }


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
    owners = list(get_run_owners_lazy(runid) or [])
    email = None
    try:
        Run, User, user_datastore = get_user_models()
        payload = parse_request_payload(request, trim_strings=True)

        email = payload.get('email')
        if email in (None, ''):
            email = payload.get('adduser-email')
        if isinstance(email, list):
            email = email[0]
        if email is None:
            return error_factory('Email address is required.')
        email = str(email).strip()
        if not email:
            return error_factory('Email address is required.')

        user = None
        if hasattr(user_datastore, 'find_user'):
            try:
                user = user_datastore.find_user(email=email)
            except Exception:
                user = None

        if user is None:
            try:
                user = User.query.filter(func.lower(User.email) == email.lower()).first()
            except Exception:
                user = None

        if user is None:
            return error_factory(f'{email} does not have a WeppCloud account.')

        try:
            run = Run.query.filter(Run.runid == runid).first()
        except Exception:
            run = None

        if run is None:
            run = user_datastore.create_run(runid, config, user)

        if user in owners:
            if run and run not in getattr(user, 'runs', []):
                user_datastore.add_run_to_user(user, run)
            return success_factory({
                'already_member': True,
                'user_id': getattr(user, 'id', None),
                'email': getattr(user, 'email', email)
            })

        if run not in getattr(user, 'runs', []):
            user_datastore.add_run_to_user(user, run)

        return success_factory({
            'user_id': getattr(user, 'id', None),
            'email': getattr(user, 'email', email)
        })
    except Exception:
        return exception_factory(f'Error adding user: {email}', runid=runid)


@project_bp.route('/runs/<string:runid>/<config>/tasks/removeuser/', methods=['POST'])
@login_required
def task_removeuser(runid, config):
    authorize(runid, config)
    load_run_context(runid, config)
    owners = list(get_run_owners_lazy(runid) or [])
    user_id = None
    try:
        Run, User, user_datastore = get_user_models()
        payload = parse_request_payload(request, trim_strings=True)

        user_id = payload.get('user_id')
        if user_id in (None, ''):
            user_id = payload.get('user-id')
        if isinstance(user_id, list):
            user_id = user_id[0]
        if user_id is None or (isinstance(user_id, str) and not user_id.strip()):
            return error_factory('user_id is required.')

        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return error_factory('user_id must be an integer.')

        try:
            user = User.query.filter(User.id == user_id).first()
        except Exception:
            user = None

        if user is None:
            return error_factory(f'User {user_id} not found.')

        try:
            run = Run.query.filter(Run.runid == runid).first()
        except Exception:
            run = None

        if run is None:
            return error_factory('Project run not found.')

        if owners and user not in owners:
            return error_factory('User is not a collaborator on this project.')

        if run not in getattr(user, 'runs', []):
            return success_factory({
                'already_removed': True,
                'user_id': user_id
            })

        user_datastore.remove_run_to_user(user, run)

        return success_factory({'user_id': user_id})
    except Exception:
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
    payload = parse_request_payload(request)
    raw_name = payload.get('name', '')
    name = str(raw_name).strip() if raw_name is not None else ''
    if not name:
        name = 'Untitled'
    ron.name = name
    return success_factory({'name': name})


@project_bp.route('/runs/<string:runid>/<config>/tasks/setscenario/', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_setscenario(runid, config):
    ctx = load_run_context(runid, config)
    ron = Ron.getInstance(str(ctx.active_root))
    payload = parse_request_payload(request)
    raw_scenario = payload.get('scenario', '')
    scenario = str(raw_scenario).strip() if raw_scenario is not None else ''
    ron.scenario = scenario
    return success_factory({'scenario': scenario})


@project_bp.route('/runs/<string:runid>/<config>/tasks/set_public', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_set_public(runid, config):
    payload = parse_request_payload(request, boolean_fields={'public'})
    state = payload.get('public', None)

    if state is None:
        return error_factory('state is None')
    if isinstance(state, str):
        return error_factory('state must be boolean')

    try:
        ctx = load_run_context(runid, config)
        Ron.getInstance(str(ctx.active_root)).public = bool(state)
    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory({'public': bool(state)})


@project_bp.route('/runs/<string:runid>/<config>/tasks/set_readonly', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_set_readonly(runid, config):
    from wepppy.rq.project_rq import (
        set_run_readonly_rq,
        TIMEOUT,
    )

    payload = parse_request_payload(request, boolean_fields={'readonly'})
    state = payload.get('readonly', None)

    if state is None:
        return error_factory('state is None')
    if isinstance(state, str):
        return error_factory('state must be boolean')

    try:
        load_run_context(runid, config)
        desired_state = bool(state)

        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
            queue = Queue(connection=redis_conn)
            job = queue.enqueue_call(set_run_readonly_rq, (runid, desired_state), timeout=TIMEOUT)
    except Exception:
        return exception_factory('Error queuing readonly task', runid=runid)

    return success_factory({'readonly': desired_state, 'job_id': job.id})


@project_bp.route('/runs/<string:runid>/<config>/tasks/set_mod', methods=['POST'])
@project_bp.route('/runs/<string:runid>/<config>/tasks/set_mod/', methods=['POST'])
@authorize_and_handle_with_exception_factory
def task_set_mod(runid, config):
    payload = parse_request_payload(request, trim_strings=True, boolean_fields={'enabled'})
    mod_name = payload.get('mod')
    enabled = payload.get('enabled')

    if mod_name in (None, ''):
        return error_factory('mod is required')
    if enabled is None or isinstance(enabled, str):
        return error_factory('enabled must be boolean')

    mod_key = str(mod_name).strip()
    try:
        state = set_project_mod_state(runid, config, mod_key, bool(enabled))
    except ValueError as exc:
        return error_factory(str(exc))
    except Exception:
        return exception_factory('Error updating module state', runid=runid)

    return success_factory(state)
