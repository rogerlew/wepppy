from wepppy.wepp.management import get_disturbed_classes, load_map, get_management_summary

import unittest

class TestWeppManagement(unittest.TestCase):
    def test_get_disturbed_classes(self):
        """
        validates files with ****** on the frist line are read correctly
        """
        clasess = get_disturbed_classes()
        
    def test_validate_disturbed_map(self):
        _map = None
        d = load_map(_map=_map)
    
        for k, v in d.items():
            man_sum = get_management_summary(k, _map)
            man = man_sum.get_management()
            
    def test_validate_eu_corrine_disturbed_map(self):
        _map = 'eu-disturbed'
        d = load_map(_map=_map)
    
        for k, v in d.items():
            man_sum = get_management_summary(k, _map)
            man = man_sum.get_management()

            
    def test_validate_c3s_disturbed_map(self):
        _map = 'c3s-disturbed'
        d = load_map(_map=_map)
    
        for k, v in d.items():
            man_sum = get_management_summary(k, _map)
            man = man_sum.get_management()
            
    def test_validate_au_disturbed_map(self):
        _map = 'au-disturbed'
        d = load_map(_map=_map)
    
        for k, v in d.items():
            man_sum = get_management_summary(k, _map)
            man = man_sum.get_management()
            
    def test_validate_revegetation_map(self):
        _map = 'revegetation'
        d = load_map(_map=_map)
    
        for k, v in d.items():
            man_sum = get_management_summary(k, _map)
            man = man_sum.get_management()
if __name__ == '__main__':
    unittest.main()