import oyaml as yaml
import shlex

from copy import deepcopy
from datetime import datetime

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


from wepppy.all_your_base import try_parse, isfloat


def _replace_parameter(original, replacement):
    replacement = str(replacement)
    if replacement is None or replacement.lower().replace('none', '').strip() == '':
        return original

    try:
        if replacement.strip().startswith('*'):
            return str(float(original) * float(replacement.replace('*', '')))
    except AttributeError:
        pass

    else:
        return replacement


def _pars_to_string(d):
    kv_pairs = []
    for k, v in d.items():
        if isinstance(v, str):
            kv_pairs.append(f"{k}='{v}'")
        else:
            kv_pairs.append(f"{k}={v}")
    return f"({', '.join(kv_pairs)})"


class WeppSoilUtil(object):
    def __init__(self, fn, compute_erodibilities=False, compute_conductivity=False):
        self.compute_erodibilities = compute_erodibilities
        self.compute_conductivity = compute_conductivity

        if fn.endswith('.sol'):
            try:
                self._parse_sol(fn)
            except:
                raise Exception(f"Error opening {fn}")
        elif fn.endswith('.yaml'):
            self._load_yaml(fn)
        elif fn.endswith('.bson'):
            self._load_bson(fn)

        self.fn = fn

    def _parse_sol(self, fn):
        with open(fn) as fp:
            lines = fp.readlines()

        header = [L.replace('#', '').strip() for L in lines if L.startswith('#')]
