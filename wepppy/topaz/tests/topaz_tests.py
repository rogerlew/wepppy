# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import join as _join
from os.path import exists as _exists
import shutil
import sys
import unittest

from osgeo import gdal, osr

from wepppy.all_your_base import get_utm_zone
from wepppy.topaz import TopazRunner

gdal.UseExceptions()


class Test_get_utm_zone(unittest.TestCase):
    def test_01(self):
        """
        dataset from California
        """
        ds = gdal.Open('dems/ned1_2016_lg.tif')
        srs = osr.SpatialReference()
        srs.ImportFromWkt(ds.GetProjectionRef())
        utm = get_utm_zone(srs)
        self.assertEqual(utm, 10)

    def test_02(self):
        """
        dataset from Idaho
        """
        ds = gdal.Open('dems/ned1_2016.tif')
        srs = osr.SpatialReference()
        srs.ImportFromWkt(ds.GetProjectionRef())
        utm = get_utm_zone(srs)
        self.assertEqual(utm, 11)

    def test_03(self):
        """
        utm dataset representing New York
        """
        ds = gdal.Open('dems/ned1_2016_ny.tif')
        srs = osr.SpatialReference()
        srs.ImportFromWkt(ds.GetProjectionRef())
        utm = get_utm_zone(srs)
        self.assertEqual(utm, 17)

    def test_04(self):
        """
        non-utm dataset should return None
        """
        ds = gdal.Open('dems/nonutm.tif')
        srs = osr.SpatialReference()
        srs.ImportFromWkt(ds.GetProjectionRef())
        utm = get_utm_zone(srs)
        self.assertEqual(utm, None)

    def test_05(self):
        """
        can only hand an osr.SpatialReference object
        """
        with self.assertRaises(TypeError):
            utm = get_utm_zone('')


