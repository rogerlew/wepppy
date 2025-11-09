from __future__ import annotations

from typing import TypedDict

class QueryPreset(TypedDict):
    id: str
    name: str
    description: str
    payload: dict[str, object]

QUERY_PRESETS: dict[str, list[QueryPreset]]
