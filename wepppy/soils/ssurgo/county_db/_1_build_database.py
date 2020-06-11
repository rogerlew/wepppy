import os
from os.path import exists as _exists
import shutil

from wepppy.soils.ssurgo import SurgoSoilCollection, StatsgoSpatial

from wepppy.all_your_base import isint

if __name__ == "__main__":

    assert _exists('dom_mukeys_by_county.csv')
    assert _exists('failed_counties.txt')

    # clean soils directory
    if _exists('soils'):
        shutil.rmtree('soils')

    os.mkdir('soils')

    # read the input table from file
    with open('dom_mukeys_by_county.csv') as fp:
        records = fp.readlines()

    # read the mukeys from input table
    mukeys = []
    for rec in records:
        rec = rec.split(',')

        try:
            mukeys.append(int(rec[-3]))
        except:
            print(rec)

    # build wepp soils 100 at a time to not overload surgo SOAP server
    for i in range(int(len(mukeys)/100)):
        print(i)
        i0 = i*100
        iend = i*100 + 100
        if iend > len(mukeys):
            iend = len(mukeys) - 1

        surgo_c = SurgoSoilCollection(mukeys[i0:iend])
        surgo_c.makeWeppSoils()

        surgo_c.writeWeppSoils('soils', write_logs=True, version='2006.2')

        print(surgo_c.invalidSoils.keys())



    # for invalid soils build statsgo soils
    # first need to determine statsgo mukeys from county centroids
    statsgoSpatial = StatsgoSpatial()
    statsgo_mukeys = set()
    county_lookup = {}
    for rec in records:
        rec = rec.split(',')
        fips = rec[3]
        lng, lat = float(rec[-2]), float(rec[-1])

        try:
            mukey = int(rec[-3])
        except:
            county_lookup[fips] = (None, None, lng, lat)
            continue

        if _exists('soils/{}.sol'.format(mukey)):
            county_lookup[fips] = (mukey, 'surgo', lng, lat)
            continue

        lng = float(rec[-2])
        lat = float(rec[-1])

        s_mukey = statsgoSpatial.identify_mukey_point(lng, lat)
        statsgo_mukeys.add(s_mukey)

        county_lookup[fips] = (s_mukey, 'statsgo', lng, lat)

    statsgo_mukeys = list(statsgo_mukeys)
    statsgo_mukeys = [v for v in statsgo_mukeys if isint(v)]
    print('statsgo mukeys:', statsgo_mukeys)

    # now we can build the statsgo soils 100 at a time
    for i in range(int(len(statsgo_mukeys)/100)):
        print(i)
        i0 = i*100
        iend = i*100 + 100
        if iend > len(statsgo_mukeys):
            iend = len(statsgo_mukeys) - 1

        surgo_c = SurgoSoilCollection(statsgo_mukeys[i0:iend], use_statsgo=True)
        surgo_c.makeWeppSoils()

        surgo_c.writeWeppSoils('soils', write_logs=True, version='2006.2')

        print(set(statsgo_mukeys[i0:iend]).difference(surgo_c.invalidSoils.keys()))
        print(set(surgo_c.invalidSoils.keys()))

    ## build soil lookup table for database
    #for s_mukey in invalid_statsgo_mukeys:
    #    for fips in county_lookup:
    #        if county_lookup[fips] == s_mukey:
    #            county_lookup[fips] = None, None, None, None

    with open('soil_lookup.csv', 'w') as fp:
        fp.write('AFFGEOID,MUKEY,source,lng,lat\n')

        for fips, item in county_lookup.items():
            mukey, src, lng, lat = item

            if not _exists('soils/{}.sol'.format(mukey)):
                mukey = None
                src = None

            fp.write('{},{},{},{},{}\n'.format(fips, mukey, src, lng, lat))

        with open('failed_counties.txt') as fpe:
            failed_counties = fpe.readlines()
            failed_counties = [fips.strip() for fips in failed_counties]

        #for fips in failed_counties:
       #     fp.write('{},{},{},{},{}\n'.format(fips, None, None, None, None))
