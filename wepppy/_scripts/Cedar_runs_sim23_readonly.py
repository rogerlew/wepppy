import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

import sys
import shutil
from glob import glob
from wepppy.nodb import Ron, Wepp
from wepppy.wepp.stats import HillSummary, ChannelSummary, OutletSummary, SedimentDelivery

from wepppy.wepp.management import pmetpara_prep

from Cedar_runs_sim23 import projects

os.chdir('/geodata/weppcloud_runs/')

if __name__ == "__main__":

    i = 0
    for proj in projects:

        wd = _join('/geodata/weppcloud_runs', proj['wd'])

        print(wd)

        with open(_join(wd, 'READONLY'), 'w') as fp:
            fp.write('')
