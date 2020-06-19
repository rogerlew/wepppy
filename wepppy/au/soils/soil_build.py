import json
import os
import hashlib
import math

from datetime import datetime
from os.path import join as _join
from os.path import exists as _exists

from wepppy.all_your_base import isfloat
from wepppy.soils.ssurgo import SoilSummary
from wepppy.wepp.soils.utils import simple_texture, soil_texture
from wepppy.wepp.soils.soilsdb import read_disturbed_wepp_soil_fire_pars
from wepppy.au.landuse_201011 import Lu10v5ua

from wepppy.au.soils.asris_2001.asris_client import query_asris
from wepppy.au.soils.asris_soil_grids import ASRISgrid

_disclaimer = """\
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
# """


_texture_defaults = {'clay loam': {'shcrit': 0.5, 'sand': 25.0, 'clay': 30.0, 'orgmat': 5.0, 'cec': 25.0, 'rfg': 15.0},
                     'silt loam': {'shcrit': 1.5, 'sand': 25.0, 'clay': 15.0, 'orgmat': 5.0, 'cec': 15.0, 'rfg': 15.0},
                     'loam': {'shcrit': 1.0, 'sand': 45.0, 'clay': 20.0, 'orgmat': 5.0, 'cec': 20.0, 'rfg': 20.0},
                     'sand loam': {'shcrit': 2.0, 'sand': 65.0, 'clay': 10.0, 'orgmat': 5.0, 'cec': 15.0, 'rfg': 25.0},
                     None: None}


def _computeErodibility(clay, sand, vfs, om):
    """
    Computes erodibility estimates according to:

    https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/usersum.pdf
    """

    # interrill, rill, shear
    if sand == 0.0 or vfs == 0.0 or om == 0.0 or clay == 0.0:
        return dict(interrill=0.0, rill=0.0, shear=0.0)

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
        rill = 0.00197 + 0.00030 * vfs + 0.03863 * math.exp(-1.84 * om)

        # apply equation 8 from usersum.pdf
        shear = 2.67 + 0.065 * clay - 0.058 * vfs
    else:
        if clay < 10.0:
            clay = 10.0

        # apply equation 9 from usersum.pdf
        interrill = 6054000.0 - 55130.0 * clay

        # apply equation 10 from usersum.pdf
        rill = 0.0069 + 0.134 * math.exp(-0.20 * clay)

        # apply equation 11 from usersum.pdf
        shear = 3.5

    return dict(interrill=interrill, rill=rill, shear=shear)


