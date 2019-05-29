# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from datetime import datetime

from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

import uuid
import json
import shutil
import traceback
from glob import glob

import numpy as np

from werkzeug.utils import secure_filename

from flask import (
    Flask, jsonify, request, render_template, 
    redirect, send_file, Response, abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_security import (
    RegisterForm,
    Security, SQLAlchemyUserDatastore,
    UserMixin, RoleMixin,
    login_required, current_user, roles_required
)

from flask_security.forms import Required

from flask_mail import Mail

from wtforms import StringField
import what3words

import wepppy

from wepppy.all_your_base import isfloat, isint, parse_datetime

from wepppy.soils.ssurgo import NoValidSoilsException
from wepppy.topaz import (
    WatershedBoundaryTouchesEdgeError,
    MinimumChannelLengthTooShortError
)
from wepppy.climates.cligen import (
    StationMeta
)
from wepppy.watershed_abstraction import (
    ChannelRoutingError,
)
from wepppy.wepp import management
from wepppy.wepp.soils import soilsdb

from wepppy.wepp.out import TotalWatSed

from wepppy.wepp.stats import (
    OutletSummary,
    HillSummary,
    ChannelSummary,
    TotalWatbal
)

from wepppy.nodb import (
    Ron,
    Topaz,
    Watershed,
    Landuse, LanduseMode, 
    Soils, SoilsMode, 
    Climate, ClimateStationMode,
    Wepp, WeppPost,
    Unitizer,
    Observed,
    DebrisFlow
)

from wepppy.nodb.mods import Baer

import socket
_hostname = socket.gethostname()
if 'wepp1' in _hostname:
    from wepppy.weppcloud.app_config import config_app
else:
    from wepppy.weppcloud.standalone_config import config_app


# noinspection PyBroadException

app = Flask(__name__)
app.jinja_env.filters['zip'] = zip
app = config_app(app)

mail = Mail(app)

# Setup Flask-Security
# Create database connection object
db = SQLAlchemy(app)

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
        wd = get_wd(self.runid)
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


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
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

    def create_run(self, runid, config, user: User):
        if user.is_anonymous:
            owner_id = None
        else:
            owner_id = user.id

        date_created = datetime.now()
        run = self.run_model(runid=runid, config=config,
                             owner_id=owner_id, date_created=date_created)
        run0 = self.put(run)
        self.commit()

        if owner_id is not None:
            self.add_run_to_user(user, run)

        return run0

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


# Create a user to test with
@app.before_first_request
def init_db():
    if not _exists('/geodata/weppcloud_runs/standalone.db') and _hostname != 'wepp1':
        import app_config
        app_config._init(db, user_datastore)


def get_run_owners(runid):
    return User.query.filter(User.runs.any(Run.runid == runid)).all()


@app.route('/profile')
@app.route('/profile/')
@login_required
def profile():
    return render_template('user/profile.html', user=current_user)


@app.route('/runs')
@app.route('/runs/')
@login_required
def runs():
    return render_template('user/runs.html', user=current_user)


@app.route('/usermod')
@app.route('/usermod/')
@roles_required('Root')
def usermod():
    return render_template('user/usermod.html', user=current_user)


@app.route('/ispoweruser')
@app.route('/ispoweruser/')
def ispoweruser():
    return jsonify(current_user.has_role('PowerUser'))

@app.route('/tasks/usermod/', methods=['POST'])
@roles_required('Root')
def task_usermod():
    user_id = request.json.get('user_id')
    role = request.json.get('role')
    role_state = request.json.get('role_state')

    user = User.query.filter(User.id == user_id).first()
    assert user is not None

    if user.has_role(role) == role_state:
        return error_factory('{} role {} already is {}'
                             .format(user.email, role, role_state))

    if role_state:
        user_datastore.add_role_to_user(user, role)
    else:
        user_datastore.remove_role_from_user(user, role)

    db.session.commit()
    return success_factory()


_thisdir = os.path.dirname(__file__)


def htmltree(_dir='.', padding='', print_files=True, recurse=False):
    def _tree(__dir, _padding, _print_files, recurse=False):
        # Original from Written by Doug Dahms
        # http://code.activestate.com/recipes/217212/
        #
        # Adapted to return string instead of printing to stdout
        
        from os import listdir, sep
        from os.path import abspath, basename, isdir
        
        s = [_padding[:-1] + '+-' + basename(abspath(__dir)) + '\n']
        f = []
        _padding += ' '
        if _print_files:
            files = listdir(__dir)
        else:
            files = [x for x in listdir(__dir) if isdir(__dir + sep + x)]
        count = 0
        for file in sorted(files):
            count += 1
            path = __dir + sep + file
            if isdir(path) and recurse:
                if count == len(files):
                    s.extend(htmltree(path, _padding + ' ', _print_files) + '\n')
                else:
                    s.extend(htmltree(path, _padding + '|', _print_files) + '\n')
            else:
                if isdir(path):
                    s.append(_padding + '+-<a href="{file}">{file}</a>\n'.format(file=file))
                else:
                    f.append(_padding + '>-<a href="{file}">{file}</a>\n'.format(file=file))

        s.extend(f)
        return s
        
    return ''.join(_tree(_dir, padding, print_files))


def get_wd(runid):
    return _join('/geodata/weppcloud_runs', runid)


def get_last():
    return _join('/geodata/weppcloud_runs', 'last')


def error_factory(msg='Error Handling Request'):
    return jsonify({'Success': False,
                    'Error': msg})


def exception_factory(msg='Error Handling Request',
                      stacktrace=None):
    if stacktrace is None:
        stacktrace = traceback.format_exc()

    return jsonify({'Success': False,
                    'Error': msg,
                    'StackTrace': stacktrace})


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
def security_processor():
    def get_run_name(runid):
        wd = get_wd(runid)
        name = Ron.getInstance(wd).name
        return name

    def run_exists(runid):
        wd = get_wd(runid)
        return _exists(_join(wd, 'ron.nodb'))

    def get_run_owner(runid):
        run = Run.query.filter(Run.runid == runid).first()
        if run.owner_id is None:
            return 'anonymous'

        owner = User.query.filter(User.id == run.owner_id).first()
        return owner.email

    def get_last_modified(runid):
        wd = get_wd(runid)
        nodbs = glob(_join(wd, '*.nodb'))

        last = 0
        for fn in nodbs:
            statbuf = os.stat(fn)
            if statbuf.st_mtime > last:
                last = statbuf.st_mtime

        return datetime.fromtimestamp(last)

    def get_all_runs():
        return [run for run in Run.query.order_by(Run.date_created).all() if run.valid]

    def get_all_users():
        return User.query.order_by(User.last_login_at).all()

    def get_anonymous_runs():
        return Run.query.filter(Run.owner_id is None)

    def w3w_center(runid):
        wd = get_wd(runid)
        return Ron.getInstance(wd).w3w

    return dict(run_exists=run_exists,
                get_run_name=get_run_name,
                get_run_owner=get_run_owner,
                get_last_modified=get_last_modified,
                get_anonymous_runs=get_anonymous_runs,
                get_all_runs=get_all_runs,
                w3w_center=w3w_center,
                get_all_users=get_all_users)


@app.route('/')
def index():
    if current_user.is_authenticated:
        if not current_user.roles:
            user_datastore.add_role_to_user(current_user.email, 'User')

    from wepppy.weppcloud import RunStatistics
    rs = RunStatistics.getInstance('/geodata/weppcloud_runs')
    c = rs.counter

    return render_template('index.htm', user=current_user, runs_counter=c)


@app.route('/lt')
@app.route('/lt/')
def lt_index():
    if current_user.is_authenticated:
        if not current_user.roles:
            user_datastore.add_role_to_user(current_user.email, 'User')
    return render_template('lt/index.htm', user=current_user)


@app.route('/portland-municipal')
@app.route('/portland-municipal/')
def portland_index():
    if current_user.is_authenticated:
        if not current_user.roles:
            user_datastore.add_role_to_user(current_user.email, 'User')
    return render_template('portland-municipal/index.htm', user=current_user)


@app.route('/seattle-municipal')
@app.route('/seattle-municipal/')
def seattle_index():
    if current_user.is_authenticated:
        if not current_user.roles:
            user_datastore.add_role_to_user(current_user.email, 'User')
    return render_template('seattle-municipal/index.htm', user=current_user)


@app.route('/create/<config>')
def create(config):
    runid = str(uuid.uuid4())

    email = getattr(current_user, 'email', '')
    if email.startswith('rogerlew@'):
        runid = 'rlew' + runid[4:]
    elif email.startswith('mdobre@'):
        runid = 'mdob' + runid[4:]
    elif request.remote_addr == '127.0.0.1':
        runid = 'devvm' + runid[5:]

    try:
        from wepppy.weppcloud import RunStatistics
        rs = RunStatistics.getInstance('/geodata/weppcloud_runs')
        rs.increment_projects(config)
    except:
        pass

    wd = get_wd(runid)
    assert not _exists(wd)
    os.mkdir(wd)

    Ron(wd, "%s.cfg" % config)
    
    # for development convenience create a symlink
    # to the this working directory
    last = get_last()
    if _exists(last):
        os.unlink(last)
    os.symlink(wd, last)

    user_datastore.create_run(runid, config, current_user)
    
    return redirect('%s/runs/%s/%s/' % (app.config['SITE_PREFIX'], runid, config))


@app.route('/runs/<runid>/<config>/create_fork')
@app.route('/runs/<runid>/<config>/create_fork/')
def create_fork(runid, config):
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
        abort(404)

    # build new runid for fork
    new_runid = str(uuid.uuid4())
    new_wd = get_wd(new_runid)
    assert not _exists(new_wd)
    
    # copy the contents over
    shutil.copytree(wd, new_wd)
    
    # replace the runid in the nodb files
    nodbs = glob(_join(new_wd, '*.nodb'))
    for fn in nodbs:
        with open(fn) as fp:
            s = fp.read()
            
        s = s.replace(runid, new_runid)
        with open(fn, 'w') as fp:
            fp.write(s)
    
    # delete any active locks    
    locks = glob(_join(new_wd, '*.lock'))
    for fn in locks:
        os.remove(fn)

    fn = _join(new_wd, 'READONLY')
    if _exists(fn):
        os.remove(fn)

    fn = _join(new_wd, 'PUBLIC')
    if _exists(fn):
        os.remove(fn)

    # redirect to fork
    return redirect('%s/runs/%s/%s/' % (app.config['SITE_PREFIX'], new_runid, config))



@app.route('/runs/<runid>/tasks/clear_locks')
@app.route('/runs/<runid>/tasks/clear_locks/')
def clear_locks(runid):
    # get working dir of original directory
    wd = get_wd(runid)

    try:

        # delete any active locks
        locks = glob(_join(wd, '*.lock'))
        for fn in locks:
            os.remove(fn)

        # redirect to fork
        return success_factory()

    except:
        return exception_factory('Error Clearing Locks')


@app.route('/runs/<runid>/<config>/archive')
@app.route('/runs/<runid>/<config>/archive/')
def archive(runid, config):
    # get working dir of original directory
    wd = get_wd(runid)

    from wepppy.export import archive_project, arc_export
    try:
        arc_export(wd)
    except:
        pass

    archive_path = archive_project(wd)
    return send_file(archive_path, as_attachment=True, attachment_filename='{}.zip'.format(runid))


def log_access(wd, current_user, ip):
    assert _exists(wd)

    fn, runid = _split(wd)
    fn = _join(fn, '.{}'.format(runid))
    with open(fn, 'a') as fp:
        email = getattr(current_user, 'email', '<anonymous>')
        fp.write('{},{},{}\n'.format(email, ip, datetime.now()))


@app.route('/runs/<runid>/<config>/')
def runs0(runid, config):
    assert config is not None

    wd = get_wd(runid)
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

    if should_abort:
        abort(404)

    topaz = Topaz.getInstance(wd)
    landuse = Landuse.getInstance(wd)
    soils = Soils.getInstance(wd)
    climate = Climate.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)

    try:
        observed = Observed.getInstance(wd)
    except:
        observed = Observed(wd, "%s.cfg" % config)

    landuseoptions = landuse.landuseoptions

    has_sbs = False
    if "baer" in ron.mods:
        has_sbs = Baer.getInstance(wd).has_map

    soildboptions = soilsdb.load_db()

    log_access(wd, current_user, request.remote_addr)
    return render_template('0.html',
                           user=current_user,
                           topaz=topaz, soils=soils,
                           ron=ron, landuse=landuse, climate=climate,
                           wepp=wepp,
                           unitizer_nodb=unitizer,
                           observed=observed,
                           landuseoptions=landuseoptions,
                           soildboptions=soildboptions,
                           precisions=wepppy.nodb.unitizer.precisions,
                           has_sbs=has_sbs)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/adduser/', methods=['POST'])
