import os
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
import shutil
import json
import subprocess
from glob import glob

from deprecated import deprecated

from wepppy.nodb.core import *
from wepppy.nodb.mods.ash_transport import Ash
from wepppy.nodb.mods.rhem import RhemPost
from wepppy.all_your_base import isnan, isinf
from wepppy.topo.watershed_abstraction.support import json_to_wgs

from wepppy.topo.peridot.flowpath import PeridotFlowpath, PeridotHillslope, PeridotChannel

@deprecated()
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

    
def legacy_arc_export(wd, verbose=False):

    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    #topaz = Topaz.getInstance(wd)
    watershed = Watershed.getInstance(wd)
    translator = watershed.translator_factory()
    map = ron.map

    ash_out = None
    ash = Ash.tryGetInstance(wd)
    ash_post = AshPost.tryGetInstance(wd)

    if ash_post is not None:
        try:
            ash_out = ash_post.ash_out
        except:
            ash_out = None

    name = ron.name
    export_dir = ron.export_legacy_arc_dir

    if _exists(export_dir):
        shutil.rmtree(export_dir)

    gtiff_dir = _join(export_dir, 'gtiffs')
    topaz_wd = ron.topaz_wd

    os.mkdir(export_dir)
    os.mkdir(gtiff_dir)

    #
    # geotiffs
    #
    arcs = glob(_join(topaz_wd, '*.ARC'))
    for arc in arcs:
        _, basename = _split(arc)
        cmd = ['gdal_translate', '-of', 'GTiff', arc, _join(gtiff_dir, basename.replace('ARC', 'TIF'))]
        if verbose:
            print(cmd)
        subprocess.check_call(cmd)

    #
    # subcatchments
    #
    if verbose:
        print('build subcatchments...', end='')

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

        if isinstance(ss, PeridotHillslope):
            ss = ss.as_dict()

        f['properties']['watershed'] = name
        f['properties']['topaz_id'] = topaz_id
        f['properties']['wepp_id'] = ss['meta']['wepp_id']
        f['properties']['width(m)'] = ss['watershed']['width']
        f['properties']['length(m)'] = ss['watershed']['length']
        area_ha = ss['watershed']['area'] * 0.0001
        f['properties']['area(ha)'] = area_ha
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
                if topaz_id in ash_out:
                    f['properties']['Awat(kg/ha)'] = ash_out[topaz_id]['water_transport (kg/ha)']
                    f['properties']['Awnd(kg/ha)'] = ash_out[topaz_id]['wind_transport (kg/ha)']
                    f['properties']['AshT(kg/ha)'] = ash_out[topaz_id]['ash_transport (kg/ha)']
                    f['properties']['Awat(tonne)'] = ash_out[topaz_id]['water_transport (kg/ha)'] * area_ha / 1000.0
                    f['properties']['Awnd(tonne)'] = ash_out[topaz_id]['wind_transport (kg/ha)'] * area_ha / 1000.0
                    f['properties']['AshT(tonne)'] = ash_out[topaz_id]['ash_transport (kg/ha)'] * area_ha / 1000.0
                    f['properties']['Burnclass'] = ash_out[topaz_id]['burn_class']

        for k, v in f['properties'].items():
            if isnan(v) or isinf(v):
                f['properties'][k] = None

        js['features'][i] = f

    geojson_fn = _join(export_dir, 'subcatchments.json')
    with open(geojson_fn, 'w') as fp:
        json.dump(js, fp, allow_nan=False)

    utm_epsg = f'epsg:{map.srid}'

    if 'crs' not in js:
        s_srs = utm_epsg
    else:
        s_srs = None
    json_to_wgs(geojson_fn, s_srs=s_srs)

    if verbose:
        print('done.')

    cmd = ['ogr2ogr', '-s_srs', utm_epsg, '-t_srs', utm_epsg,
           'subcatchments.shp', 'subcatchments.json']
    if verbose:
        print(cmd)
    subprocess.check_call(cmd, cwd=export_dir)

    assert _exists(_join(export_dir, 'subcatchments.shp')), cmd

    cmd = ['ogr2ogr', '-f', 'KML', '-s_srs', utm_epsg, '-t_srs', utm_epsg,
           'subcatchments.kml', 'subcatchments.json']
    if verbose:
        print(cmd)
    subprocess.check_call(cmd, cwd=export_dir)

    assert _exists(_join(export_dir, 'subcatchments.kml')), cmd

    geojson_fn = _join(export_dir, 'subcatchments.json')
    with open(geojson_fn, 'w') as fp:
        json.dump(js, fp, allow_nan=False)

    if verbose:
        print('done.')

    cmd = ['ogr2ogr', '-s_srs', utm_epsg, '-t_srs', utm_epsg,
           'subcatchments.shp', 'subcatchments.json']
    if verbose:
        print(cmd)
    subprocess.check_call(cmd, cwd=export_dir)

    assert _exists(_join(export_dir, 'subcatchments.shp')), cmd

    cmd = ['ogr2ogr', '-f', 'KML', '-s_srs', utm_epsg, '-t_srs', utm_epsg,
           'subcatchments.kml', 'subcatchments.json']
    if verbose:
        print(cmd)
    subprocess.check_call(cmd, cwd=export_dir)

    assert _exists(_join(export_dir, 'subcatchments.kml')), cmd

