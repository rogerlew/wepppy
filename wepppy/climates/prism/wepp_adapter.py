"""Convert raw PRISM cells to observed CLIGEN inputs without modifying sources.

Scientific contract: docs/schemas/prism-historic-climate-contract.md / ADR-0082.
"""
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd

from wepppy.climates.cligen import ClimateFile, df_to_prn

__all__ = ['validate_years', 'build_cell', 'floor_dewpoint', 'read_cli', 'validate_cli']
MJ_TO_LANGLEYS = 1_000_000.0 / 41840.0


def validate_years(start, end):
    if not 1981 <= start <= end < date.today().year:
        raise ValueError(f"PRISM requires complete years from 1981 through {date.today().year - 1}")


def read_cli(path):
    frame = ClimateFile(str(path)).as_dataframe()
    frame.index = pd.to_datetime(dict(year=frame.year, month=frame.mo, day=frame.da))
    return frame


def validate_cli(path, dates):
    frame = read_cli(path)
    if not frame.index.equals(pd.DatetimeIndex(dates)):
        raise ValueError(f'PRISM CLI calendar mismatch: {path}')
    columns = ['prcp', 'tmax', 'tmin', 'rad', 'w-vl', 'w-dir', 'tdew']
    if (not np.isfinite(frame[columns].to_numpy()).all()
            or (frame[['prcp', 'rad', 'w-vl']] < 0).any().any()
            or (frame.tmin > frame.tmax).any()
            or (frame.tdew < frame.tmin).any()):
        raise ValueError(f'Invalid PRISM-derived CLI weather: {path}')
    return frame


def floor_dewpoint(path, raw_tdmean, diagnostic):
    """Use raw Td even after monthly revision; a cooler hill must lose the WS floor."""
    frame = read_cli(path)
    if not frame.index.equals(raw_tdmean.index):
        raise ValueError('PRISM dewpoint calendar mismatch')
    adjusted = np.maximum(raw_tdmean.to_numpy(), frame.tmin.to_numpy())
    cli = ClimateFile(str(path))
    cli.replace_var('tdew', frame.index, adjusted)
    cli.write(str(path))
    pd.DataFrame({'raw_tdmean_C': raw_tdmean.to_numpy(), 'final_tmin_C': frame.tmin.to_numpy(),
                  'derived_tdmean_C': adjusted}, index=frame.index).to_csv(diagnostic, index_label='date')
    validate_cli(path, frame.index)


def build_cell(cligen, frame, wind, directory, stem, *, seed=None,
               adjust_mx_pt5=False, silent_pass_observed_quality_guard=False):
    """Generate one shared cell climate using existing PRN quantization and seed."""
    from wepppy.nodb.core.climate_build_helpers import _run_observed_with_quality_guard_handling

    directory = Path(directory)
    if (not frame.index.equals(wind.index)
            or not np.isfinite(wind[['vs(m/s)', 'th(DegreesClockwisefromnorth)']].to_numpy()).all()
            or (wind['vs(m/s)'] < 0).any()):
        raise ValueError('GridMET wind must cover every PRISM date with finite values')
    prn, cli_name = stem + '.prn', stem + '.cli'
    # df_to_prn mutates units; raw/cache/project source data remain unchanged.
    working = frame.rename(columns={'ppt': 'ppt(mm)'}).copy(deep=True)
    df_to_prn(working, str(directory / prn), 'ppt(mm)', 'tmax', 'tmin',
              pad_to_end_of_year=False, reject_internal_missing=True)
    _run_observed_with_quality_guard_handling(
        cligen, prn, cli_name, adjust_mx_pt5=adjust_mx_pt5,
        silent_pass_observed_quality_guard=silent_pass_observed_quality_guard, randseed=seed,
    )
    path = directory / cli_name
    cli = ClimateFile(str(path))
    cli.replace_var('rad', frame.index, frame.soltotal * MJ_TO_LANGLEYS)
    cli.replace_var('w-vl', frame.index, wind['vs(m/s)'])
    cli.replace_var('w-dir', frame.index, wind['th(DegreesClockwisefromnorth)'])
    cli.write(str(path))
    floor_dewpoint(path, frame.tdmean, directory / (stem + '-dewpoint.csv'))
    actual = validate_cli(path, frame.index)
    expected_ppt = np.round(frame.ppt / 25.4 * 100) * 0.254
    expected = {'prcp': expected_ppt,
                'tmax': (np.round(frame.tmax * 1.8 + 32) - 32) / 1.8,
                'tmin': (np.round(frame.tmin * 1.8 + 32) - 32) / 1.8,
                'rad': frame.soltotal * MJ_TO_LANGLEYS,
                'w-vl': wind['vs(m/s)'], 'w-dir': wind['th(DegreesClockwisefromnorth)']}
    for column, values in expected.items():
        tolerance = 0.501 if column in ('rad', 'w-dir') else 0.101
        if not np.allclose(actual[column], values, atol=tolerance, rtol=0):
            raise ValueError(f'PRISM CLI {column} differs from expected quantized forcing: {path}')
    pd.DataFrame({'raw_ppt_mm': frame.ppt, 'prn_ppt_mm': expected_ppt,
                  'trace_rain_rounded_to_zero': (frame.ppt > 0) & (expected_ppt == 0),
                  'raw_soltotal_MJ_m2_day': frame.soltotal, 'cli_rad_langley_day': actual.rad},
                 index=frame.index).to_csv(directory / (stem + '-conversion.csv'), index_label='date')
    return prn, cli_name
