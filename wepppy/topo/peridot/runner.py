import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import pandas as pd

from subprocess import Popen, PIPE

from.flowpath import PeridotFlowpath, PeridotHillslope, PeridotChannel


_thisdir = os.path.dirname(__file__)
_bin = _join(_thisdir, 'bin', 'abstract_watershed')


def _get_bin():
    if not _exists(_bin):
        raise RuntimeError('abstract_watershed binary not found')
    return _bin


def run_peridot_abstract_watershed(wd: str, clip_hillslopes: bool = True, clip_hillslope_length: float = 300.0, verbose: bool = True):
    assert _exists(_join(wd, 'dem/topaz/SUBWTA.ARC'))

    cmd = [_get_bin(), wd, '--ncpu', '24']

    if clip_hillslopes:
        assert clip_hillslope_length > 0.0
        cmd += ['--clip-hillslopes', '--clip-hillslope-length', str(clip_hillslope_length)]

    if verbose:
        print(' '.join(cmd))

    _log = open(_join(wd, '_peridot.log'), 'w')
    p = Popen(cmd, stdout=_log, stderr=_log)
    p.wait()


def post_abstract_watershed(wd: str, verbose: bool = True):
    df = pd.read_csv(_join(wd, 'watershed/hillslopes.csv'))
    df['topaz_id'] = df['topaz_id'].astype(str)
    subs_summary = {rec['topaz_id']: PeridotHillslope.from_dict(rec) for rec in df.to_dict('records')}
    del df

    df = pd.read_csv(_join(wd, 'watershed/channels.csv'))
    df['topaz_id'] = df['topaz_id'].astype(str)
    chns_summary = {rec['topaz_id']: PeridotChannel.from_dict(rec) for rec in df.to_dict('records')}
    del df


#    df = pd.read_csv(_join(wd, 'watershed/flowpaths.csv'))
#    df['topaz_id'] = df['topaz_id'].astype(str)
#    df['fp_id'] = df['fp_id'].astype(str)
#
#    # Create the dictionary structure
#    fp_summary = {}
#    for rec in df.to_dict('records'):
#        topaz_id = rec['topaz_id']
#        fp_id = rec['fp_id']
#        fp = PeridotFlowpath.from_dict(rec)
#        if topaz_id not in fp_summary:
#            fp_summary[topaz_id] = {}
#        fp_summary[topaz_id][fp_id] = fp
#    del df

    return subs_summary, chns_summary, None #fp_summary


def read_network(fname):
    with open(fname) as fp:
        lines = fp.readlines()

    network = {}
    for L in lines:
        k, vals = L.split('|')
        network[int(k)] = [int(v) for v in vals.split(',')]

    return network
