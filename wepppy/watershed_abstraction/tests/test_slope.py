# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import join as _join
from os.path import exists as _exists
import shutil
import sys
import unittest

from wepppy.watershed_abstraction import SlopeFile

class Test_slope_file(unittest.TestCase):
    def test_01(self):
        slope = SlopeFile('data/test01.slp')

    def test_02(self):
        slope = SlopeFile('data/test01.slp')
        slope.make_multiple_ofe([0.5])


if __name__ == '__main__':
    unittest.main()