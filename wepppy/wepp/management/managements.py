# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""
Provides functionality for reading and manipulating WEPP management files

weppy uses .man files to store managements for each landcover type. The mapping
of landcover to particular managements is determined by the map.json file in 
the wepppy/wepp/management/data folder.

Using the man files eliminates having to deal with using the .db and .rot files
used with the other versions of WEPP. The .dbs are difficult to management from
one installation to another, and having multiple dbs with the same condition 
entries can cause ambiguity. The rotations break if the condition cannot be found
in the db.
"""


from os.path import join as _join
from os.path import exists as _exists

import json
from copy import deepcopy
from enum import Enum
import inspect

from wepppy.all_your_base import *

_thisdir = os.path.dirname(__file__)
_management_dir = _join(_thisdir, "data")
_map_fn = _join(_management_dir, "map.json")
_rred_map_fn = _join(_management_dir, "rred_map.json")
_esdac_map_fn = _join(_management_dir, "esdac_map.json")
_lu10v5ua_map_fn =  _join(_management_dir, "lu10v5ua_map.json")

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

    def _setroot(self, root):
        self.root = root
        for name, thing in inspect.getmembers(self):
            if isinstance(thing, ScenarioReference):
                thing._setroot(root)


class SectionType(Enum):
    Plant = 1
    Op = 2
    Ini = 3
    Surf = 4
    Contour = 5
    Drain = 6
    Year = 7


def scenarioReference_factory(i, section_type, root, this):
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
    def __init__(self, section_type=None, loop_name=None, 
                 root=None, this=None):
        assert section_type is None or \
               isinstance(section_type, SectionType)
        
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
            

class PlantLoopCropland(ScenarioBase):
    def __init__(self, lines, root):
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
        assert len(line) == 8
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
        assert len(line) == 10
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
        assert len(line) == 3
        self.tmpmin = float(line.pop(0))
        self.xmxlai = float(line.pop(0))
        self.yld = float(line.pop(0))
        
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
{0.tmpmin:0.5f} {0.xmxlai:0.5f} {0.yld:0.5f}
""".format(self)


