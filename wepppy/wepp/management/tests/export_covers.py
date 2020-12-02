import csv
from wepppy.wepp.management import load_map, get_management, IniLoopCropland

db = 'disturbed'  # None  # 'lu10v5ua' #'esdac' # 'rred' # 'disturbed
d = load_map(db)

fp = open('%s_weppcloud_managements.csv' % str(db), 'w')
wtr = csv.writer(fp)

hdr = ['key', 'desc', 'man',
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
       'plant.data.oratea', 'plant.data.orater', 'plant.data.otemp', 'plant.data.pltol']

wtr.writerow([v.replace('.data', '') for v in  hdr])

for k in d:
    m = get_management(k, _map=db)
    # Ini.loop.landuse.cropland (6.6 inrcov), (9.3 rilcov)

    assert len(m.inis) == 1
    assert m.inis[0].landuse == 1
    assert isinstance(m.inis[0].data, IniLoopCropland)
    cancov, inrcov, rilcov = m.inis[0].data.cancov, m.inis[0].data.inrcov, m.inis[0].data.rilcov
    man_fn = d[k]['ManagementFile']

    row = [('{%s}' % v).format(key=k, desc=m.desc, man=man_fn, 
                               ini=m.inis[0],
                               plant=m.plants[0]) for v in hdr]
    print(row)

    wtr.writerow(row)

fp.close()
