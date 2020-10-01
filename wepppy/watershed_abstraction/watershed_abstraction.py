# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from typing import Tuple, List, Dict, Union
import os
from os.path import join as _join
from os.path import exists as _exists
import math
import json
from collections import Counter
from math import pi, atan2
import warnings

import numpy as np
from scipy.stats import circmean

from wepppy.all_your_base import (
    isfloat,
    read_arc,
    wgs84_proj4,
    centroid_px,
    GeoTransformer
)
from .wepp_top_translator import WeppTopTranslator

_thisdir = os.path.dirname(__file__)
_template_dir = _join(_thisdir, "templates")


def ischannel(topaz_id: int) -> bool:
    return str(topaz_id).endswith('4')


def garbrecht_length(distances: List[List[float]]) -> float:
    """
    calculates the length of a subcatchment from the flowpaths
    contained within the subcatchment. The length is weighted_flowpaths
    by the flowpaths length relative to its area.

    distances should be an array of distances between cells along the
    flowpath (not cumulative distance)

    eq. 3.4 in Thomas Cochrane's Dissertation
    # """
    x = np.array([np.sum(d) for d in distances])
    a = np.array([len(d) for d in distances], dtype=np.float64)
    return float(np.sum(x * a) / np.sum(a))


def cummnorm_distance(distance: List[float]) -> np.array:
    """
    builds and returns cumulative normalized distance array from an array
    of cell-to-cell distances
    """
    assert len(distance) > 0

    if len(distance) == 1:
        assert distance[0] > 0.0
        return np.array([0, 1])

    distance_p = np.cumsum(np.array(distance, np.float64))
    distance_p -= distance_p[0]
    distance_p /= distance_p[-1]
    return distance_p


def representative_normalized_elevations(x: List[float], dy: List[float]) -> List[float]:
    """
    x should be a normed distance array between 0 and 1
    dy is an array of slopes

    returns normalized elevations (relative to the length of x)
    """
    assert len(x) == len(dy), (x, dy)
    assert x[0] == 0.0
    assert x[-1] == 1.0

    # calculate the positions, assume top of hillslope is 0 y
    y = [0.0]
    for i in range(len(dy) - 1):
        step = x[i+1] - x[i]
        y.append(y[-1] - step * dy[i])

    return y


def read_geojson(fname):
    data = json.loads(open(fname).read())

    d = {}
    for feature in data['features']:
        top = feature['properties']['TopazID']
        d[top] = np.array(feature['geometry']['coordinates'][0])

    return d


def interpolate_slp(distances, slopes, max_points):
    _s = np.array(slopes)
    _d = np.array(distances)

    if _s.shape == (1,) and _d.shape == (2,):  # slope is a single cell
        _s = np.array([slopes[0], slopes[0]])

    assert _s.shape == _d.shape, str([_s.shape, _d.shape])

    for i in range(len(_d)-1):
        assert _d[i] < _d[i+1], distances

    assert _d[0] == 0.0
    assert _d[-1] == 1.0

    npts = len(_d)

    # interpolate if there are too many slope points
    if npts > max_points:
        _d2 = np.linspace(0.0, 1.0, max_points)
        _s2 = np.interp(_d2, _d, _s)
        _d, _s = _d2, _s2

    return _d, _s
    
    
def write_slp(aspect, width, cellsize, length, slope, distance_p, fp, version=97.3, max_points=19):
    """
    writes a slope file in the 97.3 format for WEPP
    """
    assert isfloat(aspect)
    assert isfloat(width)
    assert isfloat(length)
    assert isfloat(cellsize)

    _d, _s = distance_p, slope
    
    nofes = 1
    npts = len(_d)
    if npts > max_points:
        _d, _s = interpolate_slp(distance_p, slope, max_points)
        npts = len(_d)

    if version == 97.3:
        _slp = '97.3\n{nofes}\n{aspect} {width}\n{npts} {length}\n{defs} '
        defs = ' '.join(['%0.4f, %0.5f' % ds for ds in zip(_d, _s)])

        fp.write(_slp.format(nofes=nofes, aspect=aspect, width=width,
                             npts=npts, length=length, defs=defs))

    else:
        _slp = '{aspect} {cellsize}\n{npts} {length}\n{defs} \n'
        defs = ' '.join(['%0.4f %0.5f' % ds for ds in zip(_d, _s)])

        fp.write(_slp.format(nofes=nofes, aspect=aspect, cellsize=float(cellsize),
                             npts=npts, length=length, defs=defs))


def _identify_subflows(flowpaths: List[np.array]) -> List[List[int]]:
    """
    given an ndarray of flowpaths flowpath (n, 2) for a subcatchment
    identify which flowpaths travel over the same path down the
    hillslope. These are grouped into subflows of flowpath indices
    """
    # if there is only 1 flowpath then there are no subflows
    if len(flowpaths) == 1:
        return [[0]]

    # create a dictionary of px coord tuples so we can point back to the
    # index of the flowpaths list. This is aligned
    # with slopes and distance.
    fps_d = {}
    for k, fp in enumerate(flowpaths):
        fps_d[k] = list(set((fp[j, 0], fp[j, 1]) for j in range(fp.shape[0])))

    # here we create a list of tuples containing
    # the flow indices and the length of the flows
    # we want to iterate through the flows in
    # descending flow length
    lns = [(k, len(v)) for k, v in fps_d.items()]

    # build an empty list to populate subflows
    subflows = []

    # iterate over the flowpaths. If a subflow is identified as
    # a subflow then add it to the subflows index list
    # otherwise create a new subflow list
    for i, n in sorted(lns, key=lambda y: y[1], reverse=True):
        # unpack the set of pixel coords for the subflow
        fp0 = fps_d[i]

        # this gets set to 1 if fp0 is identified as a subflow
        issub = 0

        for j, fp1_indx_arr in enumerate(subflows):
            # because we are iterating in descending order the
            # first index of each subflow index list will
            # be the longest
            fp1 = fps_d[fp1_indx_arr[0]]

            # is fp0 a subset of fp1
            if fp0 <= fp1:
                subflows[j].append(i)
                issub = 1
                break

        # fp0 is not a subset so create a new subflow list
        if not issub:
            subflows.append([i])

    return subflows


