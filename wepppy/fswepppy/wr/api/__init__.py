from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import awesome_codename
from flask import Flask, jsonify, request

from wepppy.fswepppy.wr import (
    run_factory, 
    RoadDesign, 
    RoadSurface, 
    Traffic, 
    SoilTexture
)

wr_wd = '/geodata/fswepppy_runs/'

app = Flask(__name__)

@app.route('/run/')
def run():
    
    road_design = RoadDesign.eval(request.args.get('road_design'))
    road_surface = RoadSurface.eval(request.args.get('road_surface'))
    traffic = Traffic.eval(request.args.get('traffic'))
    road_slope = float(request.args.get('road_slope'))
    road_length = float(request.args.get('road_length'))    
    road_width = float(request.args.get('road_width'))
    fill_slope = float(request.args.get('fill_slope'))
    fill_length = float(request.args.get('fill_length'))
    buffer_slope = float(request.args.get('buffer_slope'))
    buffer_length = float(request.args.get('buffer_length'))
    rock_fragment = float(request.args.get('rock_fragment'))
    soil_texture = SoilTexture.eval(request.args.get('soil_texture'))
    climate = request.args.get('climate')
    hill_id = request.args.get('hill_id', None)
    wd = request.args.get('wd', None)

    
    if wd is None:
        wd = _join(wr_wd, awesome_codename.generate_codename().replace(' ', '-'))
        assert not _exists(wd)
        os.makedirs(wd)
    else:
        assert '/' not in wd
        assert '\\' not in wd
        assert ' ' not in wd
        assert '.' not in wd
        wd = _join(wr_wd, wd)
        
    assert _exists(wd)

    wr_hill = WRHill(road_design=road_design, road_surface=road_surface, traffic=traffic,
                     road_slope=road_slope, road_length=road_length, road_width=road_width,
                     fill_slope=fill_slope, fill_length=fill_length,
                     buffer_slope=buffer_slope, buffer_length=buffer_length,
                     rock_fragment=rock_fragment, soil_texture=soil_texture,
                     climate=climate, wd=wd, hill_id='wr')
    wr_hill.run()
    return jsonify(wr_hill.loss_summary())


if __name__ == '__main__':
    app.run()
