# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import join as _join
from os.path import exists as _exists

from time import time

import subprocess

_thisdir = os.path.dirname(__file__)
_template_dir = _join(_thisdir, "templates")
_wepp = _join(_thisdir, "../", "bin", "wepp")


def _template_loader(fn):
    global _template_dir
    
    with open(_join(_template_dir, fn)) as fp:
        _template = fp.readlines()
        
        # the watershedslope.template contains comments.
        # here we strip those out
        _template = [L[:L.find('#')] for L in _template]
        _template = [L.strip() for L in _template]
        _template = '\n'.join(_template)
        
    return _template


def hill_template_loader():
    return _template_loader("hillslope.template")


def flowpath_template_loader():
    return _template_loader("flowpath.template")


def watershed_template_loader():
    return _template_loader("watershed.template")
    
    
def hillstub_template_loader():
    return """
M
Y
../output/H{wepp_id}.pass.dat"""


def make_flowpath_run(fp, sim_years, runs_dir):
    _fp_template = flowpath_template_loader()

    s = _fp_template.format(fp=fp,
                            sim_years=sim_years)

    fn = _join(runs_dir, '%s.run' % fp)
    with open(fn, 'w') as fp:
        fp.write(s)


def make_hillslope_run(wepp_id, sim_years, runs_dir):
    _hill_template = hill_template_loader()
    
    s = _hill_template.format(wepp_id=wepp_id, 
                              sim_years=sim_years)
            
    fn = _join(runs_dir, 'p%s.run' % wepp_id)
    with open(fn, 'w') as fp:
        fp.write(s)


def run_hillslope(wepp_id, runs_dir):
    t0 = time()

    cmd = [os.path.abspath(_wepp)]

    assert _exists(_join(runs_dir, 'p%i.man' % wepp_id))
    assert _exists(_join(runs_dir, 'p%i.slp' % wepp_id))
    assert _exists(_join(runs_dir, 'p%i.cli' % wepp_id))
    assert _exists(_join(runs_dir, 'p%i.sol' % wepp_id))

    _run = open(_join(runs_dir, 'p%i.run' % wepp_id))
    _log = open(_join(runs_dir, 'p%i.err' % wepp_id), 'w')

    p = subprocess.Popen(cmd, stdin=_run, stdout=_log, stderr=_log, cwd=runs_dir)
    p.wait()
    _run.close()
    _log.close()

    log_fn = _join(runs_dir, 'p%i.err' % wepp_id)
    with open(log_fn) as fp:
        lines = fp.readlines()
        for L in lines:
            if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in L:
                return True, wepp_id, time() - t0
                    
    raise Exception('Error running wepp for wepp_id %i\nSee %s'
                    % (wepp_id, log_fn))


def run_flowpath(flowpath, runs_dir):
    t0 = time()

    cmd = [os.path.abspath(_wepp)]

    assert _exists(_join(runs_dir, '%s.man' % flowpath))
    assert _exists(_join(runs_dir, '%s.slp' % flowpath))
    assert _exists(_join(runs_dir, '%s.cli' % flowpath))
    assert _exists(_join(runs_dir, '%s.sol' % flowpath))

    _run = open(_join(runs_dir, '%s.run' % flowpath))
    _log = open(_join(runs_dir, '%s.err' % flowpath), 'w')

    p = subprocess.Popen(cmd, stdin=_run, stdout=_log, stderr=_log, cwd=runs_dir)
    p.wait()
    _run.close()
    _log.close()

    log_fn = _join(runs_dir, '%s.err' % flowpath)
    with open(log_fn) as fp:
        lines = fp.readlines()
        for L in lines:
            if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in L:
                return True, flowpath, time() - t0

    raise Exception('Error running wepp for %s\nSee %s'
                    % (flowpath, log_fn))


def make_watershed_run(sim_years, wepp_ids, runs_dir):
    
    block = []
    for wepp_id in wepp_ids:
        block.append(hillstub_template_loader().format(wepp_id=wepp_id))
    block = ''.join(block)
    
    _watershed_template = watershed_template_loader()
    
    s = _watershed_template.format(sub_n=len(wepp_ids), 
                                   hillslopes_block=block,
                                   sim_years=sim_years)
            
    fn = _join(runs_dir, 'pw0.run')
    with open(fn, 'w') as fp:
        fp.write(s)
        
    
def run_watershed(runs_dir):
    t0 = time()

    cmd = [os.path.abspath(_wepp)]

    assert _exists(_join(runs_dir, 'pw0.str'))
    assert _exists(_join(runs_dir, 'pw0.chn'))
    assert _exists(_join(runs_dir, 'pw0.imp'))
    assert _exists(_join(runs_dir, 'pw0.man'))
    assert _exists(_join(runs_dir, 'pw0.slp'))
    assert _exists(_join(runs_dir, 'pw0.cli'))
    assert _exists(_join(runs_dir, 'pw0.sol'))
    assert _exists(_join(runs_dir, 'pw0.run'))

    _run = open(_join(runs_dir, 'pw0.run'))
    _log = open(_join(runs_dir, 'pw0.err'), 'w')

    p = subprocess.Popen(cmd, stdin=_run, stdout=_log, stderr=_log, cwd=runs_dir)
    p.wait()
    _run.close()
    _log.close()
    
    log_fn = _join(runs_dir, 'pw0.err')

    if _exists(_join(runs_dir, '../output/pass_pw0.txt')) and \
       _exists(_join(runs_dir, '../output/loss_pw0.txt')) and \
       _exists(_join(runs_dir, '../output/chnwb.txt')) and \
       _exists(_join(runs_dir, '../output/soil_pw0.txt')) and \
       _exists(_join(runs_dir, '../output/plot_pw0.txt')) and \
       _exists(_join(runs_dir, '../output/ebe_pw0.txt')) and \
       _exists(_join(runs_dir, '../output/pass_pw0.txt')):
        return True, time() - t0

    raise Exception('Error running wepp for watershed \nSee <a href="../browse/wepp/runs/pw0.err">%s</a>' % log_fn)
