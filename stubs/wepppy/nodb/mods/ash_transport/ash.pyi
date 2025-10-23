from __future__ import annotations

from enum import IntEnum
from typing import Any, ClassVar, Dict, Iterator, List, Mapping, MutableMapping, Optional, Tuple

from wepppy.all_your_base.dateutils import YearlessDate
from wepppy.nodb.base import NoDbBase

from .ash_multi_year_model import (
    AshModel,
    BlackAshModel as BlackAshModelAnu,
    WhiteAshModel as WhiteAshModelAnu,
)
from .ash_multi_year_model_alex import (
    BlackAshModel as BlackAshModelAlex,
    WhiteAshModel as WhiteAshModelAlex,
)

__all__: List[str] = ["run_ash_model", "AshSpatialMode", "AshNoDbLockedException", "Ash"]

AshMetadata = Dict[int | str, Dict[str, Any]]
ContaminantLevels = Dict[str, float]
RasterSummary = Dict[int, float]

MULTIPROCESSING: bool


def run_ash_model(kwds: MutableMapping[str, Any]) -> str: ...


class AshSpatialMode(IntEnum):
    Single = ...
    Gridded = ...


class AshNoDbLockedException(Exception):
    ...


class Ash(NoDbBase):
    filename: ClassVar[str]
    __name__: ClassVar[str]
    fire_date: YearlessDate
    ini_black_ash_depth_mm: float
    ini_white_ash_depth_mm: float
    meta: Optional[AshMetadata]
    fire_years: Optional[int]
    low_contaminant_concentrations: ContaminantLevels
    moderate_contaminant_concentrations: ContaminantLevels
    high_contaminant_concentrations: ContaminantLevels

    def __new__(cls, *args: Any, **kwargs: Any) -> Ash: ...

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    def _load_contaminants_from_config(self) -> None: ...

    def get_cc_default(self, severity: str) -> ContaminantLevels: ...

    def parse_inputs(self, kwds: Mapping[str, Any]) -> None: ...

    def parse_cc_inputs(self, kwds: MutableMapping[str, Any]) -> None: ...

    @classmethod
    def _post_instance_loaded(cls, instance: Ash) -> Ash: ...

    @property
    def has_ash_results(self) -> bool: ...

    @property
    def anu_white_ash_model_pars(self) -> WhiteAshModelAnu: ...

    @property
    def anu_black_ash_model_pars(self) -> BlackAshModelAnu: ...

    @property
    def alex_white_ash_model_pars(self) -> WhiteAshModelAlex: ...

    @property
    def alex_black_ash_model_pars(self) -> BlackAshModelAlex: ...

    @property
    def model(self) -> str: ...

    @model.setter
    def model(self, value: str) -> None: ...

    @property
    def reservoir_storage(self) -> float: ...

    @reservoir_storage.setter
    def reservoir_storage(self, value: float) -> None: ...

    @property
    def run_wind_transport(self) -> bool: ...

    @run_wind_transport.setter
    def run_wind_transport(self, value: bool) -> None: ...

    @property
    def ash_load_d(self) -> Optional[RasterSummary]: ...

    @property
    def ash_bulk_density_d(self) -> Optional[RasterSummary]: ...

    @property
    def ash_load_fn(self) -> Optional[str]: ...

    @ash_load_fn.setter
    def ash_load_fn(self, value: Optional[str]) -> None: ...

    @property
    def ash_type_map_fn(self) -> Optional[str]: ...

    @ash_type_map_fn.setter
    def ash_type_map_fn(self, value: Optional[str]) -> None: ...

    @property
    def ash_bulk_density_fn(self) -> Optional[str]: ...

    @ash_bulk_density_fn.setter
    def ash_bulk_density_fn(self, value: Optional[str]) -> None: ...

    @property
    def ash_spatial_mode(self) -> AshSpatialMode: ...

    @ash_spatial_mode.setter
    def ash_spatial_mode(self, value: AshSpatialMode) -> None: ...

    @property
    def ash_depth_mode(self) -> int: ...

    @ash_depth_mode.setter
    def ash_depth_mode(self, value: int) -> None: ...

    @property
    def reservoir_capacity_m3(self) -> float: ...

    @reservoir_capacity_m3.setter
    def reservoir_capacity_m3(self, value: float) -> None: ...

    @property
    def reservoir_capacity_ft3(self) -> float: ...

    @property
    def ash_bulk_density_cropped_fn(self) -> str: ...

    @property
    def ash_load_cropped_fn(self) -> str: ...

    @property
    def ash_type_map_cropped_fn(self) -> str: ...

    def run_ash(
        self,
        fire_date: str = ...,
        ini_white_ash_depth_mm: float = ...,
        ini_black_ash_depth_mm: float = ...,
        slope: Optional[float] = ...,
    ) -> None: ...

    def get_ash_type(self, topaz_id: int | str) -> Optional[str]: ...

    def get_ini_ash_depth(self, topaz_id: int | str) -> Optional[float]: ...

    @property
    def available_models(self) -> List[Tuple[str, str]]: ...

    @property
    def black_ash_bulkdensity(self) -> float: ...

    @property
    def white_ash_bulkdensity(self) -> float: ...

    @property
    def field_black_ash_bulkdensity(self) -> float: ...

    @property
    def field_white_ash_bulkdensity(self) -> float: ...

    @property
    def ini_black_ash_load(self) -> float: ...

    @property
    def ini_white_ash_load(self) -> float: ...

    @property
    def has_watershed_summaries(self) -> bool: ...

    def hillslope_is_burned(self, topaz_id: int | str) -> bool: ...

    def contaminants_iter(
        self,
    ) -> Iterator[Tuple[str, Optional[float], Optional[float], Optional[float], str]] | None: ...

    def burn_class_summary(self) -> Dict[int, float]: ...
