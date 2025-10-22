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
        try:
            import rosetta  # noqa: F401
        except ModuleNotFoundError:
            self.skipTest("rosetta package not installed in this environment")

    def test_import_wepp_runner(self):
        try:
            import wepp_runner  # noqa: F401
        except ModuleNotFoundError:
            self.skipTest("wepp_runner package not installed in this environment")

    def test_import_weppcloud2(self):
        try:
            import weppcloud2  # noqa: F401
        except ModuleNotFoundError:
            self.skipTest("weppcloud2 package not installed in this environment")

    def test_f_esri(self):
        try:
            import f_esri  # noqa: F401
        except ModuleNotFoundError:
            self.skipTest("f_esri package not installed in this environment")

    def test_f_esri_has_f_esri(self):
        from wepppy.all_your_base.geo import has_f_esri
        res = has_f_esri()
        self.assertTrue(res)

    def test_wepppyo3(self):
        try:
            import wepppyo3  # noqa: F401
        except ModuleNotFoundError:
            self.skipTest("wepppyo3 package not installed in this environment")
    

if __name__ == '__main__':
    unittest.main(verbosity=2)
    
