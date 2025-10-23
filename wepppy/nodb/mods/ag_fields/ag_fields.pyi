from __future__ import annotations

import os
from enum import Enum
from typing import Any, ClassVar, Dict, Iterable, Iterator, List, Optional, Set, Tuple

import pandas as pd

from wepppy.nodb.base import NoDbBase

__all__: list[str] = ["AgFieldsNoDbLockedException", "AgFields"]


class AgFieldsNoDbLockedException(Exception):
    ...


class AgFields(NoDbBase):
    filename: ClassVar[str]
    __exclude__: ClassVar[Tuple[str, ...]]
    __name__: ClassVar[str]

    def __init__(
        self,
        wd: str,
        cfg_fn: str = ...,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    @property
    def field_n(self) -> int: ...

    @property
    def sub_field_n(self) -> int: ...

    @property
    def sub_field_fp_n(self) -> int: ...

    @property
    def geojson_timestamp(self) -> Optional[int]: ...

    @property
    def geojson_is_valid(self) -> bool: ...

    @property
    def field_columns(self) -> List[str]: ...

    @property
    def field_boundaries_geojson(self) -> Optional[str]: ...

    @property
    def field_id_key(self) -> Optional[str]: ...

    def validate_field_boundary_geojson(self, fn: str | os.PathLike[str]) -> Dict[str, List[Any]]: ...

    def get_unique_crops(self) -> Set[str]: ...

    def set_field_id_key(self, key: str) -> None: ...

    @property
    def field_boundaries_tif(self) -> str: ...

    def rasterize_field_boundaries_geojson(self) -> None: ...

    @property
    def sub_field_min_area_threshold_m2(self) -> float: ...

    @sub_field_min_area_threshold_m2.setter
    def sub_field_min_area_threshold_m2(self, value: float) -> None: ...

    def periodot_abstract_sub_fields(
        self,
        sub_field_min_area_threshold_m2: Optional[float] = ...,
        verbose: bool = ...,
    ) -> None: ...

    def get_sub_field_translator(self) -> Dict[str, Tuple[int, int, int]]: ...

    @property
    def sub_fields_map(self) -> str: ...

    @property
    def sub_fields_geojson(self) -> str: ...

    @property
    def sub_fields_wgs_geojson(self) -> str: ...

    def polygonize_sub_fields(self) -> None: ...

    @property
    def rotation_schedule_parquet(self) -> str: ...

    @property
    def ag_field_wepp_runs_dir(self) -> str: ...

    @property
    def ag_field_wepp_output_dir(self) -> str: ...

    @property
    def ag_fields_dir(self) -> str: ...

    @property
    def plant_files_dir(self) -> str: ...

    @property
    def plant_files_2017_1_dir(self) -> str: ...

    def clear_ag_field_wepp_runs(self) -> None: ...

    def clear_ag_field_wepp_outputs(self) -> None: ...

    @property
    def rotation_accessor(self) -> Optional[str]: ...

    def set_rotation_accessor(self, candidate: str) -> None: ...

    def handle_plant_file_db_upload(self, plant_db_zip_fn: str) -> None: ...

    def get_valid_plant_files(self) -> List[str]: ...

    def get_rotation_key(self, year: int) -> str: ...

    def _crop_year_iter(self) -> Iterator[int]: ...

    def validate_rotation_lookup(self) -> None: ...

    @property
    def subfields_parquet_path(self) -> str: ...

    @property
    def subfields_parquet(self) -> pd.DataFrame: ...

    def run_wepp_ag_fields(self, max_workers: Optional[int] = ...) -> None: ...


class CropRotationDatabase(Enum):
    WEPP_CLOUD = ...
    PLANT_FILES_DB = ...

    def __str__(self) -> str: ...

    def __getstate__(self) -> str: ...


class CropRotation:
    crop_name: str
    database: CropRotationDatabase
    rotation_id: int | str
    man_path: str

    def __init__(self, crop_name: str, database: CropRotationDatabase, rotation_id: int | str, man_path: str) -> None: ...

    def __repr__(self) -> str: ...

    def to_dict(self) -> Dict[str, Any]: ...


class CropRotationManager:
    ag_fields_dir: str
    rotation_lookup: Dict[str, CropRotation]
    logger_name: Optional[str]

    def __init__(self, ag_fields_dir: str, landuse_mapping: str, logger_name: Optional[str]) -> None: ...

    def dump_rotation_lookup(self) -> None: ...

    def build_rotation_stack(self, crop_rotation_schedule: List[str], man_filepath: str) -> None: ...


def run_wepp_subfield(
    wd: str,
    field_id: int,
    topaz_id: str,
    wepp_id: int,
    sub_field_id: int,
    crop_rotation_schedule: Iterable[str],
    clip_hillslopes: bool,
    clip_hillslope_length: Optional[float],
    logger_name: Optional[str] = ...,
) -> None: ...
