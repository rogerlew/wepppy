"""Disturbed native openWEPP Lane-D route-coefficient defaults."""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence, Tuple

ROUTE_COEFFICIENT_COLUMNS: Tuple[str, ...] = (
    'route_skin_friction_coefficient_ko',
    'route_form_drag_coefficient',
    'route_roughness_element_height_m',
    'route_roughness_concentration',
    'route_vegetation_drag_coefficient',
)

ROUTE_COEFFICIENT_PROVENANCE_COLUMNS: Tuple[str, ...] = (
    'route_coeff_source_ref',
    'route_coeff_authority_class',
    'route_coeff_confidence',
    'route_coeff_notes',
)

ROUTE_COEFFICIENT_ALL_COLUMNS: Tuple[str, ...] = (
    *ROUTE_COEFFICIENT_COLUMNS,
    *ROUTE_COEFFICIENT_PROVENANCE_COLUMNS,
)

ROUTE_COEFFICIENT_SOURCE_REF = (
    'ADR-0014; openWEPP WP '
    '20260707-laned-router-d16-hybrid-disturbed-route-coeff-source-acquisition-001'
)
ROUTE_COEFFICIENT_AUTHORITY_CLASS = 'operator_calibration'
ROUTE_COEFFICIENT_CONFIDENCE = 'bounded_class_calibration'

# Values are ordered as:
# k_o, form C_d, roughness height D_r (m), roughness concentration lambda, vegetation C_d.
# They are explicit Disturbed native parameters, not mechanical transforms from
# legacy WEPP row/ridge/cover/residue fields.
DISTURBED_ROUTE_COEFFICIENT_DEFAULTS: Dict[str, Tuple[float, float, float, float, float]] = {
    'agriculture crops': (480.0, 0.25, 0.010, 0.050, 0.12),
    'bare': (540.0, 0.00, 0.000, 0.000, 0.00),
    'deciduous forest': (420.0, 0.90, 0.050, 0.180, 0.65),
    'forest': (410.0, 0.95, 0.060, 0.200, 0.75),
    'forest high sev fire': (530.0, 0.18, 0.006, 0.018, 0.08),
    'forest low sev fire': (465.0, 0.58, 0.026, 0.085, 0.34),
    'forest moderate sev fire': (490.0, 0.40, 0.016, 0.050, 0.20),
    'forest prescribed fire': (450.0, 0.70, 0.035, 0.110, 0.45),
    'grass high sev fire': (530.0, 0.08, 0.003, 0.010, 0.04),
    'grass low sev fire': (475.0, 0.27, 0.010, 0.045, 0.15),
    'grass moderate sev fire': (500.0, 0.18, 0.007, 0.026, 0.09),
    'grass prescribed fire': (465.0, 0.32, 0.012, 0.055, 0.18),
    'high use skid': (575.0, 0.03, 0.000, 0.000, 0.00),
    'low or treated skid': (545.0, 0.12, 0.006, 0.020, 0.03),
    'mixed forest': (415.0, 0.92, 0.055, 0.190, 0.70),
    'mulch': (420.0, 0.85, 0.040, 0.180, 0.20),
    'short grass': (460.0, 0.34, 0.014, 0.070, 0.24),
    'shrub': (430.0, 0.72, 0.035, 0.120, 0.45),
    'shrub high sev fire': (525.0, 0.14, 0.004, 0.014, 0.06),
    'shrub low sev fire': (465.0, 0.44, 0.020, 0.065, 0.24),
    'shrub moderate sev fire': (490.0, 0.30, 0.012, 0.038, 0.14),
    'shrub prescribed fire': (450.0, 0.55, 0.026, 0.090, 0.32),
    'skid': (560.0, 0.05, 0.000, 0.000, 0.00),
    'tall grass': (440.0, 0.48, 0.020, 0.100, 0.35),
    'thinning': (435.0, 0.90, 0.045, 0.160, 0.50),
    'young forest': (430.0, 0.85, 0.045, 0.160, 0.60),
}

TREATMENT_SUFFIXES = ('-mulch_15', '-mulch_30', '-mulch_60', '-thinning', '-prescribed_fire')


