from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

@dataclass
class DatasetSpec:
    path: str
    alias: str
    columns: list[str] | None = ...

@dataclass
class JoinSpec:
    left: str
    right: str
    left_on: list[str]
    right_on: list[str]
    join_type: str

@dataclass
class AggregationSpec:
    sql: str
    alias: str | None

@dataclass
class ComputedColumnSpec:
    sql: str
    alias: str

@dataclass
class TimeseriesSeriesSpec:
    column: str
    key: str
    label: str | None
    group: str | None
    role: str | None
    color: str | None
    units: str | None
    description: str | None

@dataclass
class TimeseriesReshapeSpec:
    index_column: str
    index_key: str
    series: list[TimeseriesSeriesSpec]
    year_column: str | None
    exclude_year_indexes: list[int]
    compact: bool
    include_records: bool

@dataclass
class QueryRequest:
    datasets: list[Any]
    columns: list[str] | None = ...
    limit: int | None = ...
    include_schema: bool = ...
    include_sql: bool = ...
    joins: list[dict[str, Any]] | None = ...
    group_by: list[str] | None = ...
    aggregations: list[Any] | None = ...
    order_by: list[str] | None = ...
    filters: list[dict[str, Any]] | None = ...
    computed_columns: list[dict[str, Any]] | None = ...
    reshape: dict[str, Any] | None = ...

    @property
    def dataset_specs(self) -> list[DatasetSpec]: ...
    @property
    def join_specs(self) -> list[JoinSpec]: ...
    @property
    def aggregation_specs(self) -> list[AggregationSpec]: ...
    @property
    def computed_column_specs(self) -> list[ComputedColumnSpec]: ...
    @property
    def reshape_spec(self) -> TimeseriesReshapeSpec | None: ...

@dataclass
class QueryPlan:
    sql: str
    params: list[object]
    requires_spatial: bool = ...
