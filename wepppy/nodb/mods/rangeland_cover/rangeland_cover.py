# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
import shutil

from os.path import join as _join
from os.path import exists as _exists

from copy import deepcopy

from enum import IntEnum

import time

from glob import glob
from datetime import datetime

import numpy as np
from osgeo import gdal

from wepppy.all_your_base import cmyk_to_rgb, RGBA
from wepppy.landcover import LandcoverMap
from wepppy.nodb.core import Watershed
from ...base import NoDbBase, TriggerEvents, nodb_setter

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


def gen_cover_color(cover):
    rock = cover['rock']
    litter = cover['litter']
    forbs = cover['forbs']
    bunchgrass = cover['bunchgrass']
    sodgrass = cover['sodgrass']

    annual_perennial_tot = forbs + bunchgrass + sodgrass
    if annual_perennial_tot == 0.0:
        m = 1.0
        c = 1.0
    else:
        m = (cover['bunchgrass'] + cover['sodgrass']) / annual_perennial_tot
        c = cover['forbs'] / annual_perennial_tot

    y = (100.0 - cover['shrub']) / 100.0

    if litter > rock:
        k = 0.2 - litter / 100 * 0.2
    else:
        k = 0.2 + rock / 100 * 0.2

    r, g, b = cmyk_to_rgb(c, m, y, k)

    return RGBA(*[int(v * 255) for v in [r, g, b, 1.0]]).tohex()


class RangelandCoverNoDbLockedException(Exception):
    pass


class RangelandCoverMode(IntEnum):
    Undefined = -1
    Gridded = 0
    Single = 1
    GriddedRAP = 2


