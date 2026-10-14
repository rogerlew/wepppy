"""Local future EDDE selections; no network work during request parsing."""
from __future__ import annotations

__all__ = ['EDDE_PROJECTIONS', 'EddeSelectionError', 'validate_edde_selection']

EDDE_PROJECTIONS = {
    'WRF-MPI/SSP2-4.5': 2099,
    'WRF-MPI/SSP3-7.0': 2099,
    'WRF-Nor/SSP2-4.5': 2079,
}


class EddeSelectionError(ValueError):
    """Safe, actionable EDDE selection failure for the request boundary."""

    def __init__(self, message, field):
        super().__init__(message)
        self.field = field


def _year(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise EddeSelectionError(f'{field} must be an integer year', field)
    if isinstance(value, str) and (not value.strip().isascii() or not value.strip().isdigit()):
        raise EddeSelectionError(f'{field} must be an integer year', field)
    return int(value)


def validate_edde_selection(projection, start, end, *, locales, spatial_mode, scaling_mode):
    """Return validated model, scenario and years without coercing invalid input."""
    if not isinstance(projection, str) or projection not in EDDE_PROJECTIONS:
        raise EddeSelectionError('Select an available EDDE driving model/scenario', 'edde_projection')
    if not set(locales).intersection(('us', 'canada', 'bc-ca')):
        raise EddeSelectionError('Future EDDE is available only for continental US and Canadian projects', 'climate_catalog_id')
    if int(spatial_mode) not in (0, 1):
        raise EddeSelectionError('Future EDDE supports Single or Multiple PRISM only', 'climate_spatialmode')
    from .climate import ClimatePrecipScalingMode
    if scaling_mode == ClimatePrecipScalingMode.AnnualMonthlies:
        raise EddeSelectionError('AnnualMonthlies scaling requires observed data and is unavailable for future EDDE', 'precip_scaling_mode')
    start, end = _year(start, 'future_start_year'), _year(end, 'future_end_year')
    maximum = EDDE_PROJECTIONS[projection]
    if not 2025 <= start <= end <= maximum:
        raise EddeSelectionError(f'EDDE years must be ordered full calendar years within 2025–{maximum}', 'future_start_year' if start < 2025 or start > maximum else 'future_end_year')
    model, scenario = projection.split('/')
    return model, scenario, start, end