#    os.remove(geojson_fn)

    #
    # channels
    #
    if verbose:
        print('build channels...', end='')

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

        if weppout['Contributing Area'] is not None:
            f['properties']['cntrb(ha)'] = weppout['Contributing Area'][topaz_id]['value']

        f['properties']['slope'] = ss['watershed']['slope_scalar']
        f['properties']['aspect'] = ss['watershed']['aspect']

        try:
            f['properties']['Disch(m3)'] = weppout['Discharge Volume'][topaz_id]['value']
            f['properties']['Disch(m3)'] = round(f['properties']['Disch(m3)'], 3)
        except:
            f['properties']['Disch(m3)'] = -9999

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
        except:
            pass

        try:
            f['properties']['soil'] = ss['soil']['desc']
        except:
            pass

        for k, v in f['properties'].items():
            if isnan(v) or isinf(v):
                f['properties'][k] = None

        js['features'][i] = f

    if verbose:
        print('done.')

    geojson_fn = _join(export_dir, 'channels.json')
    json_txt = json.dumps(js, allow_nan=False)
    json_txt = json_txt.replace('NaN', 'null')

    with open(geojson_fn, 'w') as fp:
        fp.write(json_txt)

    cmd = ['ogr2ogr', '-s_srs', 'epsg:%s' % map.srid, '-t_srs', 'epsg:%s' % map.srid,
           'channels.shp', 'channels.json']
    if verbose:
        print(cmd)
    subprocess.check_call(cmd, cwd=export_dir)

    assert _exists(_join(export_dir, 'channels.shp')), cmd

    cmd = ['ogr2ogr', '-f', 'KML', '-s_srs', 'epsg:%s' % map.srid, '-t_srs', 'epsg:%s' % map.srid,
           'channels.kml', 'channels.json']
    if verbose:
        print(cmd)
    subprocess.check_call(cmd, cwd=export_dir)

    assert _exists(_join(export_dir, 'channels.kml')), cmd


