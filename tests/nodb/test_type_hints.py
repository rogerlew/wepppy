"""
Tests to validate type hints in core NoDb modules.

This test file verifies that the type hints added to core modules
are syntactically correct and that the modules can be imported without errors.
"""

import sys
from typing import get_type_hints


def test_topaz_module_imports():
    """Test that topaz module can be imported with type hints."""
    from wepppy.nodb.core import topaz
    
    # Verify the module has the expected classes
    assert hasattr(topaz, 'Topaz')
    assert hasattr(topaz, 'Outlet')
    assert hasattr(topaz, 'TopazNoDbLockedException')
    
    # Test that we can get type hints from Topaz class
    # This will fail if type hints are malformed
    hints = get_type_hints(topaz.Topaz.__init__)
    assert 'wd' in hints
    assert 'cfg_fn' in hints


def test_ron_module_imports():
    """Test that ron module can be imported with type hints."""
    from wepppy.nodb.core import ron
    
    # Verify the module has the expected classes
    assert hasattr(ron, 'Ron')
    assert hasattr(ron, 'Map')
    assert hasattr(ron, 'RonViewModel')
    assert hasattr(ron, 'RonNoDbLockedException')
    
    # Test that we can get type hints from Map class
    hints = get_type_hints(ron.Map.__init__)
    assert 'extent' in hints
    assert 'center' in hints
    assert 'zoom' in hints


def test_landuse_module_imports():
    """Test that landuse module can be imported with type hints."""
    from wepppy.nodb.core import landuse
    
    # Verify the module has the expected classes
    assert hasattr(landuse, 'Landuse')
    assert hasattr(landuse, 'LanduseMode')
    assert hasattr(landuse, 'LanduseNoDbLockedException')
    assert hasattr(landuse, 'read_cover_defaults')
    
    # Test that we can get type hints from Landuse class
    hints = get_type_hints(landuse.Landuse.__init__)
    assert 'wd' in hints
    assert 'cfg_fn' in hints


def test_soils_module_imports():
    """Test that soils module can be imported with type hints."""
    from wepppy.nodb.core import soils
    
    # Verify the module has the expected classes
    assert hasattr(soils, 'Soils')
    assert hasattr(soils, 'SoilsMode')
    assert hasattr(soils, 'SoilsNoDbLockedException')
    
    # Test that we can get type hints from Soils class
    hints = get_type_hints(soils.Soils.__init__)
    assert 'wd' in hints
    assert 'cfg_fn' in hints


def test_all_modules_importable():
    """Test that all modified modules can be imported together."""
    from wepppy.nodb.core import (
        topaz,
        ron, 
        landuse,
        soils
    )
    
    # If we got here without exceptions, the imports succeeded
    assert True


if __name__ == '__main__':
    # Run tests manually
    print("Running type hints validation tests...")
    
    try:
        test_topaz_module_imports()
        print("✓ topaz module imports successfully")
    except Exception as e:
        print(f"✗ topaz module failed: {e}")
        sys.exit(1)
    
    try:
        test_ron_module_imports()
        print("✓ ron module imports successfully")
    except Exception as e:
        print(f"✗ ron module failed: {e}")
        sys.exit(1)
    
    try:
        test_landuse_module_imports()
        print("✓ landuse module imports successfully")
    except Exception as e:
        print(f"✗ landuse module failed: {e}")
        sys.exit(1)
    
    try:
        test_soils_module_imports()
        print("✓ soils module imports successfully")
    except Exception as e:
        print(f"✗ soils module failed: {e}")
        sys.exit(1)
    
    try:
        test_all_modules_importable()
        print("✓ All modules import successfully together")
    except Exception as e:
        print(f"✗ Combined imports failed: {e}")
        sys.exit(1)
    
    print("\n✅ All type hints validation tests passed!")
