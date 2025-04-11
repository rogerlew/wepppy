# Copyright (c) 2016-, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
import sys
import csv
from datetime import datetime

from ast import literal_eval
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

from collections import Counter

import json
import shutil
import traceback
from glob import glob
from subprocess import check_output, Popen, PIPE

import awesome_codename

from werkzeug.utils import secure_filename

from deprecated import deprecated

from flask import (
    Flask, jsonify, request, render_template,
    redirect, send_file, Response, abort, make_response,
    stream_with_context, url_for
)

from sqlalchemy import func

from flask_sqlalchemy import SQLAlchemy
from flask_security import (
    RegisterForm,
    Security, SQLAlchemyUserDatastore,
    UserMixin, RoleMixin,
    login_required, current_user, roles_required
)

import re

from wtforms.validators import DataRequired as Required
from flask_mail import Mail
from flask_migrate import Migrate

from wtforms import StringField

import wepppy

import requests

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
    Rhem, RhemPost,
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

from wepppy.nodb.omni import (
    Omni,
    OmniNoDbLockedException,
    OmniScenario # IntEnum
)

from wepppy.nodb.redis_prep import RedisPrep

from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.weppcloud.utils.archive import has_archive, restore_archive, archive_run

try:
    from weppcloud2.discord_bot.discord_client import send_discord_message
except:
    send_discord_message = None


# load app configuration based on deployment
import socket
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

import hashlib


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

app = config_app(app)

# this xsendfile mod is broken on wepp.cloud
#app.config['USE_X_SENDFILE'] = True

# Configure SameSite for session cookies
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True  # Require a secure context (HTTPS)

from routes.download import download_bp
from routes.browse import browse_bp
from routes.gdalinfo import gdalinfo_bp
from routes.wepprepr import repr_bp
from routes.diff import diff_bp
from routes.rq.api.jobinfo import rq_jobinfo_bp
from routes.rq.api.api import rq_api_bp
from routes.rq.job_dashboard.routes import rq_job_dashboard_bp

app.register_blueprint(download_bp)
app.register_blueprint(browse_bp)
app.register_blueprint(gdalinfo_bp)
app.register_blueprint(repr_bp)
app.register_blueprint(diff_bp)
app.register_blueprint(rq_api_bp)
app.register_blueprint(rq_jobinfo_bp)
app.register_blueprint(rq_job_dashboard_bp)

mail = Mail(app)

# Setup Flask-Security
# Create database connection object
db = SQLAlchemy(app)
migrate = Migrate(app, db)

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
    def last_modified(self):
        return _get_last_modified(self.wd)       

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



# from wepppy.weppcloud.wepp1_config import _init
# _init(app, db, user_datastore)



@app.route('/health')
def health():
    return jsonify('OK')


@app.route('/profile')
@app.route('/profile/')
@login_required
def profile():
    try:
        return render_template('user/profile.html', user=current_user)
    except:
        return exception_factory()


@app.route('/runs')
@app.route('/runs/')
@login_required
def runs():
    try:
        user_runs = [run.meta for run in current_user.runs]
        user_runs = [meta for meta in user_runs if meta is not None]
        user_runs.sort(key=lambda meta: meta['last_modified'], reverse=True)

        return render_template('user/runs.html', 
                               user=current_user, 
                               user_runs=user_runs, 
                               show_owner=False)
    except:
        return exception_factory()


@app.route('/allruns')
@app.route('/allruns/')
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


@app.route('/usermod')
@app.route('/usermod/')
@roles_required('Root')
def usermod():
    try:
        return render_template('user/usermod.html', user=current_user)
    except:
        return exception_factory()


@app.route('/huc-fire')
@app.route('/huc-fire/')
def huc_fire():
    try:
        return render_template('huc-fire/index.html', user=current_user)
    except:
        return exception_factory()


@app.route('/huc-fire/tasks/upload_sbs/', methods=['POST'])
def upload_sbs():

    try:
        file = request.files['input_upload_sbs']
    except Exception:
        return exception_factory('Could not find file')

    try:
        if file.filename == '':
            return error_factory('no filename specified')

        filename = secure_filename(file.filename)
    except Exception:
        return exception_factory('Could not obtain filename')

    runid, wd = create_run_dir(current_user)

    config = 'disturbed9002'
    cfg = f'{config}.cfg'

    try:
        Ron(wd, cfg)
    except Exception:
        return exception_factory('Could not create run')

    if not current_user.is_anonymous:
        try:
            user_datastore.create_run(runid, config, current_user)
        except Exception:
            return exception_factory('Could not add run to user database')


    disturbed = Disturbed.getInstance(wd)
    file_path = _join(disturbed.disturbed_dir, filename)
    try:
        file.save(file_path)
    except Exception:
        return exception_factory('Could not save file')

    try:
        res = disturbed.validate(filename)
    except Exception:
        return exception_factory('Failed validating file')

    return jsonify(dict(runid=runid))


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/resources/huc.json')
def huc(runid, config):

    wd = get_wd(runid)
    disturbed = Disturbed.getInstance(wd)
    ((ymin, xmin), (ymax, xmax)) = disturbed.bounds

    # Construct the URL to query the hydro.nationalmap.gov server
    url = (f"https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/6/query?"
           f"geometry=%7B%0D%0A++%22xmin%22%3A+{xmin}%2C%0D%0A++%22ymin%22%3A+{ymin}%2C%0D%0A++%22xmax%22%3A+{xmax}%2C%0D%0A++%22ymax%22%3A+{ymax}%2C%0D%0A++%22spatialReference%22%3A+%7B%0D%0A++++%22wkid%22%3A+4326%0D%0A++%7D%0D%0A%7D"
           f"&geometryType=esriGeometryEnvelope&spatialRel=esriSpatialRelIntersects&returnGeometry=true&f=geojson&inSR=4326&outSR=4326")

    # Fetch the GeoJSON from the hydro.nationalmap.gov server
    response = requests.get(url)
    geojson_data = response.json()

    with open(_join(disturbed.disturbed_dir, 'huc.json'), 'w') as fp:
        json.dump(geojson_data, fp)

    return geojson_data


@app.route('/tasks/usermod/', methods=['POST'])
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


_thisdir = os.path.dirname(__file__)

static_dir = _join(_thisdir, 'static')


def error_factory(msg='Error Handling Request'):
    return jsonify({'Success': False,
                    'Error': msg})


def exception_factory(msg='Error Handling Request',
                      stacktrace=None,
                      runid=None):
    if stacktrace is None:
        stacktrace = traceback.format_exc()

    if runid is not None:
        wd = get_wd(runid)
        with open(_join(wd, 'exceptions.log'), 'a') as fp:
            fp.write(f'[{datetime.now()}]\n')
            fp.write(stacktrace)
            fp.write('\n\n')

    with open('/var/log/exceptions.log', 'a') as fp:
        fp.write(f'[{datetime.now()}] ')
        if runid is not None:
            fp.write(f'{runid}\n')
        fp.write(stacktrace)
        fp.write('\n\n')

    return make_response(jsonify({'Success': False,
                         'Error': msg,
                         'StackTrace': stacktrace.split('\n')}), 500)


def success_factory(kwds=None):
    if kwds is None:
        return jsonify({'Success': True})
    else:
        return jsonify({'Success': True,
                        'Content': kwds})


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


def _get_all_runs():
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
                get_all_runs=_get_all_runs,
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


@app.route('/getloadavg')
@app.route('/getloadavg/')
def getloadavg():
    return jsonify(os.getloadavg())


@app.route('/access-by-year')
@app.route('/access-by-year/')
def access_by_year():
    try:
        project_loads = Counter()

        if _exists('/geodata/weppcloud_runs/access.csv'):
            with open('/geodata/weppcloud_runs/access.csv') as fp:
                rdr = csv.DictReader(fp)
                for d in rdr:
                    project_loads[int(d['year'])] += 1

    except Exception:
        return exception_factory()

    try:
        return jsonify(project_loads)

    except Exception:
        return exception_factory()


@app.route('/access-by-month')
@app.route('/access-by-month/')
def access_by_month():
    try:
        project_loads = Counter()

        if _exists('/geodata/weppcloud_runs/access.csv'):
            with open('/geodata/weppcloud_runs/access.csv') as fp:
                rdr = csv.DictReader(fp)
                for d in rdr:
                    year = int(d['year'])
                    month = int(d['date'].strip().split('-')[1])
                    project_loads[f'{year}-{month}'] += 1

    except Exception:
        return exception_factory()

    try:
        return jsonify(project_loads)

    except Exception:
        return exception_factory()


@app.route('/stats')
@app.route('/stats/')
def stats():
    try:
        if _exists('/geodata/weppcloud_runs/runs_counter.json'):
            with open('/geodata/weppcloud_runs/runs_counter.json') as fp:
                runs_counter = json.load(fp)
    except:
        runs_counter = {}

    try:
        return jsonify(runs_counter)

    except Exception:
        return exception_factory()


@app.route('/stats/<key>')
@app.route('/stats/<key>/')
def stats_key(key):
    try:
        if _exists('/geodata/weppcloud_runs/runs_counter.json'):
            with open('/geodata/weppcloud_runs/runs_counter.json') as fp:
                runs_counter = json.load(fp)
    except:
        runs_counter = {}

    try:
        return jsonify(runs_counter.get(key))

    except Exception:
        return exception_factory()


@app.route('/joh')
@app.route('/joh/')
def joh_index():
    return render_template('locations/joh/index.htm', user=current_user)


@app.route('/joh/joh-map.htm')
def joh_map():
    return render_template('locations/joh/joh-map.htm', user=current_user)


@app.route('/portland-municipal')
@app.route('/portland-municipal/')
@app.route('/locations/portland-municipal')
@app.route('/locations/portland-municipal/')
@roles_required('PortlandGroup')
def portland_index():
    return render_template('locations/portland/index.htm', user=current_user)


@app.route('/portland-municipal/results')
@app.route('/portland-municipal/results/')
@app.route('/locations/portland-municipal/results')
@app.route('/locations/portland-municipal/results/')
def portland_results_index():

    import io
    import wepppy
    fn = _join(wepppy.nodb.mods.locations.portland.portland._thisdir, 'results', 'index.htm')

    if _exists(fn):
        with io.open(fn, mode="r", encoding="utf-8") as fp:
            return fp.read()

@app.route('/portland-municipal/results/<file>')
@app.route('/portland-municipal/results/<file>/')
@app.route('/locations/portland-municipal/results/<file>')
@app.route('/locations/portland-municipal/results/<file>/')
@roles_required('PortlandGroup')
def portland_results(file):
    """
    recursive list the file structure of the working directory
    """
    import wepppy
    fn = _join(wepppy.nodb.mods.locations.portland.portland._thisdir, 'results', file)
    
    if _exists(fn):
        return send_file(fn, as_attachment=True)
    else:
        return error_factory('File does not exist')
    

@app.route('/lt')
@app.route('/lt/')
@app.route('/locations/lt')
@app.route('/locations/lt/')
def lt_index():
    return render_template('lt/index.htm', user=current_user)


@app.route('/ltf')
@app.route('/ltf/')
def ltf_index():
    return render_template('ltf/index.htm', user=current_user)


@app.route('/lt/SteepSlopes')
@app.route('/lt/SteepSlopes/')
@app.route('/locations/lt/SteepSlopes')
@app.route('/locations/lt/SteepSlopes/')
def lt_steep_slope_index():
    return render_template('lt/SteepSlopes.html', user=current_user)

@app.route('/locations/caldor')
@app.route('/locations/caldor/')
def calsor_index():
    return render_template('locations/caldor/Caldor.html', user=current_user)

@app.route('/locations/caldor/results/<file>')
@app.route('/locations//results/<file>/')
def caldor_results(file):
    """
    recursive list the file structure of the working directory
    """
    fn = _join('/workdir/wepppy/wepppy/weppcloud/templates/locations/caldor/results', file)
    
    if _exists(fn):
        return send_file(fn, as_attachment=True)
    else:
        return error_factory('File does not exist')
    
@app.route('/seattle-municipal')
@app.route('/seattle-municipal/')
@app.route('/locations/seattle-municipal')
@app.route('/locations/seattle-municipal/')
def seattle_index():
    return render_template('locations/spu/index.htm', user=current_user)

@app.route('/seattle-municipal/results')
@app.route('/seattle-municipal/results/')
@app.route('/locations/seattle-municipal/results')
@app.route('/locations/seattle-municipal/results/')
def seattle_results_index():

    import io
    import wepppy
    fn = _join(wepppy.nodb.mods.locations.seattle.seattle._thisdir, 'results', 'index.htm')

    if _exists(fn):
        with io.open(fn, mode="r", encoding="utf-8") as fp:
            return fp.read()


@app.route('/seattle-municipal/results/<file>')
@app.route('/seattle-municipal/results/<file>/')
@app.route('/locations/seattle-municipal/results/<file>')
@app.route('/locations/seattle-municipal/results/<file>/')
# roles_required('SeattleGroup')
def seattle_results(file):
    """
    recursive list the file structure of the working directory
    """
    import io
    import wepppy
    fn = _join(wepppy.nodb.mods.locations.seattle.seattle._thisdir, 'results', file)

    if _exists(fn):

        if '.htm' in fn:
            with io.open(fn, mode="r", encoding="utf-8") as fp:
                return fp.read()
        elif '.jpeg' in fn or '.jpg' in fn:
            return send_file(fn, mimetype='image/jpg')

        return send_file(fn, as_attachment=True)
    else:
        return error_factory('File does not exist')
    

@app.route('/seattle-municipal/results/<foo>/<bar>')
@app.route('/seattle-municipal/results/<foo>/<bar>/')
@app.route('/locations/seattle-municipal/results/<foo>/<bar>')
@app.route('/locations/seattle-municipal/results/<foo>/<bar>/')
# roles_required('SeattleGroup')
def seattle_results2(foo, bar):
    """
    recursive list the file structure of the working directory
    """
    import io
    import wepppy
    fn = _join(wepppy.nodb.mods.locations.seattle.seattle._thisdir, 'results', foo, bar)

    if _exists(fn):

        if '.htm' in fn:
            with io.open(fn, mode="r", encoding="utf-8") as fp:
                return fp.read()

        elif '.jpeg' in fn or '.jpg' in fn:
            return send_file(fn, mimetype='image/jpg')

        return send_file(fn, as_attachment=True)
    else:
        return error_factory('File does not exist')
    

@app.route('/seattle-municipal/static/<file>')
@app.route('/seattle-municipal/static/<file>/')
@app.route('/locations/seattle-municipal/static/<file>')
@app.route('/locations/seattle-municipal/static/<file>/')
# roles_required('SeattleGroup')
def seattle_static(file):
    """
    recursive list the file structure of the working directory
    """
    import wepppy
    fn = _join(wepppy.nodb.mods.locations.seattle.seattle._thisdir, 'static', file)

    if _exists(fn):
        
        with io.open(fn, "r", encoding="utf-8") as fp:
            return fp.read()
    else:
        return error_factory('File does not exist')
    

@app.route('/create')
def create_redirect():
    return redirect(url_for('create_index'))

@app.route('/create/')
def create_index():
    configs = get_configs()
    x = ['<tr><td><a href="{0}">{0}</a></td>'
         '<td><a href="{0}?general:dem_db=ned1/2016">{0} ned1/2016</a></td>'
         '<td><a href="{0}?watershed:delineation_backend=taudem">{0} TauDEM</a></td></tr>'
         .format(cfg) for cfg in sorted(configs) if cfg != '_defaults']
    return '<html><body>'\
           '<link rel="stylesheet" '\
           'href="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/css/bootstrap.min.css" '\
           'integrity="sha384-TX8t27EcRE3e/ihU7zmQxVncDAy5uIKz4rEkgIXeMed4M0jlfIDPvg6uqKI2xXr2" crossorigin="anonymous">'\
           '\n<table class="table">{}</table>\n</body></html>'.format('\n'.join(x))


@app.route('/create-legacy')
def create_legacy_redirect():
    return redirect(url_for('create_legacy_index'))

