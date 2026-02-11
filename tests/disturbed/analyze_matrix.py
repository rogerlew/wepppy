#!/usr/bin/env python3
"""
Analyze the disturbed matrix test results.

Compares burned vs unburned simulations for:
- Event counts (burned > unburned, same, unburned > burned)
- Descriptive statistics for runoff, peak discharge, and sediment delivery

Output: Markdown tables for inclusion in the disturbed README.md
"""

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


# =============================================================================
# Configuration (matches test_disturbed_matrix.py)
# =============================================================================

TEXTURES = ["clay loam", "loam", "sand loam", "silt loam"]
SEVERITIES = [0, 1, 2, 3]
SEVERITY_NAMES = {0: "unburned", 1: "low", 2: "moderate", 3: "high"}
VEG_TYPES = ["forest", "shrub", "tall grass"]

DISTURBED_CLASSES = {
    # Unburned
    ("forest", 0): "forest",
    ("shrub", 0): "shrub",
    ("tall grass", 0): "tall grass",
    # Low severity
    ("forest", 1): "forest low sev fire",
    ("shrub", 1): "shrub low sev fire",
    ("tall grass", 1): "grass low sev fire",
    # Moderate severity
    ("forest", 2): "forest moderate sev fire",
    ("shrub", 2): "shrub moderate sev fire",
    ("tall grass", 2): "grass moderate sev fire",
    # High severity
    ("forest", 3): "forest high sev fire",
    ("shrub", 3): "shrub high sev fire",
    ("tall grass", 3): "grass high sev fire",
}

PASS_EVENT_LABELS = {"EVENT", "SUBEVENT", "NO EVENT"}
PASS_EVENT_FLOAT_COUNT = 24  # dur..tdep + sedcon + sediment fractions + groundwater terms


def generate_wepp_id(texture: str, severity: int, veg_type: str) -> int:
    """Generate a unique WEPP ID for this combination."""
    texture_idx = TEXTURES.index(texture)
    veg_idx = VEG_TYPES.index(veg_type)
    return texture_idx * 12 + veg_idx * 4 + severity + 1


def wepp_id_to_params(wepp_id: int) -> Tuple[str, int, str]:
    """Convert WEPP ID back to parameters."""
    wepp_id -= 1  # Convert to 0-indexed
    texture_idx = wepp_id // 12
    remainder = wepp_id % 12
    veg_idx = remainder // 4
    severity = remainder % 4
    return TEXTURES[texture_idx], severity, VEG_TYPES[veg_idx]


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Event:
    """A single runoff/erosion event from ebe.dat."""
    day: int
    month: int
    year: int
    precip: float       # mm
    runoff: float       # mm
    sed_del: float      # kg/m (sediment delivery)


@dataclass
class PeakEvent:
    """A single peak discharge event from pass.dat EVENT rows."""
    year: int
    julian: int
    peakflow: float     # m^3/s


@dataclass
class ComparisonResult:
    """Results of comparing burned vs unburned for a single combination."""
    texture: str
    veg_type: str
    severity: int
    disturbed_class: str
    total_events: int
    # Runoff comparisons
    runoff_burned_gt: int      # burned > unburned
    runoff_equal: int          # burned == unburned
    runoff_unburned_gt: int    # unburned > burned
    # Sediment comparisons
    sed_burned_gt: int
    sed_equal: int
    sed_unburned_gt: int
    # Peak discharge comparisons
    peak_total_events: int
    peak_burned_gt: int
    peak_equal: int
    peak_unburned_gt: int
    # Statistics
    runoff_burned_mean: float
    runoff_burned_std: float
    runoff_burned_median: float
    runoff_burned_sum: float
    runoff_unburned_mean: float
    runoff_unburned_std: float
    runoff_unburned_median: float
    runoff_unburned_sum: float
    sed_burned_mean: float
    sed_burned_std: float
    sed_burned_median: float
    sed_burned_sum: float
    sed_unburned_mean: float
    sed_unburned_std: float
    sed_unburned_median: float
    sed_unburned_sum: float
    peak_burned_mean: float
    peak_burned_std: float
    peak_burned_median: float
    peak_burned_sum: float
    peak_unburned_mean: float
    peak_unburned_std: float
    peak_unburned_median: float
    peak_unburned_sum: float


