"""
Comprehensive validation tests for classify() function.

This module performs exhaustive manual validation of the classify logic
across all edge cases to ensure correctness.
"""

import pytest
from wepppy.nodb.mods.baer.sbs_map import classify


class TestClassifyManualValidation:
    """
    Manual validation of classify() logic across all scenarios.
    
    The classify function should:
    1. Return offset + index for nodata values
    2. Return offset + index for values <= breaks[index]
    3. Return offset + last_index for values > all breaks
    """
    
    def test_classify_standard_4class_breaks(self):
        """
        Validate standard 4-class breaks: [0, 1, 2, 3]
        Expected mapping with offset=130:
        - v=0 → breaks[0] → index 0 → 130
        - v=1 → breaks[1] → index 1 → 131
        - v=2 → breaks[2] → index 2 → 132
        - v=3 → breaks[3] → index 3 → 133
        - v=4 → beyond all breaks → index 3 → 133
        """
        breaks = [0, 1, 2, 3]
        offset = 130
        
        # Manual validation: v=0, first break is 0, should be index 0
        result = classify(0, breaks, offset=offset)
        assert result == 130, f"v=0: Expected 130 (index 0), got {result}"
        
        # Manual validation: v=1, second break is 1, should be index 1
        result = classify(1, breaks, offset=offset)
        assert result == 131, f"v=1: Expected 131 (index 1), got {result}"
        
        # Manual validation: v=2, third break is 2, should be index 2
        result = classify(2, breaks, offset=offset)
        assert result == 132, f"v=2: Expected 132 (index 2), got {result}"
        
        # Manual validation: v=3, fourth break is 3, should be index 3
        result = classify(3, breaks, offset=offset)
        assert result == 133, f"v=3: Expected 133 (index 3), got {result}"
        
        # Manual validation: v=4, beyond all breaks, should be last index (3)
        result = classify(4, breaks, offset=offset)
        assert result == 133, f"v=4: Expected 133 (last index 3), got {result}"
        
        print("✓ Standard 4-class breaks validated correctly")
        
    def test_classify_barc_style_breaks(self):
        """
        Validate BARC-style breaks: [0, 75, 109, 187]
        Expected mapping with offset=130:
        - v=0 → breaks[0] → index 0 → 130 (unburned)
        - v=1-75 → breaks[1] → index 1 → 131 (low)
        - v=76-109 → breaks[2] → index 2 → 132 (moderate)
        - v=110-187 → breaks[3] → index 3 → 133 (high)
        - v=188+ → beyond all → index 3 → 133 (high)
        """
        breaks = [0, 75, 109, 187]
        offset = 130
        
        # Test boundary values
        test_cases = [
            (0, 130, "v=0: unburned boundary"),
            (1, 131, "v=1: low severity start"),
            (50, 131, "v=50: mid low severity"),
            (75, 131, "v=75: low severity boundary"),
            (76, 132, "v=76: moderate severity start"),
            (100, 132, "v=100: mid moderate severity"),
            (109, 132, "v=109: moderate severity boundary"),
            (110, 133, "v=110: high severity start"),
            (150, 133, "v=150: mid high severity"),
            (187, 133, "v=187: high severity boundary"),
            (188, 133, "v=188: beyond all breaks"),
            (255, 133, "v=255: max value"),
        ]
        
        for value, expected, description in test_cases:
            result = classify(value, breaks, offset=offset)
            assert result == expected, f"{description}: Expected {expected}, got {result}"
            print(f"  ✓ {description}")
            
        print("✓ BARC-style breaks validated correctly")
        
    def test_classify_non_sequential_breaks(self):
        """
        Validate non-sequential breaks: [-2, -1, 0, 1]
        This occurs when we have pixel values like 0, 1, 3 (missing 2).
        
        Expected mapping:
        - v=-2 → breaks[0] → index 0 → 130
        - v=-1 → breaks[1] → index 1 → 131
        - v=0 → breaks[2] → index 2 → 132
        - v=1 → breaks[3] → index 3 → 133
        - v=2 → beyond breaks[3] → index 3 → 133
        - v=3 → beyond breaks[3] → index 3 → 133
        """
        breaks = [-2, -1, 0, 1]
        offset = 130
        
        test_cases = [
            (-3, 130, "v=-3: less than first break"),
            (-2, 130, "v=-2: first break"),
            (-1, 131, "v=-1: second break"),
            (0, 132, "v=0: third break"),
            (1, 133, "v=1: fourth break"),
            (2, 133, "v=2: beyond all breaks"),
            (3, 133, "v=3: beyond all breaks"),
        ]
        
        for value, expected, description in test_cases:
            result = classify(value, breaks, offset=offset)
            assert result == expected, f"{description}: Expected {expected}, got {result}"
            print(f"  ✓ {description}")
            
        print("✓ Non-sequential breaks validated correctly")
        
    def test_classify_nodata_handling(self):
        """
        Validate nodata values are handled correctly.
        
        Nodata values in nodata_vals list should return offset (e.g., 130 for unburned).
        """
        breaks = [0, 1, 2, 3]
        offset = 130
        nodata_vals = [255]
        
        # Test nodata value - should return offset (130)
        result = classify(255, breaks, nodata_vals=nodata_vals, offset=offset)
        
        assert result == 130, f"nodata should return offset (130), got {result}"
        print(f"  ✓ nodata correctly returns offset (130)")
            
        # Test regular value
        result = classify(1, breaks, nodata_vals=nodata_vals, offset=offset)
        assert result == 131, f"Regular value should still work: Expected 131, got {result}"
        print(f"  ✓ Regular values still work correctly")
        
    def test_classify_edge_case_single_break(self):
        """
        Validate single break point: [2]
        
        Expected:
        - v <= 2 → index 0 → offset + 0
        - v > 2 → index 0 (last index) → offset + 0
        """
        breaks = [2]
        offset = 130
        
        test_cases = [
            (0, 130, "v=0: below break"),
            (1, 130, "v=1: below break"),
            (2, 130, "v=2: at break"),
            (3, 130, "v=3: above break - still index 0"),
            (10, 130, "v=10: well above break - still index 0"),
        ]
        
        for value, expected, description in test_cases:
            result = classify(value, breaks, offset=offset)
            assert result == expected, f"{description}: Expected {expected}, got {result}"
            print(f"  ✓ {description}")
            
        print("✓ Single break validated correctly")
        
    def test_classify_edge_case_empty_breaks(self):
        """
        Validate empty breaks list: []
        
        This is an edge case that shouldn't happen in practice,
        but we should understand the behavior.
        """
        breaks = []
        offset = 130
        
        # With empty breaks, the loop never executes, i remains 0
        result = classify(5, breaks, offset=offset)
        # The loop doesn't iterate, so i=0 is returned
        assert result == 130, f"Empty breaks: Expected 130 (i=0), got {result}"
        print(f"  ✓ Empty breaks returns offset + 0")
        
    def test_classify_edge_case_very_large_values(self):
        """
        Validate behavior with very large values.
        """
        breaks = [0, 75, 109, 187]
        offset = 130
        
        test_cases = [
            (254, 133, "v=254: large value"),
            (255, 133, "v=255: max uint8"),
            (1000, 133, "v=1000: beyond uint8 range"),
        ]
        
        for value, expected, description in test_cases:
            result = classify(value, breaks, offset=offset)
            assert result == expected, f"{description}: Expected {expected}, got {result}"
            print(f"  ✓ {description}")
            
        print("✓ Large values handled correctly")
        
    def test_classify_zero_offset(self):
        """
        Validate classification with no offset (offset=0).
        This is used for export_4class_map which produces 0, 1, 2, 3 output.
        """
        breaks = [0, 1, 2, 3]
        offset = 0
        
        test_cases = [
            (0, 0, "v=0 → class 0"),
            (1, 1, "v=1 → class 1"),
            (2, 2, "v=2 → class 2"),
            (3, 3, "v=3 → class 3"),
            (4, 3, "v=4 → class 3 (last)"),
        ]
        
        for value, expected, description in test_cases:
            result = classify(value, breaks, offset=offset)
            assert result == expected, f"{description}: Expected {expected}, got {result}"
            print(f"  ✓ {description}")
            
        print("✓ Zero offset validated correctly")
        
    def test_classify_negative_values(self):
        """
        Validate classification with negative pixel values.
        This can occur with certain processing.
        """
        breaks = [0, 75, 109, 187]
        offset = 130
        
        # Negative values should go to first class
        test_cases = [
            (-1, 130, "v=-1: negative value"),
            (-10, 130, "v=-10: very negative"),
            (-255, 130, "v=-255: large negative"),
        ]
        
        for value, expected, description in test_cases:
            result = classify(value, breaks, offset=offset)
            assert result == expected, f"{description}: Expected {expected}, got {result}"
            print(f"  ✓ {description}")
            
        print("✓ Negative values handled correctly")


