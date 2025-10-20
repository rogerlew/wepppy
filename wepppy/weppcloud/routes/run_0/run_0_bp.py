"""Routes for wepp blueprint extracted from app.py."""

import wepppy
import pathlib

from datetime import datetime
import awesome_codename

from .._common import *  # noqa: F401,F403

import wepppy
from wepppy.all_your_base import isint
from wepppy.nodb.base import get_configs
from wepppy.nodb.core import * 
from wepppy.nodb.unitizer import Unitizer
from wepppy.nodb.mods.observed import Observed
from wepppy.nodb.mods.rangeland_cover import RangelandCover
from wepppy.nodb.mods.rhem import Rhem
from wepppy.nodb.mods.treatments import Treatments
from wepppy.nodb.mods.ash_transport import Ash
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.omni import Omni, OmniScenario
from wepppy.nodb.core.climate import Climate
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.weppcloud.routes.nodb_api.landuse_bp import build_landuse_report_context
from wepppy.weppcloud.utils.helpers import (
    get_wd, authorize, get_run_owners_lazy, 
    authorize_and_handle_with_exception_factory,
    handle_with_exception_factory
)


run_0_bp = Blueprint('run_0', __name__,
                     template_folder='templates')

VAPID_PUBLIC_KEY = ''
_VAPID_PATH = pathlib.Path('/workdir/weppcloud2/microservices/wepppush/vapid.json')
if _VAPID_PATH.exists():
    with _VAPID_PATH.open() as fp:
        vapid = json.load(fp)
        VAPID_PUBLIC_KEY = vapid.get('publicKey', '')

TOC_TASK_ANCHOR_TO_TASK = {
    '#map': TaskEnum.fetch_dem,
    '#soil-burn-severity': TaskEnum.init_sbs_map,
    '#soil-burn-severity-optional': TaskEnum.init_sbs_map,
    '#channel-delineation': TaskEnum.build_channels,
    '#outlet': TaskEnum.set_outlet,
    '#subcatchments-delineation': TaskEnum.build_subcatchments,
    '#landuse-options': TaskEnum.build_landuse,
    '#landuse-report': TaskEnum.build_landuse,
    '#soil-options': TaskEnum.build_soils,
    '#climate': TaskEnum.build_climate,
    '#rap-time-series-acquisition': TaskEnum.fetch_rap_ts,
    '#wepp': TaskEnum.run_wepp_watershed,
    '#observed-data-model-fit': TaskEnum.run_observed,
    '#debris-flow-analysis': TaskEnum.run_debris,
    '#wildfire-ash-transport-and-risk-watar': TaskEnum.run_watar,
    '#rhem': TaskEnum.run_rhem,
    '#omni-scenario-runner': TaskEnum.run_omni_scenarios,
    '#omni-contrast-definitions': TaskEnum.run_omni_contrasts,
    '#partitioned-dss-export-for-hec': TaskEnum.dss_export,
    '#export': TaskEnum.dss_export,
}

TOC_TASK_EMOJI_MAP = {anchor: task.emoji() for anchor, task in TOC_TASK_ANCHOR_TO_TASK.items()}

@run_0_bp.route('/sw.js')
def service_worker():
    from flask import make_response, send_from_directory
    response = make_response(send_from_directory('static/js', 'webpush_service_worker.js'))
    response.headers['Service-Worker-Allowed'] = '/'
    return response


# Redirect to the correct to the full run path
@run_0_bp.route('/runs/<string:runid>/')
@handle_with_exception_factory
def runs0_nocfg(runid):
    run_root = pathlib.Path(get_wd(runid)).resolve()
    pup_relpath = request.args.get('pup')
    active_root = run_root

    if pup_relpath:
        pups_root = (run_root / '_pups').resolve()
        candidate = (pups_root / pup_relpath).resolve()
        try:
            candidate.relative_to(pups_root)
        except ValueError:
            abort(404)

        if not candidate.is_dir():
            abort(404)

        active_root = candidate

    try:
        ron = Ron.getInstance(str(active_root))
    except FileNotFoundError:
        abort(404)

    target_args = {'runid': runid, 'config': ron.config_stem}
    if pup_relpath:
        target_args['pup'] = pup_relpath

    return redirect(url_for_run('run_0.runs0', **target_args))