#        header = [L for L in header if L != '']
        lines = [L.strip() for L in lines if not L.startswith('#')]
        lines = [L for L in lines if L != '']
        i = 0

        datver = lines[i]  # data version
        i += 1

        datver = float(datver)
        if datver < 100:
            solwpv = int(datver * 10)
        else:
            solwpv = int(datver)

        if datver > 90.0:
            if datver >= 95.3:
                solcom = lines[i]  # user comment line
                i += 1

            if datver > 93.621:
                line2 = lines[i].split()
                ntemp = int(line2[0])   # number of ofes
                ksflag = int(line2[1])  # use internal hydraulic conductivity adjustments
                i += 1
            else:
                ntemp = int(lines[i])
                ksflag = 1
                i += 1
        else:
            ntemp = int(lines[i])
            ksflag = 1
            i += 1
            
        ofes = []
        for ofe_counter in range(ntemp):
            line = shlex.split(lines[i])
            i += 1

            ksatadj = 0
            luse = None  # Disturbed Class
            stext = None
            lkeff = None
            uksat = None
            texid_enum = None
            ksatfac = None
            ksatrec = None

            if solwpv > 9000 and solwpv < 9003:
                # 1      2     3      4        5
                ksatadj, luse, stext, ksatfac, ksatrec = line
                line = shlex.split(lines[i])
                i += 1
            elif solwpv == 9003:
                ksatadj, luse, burn_code, stext, lkeff = line
                line = shlex.split(lines[i])
                i += 1

            elif solwpv == 9005:
                ksatadj, luse, burn_code, stext, texid_enum, uksat, lkeff = line
                line = shlex.split(lines[i])
                i += 1

            if solwpv < 941 or solwpv >= 7777 or datver == 2006.2:
                # 1   2      3    4     5    6   7   8
                slid, texid, nsl, salb, sat, ki, kr, shcrit = line[:8]
                avke = None
            else:
                # 1   2      3    4     5    6   7   8       9
                slid, texid, nsl, salb, sat, ki, kr, shcrit, avke = line

            nsl = int(nsl)

            horizons = []
            for j in range(nsl):
                line = lines[i].split()
                i += 1

                if solwpv < 941 or solwpv == 7777:
                    # 1     2   3     4   5   6     7     8       9    10
                    solthk, bd, ksat, fc, wp, sand, clay, orgmat, cec, rfg = line
                    anisotropy = None
                elif solwpv >= 7778:
                    # 1     2   3     4           5   6   7     8     9       10   11
                    solthk, bd, ksat, anisotropy, fc, wp, sand, clay, orgmat, cec, rfg = line[:11]
                else:
                    solthk, sand, clay, orgmat, cec, rfg = line
                    bd = ksat = fc = wp = anisotropy = None

                if float(clay) + float(sand) > 100.0:
                    sand = str(100.0 - float(clay))

                if j == 0:
                    if self.compute_erodibilities:
                        from wepppy.wepp.soils.horizon_mixin import compute_erodibilities
                        vfs = 100.0 - float(clay) - float(sand)
                        res = compute_erodibilities(clay=float(clay), sand=float(sand), vfs=vfs, om=float(orgmat))

                        ki = round(res['interrill'])
                        kr = round(res['rill'], 5)
                        shcrit = round(res['shear'], 1)

                        header.append(f'ofe={ofe_counter},horizon={j} calculated ki, kr, and shcrit from clay, sand, vfs, and om')

                if self.compute_conductivity:
                    from wepppy.wepp.soils.horizon_mixin import compute_conductivity
                    ksat = compute_conductivity(clay=float(clay), sand=float(sand), cec=float(cec))

                    if ksat is not None:
                        ksat = round(ksat, 4)

                        header.append(f'ofe={ofe_counter},horizon={j} calculated ksat from clay, sand, and cec')
             
                horizons.append(
                    dict(solthk=try_parse(solthk),
                         bd=try_parse(bd),
                         ksat=try_parse(ksat), 
                         anisotropy=try_parse(anisotropy),
                         fc=try_parse(fc),
                         wp=try_parse(wp),
                         sand=try_parse(sand), 
                         clay=try_parse(clay),
                         orgmat=try_parse(orgmat), 
                         cec=try_parse(cec), 
                         rfg=try_parse(rfg)))

            res_lyr = None
            if solwpv >= 2006:
                try:
                    res_lyr = lines[i].split()
                    i += 1

                    if len(res_lyr) == 4:
                        res_lyr = [res_lyr[0], res_lyr[2], res_lyr[3]]
                    if len(res_lyr) != 3:
                        raise
                except:
                    res_lyr = None


            if res_lyr is not None:
                if solwpv >= 2006 and solwpv < 7778:
                    res_lyr = dict(slflag=int(res_lyr[0]),
                                   anisrt=float(res_lyr[1]),
                                   kslast=float(res_lyr[2]))
                elif solwpv >= 7778:
                    res_lyr = dict(slflag=int(res_lyr[0]),
                                   ui_bdrkth=float(res_lyr[1]),
                                   kslast=float(res_lyr[2]))
                else:
                    raise NotImplementedError(solwpv)

            if isfloat(sat):
                sat = float(sat)
            else:
                sat = 0.75

            ofes.append(
                dict(slid=slid.replace("'", '').replace('"', ''),
                     texid=texid.replace("'", '').replace('"', ''),
                     nsl=try_parse(nsl),
                     salb=try_parse(salb),
                     sat=sat,
                     ki=try_parse(ki),
                     kr=try_parse(kr),
                     shcrit=try_parse(shcrit),
                     avke=try_parse(avke),
                     horizons=horizons,
                     ksatadj=ksatadj,
                     luse=luse,
                     stext=stext,
                     uksat=uksat,
                     texid_enum=texid_enum,
                     lkeff=lkeff,
                     ksatfac=ksatfac,
                     ksatrec=ksatrec,
                     res_lyr=res_lyr))

        soil = dict(header=header,
                    datver=datver,
                    solcom=solcom,
                    ntemp=ntemp,
                    ksflag=ksflag,
                    ofes=ofes,
                    res_lyr=res_lyr)

        self.obj = soil

    def modify_initial_sat(self, initial_sat):
        self.obj['header'].append('wepppy.wepp.soils.utils.WeppSoilUtil::modify_initial_sat')
        self.obj['header'][-1] += f'(initial_sat={initial_sat})'

        for i in range(len(self.obj['ofes'])):
            self.obj['ofes'][i]['sat'] = initial_sat

    def modify_kslast(self, kslast, pars=None):
        luse = self.obj['ofes'][0]['luse']

        if luse is not None:
            if 'developed' in luse.lower():
                return

        self.obj['header'].append('wepppy.wepp.soils.utils.WeppSoilUtil::modify_kslast')

        if pars is not None:
            self.obj['header'][-1] += _pars_to_string(pars)
        else:
            self.obj['header'][-1] += f'(kslast={kslast})'

        for i in range(len(self.obj['ofes'])):
            self.obj['ofes'][i]['res_lyr']['kslast'] = kslast

        self.obj['res_lyr']['kslast'] = kslast

    def clip_soil_depth(self, max_depth):

        self.obj['header'].append(f'wepppy.wepp.soils.utils.WeppSoilUtil::clip_soil_depth(max_depth={max_depth})')

        for i in range(len(self.obj['ofes'])):
            ofe = self.obj['ofes'][i]

            horizons = []
            for j in range(len(ofe['horizons'])):
                horizon = ofe['horizons'][j]
                if horizon['solthk'] <= max_depth:
                    horizons.append(horizon)
                else:
                    horizon['solthk'] = max_depth
                    horizons.append(horizon)
                    depth = max_depth
                    break
            self.obj['ofes'][i]['horizons'] = horizons
            self.obj['ofes'][i]['nsl'] = len(horizons)

    def to7778(self, hostname=''):
        from rosetta import Rosetta2, Rosetta3

        r2 = Rosetta2()
        r3 = Rosetta3()
        new = deepcopy(self)
        if new.obj['datver'] == 7778.0:
            return new

        header = new.obj['header']
        header.append('')
        header.append('wepppy.wepp.soils.utils.WeppSoilUtil::7778migration')
        header.append('  Build Date: ' + str(datetime.now()))
        header.append(f'  Source File: {hostname}:{self.fn}' )
        header.append('')

        for i, ofe in enumerate(new.obj['ofes']):
            horizons = []
            kslast = 0.0
            for j, horizon in enumerate(ofe['horizons']):
                clay, sand, bd = horizon['clay'], horizon['sand'], horizon['bd']
                silt = 100 - clay - sand
                if not isfloat(bd):
                    ros_model = f'Rosetta(clay={clay}, sand={sand}, silt={silt})'
                    res_dict = r2.predict_kwargs(clay=float(clay), sand=float(sand), silt=float(silt))
                else:
                    ros_model = f'Rosetta(clay={clay}, sand={sand}, bd={bd}, silt={silt})'
                    res_dict = r3.predict_kwargs(bd=float(bd), clay=float(clay), sand=float(sand), silt=float(silt))

                if not isfloat(horizon['bd']):
                    horizon['bd'] = 1.4
                    header.append(f'ofe={i},horizon={j} bd default value of 1.4')

                if not isfloat(horizon['fc']):
                    horizon['fc'] = round(res_dict['fc'], 4)
                    header.append(f'ofe={i},horizon={j} fc estimated using {ros_model}')

                if not isfloat(horizon['wp']):
                    horizon['wp'] = round(res_dict['wp'], 4)
                    header.append(f'ofe={i},horizon={j} wp estimated using {ros_model}')

                if not isfloat(horizon['ksat']):
                    horizon['ksat'] = round(res_dict['ks'] * 10 / 24, 4)  # convert from cm/day to mm/hour
                    header.append(f'ofe={i},horizon={j} ksat estimated using {ros_model}')

                if not isfloat(horizon['anisotropy']):
                    if horizon['solthk'] > 50:
                        horizon['anisotropy'] = 1.0
                    else:
                        horizon['anisotropy'] = 10.0
                    header.append(f'ofe={i},horizon={j} anisotropy estimated using {ros_model}')

                kslast = horizon['ksat']
                horizons.append(horizon)

            new.obj['ofes'][i]['horizons'] = horizons

            res_lyr = ofe['res_lyr']
            if res_lyr is None:
                res_lyr = dict(slflag=1,
                               ui_bdrkth=10000.0,
                               kslast=kslast)
            else:
                slflag = res_lyr['slflag']
                kslast = res_lyr['kslast']
                if slflag:
                    res_lyr = dict(slflag=1,
                                   ui_bdrkth=10000.0,
                                   kslast=kslast)
                else:
                    res_lyr = dict(slflag=0,
                                   ui_bdrkth=0.0,
                                   kslast=kslast)
            new.obj['ofes'][i]['res_lyr'] = res_lyr

        new.obj['datver'] = 7778.0
        return new

    def __str__(self):
        from rosetta import Rosetta3
        r3 = Rosetta3()

        header = self.obj['header'] 
        header = [f'# {L}' for L in header]

        datver = self.obj['datver'] 
        solcom = self.obj['solcom'] 
        ntemp = self.obj['ntemp']
        ksflag = self.obj['ksflag']
        ofes = self.obj['ofes']

        assert datver in (7778.0, 9001.0, 9002.0, 9003.0, 9005.0), datver

        s = [str(int(datver))] 
        s += header
        s.append(solcom)
        s.append(f'{ntemp} {ksflag}')

        for i in range(ntemp):
            ofe = ofes[i]

            _luse = None
            # build its over 9000 header
            if datver > 9000:
                _luse = ofe['luse']
                if _luse is None:
                    _luse = ()

                _burn_code = 0
                if 'agriculture' in _luse:
                    _burn_code = 100
                elif 'shrub' in _luse:
                    _burn_code = 200
                elif 'forest' in _luse:
                    _burn_code = 300
                    if 'young' in _luse:
                        _burn_code += 6
                elif 'grass' in _luse:
                    _burn_code = 400

                if 'low sev' in _luse:
                    _burn_code += 1
                elif 'moderate sev' in _luse:
                    _burn_code += 2
                elif 'high sev' in _luse:
                    _burn_code += 3


            if not _luse:
                _luse = "N/A"

            if datver > 9000.0 and datver < 9003.0:
                _ksatadj = ofe['ksatadj']
                _ksatfac = ofe['ksatfac']
                _ksatrec = ofe['ksatrec']
                _stext = ofe['stext']
                s.append(f"{_ksatadj}\t '{_luse}'\t '{_stext}'\t {_ksatfac} \t {_ksatrec}")

            elif datver == 9003.0:
                _ksatadj = ofe['ksatadj']
                _stext = ofe['stext']
                _lkeff = ofe['lkeff']
                s.append(f"{_ksatadj}\t '{_luse}'\t {_burn_code}\t '{_stext}'\t {_lkeff}")

            elif datver == 9005.0:
                _ksatadj = ofe['ksatadj']
                _stext = ofe['stext']
                _lkeff = ofe['lkeff']
                _uksat = ofe['uksat']
                _texid_enum = self.simple_texture_enum
                s.append(f"{_ksatadj}\t '{_luse}'\t {_burn_code}\t '{_stext}'\t {_texid_enum}\t {_uksat}\t {_lkeff}")

            L = "'{0}'\t '{1}'".format(ofe['slid'], ofe['texid'])
            pars = 'nsl salb sat ki kr shcrit'.split()
            L2 = ('\t '.join([str(ofe[p]) for p in pars]))
            s.append(f'{L}\t {L2}')

            for j, horizon in enumerate(ofe['horizons']):
                pars = 'solthk bd ksat anisotropy fc wp sand clay orgmat cec rfg'.split()
                s.append('\t' + '\t '.join([str(horizon[p]) for p in pars]))

                if datver >= 9002.0:
                    clay = horizon['clay']
                    sand = horizon['sand']
                    silt = 100.0 - clay - sand
                    bd = horizon['bd']
                    res = r3.predict_kwargs(clay=clay, sand=sand, silt=silt, bd=bd)
                    vg_pars = 'theta_r theta_s alpha npar ks wp fc'.split()
                    s[-1] += '\t ' + '\t '.join([f'{res[p]:.4}' for p in vg_pars])

            res_lyr = ofe['res_lyr']
            if res_lyr is not None:
                s.append(f'{res_lyr["slflag"]} {res_lyr["ui_bdrkth"]} {res_lyr["kslast"]}')
            else:
                s.append('0 0.0 0.0')

        return '\n'.join(s) + '\n'
        

    def __repr__(self):
        from rosetta import Rosetta3
        r3 = Rosetta3()

        header = self.obj['header'] 
        header = [f'# {L}' for L in header]

        datver = self.obj['datver'] 
        solcom = self.obj['solcom'] 
        ntemp = self.obj['ntemp']
        ksflag = self.obj['ksflag']
        ofes = self.obj['ofes']

        assert datver in (7778.0, 9001.0, 9002.0, 9003.0, 9005.0), datver

        s = [f'datver:{int(datver)}'] 
        s += header
        s.append(f'solcom:{solcom}')
        s.append(f'ntemp:{ntemp} ksflag:{ksflag}')

        s.append('<OFEs>')
        for i in range(ntemp):
            ofe = ofes[i]

            _luse = None
            # build its over 9000 header
            if datver > 9000:
                _luse = ofe['luse']
                if _luse is None:
                    _luse = ()

                _burn_code = 0
                if 'agriculture' in _luse:
                    _burn_code = 100
                elif 'shrub' in _luse:
                    _burn_code = 200
                elif 'forest' in _luse:
                    _burn_code = 300
                    if 'young' in _luse:
                        _burn_code += 6
                elif 'grass' in _luse:
                    _burn_code = 400

                if 'low sev' in _luse:
                    _burn_code += 1
                elif 'moderate sev' in _luse:
                    _burn_code += 2
                elif 'high sev' in _luse:
                    _burn_code += 3


            if not _luse:
                _luse = "N/A"

            if datver > 9000.0 and datver < 9003.0:
                _ksatadj = ofe['ksatadj']
                _ksatfac = ofe['ksatfac']
                _ksatrec = ofe['ksatrec']
                _stext = ofe['stext']
                s.append(f"ksatadj:{_ksatadj}\t luse:'{_luse}'\t stext:'{_stext}'\t ksatfac:{_ksatfac} \t ksatrec:{_ksatrec}")

            elif datver == 9003.0:
                _ksatadj = ofe['ksatadj']
                _stext = ofe['stext']
                _lkeff = ofe['lkeff']
                s.append(f"ksatadj:{_ksatadj}\t luse:'{_luse}'\t burn_code:{_burn_code}\t stext:'{_stext}'\t lkeff:{_lkeff}")

            elif datver == 9005.0:
                _ksatadj = ofe['ksatadj']
                _stext = ofe['stext']
                _lkeff = ofe['lkeff']
                _uksat = ofe['uksat']
                _texid_enum = self.simple_texture_enum
                s.append(f"ksatadj:{_ksatadj}\t luse:'{_luse}'\t burn_code:{_burn_code}\t stext:'{_stext}'\t texid_enum:{_texid_enum}\t uksat:{_uksat}\t lkeff:{_lkeff}")

            L = "'{0}'\t '{1}'".format(ofe['slid'], ofe['texid'])
            pars = 'nsl salb sat ki kr shcrit'.split()
            L2 = ('\t '.join([f'{p}:{ofe[p]}' for p in pars]))
            s.append(f'{L}\t {L2}')

            s.append('\t<Horizons>')
            for j, horizon in enumerate(ofe['horizons']):
                pars = 'solthk bd ksat anisotropy fc wp sand clay orgmat cec rfg'.split()
                s.append('\t' + '\t '.join([ f'{p}:{horizon[p]}' for p in pars]))

                if datver >= 9002.0:
                    clay = horizon['clay']
                    sand = horizon['sand']
                    silt = 100.0 - clay - sand
                    bd = horizon['bd']
                    res = r3.predict_kwargs(clay=clay, sand=sand, silt=silt, bd=bd)
                    vg_pars = 'theta_r theta_s alpha npar ks wp fc'.split()
                    s[-1] += '\t ' + '\t '.join([f'{p}:{res[p]:.4}' for p in vg_pars])

            s.append('\t</Horizons>')
            s.append('<Restrictive Layer>')
            res_lyr = ofe['res_lyr']
            if res_lyr is not None:
                s.append(f'slflag:{res_lyr["slflag"]} ui_bdrkth:{res_lyr["ui_bdrkth"]} kslast:{res_lyr["kslast"]}')
            else:
                s.append('0 0.0 0.0')
            s.append('</Restrictive Layer>')
        s.append('</OFEs>')
        return '\n'.join(s) + '\n'
    
    def write(self, fn):
        s = self.__str__()

        with open(fn, 'w') as fp:
            fp.write(s)

    def to_7778disturbed(self, replacements, h0_min_depth=None, h0_max_om=None, hostname=''):
        if replacements is None:
            replacements = {}

        new = deepcopy(self)
        if new.obj['datver'] != 7778.0:
            new = self.to7778()

        if 'ksflag' in replacements:
            del replacements['ksflag']

        if 'ksatadj' in replacements:
            del replacements['ksatadj']

        if 'ksatfac' in replacements:
            del replacements['ksatfac']

        if 'ksatrec' in replacements:
            del replacements['ksatrec']

        header = new.obj['header']
        header.append('')
        header.append('wepppy.wepp.soils.utils.WeppSoilUtil::7778disturbed_migration')
        header.append('  Build Date: ' + str(datetime.now()))
        header.append(f'  Source File: {hostname}:{self.fn}' )
        header.append('')
        header.append('  Replacements')
        header.append('  --------------------------')
        for k, v in replacements.items():
            header.append(f'  {k} -> {v}')
        header.append('')
        header.append(f'  h0_min_depth = {h0_min_depth}')
        header.append(f'  h0_max_om = {h0_max_om}')
        header.append('')

        _ki = replacements.get('ki', None)
        _kr = replacements.get('kr', None)
        _ksat = replacements.get('avke', None)
        if _ksat is None:
            _ksat = replacements.get('ksat', None)
        _shcrit = replacements.get('shcrit', None)
        _kslast = replacements.get('kslast', None)
        _luse = replacements.get('luse', None)
        _stext = replacements.get('stext', None)

        ofes = []
        for i, ofe in enumerate(new.obj['ofes']):
            ofe['ki'] = _replace_parameter(ofe['ki'], _ki)
            ofe['kr'] = _replace_parameter(ofe['kr'], _kr)
            ofe['shcrit'] = _replace_parameter(ofe['shcrit'], _shcrit)
            ofe['luse'] = _replace_parameter(ofe['luse'], _luse)
            ofe['stext'] = _replace_parameter(ofe['stext'], _stext)

            horizons = []
            cur_depth = 0.0
            for j, horizon in enumerate(ofe['horizons']):
                solthk = horizon['solthk']
                if j == 0 and h0_min_depth is not None:
                    solthk = horizon['solthk'] = _replace_parameter(solthk, max(solthk, h0_min_depth))

                solthk = float(solthk)
                if solthk <= 200:
                    horizon['ksat'] = _replace_parameter(horizon['ksat'], _ksat)
                elif solthk > 200 and cur_depth < 200:
                    new_horizon = deepcopy(horizon)
                    new_horizon['solthk'] = 200.0
                    new_horizon['ksat'] = _replace_parameter(new_horizon['ksat'], _ksat)
                    horizons.append(new_horizon)

                if j == 0 and h0_max_om is not None:
                    if horizon['om'] < h0_max_om:
                        horizons.append(horizon)
                else:
                    horizons.append(horizon)

                cur_depth = solthk

            ofe['horizons'] = horizons
            ofe['nsl'] = len(horizons)

            ofe['res_lyr']['kslast'] = _replace_parameter(ofe['res_lyr']['kslast'], _kslast)
            ofes.append(ofe)

        new.obj['ofes'] = ofes

        return new

    def to9001(self, replacements, h0_min_depth=None, h0_max_om=None, hostname=''):
        return self.to_over9000(replacements, 
                                h0_min_depth=h0_min_depth, 
                                h0_max_om=h0_max_om, hostname=hostname,
                                version=9001)

    def to9002(self, replacements, h0_min_depth=None, h0_max_om=None, hostname=''):
        return self.to_over9000(replacements, 
                                h0_min_depth=h0_min_depth, 
                                h0_max_om=h0_max_om, hostname=hostname, 
                                version=9002)

    def to9003(self, replacements, h0_min_depth=None, h0_max_om=None, hostname=''):
        return self.to_over9000(replacements, 
                                h0_min_depth=h0_min_depth, 
                                h0_max_om=h0_max_om, hostname=hostname, 
                                version=9003)

    def to9005(self, replacements, h0_min_depth=None, h0_max_om=None, hostname=''):
        return self.to_over9000(replacements,
                                h0_min_depth=h0_min_depth,
                                h0_max_om=h0_max_om, hostname=hostname,
                                version=9005)

    def to_over9000(self, replacements, h0_min_depth=None, h0_max_om=None, hostname='', version=9002):
        if replacements is None:
            replacements = {}

        new = deepcopy(self)
        if new.obj['datver'] != 7778.0:
            new = self.to7778()

        header = new.obj['header']
        header.append('')
        header.append(f'wepppy.wepp.soils.utils.WeppSoilUtil::{version}migration')
        header.append('  Build Date: ' + str(datetime.now()))
        header.append(f'  Source File: {hostname}:{self.fn}' )
        header.append('')
        header.append('  Replacements')
        header.append('  --------------------------')
        for k, v in replacements.items():
            header.append(f'  {k} -> {v}')
        header.append('')
        header.append(f'  h0_min_depth = {h0_min_depth}')
        header.append(f'  h0_max_om = {h0_max_om}')
        header.append('')

        _ki = replacements.get('ki', None)
        _kr = replacements.get('kr', None)
        _ksat = replacements.get('avke', None)
        if not _ksat:
            _ksat = replacements.get('ksat', None)
        _shcrit = replacements.get('shcrit', None)
        _ksflag = replacements.get('ksflag', None)
        _ksatadj = replacements.get('ksatadj', None)
        _ksatfac = replacements.get('ksatfac', None)
        _ksatrec = replacements.get('ksatrec', None)
        _kslast = replacements.get('kslast', None)
        _luse = replacements.get('luse', None)
        _stext = replacements.get('stext', None)
        _lkeff = replacements.get('lkeff', '')
        _uksat = replacements.get('uksat', '')

        if _lkeff == '':
            _lkeff = '-9999'

        if _uksat == '':
            _uksat = '-9999'

        new.obj['ksflag'] = _replace_parameter(new.obj['ksflag'], _ksflag)

        ofes = []
        for i, ofe in enumerate(new.obj['ofes']):
            ofe['ki'] = _replace_parameter(ofe['ki'], _ki)
            ofe['kr'] = _replace_parameter(ofe['kr'], _kr)
            ofe['shcrit'] = _replace_parameter(ofe['shcrit'], _shcrit)

            ofe['ksatadj'] = _replace_parameter(ofe['ksatadj'], _ksatadj)

            if version < 9003:
                ofe['ksatfac'] = _replace_parameter(ofe['ksatfac'], _ksatfac)
                ofe['ksatrec'] = _replace_parameter(ofe['ksatrec'], _ksatrec)
            elif version == 9003:
                ofe['lkeff'] = _replace_parameter(ofe['lkeff'], _lkeff)
            elif version == 9005:
                ofe['lkeff'] = _replace_parameter(ofe['lkeff'], _lkeff)
                ofe['uksat'] = _uksat

            ofe['luse'] = _replace_parameter(ofe['luse'], _luse)
            ofe['stext'] = _replace_parameter(ofe['stext'], _stext)

            horizons = []
            cur_depth = 0.0
            for j, horizon in enumerate(ofe['horizons']):
                solthk = horizon['solthk']
                if j == 0 and h0_min_depth is not None:
                    solthk = horizon['solthk'] = _replace_parameter(solthk, max(solthk, h0_min_depth))

                solthk = float(solthk)

                if solthk <= 200:
                    horizon['ksat'] = _replace_parameter(horizon['ksat'], _ksat)
                elif solthk > 200 and cur_depth < 200:
                    new_horizon = deepcopy(horizon)
                    new_horizon['solthk'] = 200.0
                    new_horizon['ksat'] = _replace_parameter(new_horizon['ksat'], _ksat)
                    horizons.append(new_horizon)

                if j == 0 and h0_max_om is not None:
                    if horizon['om'] < h0_max_om:
                        horizons.append(horizon)
                else:
                    horizons.append(horizon)

                cur_depth = solthk

            ofe['horizons'] = horizons
            ofe['nsl'] = len(horizons)

            ofe['res_lyr']['kslast'] = _replace_parameter(ofe['res_lyr']['kslast'], _kslast)
            ofes.append(ofe)

        new.obj['ofes'] = ofes
        new.obj['datver'] = version

        return new

    def _load_yaml(self, fn):
        with open(fn) as fp:
            yaml_txt = fp.read()
            self.obj = yaml.safe_load(yaml_txt)

    def dump_yaml(self, dst):
        with open(dst, 'w') as fp:
            fp.write(yaml.dump(self.obj))

    def _load_bson(self, fn):
        import bson
        with open(fn, 'rb') as fp:
            bson_txt = fp.read()
            self.obj = bson.loads(bson_txt)

    def dump_bson(self, dst):
        import bson
        with open(dst, 'wb') as fp:
            fp.write(bson.dumps(self.obj))

    @property
    def datver(self):
        return self.obj['datver']

    @property
    def sand(self):
        sand = self.obj['ofes'][0]['horizons'][0]['sand']
        if sand is None:
            s7778 = self.to7778()
            sand = s7778.obj['ofes'][0]['horizons'][0]['sand']
        assert sand is not None
        return sand

    @property
    def clay(self):
        try:
            clay = self.obj['ofes'][0]['horizons'][0]['clay']
        except KeyError:
            raise Exception(repr(self.obj)) 
            clay = None

        if clay is None:
            s7778 = self.to7778()
            clay = s7778.obj['ofes'][0]['horizons'][0]['clay']
        assert clay is not None
        return clay

    @property
    def avke(self):
        return self.obj['ofes'][0].get('avke')

    @property
    def bd(self):
        bd = self.obj['ofes'][0]['horizons'][0]['bd']
        if bd is None:
            s7778 = self.to7778()
            bd = s7778.obj['ofes'][0]['horizons'][0]['bd']
