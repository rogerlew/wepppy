from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

class WeppTopTranslator:
    sub_ids: List[str]
    chn_ids: List[str]
    hillslope_n: int
    channel_n: int
    n: int

    def __init__(self, top_sub_ids: Iterable[int], top_chn_ids: Iterable[int]) -> None: ...
    @property
    def top2wepp(self) -> Dict[int, int]: ...
    @property
    def wepp2top(self) -> Dict[int, int]: ...
    def top(
        self,
        wepp: Optional[int] = ...,
        sub_id: Optional[str] = ...,
        chn_id: Optional[str] = ...,
        chn_enum: Optional[int] = ...,
    ) -> Optional[int]: ...
    def wepp(
        self,
        top: Optional[int] = ...,
        sub_id: Optional[str] = ...,
        chn_id: Optional[str] = ...,
        chn_enum: Optional[int] = ...,
    ) -> Optional[int]: ...
    def chn_enum(self, chn_id: int) -> int: ...
    def is_channel(self, top: int) -> bool: ...
    def has_top(self, top: int) -> bool: ...
    def channel_hillslopes(self, chn_id: int) -> List[int]: ...


def upland_hillslopes(
    chn_id: int,
    network: Dict[int, Sequence[int]],
    top_translator: WeppTopTranslator,
) -> List[int]: ...
