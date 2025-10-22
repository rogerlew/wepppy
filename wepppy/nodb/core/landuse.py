# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""Land cover and management assignment for WEPP simulations.

This module provides the Landuse NoDb controller for managing land cover data,
vegetation classifications, and WEPP management file (.man) assignment to
subcatchments. It supports multiple land cover data sources and management
database systems.

Key Components:
    Landuse: NoDb controller for land cover management
    LanduseMode: Enum defining land cover data sources
    
Land Cover Sources:
    - NLCD: National Land Cover Database (US)
    - RAP: Rangeland Analysis Platform
    - TreeCanopy: Tree canopy cover data
    - Single: Uniform management across watershed
    - Gridded: Custom gridded land cover
    
Management Databases:
    - Default WEPP management database
    - Custom management rotations
    - Disturbance scenarios (fire, logging, etc.)

Example:
    >>> from wepppy.nodb.core import Landuse, LanduseMode
    >>> landuse = Landuse.getInstance('/wc1/runs/my-run')
    >>> landuse.mode = LanduseMode.NLCD
    >>> landuse.build_managements()
    >>> print(landuse.domlc_d)  # Dominant land cover by subcatchment

See Also:
    - wepppy.landcover: Land cover classification and mapping
    - wepppy.wepp.management: WEPP management file handling
    - wepppy.nodb.mods.disturbed: Disturbance modeling

Note:
    Management files (.man) are generated per hillslope as p{wepp_id}.man
    in the {wd}/wepp/runs/ directory.
    
Warning:
    Land cover assignment requires completed watershed abstraction.
