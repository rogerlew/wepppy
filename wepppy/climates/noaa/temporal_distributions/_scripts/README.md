# NOAA Temporal Distributions Data Acquisition

This directory contains scripts to download temporal distribution curves from NOAA's Precipitation Frequency Data Server (PFDS).

## Data Source

- **URL**: https://hdsc.nws.noaa.gov/pfds/pfds_temporal.html
- **Provider**: NOAA's Hydrometeorological Design Studies Center (HDSC)

## What Are Temporal Distributions?

Temporal distributions show how precipitation accumulates over time during storm events. They are provided as cumulative percentages of total precipitation at various time steps for:

- **Durations**: 6-hour, 12-hour, 24-hour, and 96-hour
- **Quartile Cases**: Four precipitation cases defined by the duration quartile in which the greatest percentage of total precipitation occurred, plus an "all cases combined" distribution
- **Geographic Coverage**: 12 volumes covering the entire United States and territories

## Usage

### Download All Data

To download all temporal distributions for all volumes, areas, and durations:

```bash
cd wepppy/climates/noaa/temporal_distributions/_scripts
python download_all_temporal_distributions.py
```

This will download all files to `../data/` (approximately 150+ files).

### Custom Output Directory

To specify a custom output directory:

```bash
python download_all_temporal_distributions.py /path/to/output/directory
```

## Data Structure

The downloaded data is organized in an intuitive directory structure:

```
data/
├── volume_01_semiarid_southwest/
│   ├── area_general/
│   │   ├── 6h_temporal.csv
│   │   ├── 12h_temporal.csv
│   │   ├── 24h_temporal.csv
│   │   └── 96h_temporal.csv
│   └── area_convective/
│       ├── 6h_temporal.csv
│       ├── 12h_temporal.csv
│       ├── 24h_temporal.csv
│       └── 96h_temporal.csv
├── volume_02_ohio_river_basin_and_surrounding_states/
│   └── area_general/
│       ├── 6h_temporal.csv
│       ├── 12h_temporal.csv
│       ├── 24h_temporal.csv
│       └── 96h_temporal.csv
├── volume_03_puerto_rico_and_the_us_virgin_islands/
│   └── area_general/
│       └── ...
├── volume_04_hawaiian_islands/
│   └── area_general/
│       └── ...
├── volume_05_selected_pacific_islands/
│   └── area_general/
│       └── ...
├── volume_06_california/
│   ├── area_1/
│   │   └── ...
│   ├── area_2/
│   │   └── ...
│   ├── ...
│   └── area_14/
│       └── ...
├── volume_07_alaska/
│   ├── area_1/
│   │   └── ...
│   └── area_2/
│       └── ...
├── volume_08_midwestern_states/
│   ├── area_1/
│   ├── area_2/
│   ├── area_3/
│   └── area_4/
├── volume_09_southeastern_states/
│   ├── area_1/
│   └── area_2/
├── volume_10_northeastern_states/
│   ├── area_1/
│   └── area_2/
├── volume_11_texas/
│   ├── area_1/
│   ├── area_2/
│   └── area_3/
└── volume_12_interior_northwest/
    ├── area_1/
    └── area_2/
```

## Volumes and Coverage

| Volume | Code | Name | Areas |
|--------|------|------|-------|
| 1 | sa | Semiarid Southwest | 2 (general, convective) |
| 2 | orb | Ohio River Basin and Surrounding States | 1 (general) |
| 3 | pr | Puerto Rico and the U.S. Virgin Islands | 1 (general) |
| 4 | hi | Hawaiian Islands | 1 (general) |
| 5 | pi | Selected Pacific Islands | 1 (general) |
| 6 | sw | California | 14 (numbered 1-14) |
| 7 | ak | Alaska | 2 (numbered 1-2) |
| 8 | mw | Midwestern States | 4 (numbered 1-4) |
| 9 | se | Southeastern States | 2 (numbered 1-2) |
| 10 | ne | Northeastern States | 2 (numbered 1-2) |
| 11 | tx | Texas | 3 (numbered 1-3) |
| 12 | inw | Interior Northwest | 2 (numbered 1-2) |

## CSV File Format

Each CSV file contains temporal distribution data for all four quartile cases and the combined case. The file includes:

- **Header Information**: Describes the volume, region, and duration
- **Time Column**: Shows time from 0 to duration in increments (e.g., 0.5-hourly for 6-hour)
- **Percentage Columns**: Cumulative percentages of total precipitation at various probability levels (90%, 80%, 70%, 60%, 50%, 40%, 30%, 20%, 10%)

The data is organized by quartile cases:
- **First-Quartile Cases**: Peak precipitation in first quarter
- **Second-Quartile Cases**: Peak precipitation in second quarter
- **Third-Quartile Cases**: Peak precipitation in third quarter
- **Fourth-Quartile Cases**: Peak precipitation in fourth quarter
- **All Cases Combined**: Overall temporal distribution

## Dependencies

- Python 3.6+
- `requests` - For HTTP downloads
- `tqdm` - For progress bars (optional but recommended)

Install dependencies:

```bash
pip install requests tqdm
```

## Notes

- The script includes retry logic with exponential backoff for failed downloads
- Downloads may take several minutes depending on network speed
- Total data size is approximately 20-30 MB
- Shapefiles for temporal distribution areas are available separately from NOAA PFDS
