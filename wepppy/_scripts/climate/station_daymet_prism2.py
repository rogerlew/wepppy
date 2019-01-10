import random

import numpy as np

from wepppy.climates.cligen import CligenStationsManager, ClimateFile, Cligen
from wepppy.climates import metquery_client

days_in_mo = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])

stationMgr = CligenStationsManager()

_rowfmt = lambda x : '\t'.join(['%0.2f' % v for v in x])

stations = stationMgr.stations
random.shuffle(stations)

fp = open('climate_ppt_comparison.csv', 'w')
fp.write('par,month,lng,lat,station_ppt,prism_ppt,daymet_ppt\n')

for i, stationMeta in enumerate(stations):
    print('{} of {}'.format(i+1, len(stations)))
    if 'ak' in stationMeta.par.lower():
        continue

    try:
        print('Par:', stationMeta.par)
        par = stationMeta.par
        station = stationMeta.get_station()
        station_ppts = station.ppts * station.nwds

        lat, lng = stationMeta.latitude, stationMeta.longitude
        daymet_ppts = metquery_client.get_daymet_prcp_mean(lng, lat, units='inch/day') * days_in_mo
        prism_ppts = metquery_client.get_prism_monthly_ppt(lng, lat, units='inch')
        print('Station P', _rowfmt(station_ppts))
        print('PRISM   P', _rowfmt(prism_ppts))
        print('Daymet  P', _rowfmt(daymet_ppts))

        for j in range(12):
            fp.write('{},{},{},{},{},{},{}\n'.format(par, j+1, lng, lat, station_ppts[j], prism_ppts[j], daymet_ppts[j]))
    except:
        pass

fp.close()