# =============================================================================
# Parsing Functions
# =============================================================================

def parse_ebe_file(filepath: Path) -> List[Event]:
    """Parse a WEPP event-by-event output file (.ebe.dat)."""
    events = []

    with open(filepath, 'r') as f:
        lines = f.readlines()

    # Skip header lines (first 3 lines are header)
    for line in lines[3:]:
        line = line.strip()
        if not line:
            continue

        # Parse fixed-width format
        # day mo  year Precp  Runoff  IR-det Av-det Mx-det  Point  Av-dep Max-dep  Point Sed.Del    ER
        parts = line.split()
        if len(parts) < 14:
            continue

        try:
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])
            precip = float(parts[3])
            runoff = float(parts[4])
            sed_del = float(parts[12])  # Sed.Del column (13th column, 0-indexed as 12)

            events.append(Event(
                day=day,
                month=month,
                year=year,
                precip=precip,
                runoff=runoff,
                sed_del=sed_del
            ))
        except (ValueError, IndexError):
            continue

    return events


def load_all_events(output_dir: Path) -> Dict[int, List[Event]]:
    """Load all ebe.dat files and return dict keyed by wepp_id."""
    events_by_id = {}

    for wepp_id in range(1, 49):  # 48 simulations
        ebe_file = output_dir / f"H{wepp_id}.ebe.dat"
        if ebe_file.exists():
            events_by_id[wepp_id] = parse_ebe_file(ebe_file)
        else:
            print(f"Warning: Missing {ebe_file}")

    return events_by_id


def parse_pass_peakflow_file(filepath: Path) -> List[PeakEvent]:
    """Parse pass.dat EVENT rows and extract peak runoff rate (peak discharge)."""
    peak_events: List[PeakEvent] = []

    with open(filepath, "r") as f:
        lines = f.readlines()

    if len(lines) < 6:
        return peak_events

    header_tokens = lines[1].split()
    if not header_tokens:
        return peak_events

    try:
        start_year = int(header_tokens[-1])
    except ValueError:
        return peak_events

    data_lines = lines[5:]
    idx = 0
    while idx < len(data_lines):
        raw_line = data_lines[idx]
        label = raw_line[:8].strip().upper()
        if label != "EVENT":
            idx += 1
            continue

        tokens = raw_line[8:].split()
        idx += 1
        expected = 2 + PASS_EVENT_FLOAT_COUNT

        while len(tokens) < expected and idx < len(data_lines):
            candidate = data_lines[idx]
            candidate_label = candidate[:8].strip().upper()
            if candidate_label in PASS_EVENT_LABELS and candidate_label:
                break
            tokens.extend(candidate.split())
            idx += 1

        if len(tokens) < expected:
            continue

        try:
            absolute_year = int(tokens[0])
            julian = int(tokens[1])
            values = tokens[2:]
            if len(values) != PASS_EVENT_FLOAT_COUNT:
                continue
            peakflow = float(values[9])  # peakro field in pass EVENT payload
            sim_year = absolute_year - start_year + 1
            peak_events.append(
                PeakEvent(year=sim_year, julian=julian, peakflow=peakflow)
            )
        except (ValueError, IndexError):
            continue

    return peak_events


def load_all_peak_events(output_dir: Path) -> Dict[int, List[PeakEvent]]:
    """Load all pass.dat peakflow EVENT rows keyed by wepp_id."""
    peak_events_by_id: Dict[int, List[PeakEvent]] = {}

    for wepp_id in range(1, 49):  # 48 simulations
        pass_file = output_dir / f"H{wepp_id}.pass.dat"
        if pass_file.exists():
            peak_events_by_id[wepp_id] = parse_pass_peakflow_file(pass_file)
        else:
            print(f"Warning: Missing {pass_file}")

    return peak_events_by_id


# =============================================================================
# Analysis Functions
# =============================================================================

def events_to_dict(events: List[Event]) -> Dict[Tuple[int, int, int], Event]:
    """Convert event list to dict keyed by (day, month, year)."""
    return {(e.day, e.month, e.year): e for e in events}


