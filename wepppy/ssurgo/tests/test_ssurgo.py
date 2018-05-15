import unittest

import os
from os.path import join as _join

_thisdir = os.path.dirname(__file__)


from wepppy.ssurgo import (
    query_mukeys_in_extent,
    SurgoSoilCollection,
    StatsgoSpatial
)


class Test_query_mukeys_in_extent(unittest.TestCase):
    def test_01(self):
        extent = [-116.05, 47.0, -116.0, 47.05]
        mukeys = query_mukeys_in_extent(extent)
        assert mukeys is not None

        v = [2396743, 2396746, 2396747, 2396748, 2396765, 2396774, 2396775, 2396776, 2396777, 2396851, 2396852,
             2396853, 2396855, 2396856, 2396857, 2396858, 2396860, 2396861, 2396863, 2396866, 2396867, 2397009,
             2397043, 2397044, 2397046, 2397047, 2397467, 2397468, 2397480, 2397482]

        for _v in v:
            assert _v in mukeys

    def test_02(self):
        extent = [-115.201226, 45.372097, -115.20, 45.373]

        mukeys = query_mukeys_in_extent(extent)

        for _v in [2518587]:
            assert _v in mukeys


class Test_SurgoSoilCollection(unittest.TestCase):
    def test_01(self):
        extent = [-116.05, 47.0, -116.0, 47.05]
        mukeys = query_mukeys_in_extent(extent)

        surgo_c = SurgoSoilCollection(mukeys)
        surgo_c.makeWeppSoils(verbose=True)
        valid = surgo_c.getValidWeppSoils()

        v = [2396866, 2396867, 2396743, 2396746, 2396747, 2396748, 2397009, 2397047, 2397044, 2397467, 2397468,
             2396765, 2396774, 2396775, 2397480, 2396777, 2397482, 2397043, 2396776, 2396851, 2396852, 2396853,
             2397046, 2396855, 2396856, 2396857, 2396858, 2396860, 2396861, 2396863]

        for _v in v:
            assert _v in mukeys

    def test_02(self):
        extent = [-115.201226, 45.372097, -115.20, 45.373]
        mukeys = query_mukeys_in_extent(extent)
        surgo_c = SurgoSoilCollection(mukeys)
        surgo_c.makeWeppSoils(verbose=True)
        valid = surgo_c.getValidWeppSoils()

        assert valid == []

    def test_03_min_depth(self):
        mukeys = [1652031]

        surgo_c = SurgoSoilCollection(mukeys)
        surgo_c.makeWeppSoils(verbose=True)

        surgo_c.writeWeppSoils(_join(_thisdir, 'testsoils'))


class Test_StatsgoSpatial_mukeys(unittest.TestCase):
    def test_01(self):
        statsgospatial = StatsgoSpatial()
        mukey = statsgospatial.identify_mukey_point(-115.201226, 45.372097)
        surgo_c = SurgoSoilCollection([mukey], use_statsgo=True)
        surgo_c.makeWeppSoils(verbose=True)
        surgo_c.writeWeppSoils(_join(_thisdir, 'testsoils'))
        valid = surgo_c.getValidWeppSoils()

        assert mukey == 661951, mukey
        assert valid == [661951], valid

    def test_02(self):
        statsgospatial = StatsgoSpatial()
        extent = [-115.201226, 45.372097, -115.20, 45.373]
        mukeys = statsgospatial.identify_mukeys_extent(extent)

        v = [661787, 661951, 661956]

        assert len(mukeys) == 3
        for _v in v:
            assert _v in mukeys

    def test_03(self):
        mukeys = StatsgoSpatial().mukeys
        assert len(mukeys) == 84000


if __name__ == '__main__':
    unittest.main()
