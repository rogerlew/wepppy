# Copyright (c) 2016-, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import hashlib
import json
import logging
import os
import re
import socket
import sys
from collections import Counter
from datetime import datetime
from glob import glob
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

import awesome_codename

from werkzeug.middleware.proxy_fix import ProxyFix

from flask import (
    Flask, jsonify, request, render_template,
    redirect, send_file, Response, abort, make_response, send_from_directory,
    stream_with_context, url_for, current_app
)

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from sqlalchemy import func

from flask_sqlalchemy import SQLAlchemy
from flask_security import (
    RegisterForm,
    Security, SQLAlchemyUserDatastore,
    UserMixin, RoleMixin,
    login_required, current_user, roles_required
)


from wtforms.validators import DataRequired as Required
from flask_mail import Mail
from flask_session import Session
from flask_migrate import Migrate

from wtforms import StringField

import wepppy

from wepppy.all_your_base import isfloat, isint
from wepppy.all_your_base.geo import crop_geojson, read_raster
from wepppy.all_your_base.dateutils import parse_datetime, YearlessDate

from wepppy.nodb.mods.disturbed import write_disturbed_land_soil_lookup
from wepppy.nodb.preflight import preflight_check

from wepppy.soils.ssurgo import NoValidSoilsException

from wepppy.topo.topaz import (
    WatershedBoundaryTouchesEdgeError,
    MinimumChannelLengthTooShortError
)
from wepppy.climates.cligen import (
    StationMeta
)
from wepppy.topo.watershed_abstraction import (
    ChannelRoutingError,
)
from wepppy.wepp import management
from wepppy.wepp.soils import soilsdb

from wepppy.wepp.out import TotalWatSed2, DisturbedTotalWatSed2, Element, HillWat

from wepppy.wepp.stats import (
    OutletSummary,
    HillSummary,
    ChannelSummary,
    TotalWatbal
)

from wepppy.nodb.climate import (
    Climate,
    ClimateStationMode,
    NoClimateStationSelectedError,
    ClimateModeIsUndefinedError
)

from wepppy.nodb.watershed import (
    Watershed,
    WatershedNotAbstractedError
)

from wepppy.nodb import (
    Ron,
    Topaz,
    Landuse, LanduseMode,
    Soils, SoilsMode,
    Wepp, WeppPost,
    Unitizer,
    Observed,
    RangelandCover, RangelandCoverMode,
    Rhem,
    Baer,
    Disturbed,
    DebrisFlow,
    Ash, AshPost, AshSpatialMode,
    get_configs,
    get_legacy_configs
)

from wepppy.nodb.mods.ash_transport import ( 
    AshType, 
)

from wepppy.nodb.mods.omni import (
    Omni,
    OmniNoDbLockedException,
    OmniScenario # IntEnum
)

from wepppy.nodb.mods.treatments import TreatmentsMode, Treatments

from wepppy.nodb.redis_prep import RedisPrep

from wepppy.weppcloud.utils.helpers import (
    get_wd, authorize, render_template,
    error_factory, exception_factory, success_factory
)
from wepppy.weppcloud.utils.archive import has_archive, restore_archive, archive_run

try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except:
    send_discord_message = None


# Track number of busy workers
from multiprocessing import Semaphore

accesslog = "-"
access_log_format =  '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" rt=%(L)s busy=%({x-busy}i)s'

busy = Semaphore(0)

def pre_request(worker, req):
    busy.release()
    req.headers.append(("x-busy", str(busy._value)))

def post_request(worker, req, environ, resp):
    busy.acquire()

import logging

# load app configuration based on deployment

_hostname = socket.gethostname()
config_app = None
if 'wepp1' in _hostname or 'forest' in _hostname:
    try:
        from wepppy.weppcloud.wepp1_config import config_app
    except:
        pass
elif 'wepp2' in _hostname:
    from wepppy.weppcloud.wepp2_config import config_app
elif 'wepp3' in _hostname:
    from wepppy.weppcloud.wepp3_config import config_app


if config_app is None:
    from wepppy.weppcloud.standalone_config import config_app


sys.path.append(os.path.abspath(os.path.dirname(__file__)))

class HealthFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        return not ("OPTIONS /health" in msg or "Closing connection" in msg)

