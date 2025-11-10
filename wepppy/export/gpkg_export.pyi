from __future__ import annotations

from typing import NamedTuple

import pandas as pd


class ObjectiveParameter(NamedTuple):
    topaz_id: str
    wepp_id: str
    value: float


def esri_compatible_colnames(df: pd.DataFrame) -> pd.DataFrame: ...


def gpkg_extract_objective_parameter(
    gpkg_fn: str,
    obj_param: str,
) -> tuple[list[ObjectiveParameter], float]: ...


def gpkg_export(wd: str) -> None: ...


def _chown(dir_path: str) -> None: ...


def _chown_and_rmtree(dir_path: str) -> None: ...


def create_difference_map(
    scenario1_gpkg_fn: str,
    scenario2_gpkg_fn: str,
    difference_attributes: list[str],
    output_geojson_fn: str,
    meta_attributes: list[str] | None = ...,
) -> None: ...
