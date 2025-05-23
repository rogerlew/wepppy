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

from wepppy.climates.cligen import nullStation


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
    _line2 = lines[2].split()
    aspect = float(_line2[0])
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

    if length > 300.0:
        length = 300.0

    return dict(Length=length,
                Aspect=aspect,
                TopSlope=top * 100.0,
                MiddleSlope=middle * 100.0,
                BottomSlope=bottom * 100.0,
                UpperTopSlope=upper_top * 100.0,
                UpperBottomSlope=upper_bottom * 100.0,
                LowerTopSlope=lower_top * 100.0,
                LowerBottomSlope=lower_bottom * 100.0)

"""
# ERMIT parser
     For r = HillslopeStartRow To LastRow
            E.hs_code = Trim(.Cells(r, 1))
            E.Area = .Cells(r, 4)
            E.SoilType = Trim(LCase(.Cells(r, 6)))
            E.RockPercent = .Cells(r, 7)
            E.VegType = Trim(.Cells(r, 8))
            E.TopGradient = .Cells(r, 9)
            E.MidGradient = .Cells(r, 10)
            E.ToeGradient = .Cells(r, 11)
            E.ShrubPercent = .Cells(r, 12)
            E.GrassPercent = .Cells(r, 13)
            E.BarePercent = .Cells(r, 14)
            E.HorizontalSlopeLength = .Cells(r, 15)
            E.BurnClass = Trim(LCase(.Cells(r, 17)))


# Disturbed Batch parser ()
   For i = 0 To UBound(headers)
     'fields(headers(i)) = i
     If (headers(i) = "Rowid_1") Then Rowid_1 = i   '
     If (headers(i) = "ROWID_") Then ROWID_ = i     '
     If (headers(i) = "OID_") Then OID_ = i         '
     If (headers(i) = "HS_ID") Then HS_ID = i       '
     If (headers(i) = "UNIT_ID") Then UNIT_ID = i   '
     If (headers(i) = "SOIL_TYPE") Then SOIL_TYPE = i ' - GIS soil ype
     If (headers(i) = "AREA") Then Area_ = i        ' - area
     If (headers(i) = "UTREAT") Then Utreat = i     ' - upper treatment
     If (headers(i) = "USLP_LNG") Then USLP_LNG = i ' - upper slope length
     If (headers(i) = "UGRD_TP") Then UGRD_TP = i   ' - upper top gradient %
     If (headers(i) = "UGRD_BTM") Then UGRD_BTM = i ' - upper bottom gradient %
     If (headers(i) = "LTREAT") Then Ltreat = i     ' - lower treatment
     If (headers(i) = "LSLP_LNG") Then LSLP_LNG = i ' - lower length
     If (headers(i) = "LGRD_TP") Then LGRD_TP = i   ' - lower section top gradient %
     If (headers(i) = "LGRD_BTM") Then LGRD_BTM = i ' - lower section bottom gradient %
     If (headers(i) = "ROCK_PCT") Then ROCK_PCT = i ' - rock pct %
"""

def fmt(x):
    """
    Format anything that should be numeric to one decimal place.
    Safely handles None/''/already-formatted strings.
    """
    try:
        return f'{float(x):.1f}'
    except (TypeError, ValueError):
        return x            # leave it untouched if it isn't numeric
        

