import json
import string
from os.path import split as _split
from os.path import join as _join
from datetime import datetime
from glob import glob

from wepppy.all_your_base.geo import RasterDatasetInterpolator

from wepppy.wepp.soils import HorizonMixin
from wepppy.eu.soils.eusoilhydrogrids import SoilHydroGrids


_esdac_esdb_raster_dir = '/geodata/eu/ESDAC_ESDB_rasters/'
_esdac_derived_db_dir = '/geodata/eu/ESDAC_STU_EU_Layers/'


_texture_defaults = {'clay loam': {'dbthridbar': 1.4, 'ksat': 28.0, 'shcrit': 0.5,
                                   'field_cap': 0.001, 'wilt_pt': 0.001,
                                   'sand': 25.0, 'clay': 30.0, 'orgmat': 5.0, 'cec': 25.0, 'rfg': 15.0},
                     'silt loam': {'dbthridbar': 1.4, 'ksat': 28.0, 'shcrit': 1.5, 
                                   'field_cap': 0.001, 'wilt_pt': 0.001,
                                   'sand': 25.0, 'clay': 15.0, 'orgmat': 5.0, 'cec': 15.0, 'rfg': 15.0},
                     'loam':      {'dbthridbar': 1.4, 'ksat': 28.0, 'shcrit': 1.0, 
                                   'field_cap': 0.001, 'wilt_pt': 0.001,
                                   'sand': 45.0, 'clay': 20.0, 'orgmat': 5.0, 'cec': 20.0, 'rfg': 20.0},
                     'sand loam': {'dbthridbar': 1.4, 'ksat': 28.0, 'shcrit': 2.0, 
                                   'field_cap': 0.001, 'wilt_pt': 0.001,
                                   'sand': 65.0, 'clay': 10.0, 'orgmat': 5.0, 'cec': 15.0, 'rfg': 25.0},
                     None: None}


_tex_short_to_simple_texture = {
    '0': None,
    '9': None,
    '1': 'sand loam',
    '2': 'loam',
    '3': 'silt loam',
    '4': 'clay loam',
    '5': 'clay loam',
}


_il_short_to_depth_mm = {
    '0':   None,
    '1':   1500,
    '2':   1150,
    '3':   600,
    '4':   400
}


_cec_to_cmol_per_kg = {
    'H': 50.0, 
    'M': 27.5, 
    'L': 10
}

_texdepchg_short_to_depth_mm = {
    '0': None,
    '1': 300,
    '2': 500,
    '3': 700,
    '4': 1000,
    '5': 1200,
    '6': 400,
    '7': 900,
}

_octop_short_to_pct = {
    'H': 6.5,
    'M': 4.0,
    'L': 1.5,
    'V': 0.5,
    '': 5.0
}


_disclaimer = '''\
# THIS FILE AND THE CONTAINED DATA IS PROVIDED BY THE UNIVERSITY OF IDAHO 
# 'AS IS' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED 
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A 
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL UNIVERSITY OF IDAHO 
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHERE IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS FILE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
# '''


class Horizon(HorizonMixin):
    def __init__(self, clay: float=None, sand: float=None, silt: float=None, om: float=None,
                 bd: float=None, gravel: float=None, _cec: str=None, depth: float=None):

        self.clay = clay
        self.sand = sand
        self.silt = silt
        self.om = om
        self.bd = bd
        self.gravel = gravel
        self._cec = _cec
        self.depth = depth
       
        self._computeConductivity()
        self._computeErodibility()
        self._computeAnisotropy()
        self._rosettaPredict()

    @property
    def vfs(self):
        return self.silt

    @property
    def cec(self):
        return _cec_to_cmol_per_kg[self._cec]

    @property
    def smr(self):
        return self.gravel

    def as_dict(self):
        return dict(clay=self.clay, sand=self.sand, silt=self.silt, om=self.om,
                    bd=self.bd, gravel=self.gravel, cec=self.cec, 
                    conductivity=self.conductivity, anisotrophy=self.anisotropy,
                    interrill=self.interrill, rill=self.rill, shear=self.shear,
                    ks=self.ks, wilting_point=self.wilting_point, 
                    field_capacity=self.field_capacity)


