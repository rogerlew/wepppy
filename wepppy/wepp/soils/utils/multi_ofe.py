import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as exists


def read_soil_lines(fn):
    with open(fn) as fp:
        return fp.readlines()


class SoilMultipleOfeSynth(object):
    def __init__(self, stack=None):
        if stack is None:
            self.stack = []
        else:
            self.stack = stack

    @property
    def description(self):
        s = ["<wepppy.wepp.soils.utils.SoilMultipleOfe>", 
             "Current Working Directory", os.getcwd(), "Stack:"] + self.stack
        s = [f"# {L}" for L in s]
        return '\n'.join(s)

    @property
    def num_ofes(self):
        return len(self.stack)

    @property
    def stack_of_fns(self):
        return all(exists(fn) for fn in self.stack)

    def write(self, dst_fn, ksflag=0):
        assert len(self.stack) > 0

        versions = set()
        for fn in self.stack:
            lines = read_soil_lines(fn)
            for L in lines:
                if not L.startswith('#'):
                    versions.add(L)
                    break

        assert len(versions) == 1, f"Soils must be of the same version ({versions})"
        version = versions.pop() 

        s = [f"{version}\n{self.description}\nAny comments:\n{self.num_ofes} {ksflag}\n"]

        for fn in self.stack:
            lines = read_soil_lines(fn)
            i = 0
            for L in lines:
                if not L.startswith('#'):
                    if i > 2:
                        s.append(L)
                    i += 1
        s.append('\n\n')

        with open(dst_fn, 'w') as pf:
            pf.write(''.join(s))

