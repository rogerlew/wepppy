import json

from os.path import join as _join
from os.path import exists as _exists
import math

from osgeo import gdal

import numpy as np
from scipy.ndimage import label
from subprocess import Popen, PIPE

from wepppy.all_your_base.geo import read_tif, centroid_px
from wepppy.topo.watershed_abstraction.wepp_top_translator import WeppTopTranslator
from wepppy.topo.watershed_abstraction.support import (
    cummnorm_distance, compute_direction, representative_normalized_elevations,
    weighted_slope_average, rect_to_polar, write_slp, HillSummary, ChannelSummary, CentroidSummary,
    slp_asp_color, polygonize_netful, polygonize_bound, polygonize_subcatchments, json_to_wgs
)

from .taudem import TauDEMRunner

_USE_MPI = False
_DEBUG = False


class Node:
    def __init__(self, tau_id, network):

        self.data = tau_id

        d = network[tau_id]

        self.top = top = d['top']
        self.bottom = bottom = d['bottom']

        links = d['links']

        if len(links) == 2:
            refvec = np.array(bottom, dtype=float) - np.array(top, dtype=float)
            links = sorted([dict(tau_id=_id, point=network[_id]['top'], origin=top, refvec=refvec)
                            for _id in links], key=lambda _d: rect_to_polar(_d))
            links = [_d['tau_id'] for _d in links]

        if len(links) > 0:
            self.left = Node(links[0], network)
        else:
            self.left = None

        if len(links) > 1:
            self.right = Node(links[1], network)
        else:
            self.right = None


