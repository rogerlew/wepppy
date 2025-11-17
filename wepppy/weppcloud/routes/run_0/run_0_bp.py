"""Routes for wepp blueprint extracted from app.py."""

import wepppy
import pathlib
from collections import OrderedDict

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
from wepppy.nodb.mods.baer import Baer
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.debris_flow import DebrisFlow
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

# Preflight TOC Emoji Mapping
# Maps TOC anchor hrefs to TaskEnum members for emoji display.
# TaskEnum.emoji() is the single source of truth for all task emojis.
# See docs/ui-docs/control-ui-styling/preflight_behavior.md for architecture.
TOC_TASK_ANCHOR_TO_TASK = {
    '#map': TaskEnum.fetch_dem,
    '#disturbed-sbs': TaskEnum.init_sbs_map,
    '#channel-delineation': TaskEnum.build_channels,
    '#set-outlet': TaskEnum.set_outlet,
    '#subcatchments-delineation': TaskEnum.build_subcatchments,
    '#rangeland-cover': TaskEnum.build_rangeland_cover,
    '#landuse': TaskEnum.build_landuse,
    '#climate': TaskEnum.build_climate,
    '#rap-ts': TaskEnum.fetch_rap_ts,
    '#soils': TaskEnum.build_soils,
    '#treatments': TaskEnum.build_landuse,  # Using landuse emoji as placeholder
    '#wepp': TaskEnum.run_wepp_watershed,
    '#ash': TaskEnum.run_watar,
    '#rhem': TaskEnum.run_rhem,
    '#omni-scenarios': TaskEnum.run_omni_scenarios,
    '#omni-contrasts': TaskEnum.run_omni_contrasts,
    '#observed': TaskEnum.run_observed,
    '#debris-flow': TaskEnum.run_debris,
    '#dss-export': TaskEnum.dss_export,
    '#team': TaskEnum.project_init,  # Using project init emoji as placeholder
}

TOC_TASK_EMOJI_MAP = {anchor: task.emoji() for anchor, task in TOC_TASK_ANCHOR_TO_TASK.items()}

MOD_UI_DEFINITIONS = OrderedDict([
    ('rap_ts', {
        'label': 'RAP Time Series',
        'section_id': 'rap-ts',
        'section_class': 'wc-stack',
        'template': 'controls/rap_ts_pure.htm',
    }),
    ('treatments', {
        'label': 'Treatments',
        'section_id': 'treatments',
        'section_class': 'wc-stack',
        'template': 'controls/treatments_pure.htm',
    }),
    ('ash', {
        'label': 'Ash Transport',
        'section_id': 'ash',
        'section_class': 'wc-stack',
        'template': 'controls/ash_pure.htm',
    }),
    ('omni', {
        'label': 'Omni Scenarios',
        'section_id': 'omni-scenarios',
        'section_class': 'wc-stack',
        'template': 'controls/omni_scenarios_pure.htm',
    }),
    ('observed', {
        'label': 'Observed Data',
        'section_id': 'observed',
        'section_class': 'wc-stack',
        'template': 'controls/observed_pure.htm',
    }),
    ('debris_flow', {
        'label': 'Debris Flow',
        'section_id': 'debris-flow',
        'section_class': 'wc-stack',
        'template': 'controls/debris_flow_pure.htm',
        'requires_power_user': True,
    }),
    ('dss_export', {
        'label': 'DSS Export',
        'section_id': 'dss-export',
        'section_class': 'wc-stack',
        'template': 'controls/dss_export_pure.htm',
    }),
    ('path_ce', {
        'label': 'PATH Cost-Effective',
        'section_id': 'path-cost-effective',
        'section_class': 'wc-stack',
        'template': 'controls/path_cost_effective_pure.htm',
    }),
])

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


