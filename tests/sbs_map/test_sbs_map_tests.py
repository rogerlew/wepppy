import unittest
import os

from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap

_thisdir = os.path.dirname(os.path.abspath(__file__))
_datadir = os.path.join(_thisdir, 'data')

class TestImports(unittest.TestCase):
    def test_read_no_ct_float64(self):
        sbs_fn = '/workdir/wepppy/tests/sbs_map/data/Eaton_SBS_final.tif'
        sbs = SoilBurnSeverityMap(sbs_fn)
        print(sbs.class_pixel_map)

if __name__ == '__main__':
    unittest.main(verbosity=2)
    