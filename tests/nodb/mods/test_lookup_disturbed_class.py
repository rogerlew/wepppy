"""
Test suite for lookup_disturbed_class helper function.

This module tests that treatment suffixes are properly stripped from disturbed classes
when looking up soil parameters, ensuring fire-adjusted erodibility is used for
treatment scenarios (mulch, thinning).
"""

import pytest
from wepppy.nodb.mods.disturbed import (
    lookup_disturbed_class,
    TREATMENT_SUFFIXES,
)


@pytest.mark.unit
class TestLookupDisturbedClass:
    """Test the lookup_disturbed_class helper function."""
    
    def test_strips_mulch_15_suffix(self):
        """Mulch 15% suffix should be stripped."""
        result = lookup_disturbed_class('forest moderate sev fire-mulch_15')
        assert result == 'forest moderate sev fire'
    
    def test_strips_mulch_30_suffix(self):
        """Mulch 30% suffix should be stripped."""
        result = lookup_disturbed_class('shrub high sev fire-mulch_30')
        assert result == 'shrub high sev fire'
    
    def test_strips_mulch_60_suffix(self):
        """Mulch 60% suffix should be stripped."""
        result = lookup_disturbed_class('grass low sev fire-mulch_60')
        assert result == 'grass low sev fire'
    
    def test_strips_thinning_suffix(self):
        """Thinning suffix should be stripped."""
        result = lookup_disturbed_class('forest high sev fire-thinning')
        assert result == 'forest high sev fire'
    
    def test_strips_prescribed_fire_suffix(self):
        """Prescribed fire suffix should be stripped."""
        result = lookup_disturbed_class('forest-prescribed_fire')
        assert result == 'forest'
    
    def test_no_suffix_unchanged(self):
        """Base disturbed classes without suffixes should be unchanged."""
        result = lookup_disturbed_class('forest moderate sev fire')
        assert result == 'forest moderate sev fire'
    
    def test_none_returns_none(self):
        """None input should return None."""
        result = lookup_disturbed_class(None)
        assert result is None
    
    def test_empty_string_unchanged(self):
        """Empty string should be returned unchanged."""
        result = lookup_disturbed_class('')
        assert result == ''
    
    def test_no_fire_class_unchanged(self):
        """Non-fire classes should be returned unchanged."""
        result = lookup_disturbed_class('forest')
        assert result == 'forest'
    
    def test_partial_suffix_not_stripped(self):
        """Partial suffix matches should NOT be stripped (only exact suffix matches)."""
        result = lookup_disturbed_class('forest moderate sev fire-mulch')
        assert result == 'forest moderate sev fire-mulch'  # Not a recognized suffix


@pytest.mark.unit
class TestTreatmentSuffixes:
    """Test the TREATMENT_SUFFIXES constant."""
    
    def test_contains_all_mulch_levels(self):
        """Should include all mulch treatment levels."""
        assert '-mulch_15' in TREATMENT_SUFFIXES
        assert '-mulch_30' in TREATMENT_SUFFIXES
        assert '-mulch_60' in TREATMENT_SUFFIXES
    
    def test_contains_thinning(self):
        """Should include thinning treatment."""
        assert '-thinning' in TREATMENT_SUFFIXES
    
    def test_contains_prescribed_fire(self):
        """Should include prescribed fire treatment."""
        assert '-prescribed_fire' in TREATMENT_SUFFIXES


@pytest.mark.unit
class TestSoilLookupKeyGeneration:
    """Test that the correct lookup keys are generated for soil parameters."""
    
    def test_fire_lookup_key_for_mulch_scenario(self):
        """
        Mulch scenarios should use fire class for soil erodibility lookup,
        not the mulch class.
        
        This is the key fix for the mulch_15 > base soil loss bug:
        Soil erodibility (ki, kr) must come from fire severity, not treatment type.
        """
        disturbed_class = 'forest moderate sev fire-mulch_15'
        texid = 'sand loam'
        
        # With the fix, lookup should use base fire class
        lookup_class = lookup_disturbed_class(disturbed_class)
        key = (texid, lookup_class)
        
        # This should match the fire severity class, not mulch
        assert key == ('sand loam', 'forest moderate sev fire')
        # NOT ('sand loam', 'mulch') or ('sand loam', 'forest moderate sev fire-mulch_15')
