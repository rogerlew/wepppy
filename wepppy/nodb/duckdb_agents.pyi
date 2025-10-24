from __future__ import annotations

from typing import Any, Dict, Union

if False:  # pragma: no cover - only for type checking
    import pandas as pd

SummaryRow = Dict[str, Any]

__all__ = [
    "get_soil_sub_summary",
    "get_soil_subs_summary",
    "get_landuse_sub_summary",
    "get_landuse_subs_summary",
    "get_watershed_sub_summary",
    "get_watershed_subs_summary",
    "get_watershed_chn_summary",
    "get_watershed_chns_summary",
]


def get_soil_sub_summary(wd: str, topaz_id: Union[int, str]) -> SummaryRow: ...


def get_soil_subs_summary(
    wd: str,
    return_as_df: bool = ...,
) -> Union[Dict[Union[int, str], SummaryRow], 'pd.DataFrame']: ...


def get_landuse_sub_summary(wd: str, topaz_id: Union[int, str]) -> SummaryRow: ...


def get_landuse_subs_summary(
    wd: str,
    return_as_df: bool = ...,
) -> Union[Dict[Union[int, str], SummaryRow], 'pd.DataFrame']: ...


def get_watershed_sub_summary(wd: str, topaz_id: Union[int, str]) -> SummaryRow: ...


def get_watershed_subs_summary(
    wd: str,
    return_as_df: bool = ...,
) -> Union[Dict[Union[int, str], SummaryRow], 'pd.DataFrame']: ...


def get_watershed_chn_summary(wd: str, topaz_id: Union[int, str]) -> SummaryRow: ...


def get_watershed_chns_summary(
    wd: str,
    return_as_df: bool = ...,
) -> Union[Dict[Union[int, str], SummaryRow], 'pd.DataFrame']: ...
