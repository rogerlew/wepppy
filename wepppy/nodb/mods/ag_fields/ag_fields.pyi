from __future__ import annotations

import os
from enum import Enum
from typing import Any, ClassVar, Dict, Iterable, Iterator, List, Mapping, Optional, Set, Tuple

import pandas as pd

from wepppy.nodb.base import NoDbBase
from wepppy.nodb.mods.ag_fields.routing_schemes import AgFieldsRoutingScheme

__all__: list[str] = [
    "AgFieldsNoDbLockedException",
    "AgFieldsRunError",
    "PlantFileProcessingError",
    "RotationLookupValidationError",
    "AgFields",
]


class AgFieldsNoDbLockedException(Exception):
    ...


class AgFieldsRunError(RuntimeError):
    field_id: int
    sub_field_id: int
    def __init__(self, field_id: int, sub_field_id: int, message: str) -> None: ...


class PlantFileProcessingError(ValueError):
    filename: str
    def __init__(self, filename: str, message: str) -> None: ...


class RotationLookupValidationError(ValueError):
    results: List[Dict[str, Any]]
    def __init__(self, results: List[Dict[str, Any]]) -> None: ...


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
    def wepp_bin(self) -> Optional[str]: ...

    @wepp_bin.setter
    def wepp_bin(self, value: str) -> None: ...

    @property
    def geojson_timestamp(self) -> Optional[int]: ...

    @property
    def geojson_is_valid(self) -> bool: ...

    @property
    def geojson_hash(self) -> Optional[str]: ...

    @property
    def field_columns(self) -> List[str]: ...

    @property
    def field_boundaries_geojson(self) -> Optional[str]: ...

    @property
    def field_boundaries_source_filename(self) -> Optional[str]: ...

    @property
    def field_id_key(self) -> Optional[str]: ...

    def validate_field_boundary_geojson(
        self,
        fn: str | os.PathLike[str],
        *,
        source_filename: Optional[str] = ...,
    ) -> Dict[str, List[Any]]: ...

    def get_unique_crops(self) -> Set[str]: ...

    def validate_field_id_key(self, key: str) -> None: ...

    def set_field_id_key(self, key: str) -> None: ...

    def confirm_schema(self, field_id_key: str, rotation_accessor: str) -> None: ...

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
    def ag_field_watershed_root(self) -> str: ...

    @property
    def ag_field_watershed_runs_dir(self) -> str: ...

    @property
    def ag_field_watershed_output_dir(self) -> str: ...

    @property
    def ag_field_watershed_manifest_dir(self) -> str: ...

    def ag_field_watershed_scheme_root(
        self,
        scheme: str | AgFieldsRoutingScheme | None = ...,
    ) -> str: ...

    @property
    def plant_files_dir(self) -> str: ...

    @property
    def plant_files_2017_1_dir(self) -> str: ...

    def clear_ag_field_wepp_runs(self) -> None: ...

    def clear_ag_field_wepp_outputs(self) -> None: ...

    def clear_ag_field_wepp_artifacts(self) -> None: ...

    def run_watershed_integration(
        self,
        max_workers: Optional[int] = ...,
        phase_callback: Optional[Any] = ...,
        scheme: str | AgFieldsRoutingScheme | None = ...,
    ) -> Dict[str, Any]: ...

    def clear_watershed_integration(
        self,
        scheme: str | AgFieldsRoutingScheme | None = ...,
    ) -> None: ...

    def set_watershed_integration_job_id(
        self,
        scheme: str | AgFieldsRoutingScheme,
        job_id: str,
    ) -> None: ...

    def set_watershed_integration_job_ids(
        self,
        job_ids: Mapping[str | AgFieldsRoutingScheme, str],
    ) -> None: ...

    def get_watershed_integration_state(
        self,
        scheme: str | AgFieldsRoutingScheme | None = ...,
    ) -> Dict[str, Any]: ...

    def get_watershed_integration_states(self) -> Dict[str, Dict[str, Any]]: ...

    @property
    def rotation_accessor(self) -> Optional[str]: ...

    def validate_rotation_accessor(self, candidate: str) -> None: ...

    def set_rotation_accessor(self, candidate: str) -> None: ...

    def handle_plant_file_db_upload(self, plant_db_zip_fn: str) -> Dict[str, Any]: ...

    def get_valid_plant_files(self) -> List[str]: ...

    def get_invalid_plant_files(self) -> List[Dict[str, str]]: ...

    def get_plant_file_inventory(self) -> Dict[str, Any]: ...

    def delete_plant_file(self, filename: str) -> Dict[str, Any]: ...

    @property
    def rotation_lookup_path(self) -> str: ...

    def get_rotation_key(self, year: int) -> str: ...

    def _crop_year_iter(self) -> Iterator[int]: ...

    def validate_rotation_lookup(self) -> List[Dict[str, Any]]: ...

    def write_rotation_lookup(
        self,
        rows: Iterable[Dict[str, Any]],
    ) -> List[Dict[str, Any]]: ...

    def get_weppcloud_management_options(self) -> List[Dict[str, str]]: ...

    def get_staleness(self) -> Dict[str, bool]: ...

    def get_readiness(self) -> Dict[str, Any]: ...

    @property
    def subfields_parquet_path(self) -> str: ...

    @property
    def subfields_parquet(self) -> pd.DataFrame: ...

    def run_wepp_ag_fields(self, max_workers: Optional[int] = ...) -> Dict[str, int]: ...


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

    @staticmethod
    def resolve_rotation(
        ag_fields_dir: str,
        landuse_mapping: str,
        crop_name: str,
        database: str,
        rotation_id: str,
        *,
        logger_name: Optional[str],
    ) -> CropRotation: ...

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
    wepp_bin: str,
    logger_name: Optional[str] = ...,
) -> None: ...