@app.route('/create-legacy/')
def create_legacy_index():
    configs = get_legacy_configs()
    x = ['<tr><td><a href="{0}">{0}</a></td>'
         '<td><a href="{0}?general:dem_db=ned1/2016">{0} ned1/2016</a></td>'
         '<td><a href="{0}?watershed:delineation_backend=taudem">{0} TauDEM</a></td></tr>'
         .format(cfg) for cfg in sorted(configs) if cfg != '_defaults']
    return '<html><body>'\
           '<link rel="stylesheet" '\
           'href="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/css/bootstrap.min.css" '\
           'integrity="sha384-TX8t27EcRE3e/ihU7zmQxVncDAy5uIKz4rEkgIXeMed4M0jlfIDPvg6uqKI2xXr2" crossorigin="anonymous">'\
           '\n<table class="table">{}</table>\n</body></html>'.format('\n'.join(x))


def create_run_dir(current_user):
    wd = None
    dir_created = False
    while not dir_created:
        runid = awesome_codename.generate_codename().replace(' ', '-').replace("'", '')

        email = getattr(current_user, 'email', '')
        if email.startswith('rogerlew@'):
            runid = 'rlew-' + runid
        elif email.startswith('mdobre@'):
            runid = 'mdobre-' + runid
        elif email.startswith('srivas42@'):
            runid = 'srivas42-' + runid
        elif request.remote_addr == '127.0.0.1':
            runid = 'devvm-' + runid

        wd = get_wd(runid)
        if _exists(wd):
            continue

        if has_archive(runid):
            continue

        os.makedirs(wd)
        dir_created = True

    return runid, wd


@app.route('/create/<config>')
@app.route('/create/<config>/')
def create(config):

    cfg = "%s.cfg" % config

    overrides = '&'.join(['{}={}'.format(k, v) for k, v in request.args.items()])

    if len(overrides) > 0:
        cfg += '?%s' % overrides

    runid, wd = create_run_dir(current_user)

    try:
        Ron(wd, cfg)
    except Exception:
        return exception_factory('Could not create run')

    url = '%s/runs/%s/%s/' % (app.config['SITE_PREFIX'], runid, config)

    if not current_user.is_anonymous:
        try:
            user_datastore.create_run(runid, config, current_user)
        except Exception:
            return exception_factory('Could not add run to user database: proceed to https://wepp.cloud' + url)

    return redirect(url)

@app.route('/create-legacy/<config>')
@app.route('/create-legacy/<config>/')
def create_legacy(config):

    cfg = "legacy/%s.toml" % config

    overrides = '&'.join(['{}={}'.format(k, v) for k, v in request.args.items()])

    if len(overrides) > 0:
        cfg += '?%s' % overrides

    runid, wd = create_run_dir(current_user)

    try:
        Ron(wd, cfg)
    except Exception:
        return exception_factory('Could not create run')

    url = '%s/runs/%s/%s/' % (app.config['SITE_PREFIX'], runid, config)

    if not current_user.is_anonymous:
        try:
            user_datastore.create_run(runid, config, current_user)
        except Exception:
            return exception_factory('Could not add run to user database: proceed to https://wepp.cloud' + url)

    return redirect(url)


@app.route('/runs/<string:runid>/<config>/access-log')
@app.route('/runs/<string:runid>/<config>/access-log/')
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

    return f'<html><pre>{contents}</pre></html>'


@app.route('/runs/<string:runid>/<config>/rq-fork-console', strict_slashes=False)
@app.route('/runs/<string:runid>/<config>/rq-fork-console/', strict_slashes=False)
def rq_fork_console(runid, config):
    undisturbify = ('false', 'true')[bool(request.args.get('undisturbify', False))]

    # get working dir of original directory
    wd = get_wd(runid)
    owners = get_run_owners(runid)

    should_abort = True

    if current_user in owners:
        should_abort = False

    if current_user.has_role('Admin'):
        should_abort = False

    if len(owners) == 0:
        should_abort = False

    else:
        ron = Ron.getInstance(wd)
        if ron.public:
            should_abort = False

    if should_abort:
        abort(403)

    return render_template('controls/rq-fork-console.j2', runid=runid, config=config, undisturbify=undisturbify)


@app.route('/runs/<string:runid>/<config>/modify_disturbed')
def modify_disturbed(runid, config):
    assert config is not None

    wd = get_wd(runid)
    owners = get_run_owners(runid)
    try:
        ron = Ron.getInstance(wd)
    except FileNotFoundError:
        abort(404)

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
        return render_template('controls/edit_csv.htm', 
            csv_url='download/disturbed/disturbed_land_soil_lookup.csv')
    except:
        return exception_factory('Error Clearing Locks', runid=runid)


@app.route('/runs/<string:runid>/<config>/reset_disturbed')
@app.route('/runs/<string:runid>/<config>/reset_disturbed/')
def reset_disturbed(runid, config):
    assert config is not None

    wd = get_wd(runid)
    owners = get_run_owners(runid)
    try:
        ron = Ron.getInstance(wd)
    except FileNotFoundError:
        abort(404)

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
        disturbed = Disturbed.getInstance(wd)
        disturbed.reset_land_soil_lookup()

        return success_factory()
    except:
        return exception_factory('Error Resetting Disturbed Land Soil Lookup', runid=runid)



@app.route('/runs/<string:runid>/<config>/tasks/preflight/', methods=['POST'])
def task_preflight(runid, config):
    wd = get_wd(runid)
    res = preflight_check(wd)
    return jsonify(res)


