# Copyright (c) 2016-2025, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# noinspection PyUnusedLocal
"""
Provides functionality for reading and manipulating WEPP management files

wepppy uses .man files to store managements for each landcover type. The mapping
of landcover to particular managements is determined by the map.json file in
the wepppy/wepp/management/data folder.

Using the man files eliminates having to deal with using the .db and .rot files
used with the other versions of WEPP. The .dbs are difficult to management from
one installation to another, and having multiple dbs with the same condition
entries can cause ambiguity. The rotations break if the condition cannot be found
in the db.

`plant-file.spec.md` provides the text from the WEPP 2024 user manual
detailed description of the management/plant files.
"""

from glob import glob
import os
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

import json
from copy import deepcopy
from enum import Enum
import inspect
import random

from wepppy.all_your_base import RGBA, isfloat
from wepppy.all_your_base.dateutils import Julian

__all__ = [
    'WEPPPY_MAN_DIR',
    'ScenarioBase',
    'SectionType',
    'ScenarioReference',
    'PlantLoopCropland',
    'PlantLoopRangeland',
    'PlantLoopForest',
    'PlantLoopRoads',
    'OpLoopCropland',
    'OpLoopRangeland',
    'OpLoopForest',
    'OpLoopRoads',
    'IniLoopCropland',
    'IniLoopRangeland',
    'IniLoopForest',
    'IniLoopRoads',
    'SurfLoopCropland',
    'SurfLoopRangeland',
    'SurfLoopForest',
    'SurfLoopRoads',
    'ContourLoopCropland',
    'DrainLoopCropland',
    'DrainLoopRangeland',
    'DrainLoopRoads',
    'YearLoopCroplandAnnualFallowHerb',
    'YearLoopCroplandAnnualFallowBurn',
    'YearLoopCroplandAnnualFallowSillage',
    'YearLoopCroplandAnnualFallowCut',
    'YearLoopCroplandAnnualFallowRemove',
    'YearLoopCroplandAnnualFallow',
    'YearLoopCroplandPerennialCut',
    'YearLoopCroplandPerennialGraze',
    'YearLoopCroplandPerennial',
    'YearLoopCropland',
    'YearLoopRangelandGrazeLoop',
    'YearLoopRangelandGraze',
    'YearLoopRangelandHerb',
    'YearLoopRangelandBurn',
    'YearLoopRangeland',
    'YearLoopForest',
    'YearLoopRoads',
    'Loops',
    'PlantLoops',
    'OpLoops',
    'IniLoops',
    'SurfLoops',
    'ContourLoops',
    'DrainLoops',
    'YearLoops',
    'Loop',
    'PlantLoop',
    'OpLoop',
    'IniLoop',
    'SurfLoop',
    'ContourLoop',
    'DrainLoop',
    'YearLoop',
    'ManagementLoopManLoop',
    'ManagementLoopMan',
    'ManagementLoop',
    'get_disturbed_classes',
    'ManagementSummary',
    'Management',
    'merge_managements',
    'load_map',
    'InvalidManagementKey',
    'get_management_summary',
    'get_management',
    'get_channel_management',
    'read_management',
    'get_plant_loop_names'
 ]

_thisdir = os.path.dirname(__file__)
_management_dir = _join(_thisdir, "data")
_map_fn = _join(_management_dir, "map.json")
_rred_map_fn = _join(_management_dir, "rred_map.json")
_disturbed_map_fn = _join(_management_dir, "disturbed.json")
_c3s_disturbed_map_fn = _join(_management_dir, "c3s-disturbed.json")
_c3s_disturbed_nigeria_map_fn = _join(_management_dir, "c3s-disturbed-nigeria.json")
_revegetation_map_fn = _join(_management_dir, "revegetation.json")
_eu_disturbed_map_fn = _join(_management_dir, "eu-corine-disturbed.json")
_au_disturbed_map_fn = _join(_management_dir, "au-disturbed.json")
_ca_disturbed_map_fn = _join(_management_dir, "ca-disturbed.json")
_vi_disturbed_map_fn = _join(_management_dir, "vi-disturbed.json")
_esdac_map_fn = _join(_management_dir, "esdac_map.json")
_lu10v5ua_map_fn = _join(_management_dir, "lu10v5ua_map.json")
_turkey_map_fn = _join(_management_dir, "turkey_map.json")
_palouse_map_fn = _join(_management_dir, "palouse_map.json")

WEPPPY_MAN_DIR = _management_dir

def _parse_julian(x):
    foo = int(x)
    if foo == 0:
        return foo
    else:
        return Julian(foo)


def _parse_desc(lines, root):
    assert root is not None
    desc = [lines.pop(0), lines.pop(0), lines.pop(0)]
    for i, L in enumerate(desc):
        if len(L) > 55:
            desc[i] = L[:55]

        if len(L.strip()) == 0:
            desc[i] = '(null)'

    return desc


def pad(vals, n):
    return '\n'.join([' ' * n + '%s' % v for v in str(vals).split('\n')])


class ScenarioBase(object):
    def __init__(self):
        self.root = None

    def setroot(self, root):
        self.root = root
        for name, thing in inspect.getmembers(self):
            if isinstance(thing, ScenarioReference):
                thing.setroot(root)


class SectionType(Enum):
    Plant = 1
    Op = 2
    Ini = 3
    Surf = 4
    Contour = 5
    Drain = 6
    Year = 7


def _scenario_reference_factory(i, section_type, root, this):
    """
    builds and returns a ScenarioReference instance

    this is the caller, and is for debugging purposes
    """

    # no loops in section, should print 0
    if i == 0:
        return ScenarioReference()

    if section_type == SectionType.Plant:
        name = root.plants.nameof(i)
        scen = ScenarioReference(SectionType.Plant, name, root, this)

    elif section_type == SectionType.Op:
        name = root.ops.nameof(i)
        scen = ScenarioReference(SectionType.Op, name, root, this)

    elif section_type == SectionType.Ini:
        name = root.inis.nameof(i)
        scen = ScenarioReference(SectionType.Ini, name, root, this)

    elif section_type == SectionType.Surf:
        name = root.surfs.nameof(i)
        scen = ScenarioReference(SectionType.Surf, name, root, this)

    elif section_type == SectionType.Contour:
        name = root.contours.nameof(i)
        scen = ScenarioReference(SectionType.Contour, name, root, this)

    elif section_type == SectionType.Drain:
        name = root.drains.nameof(i)
        scen = ScenarioReference(SectionType.Drain, name, root, this)

    elif section_type == SectionType.Year:
        name = root.years.nameof(i)
        scen = ScenarioReference(SectionType.Year, name, root, this)

    else:
        raise ValueError('Unknown SectionType')

    return scen


class ScenarioReference(ScenarioBase):
    """
    This is used to dynamically find the scenario
    indexes when we build the managements
    """
    def __init__(self, section_type=None, loop_name=None, root=None, this=None):
        super().__init__()

        assert section_type is None or isinstance(section_type, SectionType)

        self.section_type = section_type
        self.loop_name = loop_name
        self.root = root
        self.this = this

    def __str__(self):
        section_type = self.section_type
        loop_name = self.loop_name

        if section_type is None and loop_name is None:
            return "0"

        if section_type == SectionType.Plant:
            i = [v.name for v in self.root.plants].index(loop_name)

        elif section_type == SectionType.Op:
            i = [v.name for v in self.root.ops].index(loop_name)

        elif section_type == SectionType.Ini:
            i = [v.name for v in self.root.inis].index(loop_name)

        elif section_type == SectionType.Surf:
            if loop_name is None:
                return "0"  # tilseq
            else:
                i = [v.name for v in self.root.surfs].index(loop_name)

        elif section_type == SectionType.Contour:
            i = [v.name for v in self.root.contours].index(loop_name)

        elif section_type == SectionType.Drain:
            i = [v.name for v in self.root.drains].index(loop_name)

        elif section_type == SectionType.Year:
            i = [v.name for v in self.root.years].index(loop_name)

        else:
            raise ValueError('Unknown SectionType')

        assert i >= 0, (id(self.root), type(self.this), section_type, loop_name)

        return str(i + 1)  # section indices are 1 indexed

    def __repr__(self):
        section_type = self.section_type
        loop_name = self.loop_name
        return f'<ScenarioReference> {str(self)} ({section_type}, {loop_name})'


