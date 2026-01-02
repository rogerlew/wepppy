#!/usr/bin/env python3
"""
NOAA Temporal Distributions Data Acquisition Script

This script downloads all temporal distribution curves from NOAA's
Precipitation Frequency Data Server (PFDS) for all volumes, temporal
distribution areas, and durations.

Data source: https://hdsc.nws.noaa.gov/pfds/pfds_temporal.html

The temporal distributions are organized by:
- 12 volumes covering different US regions and territories
- Variable temporal distribution areas per volume (1-14 areas)
- 4 durations: 6-hour, 12-hour, 24-hour, and 96-hour

File structure:
    data/
        volume_01_semiarid_southwest/
            area_general/
                6h_temporal.csv
                12h_temporal.csv
                24h_temporal.csv
                96h_temporal.csv
            area_convective/
                ...
        volume_02_ohio_river_basin/
            ...
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List
import requests

# Optional tqdm for progress bars
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    # Simple fallback progress indicator
    class tqdm:
        def __init__(self, total=None, desc="", disable=False):
            self.total = total
            self.desc = desc
            self.disable = disable
            self.n = 0
            self.postfix = {}
            if not disable:
                print(f"{desc}: 0/{total}")

        def update(self, n=1):
            self.n += n
            if not self.disable and self.n % 10 == 0:  # Update every 10 files
                postfix_str = ", ".join(f"{k}: {v}" for k, v in self.postfix.items())
                print(f"{self.desc}: {self.n}/{self.total} ({postfix_str})")

        def set_postfix(self, postfix):
            self.postfix = postfix

        def __enter__(self):
            return self

        def __exit__(self, *args):
            if not self.disable:
                postfix_str = ", ".join(f"{k}: {v}" for k, v in self.postfix.items())
                print(f"{self.desc}: Complete! {self.n}/{self.total} ({postfix_str})")


# Base URL for NOAA temporal distribution data
BASE_URL = "https://hdsc.nws.noaa.gov/pub/hdsc/data"

# Volume definitions with their codes, names, and temporal distribution areas
VOLUMES = {
    "sa": {
        "number": "01",
        "name": "Semiarid Southwest",
        "areas": ["general", "convective"]
    },
    "orb": {
        "number": "02",
        "name": "Ohio River Basin and Surrounding States",
        "areas": ["general"]
    },
    "pr": {
        "number": "03",
        "name": "Puerto Rico and the U.S. Virgin Islands",
        "areas": ["general"]
    },
    "hi": {
        "number": "04",
        "name": "Hawaiian Islands",
        "areas": ["general"]
    },
    "pi": {
        "number": "05",
        "name": "Selected Pacific Islands",
        "areas": ["general"]
    },
    "sw": {
        "number": "06",
        "name": "California",
        "file_region": "ca",
        "areas": [str(i) for i in range(1, 15)]  # 1-14
    },
    "ak": {
        "number": "07",
        "name": "Alaska",
        "areas": [str(i) for i in range(1, 3)]  # 1-2
    },
    "mw": {
        "number": "08",
        "name": "Midwestern States",
        "areas": [str(i) for i in range(1, 5)]  # 1-4
    },
    "se": {
        "number": "09",
        "name": "Southeastern States",
        "areas": [str(i) for i in range(1, 3)]  # 1-2
    },
    "ne": {
        "number": "10",
        "name": "Northeastern States",
        "areas": [str(i) for i in range(1, 3)]  # 1-2
    },
    "tx": {
        "number": "11",
        "name": "Texas",
        "areas": [str(i) for i in range(1, 4)]  # 1-3
    },
    "inw": {
        "number": "12",
        "name": "Interior Northwest",
        "areas": [str(i) for i in range(1, 3)]  # 1-2
    }
}

# Duration options
DURATIONS = ["6h", "12h", "24h", "96h"]


def sanitize_dirname(name: str) -> str:
    """Convert a volume name to a filesystem-safe directory name."""
    return name.lower().replace(" ", "_").replace(".", "").replace(",", "")


def get_download_url(volume_code: str, area: str, duration: str) -> str:
    """
    Construct the download URL for a specific temporal distribution file.

    URL pattern: {BASE_URL}/{volume_code}/{file_region}_{area}_{duration}_temporal.csv

    Args:
        volume_code: Volume code (e.g., 'sa', 'orb', 'sw')
        area: Temporal distribution area (e.g., 'general', '1', '2')
        duration: Duration (e.g., '6h', '12h', '24h', '96h')

    Returns:
        Full URL to the CSV file
    """
    volume = VOLUMES[volume_code]
    file_region = volume.get("file_region", volume_code)

    url = f"{BASE_URL}/{volume_code}/{file_region}_{area}_{duration}_temporal.csv"
    return url


def download_file(url: str, output_path: Path, retry_count: int = 3) -> bool:
    """
    Download a file from URL to output_path with retry logic.

    Args:
        url: URL to download from
        output_path: Path where file should be saved
        retry_count: Number of retries on failure

    Returns:
        True if successful, False otherwise
    """
    for attempt in range(retry_count):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Create parent directories if they don't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(output_path, 'wb') as f:
                f.write(response.content)

            return True

        except requests.exceptions.RequestException as e:
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                print(f"Failed to download {url}: {e}")
                return False

    return False


def download_all_temporal_distributions(output_dir: Path, verbose: bool = True):
    """
    Download all temporal distribution files from NOAA PFDS.

    Args:
        output_dir: Base directory where data should be saved
        verbose: Whether to show progress bars and detailed output
    """
    # Calculate total number of files
    total_files = sum(
        len(vol["areas"]) * len(DURATIONS)
        for vol in VOLUMES.values()
    )

    print(f"Downloading {total_files} temporal distribution files...")
    print(f"Output directory: {output_dir}")
    print()

    successful = 0
    failed = 0
    failed_files = []

    # Create progress bar for all files
    with tqdm(total=total_files, desc="Overall progress", disable=not verbose) as pbar:
        for volume_code, volume_info in VOLUMES.items():
            volume_name = f"volume_{volume_info['number']}_{sanitize_dirname(volume_info['name'])}"

            for area in volume_info["areas"]:
                area_name = f"area_{area}"

                for duration in DURATIONS:
                    # Construct URL and output path
                    url = get_download_url(volume_code, area, duration)
                    output_path = output_dir / volume_name / area_name / f"{duration}_temporal.csv"

                    # Download file
                    if download_file(url, output_path):
                        successful += 1
                    else:
                        failed += 1
                        failed_files.append(url)

                    # Update progress bar
                    pbar.update(1)
                    pbar.set_postfix({
                        'Success': successful,
                        'Failed': failed
                    })

    # Print summary
    print()
    print("=" * 60)
    print("Download Summary")
    print("=" * 60)
    print(f"Total files:      {total_files}")
    print(f"Successful:       {successful}")
    print(f"Failed:           {failed}")
    print()

    if failed_files:
        print("Failed downloads:")
        for url in failed_files:
            print(f"  - {url}")
        print()

    print(f"Data saved to: {output_dir}")


def main():
    """Main entry point for the script."""
    # Get script directory
    script_dir = Path(__file__).parent

    # Default output directory: ../data (relative to script)
    default_output_dir = script_dir.parent / "data"

    # Allow user to specify custom output directory
    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])
    else:
        output_dir = default_output_dir

    # Run download
    download_all_temporal_distributions(output_dir)


if __name__ == "__main__":
    main()
