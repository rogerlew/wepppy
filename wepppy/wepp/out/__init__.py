from .loss import *
from .ebe import *
from .plot import *
from .chnwb import Chnwb
from .chanwb import Chanwb
from .totalwatsed import TotalWatSed

import os

correct_daily_hillslopes_pl_path = \
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            'pl-scripts/correct_daily_hillslopes.pl'))
