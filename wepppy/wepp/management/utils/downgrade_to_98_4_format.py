"""Helpers for exporting modern WEPP management files to 98.4-compatible format."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Iterable, List, Optional

if False:  # pragma: no cover - import for typing only
    from wepppy.wepp.management.managements import Management


def downgrade_to_98_4_format(
    management: 'Management',
    filepath: str | Path,
    resurfacing_fraction_mode: str = 'fallback',
    unsupported_operation_mode: str = 'fallback',
    first_year_only: bool = False,
) -> Path:
    """Downgrade a 2016.3+ management to 98.4 and write it to disk.

    Parameters
    ----------
    management : Management
        Source management object to convert.
    filepath : str or pathlib.Path
        Destination path for the exported `.man` file.
    resurfacing_fraction_mode : {'strict', 'fallback'}
        Controls how residue resurfacing fractions (`resurf1`, `resurnf1`,
        unitless fractions in the range 0–1) are handled.

        * ``'strict'`` aborts when a resurfacing fraction is non-zero because
          WEPP 98.4 has no analogue for that behaviour.
        * ``'fallback'`` zeroes the resurfacing fractions, records the original
          values in a conversion note, and documents in the exported management
          file that resurfacing is not simulated.
    unsupported_operation_mode : {'strict', 'fallback'}
        Controls how 2016.3-only operation codes (e.g. 17, herbicide
        application) are handled.

        * ``'strict'`` aborts when an unsupported code is encountered.
        * ``'fallback'`` maps code 17 to code 4 ("other") and records a note in
          the exported management explaining that herbicide behaviour is not
          simulated in 98.4.
    first_year_only : bool, optional
        When ``True`` and the management contains multiple yearly rotations,
        retain only the first year while adjusting the simulation length to a
        single year.

    Returns
    -------
    pathlib.Path
        The path that was written.

    Raises
    ------
    ValueError
        If 2016.3+ features are present that 98.4 cannot express under the
        chosen downgrade mode.
    """

    if resurfacing_fraction_mode not in ('strict', 'fallback'):
        raise ValueError(
            "resurfacing_fraction_mode must be 'strict' or 'fallback'"
        )

    if unsupported_operation_mode not in ('strict', 'fallback'):
        raise ValueError(
            "unsupported_operation_mode must be 'strict' or 'fallback'"
        )

    def _has_meaningful_value(val: object) -> bool:
        if val in ('', None):
            return False
        if isinstance(val, (int, float)):
            return abs(val) > 1e-9
        return True

    def _apply_first_year_only(mf_obj: 'Management') -> bool:
        """Trim management rotations down to a single exported year."""

        man_section = getattr(mf_obj, 'man', None)
        loops = getattr(man_section, 'loops', None) if man_section is not None else None

        if not loops:
            return False

        trimmed = False

        if len(loops) > 1:
            del loops[1:]
            trimmed = True

        first_rotation = loops[0]
        years_collection = getattr(first_rotation, 'years', None)

        if years_collection and len(years_collection) > 1:
            del years_collection[1:]
            trimmed = True

        if years_collection and len(years_collection) >= 1:
            first_year = years_collection[0]
            if hasattr(first_year, '__iter__'):
                for ofe_index, schedule in enumerate(first_year):
                    if hasattr(schedule, '_year'):
                        schedule._year = 1
                    if hasattr(schedule, '_ofe'):
                        schedule._ofe = ofe_index + 1

        if trimmed:
            mf_obj.sim_years = 1
            if hasattr(man_section, 'setroot'):
                man_section.setroot(mf_obj)

        return trimmed

    mf = deepcopy(management)
    errors = []
    general_notes = []
    resurfacing_notes = []
    operation_fallback_notes = []

    if first_year_only:
        if _apply_first_year_only(mf):
            general_notes.append(
                "# Conversion note: Only the first rotation year was exported; simulation length forced to 1 year."
            )

    # Plant section
    for plant in mf.plants:
        data = plant.data
        if hasattr(data, 'rcc'):
            if _has_meaningful_value(data.rcc):
                errors.append(
                    f"Plant scenario '{plant.name}' uses release canopy cover which"
                    " cannot be represented in 98.4 format."
                )
            data.rcc = ''

    # Operation section
    valid_pcodes = [1, 2, 3, 4, 10, 11, 12, 13]
    for op in mf.ops:
        if op.landuse != 1:
            continue

        data = op.data

        fragile_resurf = 0.0
        non_fragile_resurf = 0.0

        if hasattr(data, 'resurf1'):
            if _has_meaningful_value(data.resurf1):
                if resurfacing_fraction_mode == 'strict':
                    errors.append(
                        f"Operation '{op.name}' has non-zero resurf1 but 98.4 has no resurfacing support."
                    )
                else:
                    fragile_resurf = float(data.resurf1)
            data.resurf1 = ''

        if hasattr(data, 'resurnf1'):
            if _has_meaningful_value(data.resurnf1):
                if resurfacing_fraction_mode == 'strict':
                    errors.append(
                        f"Operation '{op.name}' has non-zero resurnf1 but 98.4 has no resurfacing support."
                    )
                else:
                    non_fragile_resurf = float(data.resurnf1)
            data.resurnf1 = ''

        if resurfacing_fraction_mode == 'fallback' and (
            fragile_resurf > 0.0 or non_fragile_resurf > 0.0
        ):
            resurfacing_notes.append((op.name, fragile_resurf, non_fragile_resurf))

        if data.pcode not in valid_pcodes:
            if data.pcode == 17 and unsupported_operation_mode == 'fallback':
                operation_fallback_notes.append((op.name, data.pcode, 4))
                data.pcode = 4
            else:
                errors.append(
                    f"Operation '{op.name}' uses code {data.pcode}, which is unsupported in 98.4."
                )

        for attr in ['fbma1', 'fbrnol', 'frfmov1', 'frsmov1']:
            if hasattr(data, attr):
                value = getattr(data, attr)
                if _has_meaningful_value(value):
                    errors.append(
                        f"Operation '{op.name}' uses parameter '{attr}' and cannot be converted to 98.4."
                    )
                setattr(data, attr, '')

    # Initial conditions
    for ini in mf.inis:
        if ini.landuse != 1:
            continue

        data = ini.data
        if hasattr(data, 'usinrco'):
            if _has_meaningful_value(data.usinrco):
                errors.append(
                    f"Initial condition '{ini.name}' specifies understory interrill cover,"
                    " which 98.4 cannot represent."
                )
            data.usinrco = ''

        if hasattr(data, 'usrilco'):
            if _has_meaningful_value(data.usrilco):
                errors.append(
                    f"Initial condition '{ini.name}' specifies understory rill cover,"
                    " which 98.4 cannot represent."
                )
            data.usrilco = ''

    # Contours
    for contour in mf.contours:
        if contour.landuse != 1:
            continue

        data = contour.data
        if hasattr(data, 'contours_perm'):
            if _has_meaningful_value(data.contours_perm):
                errors.append(
                    f"Contour scenario '{contour.name}' marks contours as permanent,"
                    " which is unavailable in 98.4."
                )
            data.contours_perm = ''

    if errors:
        raise ValueError("Cannot convert management file to 98.4 format:\n" + "\n".join(errors))

    mf.datver = '98.4'
    mf.datver_value = 98.4

    man_lines = str(mf).splitlines()

    if resurfacing_notes:
        general_notes.append(
            "# Conversion note: Residue resurfacing fractions (dimensionless, 0-1) were set to 0.0"
        )
        general_notes.append(
            "# because WEPP 98.4 cannot store them. Original 2016.3 values:"
        )
        for name, fragile, non_fragile in resurfacing_notes:
            general_notes.append(
                f"# - Operation '{name}': fragile resurfacing={fragile:.5f}, non-fragile resurfacing={non_fragile:.5f}"
            )

    if operation_fallback_notes:
        general_notes.append(
            "# Conversion note: Herbicide operations (code 17) were exported as code 4 ('other')."
        )
        general_notes.append(
            "# WEPP 98.4 does not simulate herbicide applications; management behaviour may differ."
        )
        for name, original_code, mapped_code in operation_fallback_notes:
            general_notes.append(
                f"# - Operation '{name}': original code {original_code} -> exported code {mapped_code}"
            )

    if general_notes:
        man_lines = [man_lines[0], *general_notes, *man_lines[1:]]

    man_text = "\n".join(man_lines)
    if not man_text.endswith("\n"):
        man_text += "\n"

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as fp:
        fp.write(man_text)

    return path