@app.route('/runs/<string:runid>/<config>/tasks/modify_disturbed', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/modify_disturbed/', methods=['POST'])
def task_modify_disturbed(runid, config):
    wd = get_wd(runid)

    try:
        data = json.loads(request.data.decode('utf-8'))
        lookup_fn = Disturbed.getInstance(wd).lookup_fn
        write_disturbed_land_soil_lookup(lookup_fn, data)
        return success_factory()
    except:
        return exception_factory('Error Modifying Disturbed', runid=runid)


@app.route('/runs/<string:runid>/<config>/tasks/delete', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/delete/', methods=['POST'])
def delete_run(runid, config):
    owners = get_run_owners(runid)

    should_abort = True
    if current_user in owners:
        should_abort = False

    if current_user.has_role('Admin'):
        should_abort = False

    if should_abort:
        return error_factory('authentication error')

    # get working dir of original directory
    wd = get_wd(runid)

    ron = Ron.getInstance(wd)
    if ron.readonly:
        return error_factory('cannot delete readonly project')

    try:
        shutil.rmtree(wd)
    except:
        return exception_factory('Error removing project folder', runid=runid)

    try:
        run = Run.query.filter(Run.runid == runid).first()
        user_datastore.delete_run(run)
    except:
        return exception_factory('Error removing run from database', runid=runid)

    return success_factory()


@app.route('/runs/<string:runid>/<config>/tasks/clear_locks')
@app.route('/runs/<string:runid>/<config>/tasks/clear_locks/')
def clear_locks(runid, config):
    # get working dir of original directory
    wd = get_wd(runid)

    try:

        # delete any active locks
        locks = glob(_join(wd, '*.lock'))
        for fn in locks:
            
            if 'ron.nodb.lock' in fn:
                Ron.getInstance(wd).unlock('-f')
            elif 'landuse.nodb.lock' in fn:
                Landuse.getInstance(wd).unlock('-f')
            elif 'soils.nodb.lock' in fn:
                Soils.getInstance(wd).unlock('-f')
            elif 'climate.nodb.lock' in fn:
                Climate.getInstance(wd).unlock('-f')
            elif 'wepp.nodb.lock' in fn:
                Wepp.getInstance(wd).unlock('-f')
            elif 'watershed.nodb.lock' in fn:
                Watershed.getInstance(wd).unlock('-f')
            elif 'unitizer.nodb.lock' in fn:
                Unitizer.getInstance(wd).unlock('-f')
            elif 'topaz.nodb.lock' in fn:
                Topaz.getInstance(wd).unlock('-f')
            elif 'observed.nodb.lock' in fn:
                Observed.getInstance(wd).unlock('-f')
            elif 'rangeland_cover.nodb.lock' in fn:
                RangelandCover.getInstance(wd).unlock('-f')
            elif 'rhem.nodb.lock' in fn:
                Rhem.getInstance(wd).unlock('-f')
            elif 'disturbed.nodb.lock' in fn:
                Disturbed.getInstance(wd).unlock('-f')
            elif 'ash.nodb.lock' in fn:
                Ash.getInstance(wd).unlock('-f')
            elif 'revegetation.nodb.lock' in fn:
                from wepppy.nodb.mods import Revegetation
                Revegetation.getInstance(wd).unlock('-f')
            elif 'rap.nodb.lock' in fn:
                from wepppy.nodb.mods import RAP
                RAP.getInstance(wd).unlock('-f')
            elif 'rap_ts.nodb.lock' in fn:
                from wepppy.nodb.mods import RAP_TS
                RAP_TS.getInstance(wd).unlock('-f')
            else:
                os.remove(fn)

        return success_factory()

    except:
        return exception_factory('Error Clearing Locks', runid=runid)


@app.route('/runs/<string:runid>/<config>/archive')
@app.route('/runs/<string:runid>/<config>/archive/')
def archive(runid, config):

    try:
        # get working dir of original directory
        wd = get_wd(runid)

        from wepppy.export import archive_project, arc_export, legacy_arc_export
        from wepppy.export.prep_details import export_channels_prep_details, export_hillslopes_prep_details

        legacy = request.args.get('legacy', None) is not None

        if legacy:
            try:
                ron = Ron.getInstance(wd)
                if len(glob(_join(ron.export_arc_dir, '*.shp'))) == 0:
                    legacy_arc_export(wd)
            except Exception:
                return exception_factory('Error running legacy_arc_export', runid=runid)

        ron = Ron.getInstance(wd)
        if not _exists( _join(ron.export_dir, 'prep_details', 'hillslopes.csv')):
            export_hillslopes_prep_details(wd)

        if not _exists(_join(ron.export_dir, 'prep_details', 'channels.csv')):
            export_channels_prep_details(wd)


        archive_path = archive_project(wd)
        return send_file(archive_path, as_attachment=True, download_name='{}.zip'.format(runid))

    except:
        return exception_factory('Error Archiving Project', runid=runid)


@app.route('/runs/<string:runid>/<config>/meta/subcatchments.WGS.json')
@app.route('/runs/<string:runid>/<config>/meta/subcatchments.WGS.json/')
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


def log_access(wd, current_user, ip):
    assert _exists(wd)

    fn, runid = _split(wd)
    fn = _join(fn, '.{}'.format(runid))
    with open(fn, 'a') as fp:
        email = getattr(current_user, 'email', '<anonymous>')
        fp.write('{},{},{}\n'.format(email, ip, datetime.now()))


@app.route('/runs/<string:runid>/')
def runs0_nocfg(runid):

    wd = get_wd(runid)
    owners = get_run_owners(runid)
    try:
        ron = Ron.getInstance(wd)
    except FileNotFoundError:
        abort(404)

    return redirect(url_for('runs0', runid=runid, config=ron.config_stem))


@app.route('/runs/<string:runid>/<config>/')
def runs0(runid, config):

    from wepppy.nodb.mods.revegetation import Revegetation

    assert config is not None

    wd = get_wd(runid)
    owners = get_run_owners(runid)
    try:
        ron = Ron.getInstance(wd)
    except FileNotFoundError:
        abort(404)

    # check config
    if config != ron.config_stem:
        return redirect(url_for('runs0', runid=runid, config=ron.config_stem))

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
        site_prefix = app.config['SITE_PREFIX']

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

        from wepp_runner.wepp_runner import linux_wepp_bin_opts


        log_access(wd, current_user, request.remote_addr)
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
                               rq_job_ids=rq_job_ids,
                               landuseoptions=landuseoptions,
                               soildboptions=soildboptions,
                               critical_shear_options=critical_shear_options,
                               precisions=wepppy.nodb.unitizer.precisions,
                               run_id=runid)
    except:
        return exception_factory(runid=runid)


# https://wepp.cloud/weppcloud/runs/proletarian-respondent/baer/hillslope/21/ash/?fire_date=8.4&ash_type=white&ini_ash_depth=5.0
@app.route('/runs/<string:runid>/<config>/hillslope/<topaz_id>/ash')
@app.route('/runs/<string:runid>/<config>/hillslope/<topaz_id>/ash/')
def hillslope0_ash(runid, config, topaz_id):
    assert config is not None

    from wepppy.climates.cligen import ClimateFile

    wd = get_wd(runid)

    try:
        owners = get_run_owners(runid)
        ron = Ron.getInstance(wd)

        should_abort = True
        if current_user in owners:
            should_abort = False

        if not owners:
            should_abort = False

        if current_user.has_role('Admin'):
            should_abort = False

        if ron.public:
            should_abort = False

        #if should_abort:
        #    abort(404)

        fire_date = request.args.get('fire_date', None)
        if fire_date is None:
            fire_date = '8/4'
        _fire_date = YearlessDate.from_string(fire_date)

        ini_ash_depth = request.args.get('ini_ash_depth', None)
        if ini_ash_depth is None:
            ini_ash_depth = 5.0
        ini_ash_depth = float(ini_ash_depth)

        ash_type = request.args.get('ash_type', None)
        if ash_type is None:
            ash_type = 'black'

        _ash_type = None
        if 'black' in ash_type.lower():
            _ash_type = AshType.BLACK
        elif 'white' in ash_type.lower():
            _ash_type = AshType.WHITE

        ash_dir = _join(wd, '_ash')
        if not _exists(ash_dir):
            os.mkdir(ash_dir)

        unitizer = Unitizer.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        wepp_id = translator.wepp(top=topaz_id)
        sub = watershed.sub_summary(topaz_id)
        climate = Climate.getInstance(wd)
        wepp = Wepp.getInstance(wd)
        ash = Ash.getInstance(wd)
    
        cli_path = climate.cli_path
        cli_df = ClimateFile(cli_path).as_dataframe()

        element_fn = _join(wepp.output_dir, 'H{wepp_id}.element.dat'.format(wepp_id=wepp_id))
        element = Element(element_fn)

        hill_wat_fn = _join(wepp.output_dir, 'H{wepp_id}.wat.dat'.format(wepp_id=wepp_id))
        hill_wat = HillWat(hill_wat_fn)

        prefix = 'H{wepp_id}'.format(wepp_id=wepp_id)
        recurrence = [100, 50, 20, 10, 2.5, 1]

        from wepppy.nodb.mods.ash_transport.ash_multi_year_model import WhiteAshModel, BlackAshModel

        if _ash_type == AshType.BLACK:
            _, results, annuals = BlackAshModel().run_model(_fire_date, element.d, cli_df, hill_wat,
                                                            ash_dir, prefix=prefix, recurrence=recurrence,
                                                            ini_ash_depth=ini_ash_depth)
        elif _ash_type == AshType.WHITE:
            _, results, annuals = WhiteAshModel().run_model(_fire_date, element.d, cli_df, hill_wat,
                                                            ash_dir, prefix=prefix, recurrence=recurrence,
                                                            ini_ash_depth=ini_ash_depth)
        else:
            raise ValueError

        results = json.loads(json.dumps(results))
        annuals = json.loads(json.dumps(annuals))

        #return jsonify(dict(results=results, recurrence_intervals=recurrence))

        return render_template('reports/ash/ash_hillslope.htm',
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               sub=sub,
                               ash_type=ash_type,
                               ini_ash_depth=5.0,
                               fire_date=fire_date,
                               recurrence_intervals=recurrence,
                               results=results,
                               annuals=annuals,
                               ron=ron,
                               user=current_user)

    except:
        return exception_factory('Error loading ash hillslope results', runid=runid)

# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/adduser/', methods=['POST'])
@login_required
def task_adduser(runid, config):
    owners = get_run_owners(runid)

    should_abort = True
    if current_user in owners:
        should_abort = False

    if current_user.has_role('Admin'):
        should_abort = False

    if should_abort:
        return error_factory('Authentication Error')

    try:
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
        return exception_factory()

# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/removeuser/', methods=['POST'])
@login_required
def task_removeuser(runid, config):

    owners = get_run_owners(runid)

    should_abort = True
    if current_user in owners:
        should_abort = False

    if current_user.has_role('Admin'):
        should_abort = False

    if should_abort:
        return error_factory('Authentication Error')

    user_id = request.json.get('user_id')
    user = User.query.filter(User.id == user_id).first()
    run = Run.query.filter(Run.runid == runid).first()

    assert user is not None, user
    assert user in owners, user
    assert run is not None, run

    user_datastore.remove_run_to_user(user, run)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/report/users/')
@login_required
def report_users(runid, config):

    owners = get_run_owners(runid)

    should_abort = True
    if current_user in owners:
        should_abort = False

    if current_user.has_role('Admin'):
        should_abort = False

    if should_abort:
        return error_factory('Authentication Error')

    return render_template('reports/users.htm', owners=owners)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/resources/netful.json')
def resources_netful_geojson(runid, config):
    try:
        wd = get_wd(runid)
        watershed = Watershed.getInstance(wd)
        fn = watershed.netful_shp
        return send_file(fn, mimetype='application/json')
    except Exception:
        return exception_factory(runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/resources/subcatchments.json')
def resources_subcatchments_geojson(runid, config):
    try:
        wd = get_wd(runid)
#        watershed = Watershed.getInstance(wd)
#        fn = watershed.subwta_shp

        fn = _join(wd, 'dem/topaz/SUBCATCHMENTS.WGS.JSON')
        if not _exists(fn):
            fn = _join(wd, 'dem/taudem/subcatchments.WGS.geojson')

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


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/resources/bound.json')
def resources_bounds_geojson(runid, config):
    try:
        wd = get_wd(runid)
#        watershed = Watershed.getInstance(wd)
        fn = _join(wd, 'dem/topaz/BOUND.WGS.JSON')
        if not _exists(fn):
            fn = _join(wd, 'dem/taudem/bound.WGS.geojson')

        fn2 = fn.split('.')
        fn2.insert(-1, 'opt')
        fn2 = '.'.join(fn2)
        if _exists(fn2):
            return send_file(fn2)
        
        cmd = ['ogr2ogr', fn2, fn, '-simplify', '0.002']

        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        p.wait()

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


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/resources/channels.json')
def resources_channels_geojson(runid, config):
    try:
        wd = get_wd(runid)
        watershed = Watershed.getInstance(wd)
        fn = watershed.channels_shp

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


@app.route('/runs/<string:runid>/<config>/tasks/setname/', methods=['POST'])
def task_setname(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    ron.name = request.form.get('name', 'Untitled')
    return success_factory()


@app.route('/runs/<string:runid>/<config>/tasks/setscenario/', methods=['POST'])
def task_setscenario(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    ron.scenario = request.form.get('scenario', '')
    return success_factory()


@app.route('/runs/<string:runid>/<config>/report/tasks/set_unit_preferences/', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/set_unit_preferences/', methods=['POST'])
def task_set_unit_preferences(runid, config):
    try:
        wd = get_wd(runid)
        unitizer = Unitizer.getInstance(wd)
        res = unitizer.set_preferences(request.form)
        return success_factory(res)
    except:
        return exception_factory('Error setting unit preferences', runid=runid)


@app.route('/runs/<string:runid>/<config>/query/delineation_pass')
@app.route('/runs/<string:runid>/<config>/query/delineation_pass/')
def query_topaz_pass(runid, config):
    try:
        wd = get_wd(runid)
        watershed = Watershed.getInstance(wd)
        has_channels = watershed.has_channels
        has_subcatchments = watershed.has_subcatchments

        if not has_channels:
            return jsonify(0)

        if has_channels and not has_subcatchments:
            return jsonify(1)

        if has_channels and has_subcatchments:
            return jsonify(2)

        return None
    except:
        return exception_factory(runid=runid)


@app.route('/runs/<string:runid>/<config>/query/extent')
@app.route('/runs/<string:runid>/<config>/query/extent/')
def query_extent(runid, config):
    wd = get_wd(runid)

    return jsonify(Ron.getInstance(wd).extent)


@app.route('/runs/<string:runid>/<config>/report/channel')
@app.route('/runs/<string:runid>/<config>/report/channel/')
def report_channel(runid, config):
    wd = get_wd(runid)

    return render_template('reports/channel.htm',
                           map=Ron.getInstance(wd).map)


@app.route('/runs/<string:runid>/<config>/query/outlet')
@app.route('/runs/<string:runid>/<config>/query/outlet/')
def query_outlet(runid, config):
    wd = get_wd(runid)

    return jsonify(Watershed.getInstance(wd)
                        .outlet
                        .as_dict())


@app.route('/runs/<string:runid>/<config>/report/outlet')
@app.route('/runs/<string:runid>/<config>/report/outlet/')
def report_outlet(runid, config):
    wd = get_wd(runid)

    return render_template('reports/outlet.htm',
                           outlet=Watershed.getInstance(wd).outlet,
                           ron=Ron.getInstance(wd))


# noinspection PyBroadException
@deprecated
@app.route('/runs/<string:runid>/<config>/tasks/set_outlet/', methods=['POST'])
def task_set_outlet(runid, config):
    try:
        lat = float(request.form.get('latitude', None))
        lng = float(request.form.get('longitude', None))
    except Exception:
        return exception_factory('latitude and longitude must be provided as floats', runid=runid)

    wd = get_wd(runid)
    watershed = Watershed.getInstance(wd)

    try:
        watershed.set_outlet(lng, lat)
    except Exception:
        return exception_factory('Could not set outlet', runid=runid)

    return success_factory()


@app.route('/runs/<string:runid>/<config>/query/has_dem')
@app.route('/runs/<string:runid>/<config>/query/has_dem/')
def query_has_dem(runid, config):
    wd = get_wd(runid)
    return jsonify(Ron.getInstance(wd).has_dem)


# noinspection PyBroadException
def _parse_map_change(form):

    center = form.get('map_center', None)
    zoom = form.get('map_zoom', None)
    bounds = form.get('map_bounds', None)
    mcl = form.get('mcl', None)
    csa = form.get('csa', None)

    if center is None or zoom is None or bounds is None \
            or mcl is None or csa is None:
        error = error_factory('Expecting center, zoom, bounds, mcl, and csa')
        return error, None
    try:
        center = [float(v) for v in center.split(',')]
        zoom = float(zoom)
        extent = [float(v) for v in bounds.split(',')]
        assert len(extent) == 4
        l, b, r, t = extent
        assert l < r and b < t, (l, b, r, t)
    except Exception:
        error = exception_factory('Could not parse center, zoom, and/or bounds')
        return error, None

    try:
        mcl = float(mcl)
    except Exception:
        error = exception_factory('Could not parse mcl')
        return error, None

    try:
        csa = float(csa)
    except Exception:
        error = exception_factory('Could not parse csa')
        return error, None

    return None,  [extent, center, zoom, mcl, csa]


# noinspection PyBroadException

@deprecated
@app.route('/runs/<string:runid>/<config>/tasks/fetch_dem/', methods=['POST'])
def task_fetch_dem(runid, config):
    error, args = _parse_map_change(request.form)

    if error is not None:
        return jsonify(error)

    extent, center, zoom, mcl, csa = args

    # Acquire DEM from wmesque server
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        ron.set_map(extent, center, zoom)
        ron.fetch_dem()
    except Exception:
        return exception_factory('Fetching DEM Failed', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/export/ermit/')
def export_ermit(runid, config):
    try:
        from wepppy.export import create_ermit_input
        wd = get_wd(runid)
        fn = create_ermit_input(wd)
        name = _split(fn)[-1]
        return send_file(fn, as_attachment=True, download_name=name)
    except:
        return exception_factory('Error exporting ERMiT', runid=runid)


@app.route('/runs/<string:runid>/<config>/export/arcmap')
@app.route('/runs/<string:runid>/<config>/export/arcmap/')
def export_arcmap(runid, config):
    from wepppy.export import gpkg_export, archive_project, legacy_arc_export

    # get working dir of original directory
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    legacy = request.args.get('legacy', None) is not None
    no_cache = True

    if legacy:
        try:
            if len(glob(_join(ron.export_legacy_arc_dir, '*.shp'))) == 0:
                legacy_arc_export(wd)
        except Exception:
            return exception_factory('Error running legacy_arc_export', runid=runid)

        try:
            if not request.args.get('no_retrieve', None) is not None:
                archive_path = archive_project(ron.export_legacy_arc_dir)
                return send_file(archive_path, as_attachment=True, download_name=f'{runid}_arcmap.zip')
            else:
                return success_factory()

        except Exception:
            return exception_factory('Error running arc_export', runid=runid)

    else:
        try:
            if len(glob(_join(ron.export_arc_dir, '*.gpkg'))) == 0 or no_cache:
                gpkg_export(wd)
        except Exception:
            return exception_factory('Error running arc_export', runid=runid)

        try:
            if not request.args.get('no_retrieve', None) is not None:
                archive_path = archive_project(ron.export_arc_dir)
                return send_file(archive_path, as_attachment=True, download_name=f'{runid}_arcmap.zip')
            else:
                return success_factory()

        except Exception:
            return exception_factory('Error running arc_export', runid=runid)


@app.route('/runs/<string:runid>/<config>/export/prep_details')
@app.route('/runs/<string:runid>/<config>/export/prep_details/')
def export_prep_details(runid, config):
    # get working dir of original directory
    wd = get_wd(runid)

    from wepppy.export import archive_project
    from wepppy.export.prep_details import export_channels_prep_details, export_hillslopes_prep_details

    try:
        export_hillslopes_prep_details(wd)
        fn = export_channels_prep_details(wd)
    except Exception:
        return exception_factory(runid=runid)

    if not request.args.get('no_retrieve', None) is not None:
        archive_path = archive_project(_split(fn)[0])
        return send_file(archive_path, as_attachment=True, download_name='{}_prep_details.zip'.format(runid))
    else:
        return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/export/winwepp/')
def export_winwepp(runid, config):
    from wepppy.export import export_winwepp
    wd = get_wd(runid)
    export_winwepp_path = export_winwepp(wd)
    return send_file(export_winwepp_path, as_attachment=True, download_name='{}_winwepp.zip'.format(runid))


# noinspection PyBroadException
@deprecated
@app.route('/runs/<string:runid>/<config>/tasks/build_channels/', methods=['POST'])
def task_build_channels(runid, config):

    error, args = _parse_map_change(request.form)

    if error is not None:
        return jsonify(error)

    extent, center, zoom, mcl, csa = args

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    set_and_fetch = False
    if ron.map is None:
        set_and_fetch = True

    # determine whether we need to fetch dem
    elif ''.join(['%.7f' % v for v in ron.map.extent]) != \
       ''.join(['%.7f' % v for v in extent]):
        set_and_fetch = True

    if set_and_fetch:
        ron.set_map(extent, center, zoom)

        if not ron.dem_map:
            # Acquire DEM from WMesque server
            try:
                ron.fetch_dem()
            except Exception:
                return exception_factory('Fetching DEM Failed', runid=runid)

    # Delineate channels
    watershed = Watershed.getInstance(wd)
    try:
        watershed.build_channels(csa=csa, mcl=mcl)

    except Exception as e:
        if isinstance(e, MinimumChannelLengthTooShortError):
            return exception_factory(e.__name__, e.__doc__, runid=runid)
        else:
            return exception_factory('Building Channels Failed', runid=runid)

    return success_factory()


@deprecated
@app.route('/runs/<string:runid>/<config>/tasks/build_subcatchments/', methods=['POST'])
def task_build_subcatchments(runid, config):

    pkcsa = request.form.get('pkcsa', None)
    try:
        pkcsa = float(pkcsa)
    except:
        pass

    clip_hillslope_length = request.form.get('clip_hillslope_length', None)
    try:
        clip_hillslope_length = float(clip_hillslope_length)
    except:
        pass

    clip_hillslopes = request.form.get('clip_hillslopes', 'off')
    try:
        clip_hillslopes = clip_hillslopes.lower().startswith('on')
    except:
        pass

    walk_flowpaths = request.form.get('walk_flowpaths', 'off')
    try:
        walk_flowpaths = walk_flowpaths.lower().startswith('on')
    except:
        pass

    mofe_target_length = request.form.get('mofe_target_length', None)
    try:
        mofe_target_length = float(mofe_target_length)
    except:
        pass

    mofe_buffer = request.form.get('mofe_buffer', 'off')
    try:
        mofe_buffer = mofe_buffer.lower().startswith('on')
    except:
        pass

    bieger2015_widths = request.form.get('bieger2015_widths', 'off')
    try:
        bieger2015_widths = bieger2015_widths.lower().startswith('on')
    except:
        pass

    mofe_buffer_length = request.form.get('mofe_buffer_length', None)
    try:
        mofe_buffer_length = float(mofe_buffer_length)
    except:
        pass

    try:
        wd = get_wd(runid)
        watershed = Watershed.getInstance(wd)
        wepp = Watershed.getInstance(wd)

        if clip_hillslopes is not None:
            watershed.clip_hillslopes = clip_hillslopes

        if walk_flowpaths is not None:
            watershed.walk_flowpaths = walk_flowpaths

        if clip_hillslope_length is not None:
            watershed.clip_hillslope_length = clip_hillslope_length

        if mofe_target_length is not None:
            watershed.mofe_target_length = mofe_target_length

        if mofe_buffer is not None:
            watershed.mofe_buffer = mofe_buffer

        if mofe_buffer_length is not None:
            watershed.mofe_buffer_length = mofe_buffer_length

        if bieger2015_widths is not None:
            watershed.bieger2015_widths = bieger2015_widths

        try:
            watershed.build_subcatchments(pkcsa=pkcsa)
        except Exception as e:
            if isinstance(e, WatershedBoundaryTouchesEdgeError):
                return exception_factory(e.__name__, e.__doc__, runid=runid)
            else:
                return exception_factory('Building Subcatchments Failed', runid=runid)

        return success_factory()
    except:
        return exception_factory('Building Subcatchments Failed', runid=runid)


@app.route('/runs/<string:runid>/<config>/query/watershed/subcatchments')
@app.route('/runs/<string:runid>/<config>/query/watershed/subcatchments/')
def query_watershed_summary_subcatchments(runid, config):
    wd = get_wd(runid)
    return jsonify(Watershed.getInstance(wd).subs_summary)


@app.route('/runs/<string:runid>/<config>/query/watershed/channels')
@app.route('/runs/<string:runid>/<config>/query/watershed/channels/')
def query_watershed_summary_channels(runid, config):
    wd = get_wd(runid)
    return jsonify(Watershed.getInstance(wd).chns_summary)


@app.route('/runs/<string:runid>/<config>/report/watershed')
@app.route('/runs/<string:runid>/<config>/report/watershed/')
def query_watershed_summary(runid, config):
    try:
        wd = get_wd(runid)
        return render_template('reports/subcatchments.htm',
                               user=current_user,
                               watershed=Watershed.getInstance(wd))
    except:
        return exception_factory(runid=runid)


@app.route('/runs/<string:runid>/<config>/tasks/abstract_watershed/', methods=['GET', 'POST'])
def task_abstract_watershed(runid, config):
    wd = get_wd(runid)
    watershed = Watershed.getInstance(wd)

    try:
        watershed.abstract_watershed()
    except Exception as e:
        if isinstance(e, ChannelRoutingError):
            return exception_factory(e.__name__, e.__doc__, runid=runid)
        else:
            return exception_factory('Abstracting Watershed Failed', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/sub_intersection/', methods=['POST'])
def sub_intersection(runid, config):
    try:
        wd = get_wd(runid)

        extent = request.json.get('extent', None)

        ron = Ron.getInstance(wd)
        _map = ron.map

        subwta_fn = Watershed.getInstance(wd).subwta

        topaz_ids = _map.raster_intersection(extent, raster_fn=subwta_fn, discard=(0,))
        return jsonify(topaz_ids)
    except:
        return exception_factory(runid=runid)


@app.route('/runs/<string:runid>/<config>/query/rangeland_cover/current_cover_summary/', methods=['POST'])
def query_rangeland_cover_current(runid, config):
    wd = get_wd(runid)

    topaz_ids = request.json.get('topaz_ids', None)
    topaz_ids = [x for x in topaz_ids if x != '']

    return jsonify(RangelandCover.getInstance(wd).current_cover_summary(topaz_ids))


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_rangeland_cover_mode/', methods=['POST'])
def set_rangeland_cover_mode(runid, config):

    mode = None
    rap_year = None
    try:
        mode = int(request.form.get('mode', None))
        rap_year = int(request.form.get('rap_year', None))
    except Exception:
        exception_factory('mode and rap_year must be provided', runid=runid)

    wd = get_wd(runid)
    rangeland_cover = RangelandCover.getInstance(wd)

    try:
        rangeland_cover.mode = RangelandCoverMode(mode)
        rangeland_cover.rap_year = rap_yearsingle_selection
    except Exception:
        exception_factory('error setting mode or rap_year', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_landuse_mode/', methods=['POST'])
def set_landuse_mode(runid, config):

    mode = None
    single_selection = None
    try:
        mode = int(request.form.get('mode', None))
        single_selection = \
            int(request.form.get('landuse_single_selection', None))
    except Exception:
        exception_factory('mode and landuse_single_selection must be provided', runid=runid)

    wd = get_wd(runid)
    landuse = Landuse.getInstance(wd)

    try:
        landuse.mode = LanduseMode(mode)
        landuse.single_selection = single_selection
    except Exception:
        exception_factory('error setting landuse mode', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_landuse_db/', methods=['POST'])
def set_landuse_db(runid, config):

    mode = None
    single_selection = None
    try:
        db = request.form.get('landuse_db', None)
    except Exception:
        exception_factory('landuse_db must be provided', runid=runid)

    wd = get_wd(runid)
    landuse = Landuse.getInstance(wd)

    try:
        landuse.nlcd_db = db
    except Exception:
        exception_factory('error setting landuse mode', runid=runid)

    return success_factory()


@app.route('/runs/<string:runid>/<config>/tasks/modify_landuse_coverage', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/modify_landuse_coverage/', methods=['POST'])
def modify_landuse_coverage(runid, config):
    wd = get_wd(runid)

    dom = request.json.get('dom', None)
    cover = request.json.get('cover', None)
    value = request.json.get('value', None)

    Landuse.getInstance(wd).modify_coverage(dom, cover, value)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/modify_landuse_mapping/', methods=['POST'])
def task_modify_landuse_mapping(runid, config):
    wd = get_wd(runid)

    dom = request.json.get('dom', None)
    newdom = request.json.get('newdom', None)

    landuse = Landuse.getInstance(wd)
    landuse.modify_mapping(dom, newdom)

    return success_factory()


@app.route('/runs/<string:runid>/<config>/tasks/modify_rangeland_cover/', methods=['POST'])
def task_modify_rangeland_cover(runid, config):
    wd = get_wd(runid)

    topaz_ids = request.json.get('topaz_ids', None)
    covers = request.json.get('covers', None)

    assert topaz_ids is not None
    assert covers is not None

    for measure, value in covers.items():
        value = float(value)
        covers[measure] = float(value)
        if value < 0.0 or value > 100.0:
            return Exception('covers must be between 0 and 100')

    rangeland_cover = RangelandCover.getInstance(wd)
    rangeland_cover.modify_covers(topaz_ids, covers)

    return success_factory()


@app.route('/runs/<string:runid>/<config>/query/landuse')
@app.route('/runs/<string:runid>/<config>/query/landuse/')
def query_landuse(runid, config):
    wd = get_wd(runid)
    return jsonify(Landuse.getInstance(wd).domlc_d)


@app.route('/runs/<string:runid>/<config>/resources/legends/slope_aspect')
@app.route('/runs/<string:runid>/<config>/resources/legends/slope_aspect/')
def resources_slope_aspect_legend(runid, config):
    wd = get_wd(runid)

    return render_template('legends/slope_aspect.htm')


@app.route('/runs/<string:runid>/<config>/resources/legends/landuse')
@app.route('/runs/<string:runid>/<config>/resources/legends/landuse/')
def resources_landuse_legend(runid, config):
    wd = get_wd(runid)

    return render_template('legends/landuse.htm',
                           legend=Landuse.getInstance(wd).legend)


@app.route('/runs/<string:runid>/<config>/resources/legends/soil')
@app.route('/runs/<string:runid>/<config>/resources/legends/soil/')
def resources_soil_legend(runid, config):
    wd = get_wd(runid)

    return render_template('legends/soil.htm',
                           legend=Soils.getInstance(wd).legend)


@app.route('/runs/<string:runid>/<config>/resources/legends/sbs')
@app.route('/runs/<string:runid>/<config>/resources/legends/sbs/')
def resources_sbs_legend(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    if 'baer' in ron.mods:
        baer = Baer.getInstance(wd)
    else:
        baer = Disturbed.getInstance(wd)

    return render_template('legends/landuse.htm',
                           legend=baer.legend)


@app.route('/resources/usgs/gage_locations/')
def resources_usgs_gage_locations():
    bbox = request.args.get('bbox')
    bbox = literal_eval(bbox)
    return jsonify(crop_geojson(_join(_thisdir, 'static/resources/usgs/usgs_gage_locations.geojson'), bbox=bbox))


@app.route('/runs/<string:runid>/<config>/query/landuse/subcatchments')
@app.route('/runs/<string:runid>/<config>/query/landuse/subcatchments/')
def query_landuse_subcatchments(runid, config):
    wd = get_wd(runid)
    return jsonify(Landuse.getInstance(wd).subs_summary)


@app.route('/runs/<string:runid>/<config>/query/landuse/channels')
@app.route('/runs/<string:runid>/<config>/query/landuse/channels/')
def query_landuse_channels(runid, config):
    wd = get_wd(runid)
    return jsonify(Landuse.getInstance(wd).chns_summary)


@app.route('/runs/<string:runid>/<config>/report/landuse')
@app.route('/runs/<string:runid>/<config>/report/landuse/')
def report_landuse(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:

        landuse = Landuse.getInstance(wd)
        landuseoptions = landuse.landuseoptions

        return render_template('reports/landuse.htm',
                               landuse=landuse,
                               landuseoptions=landuseoptions,
                               report=landuse.report)

    except Exception:
        return exception_factory('Reporting landuse failed', runid=runid)

@app.route('/runs/<string:runid>/<config>/query/rangeland_cover/subcatchments')
@app.route('/runs/<string:runid>/<config>/query/rangeland_cover/subcatchments/')
def query_rangeland_cover_subcatchments(runid, config):
    wd = get_wd(runid)
    return jsonify(RangelandCover.getInstance(wd).subs_summary)


@app.route('/runs/<string:runid>/<config>/report/rangeland_cover')
@app.route('/runs/<string:runid>/<config>/report/rangeland_cover/')
def report_rangeland_cover(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    rangeland_cover = RangelandCover.getInstance(wd)

    return render_template('reports/rangeland_cover.htm',
                           rangeland_cover=rangeland_cover)


@app.route('/runs/<string:runid>/<config>/view/channel_def/<chn_key>')
@app.route('/runs/<string:runid>/<config>/view/channel_def/<chn_key>/')
def view_channel_def(runid, config, chn_key):
    wd = get_wd(runid)
    assert wd is not None

    try:
        chn_d = management.get_channel(chn_key)
    except KeyError:
        return error_factory('Could not find channel def with key "%s"' % chn_key)

    return jsonify(chn_d)

@deprecated
@app.route('/runs/<string:runid>/<config>/tasks/build_landuse/', methods=['POST'])
def task_build_landuse(runid, config):
    mofe_buffer_selection = request.form.get('mofe_buffer_selection', None)
    try:
        mofe_buffer_selection = int(mofe_buffer_selection)
    except:
        pass

    wd = get_wd(runid)
    landuse = Landuse.getInstance(wd)

    if mofe_buffer_selection is not None:
        landuse.mofe_buffer_selection = mofe_buffer_selection

    try:
        landuse.build()
    except Exception as e:
        if isinstance(e, WatershedNotAbstractedError):
            return exception_factory(e.__name__, e.__doc__, runid=runid)
        else:
            return exception_factory('Building Landuse Failed', runid=runid)

    return success_factory()


@app.route('/runs/<string:runid>/<config>/tasks/build_rangeland_cover/', methods=['POST'])
def task_build_rangeland_cover(runid, config):
    wd = get_wd(runid)
    rangeland_cover = RangelandCover.getInstance(wd)

    rap_year = request.form.get('rap_year')

    default_covers = dict(
        bunchgrass=request.form.get('bunchgrass_cover'),
        forbs=request.form.get('forbs_cover'),
        sodgrass=request.form.get('sodgrass_cover'),
        shrub=request.form.get('shrub_cover'),
        basal=request.form.get('basal_cover'),
        rock=request.form.get('rock_cover'),
        litter=request.form.get('litter_cover'),
        cryptogams=request.form.get('cryptogams_cover'))

    try:
        rangeland_cover.build(rap_year=rap_year, default_covers=default_covers)
    except Exception:
        return exception_factory('Building RangelandCover Failed')

    return success_factory()


@app.route('/runs/<string:runid>/<config>/view/management/<key>')
@app.route('/runs/<string:runid>/<config>/view/management/<key>/')
def view_management(runid, config, key):
    wd = get_wd(runid)
    assert wd is not None

    try:
        landuse = Landuse.getInstance(wd)
        man = landuse.managements[str(key)].get_management()
        contents = repr(man)

        r = Response(response=contents, status=200, mimetype="text/plain")
        r.headers["Content-Type"] = "text/plain; charset=utf-8"
        return r

    except Exception:
        return exception_factory('Error retrieving management', runid=runid)

# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/modify_landuse/', methods=['POST'])
def task_modify_landuse(runid, config):
    wd = get_wd(runid)
    landuse = Landuse.getInstance(wd)

    try:
        topaz_ids = request.form.get('topaz_ids', None)
        topaz_ids = topaz_ids.split(',')
        topaz_ids = [str(int(v)) for v in topaz_ids]
        lccode = request.form.get('landuse', None)
        lccode = str(int(lccode))
    except Exception:
        return exception_factory('Unpacking Modify Landuse Args Faied', runid=runid)

    try:
        landuse.modify(topaz_ids, lccode)
    except Exception:
        return exception_factory('Modifying Landuse Failed', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_soil_mode/', methods=['POST'])
def set_soil_mode(runid, config):

    mode = None
    single_selection = None

    try:
        mode = int(request.form.get('mode', None))
        single_selection = \
            int(request.form.get('soil_single_selection', None))

        single_dbselection = \
            request.form.get('soil_single_dbselection', None)

    except Exception:
        exception_factory('mode and soil_single_selection must be provided', runid=runid)

    wd = get_wd(runid)

    try:
        soils = Soils.getInstance(wd)
        soils.mode = SoilsMode(mode)
        soils.single_selection = single_selection
        soils.single_dbselection = single_dbselection

    except Exception:
        exception_factory('error setting soils mode', runid=runid)

    return success_factory()


@app.route('/runs/<string:runid>/<config>/query/soils')
@app.route('/runs/<string:runid>/<config>/query/soils/')
def query_soils(runid, config):
    wd = get_wd(runid)
    return jsonify(Soils.getInstance(wd).domsoil_d)


@app.route('/runs/<string:runid>/<config>/query/soils/subcatchments')
@app.route('/runs/<string:runid>/<config>/query/soils/subcatchments/')
def query_soils_subcatchments(runid, config):
    wd = get_wd(runid)
    return jsonify(Soils.getInstance(wd).subs_summary)


@app.route('/runs/<string:runid>/<config>/query/soils/channels')
@app.route('/runs/<string:runid>/<config>/query/soils/channels/')
def query_soils_channels(runid, config):
    wd = get_wd(runid)
    return jsonify(Soils.getInstance(wd).chns_summary)


@app.route('/runs/<string:runid>/<config>/report/soils')
@app.route('/runs/<string:runid>/<config>/report/soils/')
def report_soils(runid, config):
    try:
        wd = get_wd(runid)
        return render_template('reports/soils.htm',
                               report=Soils.getInstance(wd).report)
    except Exception as e:
        return exception_factory('Building Soil Failed', runid=runid)


@deprecated
@app.route('/runs/<string:runid>/<config>/tasks/build_soil/', methods=['POST'])
def task_build_soil(runid, config):
    wd = get_wd(runid)

    try:
        soils = Soils.getInstance(wd)
        initial_sat = float(request.form.get('initial_sat'))

        if 'disturbed' in soils.mods:
            disturbed = Disturbed.getInstance(wd)
            disturbed.sol_ver = float(request.form.get('sol_ver'))

        soils.build(initial_sat=initial_sat)
    except Exception as e:
        if isinstance(e, NoValidSoilsException) or isinstance(e, WatershedNotAbstractedError):
            return exception_factory(e.__name__, e.__doc__, runid=runid)
        else:
            return exception_factory('Building Soil Failed', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_climatestation_mode/', methods=['POST'])
def set_climatestation_mode(runid, config):

    try:
        mode = int(request.form.get('mode', None))
    except Exception:
        return exception_factory('Could not determine mode', runid=runid)

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climatestation_mode = ClimateStationMode(int(mode))
    except Exception:
        return exception_factory('Building setting climate station mode', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_climatestation/', methods=['POST'])
def set_climatestation(runid, config):

    try:
        station = request.form.get('station', None)
    except Exception:
        return exception_factory('Station not provided', runid=runid)

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climatestation = station
    except Exception:
        return exception_factory('Building setting climate station mode', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/upload_cli/', methods=['POST'])
def task_upload_cli(runid, config):
    wd = get_wd(runid)

    ron = Ron.getInstance(wd)
    climate = Climate.getInstance(wd)

    try:
        file = request.files['input_upload_cli']
    except Exception:
        return exception_factory('Could not find file', runid=runid)

    try:
        if file.filename == '':
            return error_factory('no filename specified')

        filename = secure_filename(file.filename)
    except Exception:
        return exception_factory('Could not obtain filename', runid=runid)

    try:
        file.save(_join(climate.cli_dir, filename))
    except Exception:
        return exception_factory('Could not save file', runid=runid)

    try:
        res = climate.set_user_defined_cli(filename)
    except Exception:
        return exception_factory('Failed validating file', runid=runid)

    return success_factory()


@app.route('/runs/<string:runid>/<config>/query/climatestation')
@app.route('/runs/<string:runid>/<config>/query/climatestation/')
def query_climatestation(runid, config):
    wd = get_wd(runid)
    return jsonify(Climate.getInstance(wd).climatestation)


@app.route('/runs/<string:runid>/<config>/query/climate_has_observed')
@app.route('/runs/<string:runid>/<config>/query/climate_has_observed/')
def query_climate_has_observed(runid, config):
    wd = get_wd(runid)
    return jsonify(Climate.getInstance(wd).has_observed)


@app.route('/runs/<string:runid>/<config>/report/climate/')
def report_climate(runid, config):
    wd = get_wd(runid)
 
    climate = Climate.getInstance(wd)
    return render_template('reports/climate.htm',
                           station_meta=climate.climatestation_meta,
                           climate=climate)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_climate_mode/', methods=['POST'])
def set_climate_mode(runid, config):
    try:
        mode = int(request.form.get('mode', None))
    except Exception:
        return exception_factory('Could not determine mode', runid=runid)

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climate_mode = mode
    except Exception:
        return exception_factory('Building setting climate mode', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_climate_spatialmode/', methods=['POST'])
def set_climate_spatialmode(runid, config):
    try:
        spatialmode = int(request.form.get('spatialmode', None))
    except Exception:
        return exception_factory('Could not determine mode', runid=runid)

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climate_spatialmode = spatialmode
    except Exception:
        return exception_factory('Building setting climate spatial mode', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/view/closest_stations/')
def view_closest_stations(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd, ignore_lock=True)

    if climate.readonly:
        results = climate.closest_stations
    else:
        try:
            results = climate.find_closest_stations()
        except Exception:
            return exception_factory('Error finding closest stations', runid=runid)

    if results is None:
        return Response('<!-- closest_stations is None -->', mimetype='text/html')

    options = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]
        options.append('<option value="{id}" {selected}>'
                       '{desc} ({distance_to_query_location:0.1f} km | {years} years)</option>'
                       .format(**r))

    return Response('n'.join(options), mimetype='text/html')


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/view/heuristic_stations/')
def view_heuristic_stations(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd, ignore_lock=True)

    if climate.readonly:
        results = climate.heuristic_stations
    else:
        try:
            results = climate.find_heuristic_stations()
        except Exception:
            return exception_factory('Error finding heuristic stations', runid=runid)

    if results is None:
        return Response('<!-- heuristic_stations is None -->', mimetype='text/html')

#    return jsonify(results)

    options = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]

        if r['distance_to_query_location'] is None:
            r['distance_to_query_location'] == -1

        options.append('<option value="{id}" {selected}>'
                       '{desc} ({rank_based_on_query_location} | '
                       '{distance_to_query_location:0.1f} km | {years} years)</option>'
                       .format(**r))

    return Response('n'.join(options), mimetype='text/html')


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/view/par/')
def view_station_par(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd, ignore_lock=True)
    contents = climate.climatestation_par_contents
    return Response(contents, content_type='text/plain;charset=utf-8')


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/view/eu_heuristic_stations/')
def view_eu_heuristic_stations(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        results = climate.find_eu_heuristic_stations()
    except Exception:
        return exception_factory('Error finding heuristic stations', runid=runid)

    if results is None:
        return Response('<!-- heuristic_stations is None -->', mimetype='text/html')

    options = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]
        options.append('<option value="{id}" {selected}>'
                       '{desc} ({rank_based_on_query_location} | {years} years)</option>'
                       .format(**r))

    return Response('n'.join(options), mimetype='text/html')

# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/view/au_heuristic_stations/')
def view_au_heuristic_stations(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        results = climate.find_au_heuristic_stations()
    except Exception:
        return exception_factory('Error finding heuristic stations', runid=runid)

    if results is None:
        return Response('<!-- heuristic_stations is None -->', mimetype='text/html')

    options = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]
        options.append('<option value="{id}" {selected}>'
                       '{desc} ({rank_based_on_query_location} | {years} years)</option>'
                       .format(**r))

    return Response('n'.join(options), mimetype='text/html')

# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/view/climate_monthlies')
@app.route('/runs/<string:runid>/<config>/view/climate_monthlies/')
def view_climate_monthlies(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        station_meta = climate.climatestation_meta
    except Exception:
        return exception_factory('Could not find climatestation_meta', runid=runid)

    if station_meta is None:
        return error_factory('Climate Station not Set')

    assert isinstance(station_meta, StationMeta)
    return render_template('controls/climate_monthlies.htm',
                           title='Summary for the selected station',
                           station=station_meta.as_dict(include_monthlies=True))


# noinspection PyBroadException
@deprecated
@app.route('/runs/<string:runid>/<config>/tasks/build_climate', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/build_climate/', methods=['POST'])
def task_build_climate(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.parse_inputs(request.form)
    except Exception:
        return exception_factory('Error parsing climate inputs', runid=runid)

    try:
        climate.build()
    except Exception as e:
        if isinstance(e, NoClimateStationSelectedError) or \
           isinstance(e, ClimateModeIsUndefinedError) or \
           isinstance(e, WatershedNotAbstractedError):
            return exception_factory(e.__name__, e.__doc__, runid=runid)
        else:
            return exception_factory('Error building climate', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_wepp_bin', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/set_wepp_bin/', methods=['POST'])
def task_set_wepp_bin(runid, config):
    try:
        wepp_bin = request.json.get('wepp_bin', None)
    except Exception:
        return exception_factory('Error parsing routine', runid=runid)

    if wepp_bin is None:
        return error_factory('wepp_bin is None')

    assert wepp_bin[:4] == 'wepp'
    assert '.' not in wepp_bin
    assert '/' not in wepp_bin
    assert '\\' not in wepp_bin

    try:
        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)
        wepp.wepp_bin = wepp_bin
    except Exception:
        return exception_factory('Error setting wepp_bin', runid=runid)

    return success_factory()

# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_run_wepp_routine', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/set_run_wepp_routine/', methods=['POST'])
def task_set_hourly_seepage(runid, config):

    try:
        routine = request.json.get('routine', None)
    except Exception:
        return exception_factory('Error parsing routine', runid=runid)

    if routine is None:
        return error_factory('routine is None')

    if routine not in ['wepp_ui', 'pmet', 'frost', 'tcr', 'snow', 'run_flowpaths']:
        return error_factory("routine not in ['wepp_ui', 'pmet', 'frost', 'tcr', 'snow', 'run_flowpaths']")

    try:
        state = request.json.get('state', None)
    except Exception:
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)

        if routine == 'wepp_ui':
            wepp.set_run_wepp_ui(state)
        elif routine == 'pmet':
            wepp.set_run_pmet(state)
        elif routine == 'frost':
            wepp.set_run_frost(state)
        elif routine == 'tcr':
            wepp.set_run_tcr(state)
        elif routine == 'snow':
            wepp.set_run_snow(state)
        elif routine == 'run_flowpaths':
            wepp.set_run_flowpaths(state)

    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()

# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_soils_ksflag', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/set_soils_ksflag/', methods=['POST'])
def task_set_soils_ksflag(runid, config):

    try:
        state = request.json.get('ksflag', None)
    except Exception:
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        soils = Soils.getInstance(wd)
        soils.ksflag = state
    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_disturbed_sol_ver', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/set_disturbed_sol_ver/', methods=['POST'])
def task_set_disturbed_sol_ver(runid, config):

    try:
        state = request.json.get('sol_ver', None)
    except Exception:
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        disturbed = Disturbed.getInstance(wd)
        disturbed.sol_ver = state
    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_run_flowpaths', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/set_run_flowpaths/', methods=['POST'])
def task_set_run_flowpaths(runid, config):

    try:
        state = request.json.get('run_flowpaths', None)
    except Exception:
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)
        wepp.set_run_flowpaths(state)
    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()

# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_public', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/set_public/', methods=['POST'])
def task_set_public(runid, config):
    owners = get_run_owners(runid)

    should_abort = True
    if current_user in owners:
        should_abort = False

    if current_user.has_role('Admin'):
        should_abort = False

    if should_abort:
        return error_factory('authentication error')

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


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/hasowners', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/hasowners/', methods=['POST'])
def get_owners(runid, config):
    owners = get_run_owners(runid)
    return jsonify(len(owners) > 0)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_readonly', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/set_readonly/', methods=['POST'])
def task_set_readonly(runid, config):
    owners = get_run_owners(runid)

    should_abort = True
    if current_user in owners:
        should_abort = False

    if current_user.has_role('Admin'):
        should_abort = False

    if should_abort:
        return error_factory('authentication error')

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


# noinspection PyBroadException
#@app.route('/runs/<string:runid>/<config>/query/status/<nodb>', methods=['GET', 'POST'])
#@app.route('/runs/<string:runid>/<config>/query/status/<nodb>/', methods=['GET', 'POST'])
def get_wepp_run_status(runid, config, nodb):
    wd = get_wd(runid)

    if nodb == 'wepp':
        wepp = Wepp.getInstance(wd)
        try:
            return success_factory(wepp.get_log_last())
        except:
            return exception_factory('Could not determine status', runid=runid)

    elif nodb == 'climate':
        climate = Climate.getInstance(wd)
        try:
            return success_factory(climate.get_log_last())
        except:
            return exception_factory('Could not determine status', runid=runid)

    elif nodb == 'rhem':
        rhem = Rhem.getInstance(wd)
        try:
            return success_factory(rhem.get_log_last())
        except:
            return exception_factory('Could not determine status', runid=runid)

    elif nodb == 'rap_ts':
        from wepppy.nodb.mods import RAP_TS
        rap_ts = RAP_TS.getInstance(wd)
        try:
            return success_factory(rap_ts.get_log_last())
        except:
            return exception_factory('Could not determine status', runid=runid)

    return error_factory('Unknown nodb')

# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/report/rhem/results')
@app.route('/runs/<string:runid>/<config>/report/rhem/results/')
def report_rhem_results(runid, config):
    wd = get_wd(runid)

    try:
        return render_template('controls/rhem_reports.htm')
    except:
        return exception_factory('Error building reports template', runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/report/wepp/results')
@app.route('/runs/<string:runid>/<config>/report/wepp/results/')
def report_wepp_results(runid, config):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)
    
    try:
        prep = RedisPrep.getInstance(wd)
    except FileNotFoundError:
        prep = None

    try:
        return render_template('controls/wepp_reports.htm',
                               climate=climate,
                               prep=prep,
                               user=current_user)
    except:
        return exception_factory('Error building reports template', runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/report/<nodb>/log')
@app.route('/runs/<string:runid>/<config>/report/<nodb>/log/')
def get_wepp_run_status_full(runid, config, nodb):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:
        if nodb == 'wepp':
            wepp = Wepp.getInstance(wd)
            with open(wepp.status_log) as fp:
                status_log = fp.read()
        elif nodb == 'climate':
            climate = Climate.getInstance(wd)
            with open(climate.status_log) as fp:
                status_log = fp.read()
        else:
            status_log = 'error'

        return render_template('reports/wepp/log.htm',
                               status_log=status_log,
                               ron=ron,
                               user=current_user)
    except:
        return exception_factory('Error reading status.log', runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/query/subcatchments_summary')
@app.route('/runs/<string:runid>/<config>/query/subcatchments_summary/')
def query_subcatchments_summary(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:
        subcatchments_summary = ron.subs_summary()

        return jsonify(subcatchments_summary)
    except:
        return exception_factory('Error building summary', runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/query/channels_summary')
@app.route('/runs/<string:runid>/<config>/query/channels_summary/')
def query_channels_summary(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:
        channels_summary = ron.chns_summary()

        return jsonify(channels_summary)
    except:
        return exception_factory('Error building summary', runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/report/wepp/prep_details')
@app.route('/runs/<string:runid>/<config>/report/wepp/prep_details/')
def get_wepp_prep_details(runid, config):

    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)

        subcatchments_summary = ron.subs_summary(abbreviated=True)
        channels_summary = ron.chns_summary(abbreviated=True)

        unitizer = Unitizer.getInstance(wd)

        return render_template('reports/wepp/prep_details.htm',
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               subcatchments_summary=subcatchments_summary,
                               channels_summary=channels_summary,
                               user=current_user,
                               ron=ron)
    except:
        return exception_factory('Error building summary', runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/run_wepp', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/run_wepp/', methods=['POST'])
def submit_task_run_wepp(runid, config):
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)

    try:
        wepp.parse_inputs(request.form)
    except Exception:
        return exception_factory('Error parsing climate inputs', runid=runid)

    soils = Soils.getInstance(wd)

    try:
        run_flowpaths = request.form.get('run_flowpaths') == 'on'
        wepp.set_run_flowpaths(run_flowpaths)
    except:
        run_flowpaths = None

    try:
        clip_soils = request.form.get('clip_soils') == 'on'
    except:
        clip_soils = None


    if clip_soils is not None:
        soils.clip_soils = clip_soils

    try:
        clip_soils_depth = int(request.form.get('clip_soils_depth'))
    except:
        clip_soils_depth = None

    if clip_soils_depth is not None:
        soils.clip_soils_depth = clip_soils_depth

    watershed = Watershed.getInstance(wd)

    try:
        clip_hillslopes = request.form.get('clip_hillslopes') == 'on'
    except:
        clip_hillslopes = None

    if clip_hillslopes is not None:
        watershed.clip_hillslopes = clip_hillslopes

    try:
        clip_hillslope_length = int(request.form.get('clip_hillslope_length'))
    except:
        clip_hillslope_length = None

    if clip_hillslope_length is not None:
        watershed.clip_hillslope_length = clip_hillslope_length

    try:
        initial_sat = float(request.form.get('initial_sat'))
    except:
        initial_sat = None

    if initial_sat is not None:
        soils.initial_sat = initial_sat


    try:
        reveg_scenario = request.form.get('reveg_scenario', None)
    except:
        reveg_scenario = None

    if reveg_scenario is not None:
        from wepppy.nodb.mods.revegetation import Revegetation
        reveg = Revegetation.getInstance(wd)
        reveg.load_cover_transform(reveg_scenario)

    try:
        prep_details_on_run_completion = request.form.get('prep_details_on_run_completion') == 'on'
    except:
        prep_details_on_run_completion = None

    try:
        arc_export_on_run_completion = request.form.get('arc_export_on_run_completion') == 'on'
    except:
        arc_export_on_run_completion = None

    try:
        legacy_arc_export_on_run_completion = request.form.get('legacy_arc_export_on_run_completion') == 'on'
    except:
        legacy_arc_export_on_run_completion = None

    try:
        dss_export_on_run_completion = request.form.get('dss_export_on_run_completion') == 'on'
    except:
        dss_export_on_run_completion = None

    try:
        wepp.lock()
        if prep_details_on_run_completion is not None:
            wepp._prep_details_on_run_completion = prep_details_on_run_completion

        if arc_export_on_run_completion is not None:
            wepp._arc_export_on_run_completion = arc_export_on_run_completion

        if legacy_arc_export_on_run_completion is not None:
            wepp._legacy_arc_export_on_run_completion = legacy_arc_export_on_run_completion


        if dss_export_on_run_completion is not None:
            wepp._dss_export_on_run_completion = dss_export_on_run_completion

        wepp.dump_and_unlock()
    except:
        wepp.unlock('-f')
        return exception_factory('Error running wepp', runid=runid)

    try:
        wepp.clean()
    except Exception:
        return exception_factory('Error cleaning wepp directories', runid=runid)

    try:


        watershed = Watershed.getInstance(wd)
        translator = Watershed.getInstance(wd).translator_factory()
        runs_dir = os.path.abspath(wepp.runs_dir)

        #
        # Prep Hillslopes
        wepp.prep_hillslopes()

        wepp.lock()
        wepp.run_hillslopes()
        #
        # Prep Watershed
        wepp.prep_watershed()

        #
        # Run Watershed
        wepp.run_watershed()
        wepp.unlock()

        wepp.post_discord_wepp_run_complete()


    except Exception:
        wepp.unlock('-f')
        return exception_factory('Error running wepp', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/run_wepp_watershed', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/run_wepp_watershed/', methods=['POST'])
def submit_task_run_wepp_watershed(runid, config):
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)

    try:
        wepp.parse_inputs(request.form)
    except Exception:
        return exception_factory('Error parsing climate inputs', runid=runid)

    try:

        watershed = Watershed.getInstance(wd)
        translator = Watershed.getInstance(wd).translator_factory()
        runs_dir = os.path.abspath(wepp.runs_dir)

        #
        # Prep Watershed
        wepp.prep_watershed()

        #
        # Run Watershed
        wepp.run_watershed()

    except Exception:
        return exception_factory('Error running wepp', runid=runid)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/run_model_fit', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/run_model_fit/', methods=['POST'])
def submit_task_run_model_fit(runid, config):
    wd = get_wd(runid)
    observed = Observed.getInstance(wd)

    textdata = request.json.get('data', None)

    try:
        observed.parse_textdata(textdata)
    except Exception:
        return exception_factory('Error parsing text', runid=runid)

    try:
        observed.calc_model_fit()
    except Exception:
        return exception_factory('Error running model fit', runid=runid)

    return success_factory()

# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/report/observed')
@app.route('/runs/<string:runid>/<config>/report/observed/')
def report_observed(runid, config):
    wd = get_wd(runid)
    observed = Observed.getInstance(wd)
    ron = Ron.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/observed.htm',
                           results=observed.results,
                           stat_names=observed.stat_names,
                           ron=ron,
                           unitizer_nodb=unitizer,
                           user=current_user)

@app.route('/runs/<string:runid>/<config>/plot/observed/<selected>/')
@app.route('/runs/<string:runid>/<config>/plot/observed/<selected>/')
def plot_observed(runid, config, selected):

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)

    graph_series = glob(_join(wepp.observed_dir, '*.csv'))
    graph_series = [_split(fn)[-1].replace('.csv', '') for fn in graph_series]
    graph_series.remove('observed')

    assert selected in graph_series

    if 'Daily' in selected:
        parseDate_fmt = "%m/%d/%Y"
    else:
        parseDate_fmt = "%Y"

    return render_template('reports/wepp/observed_comparison_graph.htm',
                           graph_series=sorted(graph_series),
                           selected=selected,
                           parseDate_fmt=parseDate_fmt,
                           ron=ron,
                           unitizer_nodb=unitizer,
                           user=current_user)


@app.route('/runs/<string:runid>/<config>/resources/observed/<file>')
def resources_observed_data(runid, config, file):

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    fn = _join(ron.observed_dir, file)

    assert _exists(fn)
    return send_file(fn, mimetype='text/csv', download_name=file)


@app.route('/runs/<string:runid>/<config>/query/landuse/cover/subcatchments')
@app.route('/runs/<string:runid>/<config>/query/landuse/cover/subcatchments/')
def query_landuse_cover_subcatchments(runid, config):
    wd = get_wd(runid)
    d = Landuse.getInstance(wd).hillslope_cancovs
    return jsonify(d)


@app.route('/runs/<string:runid>/<config>/query/wepp/phosphorus_opts')
@app.route('/runs/<string:runid>/<config>/query/wepp/phosphorus_opts/')
def query_wepp_phos_opts(runid, config):
    wd = get_wd(runid)
    phos_opts = Wepp.getInstance(wd).phosphorus_opts.asdict()
    return jsonify(phos_opts)


@app.route('/runs/<string:runid>/<config>/report/wepp/run_summary')
@app.route('/runs/<string:runid>/<config>/report/wepp/run_summary/')
def report_wepp_run_summary(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    flowpaths_n = len(glob(_join(wd, 'wepp/flowpaths/output/*.plot.dat')))
    subs_n = len(glob(_join(wd, 'wepp/output/*.pass.dat')))
    subs_n += len(glob(_join(wd, 'wepp/output/*/*.pass.dat')))

    return render_template('reports/wepp_run_summary.htm',
                           flowpaths_n=flowpaths_n,
                           subs_n=subs_n,
                           ron=ron)


@app.route('/runs/<string:runid>/<config>/report/rhem/run_summary')
@app.route('/runs/<string:runid>/<config>/report/rhem/run_summary/')
def report_rhem_run_summary(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    rhempost = RhemPost.getInstance(wd)
    subs_n = len(glob(_join(wd, 'rhem/output/*.sum')))

    return render_template('reports/rhem_run_summary.htm',
                           subs_n=subs_n,
                           rhempost=rhempost,
                           ron=ron)


@app.route('/runs/<string:runid>/<config>/report/rhem/summary')
@app.route('/runs/<string:runid>/<config>/report/rhem/summary/')
def report_rhem_avg_annuals(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    rhempost = RhemPost.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/rhem/avg_annual_summary.htm',
                           rhempost=rhempost,
                           ron=ron,
                           unitizer_nodb=unitizer,
                           precisions=wepppy.nodb.unitizer.precisions,
                           user=current_user)


@app.route('/runs/<string:runid>/<config>/report/wepp/summary')
@app.route('/runs/<string:runid>/<config>/report/wepp/summary/')
def report_wepp_loss(runid, config):
    extraneous = request.args.get('extraneous', None) == 'true'

    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))

    except:
        exclude_yr_indxs = None

    try:
        class_fractions = request.args.get('class_fractions', False)
        class_fractions = str(class_fractions).lower() == 'true'

        fraction_under = request.args.get('fraction_under', None)
        if fraction_under is not None:
            try:
                fraction_under = float(fraction_under)
            except:
                fraction_under = None

        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        loss = Wepp.getInstance(wd).report_loss(exclude_yr_indxs=exclude_yr_indxs)
        is_singlestorm = loss.is_singlestorm
        out_rpt = OutletSummary(loss)
        hill_rpt = HillSummary(loss, class_fractions=class_fractions, fraction_under=fraction_under)
        chn_rpt = ChannelSummary(loss)
        avg_annual_years = loss.avg_annual_years
        excluded_years = loss.excluded_years
        translator = Watershed.getInstance(wd).translator_factory()
        unitizer = Unitizer.getInstance(wd)


        return render_template('reports/wepp/summary.htm',
                               extraneous=extraneous,
                               out_rpt=out_rpt,
                               hill_rpt=hill_rpt,
                               chn_rpt=chn_rpt,
                               avg_annual_years=avg_annual_years,
                               excluded_years=excluded_years,
                               translator=translator,
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               ron=ron,
                               is_singlestorm=is_singlestorm,
                               user=current_user)
    except:
        return exception_factory(runid=runid)


@app.route('/runs/<string:runid>/<config>/report/wepp/yearly_watbal')
@app.route('/runs/<string:runid>/<config>/report/wepp/yearly_watbal/')
def report_wepp_yearly_watbal(runid, config):
    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))

    except:
        exclude_yr_indxs = [0, 1]

    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)

        totwatsed = TotalWatSed2(wd)
        totwatbal = TotalWatbal(totwatsed,
                                exclude_yr_indxs=exclude_yr_indxs)

        unitizer = Unitizer.getInstance(wd)

        return render_template('reports/wepp/yearly_watbal.htm',
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               rpt=totwatbal,
                               ron=ron,
                               user=current_user)
    except:
        return exception_factory(runid=runid)


@app.route('/runs/<string:runid>/<config>/report/wepp/avg_annual_by_landuse')
@app.route('/runs/<string:runid>/<config>/report/wepp/avg_annual_by_landuse/')
def report_wepp_avg_annual_by_landuse(runid, config):

    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)

        wepp = Wepp.getInstance(wd)
        dwat = DisturbedTotalWatSed2(wd, wepp.baseflow_opts, wepp.phosphorus_opts)
        unitizer = Unitizer.getInstance(wd)

        return render_template('reports/wepp/avg_annuals_by_landuse.htm',
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               report=dwat.annual_averages_report,
                               ron=ron,
                               user=current_user)
    except:
        return exception_factory('Error running wepp_avg_annual_by_landuse', runid=runid)


@app.route('/runs/<string:runid>/<config>/report/wepp/avg_annual_watbal')
@app.route('/runs/<string:runid>/<config>/report/wepp/avg_annual_watbal/')
def report_wepp_avg_annual_watbal(runid, config):

    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        wepp = Wepp.getInstance(wd)
        hill_rpt = wepp.report_hill_watbal()
        # chn_rpt = wepp.report_chn_watbal()

        unitizer = Unitizer.getInstance(wd)

        return render_template('reports/wepp/avg_annual_watbal.htm',
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               hill_rpt=hill_rpt,
                               # chn_rpt=chn_rpt,
                               ron=ron,
                               user=current_user)
    except:
        return exception_factory('Error running watbal', runid=runid)


@app.route('/runs/<string:runid>/<config>/resources/wepp/daily_streamflow.csv')
def resources_wepp_streamflow(runid, config):
    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))

    except:
        exclude_yr_indxs = [0, 1]

    stacked = request.args.get('stacked', None)
    if stacked is None:
        stacked = False
    else:
        stacked = stacked.lower() == 'true'

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    wepppost = WeppPost.getInstance(wd)
    fn = _join(ron.export_dir, 'daily_streamflow.csv')
    wepppost.export_streamflow(fn, exclude_yr_indxs=exclude_yr_indxs, stacked=stacked)

    assert _exists(fn)

    return send_file(fn, mimetype='text/csv', download_name='daily_streamflow.csv')


@app.route('/runs/<string:runid>/<config>/resources/wepp/totalwatsed.csv')
def resources_wepp_totalwatsed(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    fn = _join(ron.export_dir, 'totalwatsed.csv')
    if not _exists(fn):
        totwatsed_txt = _join(ron.output_dir, 'totalwatsed.txt')
        if not _exists(totwatsed_txt):
           return error_factory('totalwatsed.csv is not available for this project. Please use totalwatsed2.csv')
        wepp = Wepp.getInstance(wd)
        totwatsed = TotalWatSed2(totwatsed_txt,
                                wepp.baseflow_opts, wepp.phosphorus_opts)
        totwatsed.export(fn)

    assert _exists(fn)

    return send_file(fn, mimetype='text/csv', download_name='totalwatsed.csv')


@app.route('/runs/<string:runid>/<config>/resources/wepp/totalwatsed2.csv')
def resources_wepp_totalwatsed2(runid, config):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    fn = _join(ron.export_dir, 'totalwatsed2.csv')

    if not _exists(fn):
        totwatsed = TotalWatSed2(wd)
        totwatsed.export(fn)
    assert _exists(fn)

    return send_file(fn, mimetype='text/csv', download_name='totalwatsed2.csv')

@app.route('/runs/<string:runid>/<config>/plot/wepp/streamflow')
@app.route('/runs/<string:runid>/<config>/plot/wepp/streamflow/')
def plot_wepp_streamflow(runid, config):
    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))

    except:
        exclude_yr_indxs = [0, 1]


    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)

        unitizer = Unitizer.getInstance(wd)

        # stack basefow, lateral flow, runoff
        return render_template('reports/wepp/daily_streamflow_graph.htm',
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               exclude_yr_indxs=','.join(str(yr) for yr in exclude_yr_indxs),
                               ron=ron,
                               user=current_user)
    except:
        return exception_factory('Error running plot_wepp_streamflow', runid=runid)


@app.route('/runs/<string:runid>/<config>/report/rhem/return_periods')
@app.route('/runs/<string:runid>/<config>/report/rhem/return_periods/')
def report_rhem_return_periods(runid, config):

    try:
        extraneous = request.args.get('extraneous', None) == 'true'
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        rhempost = RhemPost.getInstance(wd)

        unitizer = Unitizer.getInstance(wd)

        return render_template('reports/rhem/return_periods.htm',
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               rhempost=rhempost,
                               ron=ron,
                               user=current_user)
    except:
        return exception_factory('Error running report_rhem_return_periods', runid=runid)


@app.route('/runs/<string:runid>/<config>/report/wepp/return_periods')
@app.route('/runs/<string:runid>/<config>/report/wepp/return_periods/')
def report_wepp_return_periods(runid, config):
    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))

    except:
        exclude_yr_indxs = None

    # get method and gringorten_correction
    # method default is cta gringorten_correction default is False
    method = request.args.get('method', 'cta')
    if method not in ['cta', 'am']:
        return error_factory('method must be either cta or am')
    
    gringorten_correction = request.args.get('gringorten_correction', 'false').lower() == 'true'

    try:
        wd = get_wd(runid)
        extraneous = request.args.get('extraneous', None) == 'true'

        climate = Climate.getInstance(wd)
        rec_intervals = _parse_rec_intervals(request, climate.years)

        ron = Ron.getInstance(wd)
        report = Wepp.getInstance(wd).report_return_periods(
            rec_intervals=rec_intervals, exclude_yr_indxs=exclude_yr_indxs,
            method=method, gringorten_correction=gringorten_correction)
        
        translator = Watershed.getInstance(wd).translator_factory()

        unitizer = Unitizer.getInstance(wd)

        return render_template('reports/wepp/return_periods.htm',
                               extraneous=extraneous,
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               report=report,
                               translator=translator,
                               ron=ron,
                               user=current_user)
    except:
        return exception_factory('Error generating return periods report', runid=runid)


@app.route('/runs/<string:runid>/<config>/report/wepp/frq_flood')
@app.route('/runs/<string:runid>/<config>/report/wepp/frq_flood/')
def report_wepp_frq_flood(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        report = Wepp.getInstance(wd).report_frq_flood()
        translator = Watershed.getInstance(wd).translator_factory()

        unitizer = Unitizer.getInstance(wd)

        return render_template('reports/wepp/frq_flood.htm',
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               report=report,
                               translator=translator,
                               ron=ron,
                               user=current_user)
    except:
        return exception_factory('Error running report_wepp_frq_flood', runid=runid)



@app.route('/runs/<string:runid>/<config>/report/wepp/sediment_characteristics')
@app.route('/runs/<string:runid>/<config>/report/wepp/sediment_characteristics/')
def report_wepp_sediment_delivery(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        sed_del = Wepp.getInstance(wd).report_sediment_delivery()
        translator = Watershed.getInstance(wd).translator_factory()

        unitizer = Unitizer.getInstance(wd)

        return render_template('reports/wepp/sediment_characteristics.htm',
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               sed_del=sed_del,
                               translator=translator,
                               ron=ron,
                               user=current_user)

    except Exception:
        return exception_factory("Error Handling Request: This may have occured if the run did not produce soil loss."
                                 "Check that the loss_pw0.txt contains a class fractions table.", runid=runid)


@app.route('/runs/<string:runid>/<config>/query/rhem/runoff/subcatchments')
@app.route('/runs/<string:runid>/<config>/query/rhem/runoff/subcatchments/')
def query_rhem_sub_runoff(runid, config):
    wd = get_wd(runid)
    rhempost = RhemPost.getInstance(wd)
    return jsonify(rhempost.query_sub_val('runoff'))


@app.route('/runs/<string:runid>/<config>/query/rhem/sed_yield/subcatchments')
@app.route('/runs/<string:runid>/<config>/query/rhem/sed_yield/subcatchments/')
def query_rhem_sub_sed_yield(runid, config):
    wd = get_wd(runid)
    rhempost = RhemPost.getInstance(wd)
    return jsonify(rhempost.query_sub_val('sed_yield'))


@app.route('/runs/<string:runid>/<config>/query/rhem/soil_loss/subcatchments')
@app.route('/runs/<string:runid>/<config>/query/rhem/soil_loss/subcatchments/')
def query_rhem_sub_soil_loss(runid, config):
    wd = get_wd(runid)
    rhempost = RhemPost.getInstance(wd)
    return jsonify(rhempost.query_sub_val('soil_loss'))


@app.route('/runs/<string:runid>/<config>/query/wepp/runoff/subcatchments')
@app.route('/runs/<string:runid>/<config>/query/wepp/runoff/subcatchments/')
def query_wepp_sub_runoff(runid, config):
    # blackwood http://wepp.cloud/weppcloud/runs/7f6d9b28-9967-4547-b121-e160066ed687/0/
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('Runoff'))


@app.route('/runs/<string:runid>/<config>/query/wepp/subrunoff/subcatchments')
@app.route('/runs/<string:runid>/<config>/query/wepp/subrunoff/subcatchments/')
def query_wepp_sub_subrunoff(runid, config):
    # blackwood http://wepp.cloud/weppcloud/runs/7f6d9b28-9967-4547-b121-e160066ed687/0/
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('Subrunoff'))


@app.route('/runs/<string:runid>/<config>/query/wepp/baseflow/subcatchments')
@app.route('/runs/<string:runid>/<config>/query/wepp/baseflow/subcatchments/')
def query_wepp_sub_baseflow(runid, config):
    # blackwood http://wepp.cloud/weppcloud/runs/7f6d9b28-9967-4547-b121-e160066ed687/0/
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('Baseflow'))


@app.route('/runs/<string:runid>/<config>/query/wepp/loss/subcatchments')
@app.route('/runs/<string:runid>/<config>/query/wepp/loss/subcatchments/')
def query_wepp_sub_loss(runid, config):
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('DepLoss'))


@app.route('/runs/<string:runid>/<config>/query/wepp/phosphorus/subcatchments')
@app.route('/runs/<string:runid>/<config>/query/wepp/phosphorus/subcatchments/')
def query_wepp_sub_phosphorus(runid, config):
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('Total P Density'))


