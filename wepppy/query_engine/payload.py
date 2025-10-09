from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(slots=True)
class QueryRequest:
    datasets: List[str]
    columns: Optional[List[str]] = None
    limit: Optional[int] = None
    include_schema: bool = False

    def __post_init__(self) -> None:
        if not self.datasets:
            raise ValueError("At least one dataset must be provided")
        if self.limit is not None and self.limit < 1:
            raise ValueError("limit must be >= 1")


@dataclass
class QueryPlan:
    sql: str
    params: List[object]
    requires_spatial: bool = False