def _weighted_slope_average(flowpaths, slopes, distances, max_points=19):
    """
    calculates weighted slopes based on the flowpaths contained on the hillslope
    """
    # determine longest flowpath
    lengths = [float(np.sum(d)) for d in distances]
    i = int(np.argmax(lengths))
    longest = float(lengths[i])

    # determine number of points to define slope
    num_points = len(distances[i])
    if num_points > max_points:
        num_points = max_points

    if num_points == 1:
        slope = float(slopes[i])
        return [slope, slope], [0.0, 1.0]

    # for each flowpath determine the distance from channel
    # this requires reversing the elements in the distance
    # array and calculating the cumulative sum
    rev_cum_distances = [np.cumsum(d[::-1]) for d in distances]

    # if we did this right, then the distance should equally the longest
    # length
    assert round(longest, 5) == round(rev_cum_distances[i][-1], 5)

    # determine weights for each flowpath
    areas = [f.shape[0] for f in flowpaths]
    kps = np.array([L * a for L, a in zip(lengths, areas)])

    # build an array with equally spaced points to interpolate on
    distance_p = np.linspace(0, longest, num_points)

    # this will hold the weighted slope estimates
    eps = []

    # we will weight the slope at each distance away from the channel
    for d_p in distance_p:
        num = 0  # to hold numerator value
        kpsum = 0  # to hold k_p sum

        for slp, rcd, kp in zip(slopes, rev_cum_distances, kps):
            # reverse slopes
            slp = slp[::-1]

            # we only want to interpolate where the slope is defined
            if d_p - 1e-6 > rcd[-1]:
                continue

            slp_p = np.interp(d_p, rcd, slp)
            num += slp_p * kp
            kpsum += kp

        # store the weighted slope estimate
        eps.append(num / kpsum)

    # normalize distance_p array
    distance_p /= longest

    # reverse weighted slopes and return
    w_slopes = np.array(eps[::-1])

    return w_slopes.flatten().tolist(), distance_p.tolist()


def compute_direction(head: List, tail: List) -> float:
    a = atan2(tail[1] - head[1],
              head[0] - tail[0]) * (180.0 / pi) - 180.0

    if a < 0:
        return a + 360.0

    return a


slope_template = """\
{aspect} {profile_width}
{num_points} {length}
{profile}"""


colordict = {
  0:     "#787878",
  "n":  ["#9afb0c", "#9ddd5e", "#9fc085"],
  "ne": ["#00ad43", "#3dab71", "#72a890"],
  "e":  ["#0068c0", "#5078b6", "#7c8ead"],
  "se": ["#6c00a3", "#77479d", "#8c75a0"],
  "s":  ["#ca009c", "#c04d9c", "#b47ba1"],
  "sw": ["#ff5568", "#e76f7a", "#cb8b8f"],
  "w":  ["#ffab47", "#e2a66c", "#c5a58a"],
  "nw": ["#f4fa00", "#d6db5e", "#bdbf89"]
}

c_slope_breaks = [0.05, 0.15, 0.30]


def slp_asp_color(slope: float, aspect: float) -> str:
    aspect %= 360.0

    i = 0
    for j, brk in enumerate(c_slope_breaks):
        if slope > brk:
            i = j + 1

    if i == 0:
        return colordict[0]

    cat_asp = "n"
    if 22.5 < aspect < 67.5:
        cat_asp = "ne"
    elif aspect < 112.5:
        cat_asp = "e"
    elif aspect < 157.5:
        cat_asp = "se"
    elif aspect < 202.5:
        cat_asp = "s"
    elif aspect < 247.5:
        cat_asp = "sw"
    elif aspect < 292.5:
        cat_asp = "w"
    elif aspect < 337.5:
        cat_asp = "nw"

    return colordict[cat_asp][i-1]


class ChannelRoutingError(Exception):
    """
    THE NETWORK STRUCTURE DELINEATED BY TOPAZ CONTAINS MORE THAN 3 CHANNELS
    AS INPUT TO A SINGLE CHANNEL. WEPP CAN ONLY HANDLE 3 OR LESS CHANNELS
    DRAINING INTO A SINGLE CHANNEL.

    THE CHANNELS SHOULD BE REDELINEATED AFTER ADJUSTING THE MINIMUM CHANNEL
    LENGTH (MCL) AND/OR CRITICAL SOURCE AREA (CSA)
    """

    __name__ = 'ChannelRoutingError'

    def __init__(self):
        pass


class CentroidSummary(object):
    def __init__(self, **kwds):
        self.px = tuple(int(v) for v in kwds['px'])
        self.lnglat = tuple(float(v) for v in kwds['lnglat'])


