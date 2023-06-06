from glob import glob
import json
from os.path import exists as _exists
from os.path import join as _join

from wepppy.export import arc_export

weppcloud_runs_dir = '/geodata/weppcloud_runs'

proj_fns = glob('/workdir/wepppy/wepppy/weppcloud/static/mods/lt/results/*.json')


for fn in proj_fns:
    with open(fn) as fp:
        obj = json.load(fp)

        ws = obj['ws']

        for proj in ws:
            runid = proj['runid']
            wd = _join(weppcloud_runs_dir, runid)
            if _exists(wd):
                if not _exists(_join(wd, 'export/arcmap/subcatchments.shp')):
                    arc_export(wd)

