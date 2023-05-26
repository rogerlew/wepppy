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

from numba import njit
import numpy as np
from scipy.stats import circmean

import multiprocessing

from wepppy.all_your_base import NCPU

from wepppy.all_your_base.geo import (
    read_arc,
    wgs84_proj4,
    centroid_px,
    GeoTransformer
)

from .support import (
    garbrecht_length,
    cummnorm_distance,
    representative_normalized_elevations,
    write_slp,
    identify_subflows,
    compute_direction,
    slp_asp_color,
    CentroidSummary,
    HillSummary,
    ChannelSummary,
    FlowpathSummary

)

from .wepp_top_translator import WeppTopTranslator

_thisdir = os.path.dirname(__file__)
_template_dir = _join(_thisdir, "templates")


def transform_px_to_wgs(args):
    utm_proj, indx, indy, transform, properties = args
    transformer = GeoTransformer(src_proj4=utm_proj, dst_proj4=wgs84_proj4)
    e = transform[0] + transform[1] * indx
    n = transform[3] + transform[5] * indy
    coordinates = transformer.transform(e, n)
    return properties, coordinates


@njit
def _walk_flowpath(subwta, flopat, flovec, fvslop, sub_id: int, c: int, r: int, warn=False) -> Tuple[np.array, np.array, np.array]:
    """
    walk down the gradient until we reach a channel
    to find the flowpath in pixel coords, the slope
    along the flowpath and the distance between the
    cells
    """
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
    sqrt2 = 2.0 ** 0.5
    paths = {1: ([-1, -1], sqrt2),
             2: ([0, -1], 1),
             3: ([1, -1], sqrt2),
             4: ([-1, 0], 1),
             6: ([0, 1], 1),
             7: ([-1, 1], sqrt2),
             8: ([0, 1], 1),
             9: ([1, 1], 1)}

    # we are providing the starting point of the flowpath
    flowpath = [(c, r)]
    distance = []
    slope = []

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
#            if warn:
#                warnings.warn('Flowpath c=%i, r=%i for %i went in a circle' % (c, r, sub_id))
            break

        # store the new values
        flowpath.append((c, r))
        distance.append(dis)
        slope.append(fvslop[c, r])

        # determine whether we have reached the end of the flowpath
        _id = subwta[c, r]
        pat = flopat[c, r]
        if pat in [0, 1] or _id != sub_id:
            break

        i += 1

        if i > n + m:
#            if warn:
#                warnings.warn('Flowpath c=%i, r=%i for %i is too long (>N)' % (c, r, sub_id))
            break

    # cast flowpath and distance as ndarrays
    flowpath = np.array(flowpath)
    distance = np.array(distance)
    slope = np.array(slope)

    if distance.shape != slope.shape:
        raise ValueError("Shape mismatch: distance and slope should have the same shape.")

    # return to _walk_flowpaths
    return flowpath, slope, distance


@njit
def weighted_slope_average_from_fps(flowpaths, slopes, distances, max_points=99) -> Tuple[np.array, np.array]:
    """
    calculates weighted slopes based on the flowpaths contained on the hillslope
    """
    # determine longest flowpath
    lengths = np.array([float(np.sum(d)) for d in distances])
    i = np.argmax(lengths)
    longest = float(lengths[i])

    # determine number of points to define slope
    num_points = len(distances[i])
    if num_points > max_points:
        num_points = max_points

    if num_points == 1:
        slope = slopes[i]
        slopes = np.array([slope[0], slope[0]])
        return slopes, np.array([0.0, 1.0])

    # for each flowpath determine the distance from channel
    # this requires reversing the elements in the distance
    # array and calculating the cumulative sum
    rev_cum_distances = [np.cumsum(d[::-1]) for d in distances]

    # if we did this right, then the distance should equally the longest
    # length
    if round(longest, 5) != round(rev_cum_distances[i][-1], 5):
        raise Exception('the distance should equally the longest length')

    # determine weights for each flowpath
    areas = np.array([f.shape[0] for f in flowpaths])
    kps = lengths * areas

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

    return w_slopes.flatten(), distance_p


class ChannelRoutingError(Exception):
    """
    The network structure delineated by TOPAZ contains more than 3 channels
    as input to a single channel. WEPP can only handle 3 or less channels
    draining into a single channel.

    The channels should be redelineated after adjusting the minimum channel
    length (mcl) and/or critical source area (csa)
    """

    __name__ = 'ChannelRoutingError'

    def __init__(self):
        pass


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
sqrt2 = 2.0 ** 0.5
paths = {1: ([-1, -1], sqrt2),
              2: ([0, -1], 1),
              3: ([1, -1], sqrt2),
              4: ([-1, 0], 1),
              6: ([0, 1], 1),
              7: ([-1, 1], sqrt2),
              8: ([0, 1], 1),
              9: ([1, 1], 1)}


