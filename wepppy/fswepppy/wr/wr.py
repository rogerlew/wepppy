#! /usr/bin/python3

#  wr.py -- WEPP:Road workhorse
#
#  FS WEPP
#  USDA Forest Service, Rocky Mountain Research Station
#  Soil & Water Engineering
#  Science by Bill Elliot et alia                      
#  Code by Roger Lew adapted from David Hall's wr.pl
#
import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import shutil

import warnings

from math import sqrt

from enum import Enum
import numpy as np
import subprocess
from time import time

import validators                     
import requests

from wepppy.wepp.soils.utils import WeppSoilUtil
from wepppy.wepp.out import HillLoss

_thisdir = os.path.dirname(__file__)
_datadir = _join(_thisdir, 'data')


class RoadDesign(Enum):
    InslopeBare = 1
    InslopeVegetated = 2
    OutslopeUnrutted = 3
    OutslopeRutted = 4
    
    @staticmethod
    def eval(v):
        return RoadDesign((None, 'ib', 'iv', 'ou', 'or').index(v.lower()))

class Traffic(Enum):
    NONE = 1
    Low = 2
    High = 3

    @staticmethod
    def eval(v):
        return Traffic(' nlh'.index(v.lower()))


class SoilTexture(Enum):
    Clay = 1
    Silt = 2
    Sand = 3
    Loam = 4
    
    @staticmethod
    def eval(v):
        return SoilTexture((None, 'clay', 'silt', 'sand', 'loam').index(v.lower()))


class RoadSurface(Enum):
    Natural = 0
    Gravel = 1
    Paved = 2

    @staticmethod
    def eval(v):
        return RoadSurface('ngp'.index(v.lower()))


_ROAD_SLOPE_MIN,_ROAD_SLOPE_MAX = 0.1, 40.0
_ROAD_LENGTH_MIN, _ROAD_LENGTH_MAX =  1.0, 300.0
_ROAD_WIDTH_MIN, _ROAD_WIDTH_MAX = 0.3, 100.0
_FILL_SLOPE_MIN, _FILL_SLOPE_MAX =  0.1, 150.0
_FILL_LENGTH_MIN, _FILL_LENGTH_MAX = 0.3, 100.0
_BUFFER_SLOPE_MIN, _BUFFER_SLOPE_MAX = 0.1, 100.0
_BUFFER_LENGTH_MIN, _BUFFER_LENGTH_MAX = 0.3, 300.0
_ROCK_FRAGMENT_MIN, _ROCK_FRAGMENT_MAX = 0.0, 50.0

_OUTSLOPE_DEFAULT = 0.04