class PlantLoopCropland(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        self.crunit = lines.pop(0)

        line = lines.pop(0).split()
        assert len(line) == 10, line
        self.bb = float(line.pop(0))
        self.bbb = float(line.pop(0))
        self.beinp = float(line.pop(0))
        self.btemp = float(line.pop(0))
        self.cf = float(line.pop(0))
        self.crit = float(line.pop(0))
        self.critvm = float(line.pop(0))
        self.cuthgt = float(line.pop(0))
        self.decfct = float(line.pop(0))
        self.diam = float(line.pop(0))

        line = lines.pop(0).split()
        assert len(line) == 8, line
        self.dlai = float(line.pop(0))
        self.dropfc = float(line.pop(0))
        self.extnct = float(line.pop(0))
        self.fact = float(line.pop(0))
        self.flivmx = float(line.pop(0))
        self.gddmax = float(line.pop(0))
        self.hi = float(line.pop(0))
        self.hmax = float(line.pop(0))

        self.mfocod = int(lines.pop(0))
        assert self.mfocod in [1, 2]

        line = lines.pop(0).split()
        assert len(line) == 10, line
        self.oratea = float(line.pop(0))
        self.orater = float(line.pop(0))
        self.otemp = float(line.pop(0))
        self.pltol = float(line.pop(0))
        self.pltsp = float(line.pop(0))
        self.rdmax = float(line.pop(0))
        self.rsr = float(line.pop(0))
        self.rtmmax = float(line.pop(0))
        self.spriod = int(line.pop(0))
        self.tmpmax = float(line.pop(0))

        line = lines.pop(0).split()
        assert len(line) in [3, 4], line
        has_rcc = len(line) == 4
        self.tmpmin = float(line.pop(0))
        self.xmxlai = float(line.pop(0))
        self.yld = float(line.pop(0))
        if has_rcc:
            self.rcc = float(line.pop(0)) # release cover crop for 2016.3+
        else:
            self.rcc = ''

    def __str__(self):
        return """\
{0.crunit}
{0.bb:0.5f} {0.bbb:0.5f} {0.beinp:0.5f} {0.btemp:0.5f} {0.cf:0.5f} \
{0.crit:0.5f} {0.critvm:0.5f} {0.cuthgt:0.5f} {0.decfct:0.5f} {0.diam:0.5f}
{0.dlai:0.5f} {0.dropfc:0.5f} {0.extnct:0.5f} {0.fact:0.5f} {0.flivmx:0.5f} \
{0.gddmax:0.5f} {0.hi:0.5f} {0.hmax:0.5f}
{0.mfocod}
{0.oratea:0.5f} {0.orater:0.5f} {0.otemp:0.5f} {0.pltol:0.5f} {0.pltsp:0.5f} \
{0.rdmax:0.5f} {0.rsr:0.5f} {0.rtmmax:0.5f} {0.spriod} {0.tmpmax:0.5f}
{0.tmpmin:0.5f} {0.xmxlai:0.5f} {0.yld:0.5f} {0.rcc}
""".format(self)


    def __repr__(self):
        return """\
<PlantLoopCropland>
crunit:{0.crunit}
bb:{0.bb:0.5f} bbb:{0.bbb:0.5f} beinp:{0.beinp:0.5f} btemp:{0.btemp:0.5f} cf:{0.cf:0.5f} \
crit:{0.crit:0.5f} critvm:{0.critvm:0.5f} cuthgt:{0.cuthgt:0.5f} decfct:{0.decfct:0.5f} diam:{0.diam:0.5f}
dlai:{0.dlai:0.5f} dropfc:{0.dropfc:0.5f} extnct:{0.extnct:0.5f} fact:{0.fact:0.5f} flivmx:{0.flivmx:0.5f} \
gddmax:{0.gddmax:0.5f} hi:{0.hi:0.5f} hmax:{0.hmax:0.5f}
mfocod:{0.mfocod}
oratea:{0.oratea:0.5f} orater:{0.orater:0.5f} otemp:{0.otemp:0.5f} pltol:{0.pltol:0.5f} pltsp:{0.pltsp:0.5f} \
rdmax:{0.rdmax:0.5f} rsr:{0.rsr:0.5f} rtmmax:{0.rtmmax:0.5f} spriod:{0.spriod} tmpmax:{0.tmpmax:0.5f}
tmpmin:{0.tmpmin:0.5f} xmxlai:{0.xmxlai:0.5f} yld:{0.yld:0.5f} rcc:{0.rcc}
""".format(self)


class PlantLoopRangeland(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 10, line
        self.aca = float(line.pop(0))
        self.aleaf = float(line.pop(0))
        self.ar = float(line.pop(0))
        self.bbb = float(line.pop(0))
        self.bugs = float(line.pop(0))
        self.cf1 = float(line.pop(0))
        self.cf2 = float(line.pop(0))
        self.cn = float(line.pop(0))
        self.cold = float(line.pop(0))
        self.ffp = int(line.pop(0))

        line = lines.pop(0).split()
        assert len(line) == 10, line
        self.gcoeff = float(line.pop(0))
        self.gdiam = float(line.pop(0))
        self.ghgt = float(line.pop(0))
        self.gpop = float(line.pop(0))
        self.gtemp = float(line.pop(0))
        self.hmax = float(line.pop(0))
        self.plive = float(line.pop(0))
        self.pltol = float(line.pop(0))
        self.pscday = _parse_julian(line.pop(0))
        self.rgcmin = float(line.pop(0))

        line = lines.pop(0).split()
        assert len(line) == 10, line
        self.root10 = float(line.pop(0))
        self.rootf = float(line.pop(0))
        self.scday2 = _parse_julian(line.pop(0))
        self.scoeff = float(line.pop(0))
        self.sdiam = float(line.pop(0))
        self.shgt = float(line.pop(0))
        self.spop = float(line.pop(0))
        self.tcoeff = float(line.pop(0))
        self.tdiam = float(line.pop(0))
        self.tempmn = float(line.pop(0))

        line = lines.pop(0).split()
        assert len(line) == 3, line
        self.thgt = float(line.pop(0))
        self.tpop = float(line.pop(0))
        self.wood = float(line.pop(0))

    def __str__(self):
        return """\
{0.aca:0.5f} {0.aleaf:0.5f} {0.ar:0.5f} {0.bbb:0.5f} {0.bugs:0.5f} \
{0.cf1:0.5f} {0.cf2:0.5f} {0.cn:0.5f} {0.cold:0.5f} {0.ffp}
{0.gcoeff:0.5f} {0.gdiam:0.5f} {0.ghgt:0.5f} {0.gpop:0.5f} {0.gtemp:0.5f} \
{0.hmax:0.5f} {0.plive:0.5f} {0.pltol:0.5f} {0.pscday} {0.rgcmin:0.5f}
{0.root10:0.5f} {0.rootf:0.5f} {0.scday2} {0.scoeff:0.5f} {0.sdiam:0.5f} \
{0.shgt:0.5f} {0.spop:0.5f} {0.tcoeff:0.5f} {0.tdiam:0.5f} {0.tempmn:0.5f}
{0.thgt:0.5f} {0.tpop:0.5f} {0.wood:0.5f}
""".format(self)

    def __repr__(self):
        return """\
<PlantLoopRangeland>
aca:{0.aca:0.5f} aleaf:{0.aleaf:0.5f} ar:{0.ar:0.5f} bbb:{0.bbb:0.5f} bugs:{0.bugs:0.5f} \
cf1:{0.cf1:0.5f} cf2:{0.cf2:0.5f} cn:{0.cn:0.5f} cold:{0.cold:0.5f} ffp:{0.ffp}
gcoeff:{0.gcoeff:0.5f} gdiam:{0.gdiam:0.5f} ghgt:{0.ghgt:0.5f} gpop:{0.gpop:0.5f} gtemp:{0.gtemp:0.5f} \
hmax:{0.hmax:0.5f} plive:{0.plive:0.5f} pltol:{0.pltol:0.5f} pscday:{0.pscday} rgcmin:{0.rgcmin:0.5f}
root10:{0.root10:0.5f} rootf:{0.rootf:0.5f} scday2:{0.scday2} scoeff:{0.scoeff:0.5f} sdiam:{0.sdiam:0.5f} \
shgt:{0.shgt:0.5f} spop:{0.spop:0.5f} tcoeff:{0.tcoeff:0.5f} tdiam:{0.tdiam:0.5f} tempmn:{0.tempmn:0.5f}
thgt:{0.thgt:0.5f} tpop:{0.tpop:0.5f} wood:{0.wood:0.5f}
""".format(self)


# noinspection PyUnusedLocal
class PlantLoopForest(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        raise NotImplementedError


# noinspection PyUnusedLocal
class PlantLoopRoads(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        raise NotImplementedError


class OpLoopCropland(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 3, line
        self.mfo1 = float(line.pop(0))
        self.mfo2 = float(line.pop(0))
        self.numof = int(line.pop(0))

        line = lines.pop(0).split()
        self.pcode = int(line.pop(0))

        if getattr(self.root, 'datver_value', 0.0) >= 2016.3:
            valid_pcodes = [1, 2, 3, 4, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        elif self.root.datver == '98.4':
            valid_pcodes = [1, 2, 3, 4, 10, 11, 12, 13]
        else:
            valid_pcodes = [1, 2, 3, 4]

        assert self.pcode in valid_pcodes, self.pcode

        self.cltpos = ''
        if self.pcode == 3:
            self.cltpos = int(line.pop(0))
            assert self.cltpos in [1, 2]

        assert len(line) == 0

        line = lines.pop(0).split()
        assert len(line) in [7, 9], line
        has_resurf = len(line) == 9
        self.rho = float(line.pop(0))
        self.rint = float(line.pop(0))
        self.rmfo1 = float(line.pop(0))
        self.rmfo2 = float(line.pop(0))
        self.rro = float(line.pop(0))
        self.surdis = float(line.pop(0))
        self.tdmean = float(line.pop(0))

        if has_resurf:
            self.resurf1 = float(line.pop(0))
            self.resurnf1 = float(line.pop(0))
        else:
            self.resurf1 = ''
            self.resurnf1 = ''

        self.frmove = ''
        self.iresad = ''
        self.amtres = ''
        self.fbma1 = ''
        self.fbrnol = ''
        self.frfmov1 = ''
        self.frsmov1 = ''

        if self.pcode in [10, 12]:
            line = lines.pop(0).split()
            assert len(line) >= 1, line
            self.iresad = int(line.pop(0))
            if len(line) >= 1:
                self.amtres = float(line.pop(0))
                assert len(line) == 0, line
            else:
                line = lines.pop(0).split()
                assert len(line) == 1, line
                self.amtres = float(line.pop(0))

        elif self.pcode in [11, 13, 14]:
            line = lines.pop(0).split()
            assert len(line) >= 1, line
            self.frmove = float(line.pop(0))
            assert len(line) == 0, line

        elif self.pcode == 15:
            line = lines.pop(0).split()
            assert len(line) >= 1, line
            self.fbma1 = float(line.pop(0))
            if len(line) >= 1:
                self.fbrnol = float(line.pop(0))
                assert len(line) == 0, line
            else:
                line = lines.pop(0).split()
                assert len(line) == 1, line
                self.fbrnol = float(line.pop(0))

        elif self.pcode in [18, 19]:
            line = lines.pop(0).split()
            assert len(line) >= 1, line
            self.frfmov1 = float(line.pop(0))
            if len(line) >= 1:
                self.frsmov1 = float(line.pop(0))
                assert len(line) == 0, line
            else:
                line = lines.pop(0).split()
                assert len(line) == 1, line
                self.frsmov1 = float(line.pop(0))

    def __str__(self):
        op_line = f"{self.pcode}"
        if self.cltpos != '':
            op_line = f"{op_line} {self.cltpos}"

        effect_line = (
            f"{self.rho:0.5f} {self.rint:0.5f} {self.rmfo1:0.5f} {self.rmfo2:0.5f} "
            f"{self.rro:0.5f} {self.surdis:0.5f} {self.tdmean:0.5f}"
        )
        if self.resurf1 != '':
            effect_line = f"{effect_line} {self.resurf1:0.5f} {self.resurnf1:0.5f}"

        s = (
            f"{self.mfo1:0.5f} {self.mfo2:0.5f} {self.numof}\n"
            f"{op_line}\n"
            f"{effect_line}\n"
        )

        if self.pcode in [11, 13, 14] and self.frmove != '':
            s += f"{self.frmove:0.5f}\n"

        if self.pcode in [10, 12] and self.iresad != '':
            s += f"{self.iresad}\n"
            if self.amtres != '':
                s += f"{self.amtres:0.5f}\n"

        if self.pcode == 15 and self.fbma1 != '':
            s += f"{self.fbma1:0.5f}\n"
            if self.fbrnol != '':
                s += f"{self.fbrnol:0.5f}\n"

        if self.pcode in [18, 19] and self.frfmov1 != '':
            s += f"{self.frfmov1:0.5f}\n"
            if self.frsmov1 != '':
                s += f"{self.frsmov1:0.5f}\n"

        return s

    def __repr__(self):
        s = """\
<OpLoopCropland>
mfo1:{0.mfo1:0.5f} mfo2:{0.mfo2:0.5f} numof:{0.numof}
pcode:{0.pcode} cltpos:{0.cltpos}
rho:{0.rho:0.5f} rint:{0.rint:0.5f} rmfo1:{0.rmfo1:0.5f} rmfo2:{0.rmfo2:0.5f} rro:{0.rro:0.5f} surdis:{0.surdis:0.5f} tdmean:{0.tdmean:0.5f}
""".format(self)

        if self.resurf1 != '':
            s += """resurf1:{0.resurf1:0.5f} resurnf1:{0.resurnf1:0.5f}\n""".format(self)

        if self.pcode in [11, 13, 14] and self.frmove != '':
            s += """frmove:{0.frmove:0.5f}\n""".format(self)

        if self.pcode in [10, 12] and self.iresad != '':
            s += f"iresad:{self.iresad}\n"
            if self.amtres != '':
                s += f"amtres:{self.amtres:0.5f}\n"

        if self.pcode == 15 and self.fbma1 != '':
            s += """fbma1:{0.fbma1:0.5f}\n""".format(self)
            if self.fbrnol != '':
                s += """fbrnol:{0.fbrnol:0.5f}\n""".format(self)

        if self.pcode in [18, 19] and self.frfmov1 != '':
            s += """frfmov1:{0.frfmov1:0.5f}\n""".format(self)
            if self.frsmov1 != '':
                s += """frsmov1:{0.frsmov1:0.5f}\n""".format(self)

        return s


# noinspection PyUnusedLocal
class OpLoopRangeland(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        raise NotImplementedError


# noinspection PyUnusedLocal
class OpLoopForest(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        raise NotImplementedError


# noinspection PyUnusedLocal
class OpLoopRoads(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        raise NotImplementedError


# noinspection PyUnusedLocal
class IniLoopCropland(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 6, line
        self.bdtill = float(line.pop(0))
        self.cancov = float(line.pop(0))  # canopy cover
        self.daydis = int(line.pop(0))
        self.dsharv = int(line.pop(0))
        self.frdp = float(line.pop(0))
        self.inrcov = float(line.pop(0))  # interrill cover

        i = int(lines.pop(0))
        self.iresd = _scenario_reference_factory(i, SectionType.Plant, root, self)

        self.imngmt = int(lines.pop(0))
        assert self.imngmt in [1, 2, 3], self.imngmt

        line = lines.pop(0).split()
        assert len(line) == 5, line
        self.rfcum = float(line.pop(0))
        self.rhinit = float(line.pop(0))
        self.rilcov = float(line.pop(0))  # rill cover
        self.rrinit = float(line.pop(0))
        self.rspace = float(line.pop(0))

        self.rtyp = int(lines.pop(0))

        line = lines.pop(0).split()
        assert len(line) == 5, line
        self.snodpy = float(line.pop(0))
        self.thdp = float(line.pop(0))
        self.tillay1 = float(line.pop(0))
        self.tillay2 = float(line.pop(0))
        self.width = float(line.pop(0))

        line = lines.pop(0).split()
        assert len(line) in (2, 4), line
        has_understory = len(line) == 4
        self.sumrtm = float(line.pop(0))
        self.sumsrm = float(line.pop(0))

        if has_understory:
            self.usinrco = float(line.pop(0)) # resurface 2016.3+
            self.usrilco = float(line.pop(0)) # resurface for non-fragile 2016.3+
        else:
            self.usinrco = '' # 0 defaults
            self.usrilco = '' # 0 defaults
#        if len(line) == 4:
#            self.resurf = float(line.pop(0)) # resurface 2017.1
#            self.resurnf = float(line.pop(0)) # resurface for non-fragile 2017.1
#        else:
#            self.resurf = '' # 0 defaults
#            self.resurnf = '' # 0 defaults

    def __str__(self):
        return """\
{0.bdtill:0.5f} {0.cancov:0.5f} {0.daydis} {0.dsharv} {0.frdp:0.5f} {0.inrcov:0.5f}
{0.iresd}
{0.imngmt}
{0.rfcum:0.5f} {0.rhinit:0.5f} {0.rilcov:0.5f} {0.rrinit:0.5f} {0.rspace:0.5f}
{0.rtyp}
{0.snodpy:0.5f} {0.thdp:0.5f} {0.tillay1:0.5f} {0.tillay2:0.5f} {0.width:0.5f}
{0.sumrtm:0.5f} {0.sumsrm:0.5f} {0.usinrco} {0.usrilco}
""".format(self)

    def __repr__(self):
        return """\
<IniLoopCropland>
bdtill:{0.bdtill:0.5f} cancov:{0.cancov:0.5f} daydis:{0.daydis} dsharv:{0.dsharv} frdp:{0.frdp:0.5f} inrcov:{0.inrcov:0.5f}
iresd:{0.iresd}
imngmt:{0.imngmt}
rfcum:{0.rfcum:0.5f} rhinit:{0.rhinit:0.5f} rilcov:{0.rilcov:0.5f} rrinit:{0.rrinit:0.5f} rspace:{0.rspace:0.5f}
rtyp:{0.rtyp}
snodpy:{0.snodpy:0.5f} thdp:{0.thdp:0.5f} tillay1:{0.tillay1:0.5f} tillay2:{0.tillay2:0.5f} width:{0.width:0.5f}
sumrtm:{0.sumrtm:0.5f} sumsrm:{0.sumsrm:0.5f} usinrco:{0.usinrco} usrilco:{0.usrilco}
""".format(self)


class IniLoopRangeland(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 9, line
        self.frdp = float(line.pop(0))
        self.pptg = float(line.pop(0))
        self.rmagt = float(line.pop(0))
        self.rmogt = float(line.pop(0))
        self.rrough = float(line.pop(0))
        self.snodpy = float(line.pop(0))
        self.thdp = float(line.pop(0))
        self.tillay1 = float(line.pop(0))
        self.tillay2 = float(line.pop(0))

        line = lines.pop(0).split()
        assert len(line) == 9, line
        self.resi = float(line.pop(0))
        self.roki = float(line.pop(0))
        self.basi = float(line.pop(0))
        self.cryi = float(line.pop(0))
        self.resr = float(line.pop(0))
        self.rokr = float(line.pop(0))
        self.basr = float(line.pop(0))
        self.cryr = float(line.pop(0))
        self.cancov = float(line.pop(0))

    def __str__(self):
        return """\
{0.frdp:0.5f} {0.pptg:0.5f} {0.rmagt:0.5f} {0.rmogt:0.5f} {0.rrough:0.5f} {0.snodpy:0.5f} {0.thdp:0.5f} {0.tillay1:0.5f} {0.tillay2:0.5f}
{0.resi:0.5f} {0.roki:0.5f} {0.basi:0.5f} {0.cryi:0.5f} {0.resr:0.5f} {0.rokr:0.5f} {0.basr:0.5f} {0.cryr:0.5f} {0.cancov:0.5f}
""".format(self)

    def __repr__(self):
        return """\
<IniLoopRangeland>
frdp:{0.frdp:0.5f} pptg:{0.pptg:0.5f} rmagt:{0.rmagt:0.5f} rmogt:{0.rmogt:0.5f} rrough:{0.rrough:0.5f} snodpy:{0.snodpy:0.5f} thdp:{0.thdp:0.5f} tillay1:{0.tillay1:0.5f} tillay2:{0.tillay2:0.5f}
resi:{0.resi:0.5f} roki:{0.roki:0.5f} basi:{0.basi:0.5f} cryi:{0.cryi:0.5f} resr:{0.resr:0.5f} rokr:{0.rokr:0.5f} basr:{0.basr:0.5f} cryr:{0.cryr:0.5f} cancov:{0.cancov:0.5f}
""".format(self)

# noinspection PyUnusedLocal
class IniLoopForest(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        raise NotImplementedError


# noinspection PyUnusedLocal
class IniLoopRoads(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        raise NotImplementedError


class SurfLoopCropland(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        self.mdate = _parse_julian(lines.pop(0))

        i = int(lines.pop(0))
        self.op = _scenario_reference_factory(i, SectionType.Op, root, self)

        self.tildep = float(lines.pop(0))
        self.typtil = int(lines.pop(0))
        assert self.typtil in [1, 2]

    def __str__(self):
        return """\
   {0.mdate} # mdate
   {0.op} # op
     {0.tildep:0.5f} # tildep
     {0.typtil} # typtil
""".format(self)

    def __repr__(self):
        return """\
   <SurfLoopCropland>
   mdate:{0.mdate}
   op:{0.op}
     tildep:{0.tildep:0.5f}
     typtil:{0.typtil}
""".format(self)


# noinspection PyUnusedLocal
class SurfLoopRangeland(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        raise NotImplementedError


# noinspection PyUnusedLocal
class SurfLoopForest(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        raise NotImplementedError


# noinspection PyUnusedLocal
class SurfLoopRoads(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        raise NotImplementedError


class ContourLoopCropland(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        line = lines.pop(0).split()
        assert len(line) in [4, 5], line
        has_permanent = len(line) == 5
        self.cntslp = float(line.pop(0))
        self.rdghgt = float(line.pop(0))
        self.rowlen = float(line.pop(0))
        self.rowspc = float(line.pop(0))
        if has_permanent:
            self.contours_perm = int(line.pop(0))
        else:
            self.contours_perm = ''

    def __str__(self):
        s = f"{self.cntslp:0.5f} {self.rdghgt:0.5f} {self.rowlen:0.5f} {self.rowspc:0.5f}"
        if self.contours_perm != '':
            s = f"{s} {self.contours_perm}"
        return f"{s}\n"

    def __repr__(self):
        s = (
            f"<ContourLoopCropland>\n"
            f"cntslp:{self.cntslp:0.5f} rdghgt:{self.rdghgt:0.5f} "
            f"rowlen:{self.rowlen:0.5f} rowspc:{self.rowspc:0.5f}"
        )
        if self.contours_perm != '':
            s = f"{s} contours_perm:{self.contours_perm}"
        return f"{s}\n"


class DrainLoopCropland(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 4, line
        self.ddrain = float(line.pop(0))
        self.drainc = float(line.pop(0))
        self.drdiam = float(line.pop(0))
        self.sdrain = float(line.pop(0))

    def __str__(self):
        return """\
{0.ddrain:0.5f} {0.drainc:0.5f} {0.drdiam:0.5f} {0.sdrain:0.5f}
""".format(self)

    def __repr__(self):
        return """\
<DrainLoopCropland>
ddrain:{0.ddrain:0.5f} drainc:{0.drainc:0.5f} drdiam:{0.drdiam:0.5f} sdrain:{0.sdrain:0.5f}
""".format(self)


# noinspection PyUnusedLocal
class DrainLoopRangeland(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        raise NotImplementedError


# noinspection PyUnusedLocal
class DrainLoopRoads(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        raise NotImplementedError


class YearLoopCroplandAnnualFallowHerb(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        self.jdherb = _parse_julian(lines.pop(0))

    def __str__(self):
        return """\
      {0.jdherb}
""".format(self)


    def __repr__(self):
        return """\
      <YearLoopCroplandAnnualFallowHerb>
      jdherb:{0.jdherb}
""".format(self)

class YearLoopCroplandAnnualFallowBurn(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        self.jdburn = _parse_julian(lines.pop(0))
        self.fbrnag = float(lines.pop(0))
        self.fbrnog = float(lines.pop(0))

    def __str__(self):
        return """\
      {0.jdburn}
      {0.fbrnag:0.5f}
      {0.fbrnog:0.5f}
""".format(self)

    def __repr__(self):
        return """\
      <YearLoopCroplandAnnualFallowBurn>
      jdburn:{0.jdburn}
      fbrnag:{0.fbrnag:0.5f}
      fbrnog:{0.fbrnog:0.5f}
""".format(self)


class YearLoopCroplandAnnualFallowSillage(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        self.jdslge = _parse_julian(lines.pop(0))

    def __str__(self):
        return """\
      {0.jdslge}
""".format(self)

    def __repr__(self):
        return """\
      <YearLoopCroplandAnnualFallowSillage>
      jdslge:{0.jdslge}
""".format(self)


class YearLoopCroplandAnnualFallowCut(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        self.jdcut = _parse_julian(lines.pop(0))
        self.frcut = float(lines.pop(0))
        assert self.frcut >= 0.0
        assert self.frcut <= 1.0

    def __str__(self):
        return """\
      {0.jdcut}
      {0.frcut:0.5f}
""".format(self)

    def __repr__(self):
        return """\
      <YearLoopCroplandAnnualFallowCut>
      jdcut:{0.jdcut}
      frcut:{0.frcut:0.5f}
""".format(self)


class YearLoopCroplandAnnualFallowRemove(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        self.jdmove = _parse_julian(lines.pop(0))
        self.frmove = float(lines.pop(0))
        assert self.frmove >= 0.0
        assert self.frmove <= 1.0

    def __str__(self):
        return """\
      {0.jdmove}
      {0.frmove:0.5f}
""".format(self)

    def __repr__(self):
        return """\
      <YearLoopCroplandAnnualFallowRemove>
      jdmove:{0.jdmove}
      frmove:{0.frmove:0.5f}
""".format(self)


class YearLoopCroplandAnnualFallow(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        self.jdharv = _parse_julian(lines.pop(0))
        self.jdplt = _parse_julian(lines.pop(0))
        self.rw = float(lines.pop(0))
        self.resmgt = resmgt = int(lines.pop(0))
        assert resmgt in [1, 2, 3, 4, 5, 6], resmgt

        if self.root.datver == '98.4':
            assert resmgt != 5

        if resmgt == 1:
            self.data = YearLoopCroplandAnnualFallowHerb(lines, root)
        elif resmgt == 2:
            self.data = YearLoopCroplandAnnualFallowBurn(lines, root)
        elif resmgt == 3:
            self.data = YearLoopCroplandAnnualFallowSillage(lines, root)
        elif resmgt == 4:
            self.data = YearLoopCroplandAnnualFallowCut(lines, root)
        elif resmgt == 5:
            self.data = YearLoopCroplandAnnualFallowRemove(lines, root)
        else:
            self.data = ""

    def __str__(self):
        return """\
   {0.jdharv} \t# Harvesting date or end of fallow period (jdharv)
   {0.jdplt} \t# Planting date or start of fallow period (jdplt)
   {0.rw:0.5f} \t# Row width (rw)
   {0.resmgt} \t# Residue management option (resmgt)
   {0.data}
""".format(self)

    def __repr__(self):
        return """\
   <YearLoopCroplandAnnualFallow>
   jdharv:{0.jdharv} \t# Harvesting date or end of fallow period (jdharv)
   jdplt:{0.jdplt} \t# Planting date or start of fallow period (jdplt)
   rw:{0.rw:0.5f} \t# Row width (rw)
   resmgt:{0.resmgt} \t# Residue management option (resmgt)
   {data}
""".format(self, data=repr(self.data))


class YearLoopCroplandPerennialCut(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        self.cutday = _parse_julian(lines.pop(0))

    def __str__(self):
        return """\
{0.cutday}
""".format(self)

    def __repr__(self):
        return """\
<YearLoopCroplandPerennialCut>
{0.cutday}
""".format(self)


class YearLoopCroplandPerennialGraze(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 4, line
        self.animal = float(line.pop(0))
        self.area = float(line.pop(0))
        self.bodywt = float(line.pop(0))
        self.digest = float(line.pop(0))

        self.gday = _parse_julian(lines.pop(0))

        self.gend = _parse_julian(lines.pop(0))

    def __str__(self):
        return """\
{0.animal:0.5f} {0.area:0.5f} {0.bodywt:0.5f} {0.digest:0.5f}
{0.gday}
{0.gend}
""".format(self)

    def __repr__(self):
        return """\
<YearLoopCroplandPerennialGraze>
animal:{0.animal:0.5f} area:{0.area:0.5f} bodywt:{0.bodywt:0.5f} digest:{0.digest:0.5f}
gday:{0.gday}
gend:{0.gend}
""".format(self)


class YearLoopCroplandPerennial(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        self.jdharv = _parse_julian(lines.pop(0))
        self.jdplt = _parse_julian(lines.pop(0))
        self.jdstop = _parse_julian(lines.pop(0))
        self.rw = float(lines.pop(0))
        self.mgtopt = mgtopt = int(lines.pop(0))
        assert mgtopt in [1, 2, 3]

        self.ncut = self.cut = self.ncycle = self.graze = ''
        if mgtopt == 1:
            self.ncut = ncut = int(lines.pop(0))
            assert ncut > 0

            self.cut = Loops()
            for i in range(ncut):
                self.cut.append(YearLoopCroplandPerennialCut(lines, root))
        elif mgtopt == 2:
            self.ncycle = ncycle = int(lines.pop(0))
            assert ncycle > 0

            self.graze = Loops()
            for i in range(ncycle):
                self.graze.append(YearLoopCroplandPerennialGraze(lines, root))

    def __str__(self):
        return """\
   {0.jdharv} \t# Harvesting date or end of fallow period (jdharv)
   {0.jdplt} \t# Planting date or start of fallow period (jdplt)
   {0.jdstop} \t# Planting date or start of fallow period (jdstop)
   {0.rw:0.5f} \t# Row width (rw)
   {0.mgtopt} \t# Crop management option (mgtopt)
   {0.ncut}{0.ncycle}
   {0.cut}{0.graze}
""".format(self)

    def __repr__(self):

        s = """\
   <YearLoopCroplandPerennial>
   jdharv:{0.jdharv}
   jdplt:{0.jdplt}
   jdstop:{0.jdstop}
   rw:{0.rw:0.5f}
   mgtopt:{0.mgtopt}
""".format(self)

        if self.mgtopt == 1:
            s += '{0.ncut}\n{cut}'.format(self, cut=repr(self.cut))
        if self.mgtopt == 2:
            s += '{0.ncycle}\n{graze}'.format(self, graze=repr(self.graze))

        return s


class YearLoopCropland(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root

        i = int(lines.pop(0))
        self.itype = _scenario_reference_factory(i, SectionType.Plant, root, self)

        i = int(lines.pop(0))
        self.tilseq = _scenario_reference_factory(i, SectionType.Surf, root, self)

        i = int(lines.pop(0))
        self.conset = _scenario_reference_factory(i, SectionType.Drain, root, self)

        i = int(lines.pop(0))
        self.drset = _scenario_reference_factory(i, SectionType.Contour, root, self)

        self.imngmt = imngmt = int(lines.pop(0))
        assert imngmt in [1, 2, 3], lines

        self.annualfallow = self.perennial = ''
        if imngmt in [1, 3]:
            self.annualfallow = YearLoopCroplandAnnualFallow(lines, root)
        else:
            self.perennial = YearLoopCroplandPerennial(lines, root)

    def __str__(self):
        return """\
{0.itype} \t# Plant Growth Scenario index (itype)
{0.tilseq} \t# Surface Effect Scenario index (itype)
{0.conset} \t# Contour Scenario index (conset)
{0.drset} \t# Drainage Scenario index (drset)
{0.imngmt} \t# Cropping system (imngmt)
{0.annualfallow}{0.perennial}
""".format(self)

    def __repr__(self):
        s = """\
<YearLoopCropland>
itype:{itype}
tilseq:{tilseq}
conset:{conset}
drset:{drset}
imngmt:{0.imngmt}
""".format(
    self,
    tilseq=repr(self.tilseq),
    conset=repr(self.conset),
    drset=repr(self.drset),
    itype=repr(self.itype)
)

        if self.annualfallow != '':
            s += 'annualfallow:{}\n'.format(repr(self.annualfallow))

        if self.perennial != '':
            s += 'perennial:{}\n'.format(repr(self.perennial))

        return s


class YearLoopRangelandGrazeLoop(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 2, line
        self.animal = float(line.pop(0))
        self.bodywt = float(line.pop(0))

        self.gday = _parse_julian(lines.pop(0))
        self.gend = _parse_julian(lines.pop(0))
        self.send = _parse_julian(lines.pop(0))
        self.ssday = _parse_julian(lines.pop(0))

    def __str__(self):
        return """\
{0.animal:0.5f} {0.bodywt:0.5f}
{0.gday}
{0.gend}
{0.send}
{0.ssday}
""".format(self)

    def __repr__(self):
        return """\
<YearLoopRangelandGrazeLoop>
animal:{0.animal:0.5f} bodywt:{0.bodywt:0.5f}
gday:{0.gday}
gend:{0.gend}
send:{0.send}
ssday:{0.ssday}
""".format(self)


class YearLoopRangelandGraze(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 5, line

        self.area = float(line.pop(0))

        self.access = float(line.pop(0))
        assert self.access >= 0.0
        assert self.access <= 1.0

        self.digmax = float(line.pop(0))
        assert self.digmax >= 0.0
        assert self.digmax <= 1.0

        self.digmin = float(line.pop(0))
        assert self.digmin >= 0.0
        assert self.access <= 1.0

        self.suppmt = float(line.pop(0))
        assert self.suppmt >= 0.0
        assert self.suppmt <= 1.0

        jgraz = int(lines.pop(0))
        self.loops = Loops()
        for i in range(jgraz):
            self.loops.append(YearLoopRangelandGrazeLoop(lines, root))

    def __str__(self):
        return """\
{0.area:0.5f} {0.access:0.5f} {0.digmax:0.5f} {0.digmin:0.5f} {0.suppmt:0.5f}
{0.jgraz}
{0.loops}
""".format(self)

    def __repr__(self):
        return """\
<YearLoopRangelandGraze>
area:{0.area:0.5f} access:{0.access:0.5f} digmax:{0.digmax:0.5f} digmin:{0.digmin:0.5f} suppmt:{0.suppmt:0.5f}
jgraz:{0.jgraz}
loops:{loops}
""".format(self, loops=repr(self.loops))


class YearLoopRangelandHerb(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        self.active = int(lines.pop(0))

        line = lines.pop(0).split()
        assert len(line) == 4, line
        self.dleaf = float(line.pop(0))
        self.herb = float(line.pop(0))
        self.regrow = float(line.pop(0))
        self.update = float(line.pop(0))

        self.woody = int(lines.pop(0))

        self.jfdate = int(lines.pop(0))

    def __str__(self):
        return """\
{0.active}
{0.dleaf:0.5f} {0.herb:0.5f} {0.regrow:0.5f} {0.update:0.5f}
{0.woody}
{0.jfdate}
""".format(self)


    def __repr__(self):
        return """\
<YearLoopRangelandHerb>
active:{0.active}
dleaf:{0.dleaf:0.5f} herb:{0.herb:0.5f} regrow:{0.regrow:0.5f} update:{0.update:0.5f}
woody:{0.woody}
jfdate:{0.jfdate}
""".format(self)


class YearLoopRangelandBurn(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 5, line
        self.alter = float(line.pop(0))
        self.burned = float(line.pop(0))
        self.change = float(line.pop(0))
        self.hurt = float(line.pop(0))
        self.reduce = float(line.pop(0))

    def __str__(self):
        return """\
{0.alter:0.5f} {0.burned:0.5f} {0.change:0.5f} {0.hurt:0.5f} {0.reduce:0.5f}
""".format(self)

    def __repr__(self):
        return """\
<YearLoopRangelandBurn>
alter:{0.alter:0.5f} burned:{0.burned:0.5f} change:{0.change:0.5f} hurt:{0.hurt:0.5f} reduce:{0.reduce:0.5f}
""".format(self)


class YearLoopRangeland(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root

        i = int(lines.pop(0))
        self.itype = _scenario_reference_factory(i, SectionType.Plant, root, self)

        i = int(lines.pop(0))
        self.tilseq = _scenario_reference_factory(i, SectionType.Surf, root, self)

        i = int(lines.pop(0))
        self.drset = _scenario_reference_factory(i, SectionType.Contour, root, self)

        self.grazig = grazig = int(lines.pop(0))
        assert self.grazig in [0, 1]

        if grazig:
            self.graze = YearLoopRangelandGraze(lines, root)
            self.ihdate = 0
        else:
            self.ihdate = int(lines.pop(0))

        if self.ihdate > 0:
            self.herb = YearLoopRangelandHerb(lines, root)
            self.jfdate = 0
        else:
            self.jfdate = int(lines.pop(0))

        if self.jfdate > 0:
            self.burn = YearLoopRangelandBurn(lines, root)

    def __str__(self):
        s = """\
{0.itype}
{0.tilseq}
{0.drset}
{0.grazig}
""".format(self)

        if self.grazig:
            s += str(self.graze)
        else:
            s += "{0.ihdate}\n".format(self)

        if self.ihdate > 0:
            s += str(self.herb)
        else:
            s += "{0.jfdate}\n".format(self)

        if self.jfdate > 0:
            s += str(self.burn)

        return s

    def __repr__(self):
        s = """\
<YearLoopRangeland>
itype:{0.itype}
tilseq:{0.tilseq}
drset:{0.drset}
grazig:{0.grazig}
""".format(self)

        if self.grazig:
            s += 'graze:' + repr(self.graze)
        else:
            s += "ihdate:{0.ihdate}\n".format(self)

        if self.ihdate > 0:
            s += 'herb:' + repr(self.herb)
        else:
            s += "jfdate:{0.jfdate}\n".format(self)

        if self.jfdate > 0:
            s += 'burn:' + repr(self.burn)

        return s


# noinspection PyUnusedLocal
class YearLoopForest(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        raise NotImplementedError


# noinspection PyUnusedLocal
class YearLoopRoads(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()

        self.root = root
        raise NotImplementedError


class Loops(list):
    def __init__(self):
        super().__init__()
        self.root = None

    def __str__(self):
        return '\n'.join(str(v) for v in super(Loops, self).__iter__())

    def __repr__(self):
        return '\n'.join(repr(v) for v in super(Loops, self).__iter__())

    def __contains__(self, loop):
        loop_str = str(loop)
        for line in self:
            if str(line) == loop_str:
                return True

        return False

    def nameof(self, index):

        if len(self) == 0:
            return None

        return self.__getitem__(int(index)-1).name

    def setroot(self, root):
        self.root = root
        for loop in self:
            loop.setroot(root)

    def find(self, loop):
        loop_str = str(loop)
        for i, L in enumerate(self):
            if str(L) == loop_str:
                return i

        return -1


class PlantLoops(Loops):
    def __init__(self, lines, root):
        super(PlantLoops, self).__init__()
        self.root = root
        n = int(lines.pop(0))
        for j in range(n):
            super(PlantLoops, self).append(PlantLoop(lines, root))


class OpLoops(Loops):
    def __init__(self, lines, root):
        super(OpLoops, self).__init__()
        self.root = root
        n = int(lines.pop(0))
        for j in range(n):
            super(OpLoops, self).append(OpLoop(lines, root))


class IniLoops(Loops):
    def __init__(self, lines, root):
        super(IniLoops, self).__init__()
        self.root = root
        n = int(lines.pop(0))
        for j in range(n):
            super(IniLoops, self).append(IniLoop(lines, root))


class SurfLoops(Loops):
    def __init__(self, lines, root):
        super(SurfLoops, self).__init__()
        self.root = root
        n = int(lines.pop(0))
        for j in range(n):
            super(SurfLoops, self).append(SurfLoop(lines, root))


class ContourLoops(Loops):
    def __init__(self, lines, root):
        super(ContourLoops, self).__init__()
        self.root = root
        n = int(lines.pop(0))
        for j in range(n):
            super(ContourLoops, self).append(ContourLoop(lines, root))


class DrainLoops(Loops):
    def __init__(self, lines, root):
        super(DrainLoops, self).__init__()
        self.root = root
        n = int(lines.pop(0))
        for j in range(n):
            super(DrainLoops, self).append(DrainLoop(lines, root))


class YearLoops(Loops):
    def __init__(self, lines, root):
        super(YearLoops, self).__init__()
        self.root = root
        n = int(lines.pop(0))
        for j in range(n):
            super(YearLoops, self).append(YearLoop(lines, root))


class Loop(ScenarioBase):
    def __init__(self, lines, root):
        super().__init__()
        self.root = root
        self.name = lines.pop(0)
        self.description = _parse_desc(lines, root)
        self.landuse = int(lines.pop(0))
        self.ntill = None
        self.data = None

    def setroot(self, root):
        self.root = root
        self.data.setroot(root)

    def __str__(self):
        landuse_desc = ('N/A', 'Cropland', 'Rangeland', 'Forest', 'Roads')[self.landuse]

        assert self.data is not None, self.name
        assert self.landuse is not None, self.name
        assert len(self.description) == 3, self.description

        if self.ntill is None:
            return """\
{0.name}
{0.description[0]}
{0.description[1]}
{0.description[2]}
{0.landuse} # Landuse - <{landuse_desc}>
{0.data}""".format(self, landuse_desc=landuse_desc)
        else:
            return """\
{0.name}
{0.description[0]}
{0.description[1]}
{0.description[2]}
{0.landuse} # Landuse - <{landuse_desc}>
{0.ntill} # ntill
{0.data}""".format(self, landuse_desc=landuse_desc)

    def __repr__(self):
        landuse_desc = ('N/A', 'Cropland', 'Rangeland', 'Forest', 'Roads')[self.landuse]

        assert self.data is not None, self.name
        assert self.landuse is not None, self.name
        assert len(self.description) == 3, self.description

        if self.ntill is None:
            return """\
<{0._name}>
name:{0.name}
description:'''
{0.description[0]}
{0.description[1]}
{0.description[2]}
'''
landuse:{0.landuse} ({landuse_desc})
data:{data}""".format(self, landuse_desc=landuse_desc, data=repr(self.data))
        else:
            return """\
<{0._name}>
name:{0.name}
description:'''
{0.description[0]}
{0.description[1]}
{0.description[2]}
'''
landuse:{0.landuse} ({landuse_desc})
ntill:{0.ntill}
data:{data}""".format(self, landuse_desc=landuse_desc, data=repr(self.data))


class PlantLoop(Loop):
    _name = 'PlantLoop'

    def __init__(self, lines, root):
        self.root = root
        super(PlantLoop, self).__init__(lines, root)
        landuse = self.landuse

        assert landuse in [1, 2, 3, 4]
        if landuse == 1:
            self.data = PlantLoopCropland(lines, root)
        elif landuse == 2:
            self.data = PlantLoopRangeland(lines, root)
        elif landuse == 3:
            self.data = PlantLoopForest(lines, root)
        elif landuse == 4:
            self.data = PlantLoopRoads(lines, root)


class OpLoop(Loop):
    _name = 'OpLoop'

    def __init__(self, lines, root):
        self.root = root
        super(OpLoop, self).__init__(lines, root)
        landuse = self.landuse

        assert landuse in [1, 2, 3, 4]
        if landuse == 1:
            self.data = OpLoopCropland(lines, root)
        elif landuse == 2:
            self.data = OpLoopRangeland(lines, root)
        elif landuse == 3:
            self.data = OpLoopForest(lines, root)
        elif landuse == 4:
            self.data = OpLoopRoads(lines, root)


class IniLoop(Loop):
    _name = 'IniLoop'

    def __init__(self, lines, root):
        self.root = root
        super(IniLoop, self).__init__(lines, root)
        landuse = self.landuse

        assert landuse in [1, 2, 3, 4]
        if landuse == 1:
            self.data = IniLoopCropland(lines, root)
        elif landuse == 2:
            self.data = IniLoopRangeland(lines, root)
        elif landuse == 3:
            self.data = IniLoopForest(lines, root)
        elif landuse == 4:
            self.data = IniLoopRoads(lines, root)


class SurfLoop(Loop):
    _name = 'SurfLoop'

    def __init__(self, lines, root):
        self.root = root
        super(SurfLoop, self).__init__(lines, root)
        landuse = self.landuse

        self.ntill = ntill = int(lines.pop(0))

        assert landuse in [1, 2, 3, 4], landuse
        self.data = Loops()
        for k in range(ntill):
            if landuse == 1:
                self.data.append(SurfLoopCropland(lines, root))
            elif landuse == 2:
                self.data.append(SurfLoopRangeland(lines, root))
            elif landuse == 3:
                self.data.append(SurfLoopForest(lines, root))
            elif landuse == 4:
                self.data.append(SurfLoopRoads(lines, root))


class ContourLoop(Loop):
    _name = 'ContourLoop'

    def __init__(self, lines, root):
        self.root = root
        super(ContourLoop, self).__init__(lines, root)
        landuse = self.landuse

        assert landuse in [1]
        if landuse == 1:
            self.data = ContourLoopCropland(lines, root)


class DrainLoop(Loop):
    _name = 'DrainLoop'

    def __init__(self, lines, root):
        self.root = root
        super(DrainLoop, self).__init__(lines, root)
        landuse = self.landuse

        assert landuse in [1, 2, 4]
        if landuse == 1:
            self.data = DrainLoopCropland(lines, root)
        elif landuse == 2:
            self.data = DrainLoopRangeland(lines, root)
        elif landuse == 4:
            self.data = DrainLoopRoads(lines, root)


class YearLoop(Loop):
    _name = 'YearLoop'

    def __init__(self, lines, root):
        self.root = root
        super(YearLoop, self).__init__(lines, root)
        landuse = self.landuse

        assert landuse in [1, 2, 3, 4]
        if landuse == 1:
            self.data = YearLoopCropland(lines, root)
        elif landuse == 2:
            self.data = YearLoopRangeland(lines, root)
        elif landuse == 3:
            self.data = YearLoopForest(lines, root)
        elif landuse == 4:
            self.data = YearLoopRoads(lines, root)

# In your managements.py file, find the ManagementLoopManLoop class...

# ... (import Loops if it's not available)
from .managements import Loops # Or adjust the import path as needed

class ManagementLoopManLoop(object):
    # --- CHANGE 1: Correct the __init__ method ---
    def __init__(self, lines, parent, root, year=None, ofe=None):
        self.root = root
        self.parent = parent
        self.nycrop = int(lines.pop(0))
        self._year = year
        self._ofe = ofe

        self.manindx = Loops()
        for j in range(self.nycrop):
            i = int(lines.pop(0))
            scn = _scenario_reference_factory(i, SectionType.Year, root, self)
            self.manindx.append(scn)

    def setroot(self, root):
        self.root = root
        self.manindx.setroot(root)

    def __str__(self):
        s = ["   {0.nycrop} \t# plants/year; <Year: {0._year} - OFE: {0._ofe}>  (nycrop)".format(self)]

        for scn in self.manindx:
            s.append("      {} \t# yearly index <{}>".format(scn, scn.loop_name))

        return '\n'.join(s)

    def __repr__(self):
        s = ["<ManagementLoopManLoop>",
             "   nycrop:{0.nycrop} (Year: {0._year}, OFE: {0._ofe})".format(self),
             "manindx:"]

        for scn in self.manindx:
            s.append("      {} ({})".format(scn, scn.loop_name))

        return '\n'.join(s)


class ManagementLoopMan(object):
    def __init__(self, lines, parent, root, nyears):
        self.root = root
        self.parent = parent

        self.years = Loops()

        for i in range(nyears):
            self.years.append(Loops())
            for j in range(parent.nofes):
                self.years[-1].append(ManagementLoopManLoop(lines, self, root, year=i+1, ofe=j+1))

    def setroot(self, root):
        self.root = root
        for L in self.years:
            L.setroot(root)

    @property
    def nyears(self):
        return len(self.years)

    def __str__(self):
        return """\
{0.nyears} # number of years in a single rotation
{0.years}
""".format(self)

    def __repr__(self):
        return """\
<ManagementLoopMan>
nyears:{0.nyears}
years:{years}
""".format(self, years=repr(self.years))


class ManagementLoop(object):
    """
    The management scenario contains all information associated with a single
    WEPP simulation. The yearly scenarios are used to build this final scenario.
    The yearly scenarios were built from the earlier scenarios - plants, tillage
    sequences, contouring, drainage, and management practices.
    """
    def __init__(self, lines, root):
        self.root = root
        self.name = lines.pop(0)
        self.description = _parse_desc(lines, root)
        self.nofes = nofes = int(lines.pop(0))
        self.ofeindx = Loops()

        for i in range(nofes):
            j = int(lines.pop(0))
            scen = _scenario_reference_factory(j, SectionType.Ini, root, self)
            self.ofeindx.append(scen)

        nrots = int(lines.pop(0))
        nyears = int(lines.pop(0))
        self.loops = Loops()
        for i in range(nrots):
            self.loops.append(ManagementLoopMan(lines, self, root, nyears))

#    @property
#    def nofes(self):
#        return len(self.ofeindx)

    @property
    def nrots(self):
        return len(self.loops)

    def setroot(self, root):
        self.root = root
        for L in self.loops:
            L.setroot(root)

        for L in self.ofeindx:
            L.setroot(root)

    def __str__(self):
        return """\
{0.name}
{0.description[0]}
{0.description[1]}
{0.description[2]}
{0.nofes} # number of ofes in the rotation (nofe)
# Initial Condition Scenario indices used for each OFE
{ofeindx}
{0.nrots} # number of times the rotation is repeated (nrots)
{0.loops}
""".format(self, ofeindx=pad(self.ofeindx, 2))

    def __repr__(self):
        return """\
<ManagementLoop>
name:{0.name}
description:'''
{0.description[0]}
{0.description[1]}
{0.description[2]}
'''
nofes:{0.nofes}
ofeindx:{ofeindx}
nrots:{0.nrots}
loops:{loops}
""".format(self, ofeindx=pad(self.ofeindx, 2), loops=repr(self.loops))


def get_disturbed_classes():
    with open(_join(_thisdir, 'data', 'disturbed.json')) as fp:
        js = json.load(fp)

    disturbed_classes = set()
    for k, _d in js.items():
        _c = _d['DisturbedClass']
        if _c == '':
            _c = None
        disturbed_classes.add(_c)

    return disturbed_classes


class ManagementSummary(object):
    def __init__(self, **kwargs):
        self.key = kwargs["Key"]
        self._map = kwargs.get("_map", None)
        self.man_fn = kwargs["ManagementFile"]
        self.sol_fn = kwargs.get("SoilFile", None)
        self.man_dir = kwargs.get("ManagementDir", _management_dir)
        self.desc = kwargs.get("Description", '')
        self.color = RGBA(*(kwargs["Color"])).tohex().lower()[:-2]

        if "DisturbedClass" in kwargs:
            disturbed_class = kwargs["DisturbedClass"]

            if disturbed_class != '':
                if disturbed_class not in get_disturbed_classes():
                    raise ValueError(
                        f"Disturbed class '{disturbed_class}' is not valid. "
                        f"Valid classes are: {get_disturbed_classes()}"
                    )

            self.disturbed_class = disturbed_class
        else:
            self.disturbed_class = ''

        self.area = None

        self.pct_coverage = None

        m = Management.load(key=self.key, man_fn=self.man_fn, man_dir=self.man_dir, desc=self.desc, color=self.color)
        assert len(m.inis) >= 1, m.inis
        assert m.inis[0].landuse == 1
        assert isinstance(m.inis[0].data, IniLoopCropland)

        self.cancov = m.inis[0].data.cancov
        self.inrcov = m.inis[0].data.inrcov
        self.rilcov = m.inis[0].data.rilcov

        self.cancov_override = None
        self.inrcov_override = None
        self.rilcov_override = None

    @property
    def man_path(self):
        return _join(self.man_dir, self.man_fn)

    @property
    def sol_path(self):
        if self.sol_fn is None:
            return None
        return _join(self.man_dir, self.sol_fn)

    def get_management(self):
        _map = None
        if hasattr(self, "_map"):
            _map = self._map

        m = Management.load(key=self.key, man_fn=self.man_fn, man_dir=self.man_dir, desc=self.desc, color=self.color)
        assert len(m.inis) >= 1

        for i in range(len(m.inis)):
            if m.inis[i].landuse != 1:
                continue
            if not isinstance(m.inis[i].data, IniLoopCropland):
                continue

            if self.cancov_override is not None:
                m.inis[0].data.cancov = self.cancov_override
                
            if self.inrcov_override is not None:
                m.inis[0].data.inrcov = self.inrcov_override

            if self.rilcov_override is not None:
                m.inis[0].data.rilcov = self.rilcov_override
                
        for i in range(len(m.plants)):
            if self.cancov_override is not None:
                # modify xmxlai based on cancov
                m.plants[i].data.xmxlai *= self.cancov_override

        return m

    def as_dict(self):
        _map = None
        if hasattr(self, "_map"):
            _map = self._map

        d = dict(key=self.key, _map=_map,
                 man_fn=self.man_fn, man_dir=self.man_dir,
                 desc=self.desc, color=self.color, area=self.area,
                 pct_coverage=self.pct_coverage,
                 cancov=self.cancov, inrcov=self.inrcov, rilcov=self.rilcov,
                 cancov_override=self.cancov_override,
                 inrcov_override=self.inrcov_override,
                 rilcov_override=self.rilcov_override)

        if hasattr(self, 'disturbed_class'):
            d['disturbed_class'] = self.disturbed_class

        return d


class Management(object):
    """
    Represents the .man files

    Landcover types are mapped to
    """
    def __init__(self, **kwargs):

        self.key = kwargs["Key"]
        self.man_fn = kwargs["ManagementFile"]
        self.man_dir = kwargs.get("ManagementDir", _management_dir)
        self.desc = kwargs.get("Description")
        self.color = tuple(kwargs.get("Color",
            [random.randint(0,255),
             random.randint(0,255),
             random.randint(0,255), 255]))
        self.nofe = None

        if not _exists(_join(self.man_dir, self.man_fn)):
            raise Exception("management file '%s' does not exist"
                            % _join(self.man_dir, self.man_fn))

        self._parse()

    def dump_to_json(self, fn):
        import jsonpickle

        json_str = jsonpickle.encode(self, indent=2)
        with open(fn, 'w') as fp:
            fp.write(json_str)

    @staticmethod
    def load(key, man_fn, man_dir, desc, color=None):
        
        kwargs = {
            "Key": key,
            "ManagementFile": man_fn,
            "ManagementDir": man_dir,
            "Description": desc
        }

        if color is not None:
            kwargs["Color"] = color

        return Management(**kwargs)
        
    def _parse(self):
        """
        Parses a .man file in the 95.7 format
        Details on the file format and parameters are in the
        Plant/Management Input File section (pg. 30) of
        https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/usersum.pdf
        """
        with open(_join(self.man_dir, self.man_fn)) as fp:
            lines = fp.readlines()

        desc_indxs = []
        for i, L in enumerate(lines):
            if "#landuse" in L or " # landuse" in L:
                desc_indxs.append(i-1)
                desc_indxs.append(i-2)
                desc_indxs.append(i-3)

        lines = [L[:L.find('#')].strip() for L in lines]
        lines = [L for i, L in enumerate(lines) if len(L) > 0 or i in desc_indxs]

        del desc_indxs

        self.datver = lines.pop(0)
        try:
            self.datver_value = float(self.datver)
        except ValueError:
            self.datver_value = 0.0
        self.nofe = int(lines.pop(0))
        self.sim_years = int(lines.pop(0))

        # Read Plant Growth Section
        self.plants = PlantLoops(lines, self)

        # Read Operation Section
        self.ops = OpLoops(lines, self)

        # Read Initial Condition Section
        self.inis = IniLoops(lines, self)

        # Read Surface Effects Section
        self.surfs = SurfLoops(lines, self)

        # Read Contour Section
        self.contours = ContourLoops(lines, self)

        # Read Drainage Section
        self.drains = DrainLoops(lines, self)

        # Read Yearly Section
        self.years = YearLoops(lines, self)

        # Read Management Section
        self.man = ManagementLoop(lines, self)

    @property
    def ncrop(self):
        return len(self.plants)

    @property
    def nop(self):
        return len(self.ops)

    @property
    def nini(self):
        return len(self.inis)

    @property
    def nseq(self):
        return len(self.surfs)

    @property
    def ncnt(self):
        return len(self.contours)

    @property
    def ndrain(self):
        return len(self.drains)

    @property
    def nscen(self):
        return len(self.years)

    def setroot(self):
        self.plants.setroot(self)
        self.ops.setroot(self)
        self.inis.setroot(self)
        self.surfs.setroot(self)
        self.contours.setroot(self)
        self.drains.setroot(self)
        self.years.setroot(self)
        self.man.setroot(self)

    def set_bdtill(self, value):
        assert isfloat(value), value
        for i in range(len(self.inis)):
            self.inis[i].data.bdtill = value

    def set_cancov(self, value):
        assert isfloat(value), value
        for i in range(len(self.inis)):
            self.inis[i].data.cancov = value

    def set_rdmax(self, value):
        assert isfloat(value), value
        for i in range(len(self.plants)):
            self.plants[i].data.rdmax = value

    def set_xmxlai(self, value):
        assert isfloat(value), value
        for i in range(len(self.plants)):
            self.plants[i].data.xmxlai = value

    def __setitem__(self, attr, value):
        """
        This is a helper function to set attributes on the Management object.
        It is used to set attributes like bdtill, cancov, rdmax, and xmxlai.
        """
        
        if attr.startswith('plant.data.'):
            for i in range(len(self.plants)):
                _attr = attr[11:]  # remove 'plant.data.'
                if _attr in ['iresd', 'imngmt', 'rtyp']:
                    setattr(self.plants[i].data, _attr, int(value))
                else:
                    setattr(self.plants[i].data, _attr, float(value))

            return 0
                
        if attr.startswith('ini.data.'):
            for i in range(len(self.inis)):
                _attr = attr[9:]  # remove 'ini.data.'
                if _attr in ['mfocod', 'xmxlai']:
                    setattr(self.inis[i].data, _attr, int(value))
                else:
                    setattr(self.inis[i].data, _attr, float(value))

            return 0

        raise NotImplementedError(
            f"Setting attribute '{attr}' is not implemented."
        )

    def make_multiple_ofe(self, nofe):
        assert self.nofe == 1
        assert nofe >= 2
        self.nofe = nofe
        self.man.nofes = nofe

        scen = self.man.ofeindx[0]
        for i in range(nofe-1):
            self.man.ofeindx.append(scen)

        for j in range(self.man.nrots):
            for k in range(self.sim_years):
                mlml = self.man.loops[j].years[k][0]
                for m in range(nofe-1):
                    self.man.loops[j].years[k].append(mlml)

    def build_multiple_year_man(self, sim_years):
        """
        returns a copy of Management with ManagementLoop
        set for the specified number of sim_years
        """

        # first we build the ManagementLoop
        _man = deepcopy(self.man)

        if sim_years == _man.nrots * len(_man.loops[-1].years):
            return self

        # clear the existing loops
        _man.loops = Loops()

        # iterate over the number of rotations
        # the loops repeat over:
        #    - number of rotations
        #    - simulation years
        #    - ofes or channels
        # from slowest to fastest
        for i in range(self.man.nrots):

            # copy the appropriate ManagementLoopMan
            _man.loops.append(deepcopy(self.man.loops[i]))

            # determine number of years in rotation
            yrs = len(_man.loops[-1].years)

            # clear the ManagementLoopManLoop
            _man.loops[-1].years = Loops()

            # iterate over the specified number of years and fill
            # in the apropriate plant and yearly indexes for each
            # year and ofe
            for j in range(sim_years):
                _man.loops[-1].years.append(Loops())
                for k in range(self.nofe):
                    assert len(_man.loops) > 0
                    assert len(_man.loops[-1].years) > 0
                    assert len(self.man.loops) > i
                    assert len(self.man.loops[i].years) == yrs, (len(self.man.loops[i].years), yrs)

                    if len(self.man.loops[i].years[j % yrs]) > k:
                        man_loop_man_loop = deepcopy(self.man.loops[i].years[j % yrs][k])
                    else:
                        man_loop_man_loop = deepcopy(self.man.loops[i].years[j % yrs][0])

                    man_loop_man_loop._year = j+1
                    man_loop_man_loop._ofe = k+1

                    _man.loops[-1].years[-1].append(man_loop_man_loop)

        # now we just need to create a copy of self
        # and copy over the new ManagementLoop and set sim_years
        mf = deepcopy(self)
        mf.man = _man
        mf.sim_years = sim_years
        return mf

    def __str__(self):
        return """\
{0.datver}
{0.nofe} # number of ofes or channels
{0.sim_years} # sim_years

#############################
#   Plant Growth Section    #
#############################
{0.ncrop} # ncrop
{0.plants}
#############################
#     Operation Section     #
#############################
{0.nop} # nop
{0.ops}
#############################
# Initial Condition Section
#############################
{0.nini} # nini
{0.inis}
#############################
#  Surface Effects Section  #
#############################
{0.nseq} # nseq
{0.surfs}
#############################
#      Contour Section      #
#############################
{0.ncnt} # ncnt
{0.contours}
#############################
#      Drainage Section     #
#############################
{0.ndrain} # ndrain
{0.drains}
#############################
#       Yearly Section      #
#############################
{0.nscen} # nscen
{0.years}
#############################
#     Management Section    #
#############################
{0.man}
""".format(self)

    def __repr__(self):
        return """\
datver:{0.datver}
nofe:{0.nofe}
sim_years:{0.sim_years}

ncrop:{0.ncrop}
plants:{plants}

nop:{0.nop}
ops:{ops}

nini:{0.nini}
inis:{inis}

nseq:{0.nseq}
surfs:{surfs}

ncnt:{0.ncnt}
contours:{contours}

ndrain:{0.ndrain}
drains:{drains}

nscen:{0.nscen}
years:{years}

man:{man}
""".format(
    self,
    plants=repr(self.plants),
    ops=repr(self.ops),
    inis=repr(self.inis),
    surfs=repr(self.surfs),
    contours=repr(self.contours),
    drains=repr(self.drains),
    years=repr(self.years),
    man=repr(self.man)
)

    def operations_report(self):
        """Return a chronological list of operations applied in this management."""

        def _resolve(reference):
            if not isinstance(reference, ScenarioReference):
                return None
            if reference.section_type is None or reference.loop_name is None:
                return None

            lookup = {
                SectionType.Plant: getattr(self, 'plants', None),
                SectionType.Op: getattr(self, 'ops', None),
                SectionType.Ini: getattr(self, 'inis', None),
                SectionType.Surf: getattr(self, 'surfs', None),
                SectionType.Contour: getattr(self, 'contours', None),
                SectionType.Drain: getattr(self, 'drains', None),
                SectionType.Year: getattr(self, 'years', None),
            }.get(reference.section_type)

            if not lookup:
                return None

            for loop in lookup:
                if getattr(loop, 'name', None) == reference.loop_name:
                    return loop

            return None

        def _julian_value(value):
            if value is None:
                return None
            if isinstance(value, Julian):
                return int(value.julian)
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        def _format_julian(value):
            if isinstance(value, Julian):
                return f"{value.julian:03d} ({value.month:02d}-{value.day:02d})"
            if isinstance(value, int):
                return f"{value:03d}"
            try:
                ivalue = int(value)
            except (TypeError, ValueError):
                return None
            return f"{ivalue:03d}"

        if not getattr(self, 'man', None):
            return []

        self.setroot()

        report = []

        for rotation_index, rotation in enumerate(self.man.loops, start=1):
            for year_index, year_block in enumerate(rotation.years, start=1):
                for ofe_index, management_loop in enumerate(year_block, start=1):
                    for crop_index, year_reference in enumerate(management_loop.manindx, start=1):
                        year_loop = _resolve(year_reference)
                        if year_loop is None:
                            continue

                        year_loop_data = getattr(year_loop, 'data', None)
                        plant_loop = None
                        crop_display_name = None
                        crop_description = None
                        plant_loop_name = None
                        if year_loop_data is not None and hasattr(year_loop_data, 'itype'):
                            plant_loop = _resolve(year_loop_data.itype)
                            if plant_loop is not None:
                                crop_description = list(getattr(plant_loop, 'description', []) or [])
                                plant_loop_name = getattr(plant_loop, 'name', None)
                                if crop_description:
                                    crop_display_name = crop_description[0].strip()
                                else:
                                    crop_display_name = plant_loop_name

                        surf_loop = None
                        surf_loop_name = None
                        surf_loop_description = None
                        operations_sequence = []
                        if year_loop_data is not None and hasattr(year_loop_data, 'tilseq'):
                            surf_loop = _resolve(year_loop_data.tilseq)
                            if surf_loop is not None:
                                surf_loop_name = getattr(surf_loop, 'name', None)
                                surf_loop_description = list(getattr(surf_loop, 'description', []) or [])
                                operations_sequence = list(getattr(surf_loop, 'data', []) or [])

                        if not operations_sequence:
                            continue

                        for op_index, surf_step in enumerate(operations_sequence, start=1):
                            op_reference = getattr(surf_step, 'op', None)
                            op_loop = _resolve(op_reference) if op_reference else None
                            op_name = getattr(op_loop, 'name', None)
                            op_description_lines = list(getattr(op_loop, 'description', []) or []) if op_loop else None

                            op_data = getattr(op_loop, 'data', None)
                            op_code = getattr(op_data, 'pcode', None) if op_data is not None else None
                            op_loop_name = getattr(op_loop, 'name', None)

                            mdate = getattr(surf_step, 'mdate', None)
                            julian_value = _julian_value(mdate)
                            date_display = _format_julian(mdate)
                            if date_display:
                                date_display += '-' + str(year_index)
                                
                            report.append({
                                'rotation': rotation_index,
                                'year': year_index,
                                'ofe': ofe_index,
                                'crop_sequence': crop_index,
                                'operation_sequence': op_index,
                                'julian_day': julian_value,
                                'date': date_display,
                                'operation': op_name,
                                'operation_description': op_description_lines[0].strip() if op_description_lines else None,
                                'operation_description_lines': op_description_lines,
                                'operation_code': op_code,
                                'crop': crop_display_name,
                                'crop_description_lines': crop_description,
                                'crop_loop': plant_loop_name,
                                'year_loop': getattr(year_loop, 'name', None),
                                'year_loop_description_lines': list(getattr(year_loop, 'description', []) or []),
                                'surface_loop': surf_loop_name,
                                'surface_loop_description_lines': surf_loop_description,
                                'operation_loop': op_loop_name,
                                'operation_loop_description_lines': op_description_lines,
                            })

        report.sort(key=lambda row: (
            row['rotation'],
            row['year'],
            row['crop_sequence'],
            row['julian_day'] if row['julian_day'] is not None else -1,
            row['operation_sequence'],
        ))

        return report


    def operations_report_cli(self):
        """Return a simplified text table of key operation details."""

        rows = self.operations_report()
        if not rows:
            return 'No operations scheduled.'

        columns = (
            ('Date', 'date'),
            ('OFE', 'ofe'),
            ('Operation', 'operation'),
            ('Crop', 'crop'),
        )

        def _stringify(value, default=''):
            if value is None:
                return default
            return str(value)

        width = {}
        for header, key in columns:
            width[header] = len(header)

        table_rows = []
        for row in rows:
            printable = []
            for header, key in columns:
                if key == 'date':
                    value = row.get('date') or (_stringify(row.get('julian_day')) if row.get('julian_day') else '')
                elif key == 'operation':
                    op_name = row.get('operation')
                    op_desc = row.get('operation_description')
                    if op_desc:
                        op_desc = op_desc.replace('comment...', '').replace('comment: ', '')
                    rendered_value = (op_desc or op_name or '')
                    op_loop_name = row.get('operation_loop')
                    if op_loop_name:
                        rendered_value = f"{rendered_value} ({op_loop_name})" if rendered_value else f"({op_loop_name})"
                    value = rendered_value
                elif key == 'crop':
                    display_name = row.get('crop')
                    loop_name = row.get('crop_loop')
                    rendered_value = display_name or ''
                    if loop_name:
                        rendered_value = f"{rendered_value} ({loop_name})" if rendered_value else f"({loop_name})"
                    value = rendered_value
                else:
                    value = row.get(key)
                rendered = _stringify(value)
                printable.append(rendered)
                width[header] = max(width[header], len(rendered))
            table_rows.append(printable)

        header_line = '  '.join(h.ljust(width[h]) for h, _ in columns)
        separator_line = '  '.join('-' * width[h] for h, _ in columns)
        data_lines = ['  '.join(value.ljust(width[header]) for value, (header, _) in zip(row, columns)) for row in table_rows]

        return '\n'.join([header_line, separator_line, *data_lines])


def merge_managements(mans):
    assert len(mans) > 1
    assert all([isinstance(man, Management) for man in mans])

    man0 = mans[0]
    for i in range(1, len(mans)):
        man0 = man0.merge_loops(mans[i])
    return man0


landuse_management_mapping_options = [
    dict(Key='rred', Description='RRED'),
    dict(Key='palouse', Description='palouse'),
    dict(Key='esdac', Description='esdac'),
    dict(Key='lu10v5ua', Description='lu10v5ua'),
    dict(Key='c3s-disturbed-nigeria', Description='Nigeria-c3s-disturbed'),
    dict(Key='c3s-disturbed', Description='Earth-cs3-disturbed'),
    dict(Key='eu-disturbed', Description='EU-disturbed'),
    dict(Key='au-disturbed', Description='Australia-disturbed'),
    dict(Key='ca-disturbed', Description='Canada-disturbed'),
    dict(Key='vi-disturbed', Description='Virgin Islands-disturbed'),
    dict(Key='disturbed', Description='Disturbed'),
    dict(Key='revegetation', Description='Revegetation')
]

def load_map(_map=None) -> dict[str, dict]:
    """
    json.load the management map file and return
    """

    if _map is None:
        with open(_map_fn) as fp:
            d = json.load(fp)
    elif 'rred' in _map.lower():
        with open(_rred_map_fn) as fp:
            d = json.load(fp)
    elif 'palouse' in _map.lower():
        with open(_palouse_map_fn) as fp:
            d = json.load(fp)
    elif 'esdac' in _map.lower():
        with open(_esdac_map_fn) as fp:
            d = json.load(fp)
    elif 'lu10v5ua' in _map.lower():
        with open(_lu10v5ua_map_fn) as fp:
            d = json.load(fp)
    elif 'turkey' in _map.lower():
        with open(_turkey_map_fn) as fp:
            d = json.load(fp)
    elif 'c3s-disturbed-nigeria' in _map.lower():
        with open(_c3s_disturbed_nigeria_map_fn) as fp:
            d = json.load(fp)
    elif 'c3s-disturbed' in _map.lower():
        with open(_c3s_disturbed_map_fn) as fp:
            d = json.load(fp)
    elif 'eu-disturbed' in _map.lower():
        with open(_eu_disturbed_map_fn) as fp:
            d = json.load(fp)
    elif 'au-disturbed' in _map.lower():
        with open(_au_disturbed_map_fn) as fp:
            d = json.load(fp)
    elif 'ca-disturbed' in _map.lower():
        with open(_ca_disturbed_map_fn) as fp:
            d = json.load(fp)
    elif 'vi-disturbed' in _map.lower():
        with open(_vi_disturbed_map_fn) as fp:
            d = json.load(fp)
    elif 'disturbed' in _map.lower():
        with open(_disturbed_map_fn) as fp:
            d = json.load(fp)
    elif 'revegetation' in _map.lower():
        with open(_revegetation_map_fn) as fp:
            d = json.load(fp)
    else:
        with open(_map_fn) as fp:
            d = json.load(fp)

    for k, v in d.items():
        assert k == str(v['Key'])

    return d


class InvalidManagementKey(Exception):
    """
    This Key is Unknown and should be defined in the
    wepppy/wepp/management/data/map.json file
    """

    __name__ = 'InvalidManagementKey'

    def __init__(self, key):
        self.key = key

    def __str__(self):
        return f"{self.key} is an invalid key"


def get_management_summary(dom, _map=None) -> ManagementSummary:
    """
    Parameters
    ----------
    dom : int
        dominant landcover code

    _map: string or None
        mapfile to use

    Returns
    -------
    ManagementSummary
        The object is built from the .man file cooresponding to dom in the
        weppy/wepp/management/data/map.json
    """
    d = load_map(_map=_map)
    k = str(dom)
    if k not in d:
        raise InvalidManagementKey(k)

    return ManagementSummary(**d[k], _map=_map)


def get_management(dom, _map=None) -> Management:
    """
    Parameters
    ----------
    dom : int
        dominant landcover code

    _map : str
        specifies the .json map to load

    Returns
    -------
    Management
        The object is built from the .man file cooresponding to dom in the
        weppy/wepp/management/data/map.json
    """
    d = load_map(_map=_map)
    k = str(dom)
    if k not in d:
        raise InvalidManagementKey

    return Management(**d[k])


def get_channel_management():
    return Management(**dict(Key=0,
                             ManagementFile='channel.man',
                             ManagementDir=_join(_thisdir, 'data'),
                             Description='Channel',
                             Color=[0, 0, 255, 255]))


def read_management(man_path):
    _dir, _fn = _split(man_path)
    return Management(Key=None,
                      ManagementFile=_fn,
                      ManagementDir=_dir,
                      Description='-',
                      Color=(0, 0, 0, 0))

def get_plant_loop_names(runs_dir):
    plant_loops = set()
    man_fns = glob(_join(runs_dir, '*.man'))

    for man_fn in man_fns:
        _fn = _split(man_fn)[-1]
        if 'pw0' in _fn:
            continue

        man = Management(Key=None,
                         ManagementFile=_fn,
                         ManagementDir=runs_dir,
                         Description='-',
                         Color=(0, 0, 0, 0))

        plant_loops.add(man.plants[0].name)

    return list(plant_loops)