class WatershedAbstraction:
    def __init__(self, wd, wat_dir):
        if not _exists(wd):
            raise Exception('Specified working directory does not exist')

        if not _exists(wat_dir):
            raise Exception('Specified wat_dir does not exist')

        self.wd = wd
        self.wat_dir = wat_dir


        # initialize datastructure containing json representation
        # of the abstracted watershed
        self.watershed = dict(hillslopes={}, channels={}, flowpaths={}, channel_paths={})
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

    def abstract(self, wepp_chn_type='Default', verbose=False, warn=False,
                 clip_hillslopes=False, clip_hillslope_length=300.0):
        self.abstract_channels(wepp_chn_type=wepp_chn_type, verbose=verbose)
        self.abstract_subcatchments(verbose=verbose, warn=warn,
                                    clip_hillslopes=clip_hillslopes, 
                                    clip_hillslope_length=clip_hillslope_length)
        self.abstract_structure(verbose=verbose)

    def write_slps(self, channels=1, subcatchments=1, flowpaths=1):
        """
        Writes slope files to the specified wat_dir. The channels,
        subcatchments, and flowpaths args specify what slope files
        should be written.
        """
        out_dir = self.wat_dir
        if channels:
            self._make_channel_slps(out_dir)

        if subcatchments:
            self._write_subcatchment_slps(out_dir)

        if flowpaths:
            self._write_flowpath_slps(out_dir)

    def _make_channel_slps(self, out_dir):
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
            d = ws['channels'][top]
            _chn_wepp_width = d.chn_wepp_width

            slp_fn = _join(out_dir, f'chn_{top}.slp')
            fp = open(slp_fn, 'w')
            write_slp(d.aspect, d.width, _chn_wepp_width, d.length,
                      d.slopes, d.distance_p, fp, 97.3)
            fp.close()

            write_slp(d.aspect, d.width, _chn_wepp_width, d.length,
                      d.slopes, d.distance_p, fp2, 99.1)

        fp2.close()

    def _write_subcatchment_slps(self, out_dir):
        ws = self.watershed
        cellsize = self.cellsize

        for sub_id, d in ws['hillslopes'].items():
            slp_fn = _join(out_dir, f'hill_{sub_id}.slp')
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

    def px_to_utm(self, x, y):
        _transform = self.transform
        e = _transform[0] + _transform[1] * x
        n = _transform[3] + _transform[5] * y
        return e, n

    def px_to_lnglat(self, x, y):
        proj2wgs_transformer = self.proj2wgs_transformer
        e, n = self.px_to_utm(x, y)
        lng, lat = proj2wgs_transformer.transform(e, n)
        return lng, lat

    def _read_netw_tab(self):
        translator = self.translator

        keys = "chnum order row col row1 col1 outr outc chnlen elevvup " \
               "elevdn areaup areadn1 areadn dda node1 node2 node3 node4 " \
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
            head = data[chnum]["col"] - 1, data[chnum]["row"] - 1
            center = data[chnum]["col1"] - 1, data[chnum]["row1"] - 1
            tail = data[chnum]["outc"] - 1, data[chnum]["outr"] - 1

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
            self.watershed["channels"][chnout_id].order = int(data[chnum]["order"])

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

            row = int(lines[98]) - 1
            col = int(lines[107]) - 1

            if not str(subwta[col, row]).endswith('4'):
                raise Exception('Identified outlet location is not a channel')

            return col, row

    def _determine_aspect(self, indx, indy) -> float:
        taspec = self.taspec
        rads = np.array(taspec[(indx, indy)]) * pi / 180.0
        return float(circmean(rads) * 180.0 / pi)

    @property
    def chn_ids(self):
        # extract the subcatchment and channel ids from the subwta map
        # subwta contains 0 values outside the watershed
        return self.translator._chn_ids

    def abstract_channels(self, wepp_chn_type='Default', verbose=False):
        chn_ids = self.chn_ids

        n = len(chn_ids)
        if n == 0:
            raise Exception('SUBWTA contains no channels')

        for i, chn_id in enumerate(chn_ids):
            if verbose:
                print('abstracting channel %s (%i of %i)...' % (chn_id, i + 1, n))
            chn_summary, chn_paths = self.abstract_channel(chn_id, wepp_chn_type=wepp_chn_type)

            # save channel abstraction to instance
            self.watershed['channels'][chn_id] = chn_summary
            self.watershed['channel_paths'][chn_id] = chn_paths

        self.channel_n = len(chn_ids)

    def _walk_channel(self, chn_id: int) -> \
            Tuple[np.array, np.array, np.array, np.array, np.array]:
        """
        for a channel specified by chn_id identifies
        the flowpath of the channel from top to bottom,
        the slope along the flowpath and the distance
        between points in the flowpath
        """
        global paths

        subwta = self.subwta
        relief = self.relief
        flovec = self.flovec
        fvslop = self.fvslop

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

        return chn_summary, (indx, indy)


    def write_channels_geojson(self, fn):
        watershed = self.watershed
        utm_proj = self.utmProj
        transform = self.transform

        pool = multiprocessing.Pool(NCPU)


        args_list = []
        for chn_id, summary in watershed['channels'].items():
            indx, indy = watershed['channel_paths'][chn_id]
            args_list.append([utm_proj, indx, indy, transform,
                              dict(TopazID=summary.topaz_id, WeppID=summary.wepp_id)])

        results = pool.map(transform_px_to_wgs, args_list)

        features = []
        for properties, coordinates in results:
            features.append(dict(properties=properties,
                                 geometry=dict(type='LineString', coordinates=coordinates),
                                 type='Feature'))

        fc = dict(features=features,
                  crs=dict(name=f'urn:ogc:def:crs:EPSG::4326', type='name'),
                  name='ChannelPaths',
                  type='FeatureCollection'
                 )

        with open(fn, 'w') as fp:
            json.dump(fc, fp)

    @property
    def sub_ids(self):
        return self.translator._sub_ids

    def abstract_subcatchments(self, verbose=False, warn=False,
                               clip_hillslopes=False, clip_hillslope_length=300.0):
        sub_ids = self.sub_ids

        n = len(sub_ids)
        if n == 0:
            raise Exception('SUBWTA contains no subcatchments')

        for i, sub_id in enumerate(sub_ids):
            if verbose:
                print('abstracting subtatchment %s (%i of %i)' % (sub_id, i + 1, n))
            sub_summary, fp_d = self.abstract_subcatchment(sub_id, verbose=verbose, warn=warn,
                                       clip_hillslopes=clip_hillslopes, clip_hillslope_length=clip_hillslope_length)

            self.watershed['hillslopes'][sub_id] = sub_summary
            self.watershed['flowpaths'][sub_id] = fp_d

        self.hillslope_n = len(sub_ids)

    def _walk_flowpaths(self, sub_id: int, verbose=False, warn=False) -> \
            Tuple[List[np.array], List[np.array], List[np.array], np.array, np.array]:
        """
        considers each cell of the subcatchment as a starting
        point for a flowpath. It walks down each flowpath to
        determine the slopes and distance for each.
        """
        subwta = self.subwta
        flopat = self.flopat
        flovec = self.flovec
        fvslop = self.fvslop

        flowpaths = []
        slopes = []
        distances = []

        indx, indy = np.where(subwta == sub_id)

        n = len(indx)
        for i, (c, r) in enumerate(zip(indx, indy)):
            if verbose:
                print('walking flowpath %i of %i (%s)' % (i + 1, n, sub_id))

            flowpath, slope, distance = _walk_flowpath(subwta, flopat, flovec, fvslop, sub_id, c, r, warn=warn)
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
        subflows = identify_subflows(flowpaths)

        # initialize a dictionary to hold the flowpath data
        fp_d = {}
        for j, fp_indxs in enumerate(subflows):
            # build the flowpath id
            # start at 1 to make sure wepp is happy
            fp_id = 'flow_%i_%i' % (sub_id, j + 1)

            fp_d[fp_id] = self.abstract_flowpath(flowpaths[fp_indxs[0]],
                                                 slopes[fp_indxs[0]],
                                                 distances[fp_indxs[0]])

        fp_d = {key: value for key, value in sorted(fp_d.items(), key=lambda item: item[1].length, reverse=True)}

        return fp_d, subflows

    def abstract_subcatchment(self, sub_id, verbose=False, warn=False,
                              clip_hillslopes=False, clip_hillslope_length=300.0):
        """
        define subcatchment abstraction for the purposes of running WEPP
        """
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
        chn_id = int(math.floor(sub_id / 10.0) * 10) + 4
        chn_summary = self.watershed["channels"][chn_id]

        # If subcatchment is a source type then we calculate the distance
        # by taking a weighted average based on the length of the flowpaths
        # contained in the subcatchment
        if str(sub_id).endswith('1'):
            length = cellsize * garbrecht_length(distances)
            if clip_hillslopes and length > clip_hillslope_length:
                length = clip_hillslope_length
            width = area / length

        # Otherwise the  width of the subcatchment is determined by the
        # channel that the subcatchment drains into. The length is
        # then determined by the area / width
        else:

            width = chn_summary.length
            length = area / width

            if clip_hillslopes and length > clip_hillslope_length:
                length = clip_hillslope_length
                width = area / length

        direction = chn_summary.direction
        if str(sub_id).endswith('2'):
            direction += 90
        if str(sub_id).endswith('3'):
            direction -= 90

        # determine aspect
        aspect = self._determine_aspect(indx, indy)

        # calculate weighted slope from flowpaths
        w_slopes, distance_p = \
            weighted_slope_average_from_fps(flowpaths, slopes, distances)

        # abstract the flowpaths
        fp_d, subflows = \
            self.abstract_flowpaths(sub_id, flowpaths, slopes, distances)

        fp_longest = list(fp_d.keys())[0]
        fp_longest_length = fp_d[fp_longest].length
        fp_longest_slope = fp_d[fp_longest].slope_scalar


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

        d = HillSummary(
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
            ),
            fp_longest=fp_longest,
            fp_longest_length=fp_longest_length,
            fp_longest_slope=fp_longest_slope
        )

        slp_fn = _join(self.wat_dir, f'hill_{sub_id}.slp')
        fp = open(slp_fn, 'w')
        write_slp(d.aspect, d.width, cellsize, d.length,
                  d.w_slopes, d.distance_p, fp, 97.3)
        fp.close()

        return d, fp_d

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
