from __future__ import annotations

from typing import Optional, Sequence, Tuple

import pandas as pd

from wepppy.all_your_base.dateutils import YearlessDate

from .ash_type import AshType

__all__ = ["AshNoDbLockedException", "AshModelAlex", "WhiteAshModel", "BlackAshModel"]

WHITE_ASH_BD: float
BLACK_ASH_BD: float


class AshNoDbLockedException(Exception):
    ...


class AshModelAlex:
    ini_ash_depth_mm: Optional[float]
    ini_ash_load_tonneha: Optional[float]
    ini_bulk_den: Optional[float]
    fin_bulk_den: Optional[float]
    bulk_den_fac: Optional[float]
    par_den: Optional[float]
    decomp_fac: Optional[float]
    roughness_limit: Optional[float]
    org_mat: Optional[float]
    run_wind_transport: bool
    slope: Optional[float]
    beta0: float
    beta1: float
    beta2: float
    beta3: float
    transport_mode: str
    initranscap: float
    depletcoeff: float
    ash_type: AshType

    def __init__(
        self,
        ash_type: AshType,
        ini_bulk_den: Optional[float] = ...,
        fin_bulk_den: Optional[float] = ...,
        bulk_den_fac: Optional[float] = ...,
        par_den: Optional[float] = ...,
        decomp_fac: Optional[float] = ...,
        roughness_limit: Optional[float] = ...,
        run_wind_transport: bool = ...,
        org_mat: Optional[float] = ...,
        beta0: float = ...,
        beta1: float = ...,
        beta2: float = ...,
        beta3: float = ...,
        transport_mode: str = ...,
        initranscap: float = ...,
        depletcoeff: float = ...,
    ) -> None: ...

    @property
    def ini_material_available_mm(self) -> float: ...

    @property
    def ini_material_available_tonneperha(self) -> float: ...

    def lookup_wind_threshold_proportion(self, w: float) -> float: ...

    def run_model(
        self,
        fire_date: YearlessDate,
        cli_df: pd.DataFrame,
        hill_wat_df: pd.DataFrame,
        out_dir: str,
        prefix: str,
        recurrence: Sequence[int] = ...,
        area_ha: Optional[float] = ...,
        ini_ash_depth: Optional[float] = ...,
        ini_ash_load: Optional[float] = ...,
        slope: Optional[float] = ...,
        run_wind_transport: bool = ...,
    ) -> str: ...

    def _calc_transportable_ash(
        self,
        remaining_ash_tonspha: float,
        bulk_density_gmpcm3: float,
    ) -> Tuple[float, float]: ...

    def _run_ash_model_until_gone(
        self,
        fire_date: YearlessDate,
        hill_wat_df: pd.DataFrame,
        cli_df: pd.DataFrame,
        ini_ash_load: float,
        start_index: int,
        year0: int,
    ) -> pd.DataFrame: ...


class WhiteAshModel(AshModelAlex):
    __name__: str

    def __init__(self, bulk_density: float = ...) -> None: ...

    def to_dict(self) -> dict[str, float | str]: ...


class BlackAshModel(AshModelAlex):
    __name__: str

    def __init__(self, bulk_density: float = ...) -> None: ...

    def to_dict(self) -> dict[str, float | str]: ...
