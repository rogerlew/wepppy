import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as exists


class SoilMultipleOfeSynth(object):
    def __init__(self, stack=None):
        if stack is None:
            self.stack = []
        else:
            self.stack = stack

    @property
    def description(self):
        s = ["<wepppy.wepp.soils.utils.SoilMultipleOfe>", "Current Working Directory", os.getcwd(), "Stack:"] + self.stack
        s = [f"# {L}" for L in s]
        return '\n'.join(s)

    @property
    def num_ofes(self):
        return len(self.stack)

    def write(self, dst_fn, ksflag=0):
        assert len(self.stack) > 1

        for fn in self.stack:
            assert exists(fn)

        versions = set()
        for fn in self.stack:
            with open(fn) as fp:
                lines = fp.readlines()
                for L in lines:
                    if not L.startswith('#'):
                        versions.add(L)
                        break

        assert len(versions) == 1, f"Soils must be of the same version ({versions})"

        s = [f"7778\n{self.description}\nAny comments:\n{self.num_ofes} {ksflag}\n"]

        for fn in self.stack:
            with open(fn) as fp:
                lines = fp.readlines()
                i = 0
                for L in lines:
                    if not L.startswith('#'):
                        if i > 2:
                            s.append(L)
                        i += 1
            s.append('\n\n')

        with open(dst_fn, 'w') as pf:
            pf.write(''.join(s))

