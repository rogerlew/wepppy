import unittest

class TestImports(unittest.TestCase):
    def test_import_numpy(self):
        import numpy

    def test_import_gdal(self):
        import osgeo.gdal

    def test_import_wepppy(self):
        import wepppy

    def test_all_your_base(self):
        from wepppy import all_your_base

    def test_import_wepppy_worker(self):
        from wepppy.rq import WepppyRqWorker

    def test_import_rosetta(self):
        import rosetta

    def test_import_wepp_runner(self):
        import wepp_runner

    def test_import_weppcloud2(self):
        import weppcloud2

    def test_f_esri(self):
        import f_esri

    def test_wepppyo3(self):
        import wepppyo3
    

if __name__ == '__main__':
    unittest.main()