@login_required
def task_adduser(runid):
    owners = get_run_owners(runid)

    should_abort = True
    if current_user in owners:
        should_abort = False

    if current_user.has_role('Admin'):
        should_abort = False

    if should_abort:
        return error_factory('Authentication Error')

    email = request.form.get('adduser-email')
    user = User.query.filter(User.email == email).first()
    run = Run.query.filter(Run.runid == runid).first()

    if user is None:
        return error_factory('{} does not have a WeppCloud account.'
                             .format(email))

    assert user not in owners
    assert run is not None

    user_datastore.add_run_to_user(user, run)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/removeuser/', methods=['POST'])
@login_required
def task_removeuser(runid):

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

    assert user is not None
    assert user in owners
    assert run is not None

    user_datastore.remove_run_to_user(user, run)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/report/users/')
@login_required
def report_users(runid):
    owners = get_run_owners(runid)

    return render_template('reports/users.htm', owners=owners)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/resources/netful.json')
def resources_netful_geojson(runid):
    try:
        wd = get_wd(runid)
        fn = _join(wd, 'dem', 'topaz', 'NETFUL.WGS.JSON')
        return send_file(fn, mimetype='application/json')
    except Exception:
        return exception_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/resources/subcatchments.json')
def resources_subcatchments_geojson(runid):
    try:
        wd = get_wd(runid)
        fn = _join(wd, 'dem', 'topaz', 'SUBCATCHMENTS.WGS.JSON')

        js = json.load(open(fn))
        ron = Ron.getInstance(wd)
        name = ron.name

        if name.strip() == '':
            js['name'] = runid
        else:
            js['name'] = name

        return jsonify(js)
    except Exception:
        return exception_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/resources/channels.json')
def resources_channels_geojson(runid):
    try:
        wd = get_wd(runid)
        fn = _join(wd, 'dem', 'topaz', 'CHANNELS.WGS.JSON')

        js = json.load(open(fn))
        ron = Ron.getInstance(wd)
        name = ron.name

        if name.strip() == '':
            js['name'] = runid
        else:
            js['name'] = name

        return jsonify(js)
    except Exception:
        return exception_factory()


@app.route('/runs/<string:runid>/tasks/setname/', methods=['POST'])
def task_setname(runid):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    ron.name = request.form.get('name', 'Untitled')
    return success_factory()


@app.route('/runs/<string:runid>/report/tasks/set_unit_preferences/', methods=['POST'])
@app.route('/runs/<string:runid>/tasks/set_unit_preferences/', methods=['POST'])
def task_set_unit_preferences(runid):
    wd = get_wd(runid)
    unitizer = Unitizer.getInstance(wd)
    res = unitizer.set_preferences(request.form)
    return success_factory(res)

 
@app.route('/runs/<string:runid>/query/topaz_pass')
@app.route('/runs/<string:runid>/query/topaz_pass/')
def query_topaz_pass(runid):
    wd = get_wd(runid)
    return jsonify(Topaz.getInstance(wd).topaz_pass)


@app.route('/runs/<string:runid>/query/extent')
@app.route('/runs/<string:runid>/query/extent/')
def query_extent(runid):
    wd = get_wd(runid)
    
    return jsonify(Ron.getInstance(wd).extent)
    
    
@app.route('/runs/<string:runid>/report/channel')
@app.route('/runs/<string:runid>/report/channel/')
def report_channel(runid):
    wd = get_wd(runid)
    
    return render_template('reports/channel.htm',
                           map=Ron.getInstance(wd).map)

    
