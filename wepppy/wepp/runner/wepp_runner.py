import os
from os.path import join as _join
from os.path import exists as _exists

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
    
    
def watershed_template_loader():
    return _template_loader("watershed.template")
    
    
def hillstub_template_loader():
    return """
M
Y
../output/H{wepp_id}.pass.dat"""
    
    
def make_hillslope_run(wepp_id, sim_years, runs_dir):
    _hill_template = hill_template_loader()
    
    s = _hill_template.format(wepp_id=wepp_id, 
                              sim_years=sim_years)
            
    fn = _join(runs_dir, 'p%s.run' % wepp_id)
    with open(fn, 'w') as fp:
        fp.write(s)


def run_hillslope(wepp_id, runs_dir):
    # remember current directory
    curdir = os.getcwd()
    
    # change to working directory
    os.chdir(runs_dir)

    # noinspection PyBroadException
    try:
        cmd = [os.path.abspath(_wepp)]
            
        assert _exists('p%i.man' % wepp_id)
        assert _exists('p%i.slp' % wepp_id)
        assert _exists('p%i.cli' % wepp_id)
        assert _exists('p%i.sol' % wepp_id)
            
        _run = open('p%i.run' % wepp_id)
        _log = open('p%i.err' % wepp_id, 'w')
        
        p = subprocess.Popen(cmd, stdin=_run, stdout=_log, stderr=_log)
        p.wait()
        _run.close()
        _log.close()
        
        os.chdir(curdir)
    except Exception:
        os.chdir(curdir)
        raise
        
    log_fn = _join(runs_dir, 'p%i.err' % wepp_id)
    with open(log_fn) as fp:
        lines = fp.readlines()
        for L in lines:
            if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in L:
                return True
                    
    raise Exception('Error running wepp for wepp_id %i\nSee %s'
                    % (wepp_id, log_fn))


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
    # remember current directory
    curdir = os.getcwd()
    
    # change to working directory
    os.chdir(runs_dir)

    # noinspection PyBroadException
    try:
        cmd = [os.path.abspath(_wepp)]
        
        assert _exists('pw0.str')
        assert _exists('pw0.chn')
        assert _exists('pw0.imp')
        assert _exists('pw0.man')
        assert _exists('pw0.slp')
        assert _exists('pw0.cli')
        assert _exists('pw0.sol')
        assert _exists('pw0.run')
            
        _run = open('pw0.run')
        _log = open('pw0.err', 'w')
        
        p = subprocess.Popen(cmd, stdin=_run, stdout=_log, stderr=_log)
        p.wait()
        _run.close()
        _log.close()
        
        os.chdir(curdir)
    except Exception:
        os.chdir(curdir)
        raise
    
    log_fn = _join(runs_dir, 'pw0.err')
    
    with open(log_fn) as fp:
        lines = fp.readlines()
        for L in lines:
            if 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in L:
                return True
                    
    raise Exception('Error running wepp for watershed \nSee %s' % log_fn)