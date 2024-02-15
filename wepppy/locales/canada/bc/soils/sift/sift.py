import os
from os.path import join as _join
from os.path import split as _split
import math

from subprocess import Popen, PIPE, STDOUT
from datetime import datetime

from wepppy.wepp.soils import HorizonMixin
from wepppy.all_your_base import isfloat
from wepppy.all_your_base.geo import GeoTransformer
import json

_datadir = '/geodata/ca/env.gov.bc.ca/BC_Soil_Map.gdb/'

_proj4 = '+proj=aea +datum=NAD83 +ellps=GRS80 +a=6378137.0 +rf=298.257222101 '\
         '+pm=0 +x_0=1000000.0 +y_0=0.0 +lon_0=-126.0 +lat_1=50.0 +lat_2=58.5 +lat_0=45.0 '\
         '+units=m +axis=enu +no_defs'

_gt = GeoTransformer(src_epsg=4326, dst_proj4=_proj4)


def _float_try_parse(v):
    try:
        v = float(v)
    except:
        pass
    if isinstance(v, str):
        if 'null' in v:
            v = None
    return v


def _ogrinfo_surveys(x, y):
    cmd = ['ogrinfo', _datadir, 'BC_Soil_Surveys', '-ro', '-al', '-geom=NO', '-spat', x, y, x, y] 
    return _run_ogrinfo(cmd)


def _ogrinfo_surveys_extent(xmin, ymin, xmax, ymax):
    cmd = ['ogrinfo', _datadir, 'BC_Soil_Surveys', '-ro', '-al', '-geom=NO', 
           '-spat', xmin, ymin, xmax, ymax] 
    return _run_ogrinfo(cmd)


def _ogrinfo_layers(soil_id):
    cmd = ['ogrinfo', _datadir, '-sql', f"SELECT * FROM BCSLF_Soil_Layer_File WHERE SOIL_ID = '{soil_id}'", '-ro', '-al']
    return _run_ogrinfo(cmd)


def _run_ogrinfo(cmd):
    p = Popen(cmd, bufsize=0, stdin=PIPE, stdout=PIPE, stderr=STDOUT, universal_newlines=True)
    res, _ = p.communicate()
    d = {}
    key = None
    for l in res.split('\n'):
        l = l.strip()
        if l == '':
            key = None

        if l.startswith('OGRFeature'):
            key = l.split(':')[-1]
            d[key] = {}
        else:
            if key:
                _l = l.split(' = ')
                if len(_l) == 2:
                    _k, _v = _l
                else:
                    _k, _v = _l[0], None

                d[key][_k] = _float_try_parse(_v)
    return d


class SIFT(object):
    def query(self, lng, lat):
        global _gt
        x, y = _gt.transform(lng, lat)
        x, y = str(x), str(y)

        d = _ogrinfo_surveys(x, y)

        for k, _d in d.items():
            d[k]['Layers'] = {}
            for i in range(1, 4):
                soil_id = d[k][f'SOILSYM_{i} (String)']
                if soil_id is not None:
                    d[k]['Layers'][soil_id] = _ogrinfo_layers(soil_id)
            
        return d

    def query_extent(self, extent):
        global _gt

        xmin, ymin, xmax, ymax = extent
        xmin, ymin = _gt.transform(xmin, ymin)
        xmin, ymin = str(xmin), str(ymin)
        xmax, ymax = _gt.transform(xmax, ymax)
        xmax, ymax = str(xmax), str(ymax)

        d = _ogrinfo_surveys_extent(xmin, ymin, xmax, ymax)

        for k, _d in d.items():
            d[k]['Layers'] = {}
            for i in range(1, 4):
                soil_id = d[k][f'SOILSYM_{i} (String)']
                if soil_id is not None:
                    d[k]['Layers'][soil_id] = _ogrinfo_layers(soil_id)
            
        return d

    def _build_horizons(self, dkwargs):
        soil = SiftSoil()
        for k, kwargs in dkwargs.items():
            horizon = SiftHorizon({k.split()[0]: v for k,v in kwargs.items()})
      
            try:
                horizon._rosettaPredict()
            except:
                pass

            try:
                horizon._computeConductivity()
            except:
                pass

            try:
                horizon._computeErodibility()
            except:
                pass

            try:
                horizon._computeAnisotropy()
            except:
                pass

            soil.append(horizon)