@app.route('/runs/<string:runid>/query/outlet')
@app.route('/runs/<string:runid>/query/outlet/')
def query_outlet(runid):
    wd = get_wd(runid)
    
    return jsonify(Topaz.getInstance(wd)
                        .outlet
                        .as_dict())


@app.route('/runs/<string:runid>/report/outlet')
@app.route('/runs/<string:runid>/report/outlet/')
def report_outlet(runid):
    wd = get_wd(runid)
    
    return render_template('reports/outlet.htm',
                           outlet=Topaz.getInstance(wd).outlet,
                           ron=Ron.getInstance(wd))


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/setoutlet/', methods=['POST'])
def task_setoutlet(runid):
    try:
        lat = float(request.form.get('latitude', None))
        lng = float(request.form.get('longitude', None))
    except Exception:
        return exception_factory('latitude and longitude must be provided as floats')

    wd = get_wd(runid)
    topaz = Topaz.getInstance(wd)

    try:
        topaz.set_outlet(lng, lat)
    except Exception:
        return exception_factory('Could not set outlet')

    return success_factory()


def browse_response(path, show_up=True):
    if not _exists(path):
        return error_factory('path does not exist')

    path_lower = path.lower()

    if os.path.isdir(path):
        up = ''
        if show_up:
            up = '<a href="../">Up</a>\n'

        c = '<pre>\n{}{}</pre>'\
            .format(up, htmltree(path))

        return Response(c, mimetype='text/html')

    elif path_lower.endswith('.tif') or path_lower.endswith('.png'):
        basename = path.split()[-1]
        return send_file(path, attachment_filename=basename)

    else:
        with open(path) as fp:
            try:
                contents = fp.read()
            except UnicodeDecodeError:
                return send_file(path, as_attachment=True, attachment_filename=_split(path)[-1])
                return error_factory('Cannot return this binary file.')

        if path_lower.endswith('.json') or path_lower.endswith('.nodb'):
            jsobj = json.loads(contents)
            return jsonify(jsobj)

        if path_lower.endswith('.xml'):
            r = Response(response=contents, status=200, mimetype="text/xml")
            r.headers["Content-Type"] = "text/xml; charset=utf-8"
            return r

        if path_lower.endswith('.arc'):
            c = '<pre style="font-size:xx-small;">\n{}</pre>'.format(contents)
            return Response(c, mimetype='text/html')

        r = Response(response=contents, status=200, mimetype="text/plain")
        r.headers["Content-Type"] = "text/plain; charset=utf-8"
        return r


@app.route('/runs/<string:runid>/browse')
@app.route('/runs/<string:runid>/browse/')
def dev_tree(runid):
    """
    recursive list the file strucuture of the working directory
    """
    wd = get_wd(runid)
    return browse_response(wd, show_up=False)

@app.route('/runs/<string:runid>/report/<string:wepp>/browse/<dir>/')
def wp_dev_tree1(runid, wepp, dir):
    return dev_tree1(runid, dir)


@app.route('/runs/<string:runid>/report/<string:wepp>/browse/<dir>/<dir2>/')
def wp_dev_tree2(runid, wepp, dir, dir2):
    return dev_tree2(runid, dir, dir2)


@app.route('/runs/<string:runid>/report/<string:wepp>/browse/<dir>/<dir2>/<dir3>/')
def wp_dev_tree32(runid, wepp, dir, dir2, dir3):
    return dev_tree32(runid, dir, dir2, dir3)


@app.route('/runs/<string:runid>/report/<string:wepp>/browse/<dir>/<dir2>/<dir3>/<dir4>/')
def wp_dev_tree432(runid, wepp, dir, dir2, dir3, dir4):
    return dev_tree32(runid, dir, dir2, dir3, dir4)


@app.route('/runs/<string:runid>/report/<string:wepp>/browse/<dir>/<dir2>/<dir3>/<dir4>/<dir5>/')
def wp_dev_tree5432(runid, wepp, dir, dir2, dir3, dir4, dir5):
    return dev_tree5432(runid, dir, dir2, dir3, dir4, dir5)


@app.route('/runs/<string:runid>/browse/<dir>/')
def dev_tree1(runid, dir):
    """
    recursive list the file strucuture of the working directory
    """
    wd = os.path.abspath(get_wd(runid))
    dir = os.path.abspath(_join(wd, dir))
    assert dir.startswith(wd)
    return browse_response(dir)


@app.route('/runs/<string:runid>/browse/<dir>/<dir2>/')
def dev_tree2(runid, dir, dir2):
    """
    recursive list the file strucuture of the working directory
    """
    wd = os.path.abspath(get_wd(runid))
    dir = os.path.abspath(_join(wd, dir, dir2))
    assert dir.startswith(wd)
    return browse_response(dir)


@app.route('/runs/<string:runid>/browse/<dir>/<dir2>/<dir3>/')
def dev_tree32(runid, dir, dir2, dir3):
    """
    recursive list the file strucuture of the working directory
    """
    wd = os.path.abspath(get_wd(runid))
    dir = os.path.abspath(_join(wd, dir, dir2, dir3))
    assert dir.startswith(wd)
    return browse_response(dir)


@app.route('/runs/<string:runid>/browse/<dir>/<dir2>/<dir3>/<dir4>/')
def dev_tree432(runid, dir, dir2, dir3, dir4):
    """
    recursive list the file strucuture of the working directory
    """
    wd = os.path.abspath(get_wd(runid))
    dir = os.path.abspath(_join(wd, dir, dir2, dir3, dir4))
    assert dir.startswith(wd)
    return browse_response(dir)


@app.route('/runs/<string:runid>/browse/<dir>/<dir2>/<dir3>/<dir4>/<dir5>/')
def dev_tree5432(runid, dir, dir2, dir3, dir4, dir5):
    """
    recursive list the file strucuture of the working directory
    """
    wd = os.path.abspath(get_wd(runid))
    dir = os.path.abspath(_join(wd, dir, dir2, dir3, dir4, dir5))
    assert dir.startswith(wd)
    return browse_response(dir)

@app.route('/runs/<string:runid>/browse/<dir>/<dir2>/<dir3>/<dir4>/<dir5>/<dir6>/')
def dev_tree65432(runid, dir, dir2, dir3, dir4, dir5, dir6):
    """
    recursive list the file strucuture of the working directory
    """
    wd = os.path.abspath(get_wd(runid))
    dir = os.path.abspath(_join(wd, dir, dir2, dir3, dir4, dir5, dir6))
    assert dir.startswith(wd)
    return browse_response(dir)

@app.route('/runs/<string:runid>/query/has_dem')
@app.route('/runs/<string:runid>/query/has_dem/')
def query_has_dem(runid):
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
        zoom = int(zoom)
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
@app.route('/runs/<string:runid>/tasks/fetch_dem/', methods=['POST'])
def task_fetch_dem(runid):
    error, args = _parse_map_change(request.form)

    if error is not None:
        return jsonify(error)

    extent, center, zoom, mcl, csa = args

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    ron.set_map(extent, center, zoom)

    # Acquire DEM from wmesque server
    try:
        ron.fetch_dem()
    except Exception:
        return exception_factory('Fetching DEM Failed')

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/export/ermit/')
def export_ermit(runid):
    from wepppy.export import create_ermit_input
    wd = get_wd(runid)
    fn = create_ermit_input(wd)
    name = _split(fn)[-1]
    return send_file(fn, as_attachment=True, attachment_filename=name)


@app.route('/runs/<runid>/export/arcmap')
@app.route('/runs/<runid>/export/arcmap/')
def export_arcmap(runid):
    # get working dir of original directory
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    ron.export_arc_dir

    from wepppy.export import arc_export, archive_project
    arc_export(wd)
    archive_path = archive_project(ron.export_arc_dir)
    return send_file(archive_path, as_attachment=True, attachment_filename='{}_arcmap.zip'.format(runid))