class SummaryBase(object):
    def __init__(self, **kwds):
        topaz_id = kwds['topaz_id']
        if topaz_id is not None:
            topaz_id = int(topaz_id)
        self.topaz_id = topaz_id
        
        wepp_id = kwds['wepp_id']
        if wepp_id is not None:
            wepp_id = int(wepp_id)
        self.wepp_id = wepp_id

        self.length = float(kwds['length'])
        self.width = float(kwds['width'])
        self.area = float(kwds['area'])
        self.aspect = float(kwds['aspect'])
        self.direction = float(kwds['direction'])
        self.slope_scalar = float(kwds['slope_scalar'])
        self.color = str(kwds['color'])
        self.centroid = kwds['centroid']
        self.distance_p = tuple(kwds['distance_p'])
        
        self._max_points = 19

        self.w_slopes = None
        self.slopes = None

    @property    
    def num_points(self) -> int:
        npts = len(self.distance_p)
        max_points = self.max_points
        return (npts, max_points)[npts > max_points]
        
    @property
    def max_points(self) -> int:
        return self._max_points
        
    @property
    def profile(self) -> str:
        max_points = self.max_points
        distance_p = self.distance_p

        try:
            slopes = self.w_slopes
            if slopes is None:
                slopes = self.slopes
        except AttributeError:
            slopes = self.slopes

        _d, _s = distance_p, slopes

        npts = len(_d)
        if npts > max_points:
            _d, _s = interpolate_slp(_d, _s, max_points)

        return ' '.join(["%0.6f, %0.3f" % (d, s) for d, s in zip(_d, _s)])
        
    def as_dict(self):
        d = dict(
            fname=self.fname,
            topaz_id=self.topaz_id,
            wepp_id=self.wepp_id,
            length=self.length,
            width=self.width,
            area=self.area,
            aspect=self.aspect,
            direction=self.direction,
            slope_scalar=self.slope_scalar,
            color=self.color,
            centroid=self.centroid.lnglat
        )

        try:
            d['order'] = self.order
            d['channel_type'] = self.channel_type
            d['cell_width'] = self.cell_width
        except:
            pass

        try:
            d['slopes'] = self.slopes
            d['coords'] = self.coords
        except:
            pass

        return d


class HillSummary(SummaryBase):
    def __init__(self, **kwds):
        super(HillSummary, self).__init__(**kwds)
        self.w_slopes = tuple(kwds['w_slopes'])
        self.pourpoint = tuple(kwds['pourpoint'])
        
    @property
    def fname(self) -> str:
        return 'hill_%i.slp' % self.topaz_id

    @property
    def pourpoint_coord(self):
        return str(tuple([int(v) for v in self.pourpoint])).replace(' ', '')


class ChannelSummary(SummaryBase):
    def __init__(self, **kwds):
        super(ChannelSummary, self).__init__(**kwds)
        self.slopes = tuple(kwds['slopes'])
        self._order = kwds.get('order', None)
        self.isoutlet = kwds['isoutlet']
        self.head = kwds['head']
        self.tail = kwds['tail']
        self.chn_enum = int(kwds['chn_enum'])
        self._chn_type = kwds['chn_type']

    @property
    def head_coord(self):
        return str(tuple([int(v) for v in self.head])).replace(' ', '')

    @property
    def tail_coord(self):
        return str(tuple([int(v) for v in self.tail])).replace(' ', '')

    @property
    def fname(self) -> str:
        return 'chn_%i.slp' % self.topaz_id
          
    @property
    def order(self) -> int:
        return self._order
        
    @order.setter
    def order(self, value):
        self._order = int(value) 
        
    @property
    def channel_type(self) -> str:
        return getattr(self, '_chn_type', 'Default')

        # return 'Default'
        # return ('OnEarth 1', 'OnGravel 1', 'OnRock 2')[int([None, 0, 0, 1, 1, 1, 2, 2][self.order])]

    @channel_type.setter
    def channel_type(self, value):
        self._chn_type = value

    @property
    def cell_width(self) -> int:
        return [None, 1, 2, 2, 3, 3, 3, 4, 4][self.order]


class FlowpathSummary(SummaryBase):
    def __init__(self, **kwds):
        super(FlowpathSummary, self).__init__(**kwds)
        self.slopes = tuple(kwds['slopes'])
        self.coords = kwds['coords']
    
    @property
    def fname(self) -> str:
        return 'flow_%i.slp' % self.topaz_id
                    
                    