#            print('    horizon', k, horizon.hzn_master)

        return soil

    def build_wepp_soil(self, lng, lat, outdir='./'):
        d = self.query(lng, lat)
        return self._build_wepp_soils(d, outdir=outdir)

    def build_wepp_soils(self, extent, outdir='./'):
        d = self.query_extent(extent)
        return self._build_wepp_soils(d, outdir=outdir)

    def _build_wepp_soils(self, d, outdir):
        mukey_cnt, valid_cnt, total_area, covered_area = 0, 0, 0, 0
        unique_soils = set()

        for mukey, _d in d.items():
            mukey_cnt += 1

            with open(_join(outdir, f'{mukey}.json'), 'w') as fp:
                json.dump(d[mukey], fp, indent=2, separators=(',', ': '))

            area = d[mukey]['Shape_Area (Real)']
#            print('mukey', mukey, f'({area/10_000:.0f} ha)')
            total_area += area
            for i in range(1, 4):
                soil_id = d[mukey][f'SOILSYM_{i} (String)']
                soil_name = d[mukey][f'SOILNAME_{i} (String)']
                if soil_id is not None:
                    unique_soils.add(soil_id)
#                    print('  soil_id', soil_id, soil_name)
                    soil = self._build_horizons(d[mukey]['Layers'][soil_id])
                    if soil.valid or soil.is_water:
                        valid_cnt += 1
                        covered_area += area
                        with open(_join(outdir, f'{mukey}.sol'), 'w') as fp:
                            fp.write(str(soil))
                        break

        stats = dict(mukey_cnt=mukey_cnt, valid_cnt=valid_cnt, 
                     total_area=total_area, covered_area=covered_area,
                     unique_soils=unique_soils, unique_soils_cnt=len(unique_soils))

        return stats

def _attr_validator(x):
    if x == -9:
        return None
    else:
        return x 


class SiftSoil(list):
    res_lyr_ksat_threshold = 2.0
    ksflag = 0

    @property
    def datver(self):
        return 7778.0

    @property
    def valid(self):
        for h in self:
            if h.valid:
                return True
        return False

    @property
    def soil_name(self):
        if len(self) == 0:
            return None

        return super().__getitem__(0).soil_name

    slid = soil_name

    @property
    def is_water(self):
        if len(self) == 0:
            return False

        soil_name = self.soil_name.lower()
        return 'water' in soil_name

    @property
    def texid(self):
        if len(self) == 0:
            return None

        return self[0].simple_texture

    @property
    def ki(self):
        if len(self) == 0:
            return None

        return self[0].interrill

    @property
    def kr(self):
        if len(self) == 0:
            return None

        return self[0].rill

    @property
    def shcrit(self):
        if len(self) == 0:
            return None

        return self[0].shear

    @property
    def salb(self):
        """
        surface albedo
        """
        if len(self) == 0:
            return None

        om = self[0].om
        # equation 15 on
        # http://milford.nserl.purdue.edu/weppdocs/usersummary/BaselineSoilErodibilityParameterEstimation.html#Albedo
        return 0.6 / math.exp(0.4 * om)

    @property
    def nsl(self):
        horizon_mask = [h.valid and not h.is_organic for h in self]
        return sum(horizon_mask)

    def __getitem__(self, index):
        return [h for h in self if h.valid and not h.is_organic][index]

    summary_keys = ('SOILNAME',
                    'SOIL_CODE',
                    'LAYER_NO',
                    'HZN_MAS',
                    'LU',
                    'UDEPTH',
                    'LDEPTH',
                    'TSAND',
                    'TCLAY',
                    'TSILT',
                    'VFSAND',
                    'ORGCARB',
                    'WOOD',
                    'COFRAG',
                    'KSAT',
                    'BD',
                    'CEC',
                    'KP33',
                    'KP1500')

    def summary(self):
        if self.nsl == 0:
            return '# (No Horizons)'

        import prettytable
        from prettytable import PrettyTable
        table = PrettyTable(hrules=prettytable.HEADER, vrules=prettytable.NONE) 
        table.field_names = list(self.summary_keys) + ['VALID']
        for h in self:
            table.add_row([h._d[k] for k in self.summary_keys] + [('', 'X')[h.valid]])      
        return '\n'.join([f'# {L}' for L in table.get_string().split('\n')])
    
    def _water(self):
        s = [f"{self.datver}",
              '#',
              '#            WEPPcloud (c) University of Idaho',
              '#',
              '#  Build Date: ' + str(datetime.now()),
              '#  Source Data:  BC Soil Information Finder Tool (SIFT) Database',
              '#',
              'Any comments:',                                  
              '1 1',
              "'water_7778_2'      'Water' 1   0.1600  0.7500  1.0000  0.0100  999.0000    0.1000",
              '210.000000  0.800000    100.000000  10.000000   0.242   0.115   66.800  7.000   3.000   11.300  0.00000',
              '1 10000 100']
        return '\n'.join(s)

    def __str__(self):
        if self.is_water:
            return self._water()

        nsl = self.nsl

        s = [f"{self.datver}",
              '#',
              '#            WEPPcloud (c) University of Idaho',
              '#',
              '#  Build Date: ' + str(datetime.now()),
              '#  Source Data:  BC Soil Information Finder Tool (SIFT) Database',
              '#',
              self.summary(),
              '#',
              "Any Comments:",
             f"1 {self.ksflag}",
             f"'{self.slid}' '{self.texid}' {self.nsl} {self.salb:.03f} {self.ki:.3f} {self.kr:.3f} {self.shcrit:.3f}"]

        # horizons
        for i in range(nsl):
            self[i].is_last = i == nsl - 1
            s.append(str(self[i]))

        # restrictive layer
        # TODO: maybe this should be moved to a SoilMixin
        ksat_min = 1e38        
        ksat_last = None 
        res_lyr_i = None
        res_lyr_ksat = None

        for h in (h for h in self if h.valid and not h.is_organic):
            if h.ksat < ksat_min:
                ksat_min = h.ksat    

            if h.ksat < self.res_lyr_ksat_threshold: 
                res_lyr_i = i
                res_lyr_ksat = ksat_min
    
            ksat_last = h.ksat

        if res_lyr_i is None:
            s.append('1 10000.0 %0.5f' % ksat_last)
        else:
            s.append('1 10000.0 %0.5f' % (res_lyr_ksat * 3.6))

        return '\n'.join(s)