# noinspection PyBroadException
@app.route('/runs/<string:runid>/export/winwepp/')
def export_winwepp(runid):
    from wepppy.export import export_winwepp
    wd = get_wd(runid)
    export_winwepp_path = export_winwepp(wd)
    return send_file(export_winwepp_path, as_attachment=True, attachment_filename='{}_winwepp.zip'.format(runid))


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/build_channels/', methods=['POST'])
def task_build_channels(runid):

    error, args = _parse_map_change(request.form)

    if error is not None:
        return jsonify(error)

    extent, center, zoom, mcl, csa = args

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    # determine whether we need to fetch dem
    if ''.join(['%.7f' % v for v in ron.map.extent]) != \
       ''.join(['%.7f' % v for v in extent]):

        ron.set_map(extent, center, zoom)

        # Acquire DEM from WMesque server
        try:
            ron.fetch_dem()
        except Exception:
            return exception_factory('Fetching DEM Failed')

    # Delineate channels

    topaz = Topaz.getInstance(wd)
    try:
        topaz.build_channels(csa=csa, mcl=mcl)
    except Exception as e:
        if isinstance(e, MinimumChannelLengthTooShortError):
            return exception_factory(e.__name__, e.__doc__)
        else:
            return exception_factory('Building Channels Failed')

    return success_factory()


@app.route('/runs/<string:runid>/tasks/build_subcatchments/', methods=['POST'])
def task_build_subcatchments(runid):
    wd = get_wd(runid)
    topaz = Topaz.getInstance(wd)

    try:
        topaz.build_subcatchments()
    except Exception as e:
        if isinstance(e, WatershedBoundaryTouchesEdgeError):
            return exception_factory(e.__name__, e.__doc__)
        else:
            return exception_factory('Building Subcatchments Failed')

    return success_factory()


@app.route('/runs/<string:runid>/query/watershed/subcatchments')
@app.route('/runs/<string:runid>/query/watershed/subcatchments/')
def query_watershed_summary_subcatchments(runid):
    wd = get_wd(runid)
    return jsonify(Watershed.getInstance(wd).subs_summary)


@app.route('/runs/<string:runid>/query/watershed/channels')
@app.route('/runs/<string:runid>/query/watershed/channels/')
def query_watershed_summary_channels(runid):
    wd = get_wd(runid)
    return jsonify(Watershed.getInstance(wd).chns_summary)


@app.route('/runs/<string:runid>/report/watershed')
@app.route('/runs/<string:runid>/report/watershed/')
def query_watershed_summary(runid):
    wd = get_wd(runid)
    
    return render_template('reports/subcatchments.htm',
                           watershed=Watershed.getInstance(wd))
                           

@app.route('/runs/<string:runid>/tasks/abstract_watershed/', methods=['GET', 'POST'])
def task_abstract_watershed(runid):
    wd = get_wd(runid)
    watershed = Watershed.getInstance(wd)

    try:
        watershed.abstract_watershed()
    except Exception as e:
        if isinstance(e, ChannelRoutingError):
            return exception_factory(e.__name__, e.__doc__)
        else:
            return exception_factory('Abstracting Watershed Failed')

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/sub_intersection/', methods=['POST'])
def sub_intersection(runid):
    wd = get_wd(runid)

    extent = request.json.get('extent', None)

    top = Topaz.getInstance(wd)
    topaz_ids = top.sub_intersection(extent)
    return jsonify(topaz_ids)

# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/set_landuse_mode/', methods=['POST'])
def set_landuse_mode(runid):

    mode = None
    single_selection = None
    try:
        mode = int(request.form.get('mode', None))
        single_selection = \
            int(request.form.get('landuse_single_selection', None))
    except Exception:
        exception_factory('mode and landuse_single_selection must be provided')

    wd = get_wd(runid)
    landuse = Landuse.getInstance(wd)
    
    try:
        landuse.mode = LanduseMode(mode)
        landuse.single_selection = single_selection
    except Exception:
        exception_factory('error setting landuse mode')

    return success_factory()


@app.route('/runs/<string:runid>/tasks/modify_landuse_coverage', methods=['POST'])
@app.route('/runs/<string:runid>/tasks/modify_landuse_coverage/', methods=['POST'])
def modify_landuse_coverage(runid):
    wd = get_wd(runid)

    dom = request.json.get('dom', None)
    cover = request.json.get('cover', None)
    value = request.json.get('value', None)

    Landuse.getInstance(wd).modify_coverage(dom, cover, value)

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/modify_landuse_mapping/', methods=['POST'])
def task_modify_landuse_mapping(runid):
    wd = get_wd(runid)

    dom = request.json.get('dom', None)
    newdom = request.json.get('newdom', None)

    landuse = Landuse.getInstance(wd)
    landuse.modify_mapping(dom, newdom)

    return success_factory()


@app.route('/runs/<string:runid>/query/landuse')
@app.route('/runs/<string:runid>/query/landuse/')
def query_landuse(runid):
    wd = get_wd(runid)
    return jsonify(Landuse.getInstance(wd).domlc_d)


@app.route('/runs/<string:runid>/resources/legends/slope_aspect')
@app.route('/runs/<string:runid>/resources/legends/slope_aspect/')
def resources_slope_aspect_legend(runid):
    wd = get_wd(runid)

    return render_template('legends/slope_aspect.htm')


@app.route('/runs/<string:runid>/resources/legends/landuse')
@app.route('/runs/<string:runid>/resources/legends/landuse/')
def resources_landuse_legend(runid):
    wd = get_wd(runid)

    return render_template('legends/landuse.htm',
                           legend=Landuse.getInstance(wd).legend)


@app.route('/runs/<string:runid>/resources/legends/soil')
@app.route('/runs/<string:runid>/resources/legends/soil/')
def resources_soil_legend(runid):
    wd = get_wd(runid)

    return render_template('legends/soil.htm',
                           legend=Soils.getInstance(wd).legend)


@app.route('/runs/<string:runid>/resources/legends/sbs')
@app.route('/runs/<string:runid>/resources/legends/sbs/')
def resources_sbs_legend(runid):
    wd = get_wd(runid)

    return render_template('legends/landuse.htm',
                           legend=Baer.getInstance(wd).legend)

@app.route('/runs/<string:runid>/query/landuse/subcatchments')
@app.route('/runs/<string:runid>/query/landuse/subcatchments/')
def query_landuse_subcatchments(runid):
    wd = get_wd(runid)
    return jsonify(Landuse.getInstance(wd).subs_summary)


@app.route('/runs/<string:runid>/query/landuse/channels')
@app.route('/runs/<string:runid>/query/landuse/channels/')
def query_landuse_channels(runid):
    wd = get_wd(runid)
    return jsonify(Landuse.getInstance(wd).chns_summary)


@app.route('/runs/<string:runid>/report/landuse')
@app.route('/runs/<string:runid>/report/landuse/')
def report_landuse(runid):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    landuse = Landuse.getInstance(wd)
    landuseoptions = landuse.landuseoptions

    return render_template('reports/landuse.htm',
                           landuseoptions=landuseoptions,
                           report=Landuse.getInstance(wd).report)


@app.route('/runs/<string:runid>/view/channel_def/<chn_key>')
@app.route('/runs/<string:runid>/view/channel_def/<chn_key>/')
def view_channel_def(runid, chn_key):
    wd = get_wd(runid)
    assert wd is not None

    try:
        chn_d = management.get_channel(chn_key)
    except KeyError:
        return error_factory('Could not find channel def with key "%s"' % chn_key)

    return jsonify(chn_d)


@app.route('/runs/<string:runid>/tasks/build_landuse/', methods=['POST'])
def task_build_landuse(runid):
    wd = get_wd(runid)
    landuse = Landuse.getInstance(wd)

    try:
        landuse.build()
    except Exception:
        return exception_factory('Building Landuse Failed')

    return success_factory()


