import shutil
from glob import glob

from os.path import join as _join
from os.path import exists as _exists

# non-standard
import jsonpickle
import multiprocessing

from collections import namedtuple

# wepppy
from wepppy.landcover import LandcoverMap

from wepppy.all_your_base import (
    isfloat,
    NCPU
)

from wepppy.wepp import Element
from wepppy.climates.cligen import ClimateFile

# wepppy submodules
from wepppy.nodb.mixins.log_mixin import LogMixin
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap
from wepppy.nodb.watershed import Watershed
from wepppy.nodb.climate import Climate
from wepppy.nodb.mods import Baer
from wepppy.nodb.wepp import Wepp

from .ash_model import *

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


ContaminantConcentrations = namedtuple('ContaminantConcentrations',
                                       ['PO4', 'Al', 'Si', 'Ca', 'Pb', 'Na', 'Mg', 'P',
                                        'Mn', 'Fe', 'Ni', 'Cu', 'Zn', 'As', 'Cd', 'Hg'])


def run_ash_model(kwds):
    """
    global function for running ash model to add with multiprocessing

    :param kwds: args package by Ash.run_model
    :return:
    """
    ash_type = kwds['ash_type']

    if ash_type == AshType.BLACK:
        ini_ash_depth = kwds['ini_black_ash_depth_mm']
        ash_model = WhiteAshModel(ini_ash_depth)
    else:
        ini_ash_depth = kwds['ini_white_ash_depth_mm']
        ash_model = BlackAshModel(ini_ash_depth)

    del kwds['ash_type']
    del kwds['ini_black_ash_depth_mm']
    del kwds['ini_white_ash_depth_mm']
    out_fn, return_periods, annuals = \
        ash_model.run_model(**kwds)

    return out_fn


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
            self.fire_date = None
            self.ini_black_ash_depth_mm = 5
            self.ini_white_ash_depth_mm = 5
            self.meta = None
            self.fire_years = None
            self._reservoir_capacity_m3 = 1000000
            self._reservoir_storage = 0.8
            self._ash_depth_mode = 1

            self.high_contaminant_concentrations = ContaminantConcentrations(
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
                Hg=7.71)

            self.moderate_contaminant_concentrations = ContaminantConcentrations(
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
                Hg=42.9)

            self.low_contaminant_concentrations = ContaminantConcentrations(
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
                Hg=42.9)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def parse_inputs(self, kwds):

        for k in kwds:
            try:
                kwds[k] = float(kwds[k])
            except TypeError:
                try:
                    kwds[k] = float(kwds[k][0])
                except:
                    assert 0, (k, kwds[k])

        self.lock()

        # noinspection PyBroadException
        try:
            self.high_contaminant_concentrations = ContaminantConcentrations(
                PO4=kwds.get('high_PO4'),
                Al=kwds.get('high_Al'),
                Si=kwds.get('high_Si'),
                Ca=kwds.get('high_Ca'),
                Pb=kwds.get('high_Pb'),
                Na=kwds.get('high_Na'),
                Mg=kwds.get('high_Mg'),
                P=kwds.get('high_P'),
                Mn=kwds.get('high_Mn'),
                Fe=kwds.get('high_Fe'),
                Ni=kwds.get('high_Ni'),
                Cu=kwds.get('high_Cu'),
                Zn=kwds.get('high_Zn'),
                As=kwds.get('high_As'),
                Cd=kwds.get('high_Cd'),
                Hg=kwds.get('high_Hg'))

            self.moderate_contaminant_concentrations = ContaminantConcentrations(
                PO4=kwds.get('mod_PO4'),
                Al=kwds.get('mod_Al'),
                Si=kwds.get('mod_Si'),
                Ca=kwds.get('mod_Ca'),
                Pb=kwds.get('mod_Pb'),
                Na=kwds.get('mod_Na'),
                Mg=kwds.get('mod_Mg'),
                P=kwds.get('mod_P'),
                Mn=kwds.get('mod_Mn'),
                Fe=kwds.get('mod_Fe'),
                Ni=kwds.get('mod_Ni'),
                Cu=kwds.get('mod_Cu'),
                Zn=kwds.get('mod_Zn'),
                As=kwds.get('mod_As'),
                Cd=kwds.get('mod_Cd'),
                Hg=kwds.get('mod_Hg'))
            
            self.low_contaminant_concentrations = ContaminantConcentrations(
                PO4=kwds.get('low_PO4'),
                Al=kwds.get('low_Al'),
                Si=kwds.get('low_Si'),
                Ca=kwds.get('low_Ca'),
                Pb=kwds.get('low_Pb'),
                Na=kwds.get('low_Na'),
                Mg=kwds.get('low_Mg'),
                P=kwds.get('low_P'),
                Mn=kwds.get('low_Mn'),
                Fe=kwds.get('low_Fe'),
                Ni=kwds.get('low_Ni'),
                Cu=kwds.get('low_Cu'),
                Zn=kwds.get('low_Zn'),
                As=kwds.get('low_As'),
                Cd=kwds.get('low_Cd'),
                Hg=kwds.get('low_Hg'))

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
    def getInstance(wd):
        with open(_join(wd, 'ash.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Ash), db

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

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
        return _exists(self.status_log) and len(glob(_join(self.ash_dir, '*.csv'))) > 0

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

    def run_ash(self, fire_date='8/4', ini_white_ash_depth_mm=3.0, ini_black_ash_depth_mm=5.0):

        self.lock()

        # noinspection PyBroadException
        try:
            self.log('Prepping ash run...')
            self.fire_date = fire_date = YearlessDate.from_string(fire_date)
            self.ini_white_ash_depth_mm = ini_white_ash_depth_mm
            self.ini_black_ash_depth_mm = ini_black_ash_depth_mm

            wd = self.wd
            ash_dir = self.ash_dir

            if _exists(ash_dir):
                shutil.rmtree(ash_dir)
            os.mkdir(ash_dir)

            baer = Baer.getInstance(wd)
            watershed = Watershed.getInstance(wd)
            climate = Climate.getInstance(wd)
            wepp = Wepp.getInstance(wd)

            cli_path = climate.cli_path
            cli_df = ClimateFile(cli_path).as_dataframe(calc_peak_intensities=True)

            # create LandcoverMap instance
            sbs = SoilBurnSeverityMap(baer.baer_cropped, baer.breaks, baer._nodata_vals)

            baer_4class = baer.baer_cropped.replace('.tif', '.4class.tif')
            sbs.export_4class_map(baer_4class)

            lc = LandcoverMap(baer_4class)
            sbs_d = lc.build_lcgrid(self.subwta_arc)

            translator = watershed.translator_factory()

            self.log_done()

            self.log('Running Hillslopes\n')
            meta = {}
            args = []
            for topaz_id, sub in watershed.sub_iter():
                area_ha = sub.area / 10000

                meta[topaz_id] = {}

                wepp_id = translator.wepp(top=topaz_id)

                burn_class = int(sbs_d[topaz_id])
                meta[topaz_id]['burn_class'] = burn_class
                meta[topaz_id]['area_ha'] = area_ha

                if burn_class in [2, 3]:
                    ash_type = AshType.BLACK

                elif burn_class in [4]:
                    ash_type = AshType.WHITE
                else:
                    continue

                meta[topaz_id]['ash_type'] = ash_type

                element_fn = _join(wepp.output_dir,
                                   'H{wepp_id}.element.dat'.format(wepp_id=wepp_id))
                element = Element(element_fn)

                hill_wat_fn = _join(wepp.output_dir,
                                   'H{wepp_id}.wat.dat'.format(wepp_id=wepp_id))
                hill_wat = HillWat(hill_wat_fn)

                kwds = dict(ash_type=ash_type,
                            ini_white_ash_depth_mm=ini_white_ash_depth_mm,
                            ini_black_ash_depth_mm=ini_black_ash_depth_mm,
                            fire_date=fire_date,
                            element_d=element.d,
                            cli_df=cli_df,
                            hill_wat=hill_wat,
                            out_dir=ash_dir,
                            prefix='H{wepp_id}'.format(wepp_id=wepp_id),
                            area_ha=area_ha)
                args.append(kwds)

            pool = multiprocessing.Pool(NCPU)
            for out_fn in pool.imap_unordered(run_ash_model, args):
                self.log('  completed running {}\n'.format(out_fn))
                self.log_done()

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

    def get_ash_type(self, topaz_id):
        ash_type = self.meta[str(topaz_id)]['ash_type']
        if ash_type == AshType.BLACK:
            return 'black'
        elif ash_type == AshType.WHITE:
            return 'white'

    def get_ini_ash_depth(self, topaz_id):
        ash_type = self.meta[str(topaz_id)]['ash_type']
        if ash_type == AshType.BLACK:
            return self.ini_black_ash_depth_mm
        elif ash_type == AshType.WHITE:
            return self.ini_white_ash_depth_mm

    @property
    def ini_black_ash_bulkdensity(self):
        return BlackAshModel(self.ini_black_ash_depth_mm).bulk_density

    @property
    def ini_white_ash_bulkdensity(self):
        return WhiteAshModel(self.ini_white_ash_depth_mm).bulk_density

    @property
    def ini_black_ash_load(self):
        return BlackAshModel(self.ini_black_ash_depth_mm).ini_material_available_tonneperha * 0.1  # to kg/m^2

    @property
    def ini_white_ash_load(self):
        return WhiteAshModel(self.ini_white_ash_depth_mm).ini_material_available_tonneperha * 0.1  # to kg/m^2

    @property
    def has_watershed_summaries(self):
        return len(glob(_join(self.ash_dir, 'pw0_burn_class=*,ash_stats_per_year_cum_ash_delivery_by_water.csv'))) > 0

    def hillslope_is_burned(self, topaz_id):
        watershed = Watershed.getInstance(self.wd)
        burnclass = self.meta[str(topaz_id)]['burn_class']
        return burnclass in [2, 3, 4]

    def contaminants_iter(self):
        high_contaminant_concentrations = self.high_contaminant_concentrations
        moderate_contaminant_concentrations = self.moderate_contaminant_concentrations
        low_contaminant_concentrations = self.low_contaminant_concentrations

        for contaminant in high_contaminant_concentrations._fields:
            high = getattr(high_contaminant_concentrations, contaminant)
            mod = getattr(moderate_contaminant_concentrations, contaminant)
            low = getattr(low_contaminant_concentrations, contaminant)

            if contaminant in ['As', 'Cd', 'Hg']:
                units = 'μg/kg'
            else:
                units = 'mg/kg'

            yield contaminant, high, mod, low, units

    def burnclass_summary(self):
        assert self.meta is not None

        burnclass_sum = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}

        for topaz_id, d in self.meta.items():
            burnclass = d['burn_class']
            if burnclass == 255:
                burnclass = 1
            assert burnclass in burnclass_sum, burnclass
            burnclass_sum[burnclass] += d['area_ha']

        return {k: burnclass_sum[k] for k in sorted(burnclass_sum)}
