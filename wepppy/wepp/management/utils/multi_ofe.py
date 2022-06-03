import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

from copy import deepcopy

class ManagementMultipleOfeSynth(object):
    def __init__(self, stack=None):
        if stack is None:
            self.stack = []
        else:
            self.stack = stack

    @property
    def description(self):
        s = ["<wepppy.wepp.management.ManagementMultipleOfeSynth>", 
             "Current Working Directory", os.getcwd(), "Stack:"] + self.stack
        s = [f"# {L}" for L in s]
        return '\n'.join(s)

    @property
    def num_ofes(self):
        return len(self.stack)

    def write(self, dst_fn):
        from wepppy.wepp.management import ScenarioReference, SectionType
        assert len(self.stack) > 1
        
        mf = deepcopy(self.stack[0])
        
        for i in range(1, len(self.stack)):
            other = deepcopy(self.stack[i])
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
            if len(other.years) > 0:
                for loop in other.years:
                    mf.years.append(loop)
                    mf.years[-1].root = mf
                    mf.years[-1].name = f'OFE{mf.nofe} {mf.years[-1].name}'
             
            if len(other.man.ofeindx):
                assert len(other.man.ofeindx) == 1
                mf.man.ofeindx.append(other.man.ofeindx[0])
                mf.man.ofeindx[-1].root = mf
                
            if len(other.man.loops):
                assert len(other.man.loops) == 1
                
                scn = other.man.loops[-1].years[-1][-1].manindx[0]
                #_loop_name = other.man.loops[-1].years[-1][-1].manindx[0].loop_name
                other.man.loops[-1].years[-1][-1].manindx[0] = \
                    ScenarioReference(SectionType.Year, f'OFE{mf.nofe} {scn.loop_name}', mf.man.root, other.man.loops[-1].years[-1][-1])
                other.man.loops[-1].years[-1][-1]._ofe = mf.nofe
                
                mf.man.loops[-1].years[-1].append(other.man.loops[-1].years[-1][-1])
                mf.man.loops[-1].years
                mf.root = mf
                
                mf.man.nofes = mf.nofe
                
                    
        with open(dst_fn, 'w') as pf:
            pf.write(str(mf))

