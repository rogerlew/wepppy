import shutil
from glob import glob
import os
from os.path import join as _join
from os.path import exists as _exists
from time import sleep
import jsonpickle
import multiprocessing
from subprocess import Popen, PIPE
from enum import IntEnum
from collections import namedtuple
from deprecated import deprecated

# wepppy
from wepppy.landcover import LandcoverMap

from wepppy.all_your_base import (
    isfloat,
    NCPU
)

from wepppy.wepp import Element
from wepppy.wepp.out import HillWat
from wepppy.climates.cligen import ClimateFile

# wepppy submodules
from wepppy.nodb.parameter_map import ParameterMap
from wepppy.nodb.mixins.log_mixin import LogMixin
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap
from wepppy.nodb.watershed import Watershed
from wepppy.nodb.climate import Climate
from wepppy.nodb.mods import Baer, Disturbed
from wepppy.nodb.wepp import Wepp
from wepppy.nodb.landuse import Landuse
from wepppy.nodb.ron import Ron
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

from wepppy.all_your_base.dateutils import YearlessDate


_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')

MULTIPROCESSING = True

from wepppy.nodb.mods.ash_transport.ash_multi_year_model import WHITE_ASH_BD, BLACK_ASH_BD

ContaminantConcentrations = namedtuple('ContaminantConcentrations',
                                       ['C', 'N', 'K',
                                        'PO4', 'Al', 'Si', 'Ca', 'Pb', 'Na', 'Mg', 'P',
                                        'Mn', 'Fe', 'Ni', 'Cu', 'Zn', 'As', 'Cd', 'Hg',
                                        'Cr', 'Co'])

def run_ash_model(kwds):
    """
    global function for running ash model to add with multiprocessing

    :param kwds: args package by Ash.run_model
    :return:
    """
    ash_type = kwds['ash_type']
    ini_ash_load = kwds['ini_ash_load']
    ash_bulkdensity = kwds['ash_bulkdensity']
    ash_model = kwds['ash_model']

    del kwds['ash_type']
    del kwds['ash_bulkdensity']
    del kwds['ash_model']

    logger = kwds['logger']
    prefix = kwds['prefix']

    del kwds['logger']
    out_fn = ash_model.run_model(**kwds)
    logger.log(f'  finished ash model for {prefix}\n')

    return out_fn


def reproject_map(wd, src, dst):

    if _exists(dst):
        os.remove(dst)

    map = Ron.getInstance(wd).map
    xmin, ymin, xmax, ymax = [str(v) for v in map.utm_extent]
    cellsize = str(map.cellsize)

    cmd = ['gdalwarp', '-t_srs',  'epsg:%s' % map.srid,
           '-tr', cellsize, cellsize,
           '-te', xmin, ymin, xmax, ymax,
           '-r', 'near', src, dst]

    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p.wait()

    assert _exists(dst), ' '.join(cmd)


class AshSpatialMode(IntEnum):
    Single = 1
    Gridded = 0


class AshNoDbLockedException(Exception):
    pass


