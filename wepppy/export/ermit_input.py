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
from scipy.interpolate import KroghInterpolator

from wepppy.nodb import Watershed, Landuse, Ron


def polycurve(x, dy):
    #
    # Calculate the y positions from the derivatives
    #

    # for each segment calculate the average gradient from the derivatives at each point
    dy = np.array(dy)
    dy_ = np.array([np.mean(dy[i:i + 2]) for i in range(len(dy) - 1)])

    # calculate the positions, assume top of hillslope is 0 y
    y = [0]
    for i in range(len(dy) - 1):
        step = x[i + 1] - x[i]
        y.append(y[-1] - step * dy_[i])
    y = np.array(y)

    assert len(dy) == len(y), '%i, %i, %i' % (len(x), len(dy), len(y))
    assert dy.shape == y.shape, '%i, %i' % (dy.shape, y.shape)

    xi_k = np.repeat(x, 2)
    yi_k = np.ravel(np.dstack((y, -1 * dy)))

    #
    # Return the model
    #
    return KroghInterpolator(xi_k, yi_k)


def calc_ERMiT_grads(hillslope_model):
    p = hillslope_model
    assert p.xi[0] == 0.0
    assert p.xi[-1] == 1.0

    y1 = p(0.1)
    y0 = p(0.0)
    top = -(y1 - y0) / 0.1

    y1 = p(0.9)
    y0 = p(0.1)
    middle = -(y1 - y0) / 0.8

    y1 = p(1.0)
    y0 = p(0.9)
    bottom = -(y1 - y0) / 0.1

    return top, middle, bottom


def calc_disturbed_grads(hillslope_model):
    p = hillslope_model
    assert p.xi[0] == 0.0
    assert p.xi[-1] == 1.0

    y1 = p(0.25)
    y0 = p(0.0)
    upper_top = -(y1 - y0) / 0.25

    y1 = p(0.50)
    y0 = p(0.25)
    upper_bottom = -(y1 - y0) / 0.25

    y1 = p(0.75)
    y0 = p(0.50)
    lower_top = -(y1 - y0) / 0.25

    y1 = p(1.00)
    y0 = p(0.75)
    lower_bottom = -(y1 - y0) / 0.25

    return upper_top, upper_bottom, lower_top, lower_bottom


def readSlopeFile(fname):
    fid = open(fname)
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

    fid.close()

    hillslope_model = polycurve(distances, slopes)

    #    top, middle, bottom = calc_ERMiT_grads(hillslope_model)
    upper_top, upper_bottom, lower_top, lower_bottom = \
        calc_disturbed_grads(hillslope_model)

    # How slopes are calculated on Jim Frankberger's WEPP interface
    total_slope = sum(slopes)
    top = slopes[0]
    bottom = slopes[-1]
    if len(slopes) > 2:
        middle = total_slope / (nSegments - 2.0)
    else:
        middle = total_slope / 2.0

    return dict(Length=length,
                TopSlope=top * 100.0,
                MiddleSlope=middle * 100.0,
                BottomSlope=bottom * 100.0,
                UpperTopSlope=upper_top * 100.0,
                UpperBottomSlope=upper_bottom * 100.0,
                LowerTopSlope=lower_top * 100.0,
                LowerBottomSlope=lower_bottom * 100.0)


landml2burnclass = {130: 'Unburned',
                    131: 'Low',
                    132: 'Moderate',
                    133: 'High',
                    105: 'High',
                    106: 'Low'
                    }


def create_ermit_input(wd):

    watershed = Watershed.getInstance(wd)
    landuse = Landuse.getInstance(wd)
    translator = watershed.translator_factory()
    wat_dir = watershed.wat_dir
    ron = Ron.getInstance(wd)
    name = ron.name.replace(' ', '_')

    if name == '':
        name = _split(wd)[-1]

    # write ermit input file
    header = 'HS_ID TOPAZ_ID UNIT_ID SOIL_TYPE AREA UTREAT USLP_LNG LTREAT UGRD_TP UGRD_BTM LGRD_TP LGRD_BTM LSLP_LNG '\
             'ERM_TSLP ERM_MSLP ERM_BSLP BURNCLASS'.split()

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
        burnclass = landml2burnclass.get(int(dom), 'N/A')

        slp_file = _join(wat_dir, 'hill_{}.slp'.format(topaz_id))
        v = readSlopeFile(slp_file)

        dictWriter.writerow({'HS_ID': wepp_id,
                             'TOPAZ_ID': topaz_id,
                             'UNIT_ID': '',
                             'SOIL_TYPE': 'Sandy Loam',
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
                             'BURNCLASS': burnclass
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



Column Descriptions
++++++++++++++++++++

   
HS_ID
    Wepp hillslope ID
    
TOPAZ_ID
    TOPAZ hillslope ID
    
UNIT_ID
    - (Don't know)
    
SOIL_TYPE
    - Currently is always "Sandy Loam"
    
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

'''.format(date=datetime.now(),
           name=name,
           num_hills=watershed.sub_n,
           num_chns=watershed.chn_n,
           centroid_lat=watershed.centroid[1],
           centroid_lng=watershed.centroid[0]))
    fp2.close()

    zipfn = _join(export_dir, 'ERMiT_input_{}.zip'.format(name))
    zipf = zipfile.ZipFile(zipfn, 'w', zipfile.ZIP_DEFLATED)
    zipf.write(fn, _split(fn)[-1])
    zipf.write(fn2, _split(fn2)[-1])
    zipf.close()

    return zipfn


if __name__ == "__main__":
    create_ermit_input('/geodata/weppcloud_runs/054972e3-2d7d-4caf-833a-a73d400b0f39/')

