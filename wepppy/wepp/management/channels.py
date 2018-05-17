# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import join as _join

from pprint import pprint

_thisdir = os.path.dirname(__file__)
_datadir = _join(_thisdir, 'data')


def load_channels():
    """
    loads the channel soil managements from the channel.defs file
    These are assigned based on the order of the channel and are
    needed to make the pw0.chn for the watershed run
    """
    global _datadir
    with open(_join(_datadir, 'channels.defs')) as fp:
        blocks = fp.read()
        
    d = {}
    blocks = blocks.split('\n\n')
    for block in blocks:
        block = block.strip().split('\n')
        key = block[0]
        desc = block[1]
        contents = block[2:-2]
        contents[3] = '\n'.join(contents[3].split())
        contents[4] = ' '.join(['%0.5f' % float(v) for v in contents[4].split()])
        contents[5] = ' '.join(['%0.5f' % float(v) for v in contents[5].split()])
        contents[6] = ' '.join(['%0.5f' % float(v) for v in contents[6].split()])
#        contents[7] = ' '.join(['%0.5f' % float(v) for v in contents[7].split()])
        contents = '\n'.join(contents)
        rot = block[-1]
        d[key] = dict(key=key, desc=desc, contents=contents, rot=rot)
        
    return d


def get_channel(key, erodibility=None, critical_shear=None):
    d = load_channels()
    chan = d[key]

    if erodibility is not None or critical_shear is not None:
        contents = chan['contents'].split('\n')

        line8 = contents[8].split()
        if erodibility is not None:
            line8[1] = str(erodibility)
        if critical_shear is not None:
            line8[2] = str(critical_shear)
        contents[8] = ' '.join(line8)

        chan['contents'] = '\n'.join(contents)

    return chan


if __name__ == "__main__":
    load_channels()
    
    pprint(get_channel('OnRock 2', erodibility=99, critical_shear=110))
