import json
import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

from datetime import datetime

import awesome_codename

from wepppy.nodb import Ron, Watershed, Landuse, Soils, Climate
from wepppy.nodb.climate import ClimateSpatialMode
from wepppy.nodb.mods import RangelandCover
from wepppy.weppcloud.app import get_wd


class BatchProcessor(object):
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.wd = None

    @property
    def status_log(self):
        if self.wd is None:
            raise Exception('wd not set')
        return _join(self.wd, 'batch_processor.log')     

    def _write(self, msg):
        if _exists(self.status_log):
            with open(self.status_log, 'a') as fp:
                fp.write(msg + '\n')
        else:
            try:
                with open(self.status_log, 'w') as fp:
                    fp.write(msg + '\n')
            except FileNotFoundError:
                warnings.warn('FileNotFoundError: "%s"' % self.status_log)

    def log(self, msg):
        t0 = datetime.strftime(datetime.now(), '%Y-%m-%dT%H:%M:%S.%f')
        L = f'[{t0}] {msg}'
        if self.verbose:
            print(L)
        self._write(L)

    def run_script(self, script_fn):
        self.script_fn = script_fn

        self._create_wd()
        self._load_pars()
        self._init_project()
        self._fetch_dem()
        self._run_topographic_analysis()

        if 'rangeland_cover' in self.mods:
            self._build_rangeland_cover()

        self._build_landuse()
        self._build_soils()
        self._set_climate_station()
        self._build_climate()

    @property
    def mods(self):
        return self.ron.mods

    def _create_wd(self):
        wd = None
        dir_created = False
        while not dir_created:
            runid = awesome_codename.generate_codename().replace(' ', '-')

            wd = get_wd(runid)
            if _exists(wd):
                continue

            os.mkdir(wd)
            dir_created = True

        self.wd = wd

        if self.verbose:
            self.log(f'wd = {wd}')

    def _load_pars(self):
        with open(self.script_fn) as fp:
            self.pars = json.load(fp)

    def _init_project(self):
        pars = self.pars

        cfg = "%s.cfg" % pars['project'].get('config')

        overrides = []

        override_section_keys = (('project', 'cellsize'),
                                 ('watershed', 'delineation_backend'),
                                 ('topaz', 'mcl'),
                                 ('topaz', 'csa'))

        for _section, _key in override_section_keys:
            _section_pars = pars.get(_section)
            if _section_pars:
                _par = _section_pars.get(_key)
                if _par:
                    overrides.append(f'{_section}:{_key}={_par}')

        if len(overrides) > 0:
            cfg += '?%s' % '&'.join(overrides)

        if self.verbose:
            self.log(f'cfg = {cfg}')

        ron = Ron(self.wd, cfg)
        try:
            ron.name = pars.get('project').get('name')
        except AttributeError:
            pass
  
        self.ron = ron

    @property
    def extent(self):
        return self.pars.get('watershed').get('extent')

    @property
    def map_center(self):
        return self.pars.get('watershed').get('map_center')

    @property
    def map_zoom(self):
        return self.pars.get('watershed').get('map_zoom')

    @property
    def outlet(self):
        return self.pars.get('watershed').get('outlet')

    @property
    def climate_mode(self):
        return self.pars.get('climate').get('climate_mode')


    def get_par(self, section, key):
        return self.pars.get(section).get(key)

    def _fetch_dem(self):
        ron = self.ron
        ron.set_map(extent=self.extent, center=self.map_center, zoom=self.map_zoom)
        ron.fetch_dem()

    def _run_topographic_analysis(self):
        watershed = Watershed.getInstance(self.wd)
        watershed.build_channels()
        watershed.set_outlet(*self.outlet)
        watershed.build_subcatchments()
        watershed.abstract_watershed()
        self.log(f'watershed.report = {watershed.report}')

    def _build_rangeland_cover(self):
        rangeland_cover = RangelandCover.getInstance(self.wd)
        rangeland_cover.build()

    def _build_landuse(self):
        landuse = Landuse.getInstance(self.wd)
        landuse.build()

    def _build_soils(self):
        soils = Soils.getInstance(self.wd)
        soils.build()

    def _set_climate_station(self):
        climate = Climate.getInstance(self.wd)

        try:
            station_id = self.pars['climate']['climate_station']['station_id']
        except KeyError:
            selection_mode = self.pars['climate']['climate_station']['selection_mode']
            if selection_mode == 'closest':
                station_id = climate.find_closest_stations()[0]['id'] 
            elif selection_mode == 'multi-factor' or selection_mode == 'heuristic':
                station_id = climate.find_heuristic_stations()[0]['id'] 

        climate.climatestation = station_id 

    def _build_climate(self):
        climate_mode = self.climate_mode
        climate = Climate.getInstance(self.wd)

        assert climate_mode in (
            None, 'vanilla', 'observed', 'observed_prism', 'future', 'single_storm', 
            'prism', 'observed_db', 'future_db', 'eobs', 'agdc', 'gridmet_prism'), climate_mode

        if climate_mode is not None:
            climate.climate_mode = climate_mode

        attrs = {}
        input_years = self.pars.get('climate').get('input_years')
        if input_years is not None:
            attrs['_input_years'] = input_years

        if 'prism' in climate_mode:
            attrs['_climate_spatialmode'] = ClimateSpatialMode.Multiple
        else:
            try:
                climate_spatialmode = self.pars['climate']['spatial_mode']
                attrs['_climate_spatialmode'] = ClimateSpatialMode.parse(climate_spatialmode)
            except KeyError:
                pass

        if climate_mode == 'observed' or \
             climate_mode == 'observed_prism' or \
             climate_mode == 'gridmet_prism': 
            attrs['_observed_start_year'] = self.get_par('climate', 'start_year')
            attrs['_observed_end_year'] = self.get_par('climate', 'end_year')

        elif climate_mode == 'future':
            attrs['_future_start_year'] = self.get_par('climate', 'start_year')
            attrs['_future_end_year'] = self.get_par('climate', 'end_year')


        self.log(f'attrs = {attrs}')
        climate.build(attrs=attrs)

    def _run_wepp(self):
        wepp = Wepp.getInstance()

if __name__ == "__main__":
    script_fn = '/workdir/wepppy/wepppy/rhem/tests/rap_sm.json'
    script_fn = '/workdir/wepppy/wepppy/rhem/tests/rap_sm_heuristic.json'
    script_fn = '/workdir/wepppy/wepppy/rhem/tests/rap_sm_specified_station_id.json'
    script_fn = '/workdir/wepppy/wepppy/rhem/tests/rap_sm_observed.json'
    #script_fn = '/workdir/wepppy/wepppy/rhem/tests/rap_sm_observed_prism.json'
    script_fn = '/workdir/wepppy/wepppy/rhem/tests/rap_sm_gridmet_prism.json'
    #script_fn = '/workdir/wepppy/wepppy/rhem/tests/rap_sm_observed_multiple.json'
    script_fn = '/workdir/wepppy/wepppy/rhem/tests/rap_sm_prism.json'

    batch_processor = BatchProcessor()
    batch_processor.run_script(script_fn)

