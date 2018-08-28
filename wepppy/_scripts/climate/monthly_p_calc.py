import random
from wepppy.climates.cligen import CligenStationsManager, ClimateFile, Cligen

stationMgr = CligenStationsManager()

_rowfmt = lambda x : '\t'.join(['%0.2f' % v for v in x])

stations = stationMgr.stations
random.shuffle(stations)
for stationMeta in stations[:100]:
    print('Par:', stationMeta.par)
    par = stationMeta.par
    station = stationMeta.get_station()
    print('Daily P', _rowfmt(station.ppts))
    print('Num wet', _rowfmt(station.nwds))
    par_monthlies = station.ppts * station.nwds
    print('Month P', _rowfmt(par_monthlies))
    cli_fname = '{}.cli'.format(par)

    cligen = Cligen(stationMeta)
    cligen.run_multiple_year(100, cli_fname=cli_fname)

    cli_fn = ClimateFile(cli_fname)
    monthlies = cli_fn.calc_monthlies()
    print('CligenP', _rowfmt(monthlies['ppts']))
    print('Error  ', _rowfmt(par_monthlies - monthlies['ppts']))
    print()