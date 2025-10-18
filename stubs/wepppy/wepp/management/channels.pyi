from __future__ import annotations

from typing import Dict, List, Optional, TypedDict

__all__ = ["ChannelDefinition", "load_channel_d50_cs", "load_channels", "get_channel"]


class ChannelDefinition(TypedDict):
    key: str
    desc: str
    contents: str
    rot: str


def load_channel_d50_cs() -> List[Dict[str, float | str]]: ...


def load_channels() -> Dict[str, ChannelDefinition]: ...


def get_channel(
    key: str,
    erodibility: Optional[float] = None,
    critical_shear: Optional[float] = None,
    chnnbr: Optional[int] = None,
    chnn: Optional[int] = None,
) -> ChannelDefinition: ...
