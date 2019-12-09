# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from typing import List, Set, Union, Dict
import csv
from os.path import join as _join
from os.path import exists as _exists
import warnings

from xml.etree import ElementTree
from math import exp
from collections import OrderedDict

import sqlite3

from wepppy.all_your_base import *

from wepppy.wepp.soils.utils import simple_texture

__version__ = 'v.0.1.0'

_thisdir = os.path.dirname(__file__)
# _ssurgo_cache_db = ":memory:"  # _join(_thisdir, 'ssurgo_cache.db')
_ssurgo_cache_db = _join(_thisdir, 'data', 'surgo', 'surgo_tabular.db')
_statsgo_cache_db = _join(_thisdir, 'data', 'statsgo', 'statsgo_tabular.db')

# Developer Notes
###################
#
# Documentation on the available tables
# http://www.anslab.iastate.edu/Class/AnS321L/soil%20view%20Marshall%20county/data/metadata/SSURGO%20Metadata%20Tables.pdf
# 
# Documentation on data in columns
# https://sdmdataaccess.nrcs.usda.gov/documents/TableColumnDescriptionsReport.pdf
#
# SSURGO 2.2 Data Model
# https://www.nrcs.usda.gov/Internet/FSE_DOCUMENTS/nrcs142p2_050900.pdf
#
# Web portal to test queries
# https://sdmdataaccess.nrcs.usda.gov/Query.aspx


_ssurgo_url = 'https://SDMDataAccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx'
_query_template = '''\
<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <RunQuery xmlns="http://SDMDataAccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx">
      <Query>{query}</Query>
    </RunQuery>
  </soap12:Body>
</soap12:Envelope>'''


class SsurgoRequestError(Exception):
    """
    Ssurgo request did not return 200 status code
    """


# noinspection PyPep8Naming
def _makeSOAPrequest(query):
    global _ssurgo_url, _query_template
    headers = {'Content-Type': 'application/soap+xml; charset=utf-8'}
    body = _query_template.format(query=query)
    r = requests.post(_ssurgo_url, data=body, headers=headers, timeout=30)

    if r.status_code != 200:
        raise SsurgoRequestError((r.content, query))

    return r.content


def _extract_table(xml):
    """
    extracts table data from xml returned from ssurgo

    data is organized as a list of tuples with value keys
    """
    two_keys = set()
    table = []
    root = ElementTree.fromstring(xml)
    for i, row in enumerate(root.iter('Table')):
        children = row.getchildren()
        children = tuple(try_parse(c.text) for c in children)
        key = (children[0], children[1])
        if key not in two_keys:
            two_keys.add(key)
            table.append(children)

    return table


def _extract_unique(xml):
    """
    extracts table data from xml returned from ssurgo

    data is organized as a list of tuples with value keys
    """
    elements = set()
    table = []
    root = ElementTree.fromstring(xml)
    for i, row in enumerate(root.iter('Table')):
        children = row.getchildren()
        children = tuple(try_parse(c.text) for c in children)
        key = children[0]
        if key not in elements:
            elements.add(key)
            table.append(children)

    return table


def query_mukeys_in_extent(extent: List[float]) -> Union[Set[int], None]:
    """
    Query ssurgo to determine the mukeys in the extent

    :param extent:
        xmin, ymin, xmax, ymax

    :return:
        list of mukeys
    """

    assert len(extent) == 4
    assert extent[0] < extent[2]
    assert extent[1] < extent[3]

    query = 'https://sdmdataaccess.nrcs.usda.gov/Spatial/SDMWGS84Geographic.wfs?' \
            'SERVICE=WFS&' \
            'VERSION=1.1.0&' \
            'REQUEST=GetFeature&' \
            'TYPENAME=MapunitPoly&' \
            'OUTPUTFORMAT=XMLMukeyList&' \
            'MAXFEATURES=25000&' \
            'BBOX=%s' % (','.join(map(str, extent)))

    r = requests.get(query)

    if r.status_code != 200:
        raise SsurgoRequestError

    xml = r.text
    root = ElementTree.fromstring(xml)

    assert root.tag == 'MapUnitKeyList'
    if root.text == '':
        return None

    mukeys = root.text.split(',')
    mukeys = set(int(v) for v in mukeys)

    return mukeys


class MajorComponent:
    def __init__(self, component):
        self.muname = None
        self.albedodry_r = None
        for k, v in component.items():
            setattr(self, k, v)


# noinspection PyPep8Naming
class Horizon:
    def __init__(self, cokey, layer, defaults=None):
        self.cokey = cokey
        
        if defaults is None:
            defaults = {}

        self.claytotal_r = None
        self.sandtotal_r = None
        self.cec7_r = None
        self.sandvf_r = None
        self.om_r = None
        self.ll_r = None

        self.hzdepb_r = None
        self.desgnmaster = None
        self.fraggt10_r = None
        self.frag3to10_r = None
        self.sieveno10_r = None
        self.wthirdbar_r = None
        self.wfifteenbar_r = None
        self.ksat_r = None
        self.dbthirdbar_r = None

        for k, v in layer.items():
            # we want to copy the current the current layer
            # but for each layer we need to apply defaults and
            # estimate some additional values
            if k in defaults and not isfloat(v):
                setattr(self, k, defaults[k])
            else:
                setattr(self, k, v)

        self._computeAnisotropy()
        self._computeRock(defaults.get('smr', None), 
                          defaults.get('field_cap', None),
                          defaults.get('wilt_pt', None))
        self._computeConductivity()
        
    def _computeConductivity(self):
        
        clay = try_parse_float(self.claytotal_r)
        sand = try_parse_float(self.sandtotal_r)
        cec = try_parse_float(self.cec7_r)

        conductivity = 0 
        
        # conductivity
        if sand == 0.0 or clay == 0.0 or cec == 0.0:
            return conductivity
            
        if clay <= 40.0:
            if cec > 1.0:
                # apply equation 1 from usersum.pdf
                conductivity = -0.265 + 0.0086 * pow(sand, 1.8) + \
                               11.46 * pow(cec, -0.75) 
            else:
                # this isn't documented in the usersum.pdf
                # this is what is being applied in the watershed
                # interface
                conductivity = 11.195 + 0.0086 * pow(sand, 1.8)  
        else:
            # apply equation 2 from usersum.pdf
            conductivity = 0.0066 * exp(244.0 / clay) 
            
        self.conductivity = conductivity
        
    def _computeErodibility(self):
        """
        Computes erodibility estimates according to:
        
        https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/usersum.pdf
        """
        clay = try_parse_float(self.claytotal_r)
        sand = try_parse_float(self.sandtotal_r)
