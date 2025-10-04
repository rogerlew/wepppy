import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import numpy as np
import pandas as pd

from subprocess import Popen, PIPE

from.flowpath import PeridotFlowpath, PeridotHillslope, PeridotChannel


_thisdir = os.path.dirname(__file__)


def _get_bin():
    _bin = _join(_thisdir, 'bin', 'abstract_watershed')
    
    if not _exists(_bin):
        raise RuntimeError('abstract_watershed binary not found')
    return _bin

def _get_wbt_bin():
    _bin = _join(_thisdir, 'bin', 'wbt_abstract_watershed')

    if not _exists(_bin):
        raise RuntimeError('wbt_abstract_watershed binary not found')
    return _bin

def _get_wbt_sub_field_bin():
    _bin = _join(_thisdir, 'bin', 'sub_fields_abstraction')

    if not _exists(_bin):
        raise RuntimeError('sub_fields_abstraction binary not found')
    return _bin

def run_peridot_abstract_watershed(
    wd: str,
    clip_hillslopes: bool = True,
    clip_hillslope_length: float = 300.0,
    bieger2015_widths: bool = False,
    verbose: bool = True
):
    assert _exists(_join(wd, 'dem/topaz/SUBWTA.ARC'))

    cmd = [_get_bin(), wd, '--ncpu', '24']

    if clip_hillslopes:
        assert clip_hillslope_length > 0.0
        cmd += ['--clip-hillslopes', '--clip-hillslope-length', str(clip_hillslope_length)]

    if bieger2015_widths:
        cmd += ['--bieger2015-widths']

    if verbose:
        print(' '.join(cmd))

    _log = open(_join(wd, '_peridot.log'), 'w')
    p = Popen(cmd, stdout=_log, stderr=_log)
    p.wait()

def run_peridot_wbt_abstract_watershed(
    wd: str,
    clip_hillslopes: bool = True,
    clip_hillslope_length: float = 300.0,
    bieger2015_widths: bool = False,
    verbose: bool = True
):
    """
    Run the Peridot abstract watershed tool using WhiteboxTools.
    
    Parameters:
        wd (str): Working directory where the Topaz data is located.
        clip_hillslopes (bool): Whether to clip hillslopes.
        clip_hillslope_length (float): Length to clip hillslopes.
        bieger2015_widths (bool): Whether to use Bieger 2015 widths.
        verbose (bool): If True, print command details.
    """
    assert _exists(_join(wd, 'dem/wbt/subwta.tif'))

    cmd = [_get_wbt_bin(), wd, '--ncpu', '24']

    if clip_hillslopes:
        assert clip_hillslope_length > 0.0
        cmd += ['--clip-hillslopes', '--clip-hillslope-length', str(clip_hillslope_length)]

    if bieger2015_widths:
        cmd += ['--bieger2015-widths']

    if verbose:
        print(' '.join(cmd))

    _log = open(_join(wd, '_peridot.log'), 'w')
    p = Popen(cmd, stdout=_log, stderr=_log)
    p.wait()


def post_abstract_watershed(wd: str, verbose: bool = True):
    """
    Post-process the output of the Peridot abstract watershed tool.

    calculate and return ws_cenroid and ws_area
    """

    from wepppy.topo.watershed_abstraction import WeppTopTranslator

    hill_df = pd.read_csv(_join(wd, 'watershed/hillslopes.csv'))
    sub_ids = sorted([int(x) for x in hill_df['topaz_id']])

    chn_df = pd.read_csv(_join(wd, 'watershed/channels.csv'))
    chn_ids = sorted([int(x) for x in  chn_df['topaz_id']])

    translator = WeppTopTranslator(sub_ids, chn_ids)
    get_wepp_id = lambda topaz_id: translator.wepp(topaz_id)
    get_chn_enum = lambda topaz_id: translator.chn_enum(top=topaz_id)
    
    hill_df['topaz_id'] = hill_df['topaz_id'].astype(str)
    hill_df['wepp_id'] = hill_df['topaz_id'].apply(get_wepp_id)

    hill_df['TopazID'] = hill_df['topaz_id'].astype(np.int64)
    hill_df.to_parquet(_join(wd, 'watershed/hillslopes.parquet'), index=False)
    sub_area = float(hill_df['area'].sum())
    lngs = hill_df['centroid_lon'].to_numpy()
    lats = hill_df['centroid_lat'].to_numpy()

    chn_df['topaz_id'] = chn_df['topaz_id'].astype(str)
    chn_df['wepp_id'] = chn_df['topaz_id'].apply(get_wepp_id)
    chn_df['chn_enum'] = chn_df['topaz_id'].apply(get_chn_enum)

    chn_df['TopazID'] = chn_df['topaz_id'].astype(np.int64)
    chn_df.to_parquet(_join(wd, 'watershed/channels.parquet'), index=False)
    chn_area = float(chn_df['area'].sum())
    lngs = np.concatenate((lngs, chn_df['centroid_lon'].to_numpy()))
    lats = np.concatenate((lats, chn_df['centroid_lat'].to_numpy()))

    fps_df = pd.read_csv(_join(wd, 'watershed/flowpaths.csv'))
    fps_df['topaz_id'] = fps_df['topaz_id'].astype(str)
    fps_df['fp_id'] = fps_df['fp_id'].astype(str)
    fps_df.to_parquet(_join(wd, 'watershed/flowpaths.parquet'), index=False)

    os.remove(_join(wd, 'watershed/hillslopes.csv'))
    os.remove(_join(wd, 'watershed/channels.csv')) 
    os.remove(_join(wd, 'watershed/flowpaths.csv'))

    ws_centroid = float(np.mean(lngs)), float(np.mean(lats))
    return sub_area, chn_area, ws_centroid, sub_ids, chn_ids