@app.route('/runs/<string:runid>/view/management/<key>')
@app.route('/runs/<string:runid>/view/management/<key>/')
def view_management(runid, key):
    wd = get_wd(runid)
    assert wd is not None

    landuse = Landuse.getInstance(wd)
    man = landuse.managements[str(key)].get_management()
    contents = str(man)

    r = Response(response=contents, status=200, mimetype="text/plain")
    r.headers["Content-Type"] = "text/plain; charset=utf-8"
    return r


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/modify_landuse/', methods=['POST'])
def task_modify_landuse(runid):
    wd = get_wd(runid)
    landuse = Landuse.getInstance(wd)

    try:
        topaz_ids = request.form.get('topaz_ids', None)
        topaz_ids = topaz_ids.split(',')
        topaz_ids = [str(int(v)) for v in topaz_ids]
        lccode = request.form.get('landuse', None)
        lccode = str(int(lccode))
    except Exception:
        return exception_factory('Unpacking Modify Landuse Args Faied')

    try:
        landuse.modify(topaz_ids, lccode)
    except Exception:
        return exception_factory('Modifying Landuse Failed')

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/set_soil_mode/', methods=['POST'])
def set_soil_mode(runid):

    mode = None
    single_selection = None

    try:
        mode = int(request.form.get('mode', None))
        single_selection = \
            int(request.form.get('soil_single_selection', None))

        single_dbselection = \
            request.form.get('soil_single_dbselection', None)

    except Exception:
        exception_factory('mode and soil_single_selection must be provided')

    wd = get_wd(runid)
    
    try:
        soils = Soils.getInstance(wd)
        soils.mode = SoilsMode(mode)
        soils.single_selection = single_selection
        soils.single_dbselection = single_dbselection

    except Exception:
        exception_factory('error setting soils mode')

    return success_factory()


@app.route('/runs/<string:runid>/query/soils')
@app.route('/runs/<string:runid>/query/soils/')
def query_soils(runid):
    wd = get_wd(runid)
    return jsonify(Soils.getInstance(wd).domsoil_d)


@app.route('/runs/<string:runid>/query/soils/subcatchments')
@app.route('/runs/<string:runid>/query/soils/subcatchments/')
def query_soils_subcatchments(runid):
    wd = get_wd(runid)
    return jsonify(Soils.getInstance(wd).subs_summary)


@app.route('/runs/<string:runid>/query/soils/channels')
@app.route('/runs/<string:runid>/query/soils/channels/')
def query_soils_channels(runid):
    wd = get_wd(runid)
    return jsonify(Soils.getInstance(wd).chns_summary)


@app.route('/runs/<string:runid>/report/soils')
@app.route('/runs/<string:runid>/report/soils/')
def report_soils(runid):
    wd = get_wd(runid)
    return render_template('reports/soils.htm',
                           report=Soils.getInstance(wd).report)

                           
@app.route('/runs/<string:runid>/tasks/build_soil/', methods=['POST'])
def task_build_soil(runid):
    wd = get_wd(runid)
    soils = Soils.getInstance(wd)

    try:
        soils.build()
    except Exception as e:
        if isinstance(e, NoValidSoilsException):
            return exception_factory(e.__name__, e.__doc__)
        else:
            return exception_factory('Building Soil Failed')

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/set_climatestation_mode/', methods=['POST'])
def set_climatestation_mode(runid):

    try:
        mode = int(request.form.get('mode', None))
    except Exception:
        return exception_factory('Could not determine mode')

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climatestation_mode = ClimateStationMode(int(mode))
    except Exception:
        return exception_factory('Building setting climate station mode')

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/set_climatestation/', methods=['POST'])
def set_climatestation(runid):

    try:
        station = int(request.form.get('station', None))
    except Exception:
        return exception_factory('Station not provided')

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climatestation = station
    except Exception:
        return exception_factory('Building setting climate station mode')

    return success_factory()


@app.route('/runs/<string:runid>/query/climatestation')
@app.route('/runs/<string:runid>/query/climatestation/')
def query_climatestation(runid):
    wd = get_wd(runid)
    return jsonify(Climate.getInstance(wd).climatestation)


@app.route('/runs/<string:runid>/query/climate_has_observed')
@app.route('/runs/<string:runid>/query/climate_has_observed/')
def query_climate_has_observed(runid):
    wd = get_wd(runid)
    return jsonify(Climate.getInstance(wd).has_observed)


@app.route('/runs/<string:runid>/report/climate/')
def report_climate(runid):
    wd = get_wd(runid)
    
    climate = Climate.getInstance(wd)
    return render_template('reports/climate.htm',
                           station_meta=climate.climatestation_meta,
                           climate=climate)


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/set_climate_mode/', methods=['POST'])
def set_climate_mode(runid):
    try:
        mode = int(request.form.get('mode', None))
    except Exception:
        return exception_factory('Could not determine mode')

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climate_mode = mode
    except Exception:
        return exception_factory('Building setting climate mode')

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/set_climate_spatialmode/', methods=['POST'])
def set_climate_spatialmode(runid):
    try:
        spatialmode = int(request.form.get('spatialmode', None))
    except Exception:
        return exception_factory('Could not determine mode')

    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.climate_spatialmode = spatialmode
    except Exception:
        return exception_factory('Building setting climate spatial mode')

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/view/closest_stations/')
def view_closest_stations(runid):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        results = climate.find_closest_stations()
    except Exception:
        return exception_factory('Error finding closest stations')
        
    if results is None:
        return Response('<!-- closest_stations is None -->', mimetype='text/html')
        
    options = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]
        options.append('<option value="{id}" {selected}>'
                       '{desc} ({distance_to_query_location:0.1f} km)</option>'
                       .format(**r))

    return Response('n'.join(options), mimetype='text/html')
    

# noinspection PyBroadException
@app.route('/runs/<string:runid>/view/heuristic_stations/')
def view_heuristic_stations(runid):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        results = climate.find_heuristic_stations()
    except Exception:
        return exception_factory('Error finding heuristic stations')

    if results is None:
        return Response('<!-- heuristic_stations is None -->', mimetype='text/html')
        
    options = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]
        options.append('<option value="{id}" {selected}>'
                       '{desc} ({rank_based_on_query_location} | '
                       '{distance_to_query_location:0.1f} km)</option>'
                       .format(**r))

    return Response('n'.join(options), mimetype='text/html')


# noinspection PyBroadException
@app.route('/runs/<string:runid>/view/eu_heuristic_stations/')
def view_eu_heuristic_stations(runid):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        results = climate.find_eu_heuristic_stations()
    except Exception:
        return exception_factory('Error finding heuristic stations')

    if results is None:
        return Response('<!-- heuristic_stations is None -->', mimetype='text/html')

    options = []
    for r in results:
        r['selected'] = ('', 'selected')[r['id'] == climate.climatestation]
        options.append('<option value="{id}" {selected}>'
                       '{desc} ({rank_based_on_query_location})</option>'
                       .format(**r))

    return Response('n'.join(options), mimetype='text/html')


# noinspection PyBroadException
@app.route('/runs/<string:runid>/view/climate_monthlies')
@app.route('/runs/<string:runid>/view/climate_monthlies/')
def view_climate_monthlies(runid):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)
    
    try:
        station_meta = climate.climatestation_meta
    except Exception:
        return exception_factory('Could not find climatestation_meta')

    if station_meta is None:
        return error_factory('Climate Station not Set')

    assert isinstance(station_meta, StationMeta)
    return render_template('controls/climate_monthlies.htm',
                           title='Summary for the selected station',
                           station=station_meta.as_dict(include_monthlies=True))
    

# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/build_climate', methods=['POST'])
@app.route('/runs/<string:runid>/tasks/build_climate/', methods=['POST'])
def task_build_climate(runid):
    wd = get_wd(runid)
    climate = Climate.getInstance(wd)

    try:
        climate.parse_inputs(request.form)
    except Exception:
        return exception_factory('Error parsing climate inputs')

    try:
        climate.build()
    except Exception:
        return exception_factory('Error building climate')

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/set_hourly_seepage', methods=['POST'])
@app.route('/runs/<string:runid>/tasks/set_hourly_seepage/', methods=['POST'])
def task_set_hourly_seepage(runid):

    try:
        state = request.json.get('hourly_seepage', None)
    except Exception:
        return exception_factory('Error parsing state')

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)
        wepp.set_hourly_seepage(state)
    except Exception:
        return exception_factory('Error setting state')

    return success_factory()

# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/set_run_flowpaths', methods=['POST'])
@app.route('/runs/<string:runid>/tasks/set_run_flowpaths/', methods=['POST'])
def task_set_run_flowpaths(runid):

    try:
        state = request.json.get('run_flowpaths', None)
    except Exception:
        return exception_factory('Error parsing state')

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        wepp = Wepp.getInstance(wd)
        wepp.set_run_flowpaths(state)
    except Exception:
        return exception_factory('Error setting state')

    return success_factory()

# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/set_public', methods=['POST'])
@app.route('/runs/<string:runid>/tasks/set_public/', methods=['POST'])
def task_set_public(runid):
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
        return exception_factory('Error parsing state')

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        ron.public = state
    except Exception:
        return exception_factory('Error setting state')

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/set_readonly', methods=['POST'])
@app.route('/runs/<string:runid>/tasks/set_readonly/', methods=['POST'])
def task_set_readonly(runid):
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
        return exception_factory('Error parsing state')

    if state is None:
        return error_factory('state is None')

    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        ron.readonly = state
    except Exception:
        return exception_factory('Error setting state')

    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/query/status/<nodb>', methods=['GET', 'POST'])
@app.route('/runs/<string:runid>/query/status/<nodb>/', methods=['GET', 'POST'])
def get_wepp_run_status(runid, nodb):
    wd = get_wd(runid)

    if nodb == 'wepp':
        wepp = Wepp.getInstance(wd)
        try:
            return success_factory(wepp.get_log_last())
        except:
            return exception_factory('Could not determine status')

    elif nodb == 'climate':
        climate = Climate.getInstance(wd)
        try:
            return success_factory(climate.get_log_last())
        except:
            return exception_factory('Could not determine status')

    return error_factory('Unknown nodb')


# noinspection PyBroadException
@app.route('/runs/<string:runid>/report/wepp/results')
@app.route('/runs/<string:runid>/report/wepp/results/')
def report_wepp_results(runid):

    try:
        return render_template('controls/wepp_reports.htm')
    except:
        return exception_factory('Error building reports template')


# noinspection PyBroadException
@app.route('/runs/<string:runid>/report/<nodb>/log')
@app.route('/runs/<string:runid>/report/<nodb>/log/')
def get_wepp_run_status_full(runid, nodb):
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
        return exception_factory('Error reading status.log')


# noinspection PyBroadException
@app.route('/runs/<string:runid>/query/subcatchments_summary')
@app.route('/runs/<string:runid>/query/subcatchments_summary/')
def query_subcatchments_summary(runid):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:
        subcatchments_summary = ron.subs_summary()

        return jsonify(subcatchments_summary)
    except:
        return exception_factory('Error building summary')


# noinspection PyBroadException
@app.route('/runs/<string:runid>/query/channels_summary')
@app.route('/runs/<string:runid>/query/channels_summary/')
def query_channels_summary(runid):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:
        channels_summary = ron.chns_summary()

        return jsonify(channels_summary)
    except:
        return exception_factory('Error building summary')
    
    
# noinspection PyBroadException
@app.route('/runs/<string:runid>/report/wepp/prep_details')
@app.route('/runs/<string:runid>/report/wepp/prep_details/')
def get_wepp_prep_details(runid):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:
        subcatchments_summary = ron.subs_summary()
        channels_summary = ron.chns_summary()

        unitizer = Unitizer.getInstance(wd)

        return render_template('reports/wepp/prep_details.htm',
                               unitizer_nodb=unitizer,
                               precisions=wepppy.nodb.unitizer.precisions,
                               subcatchments_summary=subcatchments_summary,
                               channels_summary=channels_summary,
                               user=current_user,
                               ron=ron)
    except:
        return exception_factory('Error building summary')

# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/run_wepp', methods=['POST'])
@app.route('/runs/<string:runid>/tasks/run_wepp/', methods=['POST'])
def submit_task_run_wepp(runid):
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)

    try:
        wepp.parse_inputs(request.form)
    except Exception:
        return exception_factory('Error parsing climate inputs')

    try:
        wepp.clean()
    except Exception:
        return exception_factory('Error cleaning wepp directories')
    
    try:

        watershed = Watershed.getInstance(wd)
        translator = Watershed.getInstance(wd).translator_factory()
        runs_dir = os.path.abspath(wepp.runs_dir)

        #
        # Prep Hillslopes
        wepp.prep_hillslopes()
        
        #
        # Run Hillslopes
#        for i, (topaz_id, _) in enumerate(watershed.sub_iter()):
#            wepp_id = translator.wepp(top=int(topaz_id))
#            assert run_hillslope(wepp_id, runs_dir)

        wepp.run_hillslopes()
        
        #
        # Prep Watershed
        wepp.prep_watershed()
        
        #
        # Run Watershed
        wepp.run_watershed()

        try:
            from wepppy.weppcloud import RunStatistics
            rs = RunStatistics.getInstance('/geodata/weppcloud_runs')
            rs.increment_hillruns(watershed.config_stem, watershed.sub_n)
        except:
            pass

    except Exception:
        return exception_factory('Error running wepp')
        
    return success_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/run_model_fit', methods=['POST'])
@app.route('/runs/<string:runid>/tasks/run_model_fit/', methods=['POST'])
def submit_task_run_model_fit(runid):
    wd = get_wd(runid)
    observed = Observed.getInstance(wd)

    textdata = request.json.get('data', None)

    try:
        observed.parse_textdata(textdata)
    except Exception:
        return exception_factory('Error parsing text')

    try:
        observed.calc_model_fit()
    except Exception:
        return exception_factory('Error running model fit')

    return success_factory()

# noinspection PyBroadException
@app.route('/runs/<string:runid>/report/observed')
@app.route('/runs/<string:runid>/report/observed/')
def report_observed(runid):
    wd = get_wd(runid)
    observed = Observed.getInstance(wd)
    ron = Ron.getInstance(wd)

    return render_template('reports/wepp/observed.htm',
                           results=observed.results,
                           ron=ron,
                           user=current_user)

@app.route('/runs/<string:runid>/plot/observed/<selected>/')
@app.route('/runs/<string:runid>/plot/observed/<selected>/')
def plot_observed(runid, selected):

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)

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
                           user=current_user)


@app.route('/runs/<string:runid>/resources/observed/<file>')
def resources_observed_data(runid, file):

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    fn = _join(ron.observed_dir, file)

    assert _exists(fn)
    return send_file(fn, mimetype='text/csv', attachment_filename=file)


@app.route('/runs/<string:runid>/query/wepp/phosphorus_opts')
@app.route('/runs/<string:runid>/query/wepp/phosphorus_opts/')
def query_wepp_phos_opts(runid):
    wd = get_wd(runid)
    phos_opts = Wepp.getInstance(wd).phosphorus_opts.asdict()
    return jsonify(phos_opts)


@app.route('/runs/<string:runid>/report/wepp/run_summary')
@app.route('/runs/<string:runid>/report/wepp/run_summary/')
def report_wepp_run_summary(runid):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    flowpaths_n = len(glob(_join(wd, 'wepp/flowpaths/output/*.plot.dat')))
    subs_n = len(glob(_join(wd, 'wepp/output/*.loss.dat')))

    with open(_join(wd, 'wepp/runs/status.log')) as fp:
        lines = fp.readlines()
        t0 = parse_datetime(lines[0])
        tend = parse_datetime(lines[-1])

    return render_template('reports/wepp_run_summary.htm',
                           flowpaths_n=flowpaths_n,
                           subs_n=subs_n,
                           run_time=tend-t0,
                           ron=ron)


@app.route('/runs/<string:runid>/report/wepp/summary')
@app.route('/runs/<string:runid>/report/wepp/summary/')
def report_wepp_loss(runid):
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

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    loss = Wepp.getInstance(wd).report_loss(exclude_yr_indxs=exclude_yr_indxs)
    out_rpt = OutletSummary(loss)
    hill_rpt = HillSummary(loss, class_fractions=class_fractions, fraction_under=fraction_under)
    chn_rpt = ChannelSummary(loss)
    avg_annual_years = loss.avg_annual_years
    excluded_years = loss.excluded_years
    translator = Watershed.getInstance(wd).translator_factory()
    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/summary.htm',
                           out_rpt=out_rpt,
                           hill_rpt=hill_rpt,
                           chn_rpt=chn_rpt,
                           avg_annual_years=avg_annual_years,
                           excluded_years=excluded_years,
                           translator=translator,
                           unitizer_nodb=unitizer,
                           precisions=wepppy.nodb.unitizer.precisions,
                           ron=ron,
                           user=current_user)


