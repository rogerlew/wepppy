from os.path import exists as _exists
from os.path import join as _join
from glob import glob
import os
from datetime import datetime

from typing import Optional, Type

from wepppy.nodb.ron import Ron
from wepppy.nodb.unitizer import Unitizer
from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.all_your_base import isfloat


RunModel: Optional[Type] = None
UserModel: Optional[Type] = None

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
    return True


def _get_run_owner(runid):
    try:
        if RunModel is None or UserModel is None:
            return '-'

        run = RunModel.query.filter(RunModel.runid == runid).first()
        if run is None:
            return '-'
        if run.owner_id is None:
            return 'anonymous'

        owner = UserModel.query.filter(UserModel.id == run.owner_id).first()
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

def _get_all_users():
    if UserModel is None:
        return []
    return UserModel.query.order_by(UserModel.last_login_at).all()

def register_context_processors(app, get_all_runs, user_model, run_model):
    global RunModel, UserModel
    RunModel = run_model
    UserModel = user_model

    @app.context_processor
    def inject_site_prefix():
        return dict(site_prefix=app.config.get('SITE_PREFIX', ''))
        
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

    @app.context_processor
    def current_ron_processor():
        # get current runid from request path
        from flask import request
        from wepppy.nodb.ron import RonViewModel
        runid = None
        path_parts = request.path.split('/')
        try:
            _indx = path_parts.index('runs')
            runid = path_parts[_indx + 1]
            ron = RonViewModel.getInstanceFromRunID(runid)
            return dict(current_ron=ron)
        except:
            return dict(current_ron=None)

    @app.context_processor
    def security_processor():
        return dict(run_exists=_run_exists,
                    get_run_name=_get_run_name,
                    get_run_owner=_get_run_owner,
                    get_last_modified=_get_last_modified,
                    get_all_runs=get_all_runs,
                    get_all_users=_get_all_users)