def peak_events_to_dict(events: List[PeakEvent]) -> Dict[Tuple[int, int], PeakEvent]:
    """Convert peak event list to dict keyed by (simulation year, julian day)."""
    return {(e.year, e.julian): e for e in events}


def compare_burned_vs_unburned(
    burned_events: List[Event],
    unburned_events: List[Event],
    tolerance: float = 1e-6
) -> Tuple[
    int, int, int, int,  # runoff: burned_gt, equal, unburned_gt, total
    int, int, int,       # sed: burned_gt, equal, unburned_gt
    List[float], List[float],  # runoff: burned, unburned (matched)
    List[float], List[float]   # sed: burned, unburned (matched)
]:
    """Compare events between burned and unburned simulations."""
    burned_dict = events_to_dict(burned_events)
    unburned_dict = events_to_dict(unburned_events)

    # Find common event dates
    common_dates = set(burned_dict.keys()) & set(unburned_dict.keys())

    # Counters
    runoff_burned_gt = 0
    runoff_equal = 0
    runoff_unburned_gt = 0

    sed_burned_gt = 0
    sed_equal = 0
    sed_unburned_gt = 0

    # Matched values for statistics
    runoff_burned = []
    runoff_unburned = []
    sed_burned = []
    sed_unburned = []

    for date in sorted(common_dates):
        b = burned_dict[date]
        u = unburned_dict[date]

        # Runoff comparison
        runoff_burned.append(b.runoff)
        runoff_unburned.append(u.runoff)

        if b.runoff > u.runoff + tolerance:
            runoff_burned_gt += 1
        elif u.runoff > b.runoff + tolerance:
            runoff_unburned_gt += 1
        else:
            runoff_equal += 1

        # Sediment comparison
        sed_burned.append(b.sed_del)
        sed_unburned.append(u.sed_del)

        if b.sed_del > u.sed_del + tolerance:
            sed_burned_gt += 1
        elif u.sed_del > b.sed_del + tolerance:
            sed_unburned_gt += 1
        else:
            sed_equal += 1

    return (
        runoff_burned_gt, runoff_equal, runoff_unburned_gt, len(common_dates),
        sed_burned_gt, sed_equal, sed_unburned_gt,
        runoff_burned, runoff_unburned,
        sed_burned, sed_unburned
    )


def compare_peakflow_burned_vs_unburned(
    burned_events: List[PeakEvent],
    unburned_events: List[PeakEvent],
    tolerance: float = 1e-9,
) -> Tuple[
    int, int, int, int,  # peakflow: burned_gt, equal, unburned_gt, total
    List[float], List[float],  # peakflow: burned, unburned (matched)
]:
    """Compare peakflow events between burned and unburned simulations."""
    burned_dict = peak_events_to_dict(burned_events)
    unburned_dict = peak_events_to_dict(unburned_events)

    common_dates = set(burned_dict.keys()) & set(unburned_dict.keys())

    peak_burned_gt = 0
    peak_equal = 0
    peak_unburned_gt = 0
    peak_burned: List[float] = []
    peak_unburned: List[float] = []

    for date in sorted(common_dates):
        b = burned_dict[date]
        u = unburned_dict[date]

        peak_burned.append(b.peakflow)
        peak_unburned.append(u.peakflow)

        if b.peakflow > u.peakflow + tolerance:
            peak_burned_gt += 1
        elif u.peakflow > b.peakflow + tolerance:
            peak_unburned_gt += 1
        else:
            peak_equal += 1

    return (
        peak_burned_gt,
        peak_equal,
        peak_unburned_gt,
        len(common_dates),
        peak_burned,
        peak_unburned,
    )


