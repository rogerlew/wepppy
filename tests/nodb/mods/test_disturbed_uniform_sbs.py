"""
Test suite for uniform SBS map generation and color table preservation.

This module tests that:
1. Uniform SBS maps are created with correct pixel values (131, 132, 133)
2. Color tables are preserved during raster cropping/warping
3. Burn class assignment works correctly for all severity levels
"""

import os
import pytest
import numpy as np
import rasterio
from osgeo import gdal

from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.core import Ron, Watershed
from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap, get_sbs_color_table
from wepppy.all_your_base.geo import raster_stacker


# Use an existing test run directory for integration tests
TEST_RUN_DIR = '/wc1/runs/le/legato-alkalinity'


@pytest.fixture
def disturbed_instance():
    """Create a Disturbed instance for testing using an existing run."""
    if not os.path.exists(TEST_RUN_DIR):
        pytest.skip(f"Test run directory {TEST_RUN_DIR} not found")
    
    disturbed = Disturbed.getInstance(TEST_RUN_DIR)
    yield disturbed
    # Cleanup: Clear singleton but don't delete files
    Disturbed._instances.clear()


@pytest.mark.nodb
@pytest.mark.integration
class TestUniformSBSGeneration:
    """Test uniform SBS raster generation."""
    
    @pytest.mark.parametrize("severity_value,expected_pixel", [
        (1, 1),  # low severity - pixel value 1, color table maps to 131
        (2, 2),  # moderate severity - pixel value 2, color table maps to 132
        (3, 3),  # high severity - pixel value 3, color table maps to 133
    ])
    def test_uniform_sbs_pixel_values(self, disturbed_instance, severity_value, expected_pixel):
        """Test that uniform SBS rasters use pixel values 1, 2, 3."""
        sbs_fn = disturbed_instance.build_uniform_sbs(value=severity_value)
        
        # Check pixel values in raster
        with rasterio.open(sbs_fn) as src:
            data = src.read(1)
            unique_vals = np.unique(data)
        
        assert len(unique_vals) == 1, f"Expected single pixel value, got {unique_vals}"
        assert unique_vals[0] == expected_pixel, \
            f"Expected pixel value {expected_pixel} for severity {severity_value}, got {unique_vals[0]}"
    
    @pytest.mark.parametrize("severity_value,expected_color", [
        (1, (127, 255, 212, 255)),  # low - aquamarine
        (2, (255, 255, 0, 255)),    # moderate - yellow
        (3, (255, 0, 0, 255)),       # high - red
    ])
    def test_uniform_sbs_color_table(self, disturbed_instance, severity_value, expected_color):
        """Test that uniform SBS rasters have correct color table entries."""
        sbs_fn = disturbed_instance.build_uniform_sbs(value=severity_value)
        
        # Check color table - color table maps pixel values 1, 2, 3 to colors
        ds = gdal.Open(sbs_fn, gdal.GA_ReadOnly)
        band = ds.GetRasterBand(1)
        ct = band.GetRasterColorTable()
        
        assert ct is not None, "Color table should exist"
        
        # Check the pixel value that was written (1, 2, or 3)
        actual_color = ct.GetColorEntry(severity_value)
        
        assert actual_color == expected_color, \
            f"Expected color {expected_color} for pixel value {severity_value}, got {actual_color}"
        
        band = None
        ds = None
    
    def test_uniform_sbs_all_standard_colors(self, disturbed_instance):
        """Test that uniform SBS includes all standard SBS color table entries."""
        sbs_fn = disturbed_instance.build_uniform_sbs(value=1)
        
        ds = gdal.Open(sbs_fn, gdal.GA_ReadOnly)
        band = ds.GetRasterBand(1)
        ct = band.GetRasterColorTable()
        
        # Color table maps pixel values 0-3 to standard SBS colors:
        # 0 = unburned, 1 = low, 2 = moderate, 3 = high, 255 = nodata
        expected_entries = {
            0: (0, 100, 0, 255),       # unburned - dark green
            1: (127, 255, 212, 255),   # low - aquamarine
            2: (255, 255, 0, 255),     # moderate - yellow
            3: (255, 0, 0, 255),       # high - red
            255: (255, 255, 255, 0),   # nodata - transparent white
        }
        
        for pixel_val, expected_color in expected_entries.items():
            actual_color = ct.GetColorEntry(pixel_val)
            assert actual_color == expected_color, \
                f"Pixel {pixel_val}: expected {expected_color}, got {actual_color}"
        
        band = None
        ds = None


