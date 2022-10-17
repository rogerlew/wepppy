from wepppy.fswepppy.wr import RoadDesign, Traffic, RoadSurface, SoilTexture, WRHill


for road_design in RoadDesign:
    for road_surface in RoadSurface:
        for traffic in Traffic:
            for soil_texture in SoilTexture:

                print(road_design, road_surface, traffic, soil_texture)
                wr_hill = WRHill(road_design=road_design, 
                                 road_surface=road_surface,
                                 traffic=traffic,
                                 soil_texture=soil_texture,
                                 road_slope=10, road_length=100, road_width=30,
                                 fill_slope=30, fill_length=300,
                                 buffer_slope=200, buffer_length=200,
                                 rock_fragment=7.0, climate_fn='/geodata/weppcloud_runs/base-monad/climate/id106388.cli', aspect=100, wd='wd')

                wr_hill.run()