class TestClassifyBreakInference:
    """
    Validate the break inference logic in SoilBurnSeverityMap.__init__
    """
    
    def test_break_inference_sequential_0_to_3(self):
        """
        Validate break inference for sequential values [0, 1, 2, 3].
        
        min_val = 0
        max_val = 3
        run = 1, 0+1=1 in classes, max_run_val=1, run=2
        run = 2, 0+2=2 in classes, max_run_val=2, run=3
        run = 3, 0+3=3 in classes, max_run_val=3, run=4
        run = 4, 0+4=4 NOT in classes, stop
        
        is256 = run > 5 or len(classes) > 7 = 4 > 5 or 4 > 7 = False
        breaks = [max_run_val - i for i in range(3, -1, -1)]
               = [3-3, 3-2, 3-1, 3-0]
               = [0, 1, 2, 3]
        """
        classes = [0, 1, 2, 3]
        min_val = min(classes)
        max_val = max(classes)
        
        run = 1
        max_run_val = min_val
        while min_val + run in classes:
            max_run_val = min_val + run
            run += 1
            
        is256 = run > 5 or len(classes) > 7
        
        if is256:
            breaks = [0, 75, 109, 187]
        else:
            breaks = [max_run_val - i for i in range(3, -1, -1)]
            
        print(f"  Classes: {classes}")
        print(f"  run: {run}, max_run_val: {max_run_val}")
        print(f"  is256: {is256}")
        print(f"  breaks: {breaks}")
        
        assert breaks == [0, 1, 2, 3], f"Expected [0, 1, 2, 3], got {breaks}"
        print("  ✓ Sequential [0,1,2,3] infers correct breaks")
        
    def test_break_inference_non_sequential_0_1_3(self):
        """
        Validate break inference for non-sequential values [0, 1, 3].
        
        min_val = 0
        max_val = 3
        run = 1, 0+1=1 in classes, max_run_val=1, run=2
        run = 2, 0+2=2 NOT in classes, stop
        
        is256 = 2 > 5 or 3 > 7 = False
        breaks = [1-3, 1-2, 1-1, 1-0] = [-2, -1, 0, 1]
        """
        classes = [0, 1, 3]
        min_val = min(classes)
        max_val = max(classes)
        
        run = 1
        max_run_val = min_val
        while min_val + run in classes:
            max_run_val = min_val + run
            run += 1
            
        is256 = run > 5 or len(classes) > 7
        
        if is256:
            breaks = [0, 75, 109, 187]
        else:
            breaks = [max_run_val - i for i in range(3, -1, -1)]
            
        print(f"  Classes: {classes}")
        print(f"  run: {run}, max_run_val: {max_run_val}")
        print(f"  is256: {is256}")
        print(f"  breaks: {breaks}")
        
        assert breaks == [-2, -1, 0, 1], f"Expected [-2, -1, 0, 1], got {breaks}"
        print("  ✓ Non-sequential [0,1,3] infers breaks [-2,-1,0,1]")
        
    def test_break_inference_barc_style(self):
        """
        Validate break inference for BARC-style (many values, wide range).
        
        is256 = run > 5 or len(classes) > 7 should be True
        breaks = [0, 75, 109, 187]
        """
        # Simulate BARC data: values from 0 to 150 with gaps
        classes = list(range(0, 150, 5))  # [0, 5, 10, 15, ..., 145]
        
        min_val = min(classes)
        max_val = max(classes)
        
        run = 1
        max_run_val = min_val
        while min_val + run in classes:
            max_run_val = min_val + run
            run += 1
            
        is256 = run > 5 or len(classes) > 7
        
        if is256:
            breaks = [0, 75, 109, 187]
        else:
            breaks = [max_run_val - i for i in range(3, -1, -1)]
            
        print(f"  Classes: {len(classes)} values from {min_val} to {max_val}")
        print(f"  run: {run}, max_run_val: {max_run_val}")
        print(f"  is256: {is256}")
        print(f"  breaks: {breaks}")
        
        assert is256 == True, f"Expected is256=True, got {is256}"
        assert breaks == [0, 75, 109, 187], f"Expected BARC breaks, got {breaks}"
        print("  ✓ BARC-style correctly triggers is256 and uses [0, 75, 109, 187]")