class RangelandCover(NoDbBase):
    __name__ = 'RangelandCover'

    filename = 'rangeland_cover.nodb'
    
    def __init__(self, wd, cfg_fn, run_group=None, group_name=None):
        super(RangelandCover, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            self._mode = RangelandCoverMode(self.config_get_int('rhem', 'mode'))
            self._rap_year = self.config_get_int('rhem', 'rap_year')

            self._bunchgrass_cover_default = 15.0
            self._forbs_cover_default = 5.0
            self._sodgrass_cover_default = 20.0
            self._shrub_cover_default = 30.0

            self._basal_cover_default = 20.0
            self._rock_cover_default = 10.0
            self._litter_cover_default = 25.0
            self._cryptogams_cover_default = 5.0

            self.covers = None

    def on(self, evt):
        pass

    @property
    def rap_year(self):
        return getattr(self, '_rap_year', self.config_get_int('rhem', 'rap_year'))

    @rap_year.setter
    @nodb_setter
    def rap_year(self, value: int):
        self._rap_year = value

    @property
    def mode(self):
        return self._mode

    @mode.setter
    @nodb_setter
    def mode(self, value):
        if isinstance(value, RangelandCoverMode):
            self._mode = value
        elif isinstance(value, int):
            self._mode = RangelandCoverMode(value)
        else:
            raise ValueError('most be RangelandCoverMode or int')
            
    @property
    def bunchgrass_cover_default(self):
        return self._bunchgrass_cover_default

    @bunchgrass_cover_default.setter
    @nodb_setter
    def bunchgrass_cover_default(self, value):
        self._bunchgrass_cover_default = value

    @property
    def forbs_cover_default(self):
        return self._forbs_cover_default

    @forbs_cover_default.setter
    @nodb_setter
    def forbs_cover_default(self, value):
        self._forbs_cover_default = value
            
    @property
    def sodgrass_cover_default(self):
        return self._sodgrass_cover_default

    @sodgrass_cover_default.setter
    @nodb_setter
    def sodgrass_cover_default(self, value):
        self._sodgrass_cover_default = value

    @property
    def shrub_cover_default(self):
        return self._shrub_cover_default

    @shrub_cover_default.setter
    @nodb_setter
    def shrub_cover_default(self, value):
        self._shrub_cover_default = value
            
    @property
    def basal_cover_default(self):
        return self._basal_cover_default

    @basal_cover_default.setter
    @nodb_setter
    def basal_cover_default(self, value):
        self._basal_cover_default = value
            
    @property
    def rock_cover_default(self):
        return self._rock_cover_default

    @rock_cover_default.setter
    @nodb_setter
    def rock_cover_default(self, value):
        self._rock_cover_default = value

    @property
    def litter_cover_default(self):
        return self._litter_cover_default

    @litter_cover_default.setter
    @nodb_setter
    def litter_cover_default(self, value):
        self._litter_cover_default = value

    @property
    def cryptogams_cover_default(self):
        return self._cryptogams_cover_default

    @cryptogams_cover_default.setter
    @nodb_setter
    def cryptogams_cover_default(self, value):
        self._cryptogams_cover_default = value

    def set_default_covers(self, default_covers):
        with self.locked():
            v = default_covers['bunchgrass']
            self._bunchgrass_cover_default = float(v)

            v = default_covers['forbs']
            self._forbs_cover_default = float(v)

            v = default_covers['sodgrass']
            self._sodgrass_cover_default = float(v)

            v = default_covers['shrub']
            self._shrub_cover_default = float(v)

            v = default_covers['basal']
            self._basal_cover_default = float(v)

            v = default_covers['rock']
            self._rock_cover_default = float(v)

            v = default_covers['litter']
            self._litter_cover_default = float(v)

            v = default_covers['cryptogams']
            self._cryptogams_cover_default = float(v)

    def build(self, rap_year=None, default_covers=None):
        if default_covers is not None:
            self.set_default_covers(default_covers)

        mode = self.mode
        if mode == RangelandCoverMode.Gridded:
            self._build_gridded_usgs_shrubland()
        elif mode == RangelandCoverMode.GriddedRAP:
            self._build_gridded_rap(rap_year)
        elif mode == RangelandCoverMode.Single:
            self._build_single()
        else:
            raise NotImplementedError() 

    def _build_single(self):
        wd = self.wd

        with self.locked():
            watershed = Watershed.getInstance(wd)
            covers = {}
            for topaz_id in watershed._subs_summary:
                cover = dict(bunchgrass=self._bunchgrass_cover_default,
                             forbs=self._forbs_cover_default,
                             sodgrass=self._sodgrass_cover_default,
                             shrub=self._shrub_cover_default,
                             basal=self._basal_cover_default,
                             rock=self._rock_cover_default,
                             litter=self._litter_cover_default,
                             cryptogams=self._cryptogams_cover_default)
                covers[topaz_id] = cover

            self.covers = covers

    @property
    def rap_report(self):
        from wepppy.nodb.mods import RAP
        return RAP.getInstance(self.wd).report

    def _build_gridded_rap(self, rap_year=None):
        wd = self.wd
        from wepppy.nodb.mods import RAP

        with self.locked():
            if rap_year is not None:
                rap_year = int(rap_year)
                self._rap_year = rap_year

            rap = RAP.getInstance(wd)
            rap.acquire_rasters(year=self.rap_year)
            rap.analyze()

            covers = {}

            for topaz_id, rap_data in rap:
                if not rap_data.isvalid:
                    cover = dict(bunchgrass=self._bunchgrass_cover_default,
                                 forbs=self._forbs_cover_default,
                                 sodgrass=self._sodgrass_cover_default,
                                 shrub=self._shrub_cover_default,
                                 basal=self._basal_cover_default,
                                 rock=self._rock_cover_default,
                                 litter=self._litter_cover_default,
                                 cryptogams=self._cryptogams_cover_default)
                else:
                    annual_forb_and_grass_normalized = rap_data.annual_forb_and_grass_normalized
                    bare_ground_normalized = rap_data.bare_ground_normalized
                    litter_normalized = rap_data.litter_normalized
                    perennial_forb_and_grass_normalized = rap_data.perennial_forb_and_grass_normalized
                    shrub_normalized = rap_data.shrub_normalized
                    tree_normalized = rap_data.tree_normalized

                    annual_fraction = annual_forb_and_grass_normalized / (annual_forb_and_grass_normalized + perennial_forb_and_grass_normalized)
                    perennial_fraction = 1.0 - annual_fraction

                    # assuming forb / (annual_grass + perenial_grass) = annual_forb / annual_grass = perennial_forb / perennial_grass
                    est_forb_fraction = self._forbs_cover_default / (self._forbs_cover_default + self._bunchgrass_cover_default + self._sodgrass_cover_default)

                    bunchgrass = perennial_forb_and_grass_normalized * (1.0 - est_forb_fraction)
                    sodgrass = annual_forb_and_grass_normalized *  (1.0 - est_forb_fraction)   
                    shrub_cover = shrub_normalized
                    basal = shrub_cover + perennial_forb_and_grass_normalized + annual_forb_and_grass_normalized
                    forbs = perennial_forb_and_grass_normalized * est_forb_fraction + annual_forb_and_grass_normalized * est_forb_fraction

                    assert basal + \
                           bare_ground_normalized + \
                           litter_normalized <= 100.01, shrubland_data

                    cryptogams = self._cryptogams_cover_default
                    if basal + \
                       bare_ground_normalized + \
                       litter_normalized + \
                       self._cryptogams_cover_default > 100.0:
                        cryptogams = 100.0 - basal - bare_ground_normalized - litter_normalized

                    rock = 100.0 - \
                           basal - \
                           bare_ground_normalized - \
                           litter_normalized - \
                           cryptogams

                    

                    cover = dict(bunchgrass=bunchgrass,
                                 forbs=forbs,
                                 sodgrass=sodgrass,
                                 shrub=shrub_cover,
                                 basal=basal,
                                 rock=rock,
                                 litter=litter_normalized,
                                 cryptogams=self._cryptogams_cover_default)

                covers[topaz_id] = cover

            self.covers = covers

    @property
    def usgs_shrubland_report(self):
        from wepppy.nodb.mods import Shrubland
        return Shrubland.getInstance(self.wd).report

    def _build_gridded_usgs_shrubland(self):
        wd = self.wd
        from wepppy.nodb.mods import Shrubland, nlcd_shrubland_layers

        with self.locked():
            shrubland = Shrubland.getInstance(wd)
            shrubland.acquire_rasters()
            shrubland.analyze()

            covers = {}

            for topaz_id, shrubland_data in shrubland:
                if not shrubland_data.isvalid:
                    cover = dict(bunchgrass=self._bunchgrass_cover_default,
                                 forbs=self._forbs_cover_default,
                                 sodgrass=self._sodgrass_cover_default,
                                 shrub=self._shrub_cover_default,
                                 basal=self._basal_cover_default,
                                 rock=self._rock_cover_default,
                                 litter=self._litter_cover_default,
                                 cryptogams=self._cryptogams_cover_default)
                else:
                    herbaceous_normalized = shrubland_data.herbaceous_normalized
                    sagebrush_normalized = shrubland_data.sagebrush_normalized
                    shrub_normalized = shrubland_data.shrub_normalized
                    big_sagebrush_normalized = shrubland_data.big_sagebrush_normalized
                    bare_ground_normalized = shrubland_data.bare_ground_normalized
                    litter_normalized = shrubland_data.litter_normalized

                    bunchgrass = herbaceous_normalized * 0.2
                    sodgrass = herbaceous_normalized * 0.8
                    shrub_cover = sagebrush_normalized + \
                                  shrub_normalized + \
                                  big_sagebrush_normalized
                    basal = shrub_cover + herbaceous_normalized

                    assert basal + \
                           bare_ground_normalized + \
                           litter_normalized <= 100.01, shrubland_data

                    cryptogams = self._cryptogams_cover_default
                    if basal + \
                       bare_ground_normalized + \
                       litter_normalized + \
                       self._cryptogams_cover_default > 100.0:
                        cryptogams = 100.0 - basal - bare_ground_normalized - litter_normalized

                    rock = 100.0 - \
                           basal - \
                           bare_ground_normalized - \
                           litter_normalized - \
                           cryptogams

                    cover = dict(bunchgrass=bunchgrass,
                                 forbs=shrubland_data.annual_herb,
                                 sodgrass=sodgrass,
                                 shrub=shrub_cover,
                                 basal=basal,
                                 rock=rock,
                                 litter=shrubland_data.litter,
                                 cryptogams=self._cryptogams_cover_default)

                covers[topaz_id] = cover

            self.covers = covers
            
    @property
    def has_covers(self):
        return self.covers is not None

    def current_cover_summary(self, topaz_ids):
        covers = self.covers
        if covers is None or len(topaz_ids) == 0:
            return dict(bunchgrass='',
                        forbs='',
                        sodgrass='',
                        shrub='',
                        basal='',
                        rock='',
                        litter='',
                        cryptogams='')

        sub_covers = dict(bunchgrass=set(),
                          forbs=set(),
                          sodgrass=set(),
                          shrub=set(),
                          basal=set(),
                          rock=set(),
                          litter=set(),
                          cryptogams=set())

        for topaz_id in topaz_ids:
            assert topaz_id in covers, topaz_id
            cover = covers[topaz_id]
            for measure in sub_covers:
                sub_covers[measure].add(round(cover[measure]))

        for measure in sub_covers:
            if len(sub_covers[measure]) > 1:
                sub_covers[measure] = '-'
            else:
                sub_covers[measure] = str(sub_covers[measure].pop())

        return sub_covers

    def modify_covers(self, topaz_ids, new_cover):
        for topaz_id in topaz_ids:
            assert topaz_id in self.covers, (topaz_id, self.covers)

        with self.locked():
            covers = self.covers

            for topaz_id in topaz_ids:
                for measure, value in new_cover.items():
                    covers[topaz_id][measure] = value

            self.covers = covers
            
    @property
    def subs_summary(self):
        """
        returns a dictionary of topaz_id keys and
        management summaries as dicts
        """
        covers = deepcopy(self.covers)

        for topaz_id, cover in covers.items():
            covers[topaz_id]['color'] = gen_cover_color(cover)

        return covers
