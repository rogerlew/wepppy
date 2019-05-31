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
    cs = clay + sand
    if (clay <= 27.0 and cs <= 50.0) or \
            (clay > 27.0 and sand <= 20.0 and cs <= 50.0):
        return "silt loam"
    elif (6.0 <= clay <= 27.0) and \
            (50.0 < cs <= 72.0) and \
            sand <= 52:
        return "loam"
    elif (sand > 52 or cs > 50 and clay < 6) and \
            sand >= 50:
        return "sand loam"
    elif (cs > 72 and sand < 50) or \
            (clay > 27 and (20 < sand <= 45)) or \
            (sand <= 20 and cs > 50):
        return "clay loam"

    return None


def soil_specialization(src, dst, replacements: SoilReplacements):
    """
    Creates a new soil file based on soil_in_fname and makes replacements
    from the provided replacements namedtuple
    """
    # read the soil_in_fname file
    with open(src) as f:
        lines = f.readlines()

    header = [L for L in lines if L.startswith('#')]
    lines = [L for L in lines if not L.startswith('#')]

    line4 = lines[3]
    line4 = line4.split()
    line4[-5] = _replace_parameter(line4[-5], replacements.Albedo)
    line4[-4] = _replace_parameter(line4[-4], replacements.iniSatLev)
    line4[-3] = _replace_parameter(line4[-3], replacements.interErod)
    line4[-2] = _replace_parameter(line4[-2], replacements.rillErod)
    line4[-1] = _replace_parameter(line4[-1], replacements.critSh)
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
        line5[7] = _replace_parameter(line5[6], replacements.Clay)
        line5[8] = _replace_parameter(line5[6], replacements.OM)
        line5[9] = _replace_parameter(line5[6], replacements.CEC)
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