@app.route('/runs/<string:runid>/<config>/query/chn_summary/<topaz_id>')
@app.route('/runs/<string:runid>/<config>/query/chn_summary/<topaz_id>/')
def query_ron_chn_summary(runid, config, topaz_id):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    return jsonify(ron.chn_summary(topaz_id))


@app.route('/runs/<string:runid>/<config>/query/sub_summary/<topaz_id>')
@app.route('/runs/<string:runid>/<config>/query/sub_summary/<topaz_id>/')
def query_ron_sub_summary(runid, config, topaz_id):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    return jsonify(ron.sub_summary(topaz_id))


@app.route('/runs/<string:runid>/<config>/report/chn_summary/<topaz_id>')
@app.route('/runs/<string:runid>/<config>/report/chn_summary/<topaz_id>/')
def report_ron_chn_summary(runid, config, topaz_id):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    return render_template('reports/hill.htm',
                           ron=ron,
                           d=ron.chn_summary(topaz_id))


@app.route('/runs/<string:runid>/<config>/query/topaz_wepp_map')
@app.route('/runs/<string:runid>/<config>/query/topaz_wepp_map/')
def query_topaz_wepp_map(runid, config):
    wd = get_wd(runid)
    translator = Watershed.getInstance(wd).translator_factory()

    d = dict([(wepp, translator.top(wepp=wepp)) for wepp in translator.iter_wepp_sub_ids()])

    return jsonify(d)