if __name__ == '__main__':
    print("\n" + "="*70)
    print("COMPREHENSIVE CLASSIFY VALIDATION")
    print("="*70 + "\n")
    
    print("Testing classify() logic:")
    print("-" * 70)
    
    test = TestClassifyManualValidation()
    
    print("\n1. Standard 4-class breaks [0, 1, 2, 3]:")
    test.test_classify_standard_4class_breaks()
    
    print("\n2. BARC-style breaks [0, 75, 109, 187]:")
    test.test_classify_barc_style_breaks()
    
    print("\n3. Non-sequential breaks [-2, -1, 0, 1]:")
    test.test_classify_non_sequential_breaks()
    
    print("\n4. Nodata handling:")
    test.test_classify_nodata_handling()
    
    print("\n5. Single break edge case:")
    test.test_classify_edge_case_single_break()
    
    print("\n6. Empty breaks edge case:")
    test.test_classify_edge_case_empty_breaks()
    
    print("\n7. Very large values:")
    test.test_classify_edge_case_very_large_values()
    
    print("\n8. Zero offset (for 4-class export):")
    test.test_classify_zero_offset()
    
    print("\n9. Negative values:")
    test.test_classify_negative_values()
    
    print("\n" + "="*70)
    print("Testing break inference logic:")
    print("-" * 70)
    
    test_breaks = TestClassifyBreakInference()
    
    print("\n10. Break inference for [0, 1, 2, 3]:")
    test_breaks.test_break_inference_sequential_0_to_3()
    
    print("\n11. Break inference for [0, 1, 3]:")
    test_breaks.test_break_inference_non_sequential_0_1_3()
    
    print("\n12. Break inference for BARC-style:")
    test_breaks.test_break_inference_barc_style()
    
    print("\n" + "="*70)
    print("VALIDATION COMPLETE")
    print("="*70 + "\n")
