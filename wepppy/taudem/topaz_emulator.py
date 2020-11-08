from typing import List

import os
import json

from os.path import join as _join
from os.path import exists as _exists
import math

from osgeo import gdal, osr

import numpy as np
from scipy.ndimage import label

from wepppy.all_your_base.geo import read_tif, centroid_px
from wepppy.watershed_abstraction.wepp_top_translator import WeppTopTranslator
from wepppy.watershed_abstraction.support import (
    cummnorm_distance, compute_direction, representative_normalized_elevations,
    weighted_slope_average, rect_to_polar
)

from .taudem import TauDEMRunner

_USE_MPI = True
_DEBUG = True


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

    def topaz2tau_translator_factory(self):
        d = self.tau2topaz_translator_factory()

        return {v: k for k, v in d.items()}

    def run_streamnet(self, single_watershed=False):
        super(TauDEMTopazEmulator, self).run_streamnet(single_watershed=single_watershed)

        translator = self.tau2topaz_translator_factory()

        with open(self._net) as fp:
            js = json.load(fp)

        for i, feature in enumerate(js['features']):
            topaz_id = translator[feature['properties']['WSNO']]
            js['features'][i]['properties']['TopazID'] = int(str(topaz_id) + '4')

        with open(self._net, 'w') as fp:
            json.dump(js, fp)

    def abstract_channels(self, use_topaz_ids=True):
        cellsize = self.cellsize
        cellsize2 = self.cellsize2

        slopes = self.data_fetcher('dinf_slope', dtype=np.float)

        with open(self._net) as fp:
            js = json.load(fp)

        chn_d = {}

        for feature in js['features']:
            topaz_id = int(str(feature['properties']['TopazID'])[:-1])
            catchment_id = feature['properties']['WSNO']
            uslinkn01 = feature['properties']['USLINKNO1']
            uslinkn02 = feature['properties']['USLINKNO2']
            dslinkn0 = feature['properties']['DSLINKNO']

            if use_topaz_ids:
                chn_id = int(str(topaz_id) + '4')
            else:
                chn_id = int(str(catchment_id) + '4')

            enz_coords = feature['geometry']['coordinates']  # listed bottom to top

            # need to identify unique pixels
            px_last, py_last = None, None
            indx, indy = [], []
            for e, n, z in enz_coords:
                px, py = self.utm_to_px(e, n)
                if px != px_last or py != py_last:
                    assert px >= 0 and px < slopes.shape[0], ((px, py), (e, n), slopes.shape)
                    assert py >= 0 and py < slopes.shape[1], ((px, py), (e, n), slopes.shape)

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

            isoutlet = dslinkn0 == -1
            c_px, c_py = centroid_px(indx, indy)
            centroid_lnglat = self.px_to_lnglat(c_px, c_py)

            chn_d[str(chn_id)] = dict(chn_id=int(chn_id),
                                      length=float(length),
                                      width=float(width),
                                      slopes=[float(v) for v in slope],
                                      isoutlet=isoutlet,
                                      direction=float(direction),
                                      distance_p=[float(v) for v in distance_p],
                                      centroid_lnglat=[float(v) for v in centroid_lnglat],
                                      elevs=list(elevs),
                                      slope_scalar=float(slope_scalar)
                                      )

        with open(_join(self.wd, 'channels.json'), 'w') as fp:
            json.dump(chn_d, fp, indent=2, sort_keys=True)

    @property
    def topaz_sub_ids(self):
        subwta = self.data_fetcher('subwta', dtype=np.uint16)
        sub_ids = sorted(list(set(subwta.flatten())))
        sub_ids.remove(0)

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

    def abstract_subcatchments(self):
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

        subwta = self.data_fetcher('subwta', dtype=np.uint16)

        lengths = self.data_fetcher('dinf_dd_horizontal', dtype=np.float)
        verticals = self.data_fetcher('dinf_dd_vertical', dtype=np.float)
        surface_lengths = self.data_fetcher('dinf_dd_surface', dtype=np.float)
        slopes = self.data_fetcher('dinf_slope', dtype=np.float)

        subs_d = {}

        for sub_id in sub_ids:
            # identify indicies of sub_id
            raw_indx, raw_indy = np.where(subwta == sub_id)
            area = float(len(raw_indx)) * cellsize2

            # qc for dinf statistics
            indx = []
            indy = []
            for x, y in zip(raw_indx, raw_indy):
                if lengths[x, y] > 0:
                    indx.append(x)
                    indy.append(y)

            # extract flowpath statistics
            fp_lengths = lengths[(indx, indy)]
            fp_verticals = verticals[(indx, indy)]
            fp_surface_lengths = surface_lengths[(indx, indy)]
            fp_slopes = slopes[(indx, indy)]

            # determine representative length and width
            # Cochrane dissertation eq 3.4
            length = float(np.sum(fp_lengths * fp_surface_lengths) / np.sum(fp_surface_lengths))
            width = area / length

            # determine representative slope profile
            w_slopes, distance_p = weighted_slope_average(fp_surface_lengths, fp_slopes, fp_lengths)

            elevs = representative_normalized_elevations(distance_p, w_slopes)
            slope_scalar = float(abs(elevs[-1]))

            # calculate centroid
            c_px, c_py = centroid_px(indx, indy)
            centroid_lnglat = self.px_to_lnglat(c_px, c_py)

            # calculate longest flowpath statistics
            fp_longest = np.argmax(fp_lengths)
            fp_longest_vertical = fp_verticals[fp_longest]
            fp_longest_length = fp_lengths[fp_longest]
            fp_longest_slope = fp_longest_vertical / fp_longest_length

            subs_d[str(sub_id)] = dict(sub_id=int(sub_id),
                        area=float(area),
                        length=float(length),
                        width=float(width),
                        w_slopes=list(w_slopes),
                        distance_p=list(distance_p),
                        centroid_lnglat=[float(v) for v in centroid_lnglat],
                        elevs=list(elevs),
                        slope_scalar=float(slope_scalar),
                        fp_longest=float(fp_longest),
                        fp_longest_length=float(fp_longest_length),
                        fp_longest_slope=float(fp_longest_slope)
                        )

        with open(_join(self.wd, 'subcatchments.json'), 'w') as fp:
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

        with open(_join(self.wd, 'structure.tsv'), 'w') as fp:
            for row in structure:
                fp.write('\t'.join([str(v) for v in row]))
                fp.write('\n')

    def delineate_subcatchments(self, use_topaz_ids=True):
        """
        in: pksrc, net,
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

        for _pass in range(2):
            for feature in js['features']:
                topaz_id = int(str(feature['properties']['TopazID'])[:-1])
                catchment_id = feature['properties']['WSNO']
                coords = feature['geometry']['coordinates']
                uslinkn01 = feature['properties']['USLINKNO1']
                uslinkn02 = feature['properties']['USLINKNO2']
                end_node = uslinkn01 == -1 and uslinkn02 == -1

                if end_node:
                    if _pass == 1:
                        continue  # this has already been processed

                else:
                    if _pass == 0:
                        continue  # don't process non end nodes on the first pass

                top = coords[-1]
                bottom = coords[0]

                top_px = self.utm_to_px(top[0], top[1])
                bottom_px = self.utm_to_px(bottom[0], bottom[1])

                # need a mask for the side subcatchments
                catchment_data = np.zeros(w_data.shape, dtype=np.int32)
                catchment_data[np.where(w_data == catchment_id)] = 1

                if end_node:
                    gw = _join(self.wd, 'wsno_%05i.tif' % catchment_id)
                    self._run_gagewatershed(easting=top[0], northing=top[1], dst=gw)

                    gw_data, _, _ = read_tif(gw, dtype=np.int16)  # gage watershed cells are 0 in the drainage area
                    gw_data += 1
                    gw_data = np.clip(gw_data, 0, 1)

                    # don't allow gw to extend beyond catchment
                    gw_data *= catchment_data

                    # identify top subcatchment cells
                    gw_indx = np.where(gw_data == 1)

                    # copy the top subcatchment to the subwta raster
                    if use_topaz_ids:
                        subwta[gw_indx] = int(str(topaz_id) + '1')
                    else:
                        subwta[gw_indx] = int(str(catchment_id) + '1')

                    if not _DEBUG:
                        os.remove(gw)
                        os.remove(gw[:-4] + '.geojson')

                # remove end subcatchments from the catchment mask
                catchment_data[np.where(subwta != 0)] = 0

                # remove channels from catchment mask
                catchment_data -= src_data
                catchment_data = np.clip(catchment_data, a_min=0, a_max=1)
                indx, indy = np.where(catchment_data == 1)

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
                if xend < self.num_cols - pad:
                    xend += pad

                y0, yend = np.min(indy), np.max(indy)

                if y0 >= pad:
                    y0 -= pad
                if yend < self.num_rows - pad:
                    yend += pad

                # crop to just the side channel catchments
                _catchment_data = catchment_data[x0:xend, y0:yend]

                # use scipy.ndimage.label to identify side subcatchments
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

        driver = gdal.GetDriverByName('GTiff')
        dst_ds = driver.Create(self._subwta, xsize=subwta.shape[0], ysize=subwta.shape[1],
                               bands=1, eType=gdal.GDT_UInt16, options=['COMPRESS=LZW', 'PREDICTOR=2'])
        dst_ds.SetGeoTransform(self.transform)
        dst_ds.SetProjection(self.srs_wkt)
        band = dst_ds.GetRasterBand(1)
        band.WriteArray(subwta.T)
        band.SetNoDataValue(0)
        dst_ds = None

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