def _log_access(wd, current_user, ip):
    assert _exists(wd)

    fn, runid = _split(wd.rstrip('/'))
    fn = _join(fn, '.{}'.format(runid))
    with open(fn, 'a') as fp:
        email = getattr(current_user, 'email', '<anonymous>')
        fp.write('{},{},{}\n'.format(email, ip, datetime.now()))

@run_0_bp.route('/runs/<string:runid>/<config>/')
@authorize_and_handle_with_exception_factory
def runs0(runid, config):
    global VAPID_PUBLIC_KEY
    from wepppy.nodb.mods.revegetation import Revegetation
    from wepppy.wepp.soils import soilsdb
    from wepppy.wepp import management
    from wepp_runner.wepp_runner import linux_wepp_bin_opts
    from wepppy.wepp.management.managements import landuse_management_mapping_options
    from wepppy.weppcloud.app import db, Run

    assert config is not None

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    base_wd = str(ctx.run_root)
    ron = Ron.getInstance(wd)

    # check config from url matches config from Ron
    if config != ron.config_stem:
        target_args = {'runid': runid, 'config': ron.config_stem}
        if ctx.pup_relpath:
            target_args['pup'] = ctx.pup_relpath
        return redirect(url_for_run('run_0.runs0', **target_args))

    if ctx.pup_root and not ron.readonly:
        try:
            ron.readonly = True
        except Exception as exc:
            current_app.logger.warning('Failed to mark pup project as readonly: %s', exc)

    # return jsonify({'wd': wd, 'base_wd': base_wd, 'runid': runid, 'config': config, 'pup_relpath': ctx.pup_relpath})
    # https://wc.bearhive.duckdns.org/runs/considerable-imperative/disturbed9002/?pup=omni/scenarios/undisturbed
    # {
    # "base_wd": "/wc1/runs/co/considerable-imperative",
    # "config": "disturbed9002",
    # "pup_relpath": "omni/scenarios/undisturbed",
    # "runid": "considerable-imperative",
    # "wd": "/wc1/runs/co/considerable-imperative/_pups/omni/scenarios/undisturbed"
    # }
    
    landuse = Landuse.getInstance(wd)
    soils = Soils.getInstance(wd)
    climate = Climate.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    watershed = Watershed.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)
    site_prefix = current_app.config['SITE_PREFIX']

    if watershed.delineation_backend_is_topaz:
        topaz = Topaz.getInstance(wd)
    else:
        topaz = None

    observed = Observed.tryGetInstance(wd)
    rangeland_cover = RangelandCover.tryGetInstance(wd)
    rhem = Rhem.tryGetInstance(wd)
    disturbed = Disturbed.tryGetInstance(wd)
    ash = Ash.tryGetInstance(wd)
    skid_trails = wepppy.nodb.mods.SkidTrails.tryGetInstance(wd)
    reveg = Revegetation.tryGetInstance(wd)
    omni = Omni.tryGetInstance(wd)
    treatments = Treatments.tryGetInstance(wd)
    redis_prep = RedisPrep.tryGetInstance(wd)
    
    if redis_prep is not None:
        rq_job_ids = redis_prep.get_rq_job_ids()
    else:
        rq_job_ids = {}

    landuseoptions = landuse.landuseoptions
    landuse_report_context = build_landuse_report_context(landuse)
    soildboptions = soilsdb.load_db()

    critical_shear_options = management.load_channel_d50_cs()


    _log_access(base_wd, current_user, request.remote_addr)
    timestamp = datetime.now()
    Run.query.filter_by(runid=runid).update({'last_accessed': timestamp})
    db.session.commit()

    return render_template('runs0_pure.htm',
                            user=current_user,
                            site_prefix=site_prefix,
                            topaz=topaz,
                            soils=soils,
                            ron=ron,
                            landuse=landuse,
                            climate=climate,
                            wepp=wepp,
                            wepp_bin_opts=linux_wepp_bin_opts,
                            rhem=rhem,
                            disturbed=disturbed,
                            ash=ash,
                            skid_trails=skid_trails,
                            reveg=reveg,
                            watershed=watershed,
                            unitizer_nodb=unitizer,
                            observed=observed,
                            rangeland_cover=rangeland_cover,
                            omni=omni,
                            OmniScenario=OmniScenario,
                            treatments=treatments,
                            rq_job_ids=rq_job_ids,
                            landuseoptions=landuseoptions,
                            landcover_datasets=landuse.landcover_datasets,
                            landuse_report_rows=landuse_report_context['report_rows'],
                            landuse_dataset_options=landuse_report_context['dataset_options'],
                            landuse_coverage_percentages=landuse_report_context['coverage_percentages'],
                            landuse_management_mapping_options=landuse_management_mapping_options,
                            soildboptions=soildboptions,
                            critical_shear_options=critical_shear_options,
                            climate_catalog=climate.catalog_datasets_payload(include_hidden=True),
                            precisions=wepppy.nodb.unitizer.precisions,
                            run_id=runid,
                            runid=runid,
                            config=config,
                            toc_task_emojis=TOC_TASK_EMOJI_MAP,
                            pup_relpath=ctx.pup_relpath,
                            VAPID_PUBLIC_KEY=VAPID_PUBLIC_KEY)