def analyze_all_comparisons(
    events_by_id: Dict[int, List[Event]],
    peak_events_by_id: Dict[int, List[PeakEvent]],
) -> List[ComparisonResult]:
    """Analyze all burned vs unburned comparisons."""
    results = []

    for texture in TEXTURES:
        for veg_type in VEG_TYPES:
            # Get unburned baseline
            unburned_id = generate_wepp_id(texture, 0, veg_type)
            if unburned_id not in events_by_id:
                print(f"Warning: Missing unburned baseline for {texture}/{veg_type}")
                continue
            unburned_events = events_by_id[unburned_id]

            # Compare each burn severity
            for severity in [1, 2, 3]:  # Low, moderate, high
                burned_id = generate_wepp_id(texture, severity, veg_type)
                if burned_id not in events_by_id:
                    print(f"Warning: Missing burned data for {texture}/{veg_type}/{SEVERITY_NAMES[severity]}")
                    continue
                burned_events = events_by_id[burned_id]

                (
                    runoff_burned_gt, runoff_equal, runoff_unburned_gt, total,
                    sed_burned_gt, sed_equal, sed_unburned_gt,
                    runoff_burned, runoff_unburned,
                    sed_burned, sed_unburned
                ) = compare_burned_vs_unburned(burned_events, unburned_events)

                peak_burned_events = peak_events_by_id.get(burned_id, [])
                peak_unburned_events = peak_events_by_id.get(unburned_id, [])
                (
                    peak_burned_gt,
                    peak_equal,
                    peak_unburned_gt,
                    peak_total,
                    peak_burned,
                    peak_unburned,
                ) = compare_peakflow_burned_vs_unburned(
                    peak_burned_events,
                    peak_unburned_events,
                )

                # Calculate statistics
                runoff_burned_arr = np.array(runoff_burned)
                runoff_unburned_arr = np.array(runoff_unburned)
                sed_burned_arr = np.array(sed_burned)
                sed_unburned_arr = np.array(sed_unburned)
                peak_burned_arr = np.array(peak_burned)
                peak_unburned_arr = np.array(peak_unburned)

                disturbed_class = DISTURBED_CLASSES[(veg_type, severity)]

                results.append(ComparisonResult(
                    texture=texture,
                    veg_type=veg_type,
                    severity=severity,
                    disturbed_class=disturbed_class,
                    total_events=total,
                    # Runoff
                    runoff_burned_gt=runoff_burned_gt,
                    runoff_equal=runoff_equal,
                    runoff_unburned_gt=runoff_unburned_gt,
                    runoff_burned_mean=np.mean(runoff_burned_arr) if len(runoff_burned_arr) else 0,
                    runoff_burned_std=np.std(runoff_burned_arr) if len(runoff_burned_arr) else 0,
                    runoff_burned_median=np.median(runoff_burned_arr) if len(runoff_burned_arr) else 0,
                    runoff_burned_sum=np.sum(runoff_burned_arr) if len(runoff_burned_arr) else 0,
                    runoff_unburned_mean=np.mean(runoff_unburned_arr) if len(runoff_unburned_arr) else 0,
                    runoff_unburned_std=np.std(runoff_unburned_arr) if len(runoff_unburned_arr) else 0,
                    runoff_unburned_median=np.median(runoff_unburned_arr) if len(runoff_unburned_arr) else 0,
                    runoff_unburned_sum=np.sum(runoff_unburned_arr) if len(runoff_unburned_arr) else 0,
                    # Sediment
                    sed_burned_gt=sed_burned_gt,
                    sed_equal=sed_equal,
                    sed_unburned_gt=sed_unburned_gt,
                    sed_burned_mean=np.mean(sed_burned_arr) if len(sed_burned_arr) else 0,
                    sed_burned_std=np.std(sed_burned_arr) if len(sed_burned_arr) else 0,
                    sed_burned_median=np.median(sed_burned_arr) if len(sed_burned_arr) else 0,
                    sed_burned_sum=np.sum(sed_burned_arr) if len(sed_burned_arr) else 0,
                    sed_unburned_mean=np.mean(sed_unburned_arr) if len(sed_unburned_arr) else 0,
                    sed_unburned_std=np.std(sed_unburned_arr) if len(sed_unburned_arr) else 0,
                    sed_unburned_median=np.median(sed_unburned_arr) if len(sed_unburned_arr) else 0,
                    sed_unburned_sum=np.sum(sed_unburned_arr) if len(sed_unburned_arr) else 0,
                    # Peakflow
                    peak_total_events=peak_total,
                    peak_burned_gt=peak_burned_gt,
                    peak_equal=peak_equal,
                    peak_unburned_gt=peak_unburned_gt,
                    peak_burned_mean=np.mean(peak_burned_arr) if len(peak_burned_arr) else 0,
                    peak_burned_std=np.std(peak_burned_arr) if len(peak_burned_arr) else 0,
                    peak_burned_median=np.median(peak_burned_arr) if len(peak_burned_arr) else 0,
                    peak_burned_sum=np.sum(peak_burned_arr) if len(peak_burned_arr) else 0,
                    peak_unburned_mean=np.mean(peak_unburned_arr) if len(peak_unburned_arr) else 0,
                    peak_unburned_std=np.std(peak_unburned_arr) if len(peak_unburned_arr) else 0,
                    peak_unburned_median=np.median(peak_unburned_arr) if len(peak_unburned_arr) else 0,
                    peak_unburned_sum=np.sum(peak_unburned_arr) if len(peak_unburned_arr) else 0,
                ))

    return results


