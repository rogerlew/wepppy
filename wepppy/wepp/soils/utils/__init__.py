from .yamlizer import YamlSoil

import csv
import shutil


class SoilReplacements(object):
    def __init__(self, Code=None, LndcvrID=None, WEPP_Type=None, New_WEPPman=None, ManName=None, Albedo=None,
                 iniSatLev=None, interErod=None, rillErod=None, critSh=None, effHC=None, soilDepth=None,
                 Sand=None, Clay=None, OM=None, CEC=None, Comment=None):
        self.Code = Code
        self.LndcvrID = LndcvrID
        self.WEPP_Type = WEPP_Type
        self.New_WEPPman = New_WEPPman
        self.ManName = ManName
        self.Albedo = Albedo
        self.iniSatLev = iniSatLev
        self.interErod = interErod
        self.rillErod = rillErod
        self.critSh = critSh
        self.effHC = effHC
        self.soilDepth = soilDepth
        self.Sand = Sand
        self.Clay = Clay
        self.OM = OM
        self.CEC = CEC
        self.Comment = Comment

    def __repr__(self):
        s = []

        if self.Code is not None:
            s.append('Code={}'.format(self.Code))

        if self.LndcvrID is not None:
            s.append('LndcvrID={}'.format(self.LndcvrID))

        if self.WEPP_Type is not None:
            s.append('WEPP_Type={}'.format(self.WEPP_Type))

        if self.New_WEPPman is not None:
            s.append('New_WEPPman={}'.format(self.New_WEPPman))

        if self.ManName is not None:
            s.append('ManName={}'.format(self.ManName))

        if self.Albedo is not None:
            s.append('Albedo={}'.format(self.Albedo))

        if self.iniSatLev is not None:
            s.append('iniSatLev={}'.format(self.iniSatLev))

        if self.interErod is not None:
            s.append('interErod={}'.format(self.interErod))

        if self.rillErod is not None:
            s.append('rillErod={}'.format(self.rillErod))

        if self.critSh is not None:
            s.append('critSh={}'.format(self.critSh))

        if self.effHC is not None:
            s.append('effHC={}'.format(self.effHC))

        if self.soilDepth is not None:
            s.append('soilDepth={}'.format(self.soilDepth))

        if self.Sand is not None:
            s.append('Sand={}'.format(self.Sand))

        if self.Clay is not None:
            s.append('Clay={}'.format(self.Clay))

        if self.OM is not None:
            s.append('OM={}'.format(self.OM))

        if self.CEC is not None:
            s.append('CEC={}'.format(self.CEC))

        return 'SoilReplacements(' + ' '.join(s) + ')'


def read_lc_file(fname):
    """
    Reads a file containing landcover parameters and returns a dictionary
    with tuple keys (LndcvrID, WEPP_Type) and namedtuple values with fields:
        Code, LndcvrID, WEPP_Type, New_WEPPman, ManName, Albedo, iniSatLev,
        interErod, rillErod, critSh, effHC, soilDepth, Sand, Clay, OM, CEC
    """
    d = {}

    with open(fname) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row['Code'] = int(row['Code'])
            row['LndcvrID'] = int(row['LndcvrID'])

            for k in row:
                v = row[k]
                if isinstance(v, str):
                    if v.lower().startswith('none'):
                        row[k] = None

            d[(str(row['LndcvrID']), row['WEPP_Type'])] = SoilReplacements(**row)

    return d


def _replace_parameter(original, replacement):
    if replacement is None:
        return original

    elif replacement.strip().startswith('*'):
        return str(float(original) * float(replacement.replace('*', '')))

    else:
        return replacement


