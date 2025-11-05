"""
Comprehensive pytest test suite for classify() and ct_classify() functions.

Tests ensure sensical classification across all variations and edge cases:
- Standard 4-class breaks
- BARC-style breaks (0-255 range)
- Non-sequential pixel values
- Nodata handling
- Color table classification
- Edge cases (empty breaks, single break, negative values, large values)
"""

import pytest
import numpy as np
from wepppy.nodb.mods.baer.sbs_map import classify, ct_classify


class TestClassifyStandardBreaks:
    """Test classify() with standard 4-class breaks [0, 1, 2, 3]."""
    
    def test_sequential_values_no_offset(self):
        """Test classification without offset (for export_4class_map)."""
        breaks = [0, 1, 2, 3]
        
        assert classify(0, breaks) == 0
        assert classify(1, breaks) == 1
        assert classify(2, breaks) == 2
        assert classify(3, breaks) == 3
        assert classify(4, breaks) == 3  # Beyond last break
        
    def test_sequential_values_with_offset(self):
        """Test classification with offset=130 (standard burn classes)."""
        breaks = [0, 1, 2, 3]
        offset = 130
        
        assert classify(0, breaks, offset=offset) == 130  # unburned
        assert classify(1, breaks, offset=offset) == 131  # low
        assert classify(2, breaks, offset=offset) == 132  # moderate
        assert classify(3, breaks, offset=offset) == 133  # high
        assert classify(4, breaks, offset=offset) == 133  # beyond breaks -> high
        
    def test_values_between_breaks(self):
        """Test that values between breaks map to correct class."""
        breaks = [0, 10, 20, 30]
        offset = 130
        
        # Values <= first break
        assert classify(0, breaks, offset=offset) == 130
        assert classify(-5, breaks, offset=offset) == 130
        
        # Values in second class
        assert classify(1, breaks, offset=offset) == 131
        assert classify(5, breaks, offset=offset) == 131
        assert classify(10, breaks, offset=offset) == 131
        
        # Values in third class
        assert classify(11, breaks, offset=offset) == 132
        assert classify(15, breaks, offset=offset) == 132
        assert classify(20, breaks, offset=offset) == 132
        
        # Values in fourth class
        assert classify(21, breaks, offset=offset) == 133
        assert classify(30, breaks, offset=offset) == 133
        
        # Beyond all breaks
        assert classify(31, breaks, offset=offset) == 133
        assert classify(100, breaks, offset=offset) == 133


class TestClassifyBARCStyle:
    """Test classify() with BARC-style breaks [0, 75, 109, 187]."""
    
    def test_barc_boundaries(self):
        """Test classification at BARC break boundaries."""
        breaks = [0, 75, 109, 187]
        offset = 130
        
        # Unburned (0)
        assert classify(0, breaks, offset=offset) == 130
        
        # Low (1-75)
        assert classify(1, breaks, offset=offset) == 131
        assert classify(37, breaks, offset=offset) == 131
        assert classify(75, breaks, offset=offset) == 131
        
        # Moderate (76-109)
        assert classify(76, breaks, offset=offset) == 132
        assert classify(90, breaks, offset=offset) == 132
        assert classify(109, breaks, offset=offset) == 132
        
        # High (110-187+)
        assert classify(110, breaks, offset=offset) == 133
        assert classify(150, breaks, offset=offset) == 133
        assert classify(187, breaks, offset=offset) == 133
        assert classify(188, breaks, offset=offset) == 133
        assert classify(255, breaks, offset=offset) == 133
        
    def test_barc_full_range(self):
        """Test classification across full 0-255 range."""
        breaks = [0, 75, 109, 187]
        offset = 130
        
        # Test every value from 0 to 255
        for val in range(256):
            result = classify(val, breaks, offset=offset)
            
            if val <= 0:
                expected = 130
            elif val <= 75:
                expected = 131
            elif val <= 109:
                expected = 132
            else:
                expected = 133
                
            assert result == expected, f"Value {val}: expected {expected}, got {result}"


