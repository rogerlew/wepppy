from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

import pandas as pd

from wepppy.all_your_base.dateutils import YearlessDate

from .ash_type import AshType

__all__ = [
    "AshNoDbLockedException",
    "AshModel",
    "WhiteAshModel",
    "BlackAshModel",
    "WHITE_ASH_BD",
    "BLACK_ASH_BD",
]

WHITE_ASH_BD: float
BLACK_ASH_BD: float

class AshNoDbLockedException(Exception): ...

class AshModel:
    def __init__(
        self,
        ash_type: AshType,
        proportion: float,
        decomposition_rate: float,
        bulk_density: float,
        density_at_fc: float,
        fraction_water_retention_capacity_at_sat: float,
        runoff_threshold: float,
        water_transport_rate: float,
        water_transport_rate_k: float,
        wind_threshold: float,
        porosity: float,
    ) -> None: ...

    @property
    def ini_material_available_mm(self) -> float: ...

    @property
    def ini_material_available_tonneperha(self) -> float: ...

    @property
    def water_retention_capacity_at_sat(self) -> float: ...

    def lookup_wind_threshold_proportion(self, w: float) -> float: ...

    def run_model(
        self,
        fire_date: YearlessDate,
        element_d,
        cli_df: pd.DataFrame,
        hill_wat_df: pd.DataFrame,
        out_dir,
        prefix,
        recurrence: Sequence[int] = ...,
        area_ha: Optional[float] = ...,
        ini_ash_depth: Optional[float] = ...,
        ini_ash_load: Optional[float] = ...,
        run_wind_transport: bool = ...,
    ) -> Tuple[str, Dict, Dict]: ...


class WhiteAshModel(AshModel):
    __name__: str

    def __init__(self, bulk_density: float = ...) -> None: ...


class BlackAshModel(AshModel):
    __name__: str

    def __init__(self, bulk_density: float = ...) -> None: ...