# =============================================================================
# Aggregate Statistics
# =============================================================================

def aggregate_by_veg_severity(
    results: List[ComparisonResult]
) -> Dict[Tuple[str, int], Dict]:
    """Aggregate results by vegetation type and severity (across textures)."""
    agg = defaultdict(lambda: {
        'total_events': 0,
        'peak_total_events': 0,
        'runoff_burned_gt': 0,
        'runoff_equal': 0,
        'runoff_unburned_gt': 0,
        'sed_burned_gt': 0,
        'sed_equal': 0,
        'sed_unburned_gt': 0,
        'peak_burned_gt': 0,
        'peak_equal': 0,
        'peak_unburned_gt': 0,
        'runoff_burned_sum': 0,
        'runoff_unburned_sum': 0,
        'sed_burned_sum': 0,
        'sed_unburned_sum': 0,
        'peak_burned_sum': 0,
        'peak_unburned_sum': 0,
        'count': 0,
    })

    for r in results:
        key = (r.veg_type, r.severity)
        agg[key]['total_events'] += r.total_events
        agg[key]['peak_total_events'] += r.peak_total_events
        agg[key]['runoff_burned_gt'] += r.runoff_burned_gt
        agg[key]['runoff_equal'] += r.runoff_equal
        agg[key]['runoff_unburned_gt'] += r.runoff_unburned_gt
        agg[key]['sed_burned_gt'] += r.sed_burned_gt
        agg[key]['sed_equal'] += r.sed_equal
        agg[key]['sed_unburned_gt'] += r.sed_unburned_gt
        agg[key]['peak_burned_gt'] += r.peak_burned_gt
        agg[key]['peak_equal'] += r.peak_equal
        agg[key]['peak_unburned_gt'] += r.peak_unburned_gt
        agg[key]['runoff_burned_sum'] += r.runoff_burned_sum
        agg[key]['runoff_unburned_sum'] += r.runoff_unburned_sum
        agg[key]['sed_burned_sum'] += r.sed_burned_sum
        agg[key]['sed_unburned_sum'] += r.sed_unburned_sum
        agg[key]['peak_burned_sum'] += r.peak_burned_sum
        agg[key]['peak_unburned_sum'] += r.peak_unburned_sum
        agg[key]['count'] += 1

    return dict(agg)


# =============================================================================
# Markdown Output
# =============================================================================

def format_number(n: float, decimals: int = 1) -> str:
    """Format number with thousands separator."""
    if decimals == 0:
        return f"{int(n):,}"
    return f"{n:,.{decimals}f}"