class TauDEMTopazEmulator(TauDEMRunner):
    def __init__(self, wd, dem, vector_ext='geojson'):
        super(TauDEMTopazEmulator, self).__init__(wd, dem, vector_ext)

    # subwta
    @property
    def _subwta(self):
        return _join(self.wd, 'subwta.tif')

    # subwta
    @property
    def _subwta_shp(self):
        return _join(self.wd, 'subwta.geojson')

    # subcatchments
    @property
    def _subcatchments_shp(self):
       return _join(self.wd, 'subcatchments.geojson')

    # bound
    @property
    def _bound(self):
        return _join(self.wd, 'bound.tif')

    # bound
    @property
    def _bound_shp(self):
        return _join(self.wd, 'bound.geojson')

    # net
    @property
    def _netful_shp(self):
        return _join(self.wd, 'netful.geojson')

    @property
    def _channels(self):
        return _join(self.wd, 'channels.tif')

    def topaz2tau_translator_factory(self):
        d = self.tau2topaz_translator_factory()

        return {v: k for k, v in d.items()}

    def run_streamnet(self, single_watershed=False):
        super(TauDEMTopazEmulator, self).run_streamnet(single_watershed=single_watershed)

        tau2top_translator = self.tau2topaz_translator_factory()

        with open(self._net) as fp:
            js = json.load(fp)

        for i, feature in enumerate(js['features']):
            topaz_id = tau2top_translator[feature['properties']['WSNO']]
            js['features'][i]['properties']['TopazID'] = int(str(topaz_id) + '4')

        with open(self._net, 'w') as fp:
            json.dump(js, fp)

        cmd = ['gdal_rasterize', '-a', 'TopazID', '-a_nodata', '0',
               '-a_srs', 'epsg:{}'.format(self.epsg), 
               '-te', self.ul_x, self.lr_y, self.lr_x, self.ul_y,
               '-tr', self.cellsize, self.cellsize,
               '-ot', 'UInt16', self._net, self._channels]
        cmd = [str(v) for v in cmd]
        print(' '.join(cmd))

        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        p.wait()
        assert _exists(self._channels)

    def build_channels(self, csa=None):
        if csa is None:
            csa = 100

        wd = self.wd

        self.run_pitremove()
        self.run_d8flowdir()
        self.run_aread8()
        self.run_gridnet()
        self.run_src_threshold(threshold=csa)

        polygonize_netful(self._src, self._netful_shp)

    def set_outlet(self, lng, lat):
        self.run_moveoutletstostrm(lng=lng, lat=lat)

    def build_subcatchments(self, threshold=None):
        self.run_peukerdouglas()
        self.run_peukerdouglas_stream_delineation(threshold=threshold)
        self.run_streamnet()
        self.run_dinfflowdir()
        self.run_areadinf()
        self.run_dinfdistdown()

        json_to_wgs(self._net)

        self.delineate_subcatchments()
        polygonize_subcatchments(self._subwta, self._subwta_shp, self._subcatchments_shp)

        self.make_bound()
        polygonize_bound(self._bound, self._bound_shp)

    def abstract_watershed(self, wepp_chn_type,
                           clip_hillslopes=False, clip_hillslope_length=300.0):
        self.abstract_channels(wepp_chn_type=wepp_chn_type)
        self.abstract_subcatchments(clip_hillslopes=clip_hillslopes, 
                                    clip_hillslope_length=clip_hillslope_length)
        self.abstract_structure()

    @property
    def _abstracted_channels(self):
        return _join(self.wd, 'channels.json')

    @property
    def abstracted_channels(self):
        with open(self._abstracted_channels) as fp:
            summaries = json.load(fp)

        translator = self.translator

        chns_summary = {}
        for topaz_id, d in summaries.items():
            wepp_id = translator.wepp(top=topaz_id)
            chn_enum = translator.chn_enum(top=topaz_id)

            slope_scalar = d['slope_scalar']
            aspect = d['aspect']

            chns_summary[topaz_id] = \
                ChannelSummary(
                    topaz_id=topaz_id,
                    wepp_id=wepp_id,
                    chn_enum=chn_enum,
                    chn_type=d['wepp_chn_type'],
                    isoutlet=d['isoutlet'],
                    length=d['length'],
                    width=d['width'],
                    order=d['order'],
                    aspect=aspect,
                    head=d['head'],
                    tail=d['tail'],
                    direction=d['direction'],
                    slope_scalar=slope_scalar,
                    color=slp_asp_color(slope_scalar, aspect),
                    area=d['area'],
                    elevs=d['elevs'],
                    distance_p=d['distance_p'],
                    slopes=d['slopes'],
                    centroid=CentroidSummary(
                        px=d['centroid_px'],
                        lnglat=d['centroid_lnglat']
                    )
                )

        return chns_summary

    @property
    def _abstracted_subcatchments(self):
        return _join(self.wd, 'subcatchments.json')

    @property
    def abstracted_subcatchments(self):
        with open(self._abstracted_subcatchments) as fp:
            summaries = json.load(fp)

        translator = self.translator

        subs_summary = {}
        for topaz_id, d in summaries.items():
            wepp_id = translator.wepp(top=topaz_id)

            slope_scalar = d['slope_scalar']
            aspect = d['aspect']

            subs_summary[topaz_id] = \
                HillSummary(topaz_id=topaz_id,
                            wepp_id=wepp_id,
                            w_slopes=d['w_slopes'],
                            length=d['length'],
                            width=d['width'],
                            area=d['area'],
                            direction=d['direction'],
                            elevs=d['elevs'],
                            aspect=aspect,
                            slope_scalar=slope_scalar,
                            color=slp_asp_color(slope_scalar, aspect),
                            distance_p=d['distance_p'],
                            centroid=CentroidSummary(
                                px=d['centroid_px'],
                                lnglat=d['centroid_lnglat']
                            ),
                            fp_longest=d['fp_longest'],
                            fp_longest_length=d['fp_longest_length'],
                            fp_longest_slope=d['fp_longest_slope']
                            )

        return subs_summary

    @property
    def _structure(self):
        return _join(self.wd, 'structure.tsv')

    @property
    def structure(self):
        with open(self._structure) as fp:
            return [[int(v) for v in line.split()] for line in fp.readlines()]

    def abstract_channels(self, wepp_chn_type=None):
        cellsize = self.cellsize
        cellsize2 = self.cellsize2
        translator = self.translator

        slopes = self.data_fetcher('dinf_slope', dtype=np.float)
        fvslop = self.data_fetcher('dinf_angle', dtype=np.float)

        with open(self._net) as fp:
            js = json.load(fp)

        chn_d = {}

        for feature in js['features']:
            topaz_id = int(str(feature['properties']['TopazID'])[:-1])
            catchment_id = feature['properties']['WSNO']
            uslinkn01 = feature['properties']['USLINKNO1']
            uslinkn02 = feature['properties']['USLINKNO2']
            dslinkn0 = feature['properties']['DSLINKNO']
            order = feature['properties']['strmOrder']
            chn_id = int(str(topaz_id) + '4')

            enz_coords = feature['geometry']['coordinates']  # listed bottom to top

            # need to identify unique pixels
            px_last, py_last = None, None
            indx, indy = [], []
            for e, n, z in enz_coords:
                px, py = self.utm_to_px(e, n)
                if px != px_last or py != py_last:
                    assert 0 <= px < slopes.shape[0], ((px, py), (e, n), slopes.shape)
                    assert 0 <= py < slopes.shape[1], ((px, py), (e, n), slopes.shape)

                    indx.append(px)
                    indy.append(py)
                    px_last, py_last = px, py

            # the pixels are listed bottom to top we want them top to bottom as if we walked downt the flowpath
            indx = indx[::-1]
            indy = indy[::-1]

            flowpath = np.array([indx, indy]).T
            _distance = flowpath[:-1, :] - flowpath[1:, :]
            distance = np.sqrt(np.power(_distance[:, 0], 2.0) +
                               np.power(_distance[:, 1], 2.0))

            slope = np.array([slopes[px, py] for px, py in zip(indx[:-1], indy[:-1])])

            assert distance.shape == slope.shape, (distance.shape, slope.shape)

            if len(indx) == 1:
                px, py = indx[0], indy[0]
                slope_scalar = float(slopes[px, py])
                slope = np.array([slope_scalar, slope_scalar])

                head = enz_coords[-1][:-1]
                tail = enz_coords[0][:-1]
                direction = compute_direction(head, tail)

                length = np.linalg.norm(np.array(head) - np.array(tail))
                if length < cellsize:
                    length = cellsize

                width = cellsize2 / length

                distance_p = [0.0, 1.0]
                elevs = representative_normalized_elevations(distance_p, list(slope))

            else:
                # need normalized distance_p to define slope
                distance_p = cummnorm_distance(distance)
                if len(slope) == 1:
                    slope = np.array([float(slope), float(slope)])

                # calculate the length from the distance array
                length = float(np.sum(distance) * cellsize)
                width = float(cellsize)
                # aspect = float(self._determine_aspect(indx, indy))

                head = [v * cellsize for v in flowpath[-1]]
                head = [float(v) for v in head]
                tail = [v * cellsize for v in flowpath[0]]
                tail = [float(v) for v in tail]

                direction = compute_direction(head, tail)

                elevs = representative_normalized_elevations(distance_p, list(slope))
                slope_scalar = float(abs(elevs[-1]))

            area = float(length) * float(width)

            # calculate aspect
            aspect = np.mean(np.angle([np.complex(np.cos(rad), np.sin(rad)) for rad in fvslop[(indx, indy)]], deg=True))

            isoutlet = dslinkn0 == -1
            c_px, c_py = centroid_px(indx, indy)
            centroid_lnglat = self.px_to_lnglat(c_px, c_py)

            chn_enum = translator.chn_enum(chn_id=chn_id)
            chn_d[str(chn_id)] = dict(chn_id=int(chn_id),
                                      chn_enum=int(chn_enum),
                                      order=int(order),
                                      length=float(length),
                                      width=float(width),
                                      area=float(area),
                                      elevs=[float(v) for v in elevs],
                                      wepp_chn_type=wepp_chn_type,
                                      head=head,
                                      tail=tail,
                                      aspect=float(aspect),
                                      slopes=[float(v) for v in slope],
                                      isoutlet=isoutlet,
                                      direction=float(direction),
                                      distance_p=[float(v) for v in distance_p],
                                      centroid_px=[int(c_px), int(c_py)],
                                      centroid_lnglat=[float(v) for v in centroid_lnglat],
                                      slope_scalar=float(slope_scalar)
                                      )

        with open(self._abstracted_channels, 'w') as fp:
            json.dump(chn_d, fp, indent=2, sort_keys=True)

    @property
    def topaz_sub_ids(self):
        subwta = self.data_fetcher('subwta', dtype=np.uint16)
        sub_ids = sorted(list(set(subwta.flatten())))
        if 0 in sub_ids:        
            sub_ids.remove(0)
        sub_ids = [v for v in sub_ids if not str(v).endswith('4')]

        return sub_ids

    @property
    def topaz_chn_ids(self):
        with open(self._net) as fp:
            js = json.load(fp)

        chn_ids = []
        for feature in js['features']:
            chn_ids.append(feature['properties']['TopazID'])

        return chn_ids

    @property
    def translator(self):
        return WeppTopTranslator(top_sub_ids=self.topaz_sub_ids, top_chn_ids=self.topaz_chn_ids)

    def abstract_subcatchments(self, clip_hillslopes=False, clip_hillslope_length=300.0):
        """
        in: dinf_dd_horizontal, dinf_dd_vertical, dinf_dd_surface, dinf_slope, subwta
        :return:
        """
        cellsize = self.cellsize
        cellsize2 = self.cellsize2
        sub_ids = self.topaz_sub_ids

        assert _exists(self._dinf_dd_horizontal), self._dinf_dd_horizontal
        assert _exists(self._dinf_dd_vertical), self._dinf_dd_vertical
        assert _exists(self._dinf_dd_surface), self._dinf_dd_surface
        assert _exists(self._dinf_slope), self._dinf_slope
        assert _exists(self._subwta), self._subwta
        assert _exists(self._dinf_angle), self._dinf_angle

        subwta = self.data_fetcher('subwta', dtype=np.uint16)

        lengths = self.data_fetcher('dinf_dd_horizontal', dtype=np.float)
        verticals = self.data_fetcher('dinf_dd_vertical', dtype=np.float)
        surface_lengths = self.data_fetcher('dinf_dd_surface', dtype=np.float)
        slopes = self.data_fetcher('dinf_slope', dtype=np.float)
        aspects = self.data_fetcher('dinf_angle', dtype=np.float)

        chns_d = self.abstracted_channels

        subs_d = {}

        for sub_id in sub_ids:
            # identify cooresponding channel
            chn_id = str(sub_id)[:-1] + '4'

            # identify indices of sub_id
            raw_indx, raw_indy = np.where(subwta == sub_id)
            area = float(len(raw_indx)) * cellsize2

            indx, indy = [], []
            for _x, _y in zip(raw_indx, raw_indy):
                if lengths[_x, _y] >= 0.0:
                    indx.append(_x)
                    indy.append(_y)

            if len(indx) == 0:
                print('sub_id', sub_id)
                print('raw_indx, raw_indy', raw_indx, raw_indy)
                print(lengths[(raw_indx, raw_indy)])
                print(surface_lengths[(raw_indx, raw_indy)])
                print(slopes[(raw_indx, raw_indy)])
                print(aspects[(raw_indx, raw_indy)])

                width = length = math.sqrt(area)
                _slp = np.mean(slopes[(raw_indx, raw_indy)])
                w_slopes = [_slp, _slp]
                distance_p = [0, 1]

                fp_longest = None
                fp_longest_length = length
                fp_longest_slope = _slp
            else:
                # extract flowpath statistics
                fp_lengths = lengths[(indx, indy)]
                fp_lengths += cellsize
                fp_verticals = verticals[(indx, indy)]
                fp_surface_lengths = surface_lengths[(indx, indy)]
                fp_surface_lengths += cellsize
                fp_surface_areas = np.ceil(fp_surface_lengths) * cellsize
                fp_slopes = slopes[(indx, indy)]

                length = float(np.sum(fp_lengths * fp_surface_areas) / np.sum(fp_surface_areas))
                if clip_hillslopes and length > clip_hillslope_length:
                    length = clip_hillslope_length

                width = area / length

                # determine representative slope profile
                w_slopes, distance_p = weighted_slope_average(fp_surface_areas, fp_slopes, fp_lengths)

                # calculate longest flowpath statistics
                fp_longest = int(np.argmax(fp_lengths))
                fp_longest_vertical = fp_verticals[fp_longest]
                fp_longest_length = fp_lengths[fp_longest]
                fp_longest_slope = fp_longest_vertical / fp_longest_length

            # calculate slope for hillslope
            elevs = representative_normalized_elevations(distance_p, w_slopes)
            slope_scalar = float(abs(elevs[-1]))

            # calculate aspect
            _aspects = aspects[(indx, indy)]
            aspect = np.mean(np.angle([np.complex(np.cos(rad), np.sin(rad)) for rad in _aspects], deg=True))

            # calculate centroid
            c_px, c_py = centroid_px(raw_indx, raw_indy)
            centroid_lnglat = self.px_to_lnglat(c_px, c_py)

            direction = chns_d[chn_id].direction
            if str(sub_id).endswith('2'):
                direction += 90
            if str(sub_id).endswith('3'):
                direction -= 90

            subs_d[str(sub_id)] = dict(sub_id=int(sub_id),
                        area=float(area),
                        length=float(length),
                        aspect=float(aspect),
                        direction=float(direction),
                        width=float(width),
                        w_slopes=list(w_slopes),
                        distance_p=list(distance_p),
                        centroid_lnglat=[float(v) for v in centroid_lnglat],
                        centroid_px=[int(c_px), int(c_py)],
                        elevs=list(elevs),
                        slope_scalar=float(slope_scalar),
                        fp_longest=fp_longest,
                        fp_longest_length=float(fp_longest_length),
                        fp_longest_slope=float(fp_longest_slope)
                        )

        with open(self._abstracted_subcatchments, 'w') as fp:
            json.dump(subs_d, fp, indent=2, sort_keys=True)

    def abstract_structure(self, verbose=False):
        translator = self.translator
        topaz_network = self.topaz_network

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
            chns = topaz_network[top] + [0, 0, 0]

            # structure line with top ids
            _structure += [hright, hleft, hcenter] + chns[:3]

            # this is where we would handle impoundments
            # for now no impoundments are assumed
            _structure += [0, 0, 0]

            # and translate topaz to wepp
            structure.append([int(v) for v in _structure])

        with open(self._structure, 'w') as fp:
            for row in structure:
                fp.write('\t'.join([str(v) for v in row]))
                fp.write('\n')

    def delineate_subcatchments(self, use_topaz_ids=True):
        """
        in: pksrc, net
        out: subwta
        :return:
        """

        w_data = self.data_fetcher('w', dtype=np.int32)
        _src_data = self.data_fetcher('pksrc', dtype=np.int32)
        src_data = np.zeros(_src_data.shape, dtype=np.int32)
        src_data[np.where(_src_data == 1)] = 1

        subwta = np.zeros(w_data.shape, dtype=np.uint16)

        with open(self._net) as fp:
            js = json.load(fp)

        # identify pourpoints of the end node catchments
        end_node_pourpoints = {}
        for feature in js['features']:
            catchment_id = feature['properties']['WSNO']
            coords = feature['geometry']['coordinates']
            uslinkn01 = feature['properties']['USLINKNO1']
            uslinkn02 = feature['properties']['USLINKNO2']
            end_node = uslinkn01 == -1 and uslinkn02 == -1

            top = coords[-1][:-1]

            if end_node:
                end_node_pourpoints[catchment_id] = top

        # make geojson with pourpoints as input for gage watershed
        outlets_fn = _join(self.wd, 'outlets.geojson')
        self._make_multiple_outlets_geojson(dst=outlets_fn, en_points_dict=end_node_pourpoints)

        gw_fn = _join(self.wd, 'end_nodes_gw.tif')
        self._run_gagewatershed(outlets_fn=outlets_fn, dst=gw_fn)

        gw, _, _ = read_tif(gw_fn, dtype=np.int16)

        for _pass in range(2):
            for feature in js['features']:
                topaz_id = int(str(feature['properties']['TopazID'])[:-1])
                catchment_id = feature['properties']['WSNO']
                coords = feature['geometry']['coordinates']
                uslinkn01 = feature['properties']['USLINKNO1']
                uslinkn02 = feature['properties']['USLINKNO2']
                end_node = uslinkn01 == -1 and uslinkn02 == -1

                if (end_node and _pass) or (not end_node and not _pass):
                    continue  # this has already been processed

                top = coords[-1]
                bottom = coords[0]

                top_px = self.utm_to_px(top[0], top[1])
                bottom_px = self.utm_to_px(bottom[0], bottom[1])

                # need a mask for the side subcatchments
                catchment_data = np.zeros(w_data.shape, dtype=np.int32)
                catchment_data[np.where(w_data == catchment_id)] = 1

                if end_node:
                    # restrict the end node catchment the catchment area.
                    # otherwise there are cases where it gets drainage from beyond the watershed
                    gw_sub = gw * catchment_data

                    # identify top subcatchment cells
                    gw_indx = np.where(gw_sub == catchment_id)

                    # copy the top subcatchment to the subwta raster
                    if use_topaz_ids:
                        subwta[gw_indx] = int(str(topaz_id) + '1')
                    else:
                        subwta[gw_indx] = int(str(catchment_id) + '1')

                # remove end subcatchments from the catchment mask
                catchment_data[np.where(subwta != 0)] = 0

                # remove channels from catchment mask
                catchment_data -= src_data
                catchment_data = np.clip(catchment_data, a_min=0, a_max=1)
                indx, indy = np.where(catchment_data == 1)

                print(catchment_id, _pass, len(indx))

                # the whole catchment drains through the top of the channel
                if len(indx) == 0:
                    continue

                if _DEBUG:
                    driver = gdal.GetDriverByName('GTiff')
                    dst_ds = driver.Create(_join(self.wd, 'catchment_for_label_%05i.tif' % catchment_id),
                                           xsize=subwta.shape[0], ysize=subwta.shape[1],
                                           bands=1, eType=gdal.GDT_Int32,
                                           options=['COMPRESS=LZW', 'PREDICTOR=2'])
                    dst_ds.SetGeoTransform(self.transform)
                    dst_ds.SetProjection(self.srs_wkt)
                    band = dst_ds.GetRasterBand(1)
                    band.WriteArray(catchment_data.T)
                    dst_ds = None

                # we are going to crop the catchment for scipy.ndimage.label. It is really slow otherwise
                # to do this we identify the bounds and then add a pad
                pad = 1
                x0, xend = np.min(indx), np.max(indx)
                if x0 >= pad:
                    x0 -= pad
                else:
                    x0 = 0
                if xend < self.num_cols - pad:
                    xend += pad
                else:
                    xend = self.num_cols - 1

                y0, yend = np.min(indy), np.max(indy)

                if y0 >= pad:
                    y0 -= pad
                else:
                    y0 = 0
                if yend < self.num_rows - pad:
                    yend += pad
                else:
                    yend = self.num_rows - 1

                # crop to just the side channel catchments
                _catchment_data = catchment_data[x0:xend, y0:yend]

                # use scipy.ndimage.label to identify side subcatchments
                # todo: compare performance to opencv connectedComponents
                # https://stackoverflow.com/questions/46441893/connected-component-labeling-in-python
                subcatchment_data, n_labels = label(_catchment_data)

                # isolated pixels in the channel can get misidentified as subcatchments
                # this gets rid of those
                subcatchment_data -= src_data[x0:xend, y0:yend]

                # we only want the two largest subcatchments. These should be the side subcatchments
                # so we need to identify which are the largest
                sub_d = []
                for i in range(n_labels):
                    s_indx, s_indy = np.where(subcatchment_data == i + 1)
                    sub_d.append(dict(rank=len(s_indx), s_indx=s_indx, s_indy=s_indy,
                                      point=(x0 + np.mean(s_indx), y0 + np.mean(s_indy)),
                                      origin=(float(bottom_px[0]), float(bottom_px[1])),
                                      refvec=np.array(top_px, dtype=float) - np.array(bottom_px, dtype=float)
                                      )
                                 )

                # sort clockwise
                sub_d = sorted(sub_d, key=lambda _d: _d['rank'], reverse=True)

                if len(sub_d) > 2:
                    sub_d = sub_d[:2]

                sub_d = sorted(sub_d, key=lambda _d: rect_to_polar(_d))

                # assert len(sub_d) == 2

                k = 2
                for d in sub_d:
                    if use_topaz_ids:
                        subwta[x0:xend, y0:yend][d['s_indx'], d['s_indy']] = int(str(topaz_id) + str(k))
                    else:
                        subwta[x0:xend, y0:yend][d['s_indx'], d['s_indy']] = int(str(catchment_id) + str(k))
                    k += 1

        channels = self.data_fetcher('channels', dtype=np.int32)
        ind = np.where(subwta == 0)
        subwta[ind] = channels[ind]     

        driver = gdal.GetDriverByName('GTiff')
        dst_ds = driver.Create(self._subwta, xsize=subwta.shape[0], ysize=subwta.shape[1],
                               bands=1, eType=gdal.GDT_UInt16, options=['COMPRESS=LZW', 'PREDICTOR=2'])
        dst_ds.SetGeoTransform(self.transform)
        dst_ds.SetProjection(self.srs_wkt)
        band = dst_ds.GetRasterBand(1)
        band.WriteArray(subwta.T)
        band.SetNoDataValue(0)
        dst_ds = None

    def make_bound(self):

        w_data = self.data_fetcher('w', dtype=np.int32)

        bound = np.zeros(w_data.shape, dtype=np.int32)
        bound[np.where(w_data > 0)] = 1

        driver = gdal.GetDriverByName('GTiff')
        dst_ds = driver.Create(self._bound, xsize=bound.shape[0], ysize=bound.shape[1],
                               bands=1, eType=gdal.GDT_Byte, options=['COMPRESS=LZW', 'PREDICTOR=2'])
        dst_ds.SetGeoTransform(self.transform)
        dst_ds.SetProjection(self.srs_wkt)
        band = dst_ds.GetRasterBand(1)
        band.WriteArray(bound.T)
        band.SetNoDataValue(0)
        dst_ds = None

    def calculate_watershed_statistics(self):
        bound = self.data_fetcher('bound', dtype=np.int32)
        fvslop = self.data_fetcher('dinf_angle', dtype=np.float32)
        relief = self.data_fetcher('fel', dtype=np.float32)

        # calculate descriptive statistics
        cellsize = self.cellsize
        wsarea = float(np.sum(bound) * cellsize * cellsize)
        mask = -1 * bound + 1

        # determine area with slope > 30
        fvslop_ma = np.ma.masked_array(fvslop, mask=mask)
        indx, indy = np.ma.where(fvslop_ma > 0.3)
        area_gt30 = float(len(indx) * cellsize * cellsize)

        # determine ruggedness of watershed
        relief_ma = np.ma.masked_array(relief, mask=mask)
        minz = float(np.min(relief_ma))
        maxz = float(np.max(relief_ma))
        ruggedness = float((maxz - minz) / math.sqrt(wsarea))

        indx, indy = np.ma.where(bound == 1)
        ws_cen_px, ws_cen_py = int(np.round(np.mean(indx))), int(np.round(np.mean(indy)))
        ws_centroid = self.px_to_lnglat(ws_cen_px, ws_cen_py)
        outlet_top_id = None  # todo

        return dict(wsarea=wsarea,
                    area_gt30=area_gt30,
                    ruggedness=ruggedness,
                    minz=minz,
                    maxz=maxz,
                    ws_centroid=ws_centroid,
                    outlet_top_id=outlet_top_id,)

    @property
    def topaz_network(self):
        tau2top = self.tau2topaz_translator_factory()

        network = self.network

        top_network = {}
        for tau_id, d in network.items():
            topaz_id = int(str(tau2top[tau_id]) + '4')
            links = [int(str(tau2top[_tau_id]) + '4') for _tau_id in d['links']]
            top_network[topaz_id] = links

        return top_network

    def tau2topaz_translator_factory(self):
        tree = Node(self.outlet_tau_id, self.network)

        def preorder_traverse(node):
            res = []
            if node:
                res.append(node.data)
                res.extend(preorder_traverse(node.left))
                res.extend(preorder_traverse(node.right))

            return res

        tau_ids = preorder_traverse(tree)

        if _DEBUG:
            print('network', tau_ids)

        d = {tau_id: i+2 for i, tau_id in enumerate(tau_ids)}

        return d

    def write_slps(self, out_dir, channels=1, subcatchments=1, flowpaths=0):
        """
        Writes slope files to the specified wat_dir. The channels,
        subcatchments, and flowpaths args specify what slope files
        should be written.
        """
        if channels:
            self._make_channel_slps(out_dir)

        if subcatchments:
            self._write_subcatchment_slps(out_dir)

        if flowpaths:
            raise NotImplementedError

    def _make_channel_slps(self, out_dir):
        channels = self.abstracted_channels
        translator = self.translator

        chn_ids = channels.keys()
        chn_enums = sorted([translator.chn_enum(chn_id=v) for v in chn_ids])

        # watershed run requires a slope file defining all of the channels in the
        # 99.1 format. Here we write a combined channel slope file and a slope
        # file for each individual channel
        fp2 = open(_join(out_dir, 'channels.slp'), 'w')
        fp2.write('99.1\n')
        fp2.write('%i\n' % len(chn_enums))

        for chn_enum in chn_enums:
            top = translator.top(chn_enum=chn_enum)
            chn_id = str(top)
            d = channels[chn_id]
            _chn_wepp_width = d.chn_wepp_width
            write_slp(d.aspect, d.width, _chn_wepp_width, d.length,
                      d.slopes, d.distance_p, fp2, 99.1)

        fp2.close()

    def _write_subcatchment_slps(self, out_dir):
        subcatchments = self.abstracted_subcatchments
        cellsize = self.cellsize

        for sub_id, d in subcatchments.items():
            slp_fn = _join(out_dir, 'hill_%s.slp' % sub_id)
            fp = open(slp_fn, 'w')
            write_slp(d.aspect, d.width, cellsize, d.length,
                      d.w_slopes, d.distance_p, fp, 97.3)
            fp.close()
