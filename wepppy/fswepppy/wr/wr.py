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

import warnings

from enum import Enum
import numpy as np

from wepppy.wepp.soils.utils import WeppSoilUtil

_thisdir = os.path.dirname(__file__)
_datadir = _join(_thisdir, 'data')


class RoadDesign(Enum):
    InslopeBare = 1
    InslopeVegetated = 2
    OutslopedUnrutted = 3
    OutslopedRutted = 4
    
    
class Traffic(Enum):
    None = 1
    Low = 2
    High = 3


class SoilTexture(Enum):
    Clay = 1
    Silt = 2
    Sand = 3
    Loam = 4


class RoadSurface(Enum):
    Natural = 0
    Gravel = 1
    Paved = 2


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
    def __init__(self, road_design: RoadDesign, road_surface: RoadSurface, traffic : Traffic, 
                 road_slope: float, road_length: float, road_width: float, 
                 fill_slope: float, fill_length: float, 
                 buffer_slope: float, buffer_length: float, 
                 rock_fragment: float, climate_fn: str, aspect=None, hill_id='wrwepp', wd='./'):
                     
        self._road_design = road_design
        self._road_surface = road_surface
        self._traffic = traffic
        
        self._road_slope = road_slope
        self._road_length = road_length
        self._road_width = road_width
        
        self._fill_slope = fill_slope
        self._fill_length = fill_length
        
        self._buffer_slope = buffer_slope
        self._buffer_length = buffer_length
        
        self._rock_fragment = rock_fragment
        
        self._cli_fn = climate_fn
        self._aspect = aspect
        
        self._hill_id = hill_id
        self._wd
    
    @property
    def road_design(self):
        return self._road_design
        
    @property
    def _road_surface(self):
        return self._road_surface
        
    @property
    def traffic(self):
        return self._traffic
        
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
        return self._cli_fn
        
    @property
    def aspect(self):
        if self._aspect is None:
            return 100.0
        else:
            return aspect
        
    @property
    def hill_id(self):
        return self._hill_id
        
    @property
    def wd(self):
        return self._wd
        
    @property
    def slp_fn(self):
        return _join(self.wd, f'{hill_id}.slp')
        
    @property
    def sol_fn(self):
        return _join(self.wd, f'{hill_id}.sol')
        
    @property
    def man_fn(self):
        road_design = self.road_design
        traffic = self.traffic
        
        man_fn = f'3{road_design}'
        if traffic == Traffic.None:
            man_fn += f'_{traffic}'
        man_fn += '.man'
        man_fn = _join(_datadir, 'managements', man_fn)
        assert _exists(man_fn), man_fn
    
        return man_fn

    @property
    def run_fn(self):
        return _join(self.wd, f'{hill_id}.run')
        
    @property
    def tauC(self):
        road_design = self.road_design
        if road_design == RoadDesign.InslopeVegetated:
            return 10.0
        elif road_design == RoadDesign.InslopeBare:
            return 1.0
        else:
            return 2.0
            
    def _create_slope_file(self):
        """
        create slope file from specified geometry
        """
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
        
        if road_design = RoadDesign.OutslopedUnrutted:
            out_slope = self.out_slope
            road_slope = sqrt(out_slope * out_slope + road_slope * road_slope)  # 11/1999
            road_length = road_width  * road_slope / out_slope
            road_width = road_length * road_width / road_length
            
        s = ["97.3",
             f"# Slope file for {road_design} by WEPPcloud:Road",
             "3",              # no. OFE
             f"{aspect} road_width\n",          # aspect; profile width         # 11/1999
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
        if traffic in (Traffic.None, Traffic.Low):
            sol.obj['ofes'][0]['ki'] /= 4.0
            sol.obj['ofes'][0]['kr'] /= 4.0
        
        # template replace UBR, UFR, UBR
        sol.obj['ofes'][0]['horizons'][0]['rfg'] = UBR  # buffer rock
        sol.obj['ofes'][1]['horizons'][0]['rfg'] = URR  # road rock
        sol.obj['ofes'][2]['horizons'][0]['rfg'] = UFR  # fill rock
    
        sol.write(self.sol_fn)
       
    def _create_run_file(hill_id, years):
        s = [
             "97.3",            # datver
             "y",               # not watershed
             "1",               # 1 = continuous
             "1",               # 1 = hillslope
             "n",               # hillsplope pass file out?
             "1",               # 1 = abreviated annual out
             "n",               # initial conditions file?
             "{hill_id}.loss",  # soil loss output file
             "n",               # water balance output?
             "n",               # crop output?
             "n",               # soil output?
             "n",               # distance/sed loss output?
             "n",               # large graphics output?
             "n",               # event-by-event out?
             "n",               # element output?
             "n",               # final summary out?
             "n",               # daily winter out?
             "n",               # plant yield out?
             "{self.man_fn}",   # management file name
             "{self.slp_fn}",   # slope file name
             "{self.cli_fn}",   # climate file name
             "{self.sol_fn}",   # soil file name
             "0",               # 0 = no irrigation
             "{years}",         # no. years to simulate
             "0"                # 0 = route all events
            ]
            
        with open("{self.run_fn}", 'w') as fp:
            fp.write('\n'.join(s))