def generate_event_counts_markdown(results: List[ComparisonResult]) -> str:
    """Generate markdown tables for event counts."""
    lines = []

    # Aggregate by veg type and severity
    agg = aggregate_by_veg_severity(results)

    lines.append("### Runoff Event Counts (Burned vs Unburned)")
    lines.append("")
    lines.append("Event counts compare burned vs unburned runoff by matching day/month/year across")
    lines.append("all 4 soil textures. Results aggregated from 100-year simulations (48 total runs).")
    lines.append("")
    lines.append("| Veg Type | Severity | Total Events | Burned > Unburned | Equal | Unburned > Burned |")
    lines.append("|----------|----------|-------------:|------------------:|------:|------------------:|")

    for veg_type in VEG_TYPES:
        for severity in [1, 2, 3]:
            key = (veg_type, severity)
            if key not in agg:
                continue
            a = agg[key]
            disturbed_class = DISTURBED_CLASSES[(veg_type, severity)]
            lines.append(
                f"| {veg_type} | {SEVERITY_NAMES[severity]} | "
                f"{format_number(a['total_events'], 0)} | "
                f"{format_number(a['runoff_burned_gt'], 0)} | "
                f"{format_number(a['runoff_equal'], 0)} | "
                f"{format_number(a['runoff_unburned_gt'], 0)} |"
            )

    lines.append("")
    lines.append("### Sediment Delivery Event Counts (Burned vs Unburned)")
    lines.append("")
    lines.append("| Veg Type | Severity | Total Events | Burned > Unburned | Equal | Unburned > Burned |")
    lines.append("|----------|----------|-------------:|------------------:|------:|------------------:|")

    for veg_type in VEG_TYPES:
        for severity in [1, 2, 3]:
            key = (veg_type, severity)
            if key not in agg:
                continue
            a = agg[key]
            lines.append(
                f"| {veg_type} | {SEVERITY_NAMES[severity]} | "
                f"{format_number(a['total_events'], 0)} | "
                f"{format_number(a['sed_burned_gt'], 0)} | "
                f"{format_number(a['sed_equal'], 0)} | "
                f"{format_number(a['sed_unburned_gt'], 0)} |"
            )

    lines.append("")
    lines.append("### Peakflow Event Counts (Burned vs Unburned)")
    lines.append("")
    lines.append("Event counts compare burned vs unburned peak discharge by matching")
    lines.append("simulation year/julian day in `H*.pass.dat` EVENT records.")
    lines.append("")
    lines.append("| Veg Type | Severity | Total Events | Burned > Unburned | Equal | Unburned > Burned |")
    lines.append("|----------|----------|-------------:|------------------:|------:|------------------:|")

    for veg_type in VEG_TYPES:
        for severity in [1, 2, 3]:
            key = (veg_type, severity)
            if key not in agg:
                continue
            a = agg[key]
            lines.append(
                f"| {veg_type} | {SEVERITY_NAMES[severity]} | "
                f"{format_number(a['peak_total_events'], 0)} | "
                f"{format_number(a['peak_burned_gt'], 0)} | "
                f"{format_number(a['peak_equal'], 0)} | "
                f"{format_number(a['peak_unburned_gt'], 0)} |"
            )

    return "\n".join(lines)


