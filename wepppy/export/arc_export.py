import os
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
import shutil
import json
import sys
from subprocess import Popen, PIPE
from glob import glob
import math

from wepppy.all_your_base import isnan, isinf
from wepppy.nodb import Ron, Wepp, Topaz, Watershed, Ash, AshPost


def has_arc_export(wd):
    ron = Ron.getInstance(wd)
    name = ron.name
    export_dir = ron.export_arc_dir
    topaz_wd = ron.topaz_wd

    sub_json = _join(topaz_wd, 'SUBCATCHMENTS.JSON')
    try:
        assert _exists(sub_json)
        assert _exists(_join(export_dir, 'subcatchments.shp'))
        assert _exists(_join(export_dir, 'channels.shp'))
    except:
        return False

    return True


def arc_export(wd):
    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    topaz = Topaz.getInstance(wd)
    watershed = Watershed.getInstance(wd)
    translator = watershed.translator_factory()

    ash_out = None
    try:
        ash = Ash.getInstance(wd)
        ash_post = AshPost.getInstance(wd)
    except FileNotFoundError:
        ash = ash_post = ash_out = None

    if ash_post is not None:
        try:
            ash_out = ash_post.ash_out
        except:
            ash_out = None

    name = ron.name
    export_dir = ron.export_arc_dir
    gtiff_dir = _join(export_dir, 'gtiffs')
    topaz_wd = ron.topaz_wd

    if _exists(export_dir):
        shutil.rmtree(export_dir)

    os.mkdir(export_dir)
    os.mkdir(gtiff_dir)

    #
    # geotiffs
    #
    arcs = glob(_join(topaz_wd, '*.ARC'))
    for arc in arcs:
        _, basename = _split(arc)

        p = Popen(['gdal_translate', '-of', 'GTiff', arc, _join(gtiff_dir, basename.replace('ARC', 'TIF'))],
                  stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()


    #
    # subcatchments
    #

    sub_json = _join(topaz_wd, 'SUBCATCHMENTS.JSON')
    assert _exists(sub_json)
    with open(sub_json) as fp:
        js = json.load(fp)

    subs_summary = {str(ss['meta']['topaz_id']): ss for ss in ron.subs_summary()}

    weppout= {}
    weppout['Runoff'] = wepp.query_sub_val('Runoff')
    weppout['Subrunoff'] = wepp.query_sub_val('Subrunoff')
    weppout['Baseflow'] = wepp.query_sub_val('Baseflow')
    weppout['DepLoss'] = wepp.query_sub_val('DepLoss')
    weppout['Total P Density'] = wepp.query_sub_val('Total P Density')
    weppout['Solub. React. P Density'] = wepp.query_sub_val('Solub. React. P Density')
    weppout['Particulate P Density'] = wepp.query_sub_val('Particulate P Density')

    weppout['Soil Loss Density'] = wepp.query_sub_val('Soil Loss Density')
    weppout['Sediment Deposition Density'] = wepp.query_sub_val('Sediment Deposition Density')
    weppout['Sediment Yield Density'] = wepp.query_sub_val('Sediment Yield Density')

    for i, f in enumerate(js['features']):
        topaz_id = str(f['properties']['TopazID'])
        ss = subs_summary[topaz_id]

        f['properties']['watershed'] = name
        f['properties']['topaz_id'] = topaz_id
        f['properties']['wepp_id'] = ss['meta']['wepp_id']
        f['properties']['width(m)'] = ss['watershed']['width']
        f['properties']['length(m)'] = ss['watershed']['length']
        f['properties']['area(ha)'] = ss['watershed']['area'] * 0.0001
        f['properties']['slope'] = ss['watershed']['slope_scalar']
        f['properties']['aspect'] = ss['watershed']['aspect']

        try:
            f['properties']['landuse'] = ss['landuse']['desc']
        except KeyError:
            pass

        try:
            f['properties']['soil'] = ss['soil']['desc']
        except KeyError:
            pass

        if weppout['Runoff'] is not None:
            f['properties']['Runoff(mm)'] = weppout['Runoff'][topaz_id]['value']

        if weppout['Subrunoff'] is not None:
            f['properties']['Subrun(mm)'] = weppout['Subrunoff'][topaz_id]['value']

        if weppout['Baseflow'] is not None:
            f['properties']['BaseF(mm)'] = weppout['Baseflow'][topaz_id]['value']

        if weppout['DepLoss'] is not None:
            f['properties']['DepLos(kg)'] = weppout['DepLoss'][topaz_id]['value']

        if weppout['Soil Loss Density'] is not None:
            f['properties']['SoLs(kg/ha)'] = weppout['Soil Loss Density'][topaz_id]['value']

        if weppout['Sediment Deposition Density'] is not None:
            f['properties']['SdDp(kg/ha)'] = weppout['Sediment Deposition Density'][topaz_id]['value']

        if weppout['Sediment Yield Density'] is not None:
            f['properties']['SdYd(kg/ha)'] = weppout['Sediment Yield Density'][topaz_id]['value']

        if weppout['Total P Density'] is not None:
            f['properties']['TP(kg/ha)'] = weppout['Total P Density'][topaz_id]['value']

        if weppout['Solub. React. P Density'] is not None:
            f['properties']['SRP(kg/ha)'] = weppout['Solub. React. P Density'][topaz_id]['value']

        if weppout['Particulate P Density'] is not None:
            f['properties']['PP(kg/ha)'] = weppout['Particulate P Density'][topaz_id]['value']

        if ash is not None:
            if ash_out is not None:
                f['properties']['Awat(kg/ha)'] = ash_out[topaz_id]['water_transport (kg/ha)']
                f['properties']['Awnd(kg/ha)'] = ash_out[topaz_id]['wind_transport (kg/ha)']
                f['properties']['AshT(kg/ha)'] = ash_out[topaz_id]['ash_transport (kg/ha)']
                f['properties']['Burnclass'] = ash_out[topaz_id]['burnclass']

        for k, v in f['properties'].items():
            if isnan(v) or isinf(v):
                f['properties'][k] = None

        js['features'][i] = f

    geojson_fn = _join(export_dir, 'subcatchments.json')
    with open(geojson_fn, 'w') as fp:
        json.dump(js, fp, allow_nan=False)

    cmd = ['ogr2ogr', '-s_srs', topaz.utmproj4, '-t_srs', topaz.utmproj4,
           'subcatchments.shp', 'subcatchments.json']
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=export_dir)
    p.wait()

    assert _exists(_join(export_dir, 'subcatchments.shp')), cmd

    cmd = ['ogr2ogr', '-f', 'KML', '-s_srs', topaz.utmproj4, '-t_srs', topaz.utmproj4,
           'subcatchments.kml', 'subcatchments.json']
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=export_dir)
    p.wait()

    assert _exists(_join(export_dir, 'subcatchments.kml')), cmd

