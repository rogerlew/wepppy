# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
import zipfile

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

import csv
from collections import namedtuple

from datetime import datetime

from osgeo import gdal
import numpy as np
from scipy import stats

import numpy as np

from wepppy.nodb import Watershed, Landuse, Ron, Climate, Soils


def calc_ERMiT_grads(hillslope_model):
    distances, relative_elevs = hillslope_model

    length = distances[-1]

    y1 = np.interp(0.1 * length, distances, relative_elevs)
    y0 = relative_elevs[0]
    top = (y1 - y0) / (0.1 * length)

    y1 = np.interp(0.9 * length, distances, relative_elevs)
    y0 = np.interp(0.1 * length, distances, relative_elevs)
    middle = (y1 - y0) / (0.8 * length)

    y1 = relative_elevs[-1]
    y0 = np.interp(0.9 * length, distances, relative_elevs)
    bottom = (y1 - y0) / (0.1 * length)

    return top, middle, bottom


def calc_disturbed_grads(hillslope_model):
    distances, relative_elevs = hillslope_model

    length = distances[-1]

    y1 = np.interp(0.25 * length, distances, relative_elevs)
    y0 = relative_elevs[0]
    upper_top = (y1 - y0) / (0.25 * length)

    y1 = np.interp(0.5 * length, distances, relative_elevs)
    y0 = np.interp(0.25 * length, distances, relative_elevs)
    upper_bottom = (y1 - y0) / (0.25 * length)

    y1 = np.interp(0.75 * length, distances, relative_elevs)
    y0 = np.interp(0.5 * length, distances, relative_elevs)
    lower_top = (y1 - y0) / (0.25 * length)

    y1 = relative_elevs[-1]
    y0 = np.interp(0.75 * length, distances, relative_elevs)
    lower_bottom = (y1 - y0) / (0.25 * length)

    return upper_top, upper_bottom, lower_top, lower_bottom


def readSlopeFile(fname):

    with open(fname) as fid:
        lines = fid.readlines()

    assert int(lines[1]), 'expecting 1 ofe'

    nSegments, length = lines[3].split()
    nSegments = int(nSegments)
    length = float(length)

    distances, slopes = [], []

    row = lines[4].replace(',', '').split()
    row = [float(v) for v in row]
    assert len(row) == nSegments * 2, row
    for i in range(nSegments):
        distances.append(row[i * 2])
        slopes.append(row[i * 2 + 1])

    assert distances[0] == 0.0
    assert distances[-1] == 1.0

    distances = [d * length for d in distances]
    relative_elevs = [10000]
    for i in range(1, nSegments):
        dx = distances[i] - distances[i - 1]
        relative_elevs.append(relative_elevs[-1] + dx * slopes[i-1])

    hillslope_model = (distances, relative_elevs)

    upper_top, upper_bottom, lower_top, lower_bottom = \
        calc_disturbed_grads(hillslope_model)

    top, middle, bottom  = calc_ERMiT_grads(hillslope_model)

    return dict(Length=length,
                TopSlope=top * 100.0,
                MiddleSlope=middle * 100.0,
                BottomSlope=bottom * 100.0,
                UpperTopSlope=upper_top * 100.0,
                UpperBottomSlope=upper_bottom * 100.0,
                LowerTopSlope=lower_top * 100.0,
                LowerBottomSlope=lower_bottom * 100.0)