@app.route('/runs/<string:runid>/<config>/report/sub_summary/<topaz_id>')
@app.route('/runs/<string:runid>/<config>/report/sub_summary/<topaz_id>/')
def report_ron_sub_summary(runid, config, topaz_id):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    return render_template('reports/hill.htm',
                           ron=ron,
                           d=ron.sub_summary(topaz_id))


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/resources/wepp_loss.tif')
def resources_wepp_loss(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        loss_grid_wgs = _join(ron.plot_dir, 'loss.WGS.tif')

        if _exists(loss_grid_wgs):
            return send_file(loss_grid_wgs, mimetype='image/tiff')

        return error_factory('loss_grid_wgs does not exist')

    except Exception:
        return exception_factory(runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/resources/flowpaths_loss.tif')
def resources_flowpaths_loss(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        loss_grid_wgs = _join(ron.plot_dir, 'flowpaths_loss.WGS.tif')

        if _exists(loss_grid_wgs):
            return send_file(loss_grid_wgs, mimetype='image/tiff')

        return error_factory('loss_grid_wgs does not exist')

    except Exception:
        return exception_factory(runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/query/bound_coords')
@app.route('/runs/<string:runid>/<config>/query/bound_coords/')
def query_bound_coords(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        bound_wgs_json = _join(ron.topaz_wd, 'BOUND.WGS.JSON')

        if _exists(bound_wgs_json):
            with open(bound_wgs_json) as fp:
                js = json.load(fp)
                coords = js['features'][0]['geometry']['coordinates'][0]
                coords = [ll[::-1] for ll in coords]

                return success_factory(coords)

        return error_factory('Could not determine coords')

    except Exception:
        return exception_factory(runid=runid)

#
# Unitizer
#


@app.route('/runs/<string:runid>/<config>/unitizer')
@app.route('/runs/<string:runid>/<config>/unitizer/')
def unitizer_route(runid, config):

    try:
        wd = get_wd(runid)
        unitizer = Unitizer.getInstance(wd)

        value = request.args.get('value')
        in_units = request.args.get('in_units')
        ctx_processer = unitizer.context_processor_package()

        contents = ctx_processer['unitizer'](float(value), in_units)
        return success_factory(contents)

    except Exception:
        return exception_factory(runid=runid)

@app.route('/runs/<string:runid>/<config>/unitizer_units')
@app.route('/runs/<string:runid>/<config>/unitizer_units/')
def unitizer_units_route(runid, config):

    try:
        wd = get_wd(runid)
        unitizer = Unitizer.getInstance(wd)

        in_units = request.args.get('in_units')
        ctx_processer = unitizer.context_processor_package()

        contents = ctx_processer['unitizer_units'](in_units)
        return success_factory(contents)

    except Exception:
        return exception_factory(runid=runid)


#
# BAER
#


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/query/baer_wgs_map')
@app.route('/runs/<string:runid>/<config>/query/baer_wgs_map/')
def query_baer_wgs_bounds(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        if 'baer' in ron.mods:
            baer = Baer.getInstance(wd)
        else:
            baer = Disturbed.getInstance(wd)

        if not baer.has_map:
            return error_factory('No SBS map has been specified')

        return success_factory(dict(bounds=baer.bounds,
                                    classes=baer.classes,
                                    imgurl='resources/baer.png'))
    except Exception:
        return exception_factory(runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/view/modify_burn_class')
@app.route('/runs/<string:runid>/<config>/view/modify_burn_class/')
def query_baer_class_map(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        if 'baer' in ron.mods:
            baer = Baer.getInstance(wd)
        else:
            baer = Disturbed.getInstance(wd)

        if not baer.has_map:
            return error_factory('No SBS map has been specified')

        return render_template('mods/baer/classify.htm', baer=baer)
    except Exception:
        return exception_factory(runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/modify_burn_class', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/modify_burn_class/', methods=['POST'])
def task_baer_class_map(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        if 'baer' in ron.mods:
            baer = Baer.getInstance(wd)
        else:
            baer = Disturbed.getInstance(wd)

        if not baer.has_map:
            return error_factory('No SBS map has been specified')

        classes = request.json.get('classes', None)
        nodata_vals = request.json.get('nodata_vals', None)

        baer.modify_burn_class(classes, nodata_vals)
        return success_factory()
    except Exception:
        return exception_factory(runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/modify_color_map', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/modify_color_map/', methods=['POST'])
def task_baer_modify_color_map(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        if 'baer' in ron.mods:
            baer = Baer.getInstance(wd)
        else:
            baer = Disturbed.getInstance(wd)

        if not baer.has_map:
            return error_factory('No SBS map has been specified')

        color_map = request.json.get('color_map', None)
        color_map = {tuple(int(c) for c in color.split('_')) : sev for color, sev in color_map.items()}

        baer.modify_color_map(color_map)

        return success_factory()
    except Exception:
        return exception_factory(runid=runid)

# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/resources/baer.png')
def resources_baer_sbs(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        if 'baer' in ron.mods:
            baer = Baer.getInstance(wd)
        else:
            baer = Disturbed.getInstance(wd)

        if not baer.has_map:
            return error_factory('No SBS map has been specified')

        return send_file(baer.baer_rgb_png, mimetype='image/png')
    except Exception:
        return exception_factory(runid=runid)

# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_firedate/', methods=['POST'])
def set_firedate(runid, config):
    wd = get_wd(runid)
    disturbed = Disturbed.getInstance(wd)
    try:
        fire_date = request.json.get('fire_date', None)
        disturbed.fire_date = fire_date
        return success_factory()
    except Exception:
        return exception_factory("failed to set firedate", runid=runid)


# noinspection PyBroadException
@deprecated
@app.route('/runs/<string:runid>/<config>/tasks/acquire_rap_ts/', methods=['POST'])
def task_rap_ts_acquire(runid, config):
    from wepppy.nodb.mods import RAP_TS
    wd = get_wd(runid)
    rap_ts = RAP_TS.getInstance(wd)
    climate = Climate.getInstance(wd)
    try:
        assert climate.observed_start_year is not None
        assert climate.observed_end_year is not None

        rap_ts.acquire_rasters(start_year=climate.observed_start_year,
                               end_year=climate.observed_end_year)
        rap_ts.analyze()
        return success_factory("RAP TS acquired and analyzed")
    except Exception:
        return exception_factory("failed to acquire RAP TS", runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/upload_sbs/', methods=['POST'])
def task_upload_sbs(runid, config):
    wd = get_wd(runid)

    ron = Ron.getInstance(wd)
    if 'baer' in ron.mods:
        baer = Baer.getInstance(wd)
    else:
        baer = Disturbed.getInstance(wd)

    try:
        file = request.files['input_upload_sbs']
    except Exception:
        return exception_factory('Could not find file', runid=runid)

    try:
        if file.filename == '':
            return error_factory('no filename specified')

        filename = secure_filename(file.filename)
    except Exception:
        return exception_factory('Could not obtain filename', runid=runid)

    try:
        file.save(_join(baer.baer_dir, filename))
    except Exception:
        return exception_factory('Could not save file', runid=runid)

    try:
        res = baer.validate(filename)
    except Exception:
        return exception_factory('Failed validating file', runid=runid)

    return success_factory(res)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/upload_cover_transform/', methods=['POST'])
def task_upload_cover_transform(runid, config):
    from wepppy.nodb.mods.revegetation import Revegetation

    wd = get_wd(runid)

    reveg = Revegetation.getInstance(wd)

    try:
        file = request.files['input_upload_cover_transform']
    except Exception:
        return exception_factory('Could not find file', runid=runid)

    try:
        if file.filename == '':
            return error_factory('no filename specified')

        filename = secure_filename(file.filename)
    except Exception:
        return exception_factory('Could not obtain filename', runid=runid)

    try:
        file.save(_join(reveg.revegetation_dir, filename))
    except Exception:
        return exception_factory('Could not save file', runid=runid)

    try:
        res = reveg.validate_user_defined_cover_transform(filename)
    except Exception:
        return exception_factory('Failed validating file', runid=runid)

    return success_factory(res)

# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/remove_sbs/', methods=['POST'])
def task_remove_sbs(runid, config):
   
    try:
        wd = get_wd(runid)

        ron = Ron.getInstance(wd)
        if 'baer' in ron.mods:
            baer = Baer.getInstance(wd)
            baer.remove_sbs()
        else:
            baer = Disturbed.getInstance(wd)
            baer.remove_sbs()
        
        return success_factory()

    except:
        return exception_factory(runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/build_uniform_sbs/<value>', methods=['POST'])
def task_build_uniform_sbs(runid, config, value):
    try:
        wd = get_wd(runid)

        disturbed = Disturbed.getInstance(wd)
        sbs_fn = disturbed.build_uniform_sbs(int(value))
    except:
        return exception_factory(runid=runid)

    try:
        res = disturbed.validate(sbs_fn)
    except Exception:
        return exception_factory('Failed validating file', runid=runid)

    return success_factory()

@deprecated
@app.route('/runs/<string:runid>/<config>/tasks/run_debris_flow', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/run_debris_flow/', methods=['POST'])
def run_debris_flow(runid, config):
    # get working dir of original directory
    wd = get_wd(runid)

    try:
        debris_flow = DebrisFlow.getInstance(wd)
        debris_flow.run_debris_flow()
        return success_factory()

    except:
        return exception_factory('Error Running Debris Flow', runid=runid)


@deprecated
def _task_upload_ash_map(wd, request, file_input_id):
    ash = Ash.getInstance(wd)

    file = request.files[file_input_id]
    if file.filename == '':
        return None
        # raise Exception('no filename specified')

    filename = secure_filename(file.filename)

    file.save(_join(ash.ash_dir, filename))

#    try:
#        res = baer.validate(filename)
#    except Exception:
#        return exception_factory('Failed validating file')

    return filename

@deprecated
@app.route('/runs/<string:runid>/<config>/tasks/run_ash', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/run_ash/', methods=['POST'])
def run_ash(runid, config):
    # get working dir of original directory
    wd = get_wd(runid)

    #return jsonify(request.form)
    '''
    {
      "ash_depth_mode": "1", 
      "field_black_bulkdensity": "0.31", 
      "field_white_bulkdensity": "0.14", 
      "fire_date": "8/13", 
      "ini_black_depth": "15", 
      "ini_black_load": "1.55", 
      "ini_white_depth": "15", 
      "ini_white_load": "0.7000000000000001"
    }
    
    '''

    fire_date = request.form.get('fire_date', None)
    ash_depth_mode = request.form.get('ash_depth_mode', None)
    ini_black_ash_depth_mm = request.form.get('ini_black_depth', None)
    ini_white_ash_depth_mm = request.form.get('ini_white_depth', None)
    ini_black_ash_load_kgm2 = request.form.get('ini_black_load', None)
    ini_white_ash_load_kgm2 = request.form.get('ini_white_load', None)
    field_black_ash_bulkdensity = request.form.get('field_black_bulkdensity', None)
    field_white_ash_bulkdensity = request.form.get('field_white_bulkdensity', None)

    try:
        assert isint(ash_depth_mode), ash_depth_mode

        if int(ash_depth_mode) == 1:
            assert isfloat(ini_black_ash_depth_mm), ini_black_ash_depth_mm
            assert isfloat(ini_white_ash_depth_mm), ini_white_ash_depth_mm
        else:
            assert isfloat(ini_black_ash_load_kgm2), ini_black_ash_load_kgm2
            assert isfloat(ini_white_ash_load_kgm2), ini_white_ash_load_kgm2
            assert isfloat(field_black_ash_bulkdensity), field_black_ash_bulkdensity
            assert isfloat(field_white_ash_bulkdensity), field_white_ash_bulkdensity

            ini_black_ash_depth_mm = float(ini_black_ash_load_kgm2) / float(field_black_ash_bulkdensity)
            ini_white_ash_depth_mm = float(ini_white_ash_load_kgm2) / float(field_white_ash_bulkdensity)

        ash = Ash.getInstance(wd)

        if request.method == 'POST':
            ash.parse_inputs(dict(request.form))
            ash = Ash.getInstance(wd)

        if int(ash_depth_mode) == 2:
          
            ash.lock()

            try:
                ash._spatial_mode = AshSpatialMode.Gridded
                ash._ash_load_fn = _task_upload_ash_map(wd, request, 'input_upload_ash_load')
                ash._ash_type_map_fn = _task_upload_ash_map(wd, request, 'input_upload_ash_type_map')
                ash.dump_and_unlock()
            except Exception:
                ash.unlock('-f')
                raise

            if ash.ash_load_fn is None:
                raise Exception('Expecting ashload map')

        ash.ash_depth_mode = 1

        ash.run_ash(fire_date, float(ini_white_ash_depth_mm), float(ini_black_ash_depth_mm))
        return success_factory()

    except:
        return exception_factory('Error Running Ash Transport', runid=runid)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/<config>/tasks/set_ash_wind_transport', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/set_ash_wind_transport/', methods=['POST'])
def task_set_ash_wind_transport(runid, config):

    try:
        state = request.json.get('run_wind_transport', None)
    except Exception:
        return exception_factory('Error parsing state', runid=runid)

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        ash = Ash.getInstance(wd)
        ash.run_wind_transport = state
    except Exception:
        return exception_factory('Error setting state', runid=runid)

    return success_factory()


@app.route('/runs/<string:runid>/<config>/report/debris_flow')
@app.route('/runs/<string:runid>/<config>/report/debris_flow/')
def report_debris_flow(runid, config):
    wd = get_wd(runid)

    ron = Ron.getInstance(wd)
    debris_flow = DebrisFlow.getInstance(wd)

    cc = request.args.get('cc', None)
    ll = request.args.get('ll', None)
    datasource = request.args.get('datasource', None)
    if cc is not None or ll is not None:
        debris_flow.run_debris_flow(cc=cc, ll=ll, req_datasource=datasource)

    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/debris_flow.htm',
                           unitizer_nodb=unitizer,
                           precisions=wepppy.nodb.unitizer.precisions,
                           debris_flow=debris_flow,
                           ron=ron,
                           user=current_user)


def _parse_rec_intervals(request, years):
    rec_intervals = request.args.get('rec_intervals', None)
    if rec_intervals is None:
        rec_intervals = [2, 5, 10, 20, 25]
        if years >= 50:
            rec_intervals.append(50)
        if years >= 100:
            rec_intervals.append(100)
        if years >= 200:
            rec_intervals.append(200)
        if years >= 500:
            rec_intervals.append(500)
        if years >= 1000:
            rec_intervals.append(1000)
        rec_intervals = rec_intervals[::-1]
    else:
        rec_intervals = literal_eval(rec_intervals)
        assert all([isint(x) for x in rec_intervals])

    return rec_intervals

@app.route('/runs/<string:runid>/<config>/report/run_ash')
@app.route('/runs/<string:runid>/<config>/report/run_ash/')
def report_run_ash(runid, config):
    try:
        wd = get_wd(runid)
        ash = Ash.getInstance(wd)

        return render_template('reports/ash/run_summary.htm',
                               ash=ash)

    except Exception:
        return exception_factory('Error', runid=runid)


@app.route('/runs/<string:runid>/<config>/report/ash')
@app.route('/runs/<string:runid>/<config>/report/ash/')
def report_ash(runid, config):
    try:
        wd = get_wd(runid)

        climate = Climate.getInstance(wd)
        rec_intervals = _parse_rec_intervals(request, climate.years)

        ron = Ron.getInstance(wd)
        ash = Ash.getInstance(wd)
        ashpost = AshPost.getInstance(wd)

        fire_date = ash.fire_date
        ini_white_ash_depth_mm = ash.ini_white_ash_depth_mm
        ini_black_ash_depth_mm = ash.ini_black_ash_depth_mm
        unitizer = Unitizer.getInstance(wd)

        disturbed = None
        try:
            disturbed = Disturbed.getInstance(wd)
        except:
            pass


        burn_class_summary = ash.burn_class_summary()

        recurrence_intervals = ashpost.recurrence_intervals
        return_periods = ashpost.return_periods
        cum_return_periods = ashpost.cum_return_periods

        #return jsonify(dict(return_periods=return_periods, cum_return_period=cum_return_periods))

        return render_template('reports/ash/ash_watershed.htm',
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               fire_date=fire_date,
                               burn_class_summary=burn_class_summary,
                               ini_black_ash_depth_mm=ini_black_ash_depth_mm,
                               ini_white_ash_depth_mm=ini_white_ash_depth_mm,
                               recurrence_intervals=recurrence_intervals,
                               return_periods=return_periods,
                               cum_return_periods=cum_return_periods,
                               ash=ash,
                               ron=ron,
                               user=current_user)

    except Exception:
        return exception_factory('Error', runid=runid)


@app.route('/runs/<string:runid>/<config>/query/ash_out')
@app.route('/runs/<string:runid>/<config>/query/ash_out/')
def query_ash_out(runid, config):
    try:
        wd = get_wd(runid)
        ashpost = AshPost.getInstance(wd)
        ash_out = ashpost.ash_out

        return jsonify(ash_out)

    except Exception:
        return exception_factory(runid=runid)


@app.route('/runs/<string:runid>/<config>/report/ash_by_hillslope')
@app.route('/runs/<string:runid>/<config>/report/ash_by_hillslope/')
def report_ash_by_hillslope(runid, config):
    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))

    except:
        exclude_yr_indxs = None

    class_fractions = request.args.get('class_fractions', False)
    class_fractions = str(class_fractions).lower() == 'true'

    fraction_under = request.args.get('fraction_under', None)
    if fraction_under is not None:
        try:
            fraction_under = float(fraction_under)
        except:
            fraction_under = None

    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        loss = Wepp.getInstance(wd).report_loss(exclude_yr_indxs=exclude_yr_indxs)
        ash = Ash.getInstance(wd)
        ashpost = AshPost.getInstance(wd)

        out_rpt = OutletSummary(loss)
        hill_rpt = HillSummary(loss, class_fractions=class_fractions, fraction_under=fraction_under)
        chn_rpt = ChannelSummary(loss)
        avg_annual_years = loss.avg_annual_years
        excluded_years = loss.excluded_years
        translator = Watershed.getInstance(wd).translator_factory()
        unitizer = Unitizer.getInstance(wd)

        fire_date = ash.fire_date
        ini_white_ash_depth_mm = ash.ini_white_ash_depth_mm
        ini_black_ash_depth_mm = ash.ini_black_ash_depth_mm

        burn_class_summary = ash.burn_class_summary()
        ash_out = ashpost.ash_out

        return render_template('reports/ash/ash_watershed_by_hillslope.htm',
                               out_rpt=out_rpt,
                               hill_rpt=hill_rpt,
                               chn_rpt=chn_rpt,
                               avg_annual_years=avg_annual_years,
                               excluded_years=excluded_years,
                               translator=translator,
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               fire_date=fire_date,
                               burn_class_summary=burn_class_summary,
                               ini_black_ash_depth_mm=ini_black_ash_depth_mm,
                               ini_white_ash_depth_mm=ini_white_ash_depth_mm,
                               ash_out=ash_out,
                               ash=ash,
                               ron=ron,
                               user=current_user)

    except Exception:
        return exception_factory('Error', runid=runid)

@app.route('/runs/<string:runid>/<config>/report/ash_contaminant', methods=['GET', 'POST'])
@app.route('/runs/<string:runid>/<config>/report/ash_contaminant/', methods=['GET', 'POST'])
def report_contaminant(runid, config):

    try:
        wd = get_wd(runid)

        climate = Climate.getInstance(wd)
        rec_intervals = _parse_rec_intervals(request, climate.years)
        contaminants = request.args.get('contaminants', 'Ca,Pb,P,Hg')
        contaminants = contaminants.split(',')


        ron = Ron.getInstance(wd)
        ash = Ash.getInstance(wd)
        ashpost = AshPost.getInstance(wd)

        if request.method == 'POST':
            ash.parse_cc_inputs(dict(request.form))
            ash = Ash.getInstance(wd)

        unitizer = Unitizer.getInstance(wd)

        # if not ash.has_watershed_summaries:
        #     ash.report()

        recurrence_intervals = ashpost.recurrence_intervals
        results = ashpost.burn_class_return_periods
        return_periods = ashpost.return_periods

        pw0_stats = ashpost.pw0_stats

        return render_template('reports/ash/ash_contaminant.htm',
                               rec_intervals=recurrence_intervals,
                               rec_results=results,
                               return_periods=return_periods,
                               contaminants=contaminants,
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               pw0_stats=pw0_stats,
                               ash=ash,
                               ron=ron,
                               user=current_user)

    except Exception:
        return exception_factory('Error', runid=runid)


@app.route('/combined_ws_viewer')
@app.route('/combined_ws_viewer/')
def combined_ws_viewer():
    return render_template('combined_ws_viewer.htm')

@app.route('/bounds_ws_viewer')
@app.route('/bounds_ws_viewer/')
def bounds_ws_viewer():
    return render_template('bounds_ws_viewer.htm')


@app.route('/combined_ws_viewer/url_generator', methods=['GET', 'POST'])
@app.route('/combined_ws_viewer/url_generator/', methods=['GET', 'POST'])
def combined_ws_viewer_url_gen():
    if current_user.is_authenticated:
        if not current_user.roles:
            user_datastore.add_role_to_user(current_user.email, 'User')

    try:
        title = request.form.get('title', '')
        runids = request.form.get('runids', '')
        runids = runids.replace(',', ' ').split()

        from .combined_watershed_viewer_generator import combined_watershed_viewer_generator
        url = combined_watershed_viewer_generator(runids, title)

        return render_template('combined_ws_viewer_url_gen.htm',
            url=url, user=current_user, title=title, runids=', '.join(runids))
    except:
        return exception_factory('Error processing request')


def get_project_name(wd):
    ron = Ron.getInstance(wd)
    return ron.name


def get_config_stem(wd):
    ron = Ron.getInstance(wd)
    return ron.config_stem


@app.route('/dev/runid_query/')
def runid_query():
    if current_user.has_role('Root') or \
       current_user.has_role('Admin') or \
       current_user.has_role('Dev'):

        wc = request.args.get('wc', '')
        name = request.args.get('name', None)

        wds = glob(_join('/geodata/weppcloud_runs', '{}*'.format(wc)))

        wds = [wd for wd in wds if _exists(_join(wd, 'ron.nodb'))]

        if name is not None:
            wds = [wd for wd in wds if name in get_project_name(wd)]

        return jsonify([_join('weppcloud/runs', _split(wd)[-1], get_config_stem(wd)) for wd in wds])
    else:
        return error_factory('not authorized')


# noinspection PyBroadException
@deprecated
@app.route('/runs/<string:runid>/<config>/tasks/run_rhem', methods=['POST'])
@app.route('/runs/<string:runid>/<config>/tasks/run_rhem/', methods=['POST'])
def submit_task_run_rhem(runid, config):
    wd = get_wd(runid)
    rhem = Rhem.getInstance(wd)

    try:
        rhem.clean()
    except Exception:
        return exception_factory('Error cleaning rhem directories', runid=runid)

    try:
        rhem.prep_hillslopes()
        rhem.run_hillslopes()

    except Exception:
        return exception_factory('Error running rhem', runid=runid)

    return success_factory()

import pathlib
import io
VIZ_RSCRIPT_DIR = '/workdir/viz-weppcloud/scripts/R/'
VIZ_RMARKDOWN_DIR = '/workdir/viz-weppcloud/scripts/Rmd'

@app.route('/runs/<string:runid>/<config>/viz/<r_format>/<routine>')
@app.route('/runs/<string:runid>/<config>/viz/<r_format>/<routine>/')
def viz_r(runid, config, r_format, routine):
    assert config is not None

    wd = get_wd(runid)
    owners = get_run_owners(runid)
    try:
        ron = Ron.getInstance(wd)
    except FileNotFoundError:
        abort(404)

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

    viz_export_dir = _join(wd, 'export/viz')
    if not _exists(viz_export_dir):
        os.mkdir(viz_export_dir)
        
    try:
        rpt_fn = _join(viz_export_dir, f'{routine}.htm')

        if r_format.lower() == 'r':
            rscript = _join(VIZ_RSCRIPT_DIR, f'{routine}.R')
            assert _exists(rscript)
            cmd = ['Rscript', rscript, runid]
        elif r_format.lower() == "rmd":
            rscript = _join(VIZ_RMARKDOWN_DIR, f'{routine}.Rmd')
            assert _exists(rscript)
            cmd = ['R', '-e', f'library("rmarkdown"); rmarkdown::render("{rscript}", params=list(proj_runid="{runid}"), output_file="{routine}.htm", output_dir="{viz_export_dir}")']

        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        output, errors = p.communicate()
        with open(_join(viz_export_dir, f'{routine}.stdout'), 'w') as fp:
            fp.write(output.decode('utf-8'))
        with open(_join(viz_export_dir, f'{routine}.stderr'), 'w') as fp:
            fp.write(errors.decode('utf-8'))

        assert _exists(rpt_fn)
        with io.open(rpt_fn, encoding='utf8') as fp:
            return fp.read()

    except:
        return exception_factory('Error running script', runid=runid)


WEPPCLOUDR_DIR = '/workdir/WEPPcloudR/scripts'


def _weppcloudr_script_locator(routine, user=None):
    global WEPPCLOUDR_DIR 
    if user is None:
        return _join(WEPPCLOUDR_DIR, routine)
    else:
        rscript =  _join(WEPPCLOUDR_DIR, 'users', user, routine)
        assert pathlib.Path(WEPPCLOUDR_DIR) in  pathlib.Path(rscript).parents
        return rscript


@app.route('/runs/<string:runid>/<config>/WEPPcloudR/<routine>')
@app.route('/runs/<string:runid>/<config>/WEPPcloudR/<routine>/')
def weppcloudr(runid, config, routine):
    assert config is not None

    wd = get_wd(runid)
    owners = get_run_owners(runid)
    try:
        ron = Ron.getInstance(wd)
    except FileNotFoundError:
        abort(404)

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

    user = request.args.get('user', None)
    
    return weppcloudr_runner(runid, config, routine, user)


def weppcloudr_runner(runid, config, routine, user):
    wd = get_wd(runid)

    viz_export_dir = _join(wd, 'export/WEPPcloudR')
    if not _exists(viz_export_dir):
        os.mkdir(viz_export_dir)
        
    sub_fn = _join(wd, 'export', 'arcmap', 'subcatchments.WGS.json')
    sub_sha = get_file_sha1(sub_fn)

    try:
        assert routine.endswith('.R') or routine.endswith('.Rmd'), routine

        # routine_stem = '.'.join(routine.split('.')[:-1]) 
        r_format = routine.split('.')[-1] 
        rpt_fn = _join(viz_export_dir, f'{routine}.{sub_sha}.htm')

        if not _exists(rpt_fn):
            rscript = _weppcloudr_script_locator(routine, user=user)
            assert _exists(rscript)

            if r_format.lower() == 'r':
                cmd = ['Rscript', rscript, runid]
            elif r_format.lower() == "rmd":
                cmd = ['R', '-e', f'library("rmarkdown"); rmarkdown::render("{rscript}", params=list(proj_runid="{runid}"), output_file="{rpt_fn}", output_dir="{viz_export_dir}")']

            p = Popen(cmd, stdout=PIPE, stderr=PIPE)
            output, errors = p.communicate()
            output = output.decode('utf-8')
            errors = errors.decode('utf-8')
            with open(_join(viz_export_dir, f'{routine}.stdout'), 'w') as fp:
                fp.write(output)
            with open(_join(viz_export_dir, f'{routine}.stderr'), 'w') as fp:
                fp.write(errors)

            if not _exists(rpt_fn):
                return f'''
<html>
<h3>Error running script</h3>

<h5>stdout</h5>
<pre>
{output}
</pre>

<h5>stderr</h5>
<pre>
{errors}
</pre>
</html>'''

        with io.open(rpt_fn, encoding='utf8') as fp:
            return fp.read()

    except:
        return exception_factory('Error running script')


@app.route('/runs/<string:runid>/<config>/report/deval_details')
@app.route('/runs/<string:runid>/<config>/report/deval_details/')
def deval_details(runid, config):
    try:
        wd = get_wd(runid)
        if not _exists(_join(wd, 'export', 'arcmap', 'subcatchments.WGS.json')):
            from wepppy.export import arc_export
            arc_export(wd)
    except:
        return exception_factory('Error running script', runid=runid)

    return weppcloudr_runner(runid, config, routine='new_report.Rmd', user='chinmay')


@app.route('/WEPPcloudR/proxy/<routine>', methods=['GET', 'POST'])
@app.route('/WEPPcloudR/proxy/<routine>/', methods=['GET', 'POST'])
def weppcloudr_proxy(routine):
    if current_user.is_authenticated:
        if not current_user.roles:
            user_datastore.add_role_to_user(current_user.email, 'User')

    user = request.args.get('user', None)
    runids = request.args.get('runids', '')
    runids = runids.replace(',', ' ').split()

    try:

        ws = []
        for i, runid in enumerate(runids):
            if runid.endswith('/'):
                runid = runid[:-1]

            wd = get_wd(runid)
            try:
                ron = Ron.getInstance(wd)
                wepp = Wepp.getInstance(wd)
                watershed = Watershed.getInstance(wd)
            except:
                raise Exception('Error acquiring nodb instances from ' + wd)

            name = ron.name
            scenario = ron.scenario

            ws.append(dict(runid=runid, cfg=ron.config_stem, name=name, scenario=scenario, location_hash=ron.location_hash))

        
        js = json.dumps(ws)

    except:
        return exception_factory('Error running script')

    wd = get_wd(runids[0]) 
    viz_export_dir = _join(wd, 'export/WEPPcloudR')
    if not _exists(viz_export_dir):
        os.mkdir(viz_export_dir)
        
    try:
        assert routine.endswith('.R') or routine.endswith('.Rmd'), routine

        # routine_stem = '.'.join(routine.split('.')[:-1]) 
        r_format = routine.split('.')[-1] 
        rpt_fn = _join(viz_export_dir, f'{routine}.htm')

        rscript = _weppcloudr_script_locator(routine, user=user)
        assert _exists(rscript)

        if r_format.lower() == 'r':
            cmd = ['Rscript', rscript, runid]
        elif r_format.lower() == "rmd":
            cmd = ['R', '-e', f'''library("rmarkdown"); rmarkdown::render("{rscript}", params=list(ws='{js}'), output_file="{rpt_fn}", output_dir="{viz_export_dir}")''']

        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        output, errors = p.communicate()
        with open(_join(viz_export_dir, f'{routine}.stdout'), 'w') as fp:
            fp.write(output.decode('utf-8'))
        with open(_join(viz_export_dir, f'{routine}.stderr'), 'w') as fp:
            fp.write(errors.decode('utf-8'))

        assert _exists(rpt_fn)
        with io.open(rpt_fn, encoding='utf8') as fp:
            return fp.read()

    except:
        return exception_factory('Error processing request')


#  R -e 'library("rmarkdown"); rmarkdown::render("03_Rmarkdown_to_generate_reports.Rmd", params=list(proj_runid="lt_202012_26_Bliss_Creek_CurCond"), output_file="rmd_rpt.htm")'

if __name__ == '__main__':
    app.run(debug=True, port=5003)

    # sudo docker run -i -p 5003:80 -v /Users/roger/geodata:/geodata -v /Users/roger/wepppy/wepppy:/workdir/wepppy/wepppy  -t wepppydocker-base

#rsync -av --progress --exclude=scripts --exclude=__pycache__ --exclude=validation  --exclude=*.pyc  /home/roger/wepppy/wepppy/  roger@wepp.cloud:/usr/lib/python3/dist-packages/wepppy/
#rsync -av --progress --no-times --no-perms --no-owner --no-group --exclude=scripts --exclude=__pycache__ --exclude=validation  --exclude=*.pyc  /workdir/wepppy/wepppy/  roger@wepp.cloud:/usr/lib/python3/dist-packages/wepppy/


