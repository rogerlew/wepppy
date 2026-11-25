import importlib
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

    def _import_optional(self, name):
        try:
            importlib.import_module(name)
        except ModuleNotFoundError as exc:
            if exc.name == name or exc.name == name.partition(".")[0]:
                self.skipTest(f"{exc.name} is unavailable in this environment")
            raise

    def test_import_rosetta(self):
        self._import_optional("rosetta")

    def test_import_wepp_runner(self):
        self._import_optional("wepp_runner")

    def test_import_weppcloud2(self):
        self._import_optional("weppcloud2")

    def test_wepppyo3(self):
        self._import_optional("wepppyo3")

    def test_wepppyo3_swat_utils(self):
        self._import_optional("wepppyo3.swat_utils")


if __name__ == '__main__':
    unittest.main(verbosity=2)