class PlantLoopRangeland(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 10
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
        assert len(line) == 10
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
        assert len(line) == 10
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
        assert len(line) == 3
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


class PlantLoopForest(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        raise NotImplementedError

        
class PlantLoopRoads(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        raise NotImplementedError

        
class OpLoopCropland(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 3
        self.mfo1 = float(line.pop(0))
        self.mfo2 = float(line.pop(0))
        self.numof = int(line.pop(0))
        
        line = lines.pop(0).split()
        self.pcode = int(line.pop(0))

        if self.root.datver == '98.4':
            assert self.pcode in [1, 2, 3, 4, 10, 11, 12, 13], self.pcode
        else:
            assert self.pcode in [1, 2, 3, 4], self.pcode
        
        self.cltpos = ''
        if self.pcode == 3:
            self.cltpos = int(line.pop(0))
            assert self.cltpos in [1, 2]
        
        line = lines.pop(0).split()
        assert len(line) == 7
        self.rho = float(line.pop(0))
        self.rint = float(line.pop(0))
        self.rmfo1 = float(line.pop(0))
        self.rmfo2 = float(line.pop(0))
        self.rro = float(line.pop(0))
        self.surdis = float(line.pop(0))
        self.tdmean = float(line.pop(0))

        if self.pcode > 5:
            line = lines.pop(0).split()

            if self.pcode in [11, 13]:
                self.frmove = float(line.pop(0))

            if self.pcode in [10, 12]:
                self.iresad = int(line.pop(0))
                self.amtres = int(line.pop(0))
        
    def __str__(self):
        s = """\
{0.mfo1:0.5f} {0.mfo2:0.5f} {0.numof}
{0.pcode} {0.cltpos}
{0.rho:0.5f} {0.rint:0.5f} {0.rmfo1:0.5f} {0.rmfo2:0.5f} {0.rro:0.5f} {0.surdis:0.5f} {0.tdmean:0.5f}
""".format(self)

        if self.pcode in [11, 13]:
            s += """{0.frmove:0.5f}\n""".format(self)

        if self.pcode in [10, 12]:
            s += """{0.iresad} {0.amtres}\n""".format(self)

        return s


class OpLoopRangeland(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        raise NotImplementedError


class OpLoopForest(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        raise NotImplementedError


class OpLoopRoads(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        raise NotImplementedError


class IniLoopCropland(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 6
        self.bdtill = float(line.pop(0))
        self.cancov = float(line.pop(0))  # canopy cover
        self.daydis = int(line.pop(0))
        self.dsharv = int(line.pop(0))
        self.frdp = float(line.pop(0))
        self.inrcov = float(line.pop(0))  # interrill cover

        i = int(lines.pop(0))
        self.iresd = scenarioReference_factory(i, SectionType.Plant, root, self)
        
        self.imngmt = int(lines.pop(0))
        assert self.imngmt in [1, 2, 3]
        
        line = lines.pop(0).split()
        assert len(line) == 5
        self.rfcum = float(line.pop(0))
        self.rhinit = float(line.pop(0))
        self.rilcov = float(line.pop(0))  # rill cover
        self.rrinit = float(line.pop(0))
        self.rspace = float(line.pop(0))
        
        self.rtyp = int(lines.pop(0))
        
        line = lines.pop(0).split()
        assert len(line) == 5
        self.snodpy = float(line.pop(0))
        self.thdp = float(line.pop(0))
        self.tillay1 = float(line.pop(0))
        self.tillay2 = float(line.pop(0))
        self.width = float(line.pop(0))
        
        line = lines.pop(0).split()
        assert len(line) == 2
        self.sumrtm = float(line.pop(0))
        self.sumsrm = float(line.pop(0))

    def __str__(self):
        return """\
{0.bdtill:0.5f} {0.cancov:0.5f} {0.daydis} {0.dsharv} {0.frdp:0.5f} {0.inrcov:0.5f} 
{0.iresd} 
{0.imngmt} 
{0.rfcum:0.5f} {0.rhinit:0.5f} {0.rilcov:0.5f} {0.rrinit:0.5f} {0.rspace:0.5f} 
{0.rtyp} 
{0.snodpy:0.5f} {0.thdp:0.5f} {0.tillay1:0.5f} {0.tillay2:0.5f} {0.width:0.5f} 
{0.sumrtm:0.5f} {0.sumsrm:0.5f}
""".format(self)


class IniLoopRangeland(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 9
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
        assert len(line) == 9
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


class IniLoopForest(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        raise NotImplementedError


class IniLoopRoads(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        raise NotImplementedError


class SurfLoopCropland(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        self.mdate = _parse_julian(lines.pop(0))
        
        i = int(lines.pop(0))
        self.op = scenarioReference_factory(i, SectionType.Op, root, self)
        
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


class SurfLoopRangeland(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        raise NotImplementedError


class SurfLoopForest(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        raise NotImplementedError


class SurfLoopRoads(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        raise NotImplementedError


class ContourLoopCropland(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 4
        self.cntslp = float(line.pop(0))
        self.rdghgt = float(line.pop(0))
        self.rowlen = float(line.pop(0))
        self.rowspc = float(line.pop(0))
        
    def __str__(self):
        return """\
{0.cntslp:0.5f} {0.rdghgt:0.5f} {0.rowlen:0.5f} {0.rowspc:0.5f}
""".format(self)


class DrainLoopCropland(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        line = lines.pop(0).split()
        assert len(line) == 4
        self.ddrain = float(line.pop(0))
        self.drainc = float(line.pop(0))
        self.drdiam = float(line.pop(0))
        self.sdrain = float(line.pop(0))
        
    def __str__(self):
        return """\
{0.ddrain:0.5f} {0.drainc:0.5f} {0.drdiam:0.5f} {0.sdrain:0.5f}
""".format(self)


class DrainLoopRangeland(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        raise NotImplementedError


class DrainLoopRoads(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        raise NotImplementedError


class YearLoopCroplandAnnualFallowHerb(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        self.jdherb = _parse_julian(lines.pop(0))
      
    def __str__(self):
        return """\
      {0.jdherb}
""".format(self)


class YearLoopCroplandAnnualFallowBurn(ScenarioBase):
    def __init__(self, lines, root):
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


class YearLoopCroplandAnnualFallowSillage(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        self.jdslge = _parse_julian(lines.pop(0))

    def __str__(self):
        return """\
            {0.jdslge}
""".format(self)


class YearLoopCroplandAnnualFallowCut(ScenarioBase):
    def __init__(self, lines, root):
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


class YearLoopCroplandAnnualFallowRemove(ScenarioBase):
    def __init__(self, lines, root):
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


class YearLoopCroplandAnnualFallow(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        self.jdharv = _parse_julian(lines.pop(0))
        self.jdplt = _parse_julian(lines.pop(0))
        self.rw = float(lines.pop(0))
        self.resmgt = resmgt = int(lines.pop(0))
        assert resmgt in [1, 2, 3, 4, 5, 6]

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
   {0.jdharv}
   {0.jdplt}
   {0.rw:0.5f}
   {0.resmgt}
   {0.data}
""".format(self)


class YearLoopCroplandPerennialCut(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        self.cutday = _parse_julian(lines.pop(0))
        
    def __str__(self):
        return """\
{0.cutday}
""".format(self)


class YearLoopCroplandPerennialGraze(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        L = lines.pop(0).split()
        assert len(L) == 4
        self.animal = float(L.pop(0))
        self.area = float(L.pop(0))
        self.bodywt = float(L.pop(0))
        self.digest = float(L.pop(0))
        
        self.gday = _parse_julian(lines.pop(0))
        
        self.gend = _parse_julian(lines.pop(0))
        
    def __str__(self):
        return """\
{0.animal:0.5f} {0.area:0.5f} {0.bodywt:0.5f} {0.digest:0.5f}
{0.gday}
{0.gend}
""".format(self)


class YearLoopCroplandPerennial(ScenarioBase):
    def __init__(self, lines, root):
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
   {0.jdharv} # jdharv
   {0.jdplt} # jdplt
   {0.jdstop} # jdstop
   {0.rw:0.5f} # rw
   {0.mgtopt} # mgtopt
   {0.ncut}{0.ncycle}
   {0.cut}{0.graze}
""".format(self)
        

class YearLoopCropland(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        
        i = int(lines.pop(0))
        self.itype = scenarioReference_factory(i, SectionType.Plant, root, self)
        
        i = int(lines.pop(0))
        self.tilseq = scenarioReference_factory(i, SectionType.Surf, root, self)
        
        i = int(lines.pop(0))
        self.conset = scenarioReference_factory(i, SectionType.Drain, root, self)
        
        i = int(lines.pop(0))
        self.drset = scenarioReference_factory(i, SectionType.Contour, root, self)
        
        self.imngmt = imngmt = int(lines.pop(0))
        assert imngmt in [1, 2, 3]
        
        self.annualfallow = self.perennial = ''
        if imngmt in [1, 3]:
            self.annualfallow = YearLoopCroplandAnnualFallow(lines, root)
        else:
            self.perennial = YearLoopCroplandPerennial(lines, root)
            
    def __str__(self):
        return """\
{0.itype}
{0.tilseq}
{0.conset}
{0.drset}
{0.imngmt}
{0.annualfallow}{0.perennial}
""".format(self)
        

class YearLoopRangelandGrazeLoop(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        L = lines.pop(0).split()
        assert len(L) == 2
        self.animal = float(L.pop(0))
        self.bodywt = float(L.pop(0))

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


class YearLoopRangelandGraze(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        L = lines.pop(0).split()
        assert len(L) == 5
        
        self.area = float(L.pop(0))
        
        self.access = float(L.pop(0))
        assert self.access >= 0.0
        assert self.access <= 1.0
        
        self.digmax = float(L.pop(0))
        assert self.digmax >= 0.0
        assert self.digmax <= 1.0
        
        self.digmin = float(L.pop(0))
        assert self.digmin >= 0.0
        assert self.access <= 1.0
        
        self.suppmt = float(L.pop(0))
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


class YearLoopRangelandHerb(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        self.active = int(lines.pop(0))
        
        L = lines.pop(0).split()
        assert len(L) == 4
        self.dleaf = float(L.pop(0))
        self.herb = float(L.pop(0))
        self.regrow = float(L.pop(0))
        self.update = float(L.pop(0))
        
        self.woody = int(lines.pop(0))
        
        self.jfdate = int(lines.pop(0))
        
    def __str__(self):
        return """\
{0.active}
{0.dleaf:0.5f} {0.herb:0.5f} {0.regrow:0.5f} {0.update:0.5f}
{0.woody}
{0.jfdate}
""".format(self)


class YearLoopRangelandBurn(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        L = lines.pop(0).split()
        assert len(L) == 5
        self.alter = float(L.pop(0))
        self.burned = float(L.pop(0))
        self.change = float(L.pop(0))
        self.hurt = float(L.pop(0))
        self.reduce = float(L.pop(0))
        
    def __str__(self):
        return """\
{0.alter:0.5f} {0.burned:0.5f} {0.change:0.5f} {0.hurt:0.5f} {0.reduce:0.5f}
""".format(self)


class YearLoopRangeland(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        
        i = int(lines.pop(0))
        self.itype = scenarioReference_factory(i, SectionType.Plant, root, self)
        
        i = int(lines.pop(0))
        self.tilseq = scenarioReference_factory(i, SectionType.Surf, root, self)
        
        i = int(lines.pop(0))
        self.drset = scenarioReference_factory(i, SectionType.Contour, root, self)
        
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
              

class YearLoopForest(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        raise NotImplementedError
        

class YearLoopRoads(ScenarioBase):
    def __init__(self, lines, root):
        self.root = root
        raise NotImplementedError
            

class Loops(list):
    def __str__(self):
        return '\n'.join(str(v) for v in super(Loops, self).__iter__())
               
    def __contains__(self, loop):
        loop_str = str(loop)
        for L in self:
            if str(L) == loop_str:
                return True
                
        return False

    def nameof(self, index):

        if len(self) == 0:
            return None

        return self.__getitem__(int(index)-1).name

    def _setroot(self, root):
        self.root = root
        for loop in self:
            loop._setroot(root)
                
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
        self.root = root
        self.name = lines.pop(0)
        self.description = _parse_desc(lines, root)
        self.landuse = int(lines.pop(0))
        self.ntill = None
        self.data = None

    def _setroot(self, root):
        self.root = root
        self.data._setroot(root)
        
    def __str__(self):
        if self.ntill is None:
            return """\
{0.name}
{0.description[0]}
{0.description[1]}
{0.description[2]}
{0.landuse} # landuse
{0.data}""".format(self)
        else:
            return """\
{0.name}
{0.description[0]}
{0.description[1]}
{0.description[2]}
{0.landuse} # landuse
{0.ntill} # ntill
{0.data}""".format(self)


class PlantLoop(Loop):
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
    def __init__(self, lines, root):
        self.root = root
        super(ContourLoop, self).__init__(lines, root)
        landuse = self.landuse
        
        assert landuse in [1]
        if landuse == 1:
            self.data = ContourLoopCropland(lines, root)
    

class DrainLoop(Loop):
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


class ManagementLoopManLoop(object):
    def __init__(self, lines, parent, root):
        self.parent = parent
        self.nycrop = int(lines.pop(0))

        self.manindx = []
        for j in range(self.nycrop):
            i = int(lines.pop(0))
            scn = scenarioReference_factory(i, SectionType.Year, root, self)
            self.manindx.append(scn)
        
    def _setroot(self, root):
        self.root = root
        self.manindx.root = root
            
    def __str__(self):
        s = ["   {0.nycrop} # number of crops per year".format(self)]

        for scn in self.manindx:
            s.append("      {} # yearly index".format(scn))

        return '\n'.join(s)


class ManagementLoopMan(object):
    def __init__(self, lines, parent, root):
        self.parent = parent
        nyears = int(lines.pop(0))
        
        self.years = Loops()
        
        for i in range(nyears):
            self.years.append(Loops())
            for j in range(parent.nofes):
                self.years[-1].append(ManagementLoopManLoop(lines, self, root))
    
    def _setroot(self, root):
        self.root = root
        for L in self.years:
            L._setroot(root)
            
    @property
    def nyears(self):
        return len(self.years)
            
    def __str__(self):
        return """\
{0.nyears} # number of years in a single rotation
{0.years}
""".format(self)


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
        nofes = int(lines.pop(0))
        self.ofeindx = Loops()
        
        for i in range(nofes):
            j = int(lines.pop(0))
            scen = scenarioReference_factory(j, SectionType.Ini, root, self)
            self.ofeindx.append(scen)
            
        nrots = int(lines.pop(0))
        self.loops = Loops()
        for i in range(nrots):
            self.loops.append(ManagementLoopMan(lines, self, root))
        
    @property
    def nofes(self):
        return len(self.ofeindx)
        
    @property
    def nrots(self):
        return len(self.loops)
        
    def _setroot(self, root):
        self.root = root
        for L in self.loops:
            L._setroot(root)
            
        for L in self.ofeindx:
            L._setroot(root)
            
    def __str__(self):
        return """\
{0.name}
{0.description[0]}
{0.description[1]}
{0.description[2]}
{0.nofes} # number of ofes in the rotation
# Initial Condition Scenario indices used for each OFE
{ofeindx}
{0.nrots} # number of times the rotation is repeated
{0.loops}
""".format(self, ofeindx=pad(self.ofeindx, 2))

        
class ManagementSummary(object):
    def __init__(self, **kwargs):
        self.key = kwargs["Key"]
        self._map = kwargs.get("_map", None)
        self.man_fn = kwargs["ManagementFile"]
        self.man_dir = kwargs.get("ManagementDir", _management_dir)
        self.desc = kwargs["Description"]
        self.color = RGBA(*(kwargs["Color"])).tohex().lower()[:-2]

        self.area = None

        self.pct_coverage = None

        m = get_management(self.key, _map=self._map)
        assert len(m.inis) == 1
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

    def get_management(self):
        _map = None
        if hasattr(self, "_map"):
            _map = self._map

        m = get_management(self.key, _map=_map)
        assert len(m.inis) == 1
        assert m.inis[0].landuse == 1
        assert isinstance(m.inis[0].data, IniLoopCropland)

        if self.cancov_override is not None:
            m.inis[0].data.cancov = self.cancov_override

        if self.inrcov_override is not None:
            m.inis[0].data.inrcov = self.inrcov_override

        if self.rilcov_override is not None:
            m.inis[0].data.rilcov = self.rilcov_override

        return m
     
    def as_dict(self):
        _map = None
        if hasattr(self, "_map"):
            _map = self._map

        return dict(key=self.key, _map=_map,
                    man_fn=self.man_fn, man_dir=self.man_dir, 
                    desc=self.desc, color=self.color, area=self.area, 
                    pct_coverage=self.pct_coverage,
                    cancov=self.cancov, inrcov=self.inrcov, rilcov=self.rilcov,
                    cancov_override=self.cancov_override,
                    inrcov_override=self.inrcov_override,
                    rilcov_override=self.rilcov_override)


class Management(object):
    """
    Represents the .man files
    
    Landcover types are mapped to 
    """
    def __init__(self, **kwargs):
        self.key = kwargs["Key"]
        self.man_fn = kwargs["ManagementFile"]
        self.man_dir = kwargs.get("ManagementDir", _management_dir)
        self.desc = kwargs["Description"]
        self.color = tuple(kwargs["Color"])
        
        if not _exists(_join(self.man_dir, self.man_fn)):
            raise Exception("management file '%s' does not exist"
                            % self.man_fn)
                            
        self._parse()
    
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
            if "#landuse" in L or  " # landuse" in L:
                desc_indxs.append(i-1)
                desc_indxs.append(i-2)
                desc_indxs.append(i-3)
                
        lines = [L[:L.find('#')].strip() for L in lines]
        lines = [L for i, L in enumerate(lines) if len(L) > 0 or i in desc_indxs]

        del desc_indxs
        
        self.datver = lines.pop(0)
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
            
    def _setroot(self):
        
        self.plants._setroot(self)
        self.ops._setroot(self)
        self.inis._setroot(self)
        self.surfs._setroot(self)
        self.contours._setroot(self)
        self.drains._setroot(self)
        self.years._setroot(self)
        self.man._setroot(self)

    def make_multiple_ofe(self, nofe):
        assert self.nofe == 1
        assert nofe >= 2
        self.nofe = nofe

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
                    assert len(self.man.loops[i].years) == yrs

                    if len(self.man.loops[i].years[j%yrs]) > k:
                        manLoopManLoop = deepcopy(self.man.loops[i].years[j%yrs][k])
                    else:
                        manLoopManLoop = deepcopy(self.man.loops[i].years[j%yrs][0])

                    _man.loops[-1].years[-1].append(manLoopManLoop)
    
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
""".format( self)
    
    def merge_loops(self, other):
        """
        """
        # 1) plant, operations, and intital condition scenarios
        #    if they don't already exist. 
        #        if Year.loop.landuse.iscen is 1 (crop)
        #            op scenario index in Year.loop.loop.cropland.op
        #            plant scenario index in Year.loop.cropland.itype
        #            surface effects index in Year.loop.cropland.tilseq
        #            contour effect index in Year.loop.cropland.tilseq
        #            drainage scenario index in Year.loop.cropland.drset
        #        if Year.loop.landuse.iscen is 2 (range)
        #            plant scenario index in Year.loop.Year.rangeland.itype
        #            surface effects scenario index in Surf.loop.loop.rangeland.tilseq
        #            drainage scenario index in Surf.Year.loop.rangeland.drset
        #        
        # 2) the Surface effects section has indexes to op scenario
        #        if Surf.loop.landuse.iseq is 1 (crop)
        #            op scearnio index in Surf.loop.loop.cropland.op
        #
        # 3) Ini also has index references
        #        if Ini.loop.landuse.lanuse is 1 (crop)
        #            plant scenario indes in Ini.loop.landuse.cropland.inrcov
        # 
        # 4) Management has references for each ofe (channel) to the ini index
        
        assert isinstance(other, Management)
        
        mf = deepcopy(self)
        other = deepcopy(other)
        mf.nofe += 1
        
        # Read Plant Growth Section
        if len(other.plants) > 0:
            for loop in other.plants:
                if mf.plants.find(loop) == -1:
                    mf.plants.append(loop)
                    
        # Read Operation Section
        if len(other.ops) > 0:
            for loop in other.ops:
                if mf.ops.find(loop) == -1:
                    mf.ops.append(loop)
                
        # Read Initial Condition Section
        if len(other.inis) > 0:
            for loop in other.inis:
                if mf.inis.find(loop) == -1:
                    mf.inis.append(loop)
                
        # Read Surface Effects Section
        if len(other.surfs) > 0:
            for loop in other.surfs:
                if mf.surfs.find(loop) == -1:
                    mf.surfs.append(loop)
    
        # Read Contour Section
        if len(other.contours) > 0:
            for loop in other.contours:
                if mf.contours.find(loop) == -1:
                    mf.contours.append(loop)
        
        # Read Drainage Section
        if len(other.drains) > 0:
            for loop in other.drains:
                if mf.drains.find(loop) == -1:
                    mf.drains.append(loop)
           
        # Read Yearly Section
        other_year_map = {}
        for loop in other.years:
            i = mf.years.find(loop)
            if i == -1:
                last = mf.years[-1].name
                last = int(''.join([v for v in last if v in '0123456789']))
                next = 'Year {}'.format(last + 1)
                other_year_map[loop.name] = next
                loop.name = next
                mf.years.append(loop)
           
        # update the ofeindx
        # has ScenarioReferences to Ini, so they should update fine
        mf.man.ofeindx.append(other.man.ofeindx) 
        
        # need to merge the loops. The loops point to yearly indexes,
        # the indexes of other have changed, so we need to set the 
        # name attribute for the ScenarioReferences based on the
        # other_year_map        
     
        for i in range(len(other.man.loops)):   # ManagementLoopMan
            for j in range(len(other.man.loops[i].years)):  # Loops
                for k in range(len(other.man.loops[i].years[j])):  # ManagementLoopManLoop
                    loop_name = other.man.loops[i].years[j][k].manindx.loop_name
                    new_name = other_year_map.get(loop_name, loop_name)
                    other.man.loops[i].years[j][k].manindx.loop_name = new_name
                    
                    mf.man.loops[-1].years[-1].append(other.man.loops[i].years[j][k])
                    
        mf._setroot()
        
        _id = id(mf)
        for loops in mf.plants, mf.inis, mf.ops, mf.surfs, mf.drains, mf.years:
            for loop in loops:
                assert _id == id(loop.root)
                assert _id == id(loop.data.root)
            
        return mf


def merge_managements(mans):
    assert len(mans) > 1
    assert all([isinstance(man, Management) for man in mans])

    man0 = mans[0]
    for i in range(1, len(mans)):
        man0 = man0.merge_loops(mans[i])
    return man0


def load_map(_map=None):

    if _map is None:
        with open(_map_fn) as fp:
            d = json.load(fp)
    elif 'rred' in _map.lower():
        with open(_rred_map_fn) as fp:
            d = json.load(fp)
    elif 'esdac' in _map.lower():
        with open(_esdac_map_fn) as fp:
            d = json.load(fp)
    elif 'lu10v5ua' in _map.lower():
        with open(_lu10v5ua_map_fn) as fp:
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
    
    def __init__(self):
        pass

        
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
    if not k in d:
        raise InvalidManagementKey

    return ManagementSummary(**d[k], _map=_map)

        
def get_management(dom, _map=None) -> Management:
    """
    Parameters
    ----------
    dom : int
        dominant landcover code
    
    Returns
    -------
    Management
        The object is built from the .man file cooresponding to dom in the
        weppy/wepp/management/data/map.json
    """
    d = load_map(_map=_map)
    k = str(dom)
    if not k in d:
        raise InvalidManagementKey
        
    return Management(**d[k])


if __name__ == "__main__":
    db = 'lu10v5ua' #None #'esdac' # None  # 'rred'

    d = load_map(db)

    print(d.keys())

#    man_sum = get_management_summary(323, _map=db)
#    print(man_sum.desc)

#    m = get_management(323, _map=db)

#    m2 = m.build_multiple_year_man(5)
    #print(m2)

    import csv

    fp = open('tests/weppcloud_managements.csv', 'w')
    wtr = csv.writer(fp)

    wtr.writerow(['key', 'desc', 'man', 'cancov', 'inrcov', 'rilcov'])

    for k in d:
        m = get_management(k, _map=db)
        #Ini.loop.landuse.cropland (6.6 inrcov), (9.3 rilcov)

        assert len(m.inis) == 1
        assert m.inis[0].landuse == 1
        assert isinstance(m.inis[0].data, IniLoopCropland)
        cancov, inrcov, rilcov = m.inis[0].data.cancov, m.inis[0].data.inrcov, m.inis[0].data.rilcov
        man_fn = d[k]['ManagementFile']

        print('{},{},{},{},{}'.format(k, m.desc, man_fn, cancov, inrcov, rilcov))

        wtr.writerow([k, m.desc, cancov, inrcov, rilcov])

    fp.close()

    """
    import jsonpickle
    
    with open(_map_fn) as fp:
        d = json.load(fp)
            
            
    m = get_management(100)
    js = jsonpickle.encode(m)    
    #print json.dumps(json.loads(js), sort_keys=True, indent=4, separators=(',', ': '))
    
    ms = []
    ms.append(get_management(100))
    ms.append(get_management(101))
    ms.append(get_management(103))
    
    m2= merge_managements(ms)
    
    sys.exit()
    
    ms = []
    for dom in d:
        print d[str(dom)]
        m = Management(**d[str(dom)])
        ms.append(m)
        
        mf = m.build_multiple_year_man(100)
        
        js = jsonpickle.encode(m)
        

        m = jsonpickle.decode(js)
        with open(_join('tests', d[str(dom)]['ManagementFile']
                  .replace('/','.')), 'w') as fp:
            fp.write(str(mf))
       

    merge_managements(ms[:20])
    
#    ms[0].merge(ms[1])       
        
        
#    m = Management(ManagementFile='tests/pw0.man', 
#               ManagementDir='./',
#               Description='watershed test file')
           
   
    with open(_join('tests', 'pw2.man'), 'w') as fp:
        fp.write(str(m))
               
               
    js = jsonpickle.encode(m)
    
    m = jsonpickle.decode(js)
    
    print m
    
    import json
    js2 = json.dumps(json.loads(js), indent=4, sort_keys=True)
    print js2
    
    with open(_join('tests', 'pw2.json'), 'w') as fp:
        fp.write(js2)
    """