@pytest.mark.nodb
@pytest.mark.integration
class TestColorTablePreservation:
    """Test that color tables are preserved during raster operations."""
    
    def test_raster_stacker_preserves_color_table(self, tmp_path, disturbed_instance):
        """Test that raster_stacker preserves color tables from source raster."""
        # Create uniform SBS with color table
        sbs_fn = disturbed_instance.build_uniform_sbs(value=1)
        
        # Get DEM to use as match raster
        ron = Ron.getInstance(disturbed_instance.wd)
        dem_fn = ron.dem_fn
        
        # Crop/warp the SBS to match DEM grid
        cropped_fn = os.path.join(tmp_path, 'cropped.tif')
        raster_stacker(sbs_fn, dem_fn, cropped_fn, resample='near')
        
        # Check that color table was preserved
        ct_src, _, _ = get_sbs_color_table(sbs_fn)
        ct_dst, _, _ = get_sbs_color_table(cropped_fn)
        
        assert ct_src is not None, "Source should have color table"
        assert ct_dst is not None, "Cropped raster should preserve color table"
        
        # Verify color table contents are the same
        assert ct_src == ct_dst, "Color table should be identical after cropping"
    
    def test_get_sbs_preserves_color_table(self, disturbed_instance):
        """Test that Disturbed.get_sbs() preserves color table through cropping."""
        # Create and validate uniform SBS
        sbs_fn = disturbed_instance.build_uniform_sbs(value=2)  # moderate
        disturbed_instance.validate(sbs_fn, mode=1, uniform_severity=2)
        
        # Get SBS through the normal flow (which crops the raster)
        sbs = disturbed_instance.get_sbs()
        
        # Check that SBS has color table
        assert sbs.ct is not None, "SBS should have color table after get_sbs()"
        
        # Verify the cropped file has color table
        cropped_fn = disturbed_instance.disturbed_cropped
        ct, _, _ = get_sbs_color_table(cropped_fn)
        assert ct is not None, "Cropped raster should have color table"


@pytest.mark.nodb
@pytest.mark.integration
class TestBurnClassAssignment:
    """Test that burn classes are correctly assigned based on SBS pixel values."""
    
    @pytest.mark.parametrize("severity_value,expected_burn_class", [
        (1, '131'),  # low
        (2, '132'),  # moderate
        (3, '133'),  # high
    ])
    def test_class_pixel_map_correct(self, disturbed_instance, severity_value, expected_burn_class):
        """Test that uniform SBS rasters classify to correct burn class via class_pixel_map."""
        sbs_fn = disturbed_instance.build_uniform_sbs(value=severity_value)
        
        # Get the SBS map and check classification
        sbs_map = disturbed_instance.get_sbs()
        class_pixel_map = sbs_map.class_pixel_map
        
        # The pixel value written is severity_value (1, 2, or 3)
        # After ct_classify with offset 130, it should map to burn class codes
        pixel_str = str(severity_value)
        assert pixel_str in class_pixel_map, \
            f"Pixel value '{pixel_str}' should be in class_pixel_map, got {class_pixel_map}"
        
        actual_burn_class = class_pixel_map[pixel_str]
        assert actual_burn_class == expected_burn_class, \
            f"Expected burn class {expected_burn_class} for pixel {pixel_str}, got {actual_burn_class}"
    
    def test_uniform_low_not_assigned_high(self, disturbed_instance):
        """Regression test: uniform low severity should not be assigned high severity."""
        # This was the original bug - uniform low (value=1, pixel=1) was 
        # being mapped to burn class 133 (high) instead of 131 (low)
        # The color table now correctly maps pixel 1 -> 'low' -> 131
        
        sbs_fn = disturbed_instance.build_uniform_sbs(value=1)
        disturbed_instance.validate(sbs_fn, mode=1, uniform_severity=1)
        
        sbs = disturbed_instance.get_sbs()
        class_pixel_map = sbs.class_pixel_map
        
        # Should map 1 -> 131, NOT 1 -> 133
        assert '1' in class_pixel_map, "Pixel value 1 should be in map"
        assert class_pixel_map['1'] == '131', \
            f"Low severity (pixel 1) incorrectly mapped to {class_pixel_map['1']}, expected 131"
        assert class_pixel_map['1'] != '133', \
            "Low severity should not map to high severity (regression)"
    
    def test_uniform_moderate_not_assigned_high(self, disturbed_instance):
        """Regression test: uniform moderate severity should not be assigned high severity."""
        sbs_fn = disturbed_instance.build_uniform_sbs(value=2)
        disturbed_instance.validate(sbs_fn, mode=1, uniform_severity=2)
        
        sbs = disturbed_instance.get_sbs()
        class_pixel_map = sbs.class_pixel_map
        
        # Should map 2 -> 132, NOT 2 -> 133
        assert '2' in class_pixel_map, "Pixel value 2 should be in map"
        assert class_pixel_map['2'] == '132', \
            f"Moderate severity (pixel 2) incorrectly mapped to {class_pixel_map['2']}, expected 132"
        assert class_pixel_map['2'] != '133', \
            "Moderate severity should not map to high severity (regression)"


@pytest.mark.nodb
@pytest.mark.integration
class TestSBSModeAndUniformSeverity:
    """Test that sbs_mode and uniform_severity properties are set correctly."""
    
    def test_sbs_mode_set_to_uniform(self, disturbed_instance):
        """Test that building uniform SBS sets sbs_mode to 1."""
        disturbed_instance.build_uniform_sbs(value=1)
        assert disturbed_instance.sbs_mode == 1, "sbs_mode should be 1 for uniform SBS"
    
    @pytest.mark.parametrize("severity_value", [1, 2, 3])
    def test_uniform_severity_set_correctly(self, disturbed_instance, severity_value):
        """Test that uniform_severity property is set to the correct value."""
        disturbed_instance.build_uniform_sbs(value=severity_value)
        assert disturbed_instance.uniform_severity == severity_value, \
            f"uniform_severity should be {severity_value}"
    
    def test_validate_preserves_mode_and_severity(self, disturbed_instance):
        """Test that validate() preserves mode and uniform_severity."""
        severity_value = 2
        sbs_fn = disturbed_instance.build_uniform_sbs(value=severity_value)
        disturbed_instance.validate(sbs_fn, mode=1, uniform_severity=severity_value)
        
        assert disturbed_instance.sbs_mode == 1
        assert disturbed_instance.uniform_severity == severity_value
