import os

from os.path import exists as _exists

from wepppy.climates.cligen import CligenStationsManager
from wepppy.climates.cligen.ghcn_daily import find_ghcn_id

if __name__ == '__main__':

    os.chdir('ghcn_daily')

    for _db in ['legacy', '2015', 'au', 'ghcn']:
        print(_db)

        stations_manager = CligenStationsManager(version=_db)

        total_stations = len(stations_manager.stations)
        found_stations = 0
        for station_meta in stations_manager.stations:
            station_id = station_meta.id

            if _exists(f'{station_id}.ghcn_daily.cli'):
                continue

            print(station_id, 
                  station_meta.build_ghcn_daily_climate(f'{station_id}.prn', f'{station_id}.ghcn_daily.cli'))

