"""Collect-and-finalize contracts for multiple-interpolated climate builds."""

from __future__ import annotations

from dataclasses import dataclass
from os.path import abspath
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wepppy.nodb.core.climate import Climate


__all__ = [
    "ClimateMultipleBuildInputError",
    "ClimateMultipleBuildSupersededError",
    "ClimateMultipleBuildInputs",
    "ClimateMultipleBuildResult",
    "capture_multiple_build_inputs",
    "finalize_multiple_build",
]


class ClimateMultipleBuildInputError(ValueError):
    """Raised when a multiple-build input snapshot cannot be established."""


class ClimateMultipleBuildSupersededError(RuntimeError):
    """Raised when collected outputs no longer match durable climate inputs."""

    def __init__(self, changed_fields: tuple[str, ...]) -> None:
        self.changed_fields = changed_fields
        fields = ", ".join(changed_fields)
        super().__init__(
            "multiple-interpolated climate build superseded by changed inputs: "
            f"{fields}"
        )


@dataclass(frozen=True)
class ClimateMultipleBuildInputs:
    """Persisted climate values that determine multiple-build outputs."""

    observed_start_year: int
    observed_end_year: int
    climatestation: Any
    cligen_db: Any
    cli_dir: str
    adjust_mx_pt5: bool
    silent_pass_observed_quality_guard: bool
    use_gridmet_wind_when_applicable: bool
    climate_mode: Any
    climate_spatialmode: Any

    def changed_fields(self, current: "ClimateMultipleBuildInputs") -> tuple[str, ...]:
        changed = []
        for field_name in self.__dataclass_fields__:
            if getattr(self, field_name) != getattr(current, field_name):
                changed.append(field_name)
        return tuple(changed)


@dataclass(frozen=True)
class ClimateMultipleBuildResult:
    """Derived fields collected without mutating or serializing Climate state."""

    monthlies: Any
    cli_fn: str
    par_fn: str
    sub_par_fns: dict[Any, str]
    sub_cli_fns: dict[Any, str]
    input_years: int
    quality_guard_bypassed: bool


def _parse_observed_year(raw_value: Any, field_name: str) -> int:
    if isinstance(raw_value, bool):
        raise ClimateMultipleBuildInputError(
            f"{field_name} must be an integer year, got {raw_value!r}"
        )
    if isinstance(raw_value, str):
        raw_value = raw_value.strip()
        if raw_value == "":
            raise ClimateMultipleBuildInputError(
                f"{field_name} must be an integer year, got empty string"
            )
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ClimateMultipleBuildInputError(
            f"{field_name} must be an integer year, got {raw_value!r}"
        ) from exc


def capture_multiple_build_inputs(climate: "Climate") -> ClimateMultipleBuildInputs:
    """Capture and validate the persisted inputs used by both builders."""

    start_year = _parse_observed_year(
        getattr(climate, "_observed_start_year", None),
        "observed_start_year",
    )
    end_year = _parse_observed_year(
        getattr(climate, "_observed_end_year", None),
        "observed_end_year",
    )
    if end_year < start_year:
        raise ClimateMultipleBuildInputError(
            "observed_end_year must be greater than or equal to "
            f"observed_start_year ({end_year} < {start_year})"
        )

    return ClimateMultipleBuildInputs(
        observed_start_year=start_year,
        observed_end_year=end_year,
        climatestation=getattr(climate, "climatestation", None),
        cligen_db=getattr(climate, "cligen_db", None),
        cli_dir=abspath(str(getattr(climate, "cli_dir"))),
        adjust_mx_pt5=bool(getattr(climate, "adjust_mx_pt5", False)),
        silent_pass_observed_quality_guard=bool(
            getattr(climate, "silent_pass_observed_quality_guard", True)
        ),
        use_gridmet_wind_when_applicable=bool(
            getattr(climate, "use_gridmet_wind_when_applicable", True)
        ),
        climate_mode=getattr(climate, "_climate_mode", None),
        climate_spatialmode=getattr(climate, "_climate_spatialmode", None),
    )


def finalize_multiple_build(
    climate: "Climate",
    snapshot: ClimateMultipleBuildInputs,
    result: ClimateMultipleBuildResult,
) -> None:
    """Refresh durable state and publish collected fields in one short lock."""

    with climate.locked():
        refreshed = climate._refresh_multiple_build_state()

        try:
            current_inputs = capture_multiple_build_inputs(refreshed)
        except ClimateMultipleBuildInputError as exc:
            raise ClimateMultipleBuildSupersededError(("malformed climate inputs",)) from exc

        changed_fields = snapshot.changed_fields(current_inputs)
        if changed_fields:
            raise ClimateMultipleBuildSupersededError(changed_fields)

        refreshed._input_years = result.input_years
        refreshed.monthlies = result.monthlies
        refreshed.cli_fn = result.cli_fn
        refreshed.par_fn = result.par_fn
        refreshed.sub_par_fns = result.sub_par_fns
        refreshed.sub_cli_fns = result.sub_cli_fns
        refreshed._publish_quality_guard_bypass_warning_if_needed(
            quality_guard_bypassed=result.quality_guard_bypassed
        )