def generate_descriptive_stats_markdown(results: List[ComparisonResult]) -> str:
    """Generate markdown tables for descriptive statistics."""
    lines = []

    lines.append("### Runoff Descriptive Statistics (mm)")
    lines.append("")
    lines.append("Statistics aggregated across all 4 soil textures for 100-year simulations.")
    lines.append("")
    lines.append("| Veg Type | Severity | Condition | Mean | Std Dev | Median | Total |")
    lines.append("|----------|----------|-----------|-----:|--------:|-------:|------:|")

    for veg_type in VEG_TYPES:
        for severity in [1, 2, 3]:
            # Aggregate across textures
            texture_results = [r for r in results
                              if r.veg_type == veg_type and r.severity == severity]
            if not texture_results:
                continue

            # Calculate aggregated stats
            burned_means = [r.runoff_burned_mean for r in texture_results]
            burned_stds = [r.runoff_burned_std for r in texture_results]
            burned_medians = [r.runoff_burned_median for r in texture_results]
            burned_sums = [r.runoff_burned_sum for r in texture_results]

            unburned_means = [r.runoff_unburned_mean for r in texture_results]
            unburned_stds = [r.runoff_unburned_std for r in texture_results]
            unburned_medians = [r.runoff_unburned_median for r in texture_results]
            unburned_sums = [r.runoff_unburned_sum for r in texture_results]

            lines.append(
                f"| {veg_type} | {SEVERITY_NAMES[severity]} | burned | "
                f"{np.mean(burned_means):.2f} | {np.mean(burned_stds):.2f} | "
                f"{np.mean(burned_medians):.2f} | {sum(burned_sums):,.0f} |"
            )
            lines.append(
                f"| | | unburned | "
                f"{np.mean(unburned_means):.2f} | {np.mean(unburned_stds):.2f} | "
                f"{np.mean(unburned_medians):.2f} | {sum(unburned_sums):,.0f} |"
            )

    lines.append("")
    lines.append("### Sediment Delivery Descriptive Statistics (kg/m)")
    lines.append("")
    lines.append("| Veg Type | Severity | Condition | Mean | Std Dev | Median | Total |")
    lines.append("|----------|----------|-----------|-----:|--------:|-------:|------:|")

    for veg_type in VEG_TYPES:
        for severity in [1, 2, 3]:
            texture_results = [r for r in results
                              if r.veg_type == veg_type and r.severity == severity]
            if not texture_results:
                continue

            burned_means = [r.sed_burned_mean for r in texture_results]
            burned_stds = [r.sed_burned_std for r in texture_results]
            burned_medians = [r.sed_burned_median for r in texture_results]
            burned_sums = [r.sed_burned_sum for r in texture_results]

            unburned_means = [r.sed_unburned_mean for r in texture_results]
            unburned_stds = [r.sed_unburned_std for r in texture_results]
            unburned_medians = [r.sed_unburned_median for r in texture_results]
            unburned_sums = [r.sed_unburned_sum for r in texture_results]

            lines.append(
                f"| {veg_type} | {SEVERITY_NAMES[severity]} | burned | "
                f"{np.mean(burned_means):.3f} | {np.mean(burned_stds):.3f} | "
                f"{np.mean(burned_medians):.3f} | {sum(burned_sums):.1f} |"
            )
            lines.append(
                f"| | | unburned | "
                f"{np.mean(unburned_means):.3f} | {np.mean(unburned_stds):.3f} | "
                f"{np.mean(unburned_medians):.3f} | {sum(unburned_sums):.1f} |"
            )

    lines.append("")
    lines.append("### Peakflow Descriptive Statistics (m^3/s)")
    lines.append("")
    lines.append("| Veg Type | Severity | Condition | Mean | Std Dev | Median | Total |")
    lines.append("|----------|----------|-----------|-----:|--------:|-------:|------:|")

    for veg_type in VEG_TYPES:
        for severity in [1, 2, 3]:
            texture_results = [r for r in results
                              if r.veg_type == veg_type and r.severity == severity]
            if not texture_results:
                continue

            burned_means = [r.peak_burned_mean for r in texture_results]
            burned_stds = [r.peak_burned_std for r in texture_results]
            burned_medians = [r.peak_burned_median for r in texture_results]
            burned_sums = [r.peak_burned_sum for r in texture_results]

            unburned_means = [r.peak_unburned_mean for r in texture_results]
            unburned_stds = [r.peak_unburned_std for r in texture_results]
            unburned_medians = [r.peak_unburned_median for r in texture_results]
            unburned_sums = [r.peak_unburned_sum for r in texture_results]

            lines.append(
                f"| {veg_type} | {SEVERITY_NAMES[severity]} | burned | "
                f"{np.mean(burned_means):.3f} | {np.mean(burned_stds):.3f} | "
                f"{np.mean(burned_medians):.3f} | {sum(burned_sums):.3f} |"
            )
            lines.append(
                f"| | | unburned | "
                f"{np.mean(unburned_means):.3f} | {np.mean(unburned_stds):.3f} | "
                f"{np.mean(unburned_medians):.3f} | {sum(unburned_sums):.3f} |"
            )

    return "\n".join(lines)


