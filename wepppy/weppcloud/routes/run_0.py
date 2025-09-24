"""Routes for wepp blueprint extracted from app.py."""

import wepppy
import pathlib

from datetime import datetime

from ._common import *  # noqa: F401,F403

import wepppy
from wepppy.all_your_base import isint
from wepppy.nodb import Landuse, Ron, Unitizer, Watershed, Wepp, WeppPost, Soils, Topaz, Observed, RangelandCover, Rhem, Treatments
from wepppy.nodb.mods.ash_transport import Ash
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.omni import Omni, OmniScenario
from wepppy.nodb.climate import Climate
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.wepp import management
from wepppy.wepp.out import DisturbedTotalWatSed2, Element, HillWat, TotalWatSed2
from wepppy.wepp.stats import ChannelSummary, HillSummary, OutletSummary, TotalWatbal
from wepppy.weppcloud.utils.helpers import get_wd, authorize, get_run_owners_lazy


run_0_bp = Blueprint('run_0', __name__)

VAPID_PUBLIC_KEY = ''
_VAPID_PATH = pathlib.Path('/workdir/weppcloud2/microservices/wepppush/vapid.json')
if _VAPID_PATH.exists():
    with _VAPID_PATH.open() as fp:
        vapid = json.load(fp)
        VAPID_PUBLIC_KEY = vapid.get('publicKey', '')

@run_0_bp.route('/sw.js')
def service_worker():
    from flask import make_response, send_from_directory
    response = make_response(send_from_directory('static/js', 'webpush_service_worker.js'))
    response.headers['Service-Worker-Allowed'] = '/'
    return response


# Redirect to the correct to the full run path
@run_0_bp.route('/runs/<string:runid>/')
def runs0_nocfg(runid):

    wd = get_wd(runid)
    owners = get_run_owners_lazy(runid)
    try:
        ron = Ron.getInstance(wd)
    except FileNotFoundError:
        abort(404)

    return redirect(url_for('run_0.runs0', runid=runid, config=ron.config_stem))



def _log_access(wd, current_user, ip):
    assert _exists(wd)

    fn, runid = _split(wd.rstrip('/'))
    fn = _join(fn, '.{}'.format(runid))
    with open(fn, 'a') as fp:
        email = getattr(current_user, 'email', '<anonymous>')
        fp.write('{},{},{}\n'.format(email, ip, datetime.now()))

@run_0_bp.route('/runs/<string:runid>/<config>/')
def runs0(runid, config):
    global VAPID_PUBLIC_KEY
    from wepppy.nodb.mods.revegetation import Revegetation
    from wepppy.wepp.soils import soilsdb
    from wepppy.wepp import management
    from wepp_runner.wepp_runner import linux_wepp_bin_opts
    from wepppy.wepp.management.managements import landuse_management_mapping_options

    from wepppy.weppcloud.app import db, Run

    assert config is not None

    wd = get_wd(runid)

    owners = get_run_owners_lazy(runid)
    try:
        ron = Ron.getInstance(wd)
    except FileNotFoundError:
        abort(404)

    # check config
    if config != ron.config_stem:
        return redirect(url_for('run_0.runs0', runid=runid, config=ron.config_stem))

    should_abort = True
    if current_user in owners:
        should_abort = False

    if not owners:
        should_abort = False

    if current_user.has_role('Admin'):
        should_abort = False

    if ron.public:
        should_abort = False

    if should_abort:
        abort(404)

    try:

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

        try:
            observed = Observed.getInstance(wd)
        except:
            observed = Observed(wd, "%s.cfg" % config)

        try:
            rangeland_cover = RangelandCover.getInstance(wd)
        except:
            rangeland_cover = None

        try:
            rhem = Rhem.getInstance(wd)
        except:
            rhem = None

        try:
            disturbed = Disturbed.getInstance(wd)
        except:
            disturbed = None

        try:
            ash = Ash.getInstance(wd)
        except:
            ash = None

        try:
            skid_trails = wepppy.nodb.mods.SkidTrails.getInstance(wd)
        except:
            skid_trails = None

        try:
            reveg = Revegetation.getInstance(wd)
        except:
            reveg = None

        try:
            omni = Omni.getInstance(wd)
        except:
            omni = None

        try:
            treatments = Treatments.getInstance(wd)
        except:
            treatments = None

        try:
            redis_prep = RedisPrep.getInstance(wd)
        except:
            redis_prep = None

        if redis_prep is not None:
            rq_job_ids = redis_prep.get_rq_job_ids()
        else:
            rq_job_ids = {}

        landuseoptions = landuse.landuseoptions
        soildboptions = soilsdb.load_db()

        critical_shear_options = management.load_channel_d50_cs()


        _log_access(wd, current_user, request.remote_addr)
        timestamp = datetime.now()
        Run.query.filter_by(runid=runid).update({'last_accessed': timestamp})
        db.session.commit()

        return render_template('0.html',
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
                               landuse_management_mapping_options=landuse_management_mapping_options,
                               soildboptions=soildboptions,
                               critical_shear_options=critical_shear_options,
                               precisions=wepppy.nodb.unitizer.precisions,
                               run_id=runid,
                               runid=runid,
                               config=config,
                               VAPID_PUBLIC_KEY=VAPID_PUBLIC_KEY)
    except:
        return exception_factory(runid=runid)

