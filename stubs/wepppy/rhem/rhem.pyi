from __future__ import annotations

from typing import Dict, Sequence


SoilTextureRow = Dict[str, str]
SoilTextureTable = Dict[str, SoilTextureRow]


def _template_loader(fn: str) -> str: ...


def _par_template_loader() -> str: ...


def read_soil_texture_table() -> SoilTextureTable: ...


soil_texture_db: SoilTextureTable


def make_parameter_file(
    scn_name: str,
    out_dir: str,
    soil_texture: str,
    moisture_content: float,
    bunchgrass_cover: float,
    forbs_cover: float,
    shrubs_cover: float,
    sodgrass_cover: float,
    rock_cover: float,
    basal_cover: float,
    litter_cover: float,
    cryptogams_cover: float,
    slope_length: float,
    slope_steepness: float,
    sl: Sequence[float],
    sx: Sequence[float],
    width: float,
    model_version: str,
) -> str: ...


def make_hillslope_run(
    run_fn: str,
    par_fn: str,
    stm_fn: str,
    out_summary: str,
    scn_name: str,
) -> None: ...


def run_hillslope(topaz_id: str, runs_dir: str) -> tuple[bool, str, float]: ...
