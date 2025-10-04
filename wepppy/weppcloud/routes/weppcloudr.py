import os
import json
import io

import pathlib
from subprocess import Popen, PIPE
import urllib
from urllib.parse import urlencode

from concurrent.futures import ThreadPoolExecutor

from typing import Optional

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from os.path import abspath, basename

from flask import abort, Blueprint, request
from flask_security import current_user

from wepppy.weppcloud.utils.helpers import get_wd, exception_factory

from wepppy.nodb.core import Ron, Wepp, Watershed

from ._run_context import RunContext, load_run_context

VIZ_RSCRIPT_DIR = '/workdir/viz-weppcloud/scripts/R/'
VIZ_RMARKDOWN_DIR = '/workdir/viz-weppcloud/scripts/Rmd'
WEPPCLOUDR_DIR = '/workdir/WEPPcloudR/scripts'


weppcloudr_bp = Blueprint('weppcloud', __name__)

@weppcloudr_bp.route('/runs/<string:runid>/<config>/viz/<r_format>/<routine>')
@weppcloudr_bp.route('/runs/<string:runid>/<config>/viz/<r_format>/<routine>/')
def viz_r(runid, config, r_format, routine):
    from wepppy.weppcloud.app import get_run_owners

    assert config is not None

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
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



def _weppcloudr_script_locator(routine, user=None):
    global WEPPCLOUDR_DIR 
    if user is None:
        return _join(WEPPCLOUDR_DIR, routine)
    else:
        rscript =  _join(WEPPCLOUDR_DIR, 'users', user, routine)
        assert pathlib.Path(WEPPCLOUDR_DIR) in  pathlib.Path(rscript).parents
        return rscript


@weppcloudr_bp.route('/runs/<string:runid>/<config>/WEPPcloudR/<routine>')
@weppcloudr_bp.route('/runs/<string:runid>/<config>/WEPPcloudR/<routine>/')
def weppcloudr(runid, config, routine):
    from wepppy.weppcloud.app import get_run_owners

    assert config is not None

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
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
    
    return weppcloudr_runner(runid, config, routine, user, ctx=ctx)


def weppcloudr_runner(runid, config, routine, user, ctx: Optional[RunContext] = None):
    from wepppy.weppcloud.app import get_file_sha1
    if ctx is None:
        ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    viz_export_dir = _join(wd, 'export/WEPPcloudR')
    if not _exists(viz_export_dir):
        os.mkdir(viz_export_dir)
        
    sub_fn = _join(wd, 'export', 'totalwatsed2.csv')
    sub_sha = get_file_sha1(sub_fn)

    try:
        assert routine.endswith('.R') or routine.endswith('.Rmd'), routine

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


@weppcloudr_bp.route('/runs/<string:runid>/<config>/report/deval_details')
@weppcloudr_bp.route('/runs/<string:runid>/<config>/report/deval_details/')
def deval_details(runid, config):
    ctx = load_run_context(runid, config)
    try:
        wd = str(ctx.active_root)
        from wepppy.export import arc_export
        arc_export(wd)
    except:
        return exception_factory('Error running script', runid=runid)

    return weppcloudr_runner(runid, config, routine='new_report.Rmd', user='chinmay', ctx=ctx)


@weppcloudr_bp.route('/WEPPcloudR/proxy/<routine>', methods=['GET', 'POST'])
@weppcloudr_bp.route('/WEPPcloudR/proxy/<routine>/', methods=['GET', 'POST'])
def weppcloudr_proxy(routine):
    from wepppy.weppcloud.app import get_run_owners
    from wepppy.weppcloud.app import user_datastore

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
