from __future__ import annotations

from typing import Dict, MutableMapping, Optional, Tuple

from deprecated import deprecated

@deprecated
class SoilReplacements:
    Code: Optional[int]
    LndcvrID: Optional[int]
    WEPP_Type: Optional[str]
    New_WEPPman: Optional[str]
    ManName: Optional[str]
    Albedo: Optional[str]
    iniSatLev: Optional[str]
    interErod: Optional[str]
    rillErod: Optional[str]
    critSh: Optional[str]
    effHC: Optional[str]
    soilDepth: Optional[str]
    Sand: Optional[str]
    Clay: Optional[str]
    OM: Optional[str]
    CEC: Optional[str]
    Comment: Optional[str]
    fname: Optional[str]
    kslast: Optional[str]

    def __init__(self, **kwargs: Optional[str | int]) -> None: ...

@deprecated
def read_lc_file(fname: str) -> Dict[Tuple[str, str], MutableMapping[str, Optional[str]]]: ...
def simple_texture(clay: float, sand: float) -> Optional[str]: ...
def simple_texture_enum(clay: float, sand: float) -> int: ...
def soil_texture(clay: float, sand: float) -> str: ...
@deprecated
def soil_specialization(src: str, dst: str, replacements: SoilReplacements, caller: str = ...) -> None: ...
def modify_kslast(src: str, dst: str, kslast: float, caller: str = ...) -> None: ...
def soil_is_water(soil_fn: str) -> bool: ...
