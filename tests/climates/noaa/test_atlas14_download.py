"""
Test script for NOAA Atlas 14 precipitation frequency data download

This script tests the pfdf.data.noaa.atlas14.download function and saves
intensity and depth artifacts for reference in further development.

Usage:
    python test_atlas14_download.py

The script will:
1. Test downloading precipitation intensity data
2. Test downloading precipitation depth data
3. Save artifacts in the noaa directory for reference
4. Verify the downloaded data has expected content
"""

from __future__ import annotations

import sys
from pathlib import Path

# Test configuration
TEST_LAT = 39.0  # Denver, CO area
TEST_LON = -105.0
TIMEOUT = 30  # seconds

# Directory setup
TEST_DIR = Path(__file__).parent
ARTIFACTS_DIR = TEST_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def test_atlas14_download_intensity():
    """Test downloading precipitation intensity data from NOAA Atlas 14"""

    try:
        from pfdf.data.noaa import atlas14
    except ImportError as e:
        print(f"✗ Failed to import pfdf.data.noaa.atlas14: {e}")
        print("  Make sure pfdf is installed: pip install git+https://github.com/rogerlew/usgs-pfdf.git")
        return False

    print("\n" + "="*80)
    print("Testing NOAA Atlas 14 - Precipitation Intensity Download")
    print("="*80)

    # Test parameters
    output_file = ARTIFACTS_DIR / "atlas14_intensity_pds_mean_metric.csv"

    print(f"\nTest Location: {TEST_LAT}°N, {TEST_LON}°W")
    print(f"Data Type: Intensity (mm/hour)")
    print(f"Series: PDS (Partial Duration Series)")
    print(f"Statistic: Mean")
    print(f"Units: Metric")
    print(f"Output File: {output_file}")
    print(f"API URL: {atlas14.query_url('mean')}")

    try:
        print("\nDownloading...")
        result = atlas14.download(
            TEST_LAT,
            TEST_LON,
            parent=ARTIFACTS_DIR,
            name=output_file.name,
            statistic='mean',
            data='intensity',
            series='pds',
            units='metric',
            timeout=TIMEOUT,
            overwrite=True
        )

        # Verify download
        if not result.exists():
            print(f"✗ Download failed - file does not exist: {result}")
            return False

        content = result.read_text()
        file_size = len(content)

        # Check for expected content
        expected_markers = [
            "NOAA Atlas 14",
            "PRECIPITATION FREQUENCY ESTIMATES",
            "Precipitation intensity",
            "millimeters/hour",
            "Partial duration"
        ]

        missing_markers = [marker for marker in expected_markers if marker not in content]

        if missing_markers:
            print(f"✗ Download failed - missing expected content:")
            for marker in missing_markers:
                print(f"  - {marker}")
            return False

        print(f"✓ Download successful!")
        print(f"✓ File size: {file_size} bytes")
        print(f"✓ Saved to: {result}")

        # Show preview
        print("\nContent preview:")
        print("-" * 80)
        lines = content.split('\n')
        for i, line in enumerate(lines[:20]):
            print(f"  {line}")
            if i == 19 and len(lines) > 20:
                print(f"  ... ({len(lines) - 20} more lines)")
        print("-" * 80)

        return True

    except Exception as e:
        print(f"✗ Download failed with exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_atlas14_download_depth():
    """Test downloading precipitation depth data from NOAA Atlas 14"""

    try:
        from pfdf.data.noaa import atlas14
    except ImportError as e:
        print(f"✗ Failed to import pfdf.data.noaa.atlas14: {e}")
        return False

    print("\n" + "="*80)
    print("Testing NOAA Atlas 14 - Precipitation Depth Download")
    print("="*80)

    # Test parameters
    output_file = ARTIFACTS_DIR / "atlas14_depth_pds_mean_metric.csv"

    print(f"\nTest Location: {TEST_LAT}°N, {TEST_LON}°W")
    print(f"Data Type: Depth (mm)")
    print(f"Series: PDS (Partial Duration Series)")
    print(f"Statistic: Mean")
    print(f"Units: Metric")
    print(f"Output File: {output_file}")

    try:
        print("\nDownloading...")
        result = atlas14.download(
            TEST_LAT,
            TEST_LON,
            parent=ARTIFACTS_DIR,
            name=output_file.name,
            statistic='mean',
            data='depth',
            series='pds',
            units='metric',
            timeout=TIMEOUT,
            overwrite=True
        )

        # Verify download
        if not result.exists():
            print(f"✗ Download failed - file does not exist: {result}")
            return False

        content = result.read_text()
        file_size = len(content)

        # Check for expected content
        expected_markers = [
            "NOAA Atlas 14",
            "PRECIPITATION FREQUENCY ESTIMATES",
            "Precipitation depth",
            "millimeters",
            "Partial duration"
        ]

        missing_markers = [marker for marker in expected_markers if marker not in content]

        if missing_markers:
            print(f"✗ Download failed - missing expected content:")
            for marker in missing_markers:
                print(f"  - {marker}")
            return False

        print(f"✓ Download successful!")
        print(f"✓ File size: {file_size} bytes")
        print(f"✓ Saved to: {result}")

        # Show preview
        print("\nContent preview:")
        print("-" * 80)
        lines = content.split('\n')
        for i, line in enumerate(lines[:20]):
            print(f"  {line}")
            if i == 19 and len(lines) > 20:
                print(f"  ... ({len(lines) - 20} more lines)")
        print("-" * 80)

        return True

    except Exception as e:
        print(f"✗ Download failed with exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_atlas14_download_english_units():
    """Test downloading with English units (inches/hour)"""

    try:
        from pfdf.data.noaa import atlas14
    except ImportError:
        return False

    print("\n" + "="*80)
    print("Testing NOAA Atlas 14 - English Units")
    print("="*80)

    output_file = ARTIFACTS_DIR / "atlas14_intensity_pds_mean_english.csv"

    print(f"\nTest Location: {TEST_LAT}°N, {TEST_LON}°W")
    print(f"Data Type: Intensity (inches/hour)")
    print(f"Units: English")
    print(f"Output File: {output_file}")

    try:
        print("\nDownloading...")
        result = atlas14.download(
            TEST_LAT,
            TEST_LON,
            parent=ARTIFACTS_DIR,
            name=output_file.name,
            statistic='mean',
            data='intensity',
            series='pds',
            units='english',
            timeout=TIMEOUT,
            overwrite=True
        )

        content = result.read_text()

        # Check for inches in content
        if "inches" not in content.lower():
            print(f"✗ English units test failed - 'inches' not found in content")
            return False

        print(f"✓ English units download successful!")
        print(f"✓ File size: {len(content)} bytes")
        print(f"✓ Saved to: {result}")

        return True

    except Exception as e:
        print(f"✗ English units test failed: {type(e).__name__}: {e}")
        return False


def main():
    """Run all tests and report results"""

    print("\n" + "="*80)
    print("NOAA Atlas 14 Download Test Suite")
    print("="*80)
    print(f"\nArtifacts will be saved to: {ARTIFACTS_DIR}")

    results = {}

    # Run tests
    results['intensity'] = test_atlas14_download_intensity()
    results['depth'] = test_atlas14_download_depth()
    results['english'] = test_atlas14_download_english_units()

    # Summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    print("\n" + "="*80)
    if all_passed:
        print("✓ All tests passed!")
        print("\nArtifacts saved:")
        for artifact in sorted(ARTIFACTS_DIR.glob("*.csv")):
            print(f"  - {artifact.name}")
    else:
        print("✗ Some tests failed")
        return 1

    print("="*80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
