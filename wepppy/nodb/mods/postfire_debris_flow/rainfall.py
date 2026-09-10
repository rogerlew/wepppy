"""Climate snapshot adapters for fixed-predictor local M1 scenarios."""
from __future__ import annotations

import calendar
import csv
from dataclasses import dataclass
import math
from pathlib import Path
from collections.abc import Mapping

import numpy as np

from .rainfall_io import (RainfallError, MAX_TEXT, fail, number, pinned, read_table)

__all__ = ['RainfallError', 'RainfallInputs']
DURATIONS = (15, 30, 60)
INTERVALS = (1, 2, 5, 10)


@dataclass(frozen=True)
class RainfallInputs:
    predictor_manifest: Path
    cli_parquet: Path
    expected_sha256: Mapping[str, str]
    project_id: str
    climate_mode: str
    date_semantics: str
    assessment_id: str
    cli_frequency_csv: Path | None = None
    noaa_csv: Path | None = None


def selections(values, supported, name):
    if not isinstance(values, (tuple, list)) or not values or len(values) > len(supported):
        fail('invalid_input', f'Invalid {name} sequence')
    if any(type(v) is not int or v not in supported for v in values) or len(set(values)) != len(values):
        fail('invalid_input', f'Unsupported or duplicate {name}')
    return tuple(sorted(values))


def identity(inputs):
    for key in ('project_id', 'climate_mode', 'assessment_id'):
        v = getattr(inputs, key)
        if not isinstance(v, str) or not v.strip() or len(v) > 256:
            fail('invalid_input', f'Invalid {key}')
    if inputs.date_semantics not in ('simulation_labels', 'calendar'):
        fail('invalid_input', 'Explicit date semantics required')
    return {k: getattr(inputs, k) for k in ('project_id','climate_mode','assessment_id','date_semantics')}


def _date_status(y, m, d, semantics):
    if any(v is None or not math.isfinite(v) or v != int(v) for v in (y,m,d)):
        return 'invalid_or_missing'
    if not 1 <= m <= 12 or y < 1 or (semantics == 'calendar' and y > 9999):
        return 'invalid_or_missing'
    # Simulation labels use their source year for leap-day validity, never ISO dates.
    if not 1 <= d <= calendar.monthrange(int(y), int(m))[1]:
        return 'invalid_or_missing'
    return semantics


def climate_events(inputs, durations, consumed):
    p = pinned(inputs.cli_parquet, inputs.expected_sha256, consumed)
    table = read_table(p, max_rows=200_000, numeric=True)
    if not {'prcp','year'} <= set(table.column_names):
        fail('invalid_input', 'CLI parquet requires prcp and year')
    df = table.to_pandas(ignore_metadata=True)
    if not np.isfinite(df.prcp).all() or (df.prcp < 0).any():
        fail('invalid_input', 'Precipitation must be finite and nonnegative')
    rows = []
    wet = df[df.prcp > 0]
    years = df.year.dropna()
    wet_years = wet.year.dropna()
    valid_years = years[np.isfinite(years) & (years == np.floor(years))]
    year_valid = bool(np.isfinite(wet.year).all() and (wet.year == np.floor(wet.year)).all())
    info = {'record_rows': len(df), 'wet_events': len(wet),
            'represented_years': int(valid_years.nunique()),
            'year_min': float(valid_years.min()) if len(valid_years) else None,
            'year_max': float(valid_years.max()) if len(valid_years) else None,
            'wet_years': int(wet_years.nunique()) if year_valid else None,
            'positive_samples': {}, 'frequency_method': 'Climate weibull_series pds',
            'invalid_wet_year_labels': not year_valid}
    for duration in durations:
        col = f'peak_intensity_{duration}'
        values = wet[col] if col in wet else None
        info['positive_samples'][str(duration)] = int((np.isfinite(values) & (values > 0)).sum()) if values is not None else 0
    for ordinal, event in wet.iterrows():
        fields = {key: (float(event[key]) if key in event and np.isfinite(event[key]) else None)
                  for key in ('year','month','day_of_month','sim_day_index')}
        common = {'event_id': f'{consumed[str(p)]}:{ordinal}', 'row_ordinal': int(ordinal),
                  **fields, 'precipitation_mm': float(event.prcp),
                  'date_status': _date_status(fields['year'],fields['month'],fields['day_of_month'],inputs.date_semantics)}
        for duration in durations:
            col = f'peak_intensity_{duration}'
            v = float(event[col]) if col in event else None
            reason = ('missing_duration' if v is None else 'missing_intensity' if math.isnan(v)
                      else 'nonfinite_intensity' if not math.isfinite(v) else 'negative_intensity' if v < 0 else None)
            rows.append({**common, **rainfall_row(duration, v if reason is None else None, reason)})
    return rows, df, info


def rainfall_row(duration, intensity, reason=None):
    return {'duration_minutes': duration, 'intensity_mm_per_hour': intensity,
            'rainfall_mm': None if intensity is None else intensity * (duration / 60),
            'probability': None, 'status': 'available' if reason is None else 'unavailable', 'reason': reason}


