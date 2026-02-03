from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

PRINT_PRT_DAILY: int
PRINT_PRT_MONTHLY: int
PRINT_PRT_YEARLY: int
PRINT_PRT_AVANN: int

DEFAULT_PRINT_PRT_TITLE: str

DEFAULT_PRINT_PRT_FLAGS_PRIMARY: List[Tuple[str, str]]
DEFAULT_PRINT_PRT_FLAGS_SECONDARY: List[Tuple[str, str]]

PRINT_PRT_OBJECT_ORDER: List[str]
PRINT_PRT_OBJECT_ORDER_NO_HRU_CB: List[str]

def mask_from_flags(
    *,
    daily: bool = ...,
    monthly: bool = ...,
    yearly: bool = ...,
    avann: bool = ...,
) -> int: ...

def mask_from_tokens(daily: str, monthly: str, yearly: str, avann: str) -> int: ...

def mask_to_tokens(mask: int) -> Tuple[str, str, str, str]: ...

@dataclass
class PrintPrtObjects:
    basin_wb: int
    basin_nb: int
    basin_ls: int
    basin_pw: int
    basin_aqu: int
    basin_res: int
    basin_cha: int
    basin_sd_cha: int
    basin_psc: int
    region_wb: int
    region_nb: int
    region_ls: int
    region_pw: int
    region_aqu: int
    region_res: int
    region_sd_cha: int
    region_psc: int
    water_allo: int
    lsunit_wb: int
    lsunit_nb: int
    lsunit_ls: int
    lsunit_pw: int
    hru_wb: int
    hru_nb: int
    hru_ls: int
    hru_pw: int
    hru_cb: int
    hru_lte_wb: int
    hru_lte_nb: int
    hru_lte_ls: int
    hru_lte_pw: int
    channel: int
    channel_sd: int
    aquifer: int
    reservoir: int
    recall: int
    hyd: int
    ru: int
    pest: int

    def iter_rows(self, order: Optional[Sequence[str]] = ...) -> List[Tuple[str, int]]: ...
    def set_mask(self, object_name: str, mask: int) -> None: ...

@dataclass
class PrintPrtConfig:
    title: str
    nyskip: int
    day_start: int
    yrc_start: int
    day_end: int
    yrc_end: int
    interval: int
    aa_int_cnt: int
    flags_primary: List[Tuple[str, str]]
    flags_secondary: List[Tuple[str, str]]
    flags_extra: List[List[Tuple[str, str]]]
    object_order: List[str]
    objects: PrintPrtObjects

    def render(self) -> str: ...

def load_print_prt(path: str) -> PrintPrtConfig: ...

def parse_print_prt(text: str) -> PrintPrtConfig: ...
