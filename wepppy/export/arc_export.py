import os
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
import shutil
import json
from subprocess import Popen, PIPE
from glob import glob

from wepppy.nodb import Ron, Wepp, Topaz


def arc_export(wd):
    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    topaz = Topaz.getInstance(wd)
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

    subs_summary = {str(ss['meta']['topaz_id']):ss for ss in ron.subs_summary()}

    weppout= {}
    weppout['Runoff'] = wepp.query_sub_val('Runoff')
    weppout['Subrunoff'] = wepp.query_sub_val('Subrunoff')
    weppout['Baseflow'] = wepp.query_sub_val('Baseflow')
    weppout['DepLoss'] = wepp.query_sub_val('DepLoss')
    weppout['Total P Density'] = wepp.query_sub_val('Total P Density')

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

        f['properties']['Runoff(mm)'] = weppout['Runoff'][topaz_id]['value']
        f['properties']['Subrun(mm)'] = weppout['Subrunoff'][topaz_id]['value']
        f['properties']['BaseF(mm)'] = weppout['Baseflow'][topaz_id]['value']
        f['properties']['DepLos(mm)'] = weppout['DepLoss'][topaz_id]['value']
        f['properties']['TP(kg/ha)'] = weppout['Total P Density'][topaz_id]['value']

        js['features'][i] = f

    geojson_fn = _join(export_dir, 'subcatchments.json')
    with open(geojson_fn, 'w') as fp:
        json.dump(js, fp)

    print(topaz.utmproj4)
    p = Popen(['ogr2ogr', '-s_srs', topaz.utmproj4, '-t_srs', topaz.utmproj4,
               'subcatchments.shp', 'subcatchments.json'],
              stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=export_dir)
    p.wait()

    assert _exists(_join(export_dir, 'subcatchments.shp'))
    os.remove(geojson_fn)

    #
    # channels
    #

    sub_json = _join(topaz_wd, 'CHANNELS.JSON')
    assert _exists(sub_json)
    with open(sub_json) as fp:
        js = json.load(fp)

    chns_summary = {str(ss['meta']['topaz_id']):ss for ss in ron.chns_summary()}

    for i, f in enumerate(js['features']):
        topaz_id = str(f['properties']['TopazID'])
        ss = chns_summary[topaz_id]

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

        js['features'][i] = f

    geojson_fn = _join(export_dir, 'channels.json')
    with open(geojson_fn, 'w') as fp:
        json.dump(js, fp)

    p = Popen(['ogr2ogr', '-s_srs', topaz.utmproj4, '-t_srs', topaz.utmproj4,
               'channels.shp', 'channels.json'],
              stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=export_dir)
    p.wait()

    assert _exists(_join(export_dir, 'channels.shp'))
    os.remove(geojson_fn)


if __name__ == '__main__':
    wd = '/home/weppdev/PycharmProjects/wepppy/wepppy/validation/Watershed_1'
    arc_export(wd)