def frequency_csv(path, expected, consumed, *, source):
    p = pinned(path, expected, consumed, MAX_TEXT)
    try:
        lines = p.read_text().splitlines()
    except UnicodeError as exc:
        raise RainfallError('invalid_input', 'CSV must be UTF-8 text') from exc
    title = ('Point precipitation frequency estimates (millimeters/hour)' if source == 'noaa'
             else 'Point precipitation frequency estimates (mm, hours, mm/hour)')
    if not lines or lines[0] != title or 'Time series type: Partial duration' not in lines:
        fail('invalid_input', 'Unsupported frequency units/time-series type')
    data_type = 'Data type: Precipitation intensity' if source == 'noaa' else 'Data type: Precipitation depth, storm duration, peak intensities'
    if data_type not in lines or lines.count('PRECIPITATION FREQUENCY ESTIMATES') != 1:
        fail('invalid_input', 'Expected mean intensity frequency table')
    if len(lines) < 2 or (not lines[1].startswith('NOAA Atlas 14 Volume ') if source == 'noaa'
                          else lines[1] != 'WEPP CLI derived precipitation frequency statistics'):
        fail('invalid_input', 'Unrecognized frequency source')
    prefix = 'by duration for ARI (years):' if source == 'noaa' else 'by metric for ARI (years):'
    headers = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(headers) != 1:
        fail('invalid_input', 'Expected one frequency header')
    start = headers[0]
    metadata = {}
    for line in lines[:start]:
        if ':' in line:
            key, value = line.split(':',1)
            if key in metadata:
                fail('invalid_input', 'Duplicate frequency metadata')
            metadata[key] = value.strip()
    for key, bound in (('Latitude',90),('Longitude',180)):
        try:
            value = float(metadata[key].removesuffix(' Degree'))
        except (KeyError, ValueError) as exc:
            raise RainfallError('invalid_input', 'Missing frequency location') from exc
        if not math.isfinite(value) or abs(value) > bound:
            fail('invalid_input', 'Invalid frequency location')
    try:
        periods = [float(v.strip()) for v in next(csv.reader([lines[start]]))[1:]]
        if not periods or len(periods) > 100 or any(not math.isfinite(v) or v <= 0 for v in periods) or len(set(periods)) != len(periods):
            fail('invalid_input', 'Invalid or duplicate return intervals')
        data = {}
        for line in lines[start+1:]:
            if not line.strip():
                break
            cells = next(csv.reader([line]))
            label = cells[0].strip().removesuffix(':')
            values = [float(v.strip()) for v in cells[1:]]
            if label in data or len(values) != len(periods) or any(not math.isfinite(v) or v < 0 for v in values):
                fail('invalid_input', 'Invalid/duplicate frequency row')
            data[label] = dict(zip(periods, values))
    except (ValueError, csv.Error) as exc:
        if isinstance(exc, RainfallError):
            raise
        raise RainfallError('invalid_input', 'Malformed frequency values') from exc
    return {'metadata': metadata, 'periods': periods, 'data': data, 'title': lines[1]}


def noaa_design(parsed, intervals, durations):
    rows = []
    for interval in intervals:
        for duration in durations:
            v = None if parsed is None else parsed['data'].get(f'{duration}-min', {}).get(interval)
            reason = 'missing_noaa' if parsed is None else 'unsupported_combination' if v is None else 'zero_placeholder' if v == 0 else None
            rows.append({**rainfall_row(duration, v if reason is None else None, reason),
                         'return_interval_years': interval, 'source': 'noaa',
                         'rank_index': None, 'positive_samples': None})
    return rows


def cli_design(df, intervals, durations, info, parsed=None):
    """Use Climate's full rank context, exposing unsupported ranks per ADR-0062."""
    from wepppy.all_your_base.stats import weibull_series
    wet = df[df.prcp > 0]
    years = info['wet_years']
    context = [v for v in (1,2,5,10,25,50,100) if years is not None and v <= years]
    ranks = weibull_series(context,years,method='pds') if context else {}
    info['recurrence_context'] = context
    info['rank_indices'] = {str(k):v for k,v in ranks.items()}
    if parsed is not None and parsed['periods'] != context:
        fail('provenance_mismatch', 'CLI CSV recurrence context differs from parquet')
    rows = []
    for duration in durations:
        column = f'peak_intensity_{duration}'
        samples = wet[column] if column in wet else None
        positive = samples[samples > 0].sort_values(ascending=False).reset_index(drop=True) if samples is not None else None
        count = len(positive) if positive is not None else 0
        nonfinite_positive = bool(count and not np.isfinite(positive).all())
        # Compare the whole Climate-owned recurrence request, including CSV
        # placeholder/clamping behavior. Rounded CSV is evidence, never input.
        if parsed is not None:
            csv_values = parsed['data'].get(f'{duration}-min intensity (mm/hour)')
            if csv_values is None:
                fail('provenance_mismatch', 'CLI parity CSV lacks duration row')
            for interval in context:
                rank = ranks.get(float(interval),0)
                value = float(positive.iloc[min(rank,count-1)]) if count else 0.
                if not math.isfinite(value) or csv_values[interval] != float(f'{value:.2f}'):
                    fail('provenance_mismatch', 'CLI rounded frequency differs from parquet ranks')
        for interval in intervals:
            rank = ranks.get(float(interval),0) if interval in context else None
            reason = ('invalid_year_labels' if info['invalid_wet_year_labels'] else
                      'unsupported_record_length' if interval not in context else
                      'missing_duration' if samples is None else 'no_positive_samples' if not count else
                      'nonfinite_intensity' if nonfinite_positive else None)
            if reason is None and rank >= count:
                reason = 'insufficient_positive_samples'
            intensity = float(positive.iloc[rank]) if reason is None else None
            if intensity is not None and not math.isfinite(intensity):
                reason, intensity = 'nonfinite_intensity', None
            rows.append({**rainfall_row(duration,intensity,reason),
                         'return_interval_years':interval,'source':'cli','rank_index':rank,
                         'positive_samples':info['positive_samples'][str(duration)]})
    rows.sort(key=lambda row:(row['return_interval_years'],row['duration_minutes']))
    return rows