def _build_runs0_context(runid, config, playwright_load_all):
    global VAPID_PUBLIC_KEY
    from wepppy.nodb.mods.revegetation import Revegetation
    from wepppy.wepp.soils import soilsdb
    from wepppy.wepp import management
    from wepp_runner.wepp_runner import linux_wepp_bin_opts
    from wepppy.wepp.management.managements import landuse_management_mapping_options
    from wepppy.weppcloud.app import db, Run

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    base_wd = str(ctx.run_root)
    ron = Ron.getInstance(wd)

    # check config from url matches config from Ron
    if config != ron.config_stem:
        target_args = {'runid': runid, 'config': ron.config_stem}
        if ctx.pup_relpath:
            target_args['pup'] = ctx.pup_relpath
        return {'redirect': url_for_run('run_0.runs0', **target_args)}

    if ctx.pup_root and not ron.readonly:
        try:
            ron.readonly = True
        except Exception as exc:
            current_app.logger.warning('Failed to mark pup project as readonly: %s', exc)

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
    baer = Baer.tryGetInstance(wd) if 'baer' in ron.mods else None
    ash = Ash.tryGetInstance(wd)
    skid_trails = wepppy.nodb.mods.SkidTrails.tryGetInstance(wd)
    reveg = Revegetation.tryGetInstance(wd)
    omni = Omni.tryGetInstance(wd)
    treatments = Treatments.tryGetInstance(wd)
    redis_prep = RedisPrep.tryGetInstance(wd)
    debris_flow = DebrisFlow.tryGetInstance(wd) if 'debris_flow' in ron.mods else None

    if redis_prep is not None:
        rq_job_ids = redis_prep.get_rq_job_ids()
    else:
        rq_job_ids = {}

    landuseoptions = landuse.landuseoptions
    landuse_report_context = build_landuse_report_context(landuse)
    soildboptions = soilsdb.load_db()

    critical_shear_options = management.load_channel_d50_cs()
    reveg_cover_transform_options = [
        ("", "Observed"),
        ("20-yr_Recovery.csv", "20-Year Recovery"),
        ("20-yr_PartialRecovery.csv", "20-Year Partial Recovery"),
        ("user_cover_transform", "User-Defined Transform")
    ]
    wepp_bin_options = [(opt, opt) for opt in linux_wepp_bin_opts]

    _log_access(base_wd, current_user, request.remote_addr)
    timestamp = datetime.now()
    Run.query.filter_by(runid=runid).update({'last_accessed': timestamp})
    db.session.commit()

    mods_list = ron.mods or []
    show_rap_ts = 'rap_ts' in mods_list or playwright_load_all
    show_treatments = 'treatments' in mods_list or playwright_load_all
    show_ash = 'ash' in mods_list or playwright_load_all
    show_omni = 'omni' in mods_list or playwright_load_all
    show_observed = (observed is not None) or playwright_load_all
    show_debris_flow = (
        current_user.has_role('PowerUser') and
        (debris_flow is not None or playwright_load_all)
    )
    show_dss_export = 'dss_export' in mods_list or playwright_load_all
    show_path_ce = 'path_ce' in mods_list or playwright_load_all
    
    omni_has_ran_scenarios = bool(omni and omni.has_ran_scenarios)

    mod_visibility = {
        'rap_ts': show_rap_ts,
        'treatments': show_treatments,
        'ash': show_ash,
        'omni': show_omni,
        'observed': show_observed,
        'debris_flow': show_debris_flow,
        'dss_export': show_dss_export,
        'path_ce': show_path_ce,
    }

    context = dict(
        user=current_user,
        site_prefix=site_prefix,
        playwright_load_all=playwright_load_all,
        topaz=topaz,
        soils=soils,
        ron=ron,
        landuse=landuse,
        climate=climate,
        wepp=wepp,
        wepp_bin_options=wepp_bin_options,
        rhem=rhem,
        disturbed=disturbed,
        baer=baer,
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
        debris_flow=debris_flow,
        rq_job_ids=rq_job_ids,
        landuseoptions=landuseoptions,
        landcover_datasets=landuse.landcover_datasets,
        landuse_report_rows=landuse_report_context['report_rows'],
        landuse_dataset_options=landuse_report_context['dataset_options'],
        landuse_coverage_percentages=landuse_report_context['coverage_percentages'],
        landuse_management_mapping_options=landuse_management_mapping_options,
        soildboptions=soildboptions,
        critical_shear_options=critical_shear_options,
        reveg_cover_transform_options=reveg_cover_transform_options,
        climate_catalog=climate.catalog_datasets_payload(include_hidden=True),
        precisions=wepppy.nodb.unitizer.precisions,
        run_id=runid,
        runid=runid,
        config=config,
        toc_task_emojis=TOC_TASK_EMOJI_MAP,
        pup_relpath=ctx.pup_relpath,
        VAPID_PUBLIC_KEY=VAPID_PUBLIC_KEY,
        show_rap_ts=show_rap_ts,
        show_treatments=show_treatments,
        show_ash=show_ash,
        show_omni=show_omni,
        show_observed=show_observed,
        show_debris_flow=show_debris_flow,
        show_dss_export=show_dss_export,
        show_path_ce=show_path_ce,
        omni_has_ran_scenarios=omni_has_ran_scenarios,
        mod_visibility=mod_visibility
    )
    return context

@run_0_bp.route('/runs/<string:runid>/<config>/')
@authorize_and_handle_with_exception_factory
def runs0(runid, config):
    assert config is not None
    playwright_load_all = request.args.get('playwright_load_all', '').lower() in ('true', '1', 'yes')
    context = _build_runs0_context(runid, config, playwright_load_all)
    if 'redirect' in context:
        return redirect(context['redirect'])
    return render_template('runs0_pure.htm', **context)


@run_0_bp.route('/runs/<string:runid>/<config>/view/mod/<string:mod_name>')
@authorize_and_handle_with_exception_factory
def view_mod_section(runid, config, mod_name):
    mod_info = MOD_UI_DEFINITIONS.get(mod_name)
    if not mod_info:
        return error_factory('Unknown module')

    context = _build_runs0_context(runid, config, playwright_load_all=False)
    if 'redirect' in context:
        return redirect(context['redirect'])

    if not context['mod_visibility'].get(mod_name):
        return error_factory('Module is not enabled for this run')

    section_inner = render_template(mod_info['template'], **context)
    section_html = render_template(
        'run_0/mod_section_wrapper.htm',
        section_id=mod_info['section_id'],
        section_class=mod_info.get('section_class', 'wc-stack'),
        section_html=section_inner,
    )
    return success_factory({
        'mod': mod_name,
        'section_id': mod_info['section_id'],
        'html': section_html,
    })

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


def _render_run_not_found_page() -> Response:
    view_args = getattr(request, "view_args", {}) or {}
    runid = view_args.get("runid") or request.args.get("runid") or ""
    config = view_args.get("config") or request.args.get("config") or ""
    context = {
        "runid": runid,
        "config": config,
        "diff_runid": "",
        "project_href": "",
        "breadcrumbs_html": "",
        "error_message": "This run either doesn't exist or you don't have access to it.",
        "page_title": "Run Not Found",
    }
    return make_response(render_template("browse/not_found.htm", **context), 404)


@run_0_bp.app_errorhandler(403)
def _runs0_forbidden(error):  # pragma: no cover - flask error hook
    return _render_run_not_found_page()


@run_0_bp.app_errorhandler(404)
def _runs0_not_found(error):  # pragma: no cover - flask error hook
    return _render_run_not_found_page()