class WatershedAbstraction:
    def __init__(self, wd, wat_dir):
        if not _exists(wd):
            raise Exception('Specified working directory does not exist')

        if not _exists(wat_dir):
            raise Exception('Specified wat_dir does not exist')

        self.wd = wd
        self.wat_dir = wat_dir

        # lookup table for the flowpath directions specified in flovec
        #
        # 1     2     3
        #   \   |   /
        #     \ | /
        # 4 <-- o --> 6
        #     / | \
        #   /   |   \
        # 7     8     9
        #
        # the origin for the maps is the top right corner
        # we read in the maps with gdal and transpose so the
        # data is in row major order. This is less consistent
        # with maps but more consistent with numpy
        sqrt2 = 2.0**0.5
        self.paths = {1: ([-1, -1], sqrt2),
                      2: ([0,  -1], 1),
                      3: ([1,  -1], sqrt2),
                      4: ([-1,  0], 1),
                      6: ([0,   1], 1),
                      7: ([-1,  1], sqrt2),
                      8: ([0,   1], 1),
                      9: ([1,   1], 1)}

        # initialize datastructure containing json representation
        # of the abstracted watershed
        self.watershed = dict(hillslopes={}, channels={}, flowpaths={})
        self.hillslope_n = 0
        self.channel_n = 0
        self.impoundment_n = 0
        self._structure = None
        self._linkdata = None
        self._network = None

        bound_fn = _join(wd, 'BOUND.ARC')
        flopat_fn = _join(wd, 'FLOPAT.ARC')
        flovec_fn = _join(wd, 'FLOVEC.ARC')
        fvslop_fn = _join(wd, 'FVSLOP.ARC')
        subwta_fn = _join(wd, 'SUBWTA.ARC')
        relief_fn = _join(wd, 'RELIEF.ARC')
        taspec_fn = _join(wd, 'TASPEC.ARC')
        dnmcnt_inp = _join(wd, 'DNMCNT.INP')

        if not _exists(bound_fn) or \
           not _exists(flopat_fn) or \
           not _exists(flovec_fn) or \
           not _exists(fvslop_fn) or \
           not _exists(subwta_fn) or \
           not _exists(relief_fn) or \
           not _exists(taspec_fn):
            raise Exception('Missing required input file')

        bound, _transform, _proj = read_arc(bound_fn, dtype=np.uint8)
        flopat, _transform, _proj = read_arc(flopat_fn, dtype=np.uint8)
        flovec, _transform, _proj = read_arc(flovec_fn, dtype=np.uint8)
        fvslop, _transform, _proj = read_arc(fvslop_fn, dtype=np.float64)
        subwta, _transform, _proj = read_arc(subwta_fn, dtype=np.int64)
        relief, _transform, _proj = read_arc(relief_fn, dtype=np.float64)
        taspec, _transform, _proj = read_arc(taspec_fn, dtype=np.float64)

        # make sure the datasets are aligned
        assert flopat.shape == flovec.shape
        assert flopat.shape == fvslop.shape
        assert flopat.shape == subwta.shape
        assert flopat.shape == relief.shape
        assert flopat.shape == taspec.shape

        # clamp slope values at 0.001 to prevent internal
        # errors in wepp
        fvslop[np.where(fvslop < 0.001)] = 0.001

        # pull cellsize from transform
        self.transform = _transform
        self.cellsize = _transform[1]
        self.cellsize2 = self.cellsize * self.cellsize
        self.totalarea = float(np.sum(bound)) * self.cellsize2

        # store in class
        self.flopat = flopat
        self.flovec = flovec
        self.fvslop = fvslop
        self.subwta = subwta
        self.relief = relief
        self.taspec = taspec

        # find outlet
        outlet = self._read_outlet(dnmcnt_inp)
        outlet_top_id = subwta[outlet[0], outlet[1]]
        assert str(outlet_top_id).endswith('4'), outlet_top_id

        self.watershed['outlet'] = outlet
        self.outlet_top_id = outlet_top_id
        self.watershed['srs'] = dict(transform=_transform,
                                     projection=_proj)

        self.utmProj = _proj
        self.proj2wgs_transformer = GeoTransformer(src_proj4=self.utmProj, dst_proj4=wgs84_proj4)

        # find the centroid_px for the watershed
        indx, indy = np.where(bound == 1)
        _centroid_px = centroid_px(indx, indy)
        centroid_lnglat = self.px_to_lnglat(*_centroid_px)

        self._centroid = CentroidSummary(px=_centroid_px,
                                         lnglat=centroid_lnglat)

        top_ids = list(set(subwta.flatten().tolist()))
        top_ids.remove(0)
        top_sub_ids = [v for v in top_ids if str(v)[-1] in '123']
        top_chn_ids = [v for v in top_ids if str(v).endswith('4')]

        self.translator = WeppTopTranslator(top_sub_ids, top_chn_ids)

    @property
    def structure(self) -> List[List[int]]:
        return self._structure

    @property
    def linkdata(self) -> Dict[int, Dict[str, List[Union[int, float]]]]:
        return self._linkdata

    @property
    def network(self) -> Dict[int, List[int]]:
        return self._network

    @property
    def centroid(self) -> CentroidSummary:
        return self._centroid

    def abstract(self, wepp_chn_type='Default', verbose=False, warn=False):
        self.abstract_channels(wepp_chn_type=wepp_chn_type, verbose=verbose)
        self.abstract_subcatchments(verbose=verbose, warn=warn)
        self.abstract_structure(verbose=verbose)

    def write_slps(self, channels=1, subcatchments=1, flowpaths=1, cell_width=None):
        """
        Writes slope files to the specified wat_dir. The channels,
        subcatchments, and flowpaths args specify what slope files
        should be written.
        """
        out_dir = self.wat_dir
        if channels:
            self._make_channel_slps(out_dir, cell_width=cell_width)

        if subcatchments:
            self._write_subcatchment_slps(out_dir)

        if flowpaths:
            self._write_flowpath_slps(out_dir)

    def _make_channel_slps(self, out_dir, cell_width=None):
        ws = self.watershed
        translator = self.translator

        chn_enums = ws["channels"].keys()
        chn_enums = sorted([translator.chn_enum(chn_id=v) for v in chn_enums])

        # watershed run requires a slope file defining all of the channels in the
        # 99.1 format. Here we write a combined channel slope file and a slope
        # file for each individual channel
        fp2 = open(_join(out_dir, 'channels.slp'), 'w')
        fp2.write('99.1\n')
        fp2.write('%i\n' % len(chn_enums))

        for chn_enum in chn_enums:
            top = translator.top(chn_enum=chn_enum)
            chn_id = 'chn_%i' % top
            d = ws['channels'][chn_id]

            if cell_width is None:
                _cell_width = d.cell_width
            else:
                _cell_width = cell_width

            slp_fn = _join(out_dir, '%s.slp' % chn_id)
            fp = open(slp_fn, 'w')
            write_slp(d.aspect, d.width, _cell_width, d.length,
                      d.slopes, d.distance_p, fp, 97.3)
            fp.close()

            write_slp(d.aspect, d.width, _cell_width, d.length,
                      d.slopes, d.distance_p, fp2, 99.1)

        fp2.close()

    def _write_subcatchment_slps(self, out_dir):
        ws = self.watershed
        cellsize = self.cellsize

        for sub_id, d in ws['hillslopes'].items():
            slp_fn = _join(out_dir, '%s.slp' % sub_id)
            fp = open(slp_fn, 'w')
            write_slp(d.aspect, d.width, cellsize, d.length,
                      d.w_slopes, d.distance_p, fp, 97.3)
            fp.close()

    def _write_flowpath_slps(self, out_dir):
        ws = self.watershed
        cellsize = self.cellsize

        for sub_id in ws['hillslopes']:
            for fp_id, d in ws['flowpaths'][sub_id].items():
                fp = open(_join(out_dir, fp_id + '.slp'), 'w')
                write_slp(d.aspect, d.width, cellsize, d.length,
                          d.slopes, d.distance_p, fp, 97.3)
                fp.close()

    def px_to_utm(self, x: int, y: int) -> Tuple[float, float]:
        _transform = self.transform
        e = _transform[0] + _transform[1] * x
        n = _transform[3] + _transform[5] * y
        return e, n

    def px_to_lnglat(self, x: int, y: int) -> Tuple[float, float]:
        proj2wgs_transformer = self.proj2wgs_transformer

        e, n = self.px_to_utm(x, y)
        lng, lat = proj2wgs_transformer.transform(e, n)
        assert not np.isinf(lng), (self.transform, x, y, e, n)
        assert not np.isinf(lat)
        return lng, lat

    def _read_netw_tab(self):
        translator = self.translator

        keys = "chnum order row col row1 col1 outr outc chnlen elevvup "\
               "elevdn areaup areadn1 areadn dda node1 node2 node3 node4 "\
               "node5 node6 node7 slopedirect slopesmoothed".split()

        types = [int, int, int, int, int, int, int, int,
                 float, float, float, float, float, float,
                 float, int, int, int, int, int, int, int,
                 float, float]

        wd = self.wd
        subwta = self.subwta

        netw_tab = _join(wd, "NETW.TAB")

        with open(netw_tab) as fid:
            lines = fid.readlines()

        last = [i for i, v in enumerate(lines) if v.strip().startswith("-1")][0]
        lines = lines[27:last]
        lines = [[_t(v) for _t, v in zip(types, l.split())] for l in lines]
        assert all([len(l) == 24 for l in lines])
        data = {l[0]: dict(zip(keys, l)) for l in lines}
        # -> Dict[int, Dict[str, List[Union[int, float]]]]
        network = {}

        for topaz_id in self.watershed["channels"]:
            self.watershed["channels"][topaz_id].order = 1

        for chnum in data:
            head = data[chnum]["col"]-1, data[chnum]["row"]-1
            center = data[chnum]["col1"]-1, data[chnum]["row1"]-1
            tail = data[chnum]["outc"]-1, data[chnum]["outr"]-1

            chn_id0 = subwta[head]
            chn_id1 = subwta[center]
            chnout_id = subwta[tail]

            assert chn_id0 != 0, chn_id0
            assert chn_id1 != 0, chn_id1
            assert chnout_id != 0, chnout_id
            assert chn_id0 == chn_id1
            assert str(chn_id0).endswith("4"), chn_id0
            assert str(chnout_id).endswith("4"), chnout_id
            assert chn_id0 >= chnout_id, "%i %i" % (chnout_id, chn_id0)

            data[chnum]["chn_id"] = chn_id0
            data[chnum]["chnout_id"] = chnout_id

            # node_indexes = [data[chnum]["node%i" % i] for i in range(1, 8)]
            # node_indexes = [indx for indx in node_indexes if indx != 0]
            self.watershed["channels"]["chn_{}".format(chnout_id)].order = int(data[chnum]["order"])

            # Old broken order assignment
            # for chn_enum in node_indexes:
            #     if chn_enum > translator.channel_n:
            #         continue
            #
            #    chn_id = "chn_%i" % translator.top(chn_enum=chn_enum)
            #     if chn_id not in self.watershed["channels"]:
            #       self.watershed["channels"][chn_id] = {}
            #
            #    order = data[chnum]["order"]
            #    self.watershed["channels"][chn_id].order = order
            #    # self.watershed["channels"][chn_id].width = self.cellsize / order

            if chnout_id == chn_id0:
                continue

            if chnout_id not in network:
                network[chnout_id] = [chn_id0]
            else:
                network[chnout_id].append(chn_id0)

        if not all([len(L) <= 3 for L in network.values()]):
            raise ChannelRoutingError()

        self._linkdata = data
        self._network = network

    def _read_outlet(self, dnmcnt_inp) -> Tuple[int, int]:
        subwta = self.subwta

        with open(dnmcnt_inp) as fid:
            lines = fid.readlines()

            row = int(lines[98])-1
            col = int(lines[107])-1

            if not str(subwta[col, row]).endswith('4'):
                raise Exception('Identified outlet location is not a channel')

            return col, row

    def _determine_aspect(self, indx, indy) -> float:
        taspec = self.taspec
        rads = np.array(taspec[(indx, indy)]) * pi / 180.0
        return float(circmean(rads) * 180.0 / pi)

    def abstract_channels(self, wepp_chn_type='Default', verbose=False):
        subwta = self.subwta

        # extract the subcatchment and channel ids from the subwta map
        # subwta contains 0 values outside the watershed
        _ids = sorted(list(set(subwta.flatten())))

        # channels end in 4
        chn_ids = [i for i in _ids if str(i).endswith('4') and i > 0]

        n = len(chn_ids)
        if n == 0:
            raise Exception('SUBWTA contains no channels')

        for i, chn_id in enumerate(chn_ids):
            if verbose:
                print('abstracting channel %s (%i of %i)...' % (chn_id, i+1, n))
            self.abstract_channel(chn_id, wepp_chn_type=wepp_chn_type)

        self.channel_n = len(chn_ids)

    def _walk_channel(self, chn_id: int) -> \
            Tuple[np.array, np.array, np.array, np.array, np.array]:
        """
        for a channel specified by chn_id identifies
        the flowpath of the channel from top to bottom,
        the slope along the flowpath and the distance
        between points in the flowpath
        """
        subwta = self.subwta
        relief = self.relief
        flovec = self.flovec
        fvslop = self.fvslop
        paths = self.paths

        # use the subwta map to identify the coordinates the channel
        indx, indy = np.where(subwta == chn_id)

        # Relief contains the elevation values of the terrain.
        # this creates a list of tuples containing indices and elevations
        # the indices are aligned to the indx and indy arrays and are sorted
        # in descending order by elevation. We can't walk down the flovec map
        # because the length of the channel gets exaggerated due to the path
        # wandering in and out of the channel.
        indices = sorted([t for t in enumerate(relief[indx, indy])],
                         key=lambda tup: tup[1], reverse=True)

        # build the flowpath
        flowpath = [[indx[t[0]], indy[t[0]]] for t in indices]

        # follow flovec down hill an additional step to connect
        # to next channel
        c, r = flowpath[-1]
        vec = flovec[c, r]
        (x, y), dis = paths[vec]
        c += x
        r += y
        flowpath.append([c, r])
        flowpath = np.array(flowpath)

        # calculate slope and distance
        slope = np.array([fvslop[indx[t[0]], indy[t[0]]] for t in indices])
        _distance = flowpath[:-1, :] - flowpath[1:, :]
        distance = np.sqrt(np.power(_distance[:, 0], 2.0) +
                           np.power(_distance[:, 1], 2.0))

        assert distance.shape == slope.shape

        # return to _abstract_channel
        return flowpath, slope, distance, indx, indy

    def abstract_channel(self, chn_id: int, wepp_chn_type='Default'):
        """
        define channel abstraction for the purposes of running WEPP
        """
        watershed = self.watershed
        translator = self.translator
        cellsize = self.cellsize

        flowpath, slope, distance, indx, indy = self._walk_channel(chn_id)

        # need normalized distance_p to define slope
        distance_p = cummnorm_distance(distance)
        if len(slope) == 1:
            slope = np.array([float(slope), float(slope)])

        # calculate the length from the distance array
        length = float(np.sum(distance) * cellsize)
        width = float(cellsize)
        aspect = float(self._determine_aspect(indx, indy))
        isoutlet = bool(chn_id == self.outlet_top_id)

        head = [v * cellsize for v in flowpath[-1]]
        head = [float(v) for v in head]
        tail = [v * cellsize for v in flowpath[0]]
        tail = [float(v) for v in tail]
        
        direction = compute_direction(head, tail)

        _centroid_px = centroid_px(indx, indy)
        centroid_lnglat = self.px_to_lnglat(*_centroid_px)

        elevs = representative_normalized_elevations(distance_p, slope)
        slope_scalar = float(abs(elevs[-1]))
        
        chn_summary = ChannelSummary(
            topaz_id=chn_id,
            wepp_id=translator.wepp(top=chn_id),
            chn_enum=translator.chn_enum(top=chn_id),
            chn_type=wepp_chn_type,
            isoutlet=isoutlet,
            length=length,
            width=width,
            aspect=aspect,
            head=head,
            tail=tail,
            direction=direction,
            elevs=elevs,
            slope_scalar=slope_scalar,
            color=slp_asp_color(slope_scalar, aspect),
            area=float(length) * float(width),
            distance_p=distance_p.tolist(),
            slopes=slope.tolist(),
            centroid=CentroidSummary(
                px=_centroid_px,
                lnglat=centroid_lnglat
            )
        )     
        
        # save channel abstraction to instance
        watershed['channels']['chn_%i' % chn_id] = chn_summary
        
    def abstract_subcatchments(self, verbose=False, warn=False):
        subwta = self.subwta

        # extract the subcatchment and channel ids from the subwta map
        # subwta contains 0 values outside the watershed
        _ids = sorted(list(set(subwta.flatten())))

        # subcatchments end in 1, 2, and 3, subcatchments that end in
        # are source subcatchments, 2 are left and 3 are right
        sub_ids = [i for i in _ids if not str(i).endswith('4') and i > 0]

        n = len(sub_ids)
        if n == 0:
            raise Exception('SUBWTA contains no channels')

        for i, sub_id in enumerate(sub_ids):
            if verbose:
                print('abstracting subtatchment %s (%i of %i)' % (sub_id, i+1, n))
            self.abstract_subcatchment(sub_id, verbose=verbose, warn=warn)

        self.hillslope_n = len(sub_ids)
        
    def _walk_flowpath(self, sub_id: int, c: int, r: int, warn=False) -> Tuple[np.array, np.array, np.array]:
        """
        walk down the gradient until we reach a channel
        to find the flowpath in pixel coords, the slope
        along the flowpath and the distance between the
        cells
        """
        subwta = self.subwta
        flopat = self.flopat
        flovec = self.flovec
        fvslop = self.fvslop
        paths = self.paths

        # we are providing the starting point of the flowpath
        flowpath = [(c, r)]
        distance = []

        n, m = subwta.shape

        # time to walk down the path
        i = 0
        while 1:
            vec = flovec[c, r]

            # break if we hit a depression, not sure what
            # happens if we hit this
            if vec == 5:
                break

            # x and y specify the direction we need to move
            (x, y), dis = paths[vec]
            c += x
            r += y

            # make sure we aren't in a loop
            if (c, r) in flowpath:
                if warn:
                    warnings.warn('Flowpath c=%i, r=%i for %i went in a circle' % (c, r, sub_id))
                break

            # store the new values
            flowpath.append((c, r))
            distance.append(dis)

            # determine whether we have reached the end of the flowpath
            _id = subwta[c, r]
            pat = flopat[c, r]
            if pat in [0, 1] or _id != sub_id:
                break

            i += 1

            if i > n + m:
                if warn:
                    warnings.warn('Flowpath c=%i, r=%i for %i is too long (>N)' % (c, r, sub_id))
                break

        # cast flowpath and distance as ndarrays
        flowpath = np.array(flowpath)
        distance = np.array(distance)
        
        # extract the slope values for the flowpath. We don't take the
        # last flowpath so it is aligned with the distance array
        slope = fvslop[(flowpath[:-1, 0], flowpath[:-1, 1])]

        # double check...
        assert distance.shape == slope.shape

        # return to _walk_flowpaths
        return flowpath, slope, distance

    def _walk_flowpaths(self, sub_id: int, verbose=False, warn=False) -> \
            Tuple[List[np.array], List[np.array], List[np.array], np.array, np.array]:
        """
        considers each cell of the subcatchment as a starting
        point for a flowpath. It walks down each flowpath to
        determine the slopes and distance for each.
        """
        subwta = self.subwta

        flowpaths = []
        slopes = []
        distances = []

        indx, indy = np.where(subwta == sub_id)

        n = len(indx)
        for i, (c, r) in enumerate(zip(indx, indy)):
            if verbose:
                print('walking flowpath %i of %i (%s)' % (i+1, n, sub_id))

            flowpath, slope, distance = self._walk_flowpath(sub_id, c, r, warn=warn)
            flowpaths.append(flowpath)
            slopes.append(slope)
            distances.append(distance)

        # return to abstract_subcatchment
        return flowpaths, slopes, distances, indx, indy

    def abstract_flowpath(self, flowpath, slope, distance) -> FlowpathSummary:
        cellsize = self.cellsize
        cellsize2 = self.cellsize2

        indx, indy = flowpath[:, 0], flowpath[:, 1]

        # we really only care about the longest flowpath
        # which is the first because of how we identify the
        # subflows
        distance_p = cummnorm_distance(distance)
        if len(slope) == 1:
            slope = np.array([float(slope), float(slope)])
        length = float(np.sum(distance) * cellsize)
        area = float(np.sum(distance) * cellsize2)
        width = float(area / length)
        aspect = float(self._determine_aspect(indx, indy))

        _centroid_px = centroid_px(indx, indy)
        centroid_lnglat = self.px_to_lnglat(*_centroid_px)

        head = [v * cellsize for v in [indx[-1], indy[-1]]]
        head = [float(v) for v in head]
        tail = [v * cellsize for v in [indx[0], indy[0]]]
        tail = [float(v) for v in tail]
        
        direction = compute_direction(head, tail)
        
        elevs = representative_normalized_elevations(distance_p, slope)
        slope_scalar = float(abs(elevs[-1]))
        color = slp_asp_color(slope_scalar, aspect)

        return FlowpathSummary(
            topaz_id=None,
            wepp_id=None,
            length=float(length),
            width=float(width),
            area=float(area),
            aspect=float(aspect),
            direction=float(direction),
            slope_scalar=slope_scalar,
            color=color,
            coords=[(int(x), int(y)) for (x, y) in zip(indx, indy)],
            distance_p=distance_p.tolist(),
            slopes=slope.tolist(),
            centroid=CentroidSummary(
                px=_centroid_px,
                lnglat=centroid_lnglat
            )
        )     
        
    def abstract_flowpaths(self, sub_id: int, flowpaths: List[np.array],
                           slopes: List[np.array], distances: List[np.array]) -> \
            Tuple[Dict[str, FlowpathSummary], List[List[int]]]:

        # returns a list of lists
        # each list contains indices corresponding to the flowpaths that
        # follow the same route. The index of the longest flowpath is
        # listed first
        subflows = _identify_subflows(flowpaths)

        # initialize a dictionary to hold the flowpath data
        fp_d = {}
        for j, fp_indxs in enumerate(subflows):
            # build the flowpath id
            # start at 1 to make sure wepp is happy
            fp_id = 'flow_%i_%i' % (sub_id, j+1)

            fp_d[fp_id] = self.abstract_flowpath(flowpaths[fp_indxs[0]],
                                                 slopes[fp_indxs[0]],
                                                 distances[fp_indxs[0]])

        return fp_d, subflows

    def abstract_subcatchment(self, sub_id, verbose=False, warn=False):
        """
        define subcatchment abstraction for the purposes of running WEPP
        """
        watershed = self.watershed
        translator = self.translator
        cellsize2 = self.cellsize2
        cellsize = self.cellsize

        # determine flowpaths
        # Tuple[List[np.array], List[np.array], List[np.array], np.array, np.array]
        flowpaths, slopes, distances, indx, indy = \
            self._walk_flowpaths(sub_id, verbose=verbose, warn=warn)

        # determine area, width, and length
        area = float(len(indx)) * cellsize2

        # find corresponding chn_id
        chn_id = 'chn_%i' % (int(math.floor(sub_id / 10.0) * 10) + 4)
        chn_summary = watershed["channels"][chn_id]
            
        # If subcatchment is a source type then we calculate the distance
        # by taking a weighted average based on the length of the flowpaths
        # contained in the subcatchment
        if str(sub_id).endswith('1'):
            length = cellsize * garbrecht_length(distances)
            width = area / length

        # Otherwise the  width of the subcatchment is determined by the
        # channel that the subcatchment drains into. The length is
        # then determined by the area / width
        else:
            width = chn_summary.length
            length = area / width
            
        direction = chn_summary.direction
        if str(sub_id).endswith('2'):
            direction += 90
        if str(sub_id).endswith('3'):
            direction -= 90

        # determine aspect
        aspect = self._determine_aspect(indx, indy)

        # calculate weighted slope from flowpaths
        w_slopes, distance_p = \
            _weighted_slope_average(flowpaths, slopes, distances)

        # abstract the flowpaths
        fp_d, subflows = \
            self.abstract_flowpaths(sub_id, flowpaths, slopes, distances)

        watershed['flowpaths']['hill_%i' % sub_id] = fp_d
        
        # cast lists of ndarrays to list of lists so we can dump to json
        flowpaths = [x.tolist() for x in flowpaths]
