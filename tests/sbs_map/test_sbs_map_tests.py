import unittest
import os

from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap, sbs_map_sanity_check

_thisdir = os.path.dirname(os.path.abspath(__file__))
_datadir = os.path.join(_thisdir, 'data')

class TestImports(unittest.TestCase):
    def test_read_no_ct_float64(self):
        sbs_fn = '/workdir/wepppy/tests/sbs_map/data/Eaton_SBS_final.tif'
        sbs = SoilBurnSeverityMap(sbs_fn)
        print(sbs.class_pixel_map)

class TestSbsMapSanityCheck(unittest.TestCase):
    def test_sanity_valid_classes(self):
        """sbs_map_sanity_check should return 0 code for a valid-class map."""
        status, msg = sbs_map_sanity_check(os.path.join(_datadir, 'Cayumanque_fire_burn_severity3.tif'))
        self.assertEqual(status, 0)
        self.assertEqual(msg, 'Map has valid classes')

    def test_sanity_too_many_classes(self):
        """sbs_map_sanity_check should flag maps with >256 classes."""
        status, msg = sbs_map_sanity_check(os.path.join(_datadir, 'SBS.tif'))
        self.assertEqual(status, 1)
        self.assertEqual(msg, 'Map has more than 256 classes')

if __name__ == '__main__':
    unittest.main(verbosity=2)
    