@deprecated()
def arc_export(wd, verbose=False):

    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    #topaz = Topaz.getInstance(wd)
    watershed = Watershed.getInstance(wd)
    translator = watershed.translator_factory()
    map = ron.map

    ash_out = None
    ash = Ash.tryGetInstance(wd)
    ash_post = AshPost.tryGetInstance(wd)

    if ash_post is not None:
        try:
            ash_out = ash_post.ash_out
        except:
            ash_out = None

    rhempost = RhemPost.tryGetInstance(wd)

    name = ron.name
    export_dir = ron.export_arc_dir
    gtiff_dir = _join(export_dir, 'gtiffs')
    topaz_wd = ron.topaz_wd

    runid = ron.runid

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
        cmd = ['gdal_translate', '-of', 'GTiff', arc, _join(gtiff_dir, basename.replace('ARC', 'TIF'))]
        if verbose:
            print(cmd)
        subprocess.check_call(cmd)

    #
    # subcatchments
    #
    if verbose:
        print('build subcatchments...', end='')

    sub_json = _join(topaz_wd, 'SUBCATCHMENTS.JSON')
    assert _exists(sub_json)
    with open(sub_json) as fp:
        js = json.load(fp)

    subs_summary = {str(ss['meta']['topaz_id']): ss for ss in ron.subs_summary()}

    weppout = None
    if wepp.has_run:
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

        if isinstance(ss, PeridotHillslope):
            ss = ss.as_dict()

        f['properties']['watershed'] = name
        f['properties']['topaz_id'] = topaz_id
        f['properties']['wepp_id'] = ss['meta']['wepp_id']
        f['properties']['width(m)'] = ss['watershed']['width']
        f['properties']['length(m)'] = ss['watershed']['length']
        area_ha = ss['watershed']['area'] * 0.0001
        f['properties']['area(ha)'] = area_ha
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

        if weppout:
            if weppout['Runoff'] is not None:
                f['properties']['Runoff (mm)'] = weppout['Runoff'][topaz_id]['value']

            if weppout['Subrunoff'] is not None:
                f['properties']['Subrunoff (mm)'] = weppout['Subrunoff'][topaz_id]['value']

            if weppout['Baseflow'] is not None:
                f['properties']['BaseFlow (mm)'] = weppout['Baseflow'][topaz_id]['value']

            if weppout['DepLoss'] is not None:
                f['properties']['Deposition Loss (kg)'] = weppout['DepLoss'][topaz_id]['value']

            if weppout['Soil Loss Density'] is not None:
                f['properties']['Soil Loss (kg/ha)'] = weppout['Soil Loss Density'][topaz_id]['value']

            if weppout['Sediment Deposition Density'] is not None:
                f['properties']['Sediment Deposition (kg/ha)'] = weppout['Sediment Deposition Density'][topaz_id]['value']

            if weppout['Sediment Yield Density'] is not None:
                f['properties']['Sediment Yield (kg/ha)'] = weppout['Sediment Yield Density'][topaz_id]['value']

            if weppout['Total P Density'] is not None:
                f['properties']['Total P (kg/ha)'] = weppout['Total P Density'][topaz_id]['value']

            if weppout['Solub. React. P Density'] is not None:
                f['properties']['Solub. React. P (kg/ha)'] = weppout['Solub. React. P Density'][topaz_id]['value']

            if weppout['Particulate P Density'] is not None:
                f['properties']['Particulate P (kg/ha)'] = weppout['Particulate P Density'][topaz_id]['value']

        if rhempost is not None:
            f['properties']['Avg-Runoff (m^3/yr)'] = rhempost.hill_summaries[topaz_id].annuals['Avg-Runoff (m^3/yr)']
            f['properties']['Avg-Soil-Yield (tonne/yr)'] = rhempost.hill_summaries[topaz_id].annuals['Avg-SY (tonne/yr)']
            f['properties']['Avg-Soil-Loss (tonne/yr)'] = rhempost.hill_summaries[topaz_id].annuals['Avg-Soil-Loss (tonne/yr)']
            f['properties']['Avg. Precipitation (m^3/yr)'] = rhempost.hill_summaries[topaz_id].annuals['Avg. Precipitation (m^3/yr)']

        if ash is not None:
            if ash_out is not None:
                if topaz_id in ash_out:
                    f['properties']['Ash Transport Water (kg/ha)'] = ash_out[topaz_id]['water_transport (kg/ha)']
                    f['properties']['Ash Transport Wind (kg/ha)'] = ash_out[topaz_id]['wind_transport (kg/ha)']
                    f['properties']['Ash Transport (kg/ha)'] = ash_out[topaz_id]['ash_transport (kg/ha)']
                    f['properties']['Ash Transport Water (tonne)'] = ash_out[topaz_id]['water_transport (kg/ha)'] * area_ha / 1000.0
                    f['properties']['Ash Transport Wind (tonne)'] = ash_out[topaz_id]['wind_transport (kg/ha)'] * area_ha / 1000.0
                    f['properties']['Ash Transport (tonne)'] = ash_out[topaz_id]['ash_transport (kg/ha)'] * area_ha / 1000.0
                    f['properties']['Burnclass'] = ash_out[topaz_id]['burn_class']

        for k, v in f['properties'].items():
            if isnan(v) or isinf(v):
                f['properties'][k] = None

        js['features'][i] = f

    geojson_fn = _join(export_dir, 'subcatchments.json')
    with open(geojson_fn, 'w') as fp:
        json.dump(js, fp, allow_nan=False)

    utm_epsg = f'epsg:{map.srid}'

    if 'crs' not in js:
        s_srs = utm_epsg
    else:
        s_srs = None
    json_to_wgs(geojson_fn, s_srs=s_srs)

    if verbose:
        print('done.')

    if _exists(_join(export_dir, f'{runid}.gpkg')):
        os.remove(_join(export_dir, f'{runid}.gpkg'))

    cmd = ['ogr2ogr', '-f', 'GPKG', '-s_srs', utm_epsg, '-t_srs', utm_epsg,
           f'{runid}.gpkg', 'subcatchments.json', '-nln', 'subcatchments']
    if verbose:
        print(cmd)
    subprocess.check_call(cmd, cwd=export_dir)

    assert _exists(_join(export_dir, f'{runid}.gpkg')), cmd