def build_asris_soils(orders, soil_dir):
    lu = Lu10v5ua()
    asris_grid = ASRISgrid()

    domsoil_d = {}
    soils = {}
    clay_d = {}
    sand_d = {}

    for topaz_id, (lng, lat) in orders:
        d = query_asris(lng, lat)

        key = hashlib.sha224(json.dumps(d, allow_nan=False).encode('utf-8')).hexdigest()

        s = ['2006.2',
             '#',
             '#            WEPPcloud (c) University of Idaho',
             '#',
             '#  Build Date: ' + str(datetime.now()),
             '#  Source Data: ASRIS 2001, ',
             '#               ASRIS National Soil Grid,',
             '#               AU Dept. of Ag. National scale land use data',
             '#', '#']

        s.extend(_disclaimer.split('\n'))

        s.append('#')
        s.append('#')
        s.append('# ASRIS 2001 Soil Parameters')
        s.append('#################################################')
        for name, row in d.items():
            s.append('# {name:36}{val:10}'.format(name=name.replace(' (value/1000)', ''), val=d[name]['Value']))

        s.append('#')
        s.append('# hash = %s' % key)

        grid_info = asris_grid.query(lng, lat)
        s.append('#')
        s.append('#')
        s.append('# ASRIS National Soil Grid Parameters')
        s.append('#################################################')
        for name, value in grid_info.items():
            s.append('# {name:36}{val:10}'.format(name=name, val=value))

        soil_type = grid_info['asc']

        dom = lu.query_dom(lng=lng, lat=lat)
        is_forest = dom.startswith('f')
        s.append('#')
        s.append('#')
        s.append(('# Land is NOT Forest', '# Land IS Forest')[is_forest] + ' (landuse DOM:%s)' % dom)

        s.append('#')
        s.append('#')
        s.append('Any comments:')
        s.append('1 1')

        # set albedo to 0.15 unless landcover is Forest, then 0.5
        salb = (0.15, 0.06)[is_forest]

        # set initial saturation to 0.75 unless landcover is Forest, then 0.5
        ini_sat = (0.75, 0.5)[is_forest]

        clay_top = d['Clay Content Topsoil %']['Value']
        silt_top = d['Silt Content Topsoil']['Value']
        sand_top = d['Sand Content Topsoil']['Value']
        om_top = d['Organic Carbon Topsoil %']['Value']
        tex_top = simple_texture(clay_top, sand_top)
        assert tex_top is not None, (clay_top, sand_top, isfloat(clay_top), isfloat(sand_top), soil_texture(clay_top, sand_top))

        thickness_top = d['Topsoil Thickness m']['Value'] * 1000
        ks_top = d['Saturated Hydraulic Topsoil mm/hr']['Value']
        cec_top = _texture_defaults[tex_top]['cec']
        rfg_top = _texture_defaults[tex_top]['rfg']

        clay_sub = d['Clay Content Subsoil %']['Value']
        silt_sub = d['Silt Content Subsoil']['Value']
        sand_sub = d['Sand Content Subsoil']['Value']
        om_sub = d['Organic Carbon Subsoil %']['Value']
        tex_sub = simple_texture(clay_sub, sand_sub)
        thickness_sub = d['Topsoil Thickness m']['Value'] * 1000
        ks_sub = d['Saturated Hydraulic Subsoil mm/hr']['Value']
        cec_sub = _texture_defaults[tex_sub]['cec']
        rfg_sub = _texture_defaults[tex_sub]['rfg']

        # set initial saturation to 0.75 unless landcover is Forest, then 0.5
        ini_sat = (0.75, 0.5)[is_forest]
        erod_d = _computeErodibility(clay=clay_top, sand=sand_top, vfs=silt_top, om=om_top)
        ki = erod_d['interrill']
        kr = erod_d['rill']
        shcrit = erod_d['shear']

        ofe_indx = len(s)
        s.append("'{slid}' \t'{texid}' \t{nsl} \t{salb} \t{sat} \t{ki} \t{kr} \t{shcrit} \t{avke}".format(
            slid=soil_type, texid=tex_top,
            nsl=1, salb=salb, sat=ini_sat, ki=ki, kr=kr, shcrit=shcrit, avke=ks_top))

        s.append('    {solthk} \t{sand} \t{clay} \t{orgmat} \t{cec} \t{rfg}'.format(
            solthk=thickness_top, sand=sand_top, clay=clay_top, orgmat= om_top, cec=cec_top, rfg=rfg_top
        ))

        tot_thickness = thickness_top + thickness_sub
        if tot_thickness < 210:
            tot_thickness = 210

        s.append('    {solthk} \t{sand} \t{clay} \t{orgmat} \t{cec} \t{rfg}'.format(
            solthk=tot_thickness, sand=sand_sub, clay=clay_sub, orgmat= om_sub, cec=cec_sub, rfg=rfg_sub
        ))

        s.append('1 \t25.0 \t0.00036')

        if key not in soils:
            fname = key + ".sol"
            fn = _join(soil_dir, fname)
            with open(fn, 'w') as fp:
                fp.write('\n'.join(s))

            soils[key] = SoilSummary(
                Mukey=key,
                FileName=fname,
                soils_dir=soil_dir,
                BuildDate=str(datetime.now),
                Description=soil_type)

            # create low severity soil file
            lowmod_key = '{}_lowmod_sev'.format(key)
            soil_pars = read_disturbed_wepp_soil_fire_pars(tex_top, 'low')
            s[ofe_indx] = "'{slid}' \t'{texid}' \t{nsl} \t{salb} \t{sat} \t{ki} \t{kr} \t{shcrit} \t{avke}".format(
                slid=soil_type, texid=tex_top, nsl=1, salb=soil_pars['salb'], sat=soil_pars['sat'],
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
                Description=soil_type)

            # create high severity soil file
            high_key = '{}_high_sev'.format(key)
            soil_pars = read_disturbed_wepp_soil_fire_pars(tex_top, 'high')
            s[ofe_indx] = "'{slid}' \t'{texid}' \t{nsl} \t{salb} \t{sat} \t{ki} \t{kr} \t{shcrit} \t{avke}".format(
                slid=soil_type, texid=tex_top, nsl=1, salb=soil_pars['salb'], sat=soil_pars['sat'],
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
                Description=soil_type)

        domsoil_d[topaz_id] = key
        clay_d[key] = clay_top
        clay_d[lowmod_key] = clay_top
        clay_d[high_key] = clay_top
        sand_d[key] = sand_top
        sand_d[lowmod_key] = sand_top
        sand_d[high_key] = sand_top

    return soils, domsoil_d, clay_d, sand_d


if __name__ == "__main__":
    orders = [(22, (146.27506256103518, -37.713973374315984))]
    build_asris_soils(orders, '')