#        cec = try_parse_float(self.cec7_r)
        vfs = try_parse_float(self.sandvf_r)
        om = try_parse_float(self.om_r)
        
        # interrill, rill, shear
        if sand == 0.0 or vfs == 0.0 or om == 0.0 or clay == 0.0:
            self.interrill = 0.0
            self.rill = 0.0
            self.shear = 0.0
            return 
        
        if sand >= 30.0:
            if vfs > 40.0:
                vfs = 40.0
            if om < 0.35:
                om = 0.35
            if clay > 40.0:
                clay = 40.0
                
            # apply equation 6 from usersum.pdf
            interrill = 2728000.0 + 192100.0 * vfs
            
            # apply equation 7 from usersum.pdf
            rill = 0.00197 + 0.00030 * vfs + 0.03863 * exp(-1.84 * om) 
            
            # apply equation 8 from usersum.pdf
            shear = 2.67 + 0.065 * clay - 0.058 * vfs
        else:
            if clay < 10.0:
                clay = 10.0
                
            # apply equation 9 from usersum.pdf
            interrill = 6054000.0 - 55130.0 * clay
            
            # apply equation 10 from usersum.pdf
            rill = 0.0069 + 0.134 * exp(-0.20 * clay)
            
            # apply equation 11 from usersum.pdf
            shear = 3.5
      
        self.interrill = interrill
        self.rill = rill
        self.shear = shear
        
    def _computeAnisotropy(self):
        
        hzdepb_r = self.hzdepb_r
        
        anisotropy = None
        if isfloat(hzdepb_r):
            if hzdepb_r > 50:
                anisotropy = 1.0
            else:
                anisotropy = 10.0
                
        self.anisotropy = anisotropy
  
    def _computeRock(self, rock_default, 
                     field_cap_default, wilt_pt_default):
                     
        desgnmaster = self.desgnmaster
        fraggt10_r = self.fraggt10_r
        frag3to10_r = self.frag3to10_r
        sieveno10_r = self.sieveno10_r
        wthirdbar_r = self.wthirdbar_r
        wfifteenbar_r = self.wfifteenbar_r
        
        if desgnmaster is None or \
           desgnmaster.startswith('O') or \
           not isfloat(sieveno10_r):
            self.smr = rock_default
            self.field_cap = field_cap_default
            self.wilt_pt = wilt_pt_default
            return
            
        # calculate rock content
        if not isfloat(fraggt10_r):
            fraggt10_r = 0.0
            
        if not isfloat(frag3to10_r):
            frag3to10_r = 0.0
            
        rocks_soil = fraggt10_r + frag3to10_r
        rock = (100.0-rocks_soil) / 100.0 * (100.0-sieveno10_r) + rocks_soil
        not_rock = 100.0 - rock

        # calculate wc
        if not_rock == 0.0:
            fc = 0.001
        elif not isfloat(wthirdbar_r):
            fc = field_cap_default
        else:
            fc = wthirdbar_r / not_rock

        # calculate fc
        if not_rock == 0.0:
            wc = 0.001
        elif not isfloat(wfifteenbar_r):
            wc = wilt_pt_default
        else:
            wc = wfifteenbar_r / not_rock

        self.smr = rock
        self.field_cap = fc
        self.wilt_pt = wc
        
    def valid(self):
        return isfloat(self.hzdepb_r) and \
               isfloat(self.sandtotal_r) and \
               isfloat(self.claytotal_r) and \
               isfloat(self.om_r) and \
               isfloat(self.cec7_r) and \
               isfloat(self.sandvf_r) and \
               isfloat(self.ksat_r) and \
               isfloat(self.dbthirdbar_r)

    @property
    def simple_texture(self):
        """
        Classifies horizon texture into silt loam, loam, sand loam, and clay loam

        Courtesy of Mary Ellen Miller
        :return:
        """
        return simple_texture(self.claytotal_r, self.sandtotal_r)



colors = [
    '#ec891d', '#66cd00', '#f1e8ca', '#ead61c', '#5588ff', '#ffc425', '#00b159', '#9958db',
    '#e8702a', '#6bd2db', '#556f55', '#845422', '#ffbe4f', '#ffb6c1', '#77aaff', '#bbcbdb',
    '#0f8880', '#4f2f4f', '#9ebd9e', '#4a4aa2', '#ff0000', '#06357a', '#d11141', '#fffeb3',
    '#c3e4f3', '#448899', '#9fb5ad', '#745151', '#9b4848', '#ffbfd3', '#8b8282', '#0ea7b5',
    '#bbeeff', '#5959db', '#ff9b83', '#5e3c58', '#666547', '#6fcb9f', '#bcd5bc', '#ffe28a',
    '#708965', '#dd855c', '#55aaaa', '#507e4e', '#0c457d', '#d7c797', '#3366ff', '#ff00a9',
    '#253949', '#fb5858', '#f37735', '#a47c48', '#afb064', '#91cfec', '#5c596d', '#d0e596',
    '#259ed9', '#014a01', '#00aedb', '#95c485']