def setup_logging():
    """Configure gunicorn loggers while keeping error output intact."""
    filter_type = HealthFilter

    # Apply filter only to the access logger to hide noisy health checks.
    access_logger = logging.getLogger("gunicorn.access")
    if access_logger:
        if not any(isinstance(f, filter_type) for f in access_logger.filters):
            access_logger.addFilter(filter_type())

        for handler in access_logger.handlers:
            if not any(isinstance(f, filter_type) for f in handler.filters):
                handler.addFilter(filter_type())

    # Ensure the error logger has no HealthFilter attached so stack traces remain visible.
    error_logger = logging.getLogger("gunicorn.error")
    error_logger.setLevel(logging.DEBUG)
    if error_logger:
        for f in list(error_logger.filters):
            if isinstance(f, filter_type):
                error_logger.removeFilter(f)

        for handler in error_logger.handlers:
            for f in list(handler.filters):
                if isinstance(f, filter_type):
                    handler.removeFilter(f)


setup_logging()


def sort_numeric_keys(value, reverse=False):
    return sorted(value.items(), key=lambda x: int(x[0]), reverse=reverse)

def extract_leading_digits(s):
    if isfloat(s):
        return float(s)

    match = re.match(r'^(\d+(\.\d+)?)', str(s))
    return float(match.group(1)) if match else 0

def sort_numeric(value, reverse=False):
    return sorted(value, key=extract_leading_digits, reverse=reverse)

def get_file_sha1(file_path):
    """
    Compute the SHA-1 hash of a file.

    :param file_path: the path to the file
    :return: the SHA-1 hash of the file as a hexadecimal string
    """
    with open(file_path, "rb") as f:
        sha1 = hashlib.sha1()
        while True:
            data = f.read(65536) # read the file in chunks of 64KB
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()

#
# IE 11 "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko"
# "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; Win64; x64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.5072       7; .NET CLR 3.0.30729; .NET CLR 3.5.30729; Zoom 3.6.0; wbx 1.0.0)"
#

# noinspection PyBroadException

app = Flask(__name__)

app.jinja_env.filters['zip'] = zip
app.jinja_env.filters['sort_numeric'] = sort_numeric
app.jinja_env.filters['sort_numeric_keys'] = sort_numeric_keys

app.jinja_env.globals.update(max=max, min=min)

app = config_app(app)

# this xsendfile mod is broken on wepp.cloud
#app.config['USE_X_SENDFILE'] = True

# Configure SameSite for session cookies
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True  # Require a secure context (HTTPS)

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1
)

from routes.admin import admin_bp
from routes.archive import archive_bp
from routes.climate import climate_bp
from routes.combined_watershed_viewer import combined_watershed_viewer_bp
from routes.command_bar import command_bar_bp
from routes.debris_flow import debris_flow_bp
from routes.disturbed import disturbed_bp
from routes.download import download_bp
from routes.export import export_bp
from routes.fork import fork_bp
from routes.browse import browse_bp
from routes.wepprepr import repr_bp
from routes.diff import diff_bp
from routes.gdalinfo import gdalinfo_bp
from routes.geodata import geodata_bp
from routes.landuse import landuse_bp
from routes.map import map_bp
from routes.observed import observed_bp
from routes.omni import omni_bp
from routes.pivottable import pivottable_bp
from routes.project import project_bp
from routes.jsoncrack import jsoncrack_bp
from routes.rangeland import rangeland_bp
from routes.rangeland_cover import rangeland_cover_bp
from routes.readme import readme_bp, ensure_readme
from routes.rhem import rhem_bp
from routes.soils import soils_bp
from routes.treatments import treatments_bp
from routes.unitizer import unitizer_bp
from routes.user import user_bp
from routes.watar import watar_bp
from routes.watershed import watershed_bp
from routes.wepp import wepp_bp
from routes.locations import locations_bp
from routes.weppcloudr import weppcloudr_bp
from routes.rq.api.jobinfo import rq_jobinfo_bp
from routes.rq.api.api import rq_api_bp
from routes.rq.job_dashboard.routes import rq_job_dashboard_bp
from routes.stats import stats_bp
from routes.run_0 import run_0_bp
from routes._security import security_logging_bp, security_ui_bp

