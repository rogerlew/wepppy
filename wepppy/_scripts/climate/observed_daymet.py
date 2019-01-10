# https://www.wcc.nrcs.usda.gov/webmap/#version=80.1&elements=&networks=!&states=!&counties=!&hucs=&minElevation=&maxElevation=&elementSelectType=all&activeOnly=true&activeForecastPointsOnly=false&hucLabels=false&hucParameterLabels=false&stationLabels=&overlays=&hucOverlays=&mode=data&openSections=dataElement,parameter,date,basin,elements,location,networks&controlsOpen=true&popup=615:NV:SNTL&popupMulti=&base=esriNgwm&displayType=station&basinType=6&dataElement=PREC&parameter=PCTAVG&frequency=DAILY&duration=mtd&customDuration=&dayPart=E&year=2018&month=4&day=14&monthPart=E&forecastPubMonth=4&forecastPubDay=1&forecastExceedance=50&seqColor=1&divColor=3&scaleType=D&scaleMin=&scaleMax=&referencePeriodType=POR&referenceBegin=1981&referenceEnd=2010&minimumYears=20&hucAssociations=true&lat=39.2434&lon=-119.6082&zoom=10.0

from glob import glob

from wepppy.climates.cligen import ClimateFile, CligenStationsManager
from wepppy.climates import cligen_client as cc

stationManager = CligenStationsManager()
cli_fns = glob('/home/weppdev/PycharmProjects/wepppy/wepppy/nodb/mods/lt/data/tahoe/observed/Daily/*.cli')

fp = open('observed_daymet.csv', 'w')
fp.write('par,month,lng,lat,measure,observed,daymet\n')

for cli_fn in cli_fns:
    print(cli_fn)

    cli = ClimateFile(cli_fn)
    lat, lng = cli.lat, cli.lng
    obs_monthlies = cli.calc_monthlies()

    stationMeta = stationManager.get_station_heuristic_search((lng, lat))

    print(lng, lat, stationMeta.longitude, stationMeta.latitude, stationMeta.desc)
    intpar = int(''.join(v for v in stationMeta.par if v in '0123456789'))
    result = cc.observed_daymet(intpar, 1980, 2016, lng, lat, returnjson=True)
    par_fn, cli_fn, monthlies = cc.unpack_json_result(result, 'daymet')

    cli = ClimateFile(cli_fn)
    daymet_monthlies = cli.calc_monthlies()

    for k in obs_monthlies:
        for j in range(12):
            fp.write('{},{},{},{},{},{},{}\n'.format(intpar, j + 1, lng, lat, k,
                                                     obs_monthlies[k][j], daymet_monthlies[k][j]))


fp.close()