#        distances = [x.tolist() for x in distances]
#        slopes = [x.tolist() for x in slopes]

        # determine pourpoint from flowpaths
        pourpoint = Counter([tuple(fp[-1]) for fp in flowpaths]).most_common()[0][0]
        pourpoint = list([v * cellsize for v in pourpoint])

        _centroid_px = centroid_px(indx, indy)
        centroid_lnglat = self.px_to_lnglat(*_centroid_px)

        elevs = representative_normalized_elevations(distance_p, w_slopes)
        slope_scalar = float(abs(elevs[-1]))

        sub_summary = HillSummary(  
            topaz_id=sub_id,
            wepp_id=translator.wepp(top=sub_id),
            w_slopes=list(w_slopes),
            pourpoint=list(pourpoint),     
            length=float(length),
            width=float(width),
            area=float(area),
            aspect=float(aspect),
            direction=direction,
            slope_scalar=slope_scalar,
            color=slp_asp_color(slope_scalar, aspect),
            distance_p=list(distance_p),
            centroid=CentroidSummary(
                px=_centroid_px,
                lnglat=centroid_lnglat
            )
        )     
        watershed['hillslopes']['hill_%i' % sub_id] = sub_summary

    def abstract_structure(self, verbose=False):
        self._read_netw_tab()
        network = self.network
        translator = self.translator

        # now we are going to define the lines of the structure file
        # this doesn't handle impoundments

        structure = []
        for chn_id in translator.iter_chn_ids():
            if verbose:
                print('abstracting structure for channel %s...' % chn_id)
            top = translator.top(chn_id=chn_id)
            chn_enum = translator.chn_enum(chn_id=chn_id)

            # right subcatchments end in 2
            hright = top - 2
            if not translator.has_top(hright):
                hright = 0

            # left subcatchments end in 3
            hleft = top - 1
            if not translator.has_top(hleft):
                hleft = 0

            # center subcatchments end in 1
            hcenter = top - 3
            if not translator.has_top(hcenter):
                hcenter = 0

            # define structure for channel
            # the first item defines the channel
            _structure = [chn_enum]

            # network is defined from the NETW.TAB file that has
            # already been read into {network}
            # the 0s are appended to make sure it has a length of
            # at least 3
            chns = network.get(top, []) + [0, 0, 0]

            # structure line with top ids
            _structure += [hright, hleft, hcenter] + chns[:3]

            # this is where we would handle impoundments
            # for now no impoundments are assumed
            _structure += [0, 0, 0]

            # and translate topaz to wepp
            structure.append([int(v) for v in _structure])

        self._structure = structure


if __name__ == '__main__':
    watershed_a = WatershedAbstraction('/geodata/weppcloud_runs/419e3b7f-ae62-4bc1-af10-bba44266f494/dem/topaz',
                                       '/geodata/weppcloud_runs/419e3b7f-ae62-4bc1-af10-bba44266f494/watershed')
    watershed_a.abstract(verbose=False)
#    watershed_a.write_slps(channels=1, subcatchments=1, flowpaths=1)
#    js = watershed_a.json()

#    watershed_b = WatershedAbstraction()
#    watershed_b.load(js)
#    watershed_b.dumpjson('wb.json')
#    pprint(watershed_b.watershed["channels"])
