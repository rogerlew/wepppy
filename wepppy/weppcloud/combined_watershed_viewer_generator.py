import json
from os.path import join as _join

import numpy as np

from wepppy.nodb import Ron, Wepp
from wepppy.weppcloud.utils.helpers import get_wd

def combined_watershed_viewer_generator(runids, title, units=None, varopts=None, varname=None, asjson=False):
    if units is None:
        units = 'SI'

    if varname is None:
        varname = 'loss'

    if varopts is None:
        varopts = {}

    runoff = varopts.get('runoff', (0.1, 10)[units == 'SI'])  # in, mm
    subrunoff = varopts.get('subrunoff', (0.1, 10)[units == 'SI'])  # in, mm
    baseflow = varopts.get('baseflow', (0.1, 10)[units == 'SI'])  # in, mm
    loss = varopts.get('loss', (0.1, 10)[units == 'SI'])  # in, mm
    phosphorus = varopts.get('phosphorus', (0.1, 10)[units == 'SI'])  # in, mm

    ws = []
    extents = None
    center_lat = None
    center_lng = None
    zoom = None

    has_phos = True

    for i, runid in enumerate(runids):
        if runid.endswith('/'):
            runid = runid[:-1]

        wd = get_wd(runid)
        try:
            ron = Ron.getInstance(wd)
            wepp = Wepp.getInstance(wd)
        except:
            raise Exception('Error acquiring nodb instances from ' + wd)

        has_phos = has_phos and wepp.phosphorus_opts.isvalid

        if i == 0:
            extents = ron.map.extent
            zoom = ron.map.zoom
        else:
            _l, _b, _r, _t = ron.map.extent
            l, b, r, t = extents

            if _l < l:
                extents[0] = l

            if _b < b:
                extents[1] = b

            if _r > r:
                extents[2] = r

            if _t > t:
                extents[3] = t

            if ron.map.zoom < zoom:
                zoom = ron.map.zoom

        ws.append(dict(runid=runid, cfg=ron.config_stem))

    if extents is not None:
        center_lng = float(np.mean([extents[0], extents[2]]))
        center_lat = float(np.mean([extents[1], extents[3]]))

    if zoom is not None:
        zoom -= 1

    phosphorus = varopts.get('phosphorus', (0.1, 10)[units == 'SI'])  # in, mm

    phos_opts = ('', ',"phosphorus":{phosphorus}')[has_phos]

    _url = '/weppcloud/combined_ws_viewer/?zoom={zoom}&center=[{center_lat},{center_lng}]&' \
           'ws={ws}&varopts={{"runoff":{runoff},"subrunoff":{subrunoff},"baseflow":{baseflow}' \
           '{phos_opts},"loss":{loss}}}&varname={varname}&title={title}&units={units}'


    url = None
    if center_lng is not None and \
            center_lat is not None and \
            zoom is not None and \
            len(ws) > 0:
        url = _url.format(center_lat=center_lat, center_lng=center_lng,
                          zoom=zoom, ws=json.dumps(ws, separators=(',', ':'), allow_nan=False), title=title,
                          runoff=runoff, subrunoff=subrunoff, baseflow=baseflow, loss=loss, varname=varname, units=units,
                          phos_opts=phos_opts.format(phosphorus=phosphorus))

    if asjson:
        varopts = dict(runoff=runoff,
                       subrunoff=subrunoff,
                       baseflow=baseflow,
                       loss=loss)

        if has_phos:
            varopts['phosphorus'] = phosphorus

        return json.dumps(dict(zoom=zoom, center=[center_lat, center_lng], ws=ws,
                               title=title, varopts=varopts, varname=varname, units=units),
                          separators=(',', ':'), allow_nan=False)

    return url
