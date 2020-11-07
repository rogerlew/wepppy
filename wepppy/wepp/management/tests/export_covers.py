import csv
from wepppy.wepp.management import load_map, get_management, IniLoopCropland

db = None  # 'lu10v5ua' #'esdac' # 'rred' # 'disturbed
d = load_map(db)

fp = open('tests/weppcloud_managements.csv', 'w')
wtr = csv.writer(fp)

wtr.writerow(['key', 'desc', 'man', 'cancov', 'inrcov', 'rilcov'])

for k in d:
    m = get_management(k, _map=db)
    # Ini.loop.landuse.cropland (6.6 inrcov), (9.3 rilcov)

    assert len(m.inis) == 1
    assert m.inis[0].landuse == 1
    assert isinstance(m.inis[0].data, IniLoopCropland)
    cancov, inrcov, rilcov = m.inis[0].data.cancov, m.inis[0].data.inrcov, m.inis[0].data.rilcov
    man_fn = d[k]['ManagementFile']

    print('{},{},{},{},{}'.format(k, m.desc, man_fn, cancov, inrcov, rilcov))

    wtr.writerow([k, m.desc, cancov, inrcov, rilcov])

fp.close()