def _attr_fmt(attr):
    _attr = ''.join(c for c in attr.lower() if
                   c in string.ascii_lowercase or c in string.digits)

    if 'lv' in _attr:
        _attr = _attr.replace('lv', 'lev')

    _replacements = {'txsrfdo': 'textsrfdom',
                     'txsrfse': 'textsrfsec',
                     'txsubdo': 'textsubdom',
                     'txsubse': 'textsubsec',
                     'txdepchg': 'textdepchg',
                     'usedo': 'usedom',
                     'erodi': 'erodibility'
                     }

    if _attr in _replacements:
        _attr = _replacements[_attr]

    return _attr


class ESDAC:
    def __init__(self):
        # { attr, raster_file_path}
        catalog = glob(_join(_esdac_esdb_raster_dir, '*.tif'))
        self.catalog = {_attr_fmt(_split(fn)[-1][:-4]): fn for fn in catalog}

        # { attr, raster_attribute table}
        rats = {}
        for fn in catalog:
            rats[_attr_fmt(_split(fn)[-1][:-4])] = self._rat_extract(fn[:-4] + '.json')
        self.rats = rats

        # { attr, raster_file_path}
        derived_db_catalog = glob(_join(_esdac_derived_db_dir, '*.tif'))
        self.derived_db_catalog = {_split(fn)[-1][:-4]: fn for fn in derived_db_catalog}


    @staticmethod
    def _rat_extract(fn):
        with open(fn.replace('.tif', '.json')) as fp:
            info = json.load(fp)

        rows = info['rat']['row']

        d = {}
        for r in rows:
            r = r['f']

            if len(r) == 3:
                d[str(r[0])] = str(r[2])
            elif len(r) == 2:
                d[str(r[0])] = str(r[0])
            else:
                raise Exception

        return d

    def query(self, lng, lat, attrs):
        from .legends import get_legend

        catalog = self.catalog
        rats = self.rats
        d = {}

        for attr in attrs:
            attr = _attr_fmt(attr)
            assert attr in catalog, attr
            rdi = RasterDatasetInterpolator(catalog[attr])
            x = rdi.get_location_info(lng, lat, method='near')
            px_val = str(int(x))
            short = rats[attr][px_val]
            legend = get_legend(attr)
            try:
                long = legend['table'][short]
            except KeyError:
                long = 'None'

            d[attr] = px_val, short, long

        return d

    def query_derived_db(self, lng, lat, attrs):

        catalog = self.derived_db_catalog
        d = {}

        for attr in attrs:
            assert attr in catalog, (attr, catalog, _esdac_derived_db_dir)
            rdi = RasterDatasetInterpolator(catalog[attr])
            x = rdi.get_location_info(lng, lat, method='near')

            d[attr] = x

        return d

    def build_wepp_soil(self, lng, lat, soils_dir, res_lyr_ksat_threshold=2.0, ksflag=0):
        """
        Build wepp soil from ESDAC data

        ksflag
           0 - do not use adjustments (conductivity will be held constant)
           1 - use internal adjustments
        """
        d_esdb = self.query(lng, lat, ('fao90lev1', 'usedom', 'textdepchg', 'il', 'cec_top', 'cec_sub', 'dgh', 'dimp', 'dr'))
        cec_top_class = d_esdb['cectop'][1]
        cec_sub_class = d_esdb['cecsub'][1]

        texdepchg_short = d_esdb['textdepchg'][1]
        solthk0 = _texdepchg_short_to_depth_mm[texdepchg_short]
        if solthk0 is None:
            solthk0 = 200

        il = d_esdb['il'][1]
        solthk1 = _il_short_to_depth_mm[il]
        if solthk1 is None:
            solthk1 = 400

        d_stu = self.query_derived_db(lng, lat, 
            ('STU_EU_T_CLAY',   'STU_EU_S_CLAY',
             'STU_EU_T_SAND',   'STU_EU_S_SAND',
             'STU_EU_T_SILT',   'STU_EU_S_SILT',
             'STU_EU_T_OC',     'STU_EU_S_OC',
             'STU_EU_T_BD',     'STU_EU_S_BD',
             'STU_EU_T_GRAVEL', 'STU_EU_S_GRAVEL'))

        h0 = Horizon(clay=d_stu['STU_EU_T_CLAY'], 
                     sand=d_stu['STU_EU_T_SAND'], 
                     silt=d_stu['STU_EU_T_SILT'], 
                     om=d_stu['STU_EU_T_OC'],
                     bd=d_stu['STU_EU_T_BD'], 
                     gravel=d_stu['STU_EU_T_GRAVEL'], 
                     _cec=cec_top_class, 
                     depth=solthk0)

        h1 = Horizon(clay=d_stu['STU_EU_S_CLAY'], 
                     sand=d_stu['STU_EU_S_SAND'], 
                     silt=d_stu['STU_EU_S_SILT'], 
                     om=d_stu['STU_EU_S_OC'],
                     bd=d_stu['STU_EU_S_BD'], 
                     gravel=d_stu['STU_EU_S_GRAVEL'], 
                     _cec=cec_sub_class, 
                     depth=solthk1)

        s = ['7778',
             '#',
             '#            WEPPcloud (c) University of Idaho',
             '#',
             '#  Build Date: ' + str(datetime.now()),
             '#  Source Data: ESDAC ESDB, EU Soil Hydro Grids v1.0',
             '#', '#']

        s.extend(_disclaimer.split('\n'))
        
        s.append('# ESDAC ESDB Soil Parameters')
        s.append('#')
        s.append('#  {:20}{:6}{:6}{}'.format('Attribute', 'PX', 'Abbr', 'Long Desc.'))
        s.append('#  ' + '-' * 120)

        for v in d_esdb:
            s.append('#  {:20}{:6}{:6}{}'.format(v, d_esdb[v][0], d_esdb[v][1], d_esdb[v][2]))

        s.append('#')

        usedom = d_esdb['usedom'][1]
        is_forest = usedom in ['5', '22']

        # set albedo to 0.15 unless landcover is Forest, then 0.5
        salb = (0.15, 0.06)[is_forest]

        # set initial saturation to 0.75 unless landcover is Forest, then 0.5
        ini_sat = (0.75, 0.5)[is_forest]


        s.append('# ESDAC STU Soil Parameters')
        s.append('#')
        s.append('#  {:10}{:>10}{:>10}'.format('Attribute', 'Top', 'Sub'))
        s.append('#  ' + '-' * 120)

        for v in ('CLAY', 'SAND', 'SILT', 'OC', 'BD', 'GRAVEL'):
            s.append('#  {:10}{:>10.1f}{:>10.1f}'.format(v, d_stu[f'STU_EU_T_{v}'], d_stu[f'STU_EU_S_{v}']))

        s.append('#')
        
        s.append('# Rosetta Soil Parameter Estimates Based on ESDAC')
        s.append('#')
        s.append('#  {:10}{:>10}{:>10}'.format('Attribute', 'Top', 'Sub'))
        s.append('#  ' + '-' * 120)
        
        for v in h0.rosetta_d:
            s.append('#  {:10}{:>10.1f}{:>10.1f}'.format(v, h0.rosetta_d[v], h1.rosetta_d[v]))
        s.append('#  + ks, wp, and fc used for WEPP soil parameters')

        s.append('#')
        s.append(('# Land IS NOT Forest', '# Land IS Forest')[is_forest])
        s.append(f'#    salb = {salb}')
        s.append(f'#    ini_sat = {ini_sat}')

        soil_hydro = SoilHydroGrids()
        ks = soil_hydro.query(lng, lat, 'KS')
        ksat_min = 1e38
        ksat_last = None 
        res_lyr_i = None
        res_lyr_ksat = None
        s.append('#')
        s.append('# EU Soil Hydro Grids')
        s.append('#')
        s.append('#  Code\tDepth\tksat')
        s.append('#  ' + '-' * 120)
        for i, (code, (_depth, _ks)) in enumerate(ks.items()):
            _ksat = _ks * 0.004166667
            s.append('#  {}  \t{}  \t{}'.format(code, _depth, _ksat))
            if _ksat < ksat_min:
                ksat_min = _ksat    

            if _ksat < res_lyr_ksat_threshold: 
                res_lyr_i = i
                res_lyr_ksat = ksat_min
    
            ksat_last = _ksat

        s.append('#')
        s.append(f'#  res_lyr_ksat_threshold = {res_lyr_ksat_threshold}')
        s.append(f'#  res_lyr_i = {res_lyr_i}')
        s.append(f'#  ksat_last = {ksat_last}')


        s.append('#')
        s.append('Any comments:')
        s.append(f'1 {ksflag}')

        description = d_esdb['fao90lev1'][2]
        num_layers = 2

        s.append(f"'{description}'\t\t'{h0.simple_texture}'\t"\
                 f"{num_layers}\t{salb:0.4f}\t"\
                 f"{ini_sat:0.4f}\t{h0.interrill:0.2f}\t{h0.rill:0.4f}\t"\
                 f"{h0.shear:0.4f}")

        s2 = f'{h0.depth:0.03f}\t{h0.bd:0.02f}\t{h0.ks:0.04f}\t'\
             f'{h0.anisotropy:0.01f}\t{h0.field_cap:0.04f}\t{h0.wilt_pt:0.04f}\t'\
             f'{h0.sand:0.2f}\t{h0.clay:0.2f}\t{h0.om:0.2f}\t'\
             f'{h0.cec:0.2f}\t{h0.smr:0.2f}'
                
        # make the layers easier to read by making cols fixed width
        # aligning to the right.
        s2 = '{0:>9}\t{1:>8}\t{2:>9}\t'\
             '{3:>5}\t{4:>9}\t{5:>9}\t'\
             '{6:>7}\t{7:>7}\t{8:>7}\t'\
             '{9:>7}\t{10:>7}'.format(*s2.split())
                 
        s.append('\t' + s2)

        s2 = f'{h1.depth:0.03f}\t{h1.bd:0.02f}\t{h1.ks:0.04f}\t'\
             f'{h1.anisotropy:0.01f}\t{h1.field_cap:0.04f}\t{h1.wilt_pt:0.04f}\t'\
             f'{h1.sand:0.2f}\t{h1.clay:0.2f}\t{h1.om:0.2f}\t'\
             f'{h1.cec:0.2f}\t{h1.smr:0.2f}'
                
        # make the layers easier to read by making cols fixed width
        # aligning to the right.
        s2 = '{0:>9}\t{1:>8}\t{2:>9}\t'\
             '{3:>5}\t{4:>9}\t{5:>9}\t'\
             '{6:>7}\t{7:>7}\t{8:>7}\t'\
             '{9:>7}\t{10:>7}'.format(*s2.split())
                 
        s.append('\t' + s2)


        if res_lyr_i is None:
            s.append('1 10000.0 %0.5f' % ksat_last)
        else:
            s.append('1 10000.0 %0.5f' % (res_lyr_ksat * 3.6))

        key = f"{d_esdb['fao90lev1'][1]}_{d_esdb['usedom'][1]}_{d_esdb['textdepchg'][1]}_{d_esdb['il'][1]}_{d_esdb['cectop'][1]}_{d_esdb['cecsub'][1]}_"\
              f"{d_esdb['dgh'][1]}_{d_esdb['dimp'][1]}_{d_esdb['dr'][1]}_{round(h0.clay)},{round(h0.vfs)},{round(h0.sand)},{round(h0.bd)}"
        fn = f"{key}.sol"

        with open(_join(soils_dir, fn), 'w') as fp:
            fp.write('\n'.join(s))

        desc = f"{d_esdb['fao90lev1'][2]} {d_esdb['usedom'][2]} {h0.simple_texture}"

        return key, h0, desc


if __name__ == "__main__":
    esd = ESDAC()
    esd.build_wepp_soil(-6.309, 43.140013)