app.register_blueprint(admin_bp)
app.register_blueprint(archive_bp)
app.register_blueprint(climate_bp)
app.register_blueprint(combined_watershed_viewer_bp)
app.register_blueprint(command_bar_bp)
app.register_blueprint(debris_flow_bp)
app.register_blueprint(disturbed_bp)
app.register_blueprint(download_bp)
app.register_blueprint(browse_bp)
app.register_blueprint(export_bp)
app.register_blueprint(gdalinfo_bp)
app.register_blueprint(geodata_bp)
app.register_blueprint(repr_bp)
app.register_blueprint(diff_bp)
app.register_blueprint(fork_bp)
app.register_blueprint(landuse_bp)
app.register_blueprint(map_bp)
app.register_blueprint(observed_bp)
app.register_blueprint(omni_bp)
app.register_blueprint(pivottable_bp)
app.register_blueprint(project_bp)
app.register_blueprint(jsoncrack_bp)
app.register_blueprint(rangeland_bp)
app.register_blueprint(rangeland_cover_bp)
app.register_blueprint(weppcloudr_bp)
app.register_blueprint(locations_bp)
app.register_blueprint(rq_api_bp)
app.register_blueprint(rq_jobinfo_bp)
app.register_blueprint(rq_job_dashboard_bp)
app.register_blueprint(readme_bp)
app.register_blueprint(soils_bp)
app.register_blueprint(rhem_bp)
app.register_blueprint(treatments_bp)
app.register_blueprint(unitizer_bp)
app.register_blueprint(user_bp)
app.register_blueprint(watar_bp)
app.register_blueprint(watershed_bp)
app.register_blueprint(wepp_bp)
app.register_blueprint(stats_bp)
app.register_blueprint(run_0_bp)
app.register_blueprint(security_logging_bp)
app.register_blueprint(security_ui_bp)

app.logger.setLevel(logging.DEBUG)

mail = Mail(app)
session_manager = Session(app)

# Setup Flask-Security
# Create database connection object
db = SQLAlchemy(app)
migrate = Migrate(app, db, directory='/workdir/wepppy/wepppy/weppcloud/migrations')

@app.context_processor
def inject_site_prefix():
    return dict(site_prefix=app.config['SITE_PREFIX'])

# Define models
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

runs_users = db.Table(
    'runs_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id'), primary_key=True),
    db.Column('run_id', db.Integer(), db.ForeignKey('run.id'), primary_key=True)
)


class Run(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    runid = db.Column(db.String(255), unique=True)
    date_created = db.Column(db.DateTime())
    owner_id = db.Column(db.String(255))
    config = db.Column(db.String(255))
    last_modified = db.Column(db.DateTime(), nullable=True)
    last_accessed = db.Column(db.DateTime(), nullable=True)

    @property
    def valid(self):
        wd = self.wd
        if not _exists(wd):
            return False

        if not _exists(_join(wd, 'ron.nodb')):
            return False

        return True

    def __eq__(self, other):
        return (self.runid == other or
                self.runid == getattr(other, 'runid', None))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self.runid

    @property
    def wd(self):
        return get_wd(self.runid)

    @property
    def _owner(self):
        if self.owner_id is None:
            return None

        return User.query.filter(User.id == self.owner_id).first()

    @property
    def owner(self):
        _owner = self._owner
        if _owner:
            return _owner.email
        else:
            return '<anonymous>'

    @property
    def meta(self):
        wd = self.wd
        try:
            ron = Ron.getInstance(wd)
        except:
            return None

        return dict(owner=self.owner,
                    runid=self.runid,
                    date_created=self.date_created,
                    last_modified=self.last_modified,
                    owner_id=self.owner_id,
                    config=self.config,
                    name=ron.name,
                    scenario=ron.scenario,
                    w3w=ron.w3w,
                    readonly=ron.readonly)


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False)
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())

    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(255))
    current_login_ip = db.Column(db.String(255))
    login_count = db.Column(db.Integer)

    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    runs = db.relationship('Run', secondary=runs_users, lazy='subquery',
                           backref=db.backref('users', lazy=True))


