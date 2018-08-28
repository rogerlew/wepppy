import random

import numpy as np

from wepppy.climates.cligen import CligenStationsManager, ClimateFile, Cligen
from wepppy.climates import metquery_client
from wepppy.climates import cligen_client as cc

days_in_mo = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])

stationMgr = CligenStationsManager()

_rowfmt = lambda x : '\t'.join(['%0.2f' % v for v in x])

stations = stationMgr.stations
random.shuffle(stations)

fp = open('climate_ppt_comparison.csv', 'w')
fp.write('par,month,lng,lat,station_ppt,prism_ppt,daymet_ppt\n')

fp2 = open('climate_ppt_intensity_comparison.csv', 'w')
fp2.write('par,lng,lat,intensity,climate,value\n')


for i, stationMeta in enumerate(stations):
#    print('{} of {}'.format(i+1, len(stations)))
    if 'ak' in stationMeta.par.lower():
        continue

    par = stationMeta.par
    station = stationMeta.get_station()
    station_ppts = station.ppts * station.nwds

    intpar =  int(''.join(v for v in stationMeta.par if v in '0123456789'))
    lat, lng = stationMeta.latitude, stationMeta.longitude

    if lng < -120.43 or lng > -119.74 or lat < 38.68 or lat > 39.47:
        continue
    print('Par:', stationMeta.par)
    print(stationMeta.longitude, stationMeta.latitude, stationMeta.desc)

    intensities = {}

    result = cc.observed_daymet(intpar, 1980, 2016, lng, lat, returnjson=True)
    par_fn, cli_fn, monthlies = cc.unpack_json_result(result, 'daymet')

    cli = ClimateFile(cli_fn)
    monthlies = cli.calc_monthlies()
    daymet_ppts = monthlies['ppts']
    intensities['daymet'] = cli.calc_intensity()

    result = cc.fetch_multiple_year(intpar, 26)
    par_fn, cli_fn, monthlies = cc.unpack_json_result(result, 'station')

    cli = ClimateFile(cli_fn)
    monthlies = cli.calc_monthlies()
    station_ppts = monthlies['ppts']
    intensities['station'] = cli.calc_intensity()

    # daymet_ppts = metquery_client.get_daymet_prcp_mean(lng, lat, units='inch/day') * days_in_mo
    daymet_ppts = monthlies['ppts']
    prism_ppts = metquery_client.get_prism_monthly_ppt(lng, lat, units='inch')
#    print('Station P', _rowfmt(station_ppts))
#    print('PRISM   P', _rowfmt(prism_ppts))
#    print('Daymet  P', _rowfmt(daymet_ppts))

    for j in range(12):
        fp.write('{},{},{},{},{},{},{}\n'.format(par, j + 1, lng, lat, station_ppts[j], prism_ppts[j], daymet_ppts[j]))

    for cli in intensities:
        for inte in intensities[cli]:
            value = intensities[cli][inte]
            fp2.write('{},{},{},{},{},{}\n'.format(par, lng, lat, inte, cli, value))

fp.close()
fp2.close()