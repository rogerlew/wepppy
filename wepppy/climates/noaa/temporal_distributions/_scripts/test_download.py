#!/usr/bin/env python3
"""
Test script to download a small subset of temporal distribution files
to verify the download script works correctly.
"""

from pathlib import Path
from download_all_temporal_distributions import (
    get_download_url, download_file, VOLUMES, DURATIONS
)


def test_download():
    """Download a small subset of files for testing."""

    # Create test output directory
    test_dir = Path(__file__).parent / "test_data"
    test_dir.mkdir(exist_ok=True)

    print("Testing download functionality...")
    print(f"Test output directory: {test_dir}")
    print()

    # Test cases: (volume_code, area, duration)
    test_cases = [
        ("sa", "general", "6h"),
        ("orb", "general", "12h"),
        ("sw", "1", "24h"),  # California
        ("inw", "1", "6h"),
    ]

    successful = 0
    failed = 0

    for volume_code, area, duration in test_cases:
        volume_name = f"volume_{VOLUMES[volume_code]['number']}_{VOLUMES[volume_code]['name'].lower().replace(' ', '_')}"
        area_name = f"area_{area}"

        url = get_download_url(volume_code, area, duration)
        output_path = test_dir / volume_name / area_name / f"{duration}_temporal.csv"

        print(f"Downloading: {volume_code}/{area}/{duration}")
        print(f"  URL: {url}")
        print(f"  Output: {output_path}")

        if download_file(url, output_path):
            file_size = output_path.stat().st_size
            print(f"  ✓ Success! ({file_size:,} bytes)")
            successful += 1
        else:
            print(f"  ✗ Failed!")
            failed += 1
        print()

    print("=" * 60)
    print(f"Test Summary: {successful} successful, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("✓ All tests passed! The download script is working correctly.")
        print(f"\nTest data saved to: {test_dir}")
        print("You can now run the full download with:")
        print("  python download_all_temporal_distributions.py")
    else:
        print("✗ Some tests failed. Please check the errors above.")

    return failed == 0


if __name__ == "__main__":
    success = test_download()
    exit(0 if success else 1)
