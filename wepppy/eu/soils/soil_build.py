import hashlib
import json
import string
from os.path import split as _split
from os.path import join as _join
from os.path import exists as _exists

from glob import glob
from datetime import datetime
from copy import deepcopy

from wepppy.soils.ssurgo import SoilSummary
from wepppy.all_your_base import RasterDatasetInterpolator

from wepppy.eu.soils.esdac import ESDAC, _attr_fmt
from wepppy.eu.soils.eusoilhydrogrids import SoilHydroGrids

from wepppy.wepp.soils.soilsdb import read_disturbed_wepp_soil_fire_pars

_texture_defaults = {'clay loam': {'shcrit': 0.5, 'sand': 25.0, 'clay': 30.0, 'orgmat': 5.0, 'cec': 25.0, 'rfg': 15.0},
                     'silt loam': {'shcrit': 1.5, 'sand': 25.0, 'clay': 15.0, 'orgmat': 5.0, 'cec': 15.0, 'rfg': 15.0},
                     'loam': {'shcrit': 1.0, 'sand': 45.0, 'clay': 20.0, 'orgmat': 5.0, 'cec': 20.0, 'rfg': 20.0},
                     'sand loam': {'shcrit': 2.0, 'sand': 65.0, 'clay': 10.0, 'orgmat': 5.0, 'cec': 15.0, 'rfg': 25.0},
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


def build_esdac_soils(orders, soil_dir):
    '''
    0   No information  -->  None
    9   No mineral texture (Peat soils)  --> ?
    1   Coarse (18% < clay and > 65% sand)  -->  sand loam
    2   Medium (18% < clay < 35% and >= 15% sand,
        or 18% < clay and 15% < sand < 65%)  -->  loam
    3   Medium fine (< 35% clay and < 15% sand)  -->  silt loam
    4   Fine (35% < clay < 60%)  -->  clay loam
    5   Very fine (clay > 60 %)  -->  clay loam
    '''
    esd = ESDAC()
    vars = ['txsrfdo', 'txsubdo', 'txdepchg',
            'fao90lv1', 'cec_top', 'cec_sub', 'il',
            'oc_top', 'vs', 'bs_top', 'bs_sub',
            'usedo', 'erodi', 'il']

    soils = {}
    domsoil_d = {}
    clay_d = {}
    sand_d = {}

    for topaz_id, (lng, lat) in orders:
        res = esd.query(lng, lat, vars)
        _vars = [_attr_fmt(v) for v in vars]

        key = '_'.join(['{}'.format(res[v][1]) for v in _vars])
        desc = ', '.join(['{}:{}'.format(v, res[v][1]) for v in _vars])

        s = ['2006.2',
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

        for v in _vars:
            s.append('#  {:20}{:6}{:6}{}'.format(v, res[v][0], res[v][1], res[v][2]))

        s.append('#')

        textsrfdom_short = res['textsrfdom'][1]
        srf_simple_texture = _tex_short_to_simple_texture[textsrfdom_short]
        srf_defaults = _texture_defaults[srf_simple_texture]

        textsubdom_short = res['textsubdom'][1]
        sub_simple_texture = _tex_short_to_simple_texture[textsubdom_short]
        sub_defaults = _texture_defaults[sub_simple_texture]

        s.append('# Surface Texture')
        s.append('# simple_texture: {}'.format(srf_simple_texture))
        s.append('# defaults {}'.format(srf_defaults))
        s.append('#')

        s.append('# Subsurface Texture')
        s.append('# simple_texture: {}'.format(sub_simple_texture))
        s.append('# defaults {}'.format(sub_defaults))
        s.append('#')

        soil_hydro = SoilHydroGrids()
        ks = soil_hydro.query(lng, lat, 'KS')
        s.append('#')
        s.append('# EU Soil Hydro Grids')
        s.append('# Code\tDepth\tksat')
        for code, (_depth, _ks) in ks.items():
            s.append('# {}  \t{}  \t{}'.format(code, _depth, _ks * 0.004166667))

        s.append('#')

        fao90lev1 = res['fao90lev1'][2]
        usedom = res['usedom'][1]

        is_forest = usedom in ['5', '22']

        s.append(('# Land is NOT Forest', '# Land IS Forest')[is_forest])
        s.append('#')

        s.append('Any comments:')
        s.append('1 1')

        # set albedo to 0.15 unless landcover is Forest, then 0.5
        salb = (0.15, 0.06)[is_forest]

        # set initial saturation to 0.75 unless landcover is Forest, then 0.5
        ini_sat = (0.75, 0.5)[is_forest]

        if srf_simple_texture == 'clay loam':
            if is_forest:
                ki = 400000.0
            else:
                ki = 1500000.0
        elif srf_simple_texture == 'loam':
            if is_forest:
                ki = 400000.0
            else:
                ki = 1000000.0
        elif srf_simple_texture == 'sand loam':
            ki = 400000.0
        elif srf_simple_texture == 'silt loam':
            ki = 1000000.0
        else:
            ki = None

        erodibility = res['erodibility'][1]
        kr = 0.00002 * float(erodibility)

        avke = ks['sl1'][1] * 0.004166667

        ofe_indx = len(s)
        s.append("'{slid}' \t'{texid}' \t{nsl} \t{salb} \t{sat} \t{ki} \t{kr} \t{shcrit} \t{avke}".format(
            slid=fao90lev1, texid=srf_simple_texture,
            nsl=1, salb=salb, sat=ini_sat, ki=ki, kr=kr, shcrit=srf_defaults['shcrit'], avke=avke))

        horizon0 = deepcopy(srf_defaults)
        horizon1 = deepcopy(sub_defaults)
        assert horizon0 is not None

        texdepchg_short = res['textdepchg'][1]
        solthk = _texdepchg_short_to_depth_mm[texdepchg_short]
        if solthk is None:
            if horizon1 is None:
                solthk = 200
            else:
                solthk = 400
        horizon0['solthk'] = solthk

        cectop = res['cectop'][1]
        if cectop == 'H':
            horizon0['cec'] = 45.0
        elif cectop == 'L':
            horizon0['cec'] = 10.0

        octop_short = res['octop'][1]
        horizon0['orgmat'] = _octop_short_to_pct[octop_short]

        s.append('    {solthk} \t{sand} \t{clay} \t{orgmat} \t{cec} \t{rfg}'.format(**horizon0))

        if horizon1 is not None:
            il = res['il'][1]
            solthk = _il_short_to_depth_mm[il]
            if solthk is None:
                solthk = 400
            horizon1['solthk'] = solthk

            cecsub = res['cecsub'][1]
            if cecsub == 'H':
                horizon1['cec'] = 45.0
            elif cecsub == 'L':
                horizon1['cec'] = 10.0

            s.append('    {solthk} \t{sand} \t{clay} \t{orgmat} \t{cec} \t{rfg}'.format(**horizon1))

        s.append('1 \t25.0 \t0.00036')

        if key not in soils:

            fname = key + '.sol'
            fn = _join(soil_dir, fname)
            with open(fn, 'w') as fp:
                fp.write('\n'.join(s))

            soils[key] = SoilSummary(
                Mukey=key,
                FileName=fname,
                soils_dir=soil_dir,
                BuildDate=str(datetime.now),
                Description=desc)

            # create low severity soil file
            lowmod_key = '{}_lowmod_sev'.format(key)
            soil_pars = read_disturbed_wepp_soil_fire_pars(srf_simple_texture, 'low')
            s[ofe_indx] = "'{slid}' \t'{texid}' \t{nsl} \t{salb} \t{sat} \t{ki} \t{kr} \t{shcrit} \t{avke}".format(
                slid=fao90lev1, texid=srf_simple_texture, nsl=1, salb=soil_pars['salb'], sat=soil_pars['sat'],
                ki=soil_pars['ki'], kr=soil_pars['kr'], shcrit=soil_pars['shcrit'], avke=soil_pars['avke'])

            fname = lowmod_key + '.sol'
            fn = _join(soil_dir, fname)
            with open(fn, 'w') as fp:
                fp.write('\n'.join(s))

            soils[lowmod_key] = SoilSummary(
                Mukey=lowmod_key,
                FileName=fname,
                soils_dir=soil_dir,
                BuildDate=str(datetime.now),
                Description=desc)

            # create high severity soil file
            high_key = '{}_high_sev'.format(key)
            soil_pars = read_disturbed_wepp_soil_fire_pars(srf_simple_texture, 'high')
            s[ofe_indx] = "'{slid}' \t'{texid}' \t{nsl} \t{salb} \t{sat} \t{ki} \t{kr} \t{shcrit} \t{avke}".format(
                slid=fao90lev1, texid=srf_simple_texture, nsl=1, salb=soil_pars['salb'], sat=soil_pars['sat'],
                ki=soil_pars['ki'], kr=soil_pars['kr'], shcrit=soil_pars['shcrit'], avke=soil_pars['avke'])

            fname = high_key + '.sol'
            fn = _join(soil_dir, fname)
            with open(fn, 'w') as fp:
                fp.write('\n'.join(s))

            soils[high_key] = SoilSummary(
                Mukey=high_key,
                FileName=fname,
                soils_dir=soil_dir,
                BuildDate=str(datetime.now),
                Description=desc)

        domsoil_d[topaz_id] = key
        clay_d[key] = horizon0['clay']
        clay_d[lowmod_key] = horizon0['clay']
        clay_d[high_key] = horizon0['clay']
        sand_d[key] = horizon0['sand']
        sand_d[lowmod_key] = horizon0['sand']
        sand_d[high_key] = horizon0['sand']

    return soils, domsoil_d, clay_d, sand_d