def generate_detailed_texture_markdown(results: List[ComparisonResult]) -> str:
    """Generate markdown tables broken down by texture."""
    lines = []

    lines.append("### Detailed Results by Soil Texture")
    lines.append("")
    lines.append("#### Runoff Event Counts by Texture")
    lines.append("")
    lines.append("| Texture | Veg Type | Severity | Total | Burned > | Equal | Unburned > |")
    lines.append("|---------|----------|----------|------:|---------:|------:|-----------:|")

    for texture in TEXTURES:
        for veg_type in VEG_TYPES:
            for severity in [1, 2, 3]:
                r = next((x for x in results
                          if x.texture == texture and x.veg_type == veg_type
                          and x.severity == severity), None)
                if not r:
                    continue
                lines.append(
                    f"| {texture} | {veg_type} | {SEVERITY_NAMES[severity]} | "
                    f"{r.total_events:,} | {r.runoff_burned_gt:,} | "
                    f"{r.runoff_equal:,} | {r.runoff_unburned_gt:,} |"
                )

    lines.append("")
    lines.append("#### Sediment Delivery Event Counts by Texture")
    lines.append("")
    lines.append("| Texture | Veg Type | Severity | Total | Burned > | Equal | Unburned > |")
    lines.append("|---------|----------|----------|------:|---------:|------:|-----------:|")

    for texture in TEXTURES:
        for veg_type in VEG_TYPES:
            for severity in [1, 2, 3]:
                r = next((x for x in results
                          if x.texture == texture and x.veg_type == veg_type
                          and x.severity == severity), None)
                if not r:
                    continue
                lines.append(
                    f"| {texture} | {veg_type} | {SEVERITY_NAMES[severity]} | "
                    f"{r.total_events:,} | {r.sed_burned_gt:,} | "
                    f"{r.sed_equal:,} | {r.sed_unburned_gt:,} |"
                )

    lines.append("")
    lines.append("#### Peakflow Event Counts by Texture")
    lines.append("")
    lines.append("| Texture | Veg Type | Severity | Total | Burned > | Equal | Unburned > |")
    lines.append("|---------|----------|----------|------:|---------:|------:|-----------:|")

    for texture in TEXTURES:
        for veg_type in VEG_TYPES:
            for severity in [1, 2, 3]:
                r = next((x for x in results
                          if x.texture == texture and x.veg_type == veg_type
                          and x.severity == severity), None)
                if not r:
                    continue
                lines.append(
                    f"| {texture} | {veg_type} | {SEVERITY_NAMES[severity]} | "
                    f"{r.peak_total_events:,} | {r.peak_burned_gt:,} | "
                    f"{r.peak_equal:,} | {r.peak_unburned_gt:,} |"
                )

    return "\n".join(lines)


def generate_full_report(results: List[ComparisonResult]) -> str:
    """Generate the full markdown report."""
    lines = []

    lines.append("## Test Matrix Analysis Results")
    lines.append("")
    lines.append("Analysis of 48 hillslope simulations across:")
    lines.append("- 4 soil textures (clay loam, loam, sand loam, silt loam)")
    lines.append("- 3 vegetation types (forest, shrub, tall grass)")
    lines.append("- 4 burn severities (unburned, low, moderate, high)")
    lines.append("")
    lines.append("**Climate**: MC KENZIE BRIDGE RS, OR - 100 years, ~1,194 mm/yr precipitation")
    lines.append("")
    lines.append("**Slope**: 201.68m variable profile (avg ~43% grade)")
    lines.append("")
    lines.append("**Soil format**: 9002 with hydrophobicity parameters")
    lines.append("")

    lines.append(generate_event_counts_markdown(results))
    lines.append("")
    lines.append(generate_descriptive_stats_markdown(results))
    lines.append("")
    lines.append(generate_detailed_texture_markdown(results))

    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Analyze disturbed matrix test results")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "disturbed_matrix0" / "output",
        help="Path to the output directory containing H*.ebe.dat/H*.pass.dat files"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).parent / "analysis_results.md",
        help="Output markdown file"
    )
    args = parser.parse_args()

    print(f"Loading events from: {args.output_dir}")
    events_by_id = load_all_events(args.output_dir)
    print(f"Loaded {len(events_by_id)} simulations")
    peak_events_by_id = load_all_peak_events(args.output_dir)
    print(f"Loaded peakflow events for {len(peak_events_by_id)} simulations")

    # Summarize event counts
    for wepp_id, events in sorted(events_by_id.items()):
        texture, severity, veg_type = wepp_id_to_params(wepp_id)
        print(f"  H{wepp_id}: {texture}, {veg_type}, {SEVERITY_NAMES[severity]} - {len(events)} events")

    print("\nAnalyzing comparisons...")
    results = analyze_all_comparisons(events_by_id, peak_events_by_id)
    print(f"Generated {len(results)} comparison results")

    # Generate report
    report = generate_full_report(results)

    # Write to file
    with open(args.out, 'w') as f:
        f.write(report)
    print(f"\nReport written to: {args.out}")

    # Also print to stdout
    print("\n" + "=" * 80)
    print(report)


if __name__ == "__main__":
    main()