class Test_topaz01(unittest.TestCase):
    def setUp(self):
        if _exists('wd'):
            shutil.rmtree('wd')

        os.mkdir('wd')

    def test_init(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        self.assertEqual(top.cellsize, 30.0)
        self.assertEqual(top.ul_x,  504090)
        self.assertEqual(top.ul_y, 5185161)
        self.assertEqual(top.lr_x,  506700)
        self.assertEqual(top.lr_y, 5180991)
        self.assertEqual(top.num_cols, 87)
        self.assertEqual(top.num_rows, 139)
        self.assertEqual(top.utm_zone, 11)


class Test_topaz02(unittest.TestCase):
    def setUp(self):
        if _exists('wd'):
            shutil.rmtree('wd')

        os.mkdir('wd')

    def test_create_dednm_input(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top._create_dednm_input()

        with open('wd/DEDNM.INP') as fp:
            d = fp.readlines()

        with open('verify/DEDNM.INP') as fp:
            v = fp.readlines()

        for _d, _v in zip(d, v):
            self.assertEqual(_d, _v)


class Test_topaz03(unittest.TestCase):
    def setUp(self):
        if _exists('wd'):
            shutil.rmtree('wd')

        os.mkdir('wd')

    def test_dnmcnt_input(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.csa = 4
        top.mcl = 60
        top._create_dnmcnt_input(1)

        with open('wd/DNMCNT.INP') as fp:
            d = fp.readlines()

        with open('verify/DNMCNT.INP') as fp:
            v = fp.readlines()

        for _d, _v in zip(d, v):
            self.assertEqual(_d, _v)


class Test_topaz04(unittest.TestCase):
    def setUp(self):
        if _exists('wd'):
            shutil.rmtree('wd')

        os.mkdir('wd')

    def test_prep_dir(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top._prep_dir()

        self.assertTrue(_exists('wd/dednm'))
        self.assertTrue(_exists('wd/rasbin'))
        self.assertTrue(_exists('wd/raspro'))
        self.assertTrue(_exists('wd/rasfor'))

        self.assertEqual(33261, os.stat('wd/dednm').st_mode)
        self.assertEqual(33261, os.stat('wd/rasbin').st_mode)
        self.assertEqual(33261, os.stat('wd/raspro').st_mode)
        self.assertEqual(33261, os.stat('wd/rasfor').st_mode)

        self.assertTrue(_exists('wd/RASFOR.INP'))
        self.assertTrue(_exists('wd/RASPRO.INP'))


class Test_topaz05(unittest.TestCase):
    def setUp(self):
        if _exists('wd'):
            shutil.rmtree('wd')

        os.mkdir('wd')

    def test_build_channels(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()

        self.assertTrue(_exists('wd/NETFUL.ARC'))
        self.assertTrue(_exists('wd/FLOPAT.ARC'))
        self.assertTrue(_exists('wd/FLOVEC.ARC'))
        self.assertTrue(_exists('wd/NETFUL.ARC'))
        self.assertTrue(_exists('wd/RELIEF.ARC'))

        # verify NETFUL
        # verify projection
        with open('wd/NETFUL.ARC') as fp:
            d = fp.readlines()

        with open('verify/NETFUL.ARC.1') as fp:
            v = fp.readlines()

        for _d, _v in zip(d, v):
            self.assertEqual(_d, _v)

        # verify projection
        with open('wd/NETFUL.PRJ') as fp:
            d = fp.readlines()

        with open('verify/NETFUL.PRJ.1') as fp:
            v = fp.readlines()

        for _d, _v in zip(d, v):
            self.assertEqual(_d, _v)


class Test_topaz06(unittest.TestCase):
    def setUp(self):
        if _exists('wd'):
            shutil.rmtree('wd')

        os.mkdir('wd')

    def test_longlat_to_pixel01(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        lng = -( 116.0 +  55.0 / 60.0 + 45.50/3600.0)
        lat = 46.0 +  48.0 / 60.0 + 4.37/3600.0

        x, y = top.longlat_to_pixel(lng,lat)

        self.assertEqual(x, 43)
        self.assertEqual(y, 69)

    def test_longlat_to_pixel02(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        lng = -120.0
        lat = 20.0

        with self.assertRaises(AssertionError):
            x, y = top.longlat_to_pixel(lng,lat)

    def test_longlat_to_pixel03(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')

        x, y = top.longlat_to_pixel(-116.9310440300905, 46.81997312092958)

        self.assertEqual(x, 39)
        self.assertEqual(y, 0)


class Test_topaz07(unittest.TestCase):
    def setUp(self):
        if _exists('wd'):
            shutil.rmtree('wd')

        os.mkdir('wd')

    def test_pixel_to_utm01(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()

        x, y = top.pixel_to_utm(0, 0)
        self.assertEqual(x,  504090)
        self.assertEqual(y, 5185161)

    def test_pixel_to_utm02(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()

        x, y = top.pixel_to_utm(43, 70)
        self.assertEqual(x,  505380.0)
        self.assertEqual(y, 5183061.0)

    def test_pixel_to_utm03(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()

        x, y = top.pixel_to_utm(86, 138)
        self.assertEqual(x,  506670)
        self.assertEqual(y, 5181021)

    def test_pixel_to_utm04(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()

        with self.assertRaises(AssertionError):
            x, y = top.pixel_to_utm(86, 139)

    def test_pixel_to_utm05(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()

        with self.assertRaises(AssertionError):
            x, y = top.pixel_to_utm(87, 138)


class Test_topaz08(unittest.TestCase):
    def setUp(self):
        if _exists('wd'):
            shutil.rmtree('wd')

        os.mkdir('wd')

    def test_pixel_to_longlat01(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()

        x, y = top.pixel_to_longlat(0, 0)
        self.assertEqual(x,  -116.94638213722368)
        self.assertEqual(y, 46.819981333488265)

    def test_pixel_to_longlat02(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()

        x, y = top.pixel_to_longlat(43, 70)
        self.assertEqual(x,  -116.92949559048503)
        self.assertEqual(y, 46.80107414405755)

    def test_pixel_to_longlat03(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()

        x, y = top.pixel_to_longlat(86, 138)
        self.assertEqual(x,  -116.91261999321354)
        self.assertEqual(y, 46.78270435450583)

    def test_pixel_to_longlat04(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()

        x, y = top.pixel_to_longlat(39, 0)
        self.assertEqual(x,  -116.9310440300905)
        self.assertEqual(y, 46.81997312092958)


class Test_topaz09(unittest.TestCase):
    def setUp(self):
        if _exists('wd'):
            shutil.rmtree('wd')

        os.mkdir('wd')

    def test_find_closest_channel02(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()

        (x, y), distance = top.find_closest_channel(44, 38, pixelcoords=True)
        self.assertEqual(x, 44)
        self.assertEqual(y, 38)
        self.assertEqual(distance, 0)

    def test_find_closest_channel03(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()

        (x, y), distance = top.find_closest_channel(23, 47, pixelcoords=True)
        self.assertEqual(x, 21)
        self.assertEqual(y, 48)
        self.assertEqual(distance, 2.23606797749979)

    def test_find_closest_channel04(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()

        (x, y), distance = top.find_closest_channel(-116.9310440300905, 46.81997312092958)
        self.assertEqual(x, 39)
        self.assertEqual(y, 0)
        self.assertEqual(distance, 0)

    def test_chn_junction(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()
        (x, y), distance = top.find_closest_channel(-116.9310440300905, 46.81997312092958)

        self.assertTrue(_exists('wd/CHNJNT.ARC'))

        # verify CHNJNT
        with open('wd/CHNJNT.ARC') as fp:
            d = fp.readlines()

        with open('verify/CHNJNT.ARC.1') as fp:
            v = fp.readlines()

        for _d, _v in zip(d, v):
            self.assertEqual(_d, _v)


class Test_topaz10(unittest.TestCase):
    def setUp(self):
        if _exists('wd'):
            shutil.rmtree('wd')

        os.mkdir('wd')

    def test_build_subcatchments01(self):
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        top.build_channels()
        top.build_subcatchments([26, 5])

        self.assertTrue(_exists('wd/NETFUL.ARC'))
        self.assertTrue(_exists('wd/FLOPAT.ARC'))
        self.assertTrue(_exists('wd/FLOVEC.ARC'))
        self.assertTrue(_exists('wd/NETFUL.ARC'))
        self.assertTrue(_exists('wd/RELIEF.ARC'))

        # new from pass 2
        self.assertTrue(_exists('wd/BOUND.ARC'))
        self.assertTrue(_exists('wd/FLOPAT.ARC'))
        self.assertTrue(_exists('wd/FLOVEC.ARC'))
        self.assertTrue(_exists('wd/FVSLOP.ARC'))
        self.assertTrue(_exists('wd/NETW.ARC'))
        self.assertTrue(_exists('wd/SUBWTA.ARC'))

        # verify FVSLOP
        with open('wd/FVSLOP.ARC') as fp:
            d = fp.readlines()

        with open('verify/FVSLOP.ARC.2') as fp:
            v = fp.readlines()

        for _d, _v in zip(d, v):
            self.assertEqual(_d, _v)

        # verify SUBWTA
        with open('wd/SUBWTA.ARC') as fp:
            d = fp.readlines()

        with open('verify/SUBWTA.ARC.2') as fp:
            v = fp.readlines()

        for _d, _v in zip(d, v):
            self.assertEqual(_d, _v)

        # verify FLOPAT
        with open('wd/FLOPAT.ARC') as fp:
            d = fp.readlines()

        with open('verify/FLOPAT.ARC.2') as fp:
            v = fp.readlines()

        for _d, _v in zip(d, v):
            self.assertEqual(_d, _v)

    def test_build_subcatchments02(self):
        top = TopazRunner('wd', 'dems/ned1_2016_lg3.tif') # 512 x 512
        top.build_channels()

    def test_build_subcatchments11(self):
        """
        check to make sure it doesn't hang when watershed falls
        outside of boundary
        """
        top = TopazRunner('wd', 'dems/ned1_2016.tif')
        with self.assertRaises(Exception):
            top.build_subcatchments([50, 135])

## these take awhile
#    def test_build_subcatchments04(self):
#        top = TopazRunner('wd', 'dems/ned1_2016_lg4.tif') # 768 x 768
#        top.build_channels()
#
#    def test_build_subcatchments05(self):
#        top = TopazRunner('wd', 'dems/ned1_2016_lg2.tif') # 1024 x 1024
#        top.build_channels(csa=5, mcl=80)
#
#    def test_build_subcatchments06(self):
#        top = TopazRunner('wd', 'dems/ned1_2016_lg.tif') # 2042 x 2042
#        top.build_channels(csa=16, mcl=240)
#
#    def test_build_subcatchments10(self):
#        top = TopazRunner('wd', 'dems/ned1_2016_lg.tif') # 2048 x 2048, takes 70+ seconds
#
#        with self.assertRaises(Exception):
#            top.build_channels()


if __name__ == '__main__':
    unittest.main()