#    os.remove(geojson_fn)

    #
    # channels
    #
    if verbose:
        print('build channels...', end='')

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

        if weppout['Contributing Area'] is not None:
            f['properties']['cntrb(ha)'] = weppout['Contributing Area'][topaz_id]['value']

        f['properties']['slope'] = ss['watershed']['slope_scalar']
        f['properties']['aspect'] = ss['watershed']['aspect']

        try:
            f['properties']['Discharge Volume (m3)'] = weppout['Discharge Volume'][topaz_id]['value']
            f['properties']['Discharge Volume (m3)'] = round(f['properties']['Discharge Volume (m3)'], 3)
        except:
            f['properties']['Discharge Volume (m3)'] = -9999

        try:
            f['properties']['Sediment Yield (tn/h)'] = weppout['Sediment Yield'][topaz_id]['value'] / _area
            f['properties']['Sediment Yield (tn/h)'] = round(f['properties']['Sediment Yield (tn/h)'], 3)
        except:
            f['properties']['SdYd(tn/h)'] = -9999

        try:
            f['properties']['Soil Loss (kg/h)'] = weppout['Soil Loss'][topaz_id]['value'] / _area
            f['properties']['Soil Loss (kg/h)'] = round(f['properties']['Soil Loss (kg/h)'], 3)
        except:
            f['properties']['Soil Loss (kg/h)'] = -9999

        if weppout['Total P Density'] is not None:
            f['properties']['Total P (kg/ha)'] = weppout['Total P Density'][topaz_id]['value']

        if weppout['Solub. React. P Density'] is not None:
            f['properties']['Solub. React. P (kg/ha)'] = weppout['Solub. React. P Density'][topaz_id]['value']

        if weppout['Particulate P Density'] is not None:
            f['properties']['Particulate P (kg/ha)'] = weppout['Particulate P Density'][topaz_id]['value']

        try:
            desc = ss['landuse']['desc']
            f['properties']['landuse'] = desc
        except:
            pass

        try:
            desc = ss['soil']['desc']
            f['properties']['soil'] = desc
        except:
            pass

        for k, v in f['properties'].items():
            if isnan(v) or isinf(v):
                f['properties'][k] = None

        js['features'][i] = f

    if verbose:
        print('done.')

    geojson_fn = _join(export_dir, 'channels.json')
    json_txt = json.dumps(js, allow_nan=False)
    json_txt = json_txt.replace('NaN', 'null')

    with open(geojson_fn, 'w') as fp:
        fp.write(json_txt)

if __name__ == '__main__':
    wd = '/geodata/weppcloud_runs/CurCond_Watershed_1'
    arc_export(wd)