class TestClassifyNonSequential:
    """Test classify() with non-sequential pixel values."""
    
    def test_non_sequential_breaks(self):
        """Test with breaks inferred from [0, 1, 3] → [-2, -1, 0, 1]."""
        breaks = [-2, -1, 0, 1]
        offset = 130
        
        # Values at and below breaks
        assert classify(-3, breaks, offset=offset) == 130  # Below first break
        assert classify(-2, breaks, offset=offset) == 130  # At first break
        assert classify(-1, breaks, offset=offset) == 131  # At second break
        assert classify(0, breaks, offset=offset) == 132   # At third break
        assert classify(1, breaks, offset=offset) == 133   # At fourth break
        
        # Values beyond breaks
        assert classify(2, breaks, offset=offset) == 133
        assert classify(3, breaks, offset=offset) == 133
        assert classify(10, breaks, offset=offset) == 133


class TestClassifyNodata:
    """Test classify() nodata handling."""
    
    def test_nodata_returns_offset(self):
        """Test that nodata values return offset (unburned)."""
        breaks = [0, 1, 2, 3]
        offset = 130
        nodata_vals = [255]
        
        # Nodata value should return offset
        result = classify(255, breaks, nodata_vals=nodata_vals, offset=offset)
        assert result == 130, f"Nodata should return offset (130), got {result}"
        
        # Regular values should still classify normally
        assert classify(0, breaks, nodata_vals=nodata_vals, offset=offset) == 130
        assert classify(1, breaks, nodata_vals=nodata_vals, offset=offset) == 131
        assert classify(2, breaks, nodata_vals=nodata_vals, offset=offset) == 132
        assert classify(3, breaks, nodata_vals=nodata_vals, offset=offset) == 133
        
    def test_multiple_nodata_values(self):
        """Test with multiple nodata values."""
        breaks = [0, 1, 2, 3]
        offset = 130
        nodata_vals = [254, 255]
        
        assert classify(254, breaks, nodata_vals=nodata_vals, offset=offset) == 130
        assert classify(255, breaks, nodata_vals=nodata_vals, offset=offset) == 130
        
        # Regular value
        assert classify(1, breaks, nodata_vals=nodata_vals, offset=offset) == 131
        
    def test_nodata_with_zero_offset(self):
        """Test nodata with zero offset (for export_4class_map)."""
        breaks = [0, 1, 2, 3]
        nodata_vals = [255]
        
        # Nodata should return 0 (offset)
        assert classify(255, breaks, nodata_vals=nodata_vals, offset=0) == 0


class TestClassifyEdgeCases:
    """Test classify() edge cases."""
    
    def test_single_break(self):
        """Test with single break point."""
        breaks = [2]
        offset = 130
        
        # All values <= 2 go to index 0
        assert classify(0, breaks, offset=offset) == 130
        assert classify(1, breaks, offset=offset) == 130
        assert classify(2, breaks, offset=offset) == 130
        
        # All values > 2 also go to index 0 (last index)
        assert classify(3, breaks, offset=offset) == 130
        assert classify(10, breaks, offset=offset) == 130
        
    def test_empty_breaks(self):
        """Test with empty breaks list."""
        breaks = []
        offset = 130
        
        # All values return offset (index 0)
        assert classify(0, breaks, offset=offset) == 130
        assert classify(5, breaks, offset=offset) == 130
        assert classify(255, breaks, offset=offset) == 130
        
    def test_negative_values(self):
        """Test with negative pixel values."""
        breaks = [0, 75, 109, 187]
        offset = 130
        
        # Negative values should map to first class
        assert classify(-1, breaks, offset=offset) == 130
        assert classify(-10, breaks, offset=offset) == 130
        assert classify(-255, breaks, offset=offset) == 130
        
    def test_very_large_values(self):
        """Test with values beyond uint8 range."""
        breaks = [0, 75, 109, 187]
        offset = 130
        
        # Large values beyond breaks
        assert classify(500, breaks, offset=offset) == 133
        assert classify(1000, breaks, offset=offset) == 133
        assert classify(65535, breaks, offset=offset) == 133


