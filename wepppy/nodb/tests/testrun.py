
        
if __name__ == '__main__':
    import os
    import shutil
    from pprint import pprint
    from time import time
    from time import sleep
    
    import wepppy
    from wepppy.nodb import *

    wd = 'test2'

    if _exists(wd):
        shutil.rmtree(wd)

    os.mkdir(wd)

    ron = Ron(wd, "lt.cfg")
    ron.name = 'my project'
    extent = [-120.149917603, 38.9362458035, -120.106058121, 38.9704202385]
    ron.set_map(extent, [-120.121850967, 38.9853663716], zoom=11)
    del ron

    ron = Ron.getInstance(wd)
    ron.fetch_dem()

    topaz = Topaz.getInstance(wd)
    print topaz.topaz_pass
    print topaz.has_channels
    topaz.build_channels()
    del topaz

    topaz = Topaz.getInstance(wd)
    topaz.set_outlet(-120.124881887, 38.9473711556)
    del topaz

    ron2 = Ron.getInstance(wd)
    print ron2
    print ron2.name

    topaz = Topaz.getInstance(wd)
    topaz.build_subcatchments()

    print 'has subcatchments', topaz.has_subcatchments

    wat = Watershed.getInstance(wd)
    wat.abstract_watershed()

    #for s,v in wat.subs_summary.items():
    #    print s, v

    landuse = Landuse.getInstance(wd)
    landuse.mode = LanduseMode.Gridded
    landuse.build()
    landuse = Landuse.getInstance(wd)
    
    #pprint(landuse.subs_summary)
    #pprint(landuse.chns_summary)
    pprint(landuse.report)

    soils = Soils.getInstance(wd)
    soils.mode = SoilsMode.Gridded
    soils.build()
    #pprint(soil.subs_summary)
    #pprint(soil.chns_summary)
#    pprint(soil.report)

    climate = Climate.getInstance(wd)
#    pprint(climate.find_closest_stations())
    del climate

    climate = Climate.getInstance(wd)
    stations = climate.find_closest_stations()
#    stations = climate.find_heuristic_stations()
#    print stations
#    pprint(climate.heuristic_stations)
    del climate

    climate = Climate.getInstance(wd)
    climate.input_years = 5
    climate.climatestation = stations[0]['id']
    climate.climate_mode = ClimateMode.Single

#    climate.climate_mode = ClimateMode.Localized

#    climate.climate_mode = ClimateMode.Observed
#    climate.set_observed_pars(start_year=1984, end_year=1986)

#    climate.climate_mode = ClimateMode.Future
#    climate.set_future_pars(start_year=2019, end_year=2019)

#    climate.climate_mode = ClimateMode.SingleStorm
    del climate

    climate = Climate.getInstance(wd)
#    print climate.climatestation
#    print climate.climate_mode
    climate.build(verbose=1)
    print climate.has_climate
    
    watershed = Watershed.getInstance(wd)
    translator = watershed.translator_factory()
#    print watershed._subs_summary.keys()
#    print watershed._chns_summary.keys()
    
#    print 'hashes'
#    print translator._wepp2top
#    print translator._top2wepp
    
    for wepp_id in translator.iter_wepp_chn_ids():
        top = translator.top(wepp=wepp_id)
#        print wepp_id, top
#        print watershed[wepp_id].profile
        
#    wepppy.export.export_winwepp(wd)
    
    wepp = Wepp.getInstance(wd)
    wepp.prep_hillslopes()
    wepp.run_hillslopes()
    
    wepp.prep_watershed()
    wepp.run_watershed()
