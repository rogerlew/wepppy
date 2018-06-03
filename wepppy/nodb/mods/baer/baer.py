# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
import ast
import shutil
from collections import Counter
import jsonpickle

from subprocess import Popen, PIPE
from os.path import join as _join
from os.path import exists as _exists

import numpy as np
from osgeo import gdal
        
from wepppy.all_your_base import wgs84_proj4, isint
from wepppy.wepp.soilbuilder.webClient import SoilSummary

from ...landuse import Landuse
from ...soils import Soils
from ...watershed import Watershed
from ...ron import Ron
from ...topaz import Topaz
from ...base import NoDbBase, TriggerEvents

from .sbs_map import SoilBurnSeverityMap

gdal.UseExceptions()

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


class BaerNoDbLockedException(Exception):
    pass


class Baer(NoDbBase):
    __name__ = 'Baer'

    def __init__(self, wd, config):
        super(Baer, self).__init__(wd, config)

        self.lock()

        # noinspection PyBroadException
        try:
            os.mkdir(self.baer_dir)
            
            self._baer_fn = None
            self._bounds = None
            self._classes = None
            self._breaks = None
            self._counts = None
            self._nodata_vals = None
            self._is256 = None
            
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
            
    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd):
        with open(_join(wd, 'baer.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Baer), db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'baer.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'baer.nodb.lock')
        
    @property
    def baer_dir(self):
        return _join(self.wd, 'baer')
            
    @property
    def baer_soils_dir(self):
        return _join(_data_dir, 'soils')
        
    @property
    def baer_fn(self):
        return self._baer_fn
            
    @property
    def has_map(self):
        return self._baer_fn is not None
        
    @property
    def is256(self):
        return self._is256 is not None
        
    @property
    def color_tbl_path(self):
        return _join(self.baer_dir, 'color_table.txt')
        
    @property
    def bounds(self):
        return self._bounds
        
    @property
    def classes(self):
        return self._classes
        
    @property
    def breaks(self):
        return self._breaks

    @property
    def nodata_vals(self):
        if self._nodata_vals is None:
            return ''

        return ', '.join(str(v) for v in self._nodata_vals)

    def classify(self, v):

        if self._nodata_vals is not None:
            if v in self._nodata_vals:
                return 'No Data'

        i = 0
        for i, brk in enumerate(self.breaks):
            if v <= brk:
                break
                
        return ('No Burn', 
                'Low Severity Burn', 
                'Medium Severity Burn', 
                'High Severity Burn')[i]
    
    @property
    def baer_path(self):
        if self._baer_fn is None:
            return None
            
        return _join(self.baer_dir, self._baer_fn)
            
    @property
    def baer_wgs(self):
        baer_path = self.baer_path
        return baer_path[:-4] + '.wgs' + baer_path[-4:]
        
    @property
    def baer_rgb(self):
        return self.baer_wgs[:-4] + '.rgb.vrt'
       
    @property
    def baer_rgb_png(self):
        return _join(self.baer_dir, 'baer.wgs.rgba.png')
        
    @property
    def baer_cropped(self):
        return _join(self.baer_dir, 'baer.tif')
        
    def write_color_table(self):
        breaks = self.breaks
        assert len(breaks) == 4

        with open(self.color_tbl_path, 'w') as fp:
            if self._nodata_vals is not None:
                for v in self._nodata_vals:
                    fp.write("{} 0 0 0".format(v))

            fp.write("{} 46 203 24\n"
                     "{} 161 250 220\n"
                     "{} 255 161 5\n"
                     "{} 217 34 3\n"
                     "nv 0 0 0".format(*breaks))

    def build_color_map(self):
        baer_rgb = self.baer_rgb
        if _exists(baer_rgb):
            os.remove(baer_rgb)
        
        cmd = ['gdaldem', 'color-relief', '-of', 'VRT',  self.baer_wgs, self.color_tbl_path, baer_rgb]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()
            
        baer_rgb_png = self.baer_rgb_png
        if _exists(baer_rgb_png):
            os.remove(baer_rgb_png)

        cmd = ['gdal_translate', '-of', 'PNG', baer_rgb, baer_rgb_png]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()
        
    @property
    def class_map(self):
        return [(v, self.classify(v), self._counts[str(v)]) for v in self.classes]
            
    def modify_burn_class(self, breaks, nodata_vals):
        self.lock()

        # noinspection PyBroadException
        try:
            assert len(breaks) == 4
            assert breaks[0] <= breaks[1]
            assert breaks[1] <= breaks[2]
            assert breaks[2] <= breaks[3]

            self._breaks = breaks
            if nodata_vals.strip() != '':
                _nodata_vals = ast.literal_eval('[{}]'.format(nodata_vals))
                assert all(isint(v) for v in _nodata_vals)
                self._nodata_vals = _nodata_vals
                
            self.write_color_table()
            self.build_color_map()

            self.dump_and_unlock()
            
        except Exception:
            self.unlock('-f')
            raise
            
    def validate(self, fn):
        self.lock()

        # noinspection PyBroadException
        try:
            print('baer path', self.baer_path)
            self._baer_fn = fn
            baer_path = self.baer_path
            print('baer path', baer_path)
            assert _exists(baer_path), baer_path
            
            ds = gdal.Open(baer_path)
            assert ds is not None
            del ds

            # transform to WGS1984 to display on map
            baer_wgs = self.baer_wgs 
            if _exists(baer_wgs):
                os.remove(baer_wgs)
                
            cmd = ['gdalwarp', '-t_srs', wgs84_proj4, 
                   '-r', 'near', baer_path, baer_wgs]
            p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            p.wait()
            
            ds = gdal.Open(baer_wgs)
            assert ds is not None
            
            transform = ds.GetGeoTransform()
            data = np.array(ds.GetRasterBand(1).ReadAsArray(), dtype=np.int)
            del ds
            
            # need the bounds for Leaflet
            sw_x = transform[0] 
            sw_y = transform[3] + transform[5] * data.shape[0]
            
            ne_x = transform[0] + transform[1] * data.shape[1]
            ne_y = transform[3]
            
            self._bounds = [[sw_y, sw_x], [ne_y, ne_x]]
            
            # build rgba for interface
            
            # determine classes
            classes = list(set(data.flatten()))
            classes = [int(v) for v in classes]
            counts = Counter(data.flatten())
            
            is256 = len(classes) > 6 or max(classes) >= 255
            
            if is256:
                breaks = [0, 76, 110, 188]
            else:
                breaks = [0, 1, 2, 3]
            
            self._is256 = is256
            self._classes = classes
            self._counts = {str(k): v for k, v in counts.items()}
            self._breaks = breaks
            
            self.write_color_table()
            self.build_color_map()

            self.dump_and_unlock()
            
        except Exception:
            self.unlock('-f')
            raise
        
    def on(self, evt):
        if evt == TriggerEvents.LANDUSE_DOMLC_COMPLETE:
            self.remap_landuse()
            
        elif evt == TriggerEvents.SOILS_BUILD_COMPLETE:
            self.modify_soils()
            
        """
        elif evt == TriggerEvents.PREPPING_PHOSPHORUS:
            self.determine_phosphorus
        """
        
    def remap_landuse(self):
        wd = self.wd
        baer_path = self.baer_path
            
        baer_cropped = self.baer_cropped
        if _exists(baer_cropped):
            os.remove(baer_cropped)

        topaz = Topaz.getInstance(wd)
        utmproj = topaz.utmproj4
        xmin, ymin, xmax, ymax = [str(v) for v in topaz.utmextent]
        cellsize = str(Ron.getInstance(wd).map.cellsize)
            
        cmd = ['gdalwarp', '-t_srs',  utmproj,
               '-tr', cellsize, cellsize,
               '-te', xmin, ymin, xmax, ymax, 
               '-r', 'near', baer_path, baer_cropped]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()
        
        assert _exists(baer_cropped), ' '.join(cmd)

        landuse = Landuse.getInstance(wd)
        landuse.lock()

        # noinspection PyBroadException
        try:
            # create LandcoverMap instance
            def _classify(v):
                i = 0

                if self._nodata_vals is not None:
                    if v in self._nodata_vals:
                        return 130

                for i, brk in enumerate(self.breaks):
                    if v <= brk:
                        break
                return i + 130
                
            sbs = SoilBurnSeverityMap(baer_cropped, _classify)

            domlc_d = sbs.build_lcgrid(self.subwta_arc, None)

            ron = Ron.getInstance(wd)
            if 'lt' in ron.mods:
                for k, sbs in domlc_d.items():
                    if sbs in ['131', '132']:
                        landuse.domlc_d[k] = '106'
                    elif sbs in ['133']:
                        landuse.domlc_d[k] = '105'

            else:
                landuse.domlc_d = domlc_d

            landuse.dump_and_unlock()
            landuse = landuse.getInstance(wd)
            landuse.build_managements()

        except Exception:
            self.unlock('-f')
            raise
        
    def modify_soils(self):
        wd = self.wd

        ron = Ron.getInstance(wd)
        if 'lt' in ron.mods:
            return

        soils_dir = self.soils_dir
        baer_soils_dir = self.baer_soils_dir
        
        soils_dict = {"130": "20-yr forest sandy loam.sol",
                      "131": "Low severity fire-sandy loam.sol",
                      "132": "Low severity fire-sandy loam.sol",
                      "133": "High severity fire-sandy loam.sol"}
        
        _soils = {}
        for k, fn in soils_dict.items():
            _soils[k] = SoilSummary(
                Mukey=k,
                FileName=fn,
                soils_dir=soils_dir,
                BuildDate="N/A",
                Description=fn[:-4]
            )
            
            shutil.copyfile(_join(baer_soils_dir, fn),
                            _join(soils_dir, fn))
        
        soils = Soils.getInstance(wd)
        soils.lock()

        # noinspection PyBroadExpection
        try:
            _domsoil_d = {}
            landuse = Landuse.getInstance(wd)
            domlc_d = landuse.domlc_d
            
            for topaz_id, mukey in soils.domsoil_d.items():
                dom = domlc_d[topaz_id]
                
                _domsoil_d[topaz_id] = dom
                    
            # need to recalculate the pct_coverages
            watershed = Watershed.getInstance(self.wd)
            for topaz_id, k in _domsoil_d.items():
                summary = watershed.sub_summary(str(topaz_id))
                if summary is not None:
                    _soils[k].area += summary["area"]

            for k in _soils:
                coverage = 100.0 * _soils[k].area / watershed.totalarea
                _soils[k].pct_coverage = coverage
                        
            soils.soils = _soils            
            soils.domsoil_d = _domsoil_d
            soils.dump_and_unlock()
            
        except Exception:
            soils.unlock('-f')
            raise