@run_0_bp.route('/create', strict_slashes=False)
@handle_with_exception_factory
def create_index():
    configs = get_configs()
    rows = []
    for cfg in sorted(configs):
        if cfg == '_defaults':
            continue

        base_url = url_for_run('run_0.create', config=cfg)
        rows.append(
            '<tr>'
            f'<td><a href="{base_url}" rel="nofollow">{cfg}</a></td>'
            f'<td><a href="{base_url}?general:dem_db=ned1/2016" rel="nofollow">{cfg} ned1/2016</a></td>'
            f'<td><a href="{base_url}?watershed:delineation_backend=wbt" rel="nofollow">{cfg} WhiteBoxTools</a></td>'
            '</tr>'
        )

    bootstrap_css = url_for('static', filename='vendor/bootstrap/bootstrap.css')
    return (
        '<!DOCTYPE html><html><body>'
        f'<link rel="stylesheet" href="{bootstrap_css}">'
        '\n<table class="table">{}</table>\n</body></html>'
    ).format('\n'.join(rows))

def create_run_dir(current_user):
    from wepppy.weppcloud.utils.archive import has_archive
    wd = None
    dir_created = False
    while not dir_created:
        runid = awesome_codename.generate_codename().replace(' ', '-').replace("'", '')

        email = getattr(current_user, 'email', '')
        if email.startswith('mdobre@'):
            runid = 'mdobre-' + runid
        elif email.startswith('srivas42@'):
            runid = 'srivas42-' + runid

        wd = get_wd(runid)
        if _exists(wd):
            continue

        if has_archive(runid):
            continue

        os.makedirs(wd)
        dir_created = True

    return runid, wd


@run_0_bp.route('/create/<config>')
@handle_with_exception_factory
def create(config):
    from wepppy.weppcloud.routes.readme_md import ensure_readme_on_create
    cfg = "%s.cfg" % config

    overrides = '&'.join(['{}={}'.format(k, v) for k, v in request.args.items()])

    if len(overrides) > 0:
        cfg += '?%s' % overrides

    try:
        runid, wd = create_run_dir(current_user)
    except PermissionError:
        return exception_factory('Could not create run directory. NAS may be down.')
    except Exception:
        return exception_factory('Could not create run directory.')

    try:
        Ron(wd, cfg)
    except Exception:
        return exception_factory('Could not create run')

    if not current_user.is_anonymous:
        from wepppy.weppcloud.app import user_datastore
        user_datastore.create_run(runid, config, current_user)

    ensure_readme_on_create(runid, config)

    return redirect(url_for_run('run_0.runs0', runid=runid, config=config))