#    os.remove(geojson_fn)

    #
    # channels
    #

    sub_json = _join(topaz_wd, 'CHANNELS.JSON')
    assert _exists(sub_json)
    with open(sub_json) as fp:
        js = json.load(fp)

    # Discharge Volume
    # Sediment Yield
    # Soil Loss
    # SRP
    # PP
    # TP

    chns_summary = {str(ss['meta']['topaz_id']): ss for ss in ron.chns_summary()}

    weppout= {}
    weppout['Discharge Volume'] = wepp.query_chn_val('Discharge Volume')
    weppout['Sediment Yield'] = wepp.query_chn_val('Sediment Yield')
    weppout['Soil Loss'] = wepp.query_chn_val('Soil Loss')
    weppout['Total P Density'] = wepp.query_chn_val('Total P Density')
    weppout['Solub. React. P Density'] = wepp.query_chn_val('Solub. React. P Density')
    weppout['Particulate P Density'] = wepp.query_chn_val('Particulate P Density')
    weppout['Contributing Area'] = wepp.query_chn_val('Contributing Area')

    for i, f in enumerate(js['features']):
        topaz_id = str(f['properties']['TopazID'])
        ss = chns_summary[topaz_id]
        chn_id = translator.chn_enum(top=topaz_id)
        _area = ss['watershed']['area'] * 0.0001

        f['properties']['watershed'] = name
        f['properties']['topaz_id'] = topaz_id
        f['properties']['chn_id'] = chn_id
        f['properties']['wepp_id'] = ss['meta']['wepp_id']
        f['properties']['width(m)'] = ss['watershed']['width']
        f['properties']['length(m)'] = ss['watershed']['length']
        f['properties']['area(ha)'] = _area
        f['properties']['cntrb(ha)'] = weppout['Contributing Area'][topaz_id]['value']
        f['properties']['slope'] = ss['watershed']['slope_scalar']
        f['properties']['aspect'] = ss['watershed']['aspect']

        try:
            f['properties']['Dis(m3/ha)'] = weppout['Discharge Volume'][topaz_id]['value'] / _area
            f['properties']['Dis(m3/ha)'] = round(f['properties']['Dis(m3/ha)'], 3)
        except:
            f['properties']['Dis(m3/ha)'] = -9999

        try:
            f['properties']['SdYd(tn/h)'] = weppout['Sediment Yield'][topaz_id]['value'] / _area
            f['properties']['SdYd(tn/h)'] = round(f['properties']['SdYd(tn/h)'], 3)
        except:
            f['properties']['SdYd(tn/h)'] = -9999

        try:
            f['properties']['SlLs(kg/h)'] = weppout['Soil Loss'][topaz_id]['value'] / _area
            f['properties']['SlLs(kg/h)'] = round(f['properties']['SlLs(kg/h)'], 3)
        except:
            f['properties']['SlLs(kg/h)'] = -9999

        if weppout['Total P Density'] is not None:
            f['properties']['TP(kg/ha)'] = weppout['Total P Density'][topaz_id]['value']

        if weppout['Solub. React. P Density'] is not None:
            f['properties']['SRP(kg/ha)'] = weppout['Solub. React. P Density'][topaz_id]['value']

        if weppout['Particulate P Density'] is not None:
            f['properties']['PP(kg/ha)'] = weppout['Particulate P Density'][topaz_id]['value']

        try:
            f['properties']['landuse'] = ss['landuse']['desc']
        except KeyError:
            pass

        try:
            f['properties']['soil'] = ss['soil']['desc']
        except KeyError:
            pass

        for k, v in f['properties'].items():
            if isnan(v) or isinf(v):
                f['properties'][k] = None

        js['features'][i] = f

    geojson_fn = _join(export_dir, 'channels.json')
    json_txt = json.dumps(js, allow_nan=False)
    json_txt = json_txt.replace('NaN', 'null')

    with open(geojson_fn, 'w') as fp:
        fp.write(json_txt)

    cmd = ['ogr2ogr', '-s_srs', topaz.utmproj4, '-t_srs', topaz.utmproj4,
           'channels.shp', 'channels.json']
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=export_dir)
    p.wait()
    stdout, stderr = p.communicate()

    assert _exists(_join(export_dir, 'channels.shp')), cmd

    cmd = ['ogr2ogr', '-f', 'KML', '-s_srs', topaz.utmproj4, '-t_srs', topaz.utmproj4,
           'channels.kml', 'channels.json']
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=export_dir)
    p.wait()

    assert _exists(_join(export_dir, 'channels.kml')), cmd

#    os.remove(geojson_fn)


if __name__ == '__main__':
    wd = '/geodata/weppcloud_runs/CurCond_Watershed_1'
    arc_export(wd)