"""

# standard library
import csv
import json

import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from typing import Optional, Dict, List, Any, Tuple
import shutil
from enum import IntEnum
import time

from copy import deepcopy

import numpy as np
import pandas as pd

from deprecated import deprecated

from wepppy.landcover import LandcoverMap
from wepppy.query_engine import update_catalog_entry
from wepppy.wepp.management import get_management_summary
from wepppy.topo.watershed_abstraction.support import is_channel
from wepppy.all_your_base import isfloat
from wepppy.all_your_base.geo.webclients import wmesque_retrieve
from wepppy.all_your_base.geo import read_raster
    
from wepppy.nodb.base import (
    NoDbBase,
    TriggerEvents,
    nodb_setter,
)

from wepppy.nodb.duckdb_agents import (
    get_landuse_subs_summary,
    get_landuse_sub_summary
)

from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

from wepppy.landcover.rap import RAP_Band

from wepppy.nodb.locales import LanduseDataset, available_landuse_datasets

__all__ = [
    'LanduseNoDbLockedException',
    'LanduseMode',
    'read_cover_defaults',
    'Landuse',
]

import wepppyo3
from wepppyo3.raster_characteristics import identify_mode_single_raster_key
from wepppyo3.raster_characteristics import identify_mode_intersecting_raster_keys

class LanduseNoDbLockedException(Exception):
    pass


class LanduseMode(IntEnum):
    Undefined = -1
    Gridded = 0
    Single = 1
    Vanilla = 1  # Backward compatibility alias
    RRED_Unburned = 2
    RRED_Burned = 3
    UserDefined = 4
    SpatialAPI = 9


_COVERAGE_PERCENTAGES: Tuple[float, ...] = tuple(i / 100.0 for i in range(0, 103))


def read_cover_defaults(fn: str) -> Dict[str, Dict]:
    with open(fn) as fp:
        d = {}
        rdr = csv.DictReader(fp)
        for row in rdr:
            d[row['key']] = row

    return d


class Landuse(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'Landuse'

    filename = 'landuse.nodb'
    
    def __init__(
        self, 
        wd: str, 
        cfg_fn: str, 
        run_group: Optional[str] = None, 
        group_name: Optional[str] = None
    ) -> None:
        super(Landuse, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            self._mode = LanduseMode.Gridded
            self._single_selection = 0  # No Data
            self._single_man = None
            self.domlc_d = None  # topaz_id keys, ManagementSummary values
            self.managements = None
            cover_defaults_fn = self.config_get_path('landuse', 'cover_defaults')

            if cover_defaults_fn is not None:
                self.cover_defaults_d = read_cover_defaults(cover_defaults_fn)
            else:
                self.cover_defaults_d = None

            self._mapping = self.config_get_str('landuse', 'mapping')
            self._nlcd_db = self.config_get_path('landuse', 'nlcd_db')

            lc_dir = self.lc_dir
            if not _exists(lc_dir):
                os.mkdir(lc_dir)

            _landuse_map = self.config_get_path('landuse', 'landuse_map')
            if _landuse_map is not None:
                shutil.copyfile(_landuse_map, self.lc_fn)
                prj = _landuse_map[:-4] + '.prj'
                if _exists(prj):
                    shutil.copyfile(_landuse_map[:-4] + '.prj', self.lc_fn[:-4] + '.prj')

            self._landuse_map = _landuse_map

            self.domlc_mofe_d = None
            self._mofe_buffer_selection = self.config_get_int('landuse', 'mofe_buffer_selection')
            self._buffer_man = None

            self._fractionals = self.config_get_list('landuse', 'fractionals')

            self._hillslope_cancovs = None
            self._hillslope_mofe_cancovs = None

    @classmethod
    def _post_instance_loaded(cls, instance: 'Landuse') -> 'Landuse':
        instance = super()._post_instance_loaded(instance)

        if hasattr(instance, 'domlc_mofe_d') and instance.domlc_mofe_d is not None:
            for topaz_id in instance.domlc_mofe_d:
                mofe_d = {}
                for _id in sorted(int(_id) for _id in instance.domlc_mofe_d[topaz_id]):
                    _id = str(_id)
                    mofe_d[_id] = instance.domlc_mofe_d[topaz_id][_id]
                instance.domlc_mofe_d[topaz_id] = mofe_d

        return instance

    @property
    def mapping(self) -> Optional[str]:
        if hasattr(self, '_mapping'):
            return self._mapping

        _mapping = None
        if self._mode in [LanduseMode.RRED_Unburned, LanduseMode.RRED_Burned]:
            _mapping = 'rred'
        elif self._mode == LanduseMode.Gridded and 'eu' in self.locales:
            _mapping = 'esdac'
        elif self._mode == LanduseMode.Gridded and 'au' in self.locales:
            _mapping = 'lu10v5ua'

        return _mapping
    
    @mapping.setter
    @nodb_setter
    def mapping(self, value: str):
        self._mapping = value

    def get_mapping_dict(self) -> dict[str, dict]:
        """
        Returns the management mapping dictionary
        """
        from wepppy.wepp.management import load_map
        mapping = self.mapping
        assert mapping is not None
        return load_map(mapping)

    @property
    def mode(self) -> LanduseMode:
        return self._mode
    
    @mode.setter
    @nodb_setter
    def mode(self, value: Any) -> None:
        if isinstance(value, LanduseMode):
            self._mode = value
        elif isinstance(value, int):
            self._mode = LanduseMode(value)
        else:
            raise ValueError('most be LanduseMode or int')

    @property
    def single_selection(self) -> int:
        """
        id of the selected management
        """
        return self._single_selection

    @single_selection.setter
    @nodb_setter
    def single_selection(self, landuse_single_selection: int) -> None:
        k = landuse_single_selection
        self._single_selection = k
        self._single_man = get_management_summary(k)

    @property
    def single_man(self) -> Optional[Any]:
        """
        management summary object
        """
        return self._single_man

    @property
    def mofe_buffer_selection(self) -> int:
        """
        id of the selected management
        """
        return getattr(self, '_mofe_buffer_selection', None)

    @mofe_buffer_selection.setter
    @nodb_setter
    def mofe_buffer_selection(self, k: int) -> None:
        self._mofe_buffer_selection = str(k)
        self._buffer_man = get_management_summary(k)

    @property
    def buffer_man(self) -> Optional[Any]:
        """
        management summary object
        """
        return getattr(self, '_buffer_man', None)

    @property
    def has_landuse(self) -> bool:
        mode = self._mode

        if mode == LanduseMode.Undefined:
            return False

        else:
            return self.domlc_d is not None

    #
    # build
    #

    def clean(self) -> None:

        lc_dir = self.lc_dir
        if _exists(lc_dir):
            shutil.rmtree(lc_dir)
        os.mkdir(lc_dir)

    def _build_ESDAC(self) -> None:
        from wepppy.eu.soils.esdac import ESDAC
        esd = ESDAC()

        domlc_d = {}

        watershed = self.watershed_instance
        for topaz_id, (lng, lat) in watershed.centroid_hillslope_iter():
            d = esd.query(lng, lat, ['usedo'])
            assert 'usedom' in d, d
            dom = d['usedom'][1]
            domlc_d[topaz_id] = str(dom)

        self.domlc_d = domlc_d

    def _build_lu10v5ua(self) -> None:
        from wepppy.au.landuse_201011 import Lu10v5ua
        lu = Lu10v5ua()

        domlc_d = {}

        watershed = self.watershed_instance
        for topaz_id, (lng, lat) in watershed.centroid_hillslope_iter():
            dom = lu.query_dom(lng, lat)
            domlc_d[topaz_id] = dom

        self.domlc_d = domlc_d

    @property
    def fractionals(self) -> Optional[List]:
        return getattr(self, '_fractionals', self.config_get_list('landuse', 'fractionals'))

    @fractionals.setter
    @nodb_setter
    def fractionals(self, value: List) -> None:
        self._fractionals = value

    @property
    def nlcd_db(self) -> Optional[str]:
        return getattr(self, '_nlcd_db', self.config_get_str('landuse', 'nlcd_db'))

    @nlcd_db.setter
    @nodb_setter
    def nlcd_db(self, value: str) -> None:
        self._nlcd_db = value

    def _build_NLCD(self, retrieve_nlcd: bool = True) -> None:
        global wepppyo3

        _map = self.ron_instance.map

        # Get NLCD 2011 from wmesque webservice
        lc_fn = self.lc_fn

        if retrieve_nlcd:
            wmesque_retrieve(self.nlcd_db, _map.extent, lc_fn, _map.cellsize, 
                             v=self.wmesque_version, wmesque_endpoint=self.wmesque_endpoint)
            update_catalog_entry(self.wd, lc_fn)
        elif not _exists(lc_fn):
            raise FileNotFoundError(f"'{lc_fn}' not found!")
            
        subwta_fn = self.watershed_instance.subwta

        if wepppyo3 is None:
            self.logger.info('Building landcover grid from NLCD raster using LandcoverMap.build_lcgrid')
            # create LandcoverMap instance
            lc = LandcoverMap(lc_fn)

            # build the grid
            # domlc_fn map is a property of NoDbBase
            # domlc_d is a dictionary with topaz_id keys
            self.domlc_d = lc.build_lcgrid(subwta_fn, None)
        else:
            self.logger.info('Building landcover grid from NLCD raster using wepppyo3 identify_mode_single_raster_key')
            domlc_d = identify_mode_single_raster_key(
                key_fn=subwta_fn, parameter_fn=lc_fn, ignore_channels=True, ignore_keys=set())
            self.domlc_d = {k: str(v) for k, v in domlc_d.items()}

    def _build_single_selection(self) -> None:
        assert self.single_selection is not None

        domlc_d = {}

        watershed = self.watershed_instance
        for topaz_id in watershed._subs_summary:
            domlc_d[topaz_id] = str(self.single_selection)

        self.domlc_d = domlc_d

    def _build_spatial_api(self) -> None:
        # fetch landcover map

        _map = self.ron_instance.map

        # Get NLCD 2011 from wmesque webservice
        lc_fn = self.lc_fn

        wmesque_retrieve(self.nlcd_db, _map.extent, lc_fn, _map.cellsize, 
                         v=self.wmesque_version, wmesque_endpoint=self.wmesque_endpoint)
        update_catalog_entry(self.wd, lc_fn)

        # read the keys out of the raster
        nlcd, transform, proj = read_raster(lc_fn, dtype=np.int32)

        doms = set([int(x) for x in nlcd.flatten()])
        doms = sorted(doms)

        managements = {}
        for dom in doms:
            man = managements[dom] = get_management_summary(dom, self.mapping)

            # copy the management file to landuse directory
            shutil.copyfile(_join(man.man_dir, man.man_fn), _join(self.lc_dir, _split(man.man_fn)[-1]))
            managements[dom].man_dir = self.lc_dir

        with self.locked():
            self._managements = managements

    def build(self) -> None:
        assert not self.islocked()
        self.logger.info('Building landuse')

        wd = self.wd

        if self._mode == LanduseMode.SpatialAPI:
            self._build_spatial_api()
            return

        watershed = self.watershed_instance
        if not watershed.is_abstracted:
            from wepppy.nodb.core.watershed import WatershedNotAbstractedError
            raise WatershedNotAbstractedError()

        if self._mode in [LanduseMode.RRED_Burned, LanduseMode.RRED_Unburned]:
            from wepppy.nodb.mods.rred import Rred
            rred = Rred.getInstance(wd)
            rred.build_landuse(self._mode)
            self = self.getInstance(wd)  # reload instance from .nodb
            self.build_managements()
            return

        with self.locked():
            if self._mode != LanduseMode.UserDefined:
                self.clean()
            if self._mode == LanduseMode.UserDefined:
                self._build_NLCD(retrieve_nlcd=False)
            elif self._mode == LanduseMode.Gridded:
                if 'au' in self.locales:
                    self._build_lu10v5ua()
                else:
                    self._build_NLCD()
            elif self._mode == LanduseMode.Single:
                self._build_single_selection()
            elif self._mode == LanduseMode.Undefined:
                raise Exception('LanduseMode is not set')

        self.build_managements()

        if 'rap' in self.mods:
            from wepppy.nodb.mods.rap import RAP
            with self.timed('  Calculating RAP'):
                rap = RAP.getInstance(wd)
                year = int(self.nlcd_db[-4:])
                rap.acquire_rasters(year)
                rap.analyze()
        else:
            rap = None

        if self.multi_ofe:
            self._build_multiple_ofe()

        self = Landuse.getInstance(wd)
        self.trigger(TriggerEvents.LANDUSE_DOMLC_COMPLETE)

        self = Landuse.getInstance(wd)
        self.build_managements()

        self.set_cover_defaults()
        if rap:
            self.logger.info('Calculating covers from RAP')

            cancov_d = {}
            for i, (topaz_id, dom) in enumerate(self.domlc_d.items()):
                if topaz_id.endswith('4'):
                    continue

                _tree_cov = rap.data[RAP_Band.TREE][topaz_id] / 100.0
                _shrub_cov = rap.data[RAP_Band.SHRUB][topaz_id] / 100.0
                _grass_cov = (rap.data[RAP_Band.ANNUAL_FORB_AND_GRASS][topaz_id] + rap.data[RAP_Band.PERENNIAL_FORB_AND_GRASS][topaz_id]) / 100.0

                man_summary = self.managements[dom]

                # rhem has rap but no disturbed class
                disturbed_class = getattr(man_summary, 'disturbed_class', None)
                self.logger.info(f'topaz_id: {topaz_id}\t dom:{dom}\t disturbed_class: {disturbed_class}')

                if disturbed_class is None or disturbed_class == '':
                    continue

                cancov = 0.0
                if disturbed_class in ['tall grass', 'grass high sev fire', 'grass moderate sev fire', 'grass low sev fire']:
                    cancov = _grass_cov
                elif disturbed_class in ['shrub', 'shrub high sev fire', 'shrub moderate sev fire', 'shrub low sev fire']:
                    cancov = _grass_cov + _shrub_cov
                elif disturbed_class in ['forest', 'young forest', 'forest high sev fire', 'forest moderate sev fire', 'forest low sev fire']:
                    cancov = _grass_cov + _shrub_cov + _tree_cov
                cancov_d[topaz_id] = max(cancov, 0.05)

#            self.logger.info(f"cancov: {cancov_d}")

            if cancov_d:
                self.hillslope_cancovs = cancov_d

            # need to find covers by landuse type
            area_data = {}
            for i, (topaz_id, dom) in enumerate(self.domlc_d.items()):
                if topaz_id.endswith('4'):
                    continue

                if dom not in area_data:
                    area_data[dom] = []

                area = watershed.hillslope_area(topaz_id)
                _cancov=cancov_d.get(topaz_id, None)
                if _cancov is not None:
                    area_data[dom].append(dict(area=area, cancov=_cancov))

            with self.locked():
                cancov = 0.0
                for dom, values in area_data.items():
                    dom_total_area = sum(d['area'] for d in values)
                    x = sum(d['area'] * d['cancov'] for d in values)
                    if dom_total_area > 0.0:
                        cancov = x / dom_total_area
                    self._modify_coverage(dom, 'cancov', cancov)

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.build_landuse)
        except FileNotFoundError:
            pass

        self._build_fractionals()

    def _build_fractionals(self) -> None:
        global wepppyo3

        fractionals = self.fractionals
        frac_dir = _join(self.lc_dir, 'fractionals')

        if len(fractionals) == 0:
            return

        os.makedirs(frac_dir, exist_ok=True)

        _map = self.ron_instance.map
        subwta_fn = self.watershed_instance.subwta

        frac_d = {}
        dom_d = {}
        for frac in fractionals:
            lc_fn = _join(frac_dir, frac.replace('/', '_') + '.tif')
            wmesque_retrieve(frac, _map.extent, lc_fn, _map.cellsize, 
                             v=self.wmesque_version, wmesque_endpoint=self.wmesque_endpoint)
            update_catalog_entry(self.wd, lc_fn)

            if wepppyo3 is None:
                lc = LandcoverMap(lc_fn)

                dom_d[frac] = lc.build_lcgrid(subwta_fn)
                frac_d[frac] = lc.calc_fractionals(subwta_fn)
            else:
                dom_d[frac] = identify_mode_single_raster_key(
                    key_fn=subwta_fn, parameter_fn=lc_fn, ignore_channels=True, ignore_keys=set())
                dom_d[frac] = {k: str(v) for k, v in dom_d[frac].items()}

                frac_d[frac] = identify_mode_single_raster_key(
                    key_fn=subwta_fn, parameter_fn=lc_fn, ignore_channels=True, ignore_keys=set())
                frac_d[frac] = {k: str(v) for k, v in frac_d[frac].items()}

        with open(_join(frac_dir, 'dom.json'), 'w') as fp:
            json.dump(dom_d, fp, indent=2)

        with open(_join(frac_dir, 'fractionals.json'), 'w') as fp:
            json.dump(frac_d, fp, indent=2)

    def _build_multiple_ofe(self) -> None:
        from wepppy.wepp.management.utils import ManagementMultipleOfeSynth
        from wepppy.nodb.mods.disturbed import Disturbed

        wd = self.wd

        watershed = self.watershed_instance
        disturbed = Disturbed.tryGetInstance(wd)
        if disturbed is not None:
            _land_soil_replacements_d = disturbed.land_soil_replacements_d
        else:
            _land_soil_replacements_d = None

        if wepppyo3 is None:
            lc = LandcoverMap(self.lc_fn)
            domlc_d = lc.build_lcgrid(watershed.subwta, watershed.mofe_map)
        else:
            domlc_d = identify_mode_intersecting_raster_keys(
                key_fn=watershed.subwta,
                key2_fn=watershed.mofe_map,
                parameter_fn=self.lc_fn
            )

            for k, v in domlc_d.items():
                for k2 in sorted(v.keys()):
                    domlc_d[k][k2] = str(v[k2])

        if disturbed is not None:
            disturbed_key_lookup = disturbed.get_disturbed_key_lookup()
            burn_shrubs = disturbed.burn_shrubs
            burn_grass = disturbed.burn_grass
            sbs = disturbed.get_sbs()

            sbs_lc_d = identify_mode_intersecting_raster_keys(
                key_fn=watershed.subwta,
                key2_fn=watershed.mofe_map,
                parameter_fn=disturbed.disturbed_cropped
            )
            
            for k, v in sbs_lc_d.items():
                for k2, v2 in v.items():
                    sbs_lc_d[k][k2] = str(v2)
                    
            class_pixel_map = sbs.class_pixel_map
           
            meta = {}
            for topaz_id, hill_sbs_d in sbs_lc_d.items():
                if (int(topaz_id) - 4) % 10 == 0:
                    continue

                for mofe_id, val in hill_sbs_d.items():
                    dom = domlc_d[topaz_id][mofe_id]
                    man = man = get_management_summary(dom, self.mapping)

                    burn_class = class_pixel_map[val]

                    if burn_class in ['131', '132', '133']:
                        if man.disturbed_class in ['forest', 'young forest']:
                            domlc_d[topaz_id][mofe_id] = {'131': disturbed_key_lookup['forest_low_sev_fire'], 
                                                          '132': disturbed_key_lookup['forest_moderate_sev_fire'], 
                                                          '133': disturbed_key_lookup['forest_high_sev_fire']}[burn_class]

                        elif man.disturbed_class == 'shrub' and burn_shrubs:
                            domlc_d[topaz_id][mofe_id] = {'131': disturbed_key_lookup['shrub_low_sev_fire'], 
                                                          '132': disturbed_key_lookup['shrub_moderate_sev_fire'], 
                                                          '133': disturbed_key_lookup['shrub_high_sev_fire']}[burn_class]
                            
                        elif man.disturbed_class in ['tall grass'] and burn_grass:
                            domlc_d[topaz_id][mofe_id] = {'131': disturbed_key_lookup['grass_low_sev_fire'], 
                                                          '132': disturbed_key_lookup['grass_moderate_sev_fire'], 
                                                          '133': disturbed_key_lookup['grass_high_sev_fire']}[burn_class]

                    meta[topaz_id] = dict(burn_class=burn_class, disturbed_class=man.disturbed_class)
        
        self.logger.info(f'domlc_d = {domlc_d}')

        if 'rap' in self.mods:
            self.logger.info(f'acquiring rap')
            from wepppy.nodb.mods.rap import RAP

            rap = RAP.getInstance(wd)
        else:
            rap = None


        lc_dir = self.lc_dir
        managements = self.managements

        watershed = self.watershed_instance
        cancov_d = {}
        for topaz_id in watershed._subs_summary:
            if rap is not None:
                cancov_d[topaz_id] = {}

            self.logger.info(f'building management for hillslope: {topaz_id}')

            nsegments = int(watershed.mofe_nsegments[str(topaz_id)])
            mofe_lc_fn = _join(lc_dir, f'hill_{topaz_id}.mofe.man')

            mofe_ids = sorted([_id for _id in domlc_d[str(topaz_id)]])
            #assert len(mofe_ids) == nsegments, (topaz_id, mofe_ids, nsegments, len(mofe_ids) )

            apply_buffer = watershed.mofe_buffer and not str(topaz_id).endswith('1')
            if apply_buffer:
                domlc_d[topaz_id][mofe_ids[-1]] = self.mofe_buffer_selection

            doms = [domlc_d[topaz_id][_id] for _id in mofe_ids]

            stack = []
            for i, dom in enumerate(doms):
                mofe_id = str(i + 1)

                if dom not in managements:
                    managements[dom] = get_management_summary(dom, self.mapping)

                management = managements[dom].get_management()
                disturbed_class = managements[dom].disturbed_class
                texid = 'sand loam'

                if disturbed_class is None or disturbed_class == '':
                    rdmax = None
                    xmxlai = None
                else:
                    if rap is not None:
                        _tree_cov = rap.mofe_data[RAP_Band.TREE][topaz_id][mofe_id] / 100.0
                        _shrub_cov = rap.mofe_data[RAP_Band.SHRUB][topaz_id][mofe_id] / 100.0
                        _grass_cov = (rap.mofe_data[RAP_Band.ANNUAL_FORB_AND_GRASS][topaz_id][mofe_id] + rap.mofe_data[RAP_Band.PERENNIAL_FORB_AND_GRASS][topaz_id][mofe_id]) / 100.0
                        cancov = 0.0
                        if disturbed_class in ['tall grass', 'grass high sev fire', 'grass moderate sev fire', 'grass low sev fire']:
                            cancov = _grass_cov
                        elif disturbed_class in ['shrub', 'shrub high sev fire', 'shrub moderate sev fire', 'shrub low sev fire']:
                            cancov = _grass_cov + _shrub_cov
                        elif disturbed_class in ['forest', 'young forest', 'forest high sev fire', 'forest moderate sev fire', 'forest low sev fire']:
                            cancov = _grass_cov + _shrub_cov + _tree_cov
                        cancov_d[topaz_id][mofe_id] = max(cancov, 0.05)

                        management.set_cancov(cancov_d[topaz_id][mofe_id])

                    if (texid, disturbed_class) in _land_soil_replacements_d:
                        rdmax = _land_soil_replacements_d[(texid, disturbed_class)]['rdmax']
                        xmxlai = _land_soil_replacements_d[(texid, disturbed_class)]['xmxlai']

                if rdmax is not None:
                    if isfloat(rdmax):
                        management.set_rdmax(float(rdmax))

                if xmxlai is not None:
                    if isfloat(xmxlai):
                        management.set_xmxlai(float(xmxlai))

                stack.append(management)

            assert len(stack) > 0, topaz_id
            assert len(stack) == nsegments, (topaz_id, len(stack),  nsegments)

            if len(stack) == 1:
                with open(mofe_lc_fn, 'w') as pf:
                    pf.write(str(stack[0]))
            else:

                self.logger.info(f"building management for hillslope: {topaz_id} with doms {doms}")
                mofe_synth = ManagementMultipleOfeSynth()

                # just replicate the dom
                mofe_synth.stack = stack
                merged = mofe_synth.write(mofe_lc_fn)

        with self.locked():
            if cancov_d:
                self._hillslope_mofe_cancovs = cancov_d
            self.domlc_mofe_d = domlc_d
            self.managements = managements

    def identify_disturbed_class(
        self, 
        topaz_id: str, 
        mofe_id: Optional[str] = None
    ) -> Optional[str]:

        if mofe_id is None:
            dom = self.domlc_d[str(topaz_id)]
        else:
            dom = self.domlc_mofe_d[str(topaz_id)][str(mofe_id)]

        man = self.managements[dom]
        if disturbed_class is None or disturbed_class == '':
            return ''
            
        disturbed_class = man.disturbed_class.lower()

        if 'forest' in disturbed_class:
            return 'forest'

        elif 'shrub' in disturbed_class:
            return 'shrub'

        if 'grass' in disturbed_class:
            return 'grass'

        return ''

    def identify_burn_class(
        self, 
        topaz_id: str, 
        mofe_id: Optional[str] = None
    ) -> Optional[str]:

        if mofe_id is None:
            dom = self.domlc_d[str(topaz_id)]
        else:
            dom = self.domlc_mofe_d[str(topaz_id)][str(mofe_id)]

        man = self.managements[dom]
        desc = man.desc.lower()

        if 'unburned' in desc:
            return 'Unburned'

        if 'sev' not in desc or 'fire' not in desc:
            return 'Unburned'

        if 'low' in desc or 'prescribed' in desc:
            return 'Low'

        elif 'mod' in desc:
            return 'Moderate'

        elif 'high' in desc:
            return 'High'

        return 'Unburned'

    def set_cover_defaults(self) -> None:

        defaults = self.cover_defaults_d

        if defaults is None:
            return

        with self.locked():
            for dom in self.managements:
                dom = str(dom)
                if dom in defaults:
                    for cover in ['cancov', 'inrcov', 'rilcov']:
                        self._modify_coverage(dom, cover, defaults[dom][cover])

    def _modify_coverage(
        self, 
        dom: str, 
        cover: str, 
        value: float
    ) -> None:
        if not self.islocked():
            raise Exception('must be locked to call _modify_coverage')
        
        dom = str(dom)
        assert dom in self.managements

        assert cover in ['cancov', 'inrcov', 'rilcov']

        value = float(value)
        assert value >= 0.0
        assert value <= 1.0

        if cover == 'cancov':
            self.managements[dom].cancov_override = value
        elif cover == 'inrcov':
            self.managements[dom].inrcov_override = value
        elif cover == 'rilcov':
            self.managements[dom].rilcov_override = value

    def modify_coverage(
        self, 
        dom: str, 
        cover: str, 
        value: float
    ) -> None:
        with self.locked():
            self._modify_coverage(dom, cover, value)

    def modify_mapping(self, dom: str, newdom: str) -> None:
        with self.locked():
            dom = str(dom)
            newdom = str(newdom)
            assert dom in self.managements

            for topazid in self.domlc_d:
                if self.domlc_d[topazid] == dom:
                    self.domlc_d[topazid] = newdom

            self = self.getInstance(self.wd)  # reload instance from .nodb

        self.build_managements()

    @property
    def landuseoptions(self) -> Dict:
        return [
            dataset.to_mapping()
            for dataset in self.available_datasets
            if dataset.kind == "mapping"
        ]

    @property
    def available_datasets(self) -> List[LanduseDataset]:
        return available_landuse_datasets(self.mapping, self.mods, self.locales)

    @property
    def landcover_datasets(self) -> List[LanduseDataset]:
        return [dataset for dataset in self.available_datasets if dataset.kind == "landcover"]

    @property
    def coverage_percentages(self) -> Tuple[float, ...]:
        return _COVERAGE_PERCENTAGES

    def build_managements(self, _map: Optional[str] = None) -> None:
        if _map is None:
            _map = self.mapping

        with self.locked(): 
            watershed = self.watershed_instance
            ron = self.ron_instance
            cell2 = ron.cellsize ** 2
            domlc_d = self.domlc_d

            subwta, transform, proj = read_raster(watershed.subwta, dtype=np.int32)
            if self.multi_ofe:
                mofe_map, transform_m, proj_m = \
                    read_raster(watershed.mofe_map, dtype=np.int32)

            # create a dictionary of management keys and
            # wepppy.landcover.ManagementSummary values
            managements = {}

            # while we are at it we will calculate the pct coverage
            # for the landcover types in the watershed
            total_area = 0.0
            for topaz_id, k in domlc_d.items():
                area = len(np.where(subwta == int(topaz_id))[0])
                area *= cell2 / 10000

                if k not in managements:
                    man = get_management_summary(k, _map)
                    man.area = area
                    managements[k] = man
                else:
                    managements[k].area += area

                if self.multi_ofe:
                    managements[k].area = 0

                total_area += area

            if not hasattr(self, 'domlc_mofe_d'):
                self.domlc_mofe_d = None

            if self.multi_ofe and self.domlc_mofe_d is not None:
                total_area = 0.0
                for topaz_id in self.domlc_mofe_d:
                    for _id, k in self.domlc_mofe_d[topaz_id].items():
                        area = len(np.where((subwta == int(topaz_id)) &
                                            (mofe_map == int(_id)))[0])
                        area *= cell2 / 10000

                        if k not in managements:
                            man = get_management_summary(k, _map)
                            man.area = area
                            managements[k] = man
                        else:
                            managements[k].area += area
                        total_area += area

            for k in managements:
                coverage = 100.0 * managements[k].area / total_area
                managements[k].pct_coverage = coverage

            # store the managements dict
            self.managements = managements

        self.dump_landuse_parquet()
        self.trigger(TriggerEvents.LANDUSE_BUILD_COMPLETE)

    @property
    def report(self) -> str:
        """
        returns a list of managements sorted by coverage in
        descending order
        """
        used_mans = [dom for dom, man in self.managements.items() if man.area > 0]
        report = [self.managements[str(dom)] for dom in used_mans]
        report.sort(key=lambda x: x.pct_coverage, reverse=True)
        return [man.as_dict() for man in report]

    #
    # modify
    #
    def modify(self, topaz_ids: List[str], landuse: str) -> None:
        with self.locked():
            landuse = str(int(landuse))
            assert self.domlc_d is not None

            for topaz_id in topaz_ids:
                assert topaz_id in self.domlc_d
                self.domlc_d[topaz_id] = landuse

        self.build_managements()
        self.set_cover_defaults()

    def _x_summary(self, topaz_id: str):
        
        if _exists(_join(self.lc_dir, 'landuse.parquet')):
            return get_landuse_sub_summary(self.wd, topaz_id)
        
        return self._deprecated_x_summary(topaz_id)
        
    @deprecated
    def _deprecated_x_summary(self, topaz_id: str):
        topaz_id = str(topaz_id)
        domlc_d = self.domlc_d

        if domlc_d is None:
            return None

        if str(topaz_id) in domlc_d:
            dom = str(domlc_d[topaz_id])
            d = self.managements[dom].as_dict()

            if self.hillslope_cancovs:
                d['cancov'] = self._hillslope_cancovs.get(topaz_id, d['cancov'])
            return d
        else:
            return None

    @property
    def legend(self) -> List[str]:
        doms = sorted(set(self.domlc_d.values()))
        mans = [self.managements[dom] for dom in doms]
        descs = [man.desc for man in mans]
        colors = [man.color for man in mans]

        return list(zip(doms, descs, colors))

    def sub_summary(self, topaz_id: str):
        return self._x_summary(topaz_id)

    def chn_summary(self, topaz_id: str) -> Optional[Dict]:
        return self._x_summary(topaz_id)

    @property
    def hillslope_cancovs(self) -> Optional[List]:
        return getattr(self, '_hillslope_cancovs', None)

    @hillslope_cancovs.setter
    @nodb_setter
    def hillslope_cancovs(self, value):
        self._hillslope_cancovs = value

    @property
    def hillslope_mofe_cancovs(self) -> Optional[List]:
        return getattr(self, '_hillslope_mofe_cancovs', None)

    @property
    def subs_summary(self) -> Dict:
        """
        Returns a dictionary with topaz_id keys and dictionary soils values.
        """
        if _exists(_join(self.lc_dir, 'landuse.parquet')):
            return get_landuse_subs_summary(self.wd)
            
        return self._subs_summary_gen()
        
    def _subs_summary_gen(self):

        domlc_d = self.domlc_d
        mans = self.managements

        if domlc_d is None:
            return None

        man_dicts_cache = {dom: man.as_dict() for dom, man in mans.items()}

        # Compile the summary using cached soil dictionaries
        summary = {
            topaz_id: deepcopy(man_dicts_cache[dom])
            for topaz_id, dom in domlc_d.items()
            if not is_channel(topaz_id)
        }

        hillslope_cancovs = self.hillslope_cancovs

        if hillslope_cancovs is not None:
            for topaz_id in hillslope_cancovs:
                summary[topaz_id].update(dict(cancov=hillslope_cancovs[topaz_id]))

        return summary

    def dump_landuse_parquet(self) -> None:
        """
        Dumps the subs_summary to a Parquet file using Pandas.
        """
        dict_result = self._subs_summary_gen()
        if dict_result is None or len(dict_result) == 0:
            return
            
        df = pd.DataFrame.from_dict(dict_result, orient='index')
        df.index.name = 'topaz_id'
        df.reset_index(inplace=True)

        df['topaz_id'] = pd.to_numeric(df['topaz_id'], errors='raise').astype('Int32')

        translator = None
        try:
            translator = self.watershed_instance.translator_factory()
        except Exception:
            translator = None

        if 'wepp_id' in df.columns:
            df['wepp_id'] = pd.to_numeric(df['wepp_id'], errors='coerce').astype('Int32')
        else:
            if translator is not None:
                wepp_values = []
                for top in df['topaz_id']:
                    if pd.isna(top):
                        wepp_values.append(pd.NA)
                    else:
                        try:
                            value = translator.wepp(top=int(top))
                        except Exception:
                            value = None
                        wepp_values.append(value if value is not None else pd.NA)
                df['wepp_id'] = pd.Series(pd.array(wepp_values, dtype='Int32'))
            else:
                df['wepp_id'] = pd.Series(pd.array([pd.NA] * len(df), dtype='Int32'))

        for legacy_col in ('TopazID', 'WeppID'):
            if legacy_col in df.columns:
                df.drop(columns=[legacy_col], inplace=True)

        preferred_order = ['topaz_id', 'wepp_id']
        remaining = [c for c in df.columns if c not in preferred_order]
        df = df.loc[:, preferred_order + remaining]

        df.to_parquet(_join(self.lc_dir, 'landuse.parquet'), index=False)
        update_catalog_entry(self.wd, 'landuse/landuse.parquet')

    @property
    def hill_table(self) -> List[Dict]:
        """
        Returns a pandas DataFrame with the hill table.
        """
        if _exists(_join(self.lc_dir, 'landuse.parquet')):
            return get_landuse_subs_summary(self.wd, return_as_df=True)
        
        return self._deprecated_hill_table()

    @deprecated
    def _deprecated_hill_table(self):
        
        dict_result = self._subs_summary_gen()
        df = pd.DataFrame.from_dict(dict_result, orient='index')
        df.index.name = 'topaz_id'
        df.reset_index(inplace=True)
        df['topaz_id'] = pd.to_numeric(df['topaz_id'], errors='raise').astype('Int32')

        translator = None
        try:
            translator = self.watershed_instance.translator_factory()
        except Exception:
            translator = None

        if translator is not None:
            wepp_values = []
            for top in df['topaz_id']:
                if pd.isna(top):
                    wepp_values.append(pd.NA)
                else:
                    try:
                        value = translator.wepp(top=int(top))
                    except Exception:
                        value = None
                    wepp_values.append(value if value is not None else pd.NA)
            df['wepp_id'] = pd.Series(pd.array(wepp_values, dtype='Int32'))
        else:
            df['wepp_id'] = pd.Series(pd.array([pd.NA] * len(df), dtype='Int32'))

        return df
    
    def sub_iter(self):
        domlc_d = self.domlc_d
        mans = self.managements

        assert mans is not None

        if domlc_d is not None:
            for topaz_id, k in domlc_d.items():
                if is_channel(topaz_id):
                    continue

                yield topaz_id, mans[k]

    @property
    def chns_summary(self) -> Dict:
        """
        returns a dictionary of topaz_id keys and jsonified
        managements values
        """
        domlc_d = self.domlc_d
        mans = self.managements

        assert mans is not None

        summary = {}
        for topaz_id, k in domlc_d.items():
            if not is_channel(topaz_id):
                continue

            summary[topaz_id] = mans[k].as_dict()

        return summary

    def chn_iter(self):
        domlc_d = self.domlc_d
        mans = self.managements

        if domlc_d is not None:
            for topaz_id, k in domlc_d.items():
                if not is_channel(topaz_id):
                    continue

                yield topaz_id, mans[k]

    # gotcha: using __getitem__ breaks jinja's attribute lookup, so...
    def _(self, wepp_id):
        wd = self.wd

        translator = self.watershed_instance.translator_factory()
        topaz_id = str(translator.top(wepp=int(wepp_id)))
        domlc_d = self.domlc_d

        if topaz_id in domlc_d:
            key = domlc_d[topaz_id]
            return self.managements[key]

        raise IndexError