def normalize_disturbed_route_class(disturbed_class: Optional[str]) -> str:
    if disturbed_class is None:
        raise ValueError('disturbed_class is required for route coefficients')

    route_class = str(disturbed_class).strip()
    if not route_class:
        raise ValueError('disturbed_class is required for route coefficients')

    for suffix in TREATMENT_SUFFIXES:
        if route_class.endswith(suffix):
            route_class = route_class[:-len(suffix)]
            break

    if route_class == 'forest prescribed fire':
        route_class = 'forest prescribed fire'

    if 'mulch' in route_class and route_class not in DISTURBED_ROUTE_COEFFICIENT_DEFAULTS:
        route_class = 'mulch'
    elif 'thinning' in route_class and route_class not in DISTURBED_ROUTE_COEFFICIENT_DEFAULTS:
        route_class = 'young forest'

    if route_class not in DISTURBED_ROUTE_COEFFICIENT_DEFAULTS:
        raise KeyError(f"No disturbed route-coefficient defaults for {disturbed_class!r}")
    return route_class


def route_coefficient_values_for_class(disturbed_class: Optional[str]) -> Tuple[float, float, float, float, float]:
    return DISTURBED_ROUTE_COEFFICIENT_DEFAULTS[normalize_disturbed_route_class(disturbed_class)]


def route_coefficient_defaults_for_class(disturbed_class: Optional[str]) -> Dict[str, Any]:
    route_class = normalize_disturbed_route_class(disturbed_class)
    values = DISTURBED_ROUTE_COEFFICIENT_DEFAULTS[route_class]
    row = dict(zip(ROUTE_COEFFICIENT_COLUMNS, values))
    row.update(
        route_coeff_source_ref=ROUTE_COEFFICIENT_SOURCE_REF,
        route_coeff_authority_class=ROUTE_COEFFICIENT_AUTHORITY_CLASS,
        route_coeff_confidence=ROUTE_COEFFICIENT_CONFIDENCE,
        route_coeff_notes=f'texture_invariant; route_class={route_class}',
    )
    return row


def routing_coefficients_from_row(row: Dict[str, Any]) -> Tuple[float, float, float, float, float]:
    return tuple(float(row[column]) for column in ROUTE_COEFFICIENT_COLUMNS)


def validate_route_coefficient_row(row: Dict[str, Any]) -> None:
    values = routing_coefficients_from_row(row)
    for column, value in zip(ROUTE_COEFFICIENT_COLUMNS, values):
        if not math.isfinite(value):
            raise ValueError(f'{column} must be finite; got {value!r}')

    ko, form_cd, roughness_height, roughness_concentration, veg_cd = values
    if ko <= 0:
        raise ValueError('route_skin_friction_coefficient_ko must be > 0')
    if form_cd < 0:
        raise ValueError('route_form_drag_coefficient must be >= 0')
    if roughness_height < 0:
        raise ValueError('route_roughness_element_height_m must be >= 0')
    if roughness_concentration < 0 or roughness_concentration > 1:
        raise ValueError('route_roughness_concentration must be in [0, 1]')
    if veg_cd < 0:
        raise ValueError('route_vegetation_drag_coefficient must be >= 0')
    if (roughness_height == 0) != (roughness_concentration == 0):
        raise ValueError(
            'route_roughness_element_height_m and route_roughness_concentration '
            'must both be zero or both be positive'
        )
    if veg_cd == 0:
        route_class = normalize_disturbed_route_class(row.get('disturbed_class') or row.get('luse'))
        if route_class not in {'bare', 'high use skid', 'skid'}:
            raise ValueError(
                'route_vegetation_drag_coefficient may be zero only for bare/high-use-skid/skid surfaces'
            )
    for column in ROUTE_COEFFICIENT_PROVENANCE_COLUMNS:
        if not str(row.get(column, '')).strip():
            raise ValueError(f'{column} is required')
    if row.get('route_coeff_authority_class') == 'unsupported':
        raise ValueError('unsupported route coefficient authority is not acceptable')


def enrich_route_coefficient_row(row: Dict[str, Any]) -> Dict[str, Any]:
    defaults = route_coefficient_defaults_for_class(row.get('disturbed_class') or row.get('luse'))
    for column, value in defaults.items():
        row[column] = value
    validate_route_coefficient_row(row)
    return row


def validate_route_coefficient_rows(rows: Sequence[Dict[str, Any]]) -> None:
    for row in rows:
        validate_route_coefficient_row(row)