def read_network(fname):
    with open(fname) as fp:
        lines = fp.readlines()

    network = {}
    for L in lines:
        k, vals = L.split('|')
        network[int(k)] = [int(v) for v in vals.split(',')]

    return network

def run_peridot_wbt_sub_fields_abstraction(
    wd: str,
    clip_hillslopes: bool = True,
    clip_hillslope_length: float = 300.0,
    sub_field_min_area_threshold_m2: float = 0.0,
    verbose: bool = True
):
    """
    Run the Peridot abstract watershed tool using WhiteboxTools.

    Parameters:
        wd (str): Working directory where the Topaz data is located.
        clip_hillslopes (bool): Whether to clip hillslopes.
        clip_hillslope_length (float): Length to clip hillslopes.
        sub_field_min_area_threshold_m2 (float): Minimum area threshold for sub-fields.
        verbose (bool): If True, print command details.
    """
    assert _exists(_join(wd, 'dem/wbt/flovec.tif')), 'dem/wbt/flovec.tif not found'
    assert _exists(_join(wd, 'ag_fields/field_boundaries.tif')), 'ag_fields/field_boundaries.tif not found'

    cmd = [_get_wbt_sub_field_bin(), wd, '--ncpu', '24']

    if clip_hillslopes:
        assert clip_hillslope_length > 0.0
        cmd += ['--clip-hillslopes', '--clip-hillslope-length', str(clip_hillslope_length)]

    if sub_field_min_area_threshold_m2 > 0.0:
        cmd += ['--sub-field-min-area-threshold-m2', str(sub_field_min_area_threshold_m2)]

    if verbose:
        print(' '.join(cmd))

    _log = open(_join(wd, '_peridot.log'), 'w')
    p = Popen(cmd, stdout=_log, stderr=_log)
    p.wait()


def post_abstract_sub_fields(wd: str, verbose: bool = True):
    """
    Post-process the output of the Peridot abstract watershed tool.

    calculate and return ws_cenroid and ws_area
    """

    from wepppy.nodb.core import Watershed

    field_df = pd.read_csv(_join(wd, 'ag_fields/sub_fields/fields.csv'))

    translator = Watershed.getInstance(wd)
    get_wepp_id = lambda topaz_id: translator.wepp(topaz_id)
    field_df['topaz_id'] = field_df['topaz_id'].astype(str)
    field_df['wepp_id'] = field_df['topaz_id'].apply(get_wepp_id)
    field_df['TopazID'] = field_df['topaz_id'].astype(np.int64)
    field_df.to_parquet(_join(wd, 'ag_fields/sub_fields/fields.parquet'), index=False)

    fps_df = pd.read_csv(_join(wd, 'ag_fields/sub_fields/field_flowpaths.csv'))
    fps_df['topaz_id'] = fps_df['topaz_id'].astype(str)
    fps_df['fp_id'] = fps_df['fp_id'].astype(str)
    fps_df.to_parquet(_join(wd, 'ag_fields/sub_fields/field_flowpaths.parquet'), index=False)

    os.remove(_join(wd, 'ag_fields/sub_fields/field_flowpaths.csv'))
    os.remove(_join(wd, 'ag_fields/sub_fields/fields.csv'))

    return len(field_df), len(fps_df)