def create_ermit_input(wd):

    _log = [f'Creating ERMiT input for {wd}']

    watershed = Watershed.getInstance(wd)
    landuse = Landuse.getInstance(wd)
    translator = watershed.translator_factory()
    wat_dir = watershed.wat_dir
    ron = Ron.getInstance(wd)
    name = ron.name.replace(' ', '_')
    climate = Climate.getInstance(wd)
    climatestation_meta = climate.climatestation_meta

    if climatestation_meta is None:
        _log.append('No climate station found')
        climatestation_meta = nullStation

    soils = Soils.getInstance(wd)

    if name == '':
        name = _split(wd)[-1]


    #         header         index     ERMiT                                     Disturbed                                          Description
    header = ['HS_ID',     #     1     E.hs_code = Trim(.Cells(r, 1))            If (headers(i) = "HS_ID") Then HS_ID = i           wepp id
              'TOPAZ_ID',  #     2                                                                                                  topaz_id (not used)
              'UNIT_ID',   #     3                                               If (headers(i) = "UNIT_ID") Then UNIT_ID = i       unit_id (empty, don't know what this is for. it is read by disturbed)
              'AREA',      #     4     E.Area = .Cells(r, 4)                     If (headers(i) = "AREA") Then Area_ = i            area (ha)
              'ROWID_',    #     5                                               If (headers(i) = "ROWID_") Then ROWID_ = i         row_id
              'SOIL_TYPE', #     6     E.SoilType = Trim(LCase(.Cells(r, 6)))    If (headers(i) = "SOIL_TYPE") Then SOIL_TYPE = i   4 class soil texture
              'ROCK_PCT',  #     7     E.RockPercent = .Cells(r, 7)              If (headers(i) = "ROCK_PCT") Then ROCK_PCT = i     rock content in percent
              'VEG_TYPE',  #     8     E.VegType = Trim(.Cells(r, 8))                                                               vegetation/landuse from weppcloud undisturbed
              'ERM_TSLP',  #     9     E.TopGradient = .Cells(r, 9)                                                                 top gradient for ERmiT
              'ERM_MSLP',  #    10     E.MidGradient = .Cells(r, 10)                                                                middle gradient from ERmiT
              'ERM_BSLP',  #    11     E.ToeGradient = .Cells(r, 11)                                                                bottom gradient for ERmiT
              'SHRUB_PCT', #    12     E.ShrubPercent = .Cells(r, 12)                                                               shrub percentage for ERmiT
              'GRASS_PCT', #    13     E.GrassPercent = .Cells(r, 13)                                                               grass percentage for ERmiT
              'BARE_PCT',  #    14     E.BarePercent = .Cells(r, 14)                                                                bare percentage for ERmiT
              'LENGTH',    #    15     E.HorizontalSlopeLength = .Cells(r, 15)                                                      horizontal slope length from ERmiT (m)
              'ASPECT',    #    16                                                                                                  aspect (not used)
              'BURNCLASS', #    17     E.BurnClass = Trim(LCase(.Cells(r, 17)))                                                     burn class for ERMiT
              'UTREAT',    #    18                                               If (headers(i) = "UTREAT") Then Utreat = i         upper treatment (management) for disturbed batch
              'USLP_LNG',  #    19                                               If (headers(i) = "USLP_LNG") Then USLP_LNG = i     upper slope length for disturbed batch (m)
              'UGRD_TP',   #    20                                               If (headers(i) = "UGRD_TP") Then UGRD_TP = i       upper top gradient for disturbed batch
              'UGRD_BTM',  #    21                                               If (headers(i) = "UGRD_BTM") Then UGRD_BTM = i     upper bottom gradient for disturbed batch
              'LTREAT',    #    22                                               If (headers(i) = "LTREAT") Then Ltreat = i         lower treatment (management) for disturbed batch
              'LSLP_LNG',  #    23                                               If (headers(i) = "LSLP_LNG") Then LSLP_LNG = i     lower slope length for disturbed batch (m)
              'LGRD_TP',   #    24                                               If (headers(i) = "LGRD_TP") Then LGRD_TP = i       lower top gradient for disturbed batch
              'LGRD_BTM']  #    25                                               If (headers(i) = "LGRD_BTM") Then LGRD_BTM = i     lower bottom gradient for disturbed batch
              
    export_dir = watershed.export_dir

    if not _exists(export_dir):
        os.mkdir(export_dir)

    fn = _join(export_dir, 'ERMiT_input_{}.csv'.format(name))
    fp = open(fn, 'w')
    dictWriter = csv.DictWriter(fp, fieldnames=header, lineterminator='\r\n')
    dictWriter.writeheader()

    row_id = 1
    for topaz_id in watershed._subs_summary:
        _log.append(f'  processing {topaz_id}')
        wepp_id = translator.wepp(top=int(topaz_id))
        dom = landuse.domlc_d[str(topaz_id)]
        man = landuse.managements[dom]

        veg_type = ''

        if hasattr(man, 'disturbed_class'):
            veg_type = man.disturbed_class

        shrub_pct = ''
        grass_pct = ''
        bare_pct = ''
        if _exists(_join(wd, 'rap.nodb')):
            # load cover from rap
            pass
        
        burn_class = landuse.identify_burn_class(topaz_id)
        mukey = soils.domsoil_d[topaz_id]
        soil_type = soils.soils[mukey].simple_texture
        rock_pct = soils.soils[mukey].smr

        if rock_pct < 10:
            _log.append(f'    {topaz_id} rock_pct = {rock_pct} < 10')
            rock_pct = 10

        if soil_type is None:
            try:
                mukey = soils.ssurgo_domsoil_d[topaz_id]
                soil_type = soils.soils[mukey].simple_texture
            except KeyError:
                soil_type = 'clay loam'

        slp_file = _join(wat_dir, 'hill_{}.slp'.format(topaz_id))

        if not _exists(slp_file):
            slp_file = _join(wat_dir, 'slope_files', 'hillslopes', 'hill_{}.slp'.format(topaz_id))

        _log.append(f'    reading {slp_file}')
        v = readSlopeFile(slp_file)

        dictWriter.writerow({
            'HS_ID'     : wepp_id,
            'TOPAZ_ID'  : topaz_id,
            'UNIT_ID'   : '',
            'AREA'      : watershed.hillslope_area(topaz_id) / 1e4,
            'ROWID_'    : row_id,
            'SOIL_TYPE' : soil_type,
            'ROCK_PCT'  : fmt(rock_pct),
            'VEG_TYPE'  : veg_type,
            'ERM_TSLP'  : fmt(v['TopSlope']),
            'ERM_MSLP'  : fmt(v['MiddleSlope']),
            'ERM_BSLP'  : fmt(v['BottomSlope']),
            'SHRUB_PCT' : fmt(shrub_pct),
            'GRASS_PCT' : fmt(grass_pct),
            'BARE_PCT'  : fmt(bare_pct),
            'LENGTH'    : fmt(v['Length']),
            'ASPECT'    : fmt(v['Aspect']),
            'BURNCLASS' : burn_class,
            'UTREAT'    : man.desc,
            'USLP_LNG'  : fmt(v['Length'] / 2.0),
            'UGRD_TP'   : fmt(v['UpperTopSlope']),
            'UGRD_BTM'  : fmt(v['UpperBottomSlope']),
            'LTREAT'    : man.desc,
            'LSLP_LNG'  : fmt(v['Length'] / 2.0),
            'LGRD_TP'   : fmt(v['LowerTopSlope']),
            'LGRD_BTM'  : fmt(v['LowerBottomSlope']),
        })

        row_id += 1

    fp.close()
    
    fn1 = _join(export_dir, 'ERMiT_input_{}_log.txt'.format(name))
    fp1 = open(fn1, 'w')
    fp1.write('\n'.join(_log))
    fp1.close()

    fn2 = _join(export_dir, f'ERMiT_input_{name}_meta.txt')
    with open(fn2, 'w') as fp2:
        # header
        fp2.write(f"""\
ERMiT/Disturbed WEPP GIS Hillslope File
=======================================

Created by WeppCloud
Date: {datetime.now():%Y-%m-%d}

Watershed Name: {name}
# of Hillslopes: {watershed.sub_n}
# of Channels: {watershed.chn_n}

Watershed Centroid Location
   Latitude: {watershed.centroid[1]}
   Longitude: {watershed.centroid[0]}

Climate Station
   State: {climatestation_meta.state}
   Station: {climatestation_meta.desc}
   PAR: {climatestation_meta.par}
   Elevation: {climatestation_meta.elevation}
   Latitude: {climatestation_meta.latitude}
   Longitude: {climatestation_meta.longitude}


Column Order & Descriptions
---------------------------
""")

        # your new ordered list of (header, description)
        cols = [
            ('HS_ID',     'WEPP hillslope ID'),
            ('TOPAZ_ID',  'TOPAZ hillslope ID (not used)'),
            ('UNIT_ID',   'Unit ID (empty; read by disturbed)'),
            ('AREA',      'Area in hectares'),
            ('ROWID_',    'Row identifier'),
            ('SOIL_TYPE', 'Soil texture class (4-class; from SSURGO/STATSGO)'),
            ('ROCK_PCT',  'Percent rock in soil'),
            ('VEG_TYPE',  'Vegetation/landuse (undisturbed)'),
            ('ERM_TSLP',  'Top gradient (%) for ERMiT'),
            ('ERM_MSLP',  'Middle gradient (%) for ERMiT'),
            ('ERM_BSLP',  'Bottom gradient (%) for ERMiT'),
            ('SHRUB_PCT', 'Shrub cover (%) for ERMiT'),
            ('GRASS_PCT', 'Grass cover (%) for ERMiT'),
            ('BARE_PCT',  'Bare ground (%) for ERMiT'),
            ('LENGTH',    'Horizontal slope length (m) from ERMiT'),
            ('ASPECT',    'Aspect (°; not used)'),
            ('BURNCLASS', 'Burn class for ERMiT: Unburned, Low, Moderate, High'),
            ('UTREAT',    'Upper treatment (disturbed batch)'),
            ('USLP_LNG',  'Upper slope length (m; disturbed batch)'),
            ('UGRD_TP',   'Upper top gradient (%) (disturbed batch)'),
            ('UGRD_BTM',  'Upper bottom gradient (%) (disturbed batch)'),
            ('LTREAT',    'Lower treatment (disturbed batch)'),
            ('LSLP_LNG',  'Lower slope length (m; disturbed batch)'),
            ('LGRD_TP',   'Lower top gradient (%) (disturbed batch)'),
            ('LGRD_BTM',  'Lower bottom gradient (%) (disturbed batch)'),
        ]

        # write them in order
        for hdr, desc in cols:
            fp2.write(f"{hdr:<10} {desc}\n")

        # now the two slope‐parameter sections
        fp2.write("""

Slope parameters for Disturbed WEPP Batch File
----------------------------------------------
Slope is divided into four segments each 25% of total slope
"U" is for Upper, "L" is for Lower

UTREAT
    - description of management: OldForest, YoungForest, Shrub, Bunchgrass, Sod, LowFire, HighFire, Skid

USLP_LNG
    - length of the upper slope (50% of total slope) in meters

LTREAT
    - description of management: OldForest, YoungForest, Shrub, Bunchgrass, Sod, LowFire, HighFire, Skid

UGRD_TP
    - Upper top slope (%)

UGRD_BTM
    - Upper bottom slope (%)

LGRD_TP
    - Lower top slope (%)

LGRD_BTM
    - Lower bottom slope (%)

LSLP_LNG
    - length of the lower slope (50% of total slope) in meters


Slope parameters for ERMiT WEPP Batch File
------------------------------------------
According to ERMiT documentation the slope is divided into 
3 segments representing the top 10%, middle 80% and bottom 10%.

ERM_TSLP
    - Top slope (%)

ERM_MSLP
    - Middle slope (%)

ERM_BSLP
    - Bottom slope (%)

BURNCLASS
    - Burn class as Unburned, Low, Moderate, High

ROCK_PCT
    - Calculated percent rock from soil file
""")

    zipfn = _join(export_dir, 'ERMiT_input_{}.zip'.format(name))
    zipf = zipfile.ZipFile(zipfn, 'w', zipfile.ZIP_DEFLATED)
    zipf.write(fn, _split(fn)[-1])
    zipf.write(fn1, _split(fn1)[-1])
    zipf.write(fn2, _split(fn2)[-1])
    zipf.close()

    return zipfn


if __name__ == "__main__":
    create_ermit_input('/geodata/weppcloud_runs/054972e3-2d7d-4caf-833a-a73d400b0f39/')