class WRHill(object):
    def __init__(self, road_design: RoadDesign, road_surface: RoadSurface, 
                 traffic: Traffic, soil_texture: SoilTexture,
                 road_slope: float, road_length: float, road_width: float, 
                 fill_slope: float, fill_length: float, 
                 buffer_slope: float, buffer_length: float, 
                 rock_fragment: float, climate: str, aspect=None, hill_id='wrwepp', wd='./'):
        self._road_design = road_design
        self._road_surface = road_surface
        self._traffic = traffic
        self._soil_texture = soil_texture
        
        self._road_slope = road_slope
        self._road_length = road_length
        self._road_width = road_width
        
        self._fill_slope = fill_slope
        self._fill_length = fill_length
        
        self._buffer_slope = buffer_slope
        self._buffer_length = buffer_length
        
        self._rock_fragment = rock_fragment
        
        self._cli_fn = _split(climate)[-1]
        self._aspect = aspect
        
        self._hill_id = hill_id
        self._wd = wd

        if validators.url(climate):
            response = requests.get(climate, allow_redirects=True)
            if response.status_code == 200:
                with open(self.cli_fn, 'w') as fp:
                    fp.write(response.text)
        else:
            shutil.copyfile(climate, self.cli_fn)
    
    @property
    def road_design(self):
        return self._road_design
        
    @property
    def road_surface(self):
        return self._road_surface
        
    @property
    def traffic(self):
        return self._traffic
        
    @property
    def soil_texture(self):
        return self._soil_texture
        
    @property
    def out_slope(self):
        return _OUTSLOPE_DEFAULT
    
    @property
    def road_slope(self):
        return np.clip(self._road_slope, _ROAD_SLOPE_MIN, _ROAD_SLOPE_MAX)
        
    @property
    def road_length(self):
        return np.clip(self._road_length, _ROAD_LENGTH_MIN, _ROAD_LENGTH_MAX)
        
    @property
    def road_width(self):
        return np.clip(self._road_width, _ROAD_WIDTH_MIN, _ROAD_WIDTH_MAX)
        
    @property
    def fill_slope(self):
        return np.clip(self._fill_slope, _FILL_SLOPE_MIN,  _FILL_SLOPE_MAX)
        
    @property
    def fill_length(self):
        return np.clip(self._fill_length, _FILL_LENGTH_MIN, _FILL_LENGTH_MAX)
        
    @property
    def buffer_slope(self):
        return np.clip(self._buffer_slope, _BUFFER_SLOPE_MIN, _BUFFER_SLOPE_MAX)
        
    @property
    def buffer_length(self):
        return np.clip(self._buffer_length, _BUFFER_LENGTH_MIN, _BUFFER_LENGTH_MAX)
        
    @property
    def rock_fragment(self):
        return np.clip(self._rock_fragment, _ROCK_FRAGMENT_MIN, _ROCK_FRAGMENT_MAX)
        
    @property
    def cli_fn(self):
        return _join(self.wd, self._cli_fn)
        
    @property
    def aspect(self):
        if self._aspect is None:
            return 100.0
        else:
            return self._aspect
        
    @property
    def hill_id(self):
        return self._hill_id
        
    @property
    def wd(self):
        return self._wd
        
    @property
    def slp_fn(self):
        return _join(self.wd, f'{self.hill_id}.slp')
        
    @property
    def sol_fn(self):
        return _join(self.wd, f'{self.hill_id}.sol')
        
    @property
    def man_template_dir(self):
        return _join(_datadir, 'managements')

    @property
    def man_template_fn(self):
        return f'3_{self.road_design}_{self.traffic}.man'

    @property
    def man_fn(self):
        return _join(self.wd, f'{self.hill_id}.man')
        
    @property
    def run_fn(self):
        return _join(self.wd, f'{self.hill_id}.run')
        
    @property
    def tauC(self):
        road_design = self.road_design
        road_surface = self.road_surface
        if road_design == RoadDesign.InslopeVegetated:
            return 10.0
        elif road_design == RoadDesign.InslopeBare and road_surface == RoadSurface.Paved:
            return 1.0
        else:
            return 2.0
       
    @property
    def input_years(self):
        from wepppy.climates.cligen import ClimateFile
        cli = ClimateFile(self.cli_fn)
        return cli.input_years

    def _create_slope_file(self):
        """
        create slope file from specified geometry
        """
        hill_id = self.hill_id

        road_slope = self.road_slope
        road_width = self.road_width
        road_length = self.road_length
        
        fill_slope = self.fill_slope
        fill_length = self.fill_length
        
        buffer_slope = self.buffer_slope
        buffer_length = self.buffer_length
        road_design = self.road_design
        aspect = self.aspect
        
        slp_fn = self.slp_fn
        
        if road_design == RoadDesign.OutslopeUnrutted:
            out_slope = self.out_slope
            road_slope = sqrt(out_slope * out_slope + road_slope * road_slope)  # 11/1999
            road_length = road_width  * road_slope / out_slope
            road_width = road_length * road_width / road_length
            
        s = ["97.3",
             f"# Slope file for {road_design} by WEPPcloud:Road",
             "3",              # no. OFE
             f"{aspect} {road_width}",          # aspect; profile width         # 11/1999
             # OFE 1 (road)
             f"2 {road_length}",     # no. points, OFE length
             f"0 {road_slope}",
             f"1 {road_slope}",
             # OFE 2 (fill)
             f"3 {fill_length}",
             f"0 {road_slope}",
             f"0.05 {fill_slope}",
             f"1 {fill_slope}",
             # OFE 3 (buffer)
             f"3 {buffer_length}",
             f"0 {fill_slope}",
             f"0.05 {buffer_slope}",
             f"1 {buffer_slope}"]
             
        with open(slp_fn, 'w') as fp:
            fp.write('\n'.join(s))
            
        assert _exists(slp_fn)
        
    def _create_soil_file(self):
        """                                                          
        Read a WEPP:Road soil file template and create a usable soil file.
        File may have 'urr', 'ufr' and 'ubr' as placeholders for rock fragment
        Adjust road surface Kr downward for traffic levels of 'low' or 'none'
        Adjust road surface Ki downward for traffic levels of 'low' or 'none'
                DEH 2004.01.26
        uses: $soilFilefq   fully qualified input soil file name
              $newSoilFile  name of soil file to be created
              $surface      native, graveled, paved
              $traffic      High, Low, None
              $UBR          user-specified rock fragment decimal percentage for
        buffer
        sets: $URR          calculated rock fragment decimal percentage for road
              $UFR          calculated rock fragment decimal percentage for fill
        """
        
        tauC = self.tauC
        road_surface = self.road_surface
        traffic = self.traffic
        soil_texture = self.soil_texture
        
        UBR = self.rock_fragment
        if road_surface == RoadSurface.Gravel:
            URR = 65.0
            UFR = (UBR + 65.0) / 2.0
        elif road_surface == RoadSurface.Paved:
            URR = 95.0
            UFR = (UBR + 65.0) / 2.0
        else:
            URR = UBR
            UFR = UBR

        template_fn = _join(_datadir, 'soils', f'3_{road_surface}_{soil_texture}_{int(tauC)}.sol')
        
        sol = WeppSoilUtil(template_fn)
       
        # modify kr and ki for 'no traffic' and 'low traffic' 
        if traffic in (Traffic.NONE, Traffic.Low):
            sol.obj['ofes'][0]['ki'] /= 4.0
            sol.obj['ofes'][0]['kr'] /= 4.0
        
        # template replace UBR, UFR, UBR
        sol.obj['ofes'][0]['horizons'][0]['rfg'] = UBR  # buffer rock
        sol.obj['ofes'][1]['horizons'][0]['rfg'] = URR  # road rock
        sol.obj['ofes'][2]['horizons'][0]['rfg'] = UFR  # fill rock
    
        sol.write(self.sol_fn)
    
    def _create_man_file(self):
        from wepppy.wepp.management import Management
        man = Management(ManagementDir=self.man_template_dir, 
                         ManagementFile=self.man_template_fn,
                         Key=self.man_template_fn[:-4])
        multi = man.build_multiple_year_man(self.input_years)
        
        fn_contents = str(multi)
        with open(self.man_fn, 'w') as fp:
            fp.write(fn_contents)

    def _create_run_file(self):
        s = [
             "97.3",                # datver
             "y",                   # not watershed
             "1",                   # 1 = continuous
             "1",                   # 1 = hillslope
             "n",                   # hillsplope pass file out?
             "1",                   # 1 = abreviated annual out
             "n",                   # initial conditions file?
            f"{self.hill_id}.loss", # soil loss output file
             "n",                   # water balance output?
             "n",                   # crop output?
             "n",                   # soil output?
             "n",                   # distance/sed loss output?
             "n",                   # large graphics output?
             "n",                   # event-by-event out?
             "n",                   # element output?
             "n",                   # final summary out?
             "n",                   # daily winter out?
             "n",                   # plant yield out?
            f"{_split(self.man_fn)[-1]}",       # management file name
            f"{_split(self.slp_fn)[-1]}",       # slope file name
            f"{_split(self.cli_fn)[-1]}",       # climate file name
            f"{_split(self.sol_fn)[-1]}",       # soil file name
             "0",                   # 0 = no irrigation
            f"{self.input_years}",  # no. years to simulate
             "0"                    # 0 = route all events
            ]
            
        with open(self.run_fn, 'w') as fp:
            fp.write('\n'.join(s))

    def _run_hillslope(self, wepp_bin='latest'):
        from wepppy.wepp import bin as _bin
        hill_id = self.hill_id
        wd = self.wd 

        t0 = time()

        cmd = [os.path.abspath(_join(_bin._thisdir, "../", "bin", wepp_bin))]

        assert _exists(self.man_fn)
        assert _exists(self.slp_fn)
        assert _exists(self.cli_fn)
        assert _exists(self.sol_fn)

        _run = open(self.run_fn)
        _log = open(_join(wd, f'{hill_id}.err'), 'w')

        p = subprocess.Popen(cmd, stdin=_run, stdout=_log, stderr=_log, cwd=wd)
        p.wait()
        _run.close()
        _log.close()

        log_fn = _join(wd, f'{hill_id}.err')
        with open(log_fn) as fp:
            lines = fp.readlines()
            for L in lines:
                if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in L:
                    return True, hill_id, time() - t0

        raise Exception(f'Error running wepp for wepp_id {hill_id}\nSee {log_fn}')

    def run(self):
        self._create_slope_file()
        self._create_soil_file()
        self._create_man_file()
        self._create_run_file()
        self._run_hillslope()


    def loss_summary(self):
        loss_fn = _join(self.wd, f'{self.hill_id}.loss')
        hill_loss = HillLoss(loss_fn)
        return hill_loss.annuals_d


def run_factory(parameters_str: str, wd: str, hill_id='wr'):
    parameters = parameters_str.replace(',',' ').split()
    assert len(parameters) >= 13

    road_design = RoadDesign.eval(parameters[0])
    road_surface = RoadSurface.eval(parameters[1])
    traffic = Traffic.eval(parameters[2])
    road_slope = float(parameters[3])
    road_length = float(parameters[4])
    road_width = float(parameters[5])
    fill_slope = float(parameters[6])
    fill_length = float(parameters[7])
    buffer_slope = float(parameters[8])
    buffer_length = float(parameters[9])
    rock_fragment = float(parameters[10])
    soil_texture = SoilTexture.eval(parameters[11])
    climate = parameters[12]
    
    wr_hill = WRHill(road_design=road_design, road_surface=road_surface, traffic=traffic,
                     road_slope=road_slope, road_length=road_length, road_width=road_width,
                     fill_slope=fill_slope, fill_length=fill_length,
                     buffer_slope=buffer_slope, buffer_length=buffer_length,
                     rock_fragment=rock_fragment, soil_texture=soil_texture,
                     climate=climate, wd=wd, hill_id='wr')
    wr_hill.run()
    return wr_hill.loss_summary()

                  