class SoilSummary(object):
    def __init__(self, **kwargs):
        mukey = kwargs.get("Mukey", None)
        assert mukey is not None

        if isint(mukey):
            self.mukey = int(mukey)
            self.color = colors[self.mukey % len(colors)]

        else:
            self.mukey = mukey
            self.color = colors[sum(str.encode(mukey)) % len(colors)]

        self.fname = kwargs["FileName"]
        self.soils_dir = kwargs["soils_dir"]
        self.build_date = kwargs["BuildDate"]
        self.desc = kwargs["Description"]

        self.area = 0.0
        self.pct_coverage = kwargs.get('pct_coverage', None)

        self.clay = None
        self.sand = None
        self.ll = None
        self.simple_texture = None
        self.texture = None

    def as_dict(self):
        return dict(mukey=self.mukey, fname=self.fname,
                    soils_dir=self.soils_dir,
                    build_date=self.build_date, desc=self.desc,
                    color=self.color, area=self.area,
                    pct_coverage=self.pct_coverage,
                    clay=self.clay, sand=self.sand, ll=self.ll,
                    simple_texture=self.simple_texture)

    @property
    def path(self):
        return _join(self.soils_dir, self.fname)


# noinspection PyPep8Naming,PyProtectedMember
class WeppSoil:
    def __init__(self, ssurgo_c, mukey, initial_ksat=0.75, 
                 horizon_defaults=None,
                 res_lyr_ksat_threshold=2.0):
                      
        assert mukey in ssurgo_c.mukeys        
        
        self.ssurgo_c = ssurgo_c
        self.mukey = mukey
        self.initial_ksat = initial_ksat
        self.horizons = None
        self.horizons_mask = None
        self.majorComponent = None
        self.res_lyr_i = None  # index of res_lyr in horizon
        self.res_lyr_ksat = None
        self.num_layers = 0
        self.res_lyr_ksat_threshold = res_lyr_ksat_threshold
        self.albedo_estimated = False
        self.is_urban = False
        self.is_water = False
        
        self._disclaimer = """\
THIS FILE AND THE CONTAINED DATA IS PROVIDED BY THE UNIVERSITY OF IDAHO 
'AS IS' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED 
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A 
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL UNIVERSITY OF IDAHO 
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHElementTreeHER IN 
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
ARISING IN ANY WAY OUT OF THE USE OF THIS FILE, EVEN IF ADVISED OF THE 
POSSIBILITY OF SUCH DAMAGE."""
        
        if horizon_defaults is None:
            self.horizon_defaults = {}
        else:
            self.horizon_defaults = horizon_defaults
        
        self.num_ofes = 1
        self.log = None
        
        self.build()

    @property
    def short_description(self):
        if self.is_urban:
            return "Urban"
        elif self.is_water:
            return "Water"
        else:
            return "%s (%s)" % (self.majorComponent.muname, 
                                self.horizons[0].texture)
                
    def build(self):
        """
        Return the major component for a given mukey is the component 
        with the highest comppct_r value and a obtained cokey. If no 
        components have a usable cokey then None is returned.
        """
        ssurgo_c = self.ssurgo_c
        mukey = self.mukey
        self.log = ['mukey: {}'.format(mukey)]
        
        components = ssurgo_c.get_components(mukey)
        self.log.append('found {} components'.format(len(components)))

        self.log.append('looping over components')
        for c in components:
            cokey = c['cokey']
            self.log.append('analyzing cokey {}'.format(cokey))

            horizons, mask = self._getHorizons(cokey)
            if sum(mask) > 0:
                self.log.append('building major component')
                self.majorComponent = MajorComponent(c)
                self.horizons = horizons
                self.horizons_mask = mask
                if not isfloat(self.majorComponent.albedodry_r):
                    self._compute_albedo()
                self._analyze_restrictive_layer()
                self._build_description()

                self.log.append('done')
                return 1
                
        # is urban?
        if np.any(['urban' in c['compname'].lower() for c in components]):
            self.log.append('identified as urban')
            self.is_urban = True
            self._build_description()
            return 1

        # is water?
        if np.any(['water' in c['compname'].lower() for c in components]):
            self.log.append('identified as water')
            self.is_water = True
            self._build_description()
            return 1
           
        # Failed to find a valid_mukeys
        self.log.append('build failed to find valid mukeys')
        self.horizons = None
        return 0
        
    def getFirstHorizon(self):
        if self.is_urban or self.is_water:
            return None
    
        for h, m in zip(self.horizons, self.horizons_mask):
            if m == 0:
                continue
            return h
            
        return None
    
    def _getHorizons(self, cokey):
        """
        Return all layer information matching the cokey, ordered by depth
        """
        defaults = self.horizon_defaults
        ssurgo_c = self.ssurgo_c
        
        layers = ssurgo_c.get_layers(cokey)
        self.log.append('found {} layers'.format(len(layers)))
            
        horizons = []
        
        for L in layers:
            chkey = L['chkey']
            self.log.append('analyzing chkey {}'.format(chkey))

            L['fragvol_r'] = ssurgo_c.get_fragvol_r(chkey)
            L['texture'] = ssurgo_c.get_texture(chkey)
            L['reskind'] = ssurgo_c.get_reskind(L['cokey'])
            h = Horizon(cokey, L, defaults)
            horizons.append(h)
        
        # create mask of valid layers
        horizons_mask = [h.valid() for h in horizons]
        self.log.append('horizons mask: {}'.format(horizons_mask))

        # compute erodibility for top layer
        if len(horizons) > 0:
            horizons[0]._computeErodibility()
            self.log.append('computing erodibility for h0')

        return horizons, horizons_mask
        
    def _compute_albedo(self):
        """
        equation 15 on
        http://milford.nserl.purdue.edu/weppdocs/usersummary/BaselineSoilErodibilityParameterEstimation.html#Albedo
        """
        om_r = self.horizons[0].om_r
        self.majorComponent.albedodry_r = \
            0.6 / exp(0.4 * om_r)
        self.albedo_estimated = 1
        
    def _analyze_restrictive_layer(self):
        """
        """
        horizons = self.horizons
        horizons_mask = self.horizons_mask
        
        res_lyr_ksat_threshold = self.res_lyr_ksat_threshold
        
        ksat_min = 1e38
        n = 0
        
        # iterate over the layers and look for res_lyr
        for i, (h, m) in enumerate(zip(horizons, horizons_mask)):
            if isfloat(h.ksat_r) and h.ksat_r < ksat_min:
                ksat_min = h.ksat_r

            n += m

            if isfloat(h.ksat_r) and h.ksat_r < res_lyr_ksat_threshold:
                self.res_lyr_i = i
                self.res_lyr_ksat = ksat_min * 0.01
                break

        # determine number of layers
        n = 0
        for i, (h, m) in enumerate(zip(horizons, horizons_mask)):
            if i == self.res_lyr_i:
                break

            if m == 0:
                #  depth += h.hzdepb_r
                continue

            n += 1

        self.num_layers = n

        self.log.append('identified {} layers, ksat_min={}'.format(n, ksat_min))

    def _abbreviated_description(self):
    
        s = ['',
             '            WEPPcloud ' + __version__ + ' (c) University of Idaho',
             '',
             '  Build Date: ' + str(datetime.now()),
             '  Source Data: Default Soil Type',
             '']
             
        s.extend(self._disclaimer.split('\n'))
        
        s = ['# %s' % L for L in s]
        self.description = '\n'.join(s)
        
    def _build_description(self):
    
        source_data = self.ssurgo_c.source_data

        if self.is_urban or self.is_water:
            self._abbreviated_description()
            return
            
        s = ['',
             '            WEPPcloud ' + __version__ + ' (c) University of Idaho',
             '',
             '  Build Date: ' + str(datetime.now()),
             '  Source Data: ' + source_data,
             '',
             'Mukey: %s' % str(self.mukey),
             'Major Component: {0.cokey} (comppct_r = {0.comppct_r})'
             .format(self.majorComponent),
             'Texture: {}'
             .format(self.getFirstHorizon().simple_texture),
             '',
             '  Chkey   hzname  mask hzdepb_r  ksat_r fraggt10_r frag3to10_r dbthirdbar_r',
             '----------------------------------------------------------------------------']
             
        for i, h in enumerate(self.horizons):
            desc = ''
            if not self.horizons_mask[i]:
                desc = 'X'
            if self.res_lyr_i == i:
                desc = 'R'
             
            ksat = h.ksat_r   
            
            foo = [h.chkey, h.hzname, desc, h.hzdepb_r, ksat, 
                   h.fraggt10_r, h.frag3to10_r, h.dbthirdbar_r]
            foo = [[v, ' - '][v is None] for v in foo]
            s.append(' {0:<11}{1:<5}{2:>3}{3:>11}{4:>8}{5:>11}{6:>12}{7:>13}'
                     .format(*foo))
            
        s.extend(['',
                  'Restricting Layer:',
                  '    ksat threshold: %0.05f' % self.res_lyr_ksat_threshold])
                  
        if self.res_lyr_ksat is not None:
            s.extend(['    type: %s' % self.horizons[self.res_lyr_i].reskind,
                      '    ksat: %0.05f' % float(self.res_lyr_ksat),
                      ''])
        
        else:
            s.extend(['    type: -',
                      '    ksat: -',
                      ''])
        
        if len(self.horizon_defaults) > 0:
            s.append('defaults applied to missing chorizon data:')
            for k, v in self.horizon_defaults.items():
                s.append('    {0:<12} -> {1:>11}'.format(k, '%0.3f' % v))
             
        s.append('')
        
        s.append('Build Notes:')
        s.append('  initial assumed ksat = %0.03f' % self.initial_ksat)
        if self.albedo_estimated:
            s.append('  albedo estimated from om_r')
            s.append('')
            
        val_file = 'erin_lt_files/%s.sol' % str(self.mukey)
        if _exists(val_file):
            s.append('')
            s.append('VALIDATION FILE: %s' % val_file)
            s.append('#'*78)
            s.extend([L.strip() for L in open(val_file).readlines()])
            s.append('#'*78)
            s.append('')
            
        s.extend(self._disclaimer.split('\n'))
        s.extend('''

  If you change the original contexts of this file please 
  indicate it by putting an 'X' in the box here -> [ ]

'''.split('\n'))

        s = ['# %s' % L for L in s]
        self.description = '\n'.join(s)

    @property
    def has_majorComponent(self) -> bool:
        return self.majorComponent is not None

    @property
    def has_horizons(self) -> bool:
        return self.horizons is not None and self.num_layers > 0

    def valid(self) -> bool:
        if self.is_urban:
            self.log.append('Validity: is_urban')
            return True

        if self.is_water:
            self.log.append('Validity: is_water')
            return True

        if not self.has_majorComponent:
            self.log.append('Validity: no majorComponent')
            return False

        if not self.has_horizons:
            self.log.append('Validity: no horizons')
            return False

        if len(self.horizons) < self.num_layers:
            self.log.append('Validity: horizons < num_layers')
            return False

        self.log.append('Validity: all checks passed')
        return True
   
    def _build_urban(self):
        return '''7778\n''' + self.description + '''        
Any comments:                               
1  1                                        
'Urban_1'\t\t'Urban'\t1\t0.16\t0.75\t4649000\t0.0140\t2.648\t0.0000
210\t1.4\t100.8\t10\t 0.242\t 0.1145\t 66.8\t7\t3\t11.3\t55.5
1\t10000\t100.8'''

    def _build_urban_v2006_2(self):
        return '''2006.2\n''' + self.description + '''        
Any comments:                               
1  1                                        
'Urban_1'\t\t'Urban'\t1\t0.16\t0.75\t4649000\t0.0140\t2.648\t100.8
210\t 66.8\t7\t3\t11.3\t55.5
1\t10000\t100.8'''

    def _build_water(self):
        return '''7778\n''' + self.description + '''
Any comments:                                   
1 1
'water_7778_2'		'Water'	1 	0.1600 	0.7500 	1.0000 	0.0100 	999.0000 	0.1000
	210.000000 	1.400000 	100.000000 	10.000000 	0.242 	0.115 	66.800 	7.000 	3.000 	11.300	55.500
0 0 0'''

    def _build_water_v2006_2(self):
        return '''2006.2\n''' + self.description + '''
Any comments:                                   
1  0                                        
'Water_1'\t'Water'\t0 0.000000\t0.750000\t0.000000\t0.000000\t0.000000\t0.000000
0\t0\t0'''

    def write(self, wd='./', overwrite=True, fname=None, db_build=False, version='7778') -> SoilSummary:
        assert version in ['7778', '2006.2']
        assert _exists(wd), wd

        if version == '7778':
            return self._write7778(wd, overwrite, fname, db_build)

        else:
            return self._write2006_2(wd, overwrite, fname, db_build)

    def _write7778(self, wd, overwrite, fname, db_build):
        txt = self.build_file_contents()
        txt = txt.replace('\r\n', '\n').replace('\r', '\n')
        txt = '\r\n'.join(txt.splitlines())

        mukey = str(self.mukey)

        if db_build:
            wd = _join(wd, mukey[:3])
            if not _exists(wd):
                os.mkdir(wd)

        if fname is None:
            fname = '%s.sol' % mukey
        fpath = _join(wd, fname)
            
        if _exists(fpath):
            if overwrite:
                os.remove(fpath)
            else:
                return
        
        with open(fpath, 'w') as fp:
            fp.write(txt)

        return SoilSummary(
            Mukey=int(mukey),
            FileName=fname,
            soils_dir=wd,
            BuildDate=str(datetime.now()),
            Description=self.short_description
        )

    def _write2006_2(self, wd, overwrite, fname, db_build):
        txt = self.build_file_contents_v2006_2()
        txt = txt.replace('\r\n', '\n').replace('\r', '\n')
        txt = '\r\n'.join(txt.splitlines())

        mukey = str(self.mukey)

        if db_build:
            wd = _join(wd, mukey[:3])
            if not _exists(wd):
                os.mkdir(wd)

        if fname is None:
            fname = '%s.sol' % mukey
        fpath = _join(wd, fname)

        if _exists(fpath):
            if overwrite:
                os.remove(fpath)
            else:
                return

        with open(fpath, 'w') as fp:
            fp.write(txt)

        return SoilSummary(
            Mukey=int(mukey),
            FileName=fname,
            soils_dir=wd,
            BuildDate=str(datetime.now()),
            Description=self.short_description
        )

    def write_log(self, wd='./', overwrite=True, fname=None, db_build=False):
        assert _exists(wd), wd

        if self.log is None:
            txt = 'Log is empty'
        else:
            txt = '\n'.join(self.log)
        mukey = str(self.mukey)

        if db_build:
            wd = _join(wd, mukey[:3])
            if not _exists(wd):
                os.mkdir(wd)

        if fname is None:
            fname = _join(wd, '%s.log' % str(self.mukey))
        else:
            fname = _join(wd, fname)

        if _exists(fname):
            if overwrite:
                os.remove(fname)
            else:
                return

        with open(fname, 'w') as fp:
            fp.write(txt)

    def build_file_contents(self):
        assert self.valid()
                
        if self.is_urban:
            return self._build_urban()
            
        if self.is_water:
            return self._build_water()

        s = "7778\n{0.description}\nAny comments:\n{0.num_ofes} 1\n"\
            "'{majorComponent.muname}'\t\t'{horizon0.texture}'\t"\
            "{0.num_layers}\t{majorComponent.albedodry_r:0.4f}\t"\
            "{0.initial_ksat:0.4f}\t{horizon0.interrill:0.2f}\t{horizon0.rill:0.4f}\t"\
            "{horizon0.shear:0.4f}\t0.0000"

        s = [s.format(self, majorComponent=self.majorComponent,
                      horizon0=self.horizons[0])]

        ksat_last = 0.0
        
        last_valid_i = None
        for i, m in enumerate(self.horizons_mask):
            if i == self.res_lyr_i:
                break

            if m:
                last_valid_i = i

        assert len(self.horizons) == len(self.horizons_mask)

        total_depth = 0.0
        for i, (h, m) in enumerate(zip(self.horizons, self.horizons_mask)):

            if i == self.res_lyr_i:
                break

            if not m:
                #  depth += h.hzdepb_r
                continue
            
            hzdepb_r10 = h.hzdepb_r * 10.0

            # check if on last layer
            if i == last_valid_i:
                # make sure the total depth is at least 200 mm
                if hzdepb_r10 < 210.0:
                    hzdepb_r10 = 210.0

            s2 = '{hzdepb_r10:0.03f}\t{0.dbthirdbar_r:0.02f}\t{ksat:0.04f}\t'\
                 '{0.anisotropy:0.01f}\t{0.field_cap:0.04f}\t{0.wilt_pt:0.04f}\t'\
                 '{0.sandtotal_r:0.2f}\t{0.claytotal_r:0.2f}\t{0.om_r:0.2f}\t'\
                 '{0.cec7_r:0.2f}\t{0.smr:0.2f}'\
                 .format(h, ksat=h.ksat_r * 3.6, hzdepb_r10=hzdepb_r10)
            ksat_last = h.ksat_r * 3.6
                
            # make the layers easier to read by making cols fixed width
            # aligning to the right.
            s2 = '{0:>9}\t{1:>8}\t{2:>9}\t'\
                 '{3:>5}\t{4:>9}\t{5:>9}\t'\
                 '{6:>7}\t{7:>7}\t{8:>7}\t'\
                 '{9:>7}\t{10:>7}'.format(*s2.split())
                 
            s.append('\t' + s2)
            depth = 0.0

        if self.res_lyr_i is None:
            s.append('1 10000.0 %0.5f' % ksat_last)
        else:
            s.append('1 10000.0 %0.5f' % (self.res_lyr_ksat * 3.6))
            
        return '\n'.join(s)

    def build_file_contents_v2006_2(self):
        assert self.valid()

        if self.is_urban:
            return self._build_urban_v2006_2()

        if self.is_water:
            return self._build_water_v2006_2()

        s = "2006.2\n{0.description}\nAny comments:\n{0.num_ofes} 1\n" \
            "'{majorComponent.muname}'\t\t'{horizon0.texture}'\t" \
            "{0.num_layers}\t{majorComponent.albedodry_r:0.4f}\t" \
            "{0.initial_ksat:0.4f}\t{horizon0.interrill:0.2f}\t{horizon0.rill:0.4f}\t" \
            "{horizon0.shear:0.4f}\t{ksat:0.4f}"

        s = [s.format(self, majorComponent=self.majorComponent,
                      horizon0=self.horizons[0],
                      ksat=self.horizons[0].ksat_r * 3.6)]

        ksat_last = 0.0

        last_valid_i = None
        for i, m in enumerate(self.horizons_mask):
            if i == self.res_lyr_i:
                break

            if m:
                last_valid_i = i

        assert len(self.horizons) == len(self.horizons_mask)

        total_depth = 0.0
        for i, (h, m) in enumerate(zip(self.horizons, self.horizons_mask)):

            if i == self.res_lyr_i:
                break

            if m == 0:
                #  depth += h.hzdepb_r
                continue

            hzdepb_r10 = h.hzdepb_r * 10.0

            # check if on last layer
            if i == last_valid_i:
                # make sure the total depth is at least 200 mm
                if hzdepb_r10 < 210.0:
                    hzdepb_r10 = 210.0

            s2 = '{hzdepb_r10:0.03f}\t'\
                 '{0.sandtotal_r:0.2f}\t{0.claytotal_r:0.2f}\t{0.om_r:0.2f}\t' \
                 '{0.cec7_r:0.2f}\t{0.smr:0.2f}' \
                .format(h, hzdepb_r10=hzdepb_r10)
            ksat_last = h.ksat_r * 3.6

            # make the layers easier to read by making cols fixed width
            # aligning to the right.
            s2 = '{0:>9}\t' \
                 '{1:>7}\t{2:>7}\t{3:>7}\t' \
                 '{4:>7}\t{5:>7}'.format(*s2.split())


            s.append('\t' + s2)
            depth = 0.0

        if self.res_lyr_i is None:
            s.append('1 10000.0 %0.5f' % ksat_last)
        else:
            s.append('1 10000.0 %0.5f' % (self.res_lyr_ksat * 3.6))

        return '\n'.join(s)