class TestCtClassifyBasic:
    """Test ct_classify() basic functionality."""
    
    def test_standard_color_table(self):
        """Test with standard color table mapping."""
        ct = {
            'unburned': [0],
            'low': [1],
            'mod': [2],
            'high': [3]
        }
        
        # Without offset
        assert ct_classify(0, ct) == 0
        assert ct_classify(1, ct) == 1
        assert ct_classify(2, ct) == 2
        assert ct_classify(3, ct) == 3
        
        # With offset
        offset = 130
        assert ct_classify(0, ct, offset=offset) == 130
        assert ct_classify(1, ct, offset=offset) == 131
        assert ct_classify(2, ct, offset=offset) == 132
        assert ct_classify(3, ct, offset=offset) == 133
        
    def test_multiple_pixels_per_class(self):
        """Test color table with multiple pixels per severity class."""
        ct = {
            'unburned': [0, 10, 20],
            'low': [1, 11, 21],
            'mod': [2, 12, 22],
            'high': [3, 13, 23]
        }
        offset = 130
        
        # Test all unburned pixels
        assert ct_classify(0, ct, offset=offset) == 130
        assert ct_classify(10, ct, offset=offset) == 130
        assert ct_classify(20, ct, offset=offset) == 130
        
        # Test all low pixels
        assert ct_classify(1, ct, offset=offset) == 131
        assert ct_classify(11, ct, offset=offset) == 131
        assert ct_classify(21, ct, offset=offset) == 131
        
        # Test all mod pixels
        assert ct_classify(2, ct, offset=offset) == 132
        assert ct_classify(12, ct, offset=offset) == 132
        assert ct_classify(22, ct, offset=offset) == 132
        
        # Test all high pixels
        assert ct_classify(3, ct, offset=offset) == 133
        assert ct_classify(13, ct, offset=offset) == 133
        assert ct_classify(23, ct, offset=offset) == 133


class TestCtClassifyNodata:
    """Test ct_classify() nodata handling."""
    
    def test_nodata_returns_offset(self):
        """Test that nodata values return offset."""
        ct = {
            'unburned': [0],
            'low': [1],
            'mod': [2],
            'high': [3]
        }
        offset = 130
        nodata_vals = [255]
        
        # Nodata should return offset (130)
        result = ct_classify(255, ct, offset=offset, nodata_vals=nodata_vals)
        assert result == 130, f"Nodata should return offset (130), got {result}"
        
        # Regular values should still work
        assert ct_classify(1, ct, offset=offset, nodata_vals=nodata_vals) == 131
        assert ct_classify(2, ct, offset=offset, nodata_vals=nodata_vals) == 132
        
    def test_unknown_color_returns_255(self):
        """Test that unknown colors (not in ct, not in nodata) return 255."""
        ct = {
            'unburned': [0],
            'low': [1],
            'mod': [2],
            'high': [3]
        }
        offset = 130
        
        # Unknown pixel values return 255
        assert ct_classify(99, ct, offset=offset) == 255
        assert ct_classify(100, ct, offset=offset) == 255
        assert ct_classify(254, ct, offset=offset) == 255
        
    def test_nodata_vs_unknown(self):
        """Test distinction between nodata (→offset) and unknown (→255)."""
        ct = {
            'unburned': [0],
            'low': [1],
            'mod': [2],
            'high': [3]
        }
        offset = 130
        nodata_vals = [255]
        
        # Nodata returns offset
        assert ct_classify(255, ct, offset=offset, nodata_vals=nodata_vals) == 130
        
        # Unknown (not in ct, not in nodata) returns 255
        assert ct_classify(99, ct, offset=offset, nodata_vals=nodata_vals) == 255
        assert ct_classify(254, ct, offset=offset, nodata_vals=nodata_vals) == 255