@app.route('/runs/<string:runid>/report/wepp/yearly_watbal')
@app.route('/runs/<string:runid>/report/wepp/yearly_watbal/')
def report_wepp_yearly_watbal(runid):
    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))

    except:
        exclude_yr_indxs = [0, 1]

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)

    totwatsed_fn = _join(wepp.output_dir, 'totalwatsed.txt')
    totwatsed = TotalWatSed(totwatsed_fn, wepp.baseflow_opts,
                            phosOpts=wepp.phosphorus_opts)
    totwatbal = TotalWatbal(totwatsed,
                            exclude_yr_indxs=exclude_yr_indxs)

    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/yearly_watbal.htm',
                           unitizer_nodb=unitizer,
                           precisions=wepppy.nodb.unitizer.precisions,
                           rpt=totwatbal,
                           ron=ron,
                           user=current_user)

@app.route('/runs/<string:runid>/report/wepp/avg_annual_watbal')
@app.route('/runs/<string:runid>/report/wepp/avg_annual_watbal/')
def report_wepp_avg_annual_watbal(runid):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    hill_rpt = wepp.report_hill_watbal()
    chn_rpt = wepp.report_chn_watbal()

    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/avg_annual_watbal.htm',
                           unitizer_nodb=unitizer,
                           precisions=wepppy.nodb.unitizer.precisions,
                           hill_rpt=hill_rpt,
                           chn_rpt=chn_rpt,
                           ron=ron,
                           user=current_user)


@app.route('/runs/<string:runid>/resources/wepp/daily_streamflow.csv')
def resources_wepp_streamflow(runid):
    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))

    except:
        exclude_yr_indxs = [0, 1]

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    wepppost = WeppPost.getInstance(wd)
    fn = _join(ron.export_dir, 'daily_streamflow.csv')
    wepppost.export_streamflow(fn, exclude_yr_indxs=exclude_yr_indxs)

    assert _exists(fn)

    return send_file(fn, mimetype='text/csv', attachment_filename='daily_streamflow.csv')


@app.route('/runs/<string:runid>/resources/wepp/totalwatsed.csv')
def resources_wepp_totalwatsed(runid):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    fn = _join(ron.export_dir, 'totalwatsed.csv')

    totwatsed = TotalWatSed(_join(ron.output_dir, 'totalwatsed.txt'),
                            wepp.baseflow_opts, wepp.phosphorus_opts)
    totwatsed.export(fn)
    assert _exists(fn)

    return send_file(fn, mimetype='text/csv', attachment_filename='totalwatsed.csv')


@app.route('/runs/<string:runid>/plot/wepp/streamflow')
@app.route('/runs/<string:runid>/plot/wepp/streamflow/')
def plot_wepp_streamflow(runid):
    try:
        res = request.args.get('exclude_yr_indxs')
        exclude_yr_indxs = []
        for yr in res.split(','):
            if isint(yr):
                exclude_yr_indxs.append(int(yr))

    except:
        exclude_yr_indxs = [0, 1]

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    
    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/daily_streamflow_graph.htm',
                           unitizer_nodb=unitizer,
                           precisions=wepppy.nodb.unitizer.precisions,
                           exclude_yr_indxs=','.join(str(yr) for yr in exclude_yr_indxs),
                           ron=ron,
                           user=current_user)

@app.route('/runs/<string:runid>/report/wepp/return_periods')
@app.route('/runs/<string:runid>/report/wepp/return_periods/')
def report_wepp_return_periods(runid):

    extraneous = request.args.get('extraneous', None) == 'true'
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    report = Wepp.getInstance(wd).report_return_periods()
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


@app.route('/runs/<string:runid>/report/wepp/frq_flood')
@app.route('/runs/<string:runid>/report/wepp/frq_flood/')
def report_wepp_frq_flood(runid):
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


@app.route('/runs/<string:runid>/report/wepp/sediment_delivery')
@app.route('/runs/<string:runid>/report/wepp/sediment_delivery/')
def report_wepp_sediment_delivery(runid):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    sed_del = Wepp.getInstance(wd).report_sediment_delivery()
    translator = Watershed.getInstance(wd).translator_factory()

    unitizer = Unitizer.getInstance(wd)

    return render_template('reports/wepp/sediment_delivery.htm',
                           unitizer_nodb=unitizer,
                           precisions=wepppy.nodb.unitizer.precisions,
                           sed_del=sed_del,
                           translator=translator,
                           ron=ron,
                           user=current_user)


@app.route('/runs/<string:runid>/query/wepp/runoff/subcatchments')
@app.route('/runs/<string:runid>/query/wepp/runoff/subcatchments/')
def query_wepp_sub_runoff(runid):
    # blackwood http://wepp1.nkn.uidaho.edu/weppcloud/runs/7f6d9b28-9967-4547-b121-e160066ed687/0/
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('Runoff'))


@app.route('/runs/<string:runid>/query/wepp/subrunoff/subcatchments')
@app.route('/runs/<string:runid>/query/wepp/subrunoff/subcatchments/')
def query_wepp_sub_subrunoff(runid):
    # blackwood http://wepp1.nkn.uidaho.edu/weppcloud/runs/7f6d9b28-9967-4547-b121-e160066ed687/0/
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('Subrunoff'))


@app.route('/runs/<string:runid>/query/wepp/baseflow/subcatchments')
@app.route('/runs/<string:runid>/query/wepp/baseflow/subcatchments/')
def query_wepp_sub_baseflow(runid):
    # blackwood http://wepp1.nkn.uidaho.edu/weppcloud/runs/7f6d9b28-9967-4547-b121-e160066ed687/0/
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('Baseflow'))
    
    
@app.route('/runs/<string:runid>/query/wepp/loss/subcatchments')
@app.route('/runs/<string:runid>/query/wepp/loss/subcatchments/')
def query_wepp_sub_loss(runid):
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('DepLoss'))
    
    
@app.route('/runs/<string:runid>/query/wepp/phosphorus/subcatchments')
@app.route('/runs/<string:runid>/query/wepp/phosphorus/subcatchments/')
def query_wepp_sub_phosphorus(runid):
    wd = get_wd(runid)
    wepp = Wepp.getInstance(wd)
    return jsonify(wepp.query_sub_val('Total P Density'))
    
    
@app.route('/runs/<string:runid>/query/chn_summary/<topaz_id>')
@app.route('/runs/<string:runid>/query/chn_summary/<topaz_id>/')
def query_ron_chn_summary(runid, topaz_id):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    return jsonify(ron.chn_summary(topaz_id))
    
    
@app.route('/runs/<string:runid>/query/sub_summary/<topaz_id>')
@app.route('/runs/<string:runid>/query/sub_summary/<topaz_id>/')
def query_ron_sub_summary(runid, topaz_id):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    return jsonify(ron.sub_summary(topaz_id))
    
    
@app.route('/runs/<string:runid>/report/chn_summary/<topaz_id>')
@app.route('/runs/<string:runid>/report/chn_summary/<topaz_id>/')
def report_ron_chn_summary(runid, topaz_id):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    return render_template('reports/hill.htm',
                           d=ron.chn_summary(topaz_id))

@app.route('/runs/<string:runid>/query/topaz_wepp_map')
@app.route('/runs/<string:runid>/query/topaz_wepp_map/')
def query_topaz_wepp_map(runid):
    wd = get_wd(runid)
    translator = Watershed.getInstance(wd).translator_factory()

    d = dict([(wepp, translator.top(wepp=wepp)) for wepp in translator.iter_wepp_sub_ids()])

    return jsonify(d)
    
@app.route('/runs/<string:runid>/report/sub_summary/<topaz_id>')
@app.route('/runs/<string:runid>/report/sub_summary/<topaz_id>/')
def report_ron_sub_summary(runid, topaz_id):
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    return render_template('reports/hill.htm',
                           d=ron.sub_summary(topaz_id))