class WeppCloudUserDatastore(SQLAlchemyUserDatastore):
    def __init__(self, _db, user_model, role_model, run_model):
        SQLAlchemyUserDatastore.__init__(self, _db, user_model, role_model)
        self.run_model = run_model

    def create_run(self, runid, config, user: User, date_created=None):
        if user.is_anonymous:
            owner_id = None
        else:
            owner_id = user.id

        if date_created is None:
            date_created = datetime.now()

        run = self.run_model(runid=runid, config=config,
                             owner_id=owner_id, date_created=date_created)
        run0 = self.put(run)
        self.commit()

        if owner_id is not None:
            self.add_run_to_user(user, run)

        return run0

    def delete_run(self, run: Run):
        self.delete(run)
        self.commit()

    def add_run_to_user(self, user: User, run: Run):
        """Adds a run to a user.

        :param user: The user to manipulate
        :param run: The run to remove from the user
        """
        user.runs.append(run)
        self.put(user)
        self.commit()

        return True

    def remove_run_to_user(self, user: User, run: Run):
        """Removes a run from a user.

        :param user: The user to manipulate
        :param run: The run to add to the user
        """
        if run in user.runs:
            user.runs.remove(run)
            self.put(user)
            self.commit()
        return True


user_datastore = WeppCloudUserDatastore(db, User, Role, Run)


class ExtendedRegisterForm(RegisterForm):
    first_name = StringField('First Name', [Required()])
    last_name = StringField('Last Name', [Required()])


security = Security(app, user_datastore,
                    register_form=ExtendedRegisterForm,
                    confirm_register_form=ExtendedRegisterForm)


def get_run_owners(runid):
    return User.query.filter(User.runs.any(Run.runid == runid)).all()

#
# Frequent base routes

@app.route('/health')
def health():
    return jsonify('OK')



_thisdir = os.path.dirname(__file__)

@app.context_processor
def utility_processor():
    def format_mode(mode):
        return str(int(mode))
    return dict(format_mode=format_mode)


@app.context_processor
def units_processor():
    return Unitizer.context_processor_package()


@app.context_processor
def commafy_processor():
    def commafy(v):
        try:
            return "{:,}".format(int(v))
        except:
            return v

    return dict(commafy=commafy)


@app.context_processor
def isfloat_processor():
    return dict(isfloat=isfloat)


@app.context_processor
def startswith_processor():
    return dict(startswith=lambda x, y: str(x).startswith(str(y)))


@app.context_processor
def hasattr_processor():
    return dict(hasattr=lambda item, attr: hasattr(item, attr))


def _get_run_name(runid):
    try:
        wd = get_wd(runid)
        name = Ron.getInstance(wd).name
        return name
    except:
        return '-'


def _run_exists(runid):
    wd = get_wd(runid)
    if not _exists(_join(wd, 'ron.nodb')):
        return False

    try:
#        ron = Ron.getInstance(wd)
        return True
    except:
        return False


def _get_run_owner(runid):
    try:
        run = Run.query.filter(Run.runid == runid).first()
        if run.owner_id is None:
            return 'anonymous'

        owner = User.query.filter(User.id == run.owner_id).first()
        return owner.email
    except:
        return '-'


def _get_last_modified(runid):
    wd = get_wd(runid)
    nodbs = glob(_join(wd, '*.nodb'))

    last = 0
    for fn in nodbs:
        statbuf = os.stat(fn)
        if statbuf.st_mtime > last:
            last = statbuf.st_mtime

    return datetime.fromtimestamp(last)


def get_all_runs():
    return [run for run in Run.query.order_by(Run.date_created).all()]


def _get_all_users():
    return User.query.order_by(User.last_login_at).all()


def _get_anonymous_runs():
    return Run.query.filter(Run.owner_id is None)


def _w3w_center(runid):
    wd = get_wd(runid)
    return Ron.getInstance(wd).w3w


@app.context_processor
def security_processor():

    return dict(run_exists=_run_exists,
                get_run_name=_get_run_name,
                get_run_owner=_get_run_owner,
                get_last_modified=_get_last_modified,
                get_anonymous_runs=_get_anonymous_runs,
                get_all_runs=get_all_runs,
                w3w_center=_w3w_center,
                get_all_users=_get_all_users)


@app.route('/')
def index():

    runs_counter = Counter()
    try:
        if _exists('/geodata/weppcloud_runs/runs_counter.json'):
            with open('/geodata/weppcloud_runs/runs_counter.json') as fp:
                runs_counter = Counter(json.load(fp))
    except:
        pass

    try:
        return render_template('index.htm', user=current_user, runs_counter=runs_counter)

    except Exception:
        return exception_factory()