def simple_texture(clay, sand):
    """
    Classifies horizon texture into silt loam, loam, sand loam, and clay loam

    Courtesy of Mary Ellen Miller
    :return:
    """
    # clay = 21
    # sand = 52
    # cs = 73

    cs = clay + sand
    if (clay <= 27.0 and cs <= 50.0) or \
       (clay > 27.0 and sand <= 20.0 and cs <= 50.0):
        return 'silt loam'
    elif (6.0 <= clay <= 27.0) and \
            (50.0 < cs <= 72.0) and \
            sand <= 52:
        return 'loam'
    elif (sand > 52 or cs > 50 and clay < 6) and \
            sand >= 50:
        return 'sand loam'
    elif (cs > 72 and sand < 50) or \
            (clay > 27 and (20 < sand <= 45)) or \
            (sand <= 20 and cs > 50):
        return 'clay loam'

    tex = soil_texture(clay, sand)
    if tex.startswith('sand'):
        return 'sand loam'
    elif tex.startswith('silt'):
        return 'silt loam'
    elif tex.startswith('clay'):
        return 'clay loam'
    elif tex.startswith('loam'):
        return 'loam'
    
    return None


def _soil_texture(clay, sand):
    assert sand + clay <= 100
    silt = 100.0 - sand - clay

    if clay >= 40:
        if silt >= 40:
            return 'silty clay'
        elif sand <= 45:
            return 'clay'

    if clay >= 35 and sand > 45:
        return 'sandy clay'

    if clay >= 27:
        if sand <= 20:
            return 'silty clay loam'
        elif sand <= 45:
            return 'clay loam'
    else:
        if silt >= 50:
            if clay < 12.0 and silt >= 80:
                return 'silt'
            return 'silt loam'
        elif silt >= 28 and clay >= 7 and sand <= 52:
            return 'loam'

    if clay >= 20 and sand > 45 and silt <= 28:
        return 'sandy clay loam'
    else:
        if silt + 1.5 * clay < 15:
            return 'sand'
        elif silt + 2 * clay < 30:
            return 'loamy sand'
        return 'sandy loam'


def soil_texture(clay, sand):
    res = _soil_texture(clay, sand)
    assert res is not None
    return res


def soil_specialization(src, dst, replacements: SoilReplacements):
    """
    Creates a new soil file based on soil_in_fname and makes replacements
    from the provided replacements namedtuple
    """
    # read the soil_in_fname file
    with open(src) as f:
        lines = f.readlines()

    header = [L for L in lines if L.startswith('#')]
    header.append('# {}\n'.format(repr(replacements)))

    lines = [L for L in lines if not L.startswith('#')]

    line4 = lines[3]
    line4 = line4.split()
    line4[-6] = _replace_parameter(line4[-6], replacements.Albedo)
    line4[-5] = _replace_parameter(line4[-5], replacements.iniSatLev)
    line4[-4] = _replace_parameter(line4[-4], replacements.interErod)
    line4[-3] = _replace_parameter(line4[-3], replacements.rillErod)
    line4[-2] = _replace_parameter(line4[-2], replacements.critSh)
    line4 = ' '.join(line4) + '\n'

    line5 = lines[4]
    line5 = line5.split()
    line5[2] = _replace_parameter(line5[2], replacements.effHC)

    if len(line5) < 5:  # no horizons (e.g. rock)
        shutil.copyfile(src, dst)
        return

    if "rock" not in lines[3].lower() and \
            "water" not in lines[3].lower():
        line5[6] = _replace_parameter(line5[6], replacements.Sand)
        line5[7] = _replace_parameter(line5[7], replacements.Clay)
        line5[8] = _replace_parameter(line5[8], replacements.OM)
        line5[9] = _replace_parameter(line5[9], replacements.CEC)
    line5 = ' '.join(line5) + '\n'

    # Create new soil files
    with open(dst, 'w') as f:
        f.writelines(header)
        f.writelines(lines[:3])
        f.writelines(line4)
        f.writelines(line5)
        if len(lines) > 5:
            f.writelines(lines[5:])


if __name__ == "__main__":
    read_lc_file('/home/roger/wepppy/wepppy/nodb/mods/lt/data/landSoilLookup.csv')