# noinspection PyBroadException
@app.route('/runs/<string:runid>/resources/wepp_loss.tif')
def resources_wepp_loss(runid):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        loss_grid_wgs = _join(ron.plot_dir, 'loss.WGS.tif')

        if _exists(loss_grid_wgs):
            return send_file(loss_grid_wgs, mimetype='image/tiff')

        return error_factory('loss_grid_wgs does not exist')

    except Exception:
        return exception_factory()

# noinspection PyBroadException
@app.route('/runs/<string:runid>/query/bound_coords')
@app.route('/runs/<string:runid>/query/bound_coords/')
def query_bound_coords(runid):
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
        return exception_factory()

#
# Unitizer
#

@app.route('/runs/<string:runid>/unitizer')
@app.route('/runs/<string:runid>/unitizer/')
def unitizer_route(runid):

    try:
        wd = get_wd(runid)
        unitizer = Unitizer.getInstance(wd)

        value = request.args.get('value')
        in_units = request.args.get('in_units')
        ctx_processer = unitizer.context_processor_package()

        contents = ctx_processer['unitizer'](float(value), in_units)
        return success_factory(contents)

        return error_factory('loss_grid_wgs does not exist')

    except Exception:
        return exception_factory()

@app.route('/runs/<string:runid>/unitizer_units')
@app.route('/runs/<string:runid>/unitizer_units/')
def unitizer_units_route(runid):

    try:
        wd = get_wd(runid)
        unitizer = Unitizer.getInstance(wd)

        in_units = request.args.get('in_units')
        ctx_processer = unitizer.context_processor_package()

        contents = ctx_processer['unitizer_units'](in_units)
        return success_factory(contents)

        return error_factory('loss_grid_wgs does not exist')

    except Exception:
        return exception_factory()


#
# BAER
#                           


# noinspection PyBroadException
@app.route('/runs/<string:runid>/query/baer_wgs_map')
@app.route('/runs/<string:runid>/query/baer_wgs_map/')
def query_baer_wgs_bounds(runid):
    try:
        wd = get_wd(runid)
        baer = Baer.getInstance(wd)
        if not baer.has_map:
            return error_factory('No SBS map has been specified')
            
        return success_factory(dict(bounds=baer.bounds,
                               classes=baer.classes,
                               imgurl='../resources/baer.png'))
    except Exception:
        return exception_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/view/modify_burn_class')
@app.route('/runs/<string:runid>/view/modify_burn_class/')
def query_baer_class_map(runid):
    try:
        wd = get_wd(runid)
        baer = Baer.getInstance(wd)
        if not baer.has_map:
            return error_factory('No SBS map has been specified')
            
        return render_template('mods/baer/classify.htm', baer=baer)
    except Exception:
        return exception_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/modify_burn_class', methods=['POST'])
@app.route('/runs/<string:runid>/tasks/modify_burn_class/', methods=['POST'])
def task_baer_class_map(runid):
    try:
        wd = get_wd(runid)
        baer = Baer.getInstance(wd)
        if not baer.has_map:
            return error_factory('No SBS map has been specified')
            
        classes = request.json.get('classes', None)
        nodata_vals = request.json.get('nodata_vals', None)
        
        baer.modify_burn_class(classes, nodata_vals)
        return success_factory()
    except Exception:
        return exception_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/resources/baer.png')
def resources_baer_sbs(runid):
    try:
        wd = get_wd(runid)
        baer = Baer.getInstance(wd)
        if not baer.has_map:
            return error_factory('No SBS map has been specified')
        
        fn = _join(baer.baer_dir, 'baer.wgs.rgba.png')
        return send_file(fn, mimetype='image/png')
    except Exception:
        return exception_factory()


# noinspection PyBroadException
@app.route('/runs/<string:runid>/tasks/upload_sbs/', methods=['POST'])
def task_upload_sbs(runid):
    wd = get_wd(runid)
    baer = Baer.getInstance(wd)
    
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
        
    try:
        file.save(_join(baer.baer_dir, filename))
    except Exception:
        return exception_factory('Could not save file')

    try:
        res = baer.validate(filename)
    except Exception:
        return exception_factory('Failed validating file')

    return success_factory(res)


@app.route('/runs/<runid>/tasks/run_debris_flow', methods=['POST'])
@app.route('/runs/<runid>/tasks/run_debris_flow/', methods=['POST'])
def run_debris_flow(runid):
    # get working dir of original directory
    wd = get_wd(runid)

    try:
        debris_flow = DebrisFlow.getInstance(wd)
        debris_flow.run_debris_flow()
        return success_factory()

    except:
        return exception_factory('Error Running Debris Flow')


@app.route('/runs/<string:runid>/report/debris_flow')
@app.route('/runs/<string:runid>/report/debris_flow/')
def report_debris_flow(runid):
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


@app.route('/combined_ws_viewer')
@app.route('/combined_ws_viewer/')
def combined_ws_viewer():
    return render_template('combined_ws_viewer.htm')


@app.route('/combined_ws_viewer/url_generator', methods=['GET', 'POST'])
@app.route('/combined_ws_viewer/url_generator/', methods=['GET', 'POST'])
def combined_ws_viewer_url_gen():
    if current_user.is_authenticated:
        if not current_user.roles:
            user_datastore.add_role_to_user(current_user.email, 'User')

    title = request.form.get('title', '')
    runids = request.form.get('runids', '')  # devvmfac-3e27-459a-96d4-f1a731fe7502, devvm647-3e1d-4c81-b23f-9700145612c0
    runids = runids.replace(',', ' ').split()

    ws = []
    extents = None
    center_lat = None
    center_lng = None
    zoom = None
    has_phos = True

    for i, runid in enumerate(runids):
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        wepp = Wepp.getInstance(wd)

        has_phos = has_phos and wepp.phosphorus_opts.isvalid

        if i == 0:
            extents = ron.map.extent
            zoom = ron.map.zoom
        else:
            _l, _b, _r, _t = ron.map.extent
            l, b, r, t = extents

            if _l < l:
                extents[0] = l

            if _b < b:
                extents[1] = b

            if _r > r:
                extents[2] = r

            if _t > t:
                extents[3] = t

            if ron.map.zoom < zoom:
                zoom = ron.map.zoom

        ws.append(dict(runid=runid, cfg=ron.config_stem))

    if extents is not None:
        center_lng = float(np.mean([extents[0], extents[2]]))
        center_lat = float(np.mean([extents[1], extents[3]]))

    if zoom is not None:
        zoom -= 1

    phos_opts = ('', '"phosphorus":1.0,')[has_phos]

    _url = '/weppcloud/combined_ws_viewer/?zoom={zoom}&center=[{center_lat},{center_lng}]&' \
           'ws={ws}&varopts={{"runoff":10,"subrunoff":10,"baseflow":10,{phos_opts}"loss":4000}}&' \
           'varname=loss&title={title}'

    url = None
    if center_lng is not None and \
       center_lat is not None and \
       zoom is not None and \
       len(ws) > 0:
        url = _url.format(center_lat=center_lat, center_lng=center_lng,
                          zoom=zoom, ws=json.dumps(ws), title=title,
                          phos_opts=phos_opts)

    return render_template('combined_ws_viewer_url_gen.htm',
        url=url, user=current_user, title=title, runids=', '.join(runids))


@app.route('/dev/usage_statistics')
def usage_statistics():
    from wepppy.weppcloud import RunStatistics
    rs = RunStatistics.getInstance('/geodata/weppcloud_runs')
    fn = rs._json
    return send_file(fn, mimetype='application/json')


def get_config_stem(wd):
    ron = Ron.getInstance(wd)
    return ron.config_stem


@app.route('/dev/runid_query/<wc>')
def runid_query(wc):
    if current_user.has_role('Root') or \
       current_user.has_role('Admin') or \
       current_user.has_role('Dev'):

        wds = glob(_join('/geodata/weppcloud_runs', '{}*'.format(wc)))
        return jsonify([_join('weppcloud/runs', _split(wd)[-1], get_config_stem(wd)) for wd in wds])
    else:
        return error_factory('not authorized')


if __name__ == '__main__':
    app.run(debug=True)
