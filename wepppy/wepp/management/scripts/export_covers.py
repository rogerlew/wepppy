import csv
from wepppy.wepp.management import load_map, get_management, IniLoopCropland
from wepppy.nodb.mods.disturbed import read_disturbed_land_soil_lookup

import os
import json

_thisdir = os.path.dirname(os.path.abspath(__file__))
os.chdir(_thisdir)

db = 'disturbed'  # None  # 'lu10v5ua' #'esdac' # 'rred' # 'disturbed
d = load_map(db)

fp = open('%s_weppcloud_managements.csv' % str(db), 'w')
wtr = csv.writer(fp)

hdr = ['key', 'desc', 'man', 'disturbed_class',
       'ini.data.bdtill', 'ini.data.cancov', 'ini.data.daydis', 'ini.data.dsharv', 'ini.data.frdp', 
       'ini.data.inrcov', 'ini.data.iresd', 'ini.data.imngmt', 'ini.data.rfcum', 'ini.data.rhinit',
       'ini.data.rilcov', 'ini.data.rrinit', 'ini.data.rspace', 'ini.data.rtyp', 'ini.data.snodpy',
       'ini.data.thdp', 'ini.data.tillay1', 'ini.data.tillay2', 'ini.data.width', 'ini.data.sumrtm',
       'ini.data.sumsrm',
       'plant.data.bb', 'plant.data.bbb', 'plant.data.beinp', 'plant.data.btemp', 'plant.data.cf', 
       'plant.data.crit', 'plant.data.critvm', 'plant.data.cuthgt', 'plant.data.decfct', 'plant.data.diam', 
       'plant.data.dlai', 'plant.data.dropfc', 'plant.data.extnct', 'plant.data.fact', 'plant.data.flivmx', 
       'plant.data.gddmax', 'plant.data.hi', 'plant.data.hmax',
       'plant.data.mfocod',
       'plant.data.oratea', 'plant.data.orater', 'plant.data.otemp', 'plant.data.pltol',
       'plant.data.pltsp', 'plant.data.rdmax', 'plant.data.rsr', 'plant.data.rtmmax', 
       'plant.data.spriod', 'plant.data.tmpmax', 'plant.data.tmpmin',
       'plant.data.xmxlai', 'plant.data.yld']

wtr.writerow([v.replace('.data', '') for v in  hdr])

man_d = {}
for k in d:
    m = get_management(k, _map=db)
    # Ini.loop.landuse.cropland (6.6 inrcov), (9.3 rilcov)

    assert len(m.inis) == 1
    assert m.inis[0].landuse == 1
    assert isinstance(m.inis[0].data, IniLoopCropland)
    cancov, inrcov, rilcov = m.inis[0].data.cancov, m.inis[0].data.inrcov, m.inis[0].data.rilcov
    man_fn = d[k]['ManagementFile']
    disturbed_class = d[k].get('DisturbedClass', '-')

    row = [('{%s}' % v).format(key=k, desc=m.desc, man=man_fn, 
                               disturbed_class=disturbed_class,
                               ini=m.inis[0],
                               plant=m.plants[0]) for v in hdr]

    man_d[disturbed_class] = dict(zip(hdr, row))
    wtr.writerow(row)

fp.close()

landsoil_lookup_fn = '/workdir/wepppy/wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv'
landsoil_lookup = read_disturbed_land_soil_lookup(landsoil_lookup_fn)

extended_landsoil_lookup = 'extended_disturbed_land_soil_lookup.csv'

wtr = None
with open(extended_landsoil_lookup, 'w') as f:
    for (texid, disturbed_class), _d in landsoil_lookup.items():
        if disturbed_class not in man_d:
            print(f'No management found for {disturbed_class} in man_d')
            continue

        _d.update(man_d[disturbed_class])

        sev_enum = 0
        disturbed_class = _d.get('luse', '')
        if 'high sev' in disturbed_class:
            sev_enum = 4
        elif 'moderate sev' in disturbed_class:
            sev_enum = 3
        elif 'low sev' in disturbed_class:
            sev_enum = 2
        elif 'prescribed' in disturbed_class:
            sev_enum = 1

        luse = f'{disturbed_class}'

        if 'forest' in luse:
            luse = 'forest'
        elif 'grass' in luse and 'short' not in luse:
            luse = 'tall grass'
        elif 'shrub' in luse:
            luse = 'shrub'

        del _d['luse']

        _d = {'sev_enum': sev_enum,  'landuse': luse, 'disturbed_class': disturbed_class, **_d}

        _d['plant.data.rdmax'] = _d['rdmax']
        del _d['rdmax']

        _d['plant.data.xmxlai'] = _d['xmxlai']
        del _d['xmxlai']


        if wtr is None:
            wtr = csv.DictWriter(f, fieldnames=_d.keys())
            wtr.writeheader()

        wtr.writerow(_d)