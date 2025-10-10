# Copyright (c) 2016-, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import logging
from datetime import datetime
from glob import glob
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

import awesome_codename

from werkzeug.middleware.proxy_fix import ProxyFix

from flask import (
    Flask, jsonify, request, render_template
)

from sqlalchemy import func

from flask_sqlalchemy import SQLAlchemy
from flask_security import (
    RegisterForm,
    Security, SQLAlchemyUserDatastore,
    UserMixin, RoleMixin
)

from wtforms.validators import DataRequired as Required
from flask_mail import Mail
from flask_session import Session
from flask_session.sessions import RedisSessionInterface
from flask_migrate import Migrate

from wtforms import StringField

from wepppy.nodb.core import Ron
from wepppy.weppcloud.utils.helpers import get_wd

import logging
from wepppy.weppcloud._jinja_filters import register_jinja_filters
from wepppy.weppcloud._blueprints_context import register_blueprints
from wepppy.weppcloud._context_processors import register_context_processors
from wepppy.weppcloud._config_app import config_app
from wepppy.weppcloud._config_logging import config_logging

config_logging(logging.INFO)

app = Flask(__name__)
config_app(app)

# Flask 3 removed the legacy attribute that older extensions (Flask-Session)
# still reference; reintroduce it for compatibility.
if not hasattr(app, "session_cookie_name"):
    app.session_cookie_name = app.config.get("SESSION_COOKIE_NAME", "session")

# Configure ProxyFix middleware to handle reverse proxy headers
# This ensures Flask correctly interprets X-Forwarded-* headers when
# running behind a reverse proxy (nginx, Apache, etc.)
# x_for=1: Trust X-Forwarded-For for client IP
# x_proto=1: Trust X-Forwarded-Proto for scheme (http/https)  
# x_host=1: Trust X-Forwarded-Host for hostname
# x_port=1: Trust X-Forwarded-Port for port
# x_prefix=1: Trust X-Forwarded-Prefix for URL prefix
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1
)

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

# Represents a WEPPcloud run
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

def get_all_runs():
    return [run for run in Run.query.order_by(Run.date_created).all()]

def get_run_owners(runid):
    return User.query.filter(User.runs.any(Run.runid == runid)).all()

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

# flask-security extended form
class ExtendedRegisterForm(RegisterForm):
    first_name = StringField('First Name', [Required()])
    last_name = StringField('Last Name', [Required()])

migrate = Migrate(app, db, directory='/workdir/wepppy/wepppy/weppcloud/migrations')

security = Security(app, user_datastore,
                    register_form=ExtendedRegisterForm,
                    confirm_register_form=ExtendedRegisterForm)

mail = Mail(app)
session_manager = Session(app)

register_jinja_filters(app)
register_blueprints(app)
register_context_processors(app, get_all_runs, User, Run)
