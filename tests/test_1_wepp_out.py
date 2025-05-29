from wepppy.wepp.out import Element
import unittest

class TestWeppOut(unittest.TestCase):
    def test_wepp_out_element(self):
        """
        validates files with ****** on the frist line are read correctly
        """
        element_fn = '/workdir/wepppy/tests/wepp/out/H1.element.dat'
        ebe = Element(element_fn)
        self.assertIsInstance(ebe, Element)

    def test_wepp_out_element2(self):
        """
        validates files ****** past the first line are read correctly
        """
        element_fn = '/workdir/wepppy/tests/wepp/out/H2.element.dat'
        ebe = Element(element_fn)
        self.assertIsInstance(ebe, Element)

if __name__ == '__main__':
    unittest.main()