def _fetch_components(mukeys):
    """
    queries the ssurgo server to get soil component information from map unit
    keys (mukeys)
    """
    keys = ','.join([str(k) for k in mukeys])
    query = 'SELECT component.mukey, component.cokey, ' \
            'component.compname, component.comppct_r, ' \
            'component.albedodry_r, component.hydricrating, ' \
            'component.drainagecl, muaggatt.muname, ' \
            'muaggatt.wtdepannmin, muaggatt.flodfreqdcd, ' \
            'muaggatt.aws025wta, muaggatt.aws0150wta, ' \
            'muaggatt.hydgrpdcd, muaggatt.drclassdcd, ' \
            'component.taxclname, component.geomdesc, ' \
            'component.taxorder, component.taxsuborder ' \
            'FROM component ' \
            'INNER JOIN muaggatt ON component.mukey=muaggatt.mukey ' \
            'WHERE component.mukey IN ( %s ) ORDER BY mukey' % keys

    xml = _makeSOAPrequest(query)
    return _extract_table(xml)


def _fetch_chorizon(cokeys):
    """
    queries the ssurgo server to get soil chorizon information.
    """
    keys = ','.join([str(k) for k in cokeys])
    query = 'SELECT cokey, chkey, hzname,  hzdepb_r,  hzdept_r, hzthk_r, ' \
            'dbthirdbar_r, ksat_r, sandtotal_r, claytotal_r, ' \
            'om_r, cec7_r, awc_l, fraggt10_r, frag3to10_r, ' \
            'desgnmaster, sieveno10_r, wthirdbar_r, wfifteenbar_r, ' \
            'sandvf_r, ll_r ' \
            'FROM chorizon ' \
            'WHERE cokey IN (%s) ORDER BY cokey' % keys

    xml = _makeSOAPrequest(query)
    return _extract_table(xml)


