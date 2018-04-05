# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from wepppy.climates.cligen import (
    CligenStationsManager,
    Cligen,
    ClimateFile
)

cligenStations = CligenStationsManager()
cligenStations.order_by_distance_to_location([-120.0, 46.0 ])
#for station in cligenStations.stations:
#    print repr(station)
#    raw_input()
station = cligenStations.get_closest_station([-117.654, 46.5])
print(station.years)
#cligen = Cligen(station, 'tests/wd')
#cligen.run(100)

cligen = Cligen(station, 'wd', '5.3')
cligen.run_multiple_year(5)

cli = ClimateFile('wd/wepp.cli')
print(cli.calc_monthlies())
