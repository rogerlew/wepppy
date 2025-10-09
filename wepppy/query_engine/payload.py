from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    datasets: List[str]
    columns: Optional[List[str]] = None
    limit: Optional[int] = Field(default=None, ge=1)


@dataclass
class QueryPlan:
    sql: str
    params: List[object]
    requires_spatial: bool = False