def create_ermit_input(wd):

    watershed = Watershed.getInstance(wd)
    landuse = Landuse.getInstance(wd)
    translator = watershed.translator_factory()
    wat_dir = watershed.wat_dir
    ron = Ron.getInstance(wd)
    name = ron.name.replace(' ', '_')
    climate = Climate.getInstance(wd)
    soils = Soils.getInstance(wd)

    if name == '':
        name = _split(wd)[-1]

    # write ermit input file
    header = 'HS_ID TOPAZ_ID UNIT_ID SOIL_TYPE AREA UTREAT USLP_LNG LTREAT UGRD_TP UGRD_BTM LGRD_TP LGRD_BTM LSLP_LNG '\
             'ERM_TSLP ERM_MSLP ERM_BSLP BURNCLASS ROCK_PCT'.split()

    export_dir = watershed.export_dir

    if not _exists(export_dir):
        os.mkdir(export_dir)

    fn = _join(export_dir, 'ERMiT_input_{}.csv'.format(name))
    fp = open(fn, 'w')
    dictWriter = csv.DictWriter(fp, fieldnames=header, lineterminator='\r\n')
    dictWriter.writeheader()

    for topaz_id, sub in watershed.sub_iter():
        wepp_id = translator.wepp(top=int(topaz_id))
        dom = landuse.domlc_d[str(topaz_id)]
        man = landuse.managements[dom]
        burn_class = landuse.identify_burn_class(topaz_id)
        mukey = soils.domsoil_d[topaz_id]
        soil_type = soils.soils[mukey].simple_texture
        rock_pct = soils.soils[mukey].smr

        if soil_type is None:
            try:
                mukey = soils.ssurgo_domsoil_d[topaz_id]
                soil_type = soils.soils[mukey].simple_texture
            except KeyError:
                soil_type = 'clay loam'

        slp_file = _join(wat_dir, 'hill_{}.slp'.format(topaz_id))
        v = readSlopeFile(slp_file)

        dictWriter.writerow({'HS_ID': wepp_id,
                             'TOPAZ_ID': topaz_id,
                             'UNIT_ID': '',
                             'SOIL_TYPE': soil_type,
                             'AREA': sub.area / 10000.0,
                             'UTREAT': man.desc,
                             'USLP_LNG': v['Length'] / 2.0,
                             'LTREAT': man.desc,
                             'LSLP_LNG': v['Length'] / 2.0,
                             'ERM_TSLP': v['TopSlope'],
                             'ERM_MSLP': v['MiddleSlope'],
                             'ERM_BSLP': v['BottomSlope'],
                             'UGRD_TP': v['UpperTopSlope'],
                             'UGRD_BTM': v['UpperBottomSlope'],
                             'LGRD_TP': v['LowerTopSlope'],
                             'LGRD_BTM': v['LowerBottomSlope'],
                             'BURNCLASS': burn_class,
                             'ROCK_PCT': rock_pct
                             })

    fp.close()

    fn2 = _join(export_dir, 'ERMiT_input_{}_meta.txt'.format(name))
    fp2 = open(fn2, 'w')
    fp2.write('''\
ERMiT/Disturbed WEPP GIS Hillslope File
=======================================

Created by WeppCloud
Date: {date}

Watershed Name: {name}
# of Hillslopes: {num_hills}
# of Channels: {num_chns}

Watershed Centroid Location
   Latitude: {centroid_lat}
   Longitude: {centroid_lng}   
   
Climate Station
   State: {station.state}
   Station: {station.desc}
   PAR: {station.par}
   Elevation: {station.elevation}
   Latitude: {station.latitude}
   Longitude: {station.longitude}

Column Descriptions
++++++++++++++++++++

   
HS_ID
    Wepp hillslope ID
    
TOPAZ_ID
    TOPAZ hillslope ID
    
UNIT_ID
    - (Don't know)
    
SOIL_TYPE
    - Soil texture classified from ssurgo/statsgo
    
AREA
    - Area in hectares

    
Slope parameters for Disturbed WEPP Batch File
----------------------------------------------

Slope is divided into four segments each 25% of total slope
    
"U" is for Upper, "L" is for Lower
    
UTREAT
    - description of management file
    
USLP_LNG
    - length of the upper slope (50% of total slope)

LTREAT
    - description of management file
    
UGRD_TP
    - Upper top slope (%)
    
UGRD_BTM
    - Upper bottom slope (%)
    
LGRD_TP
    - Lower top slope (%)

LGRD_BTM
    - Lower bottom slope (%)
    
LSLP_LNG
    - length of the lower slope (50% of total slope)
    
Slope parameters for ERMiT WEPP Batch File
----------------------------------------------

According to ERMiT documentation the slope is divided into 
3 segments representing the top 10% middle 80% and bottom 10%.

Interface replicates Jim Frakenberger's code which uses the first 
slope point as the top and the last slope point as the bottom.

ERM_TSLP
    - Top slope (%)
    
ERM_MSLP
    - Middle slope (%)
    
ERM_BSLP
    - Bottom slope (%)
    
BURNCLASS
    - Burn class as Unburned, Low, Moderate, High

ROCK_PCT
    - Calcuated percent rock from soil file
'''.format(date=datetime.now(),
           name=name,
           num_hills=watershed.sub_n,
           num_chns=watershed.chn_n,
           centroid_lat=watershed.centroid[1],
           centroid_lng=watershed.centroid[0],
           station=climate.climatestation_meta))

    fp2.close()

    zipfn = _join(export_dir, 'ERMiT_input_{}.zip'.format(name))
    zipf = zipfile.ZipFile(zipfn, 'w', zipfile.ZIP_DEFLATED)
    zipf.write(fn, _split(fn)[-1])
    zipf.write(fn2, _split(fn2)[-1])
    zipf.close()

    return zipfn


if __name__ == "__main__":
    create_ermit_input('/geodata/weppcloud_runs/054972e3-2d7d-4caf-833a-a73d400b0f39/')

