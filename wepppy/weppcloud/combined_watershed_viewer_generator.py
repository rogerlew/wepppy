"""Compatible collection URLs and read-only metadata for the Deck.gl viewer."""
import json
from urllib.parse import urlencode

from wepppy.nodb.core import Ron, Watershed, Wepp
from wepppy.weppcloud.utils.helpers import get_wd

VARIABLES = ('runoff', 'subrunoff', 'baseflow', 'loss', 'phosphorus')


def collection_metadata(runids, *, include_ids=False):
    runs = []
    extent = None
    zoom = None
    for runid in dict.fromkeys(runids):
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        if ron.map is None or not ron.map.extent:
            raise ValueError(f'{runid}: map extent is not ready')
        bounds = list(ron.map.extent)
        if extent is None:
            extent = bounds
        else:
            extent = [min(extent[0], bounds[0]), min(extent[1], bounds[1]),
                      max(extent[2], bounds[2]), max(extent[3], bounds[3])]
        zoom = ron.map.zoom if zoom is None else min(zoom, ron.map.zoom)
        wepp = Wepp.getInstance(wd)
        item = dict(runid=runid, cfg=ron.config_stem,
                    phosphorus=bool(wepp.phosphorus_opts and wepp.phosphorus_opts.isvalid))
        if include_ids:
            watershed = Watershed.getInstance(wd)
            if not watershed.subs_summary:
                raise ValueError(f'{runid}: hillslope identifiers are not ready')
            translator = watershed.translator_factory()
            item['weppIds'] = {str(top): int(translator.wepp(top=int(top)))
                               for top in watershed.subs_summary}
        runs.append(item)
    return dict(ws=runs, center=None if extent is None else [
        (extent[1] + extent[3]) / 2, (extent[0] + extent[2]) / 2],
        zoom=None if zoom is None else max(0, zoom - 1))


def combined_watershed_viewer_generator(runids, title, units=None, varopts=None,
                                        varname=None, asjson=False):
    units = units or 'SI'
    metadata = collection_metadata([item.rstrip('/') for item in runids])
    if not metadata['ws']:
        return json.dumps(dict(metadata, title=title)) if asjson else None
    default = 10 if units == 'SI' else 0.1
    values = {key: (varopts or {}).get(key, default) for key in VARIABLES}
    if not all(run['phosphorus'] for run in metadata['ws']):
        values.pop('phosphorus')
    payload = dict(metadata, ws=[dict(runid=r['runid'], cfg=r['cfg']) for r in metadata['ws']],
                   title=title, units=units, varopts=values, varname=varname or 'loss')
    if asjson:
        return json.dumps(payload, separators=(',', ':'), allow_nan=False)
    return '/weppcloud/combined_ws_viewer/?' + urlencode({
        key: json.dumps(value, separators=(',', ':'), allow_nan=False)
        if isinstance(value, (list, dict)) else value
        for key, value in payload.items()
    })
