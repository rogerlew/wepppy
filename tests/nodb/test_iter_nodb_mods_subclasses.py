import unittest

from wepppy.nodb.base import iter_nodb_mods_subclasses
from wepppy.nodb.mods.disturbed.disturbed import Disturbed


class IterNoDbModsSubclassesTests(unittest.TestCase):
    def test_iterates_more_than_one_and_includes_disturbed(self):
        results = list(iter_nodb_mods_subclasses())

        self.assertGreater(len(results), 1)

        mapping = dict(results)
        self.assertIn('disturbed', mapping)
        self.assertIs(mapping['disturbed'], Disturbed)


if __name__ == '__main__':
    unittest.main()