class TestClassifyCtClassifyConsistency:
    """Test that classify() and ct_classify() produce consistent results."""
    
    def test_same_output_for_sequential_values(self):
        """Test both methods produce same output for sequential 0-3 values."""
        breaks = [0, 1, 2, 3]
        ct = {
            'unburned': [0],
            'low': [1],
            'mod': [2],
            'high': [3]
        }
        offset = 130
        
        for val in [0, 1, 2, 3]:
            result_breaks = classify(val, breaks, offset=offset)
            result_ct = ct_classify(val, ct, offset=offset)
            assert result_breaks == result_ct, \
                f"Value {val}: classify={result_breaks}, ct_classify={result_ct}"
                
    def test_nodata_consistency(self):
        """Test both methods handle nodata consistently."""
        breaks = [0, 1, 2, 3]
        ct = {
            'unburned': [0],
            'low': [1],
            'mod': [2],
            'high': [3]
        }
        offset = 130
        nodata_vals = [255]
        
        # Both should return offset for nodata
        result_breaks = classify(255, breaks, nodata_vals=nodata_vals, offset=offset)
        result_ct = ct_classify(255, ct, offset=offset, nodata_vals=nodata_vals)
        
        assert result_breaks == 130
        assert result_ct == 130
        assert result_breaks == result_ct


class TestClassifyRealWorldScenarios:
    """Test real-world SBS classification scenarios."""
    
    def test_uniform_low_severity(self):
        """Test uniform low severity map (pixel value 1)."""
        breaks = [0, 1, 2, 3]
        offset = 130
        
        # Pixel value 1 should map to low (131)
        assert classify(1, breaks, offset=offset) == 131
        
    def test_uniform_moderate_severity(self):
        """Test uniform moderate severity map (pixel value 2)."""
        breaks = [0, 1, 2, 3]
        offset = 130
        
        # Pixel value 2 should map to moderate (132)
        assert classify(2, breaks, offset=offset) == 132
        
    def test_uniform_high_severity(self):
        """Test uniform high severity map (pixel value 3)."""
        breaks = [0, 1, 2, 3]
        offset = 130
        
        # Pixel value 3 should map to high (133)
        assert classify(3, breaks, offset=offset) == 133
        
    def test_baer_style_map(self):
        """Test BAER-style continuous severity map."""
        breaks = [0, 75, 109, 187]
        offset = 130
        
        # Sample BAER values
        test_cases = [
            (0, 130, "unburned"),
            (30, 131, "low severity"),
            (75, 131, "low boundary"),
            (90, 132, "moderate severity"),
            (109, 132, "moderate boundary"),
            (150, 133, "high severity"),
            (187, 133, "high boundary"),
            (200, 133, "beyond high"),
        ]
        
        for value, expected, description in test_cases:
            result = classify(value, breaks, offset=offset)
            assert result == expected, f"{description}: value={value}, expected={expected}, got={result}"
            
    def test_map_with_nodata_regions(self):
        """Test map with nodata regions (e.g., outside watershed)."""
        breaks = [0, 1, 2, 3]
        offset = 130
        nodata_vals = [255]
        
        # Regular pixels
        assert classify(0, breaks, nodata_vals=nodata_vals, offset=offset) == 130
        assert classify(1, breaks, nodata_vals=nodata_vals, offset=offset) == 131
        assert classify(2, breaks, nodata_vals=nodata_vals, offset=offset) == 132
        assert classify(3, breaks, nodata_vals=nodata_vals, offset=offset) == 133
        
        # Nodata pixels (outside watershed)
        assert classify(255, breaks, nodata_vals=nodata_vals, offset=offset) == 130


class TestClassifyArrayOperations:
    """Test classify() works correctly when applied to arrays."""
    
    def test_classify_numpy_array(self):
        """Test classification of numpy array values."""
        breaks = [0, 1, 2, 3]
        offset = 130
        
        # Create test array
        values = np.array([0, 1, 2, 3, 4])
        expected = np.array([130, 131, 132, 133, 133])
        
        # Apply classify to each value
        results = np.array([classify(v, breaks, offset=offset) for v in values])
        
        np.testing.assert_array_equal(results, expected)
        
    def test_classify_with_nodata_in_array(self):
        """Test classification of array with nodata values."""
        breaks = [0, 1, 2, 3]
        offset = 130
        nodata_vals = [255]
        
        # Array with mixed values and nodata
        values = np.array([0, 1, 255, 2, 255, 3])
        expected = np.array([130, 131, 130, 132, 130, 133])  # nodata → 130
        
        results = np.array([classify(v, breaks, nodata_vals=nodata_vals, offset=offset) 
                           for v in values])
        
        np.testing.assert_array_equal(results, expected)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