#        assert bd is not None
        return bd

    @property
    def simple_texture(self):
        from wepppy.wepp.soils.utils import simple_texture
        return simple_texture(clay=self.clay, sand=self.sand)

    @property
    def simple_texture_enum(self):
        from wepppy.wepp.soils.utils import simple_texture_enum
        return simple_texture_enum(clay=self.clay, sand=self.sand)


if __name__ == "__main__":
    from glob import glob
    import csv

    #YamlSoil('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/soils/soilsdb/data/Forest/High sev fire-loam.sol')

    sol_fns = glob('/home/roger/PycharmProjects/wepppy/wepppy/wepp/soils/soilsdb/data/Forest/*.sol')
    #sol_fns = glob('/home/roger/PycharmProjects/wepppy/wepppy/nodb/mods/baer/data/soils/*.sol')

    #fp = open('/home/weppdev/PycharmProjects/wepppy/wepppy/nodb/mods/baer/data/soils/summary.csv', 'w')
    fp = open('/home/roger/PycharmProjects/wepppy/wepppy/wepp/soils/soilsdb/data/Forest/summary.csv', 'w')
    fp.write('slid,texid,burn_class,salb,sat,ki,kr,shcrit,avke,sand,clay,orgmat,cec,rfg,solthk\n')
    for sol_fn in sol_fns:
        sol = WeppSoilUtil(sol_fn)
        sol.dump_yaml(sol_fn.replace('.sol', '.sol.yaml'))

        ofe = sol.obj['ofes'][0]
        hor = ofe['horizons'][0]

        burn_class = ''
        if 'high' in ofe['slid'].lower():
            burn_class = 'high'

        if 'low' in ofe['slid'].lower():
            burn_class = 'low'

        fp.write('{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n'
                 .format(ofe['slid'], ofe['texid'], burn_class, ofe['salb'], ofe['sat'], ofe['ki'], ofe['kr'], ofe['shcrit'], ofe['avke'],
                         hor['sand'], hor['clay'], hor['orgmat'], hor['cec'], hor['rfg'], hor['solthk']))

    fp.close()