class SiftHorizon(HorizonMixin):
    def __init__(self, kwargs):        
        self._d = kwargs

    @property
    def clay(self):
        return _attr_validator(self._d['TCLAY'])

    @property
    def silt(self):
        silt = _attr_validator(self._d['TSILT'])
        vfs = _attr_validator(self._d['VFSAND'])
        if silt is None and vfs is None:
            return None
        elif silt is None:
            return vfs
        elif vfs is None:
            return silt
        else:
            return vfs + silt
    vfs = silt

    @property
    def sand(self):
        return _attr_validator(self._d['TSAND'])

    @property
    def om(self):
        oc = _attr_validator(self._d['ORGCARB'])
        wood = _attr_validator(self._d['WOOD'])
        if oc is None and wood is None:
            return None
        elif oc is None:
            return wood
        elif wood is None:
            return oc
        else:
            return oc + wood
    orgmat = om

    @property
    def rfg(self):
        return _attr_validator(self._d['COFRAG'])

    @property
    def bd(self):
        return _attr_validator(self._d['BD'])

    @property
    def ksat(self):
        return _attr_validator(self._d['KSAT'])

    @property
    def cec(self):
        return _attr_validator(self._d['CEC'])

    @property
    def hzn_master(self):
        return self._d['HZN_MAS']

    @property
    def is_organic(self):
        return self.hzn_master in ('F', 'FH', 'H', 'L', 'LF', 'LFH', 'LH', 'O')

    @property
    def is_rock(self):
        return self.hzn_master == 'R'

    @property
    def is_water(self):
        return self.hzn_master == 'W'

    @property
    def soil_name(self):
        return self._d['SOILNAME']

    @property
    def depth(self):
        depth = _attr_validator(self._d['LDEPTH'])
        if isfloat(depth):
            depth *= 10.0
        return depth

    @property
    def is_last(self):
        return getattr(self, '_is_last', False)

    @is_last.setter
    def is_last(self, v: bool):
        self._is_last = v

    @property
    def solthk(self):
        v = self.depth
        if self.is_last:
            if v < 200:
                return 200
            return math.ceil(v / 200) * 200
        else:
            return v

    @property
    def valid(self):
        return self.clay is not None and \
               self.sand is not None and \
               self.vfs is not None and \
               self.bd is not None and \
               self.rfg is not None and \
               self.om is not None and \
               self.ksat is not None and \
               isfloat(self.depth) and \
               getattr(self, 'anisotropy', 0) > 0 and \
               getattr(self, 'interrill', 0) > 0 and \
               getattr(self, 'rill', 0) > 0 and \
               getattr(self, 'shear', 0) > 0

    def __str__(self):
        return f'  {self.solthk} {self.bd:.03f} {self.ksat:.03f} {self.anisotropy:.01f} ' \
               f'{self.field_cap:.03f} {self.wilt_pt:.03f} {self.sand:.01f} ' \
               f'{self.clay:.01f} {self.orgmat:.01f} {self.cec:.01f} {self.rfg:.01f}'


if __name__ == "__main__":
    from pprint import pprint
    sift = SIFT()

#    stats = sift.build_wepp_soil(-123.69489669799805, 48.53206641352563)
#    stats = sift.build_wepp_soil(-123.7, 48.549)  # water
    stats = sift.build_wepp_soils([-123.9, 48.39, -123.54, 48.6])

    print()
    pprint(stats)