def _fetch_chfrags(chkeys):
    keys = ','.join([str(k) for k in chkeys])

    query = 'SELECT chkey, fragvol_r ' \
            'FROM chfrags ' \
            'WHERE chkey IN (%s) ORDER BY chkey' % keys

    xml = _makeSOAPrequest(query)
    return _extract_unique(xml)


def _fetch_chtexturegrp(chkeys):
    keys = ','.join([str(k) for k in chkeys])

    query = 'SELECT chkey, texture ' \
            'FROM chtexturegrp ' \
            'WHERE chkey IN (%s) ORDER BY chkey' % keys

    xml = _makeSOAPrequest(query)
    return _extract_unique(xml)


def _fetch_corestrictions(cokeys):
    keys = ','.join([str(k) for k in cokeys])

    query = 'SELECT cokey, reskind ' \
            'FROM corestrictions ' \
            'WHERE cokey IN (%s) ORDER BY cokey' % keys

    xml = _makeSOAPrequest(query)
    return _extract_unique(xml)


# noinspection PyPep8Naming
class SurgoSoilCollection(object):
    """
    Represents a collection of soil data
    
    see the following document for information on the schema:
        https://www.nrcs.usda.gov/Internet/FSE_DOCUMENTS/nrcs142p2_050900.pdf
    """
    def __init__(self, mukeys, use_statsgo=False):
        """
        Builds a collection of soil components and layers from a list of mukeys.
        SSurgo is queried when the collection is initialized.
        """
        mukeys = [int(v) for v in mukeys]
        if use_statsgo:
            self.conn = sqlite3.connect(_statsgo_cache_db)
            self.source_data = 'StatsGo'
        else:
            self.conn = sqlite3.connect(_ssurgo_cache_db)
            self.source_data = 'Surgo'

        self.cur = cur = self.conn.cursor()
        self._initialize_cache_db()

        n = 0

        # component
        n += self._sync('component', _fetch_components, 'mukey', mukeys)
        
        # identify cokeys
        query = 'SELECT  cokey FROM component WHERE mukey in (%s)' \
                % ','.join([str(k) for k in mukeys])
        cokeys = [r[0] for r in cur.execute(query)]
        
        # chorizon
        n += self._sync('chorizon', _fetch_chorizon, 'cokey', cokeys)
    
        # corestrictions
        n += self._sync('corestrictions', _fetch_corestrictions, 'cokey', cokeys, True)
        
        # identify chkeys
        query = 'SELECT chkey FROM chorizon WHERE cokey in (%s)' \
                % ','.join([str(k) for k in cokeys])
        chkeys = [r[0] for r in cur.execute(query)]
        
        # chfrags
        n += self._sync('chfrags', _fetch_chfrags, 'chkey', chkeys, True)
        
        # chtexturegrp
        n += self._sync('chtexturegrp', _fetch_chtexturegrp, 'chkey', chkeys, True)
        
        # store keys to instance
        self._sync_n = n
        self.mukeys = mukeys
        self.cokeys = cokeys
        self.chkeys = chkeys

        self.weppSoils = None
        self.invalidSoils = None

    def dump(self, table, fname):
        conn, cur = self.conn, self.cur

        if table == 'component':
            keyname = 'mukey'
            keys = ','.join([str(k) for k in self.mukeys])
        elif table == 'chorizon':
            keyname = 'cokey'
            keys = ','.join([str(k) for k in self.cokeys])
        elif table in ['chfrags', 'chtexturegrp']:
            keyname = 'chkey'
            keys = ','.join([str(k) for k in self.chkeys])

        query = 'SELECT * FROM {table} WHERE {keyname} IN ({keys})' \
            .format(table=table, keyname=keyname, keys=keys)

        cur = conn.execute(query)
        hdr = [desc[0] for desc in cur.description]
        listofdicts = [dict(zip(hdr, r)) for r in cur.fetchall()]

        csvfile = open(fname, 'w')
        fieldnames = listofdicts[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames,
                                lineterminator='\n')
        writer.writeheader()
        for c in listofdicts:
            writer.writerow(c)
        csvfile.close()

    def makeWeppSoils(self, initial_ksat=0.75, verbose=False,
                      horizon_defaults=OrderedDict([('sandtotal_r', 66.8),
                                               ('claytotal_r', 7.0),
                                               ('om_r', 7.0),
                                               ('cec7_r', 11.3),
                                               ('sandvf_r', 10.0),
                                               ('ksat_r', 28.0),
                                               ('dbthirdbar_r', 1.4),
                                               ('smr', 55.5),
                                               ('field_cap', 0.242),
                                               ('wilt_pt', 0.1145)])):
        weppSoils = {}
        invalidSoils = {}
        for mukey in self.mukeys:
            weppSoil = WeppSoil(self, mukey, initial_ksat, horizon_defaults=horizon_defaults)

            if weppSoil.valid():
                weppSoils[mukey] = weppSoil
            else:
                invalidSoils[mukey] = weppSoil

            if verbose:
                print('\n'.join(weppSoil.log))

        self.weppSoils = weppSoils
        self.invalidSoils = invalidSoils

    def getValidWeppSoils(self) -> List[int]:
        return list(self.weppSoils.keys())

    def getInValidWeppSoils(self) -> List[int]:
        return list(self.invalidSoils.keys())

    def writeWeppSoils(self, wd='./', overwrite=True,
                       write_logs=False, db_build=False,
                       version='7778') -> Dict[int, SoilSummary]:
        assert self.weppSoils is not None
        soils = {}
        for weppSoil in self.weppSoils.values():
            soil = weppSoil.write(wd, overwrite, db_build=db_build, version=version)
            soils[soil.mukey] = soil
            if write_logs:
                weppSoil.write_log(wd, overwrite, db_build=db_build)
        return soils

    def logInvalidSoils(self, wd='./', overwrite=True, db_build=False):
        assert self.invalidSoils is not None
        for weppSoil in self.invalidSoils.values():
            weppSoil.write_log(wd, overwrite, db_build=db_build)

    def _sync(self, table, fetch_func, keyname, keys, insert_null_data=True) -> int:
        conn, cur = self.conn, self.cur
        
        # identify what we have
        query = 'SELECT {keyname} FROM {table}'.format(keyname=keyname, table=table)
        acquired = [r[0] for r in cur.execute(query)]

        # identify what has previously been attempted and failed
        bad_tbl = 'bad_{table}_{keyname}'\
                  .format(table=table, keyname=keyname)
        query = 'SELECT {keyname} FROM {bad_tbl}'\
                .format(bad_tbl=bad_tbl, keyname=keyname)
        bad = set([r[0] for r in cur.execute(query)])

        # identify what needs to be acquired
        needed = set(keys).difference(acquired).difference(bad)

        # fetch from ssurgo if we needed isn't an empty set
        if len(needed) == 0:
            return 0

        data = fetch_func(needed)
        if len(data) == 0:
            return 0

        if not insert_null_data:
            data = [r for r in data if sum([v == '' for v in r]) == 0]

        # insert data from ssurgo into sqlite3 db
        nqs = '?,' * len(data[0])
        nqs = nqs[:-1]
        query = 'INSERT INTO {table} VALUES ({nqs})'\
                .format(table=table, nqs=nqs)
        try:
            cur.executemany(query, data)
        except sqlite3.IntegrityError:
            warnings.warn('Error syncing {} ({})'.format(keyname, keys))

        conn.commit()

        # set bad table in sqlite3 db
        just_acquired = [r[0] for r in data]
        bad.update(needed.difference(just_acquired))

        query = 'DROP TABLE IF EXISTS {bad_tbl}'\
                .format(bad_tbl=bad_tbl)
        cur.execute(query)

        query = 'CREATE TABLE {bad_tbl} ({keyname} INTEGER)'\
                .format(bad_tbl=bad_tbl, keyname=keyname)
        cur.execute(query)

        query = 'INSERT INTO {bad_tbl} VALUES (?)'\
                .format(bad_tbl=bad_tbl)
        cur.executemany(query, [[int(v)] for v in sorted(bad)])
        conn.commit()

        return len(needed)
        
    def _cache_tbl_exists(self, table_name):
        cur = self.cur
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" 
                    % table_name)
        return cur.fetchone() is not None
    
    def _initialize_cache_db(self):
        conn, cur = self.conn, self.cur
        
        if not self._cache_tbl_exists('component'):
            cur.execute('''CREATE TABLE component
                          (mukey INTEGER, cokey INTEGER UNIQUE, compname TEXT, 
                           comppct_r REAL, albedodry_r REAL, 
                           hydricrating REAL, drainagecl REAL, muname TEXT,
                           wtdepannmin TEXT, flodfreqdcd TEXT,
                           aws025wta TEXT, aws0150wta TEXT,
                           hydgrpdcd TEXT, drclassdcd TEXT,
                           taxclname TEXT, geomdesc TEXT,
                           taxorder TEXT, taxsuborder TEXT)''')
            cur.execute('''CREATE INDEX mukey_cokey ON component(mukey, cokey)''')

        if not self._cache_tbl_exists('chorizon'):
            cur.execute('''CREATE TABLE chorizon
                          (cokey INTEGER, chkey INTEGER UNIQUE, hzname TEXT,
                           hzdepb_r REAL, hzdept_r REAL, hzthk_r REAL, 
                           dbthirdbar_r REAL, ksat_r REAL, 
                           sandtotal_r REAL, claytotal_r REAL, om_r REAL, 
                           cec7_r REAL, awc_l REAL, fraggt10_r REAL, 
                           frag3to10_r REAL, desgnmaster TEXT, 
                           sieveno10_r REAL, wthirdbar_r REAL, 
                           wfifteenbar_r REAL, sandvf_r  REAL,
                           ll_r  REAL)''')
            cur.execute('''CREATE INDEX cokey_chkey ON chorizon(cokey, chkey)''')
                           
        if not self._cache_tbl_exists('chfrags'):
            cur.execute('''CREATE TABLE chfrags
                          (chkey INTEGER PRIMARY KEY , fragvol_r REAL)''')
        
        if not self._cache_tbl_exists('chtexturegrp'):
            cur.execute('''CREATE TABLE chtexturegrp
                          (chkey INTEGER PRIMARY KEY , texture TEXT)''')
                          
        if not self._cache_tbl_exists('corestrictions'):
            cur.execute('''CREATE TABLE corestrictions
                          (cokey INTEGER PRIMARY KEY , reskind TEXT)''')
                          
        if not self._cache_tbl_exists('bad_component_mukey'):
            cur.execute('''CREATE TABLE bad_component_mukey
                          (mukey INTEGER PRIMARY KEY )''')
                          
        if not self._cache_tbl_exists('bad_chorizon_cokey'):
            cur.execute('''CREATE TABLE bad_chorizon_cokey
                          (cokey INTEGER PRIMARY KEY )''')
                          
        if not self._cache_tbl_exists('bad_corestrictions_cokey'):
            cur.execute('''CREATE TABLE bad_corestrictions_cokey
                          (cokey INTEGER PRIMARY KEY )''')
                          
        if not self._cache_tbl_exists('bad_chfrags_chkey'):
            cur.execute('''CREATE TABLE bad_chfrags_chkey
                          (chkey INTEGER PRIMARY KEY )''')
                          
        if not self._cache_tbl_exists('bad_chtexturegrp_chkey'):
            cur.execute('''CREATE TABLE bad_chtexturegrp_chkey
                          (chkey INTEGER PRIMARY KEY )''')
                          
        conn.commit()
        
    def get_components(self, mukey):
        conn, cur = self.conn, self.cur
        
        query = 'SELECT * FROM component WHERE mukey={mukey} ORDER BY comppct_r DESC'\
                .format(mukey=mukey)
        cur = conn.execute(query)
        hdr = [desc[0] for desc in cur.description]
        return [dict(zip(hdr, r)) for r in cur.fetchall()]
                          
    def get_layers(self, cokey):
        conn, cur = self.conn, self.cur
        
        query = 'SELECT * FROM chorizon WHERE cokey={cokey} ORDER BY hzdepb_r'\
                .format(cokey=cokey)
        cur = conn.execute(query)
        hdr = [desc[0] for desc in cur.description]
        return [dict(zip(hdr, r)) for r in cur.fetchall()]
        
    def get_fragvol_r(self, chkey):
        conn, cur = self.conn, self.cur
        
        query = 'SELECT avg(fragvol_r) FROM chfrags WHERE chkey={chkey}'\
                .format(chkey=chkey)
        cur.execute(query)
        return cur.fetchone()[0]
        
    def get_texture(self, chkey):
        conn, cur = self.conn, self.cur
        
        query = 'SELECT texture FROM chtexturegrp WHERE chkey={chkey}'\
                .format(chkey=chkey)
        cur.execute(query)
        try:
            return cur.fetchall()[0][0]
        except IndexError:
            return 'N/A'
    
    def get_reskind(self, cokey):
        conn, cur = self.conn, self.cur
        
        query = 'SELECT reskind FROM corestrictions WHERE cokey={cokey}'\
                .format(cokey=cokey)
        cur.execute(query)
        res = cur.fetchall()
        
        if len(res) == 0:
            return 'N/A'
        else:
            return res[0][0]
            
if __name__ == "__main__":
    ssc = SurgoSoilCollection([2485028])
    ssc.makeWeppSoils()
    for mukey, soil in ssc.weppSoils.items():
        soil.write('tests')