class Ash(NoDbBase, LogMixin):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'Ash'

    def __init__(self, wd, cfg_fn):
        super(Ash, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            # config = self.config
            self.fire_date = YearlessDate(8, 4) 
            self.ini_black_ash_depth_mm = 5.0
            self.ini_white_ash_depth_mm = 5.0
            self.meta = None
            self.fire_years = None
            self._reservoir_capacity_m3 = 1000000
            self._reservoir_storage = 80
            self._ash_depth_mode = 1
            self._spatial_mode = AshSpatialMode.Single           

            self._ash_load_fn = self.config_get_path('ash', 'ash_load_fn')
            self._ash_bulk_density_fn = self.config_get_path('ash', 'ash_bulk_density_fn')
            self._ash_type_map_fn = self.config_get_path('ash', 'ash_type_map_fn')

            self._ash_load_d = None
            self._ash_type_d = None
            
            self._field_black_ash_bulkdensity = BLACK_ASH_BD
            self._field_white_ash_bulkdensity = WHITE_ASH_BD

            self._black_ash_bulkdensity = BLACK_ASH_BD
            self._white_ash_bulkdensity = WHITE_ASH_BD

            self._run_wind_transport = self.config_get_bool('ash', 'run_wind_transport')
            self._model = 'multi' #: self.config_get_str('ash', 'model')

            from .ash_multi_year_model import AshType, WhiteAshModel, BlackAshModel
            self._anu_white_ash_model_pars = WhiteAshModel()
            self._anu_black_ash_model_pars = BlackAshModel()
            
            self.dump_and_unlock()

            ash_dir = self.ash_dir
            if _exists(ash_dir):
                shutil.rmtree(ash_dir)
            os.mkdir(ash_dir)

        except Exception:
            self.unlock('-f')
            raise

        self._load_default_contaminants()

    @property
    def cc_high_default(self):
        return ContaminantConcentrations(
                C=248.4,
                N=5.4,
                K=1.5,
                PO4=3950,  # mg*Kg-1
                Al=7500,
                Si=880,
                Ca=20300,
                Pb=25.0,
                Na=553,
                Mg=980,
                P=1289,
                Mn=42.0,
                Fe=5600,
                Ni=13.0,
                Cu=11.0,
                Zn=35.0,
                As=2441,  # µg*Kg-1
                Cd=413,
                Hg=7.71,
                Cr=49.0,
                Co=7.2)

    @property
    def cc_moderate_default(self):
        return ContaminantConcentrations(
            C=273.5,
            N=5.42,
            K=1.1,
            PO4=9270,
            Al=1936,
            Si=2090,
            Ca=18100,
            Pb=70.0,
            Na=1213,
            Mg=4100,
            P=3025,
            Mn=910,
            Fe=2890,
            Ni=26.0,
            Cu=59.0,
            Zn=150,
            As=713,
            Cd=802,
            Hg=42.9,
            Cr=36.1,
            Co=5.0)

    @property
    def cc_moderate_default(self):
        return ContaminantConcentrations(
            C=273.5,
            N=5.42,
            K=1.1,
            PO4=9270,
            Al=1936,
            Si=2090,
            Ca=18100,
            Pb=70.0,
            Na=1213,
            Mg=4100,
            P=3025,
            Mn=910,
            Fe=2890,
            Ni=26.0,
            Cu=59.0,
            Zn=150,
            As=713,
            Cd=802,
            Hg=42.9,
            Cr=36.1,
            Co=5.0)

    @property
    def cc_low_default(self):
        return ContaminantConcentrations(
                C=273.5,
                N=5.42,
                K=1.1,
                PO4=9270,
                Al=1936,
                Si=2090,
                Ca=18100,
                Pb=70.0,
                Na=1213,
                Mg=4100,
                P=3025,
                Mn=910,
                Fe=2890,
                Ni=26.0,
                Cu=59.0,
                Zn=150,
                As=714,
                Cd=803,
                Hg=42.9,
                Cr=36.1,
                Co=5.0)

    def _load_default_contaminants(self):
        self.lock()

        # noinspection PyBroadException
        try:
            self.high_contaminant_concentrations = self.cc_high_default
            self.moderate_contaminant_concentrations = self.cc_moderate_default
            self.low_contaminant_concentrations = self.cc_low_default

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def parse_inputs(self, kwds):

        for k in kwds:
            try:
                kwds[k] = float(kwds[k])
            except ValueError:
                pass

        self.lock()

        # noinspection PyBroadException
        try:
            self._field_black_ash_bulkdensity = kwds.get('field_black_bulkdensity', self._field_black_ash_bulkdensity)
            self._field_white_ash_bulkdensity = kwds.get('field_white_bulkdensity', self._field_white_ash_bulkdensity)

            self._anu_white_ash_model_pars.ini_bulk_den = kwds.get('white_ini_bulk_den', self._anu_white_ash_model_pars.ini_bulk_den)
            self._anu_white_ash_model_pars.fin_bulk_den = kwds.get('white_fin_bulk_den', self._anu_white_ash_model_pars.fin_bulk_den)
            self._anu_white_ash_model_pars.bulk_den_fac = kwds.get('white_bulk_den_fac', self._anu_white_ash_model_pars.bulk_den_fac)
            self._anu_white_ash_model_pars.par_den = kwds.get('white_par_den', self._anu_white_ash_model_pars.par_den)
            self._anu_white_ash_model_pars.decomp_fac = kwds.get('white_decomp_fac', self._anu_white_ash_model_pars.decomp_fac)
            self._anu_white_ash_model_pars.ini_erod = kwds.get('white_ini_erod', self._anu_white_ash_model_pars.ini_erod)
            self._anu_white_ash_model_pars.fin_erod = kwds.get('white_fin_erod', self._anu_white_ash_model_pars.fin_erod)
            self._anu_white_ash_model_pars.roughness_limit = kwds.get('white_roughness_limit', self._anu_white_ash_model_pars.roughness_limit)
            self._anu_black_ash_model_pars.ini_bulk_den = kwds.get('black_ini_bulk_den', self._anu_black_ash_model_pars.ini_bulk_den)
            self._anu_black_ash_model_pars.fin_bulk_den = kwds.get('black_fin_bulk_den', self._anu_black_ash_model_pars.fin_bulk_den)
            self._anu_black_ash_model_pars.bulk_den_fac = kwds.get('black_bulk_den_fac', self._anu_black_ash_model_pars.bulk_den_fac)
            self._anu_black_ash_model_pars.par_den = kwds.get('black_par_den', self._anu_black_ash_model_pars.par_den)
            self._anu_black_ash_model_pars.decomp_fac = kwds.get('black_decomp_fac', self._anu_black_ash_model_pars.decomp_fac)
            self._anu_black_ash_model_pars.ini_erod = kwds.get('black_ini_erod', self._anu_black_ash_model_pars.ini_erod)
            self._anu_black_ash_model_pars.fin_erod = kwds.get('black_fin_erod', self._anu_black_ash_model_pars.fin_erod)
            self._anu_black_ash_model_pars.roughness_limit = kwds.get('black_roughness_limit', self._anu_black_ash_model_pars.roughness_limit )

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def parse_cc_inputs(self, kwds):

        for k in kwds:
            try:
                kwds[k] = float(kwds[k])
            except TypeError:
                try:
                    kwds[k] = float(kwds[k][0])
                except:
                    assert 0, (k, kwds[k])

        self.lock()

        cc_high_default = self.cc_high_default
        cc_moderate_default = self.cc_moderate_default
        cc_low_default = self.cc_low_default

        # noinspection PyBroadException
        try:

            self.high_contaminant_concentrations = ContaminantConcentrations(
                C=kwds.get('high_C', cc_high_default.C),
                N=kwds.get('high_N', cc_high_default.N),
                K=kwds.get('high_K', cc_high_default.K),
                PO4=kwds.get('high_PO4', cc_high_default.K),
                Al=kwds.get('high_Al', cc_high_default.Al),
                Si=kwds.get('high_Si', cc_high_default.Si),
                Ca=kwds.get('high_Ca', cc_high_default.Ca),
                Pb=kwds.get('high_Pb', cc_high_default.Pb),
                Na=kwds.get('high_Na', cc_high_default.Na),
                Mg=kwds.get('high_Mg', cc_high_default.Mg),
                P=kwds.get('high_P', cc_high_default.P),
                Mn=kwds.get('high_Mn', cc_high_default.Mn),
                Fe=kwds.get('high_Fe', cc_high_default.Fe),
                Ni=kwds.get('high_Ni', cc_high_default.Ni),
                Cu=kwds.get('high_Cu', cc_high_default.Cu),
                Zn=kwds.get('high_Zn', cc_high_default.Zn),
                As=kwds.get('high_As', cc_high_default.As),
                Cd=kwds.get('high_Cd', cc_high_default.Cd),
                Hg=kwds.get('high_Hg', cc_high_default.Hg),
                Cr=kwds.get('high_Cr', cc_high_default.Cr),
                Co=kwds.get('high_Co', cc_high_default.Co))

            self.moderate_contaminant_concentrations = ContaminantConcentrations(
                C=kwds.get('mod_C', cc_moderate_default.C),
                N=kwds.get('mod_N', cc_moderate_default.N),
                K=kwds.get('mod_K', cc_moderate_default.K),
                PO4=kwds.get('mod_PO4', cc_moderate_default.K),
                Al=kwds.get('mod_Al', cc_moderate_default.Al),
                Si=kwds.get('mod_Si', cc_moderate_default.Si),
                Ca=kwds.get('mod_Ca', cc_moderate_default.Ca),
                Pb=kwds.get('mod_Pb', cc_moderate_default.Pb),
                Na=kwds.get('mod_Na', cc_moderate_default.Na),
                Mg=kwds.get('mod_Mg', cc_moderate_default.Mg),
                P=kwds.get('mod_P', cc_moderate_default.P),
                Mn=kwds.get('mod_Mn', cc_moderate_default.Mn),
                Fe=kwds.get('mod_Fe', cc_moderate_default.Fe),
                Ni=kwds.get('mod_Ni', cc_moderate_default.Ni),
                Cu=kwds.get('mod_Cu', cc_moderate_default.Cu),
                Zn=kwds.get('mod_Zn', cc_moderate_default.Zn),
                As=kwds.get('mod_As', cc_moderate_default.As),
                Cd=kwds.get('mod_Cd', cc_moderate_default.Cd),
                Hg=kwds.get('mod_Hg', cc_moderate_default.Hg),
                Cr=kwds.get('mod_Cr', cc_moderate_default.Cr),
                Co=kwds.get('mod_Co', cc_moderate_default.Co))
            
            self.low_contaminant_concentrations = ContaminantConcentrations(
                C=kwds.get('low_C', cc_low_default.C),
                N=kwds.get('low_N', cc_low_default.N),
                K=kwds.get('low_K', cc_low_default.K),
                PO4=kwds.get('low_PO4', cc_low_default.K),
                Al=kwds.get('low_Al', cc_low_default.Al),
                Si=kwds.get('low_Si', cc_low_default.Si),
                Ca=kwds.get('low_Ca', cc_low_default.Ca),
                Pb=kwds.get('low_Pb', cc_low_default.Pb),
                Na=kwds.get('low_Na', cc_low_default.Na),
                Mg=kwds.get('low_Mg', cc_low_default.Mg),
                P=kwds.get('low_P', cc_low_default.P),
                Mn=kwds.get('low_Mn', cc_low_default.Mn),
                Fe=kwds.get('low_Fe', cc_low_default.Fe),
                Ni=kwds.get('low_Ni', cc_low_default.Ni),
                Cu=kwds.get('low_Cu', cc_low_default.Cu),
                Zn=kwds.get('low_Zn', cc_low_default.Zn),
                As=kwds.get('low_As', cc_low_default.As),
                Cd=kwds.get('low_Cd', cc_low_default.Cd),
                Hg=kwds.get('low_Hg', cc_low_default.Hg),
                Cr=kwds.get('low_Cr', cc_low_default.Cr),
                Co=kwds.get('low_Co', cc_low_default.Co))

            self._reservoir_capacity_m3 = kwds.get('reservoir_capacity')
            self._reservoir_storage = kwds.get('reservoir_storage')

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd='.', allow_nonexistent=False, ignore_lock=False):
        with open(_join(wd, 'ash.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Ash), db

        if _exists(_join(wd, 'READONLY')):
            db.wd = os.path.abspath(wd)
            return db

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            if not db.islocked():
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

        return db

    @staticmethod
    def getInstanceFromRunID(runid, allow_nonexistent=False, ignore_lock=False):
        from wepppy.weppcloud.utils.helpers import get_wd
        return Ash.getInstance(
            get_wd(runid), allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock)

    @property
    def _nodb(self):
        return _join(self.wd, 'ash.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'ash.nodb.lock')

    @property
    def status_log(self):
        return os.path.abspath(_join(self.ash_dir, 'status.log'))

    @property
    def has_ash_results(self):
        return _exists(self.status_log) and len(glob(_join(self.ash_dir, 'post', '*.pkl'))) > 0

    @property
    def anu_white_ash_model_pars(self):
        pars = getattr(self, '_anu_white_ash_model_pars', None)
        if pars is None:
            try:
                from .ash_multi_year_model import AshType, WhiteAshModel, BlackAshModel
                self.lock()
                pars = self._anu_white_ash_model_pars = WhiteAshModel()
                
                self.dump_and_unlock()
    
            except Exception:
                self.unlock('-f')
                raise
        return pars

    @property
    def anu_black_ash_model_pars(self):
        pars = getattr(self, '_anu_black_ash_model_pars', None)
        if pars is None:
            try:
                from .ash_multi_year_model import AshType, WhiteAshModel, BlackAshModel
                 
                self.lock()
                pars = self._anu_black_ash_model_pars = BlackAshModel()
                
                self.dump_and_unlock()
    
            except Exception:
                self.unlock('-f')
                raise
        return pars

    @property
    def model(self):
        return 'multi'

    @model.setter
    def model(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._model = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            
    @property
    def reservoir_storage(self):
        if not getattr(self, '_reservoir_storage'):
            self.reservoir_storage = 1000000

        return self._reservoir_storage

    @reservoir_storage.setter
    def reservoir_storage(self, value):
        assert isfloat(value), value

        self.lock()

        # noinspection PyBroadException
        try:
            self._reservoir_storage = float(value)
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def run_wind_transport(self):
        return getattr(self, '_run_wind_transport', False)

    @run_wind_transport.setter
    def run_wind_transport(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._run_wind_transport = bool(value)
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def ash_load_d(self):
        return getattr(self, '_ash_load_d', None)

    @property
    def ash_bulk_density_d(self):
        return getattr(self, '_ash_bulk_density_d', None)

    @property
    def ash_load_fn(self):
        fn = getattr(self, '_ash_load_fn', None) 

        if fn is None:
            return None

        return _join(self.ash_dir, fn)
        
    @ash_load_fn.setter
    def ash_load_fn(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._ash_load_fn = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def ash_type_map_fn(self):
        fn = getattr(self, '_ash_type_map_fn', None) 
        if fn is None:
            return None

        return _join(self.ash_dir, fn)

    @ash_type_map_fn.setter
    def ash_type_map_fn(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._ash_type_map_fn = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    @deprecated
    def ash_bulk_density_fn(self):
        fn = getattr(self, '_ash_bulk_density_fn', None) 
        if fn is None:
            return None

        return _join(self.ash_dir, fn)

    @ash_bulk_density_fn.setter
    @deprecated
    def ash_bulk_density_fn(self, value):
        self.lock()

        # noinspection PyBroadException
        try:
            self._ash_bulk_density_fn = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def ash_spatial_mode(self):
        if not getattr(self, '_ash_spatial_mode'):
            self.ash_spatial_mode = AshSpatialMode.Single

        return self._ash_spatial_mode

    @ash_spatial_mode.setter
    def ash_spatial_mode(self, value):
        assert isinstance(self, AshSpatialMode), value

        self.lock()

        # noinspection PyBroadException
        try:
            self._ash_spatial_mode = value
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def ash_depth_mode(self):
        if not getattr(self, '_ash_depth_mode'):
            self.ash_depth_mode = 1

        return self._ash_depth_mode

    @ash_depth_mode.setter
    def ash_depth_mode(self, value):
        assert isfloat(value), value

        self.lock()

        # noinspection PyBroadException
        try:
            self._ash_depth_mode = int(value)
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def reservoir_capacity_m3(self):
        if not getattr(self, '_reservoir_capacity_m3'):
            self.reservoir_capacity_m3 = 1000000

        return self._reservoir_capacity_m3

    @property
    def reservoir_capacity_ft3(self):
        return self.reservoir_capacity_m3 * 35.3147

    @reservoir_capacity_m3.setter
    def reservoir_capacity_m3(self, value):
        assert isfloat(value), value

        self.lock()

        # noinspection PyBroadException
        try:
            self._reservoir_capacity_m3 = float(value)
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    @deprecated
    def ash_bulk_density_cropped_fn(self):
        return _join(self.ash_dir, 'ash_bulk_density_cropped.tif')

    @property
    def ash_load_cropped_fn(self):
        return _join(self.ash_dir, 'ash_load_cropped.tif')

    @property
    def ash_type_map_cropped_fn(self):
        return _join(self.ash_dir, 'ash_type_map_cropped.tif')

    def run_ash(self, fire_date='8/4', ini_white_ash_depth_mm=3.0, ini_black_ash_depth_mm=5.0):
        run_wind_transport=self.run_wind_transport

        self.clean_log()

        self.lock()

        # noinspection PyBroadException
        try:
            self.log(f"Ash::run_ash(fire_date='{fire_date}', ini_white_ash_depth_mm={ini_white_ash_depth_mm}, ini_black_ash_depth_mm={ini_black_ash_depth_mm}\n")
            self.fire_date = fire_date = YearlessDate.from_string(fire_date)
            self.ini_white_ash_depth_mm = ini_white_ash_depth_mm
            self.ini_black_ash_depth_mm = ini_black_ash_depth_mm

            assert ini_white_ash_depth_mm > 0.0, ini_white_ash_depth_mm
            assert ini_black_ash_depth_mm > 0.0, ini_black_ash_depth_mm

            wd = self.wd
            ash_dir = self.ash_dir
            model = self.model

            if 'multi' in model:
                from .ash_multi_year_model import AshType, WhiteAshModel, BlackAshModel
            else:
                raise NotImplementedError

            if _exists(ash_dir):

                for fn in glob(_join(ash_dir, '*.parquet')):
                    self.log(f"  Removing {fn}\n")
                    os.remove(fn)

                for fn in glob(_join(ash_dir, '*.png')):
                    self.log(f"  Removing {fn}\n")
                    os.remove(fn)

                for fn in glob(_join(ash_dir, 'post', '*.pkl')):
                    self.log(f"  Removing {fn}\n")
                    os.remove(fn)

            if not _exists(ash_dir):
                os.makedirs(ash_dir)

            watershed = Watershed.getInstance(wd)
            climate = Climate.getInstance(wd)
            wepp = Wepp.getInstance(wd)
            landuse = Landuse.getInstance(wd)

            cli_path = climate.cli_path
            cli_df = ClimateFile(cli_path).as_dataframe(calc_peak_intensities=False)

            if self.ash_load_fn is not None:
                self.log(f"  Reading ash load map {self.ash_load_fn}\n")
                reproject_map(wd, self.ash_load_fn, self.ash_load_cropped_fn)
                load_map = ParameterMap(self.ash_load_cropped_fn)
                load_d = load_map.build_ave_grid(watershed.subwta)
            else:
                self.log(f"  No ash load map found\n")
                load_d = None

            if self.ash_type_map_fn is not None:
                self.log(f"  Reading ash type map {self.ash_type_map_fn}\n")
                reproject_map(wd, self.ash_type_map_fn, self.ash_type_map_cropped_fn)
                bd_map = ParameterMap(self.ash_type_map_cropped_fn)
                ash_type_d = bd_map.build_ave_grid(watershed.subwta)
            else:
                self.log(f"  No ash type map found\n")
                ash_type_d = None

            translator = watershed.translator_factory()

            self.log_done()

            self.log('  Running Hillslopes\n')
            meta = {}
            args = []
            for topaz_id in watershed._subs_summary:
                self.log(f'    Running Hillslope {topaz_id}\n')

                meta[topaz_id] = {}
                wepp_id = translator.wepp(top=topaz_id)
                area_ha = watershed.hillslope_area(topaz_id) / 10000

                burn_class = landuse.identify_burn_class(topaz_id)
                burn_class = ['Unburned', 'Low', 'Moderate', 'High'].index(burn_class)
                if burn_class == 255:
                    burn_class = 0

                self.log(f'      burn_class: {burn_class}\n')

                if ash_type_d is None:
                    self.log('      ash_type_d is None. Assigning ash type from burn_class\n')
                    ash_type = (None, AshType.BLACK, AshType.BLACK, AshType.WHITE)[burn_class]
                else:
                    self.log(f'      ash_type_d: {ash_type_d[topaz_id]}\n')
                    ash_type = (None, AshType.BLACK, AshType.WHITE)[int(ash_type_d[topaz_id])]

                self.log(f'      ash_type: {ash_type}\n')


                meta[topaz_id]['ash_type'] = ash_type
                meta[topaz_id]['burn_class'] = burn_class
                meta[topaz_id]['area_ha'] = area_ha

                if ash_type is None:
                    continue

                if load_d is not None:
                    if load_d[topaz_id] <= 0.0:
                        continue

                element_fn = _join(wepp.output_dir,
                                   'H{wepp_id}.element.dat'.format(wepp_id=wepp_id))
                element = Element(element_fn)

                hill_wat_fn = _join(wepp.output_dir,
                                   'H{wepp_id}.wat.dat'.format(wepp_id=wepp_id))
                hill_wat = HillWat(hill_wat_fn)

                field_white_ash_bulkdensity = self.field_white_ash_bulkdensity
                field_black_ash_bulkdensity = self.field_black_ash_bulkdensity

                assert field_white_ash_bulkdensity > 0.0, field_white_ash_bulkdensity
                assert field_black_ash_bulkdensity > 0.0, field_black_ash_bulkdensity

                if load_d is None:
                    self.log('      load_d is None. Using initial ash depth\n')
                    white_ash_depth = ini_white_ash_depth_mm
                    black_ash_depth = ini_black_ash_depth_mm
                    
                    white_ash_load = ini_white_ash_depth_mm * field_white_ash_bulkdensity * 10
                    black_ash_load = ini_black_ash_depth_mm * field_black_ash_bulkdensity * 10

                else:
                    self.log(f'      load_d: {load_d[topaz_id]} tonne/ha\n')
                    _load_kg_m2 = load_d[topaz_id] * 0.1

                    white_ash_depth = _load_kg_m2 / field_white_ash_bulkdensity
                    black_ash_depth = _load_kg_m2 / field_black_ash_bulkdensity

                    self.log('      setting ash depth based on load_d and field bulk densities\n')
                    self.log(f'        white_ash_depth: {white_ash_depth}\n')
                    self.log(f'        black_ash_depth: {black_ash_depth}\n')

                    white_ash_load = black_ash_load = load_d[topaz_id]

                if ash_type == AshType.WHITE:
                    ini_ash_depth = white_ash_depth
                    field_ash_bulkdensity = field_white_ash_bulkdensity
                    ini_ash_load = white_ash_load
                    ash_bulkdensity = self.white_ash_bulkdensity
                else:
                    ini_ash_depth = black_ash_depth
                    field_ash_bulkdensity = field_black_ash_bulkdensity
                    ini_ash_load = black_ash_load
                    ash_bulkdensity = self.black_ash_bulkdensity

                assert ini_ash_load > 0.0, (ini_ash_load, ini_white_ash_depth_mm, ini_black_ash_depth_mm, field_white_ash_bulkdensity, field_black_ash_bulkdensity)

                if ash_type == AshType.BLACK:
                    ash_model = self.anu_black_ash_model_pars  # BlackAshModel instance with properties set by parse_inputs
                else:
                    ash_model = self.anu_white_ash_model_pars  # WhiteAshModel instance with properties set by parse_inputs

                meta[topaz_id]['ini_ash_depth'] = ini_ash_depth
                meta[topaz_id]['field_ash_bulkdensity'] = field_ash_bulkdensity
                meta[topaz_id]['ini_ash_load'] = ini_ash_load
                meta[topaz_id]['ash_bulkdensity'] = ash_bulkdensity

                self.log(f'      ash parameters\n')
                self.log(f'        ini_ash_depth: {ini_ash_depth}\n')
                self.log(f'        field_ash_bulkdensity: {field_ash_bulkdensity}\n')
                self.log(f'        ini_ash_load: {ini_ash_load}\n')
                self.log(f'        ash_bulkdensity: {ash_bulkdensity}\n')

                kwds = dict(ash_type=ash_type,
                            ini_ash_load=ini_ash_load,
                            ash_bulkdensity=ash_bulkdensity,
                            fire_date=fire_date,
                            element_d=element.d,
                            cli_df=cli_df,
                            hill_wat=hill_wat,
                            out_dir=ash_dir,
                            prefix='H{wepp_id}'.format(wepp_id=wepp_id),
                            area_ha=area_ha,
                            run_wind_transport=run_wind_transport,
                            ash_model=ash_model,
                            logger=self)

                args.append(kwds)

            if MULTIPROCESSING:
                # Use a 'with' statement to create the pool and automatically close and join it
                with multiprocessing.Pool(NCPU) as pool:
                    # Use 'pool.map()' to apply the function to the arguments and wait for all the jobs to finish
                    pool.map(run_ash_model, args)


            else:
                for kwds in args:
                    self.log(f"  running {kwds['prefix']}\n")
                    run_ash_model(kwds)
                    self.log_done()

            self._ash_load_d = load_d
            self._ash_type_d = ash_type_d

            self.meta = meta
            try:
                self.fire_years = climate.input_years - 1
            except:
                pass

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

        from wepppy.nodb import AshPost

        if not _exists(_join(wd, 'ashpost.nodb')):
            ashpost = AshPost(wd, '{}.cfg'.format(self.config_stem))
        else:
            ashpost = AshPost.getInstance(wd)

        ashpost.run_post()

        try:
            prep = RedisPrep.getInstance(wd)
            prep.timestamp(TaskEnum.run_watar)
        except FileNotFoundError:
            pass

    @property
    def _status_channel(self):
        return f'{self.runid}:ash'

    def get_ash_type(self, topaz_id):
        if 'multi' not in self.model:
            raise DeprecationWarning
        else:
            from wepppy.nodb.mods.ash_transport.ash_multi_year_model import AshType

        ash_type = self.meta[str(topaz_id)].get('ash_type', None)
        if ash_type == AshType.BLACK:
            return 'black'
        elif ash_type == AshType.WHITE:
            return 'white'

    def get_ini_ash_depth(self, topaz_id):
        if 'multi' not in self.model:
            raise DeprecationWarning
        else:
            from wepppy.nodb.mods.ash_transport.ash_multi_year_model import AshType

        _meta = self.meta[str(topaz_id)]

        if 'ini_ash_depth' in _meta:
            return _meta['ini_ash_depth']

        load_d = self.ash_load_d
        black_bd = self.field_black_ash_bulkdensity
        white_bd = self.field_white_ash_bulkdensity

        ash_type = _meta.get('ash_type', None)

        if ash_type is None:
            return None

        if ash_type == AshType.BLACK:
            if load_d is None:
                return self.ini_black_ash_depth_mm
            else:
                return load_d[str(topaz_id)] * 0.1 / black_bd
        elif ash_type == AshType.WHITE:
            if load_d is None:
                return self.ini_white_ash_depth_mm
            else:
                return load_d[str(topaz_id)] * 0.1 / white_bd

    @property
    def black_ash_bulkdensity(self):
        return getattr(self, '_black_ash_bulkdensity', 
                       self.config_get_float('ash', 'black_ash_bulkdensity'))

    @property
    def white_ash_bulkdensity(self):
        return getattr(self, '_white_ash_bulkdensity', 
                       self.config_get_float('ash', 'white_ash_bulkdensity'))

    @property
    def field_black_ash_bulkdensity(self):
        return getattr(self, '_field_black_ash_bulkdensity', BLACK_ASH_BD)

    @property
    def field_white_ash_bulkdensity(self):
        return getattr(self, '_field_white_ash_bulkdensity', WHITE_ASH_BD)

    @property
    def ini_black_ash_load(self):
        return self.ini_black_ash_depth_mm * self.field_black_ash_bulkdensity

    @property
    def ini_white_ash_load(self):
        return self.ini_white_ash_depth_mm * self.field_white_ash_bulkdensity

    @property
    def has_watershed_summaries(self):
        return len(glob(_join(self.ash_dir, 'post/watershed_annuals.pkl'))) > 0

    def hillslope_is_burned(self, topaz_id):
        watershed = Watershed.getInstance(self.wd)
        burn_class = self.meta[str(topaz_id)]['burn_class']
        return burn_class in [2, 3, 4]

    def contaminants_iter(self):
        high_contaminant_concentrations = self.high_contaminant_concentrations
        moderate_contaminant_concentrations = self.moderate_contaminant_concentrations
        low_contaminant_concentrations = self.low_contaminant_concentrations

        for contaminant in high_contaminant_concentrations._fields:
            high = getattr(high_contaminant_concentrations, contaminant)
            mod = getattr(moderate_contaminant_concentrations, contaminant)
            low = getattr(low_contaminant_concentrations, contaminant)

            if contaminant in ['C', 'N', 'K']:
                units = 'g/kg'
            elif contaminant in ['As', 'Cd', 'Hg']:
                units = 'μg/kg'
            else:
                units = 'mg/kg'

            yield contaminant, high, mod, low, units

    def burn_class_summary(self):
        assert self.meta is not None

        burn_class_sum = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}

        for topaz_id, d in self.meta.items():
            burn_class = d['burn_class']
            if burn_class in (0, 255):
                burn_class = 1
            assert burn_class in burn_class_sum, burn_class
            burn_class_sum[burn_class] += d['area_ha']

        return {k: burn_class_sum[k] for k in sorted(burn_class_sum)}
