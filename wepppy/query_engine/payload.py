from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _ensure_str_list(value: Iterable[Any], *, name: str) -> List[str]:
    items = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError(f"{name} entries must be strings")
        items.append(item)
    return items


def _escape_alias_candidate(text: str) -> str:
    safe = []
    for char in text:
        if char.isalnum() or char == "_":
            safe.append(char)
        else:
            safe.append("_")
    candidate = "".join(safe).strip("_")
    return candidate or "dataset"


@dataclass(slots=True)
class DatasetSpec:
    path: str
    alias: str
    columns: Optional[List[str]] = None


@dataclass(slots=True)
class JoinSpec:
    left: str
    right: str
    left_on: List[str]
    right_on: List[str]
    join_type: str


@dataclass(slots=True)
class AggregationSpec:
    sql: str
    alias: Optional[str]


@dataclass(slots=True)
class ComputedColumnSpec:
    sql: str
    alias: str


@dataclass(slots=True)
class TimeseriesSeriesSpec:
    column: str
    key: str
    label: Optional[str]
    group: Optional[str]
    role: Optional[str]
    color: Optional[str]
    units: Optional[str]
    description: Optional[str]


@dataclass(slots=True)
class TimeseriesReshapeSpec:
    index_column: str
    index_key: str
    series: List[TimeseriesSeriesSpec]
    year_column: Optional[str]
    exclude_year_indexes: List[int]
    compact: bool
    include_records: bool


def _normalise_computed_column(item: Any, *, used_aliases: set[str]) -> ComputedColumnSpec:
    if not isinstance(item, dict):
        raise TypeError("computed_columns entries must be objects")

    alias = item.get("alias")
    if not alias or not isinstance(alias, str):
        raise ValueError("Computed column requires an 'alias' string")
    alias = alias.strip()
    if not alias:
        raise ValueError("Computed column alias cannot be empty")
    if alias in used_aliases:
        raise ValueError(f"Computed column alias '{alias}' defined multiple times")
    used_aliases.add(alias)

    if "sql" in item:
        expression = item["sql"]
    elif "expression" in item:
        expression = item["expression"]
    elif "date_parts" in item:
        parts = item["date_parts"]
        if not isinstance(parts, dict):
            raise TypeError("Computed column 'date_parts' must be an object with 'year', 'month', 'day'")
        try:
            year_expr = parts["year"]
            month_expr = parts["month"]
            day_expr = parts["day"]
        except KeyError as exc:  # pragma: no cover - defensive
            raise ValueError("Computed column 'date_parts' requires 'year', 'month', and 'day' keys") from exc
        expression = f"MAKE_DATE({year_expr}, {month_expr}, {day_expr})"
    else:
        raise ValueError("Computed column must define 'sql', 'expression', or 'date_parts'")

    expression = str(expression).strip()
    if not expression:
        raise ValueError("Computed column expression cannot be empty")

    return ComputedColumnSpec(sql=expression, alias=alias)


def _normalise_timeseries_series(entry: Any) -> TimeseriesSeriesSpec:
    if not isinstance(entry, dict):
        raise TypeError("reshape.series entries must be objects")
    column = entry.get("column")
    if not column or not isinstance(column, str):
        raise ValueError("reshape.series entries require a 'column' string")

    key = entry.get("key") or entry.get("id") or column
    if not isinstance(key, str):
        raise TypeError("reshape.series 'key' must be a string when provided")
    key = key.strip()
    if not key:
        raise ValueError("reshape.series key cannot be empty")

    label = entry.get("label")
    if label is not None and not isinstance(label, str):
        raise TypeError("reshape.series label must be a string")

    group = entry.get("group")
    if group is not None and not isinstance(group, str):
        raise TypeError("reshape.series group must be a string")

    role = entry.get("role")
    if role is not None and not isinstance(role, str):
        raise TypeError("reshape.series role must be a string")

    color = entry.get("color")
    if color is not None and not isinstance(color, str):
        raise TypeError("reshape.series color must be a string")

    units = entry.get("units")
    if units is not None and not isinstance(units, str):
        raise TypeError("reshape.series units must be a string")

    description = entry.get("description")
    if description is not None and not isinstance(description, str):
        raise TypeError("reshape.series description must be a string")

    return TimeseriesSeriesSpec(
        column=column,
        key=key,
        label=label,
        group=group,
        role=role,
        color=color,
        units=units,
        description=description,
    )


def _normalise_reshape(reshape: Any) -> TimeseriesReshapeSpec | None:
    if reshape is None:
        return None
    if not isinstance(reshape, dict):
        raise TypeError("reshape must be an object")

    reshape_type = str(reshape.get("type") or "timeseries").lower()
    if reshape_type != "timeseries":
        raise ValueError(f"Unsupported reshape type '{reshape_type}'")

    index_entry = reshape.get("index")
    if not isinstance(index_entry, dict):
        raise TypeError("reshape.index must be an object")
    index_column = index_entry.get("column")
    if not index_column or not isinstance(index_column, str):
        raise ValueError("reshape.index requires a 'column' string")
    index_key = index_entry.get("key") or index_column
    if not isinstance(index_key, str):
        raise TypeError("reshape.index 'key' must be a string when provided")
    index_key = index_key.strip()
    if not index_key:
        raise ValueError("reshape.index key cannot be empty")

    series_entries = reshape.get("series")
    if not isinstance(series_entries, Sequence) or isinstance(series_entries, (str, bytes)):
        raise TypeError("reshape.series must be a list of objects")
    series_specs = [_normalise_timeseries_series(entry) for entry in series_entries]
    if not series_specs:
        raise ValueError("reshape.series must contain at least one series")

    year_column = reshape.get("year_column")
    if year_column is not None and not isinstance(year_column, str):
        raise TypeError("reshape.year_column must be a string")

    exclude_indexes_value = reshape.get("exclude_year_indexes") or reshape.get("exclude_year_indices")
    exclude_year_indexes: List[int] = []
    if exclude_indexes_value is not None:
        if not isinstance(exclude_indexes_value, Sequence):
            raise TypeError("reshape.exclude_year_indexes must be a list of integers")
        for item in exclude_indexes_value:
            try:
                exclude_year_indexes.append(int(item))
            except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
                raise ValueError("reshape.exclude_year_indexes must contain integers") from exc

    compact = bool(reshape.get("compact", False))
    include_records = bool(reshape.get("include_records", not compact))

    return TimeseriesReshapeSpec(
        index_column=index_column,
        index_key=index_key,
        series=series_specs,
        year_column=year_column,
        exclude_year_indexes=exclude_year_indexes,
        compact=compact,
        include_records=include_records,
    )


def _normalise_dataset(
    dataset: Any,
    *,
    index: int,
    used_aliases: set[str],
) -> DatasetSpec:
    if isinstance(dataset, str):
        path = dataset
        alias_candidate = Path(dataset).stem or f"dataset_{index}"
        alias = _ensure_unique_alias(alias_candidate, used_aliases)
        columns = None
    elif isinstance(dataset, dict):
        path = dataset.get("path") or dataset.get("dataset")
        if not path:
            raise ValueError("Dataset object must define 'path'")
        alias_candidate = dataset.get("alias") or Path(path).stem or f"dataset_{index}"
        alias = _ensure_unique_alias(alias_candidate, used_aliases)
        columns_value = dataset.get("columns")
        if columns_value is not None:
            if not isinstance(columns_value, Sequence) or isinstance(columns_value, (str, bytes)):
                raise TypeError("Dataset 'columns' must be a list of strings")
            columns = _ensure_str_list(columns_value, name="dataset columns")
        else:
            columns = None
    else:
        raise TypeError("datasets entries must be strings or objects with a 'path'")

    path = str(path)
    if not path:
        raise ValueError("Dataset 'path' cannot be empty")

    return DatasetSpec(path=path, alias=alias, columns=columns)


def _ensure_unique_alias(candidate: str, used_aliases: set[str]) -> str:
    base = _escape_alias_candidate(candidate or "dataset")
    alias = base or "dataset"
    suffix = 1
    while alias in used_aliases:
        alias = f"{base}_{suffix}"
        suffix += 1
    used_aliases.add(alias)
    return alias


def _normalise_join(join: Any) -> JoinSpec:
    if not isinstance(join, dict):
        raise TypeError("joins entries must be objects")

    left = join.get("left")
    right = join.get("right")
    if not left or not right:
        raise ValueError("Join entries must define 'left' and 'right' aliases")

    join_type_raw = str(join.get("type") or join.get("join_type") or "inner").lower()
    join_type_map = {
        "inner": "INNER",
        "left": "LEFT",
        "left_outer": "LEFT",
        "right": "RIGHT",
        "right_outer": "RIGHT",
        "full": "FULL",
        "full_outer": "FULL",
        "outer": "FULL",
    }
    if join_type_raw not in join_type_map:
        raise ValueError(f"Unsupported join type '{join_type_raw}'")
    join_type = join_type_map[join_type_raw]

    if "on" in join:
        on_value = join["on"]
        if isinstance(on_value, str):
            left_on = right_on = [on_value]
        elif isinstance(on_value, Sequence):
            on_list = _ensure_str_list(on_value, name="join on")
            if not on_list:
                raise ValueError("Join 'on' collection cannot be empty")
            left_on = right_on = on_list
        else:
            raise TypeError("Join 'on' must be a string or list of strings")
    else:
        left_on_val = join.get("left_on")
        right_on_val = join.get("right_on")
        if not left_on_val or not right_on_val:
            raise ValueError("Join must define either 'on' or both 'left_on' and 'right_on'")
        left_on = _ensure_str_list(left_on_val, name="join left_on")
        right_on = _ensure_str_list(right_on_val, name="join right_on")
        if len(left_on) != len(right_on):
            raise ValueError("Join 'left_on' and 'right_on' must contain the same number of entries")

    return JoinSpec(left=str(left), right=str(right), left_on=left_on, right_on=right_on, join_type=join_type)


def _normalise_aggregation(aggregation: Any) -> AggregationSpec:
    if isinstance(aggregation, str):
        sql = aggregation
        alias = None
    elif isinstance(aggregation, dict):
        alias = aggregation.get("alias")
        if alias is not None and not isinstance(alias, str):
            raise TypeError("Aggregation alias must be a string")

        if "expression" in aggregation:
            sql = aggregation["expression"]
        elif "sql" in aggregation:
            sql = aggregation["sql"]
        else:
            fn = aggregation.get("fn") or aggregation.get("function")
            column = aggregation.get("column")
            if not fn or not column:
                raise ValueError("Aggregation must specify 'expression', 'sql', or both 'fn' and 'column'")
            sql = f"{str(fn).upper()}({column})"
    else:
        raise TypeError("Aggregations entries must be strings or objects")

    sql = str(sql).strip()
    if not sql:
        raise ValueError("Aggregation SQL cannot be empty")
    return AggregationSpec(sql=sql, alias=alias)


@dataclass(slots=True)
class QueryRequest:
    datasets: List[Any]
    columns: Optional[List[str]] = None
    limit: Optional[int] = None
    include_schema: bool = False
    include_sql: bool = False
    joins: Optional[List[Dict[str, Any]]] = None
    group_by: Optional[List[str]] = None
    aggregations: Optional[List[Any]] = None
    order_by: Optional[List[str]] = None
    filters: Optional[List[Dict[str, Any]]] = None
    computed_columns: Optional[List[Dict[str, Any]]] = None
    reshape: Optional[Dict[str, Any]] = None

    _dataset_specs: List[DatasetSpec] = field(init=False, repr=False)
    _join_specs: List[JoinSpec] = field(init=False, repr=False)
    _aggregation_specs: List[AggregationSpec] = field(init=False, repr=False)
    _computed_columns_specs: List[ComputedColumnSpec] = field(init=False, repr=False)
    _reshape_spec: TimeseriesReshapeSpec | None = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.datasets:
            raise ValueError("At least one dataset must be provided")
        if self.limit is not None and self.limit < 1:
            raise ValueError("limit must be >= 1")

        if not isinstance(self.include_schema, bool):
            raise TypeError("include_schema must be a boolean")
        if not isinstance(self.include_sql, bool):
            raise TypeError("include_sql must be a boolean")

        if self.columns is not None:
            if not isinstance(self.columns, Sequence) or isinstance(self.columns, (str, bytes)):
                raise TypeError("columns must be a list of strings")
            self.columns = _ensure_str_list(self.columns, name="columns")

        used_aliases: set[str] = set()
        self._dataset_specs = [
            _normalise_dataset(dataset, index=index, used_aliases=used_aliases)
            for index, dataset in enumerate(self.datasets)
        ]

        computed_entries = self.computed_columns or []
        computed_aliases: set[str] = set()
        self._computed_columns_specs = [
            _normalise_computed_column(entry, used_aliases=computed_aliases)
            for entry in computed_entries
        ]

        join_entries = self.joins or []
        join_specs = [_normalise_join(join) for join in join_entries]
        self._join_specs = join_specs

        if len(self._dataset_specs) > 1 and not join_specs:
            raise ValueError("joins must be provided when querying multiple datasets")

        aggregation_entries = self.aggregations or []
        self._aggregation_specs = [_normalise_aggregation(item) for item in aggregation_entries]

        if self.group_by is not None:
            if not isinstance(self.group_by, Sequence) or isinstance(self.group_by, (str, bytes)):
                raise TypeError("group_by must be a list of strings")
            self.group_by = _ensure_str_list(self.group_by, name="group_by")

        if self.order_by is not None:
            if not isinstance(self.order_by, Sequence) or isinstance(self.order_by, (str, bytes)):
                raise TypeError("order_by must be a list of strings")
            self.order_by = _ensure_str_list(self.order_by, name="order_by")

        if self.filters is not None:
            if not isinstance(self.filters, Sequence):
                raise TypeError("filters must be a list of dicts")
            normalised_filters: List[dict[str, object]] = []
            for filt in self.filters:
                if not isinstance(filt, dict):
                    raise TypeError("filters entries must be objects")
                column = filt.get("column") or filt.get("field")
                if not column or not isinstance(column, str):
                    raise ValueError("Each filter must define a 'column' string")
                op = str(filt.get("op") or filt.get("operator") or "=").upper()
                value = filt.get("value")
                if op not in {"IS NULL", "IS NOT NULL"} and value is None:
                    raise ValueError("Each filter must supply a 'value'")
                allowed_ops = {"=", "!=", "<", "<=", ">", ">=", "LIKE", "ILIKE", "IN", "NOT IN", "BETWEEN", "IS NULL", "IS NOT NULL"}
                if op not in allowed_ops:
                    raise ValueError(f"Unsupported filter operator '{op}'")
                filter_payload: dict[str, object] = {"column": column, "operator": op}
                if op in {"IS NULL", "IS NOT NULL"}:
                    if value not in (None, "", False):
                        raise ValueError("IS NULL/IS NOT NULL filters do not accept a value")
                elif op == "BETWEEN":
                    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                        raise ValueError("BETWEEN filters expect a list/tuple with two values")
                    if len(value) != 2:
                        raise ValueError("BETWEEN filters require exactly two values")
                    filter_payload["value"] = list(value)
                elif op in {"IN", "NOT IN"}:
                    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                        raise ValueError("IN/NOT IN filters expect a list of values")
                    values = list(value)
                    if not values:
                        raise ValueError("IN/NOT IN filters require at least one value")
                    filter_payload["value"] = values
                else:
                    filter_payload["value"] = value
                normalised_filters.append(filter_payload)
            self.filters = normalised_filters

        self._reshape_spec = _normalise_reshape(self.reshape)

    @property
    def dataset_specs(self) -> List[DatasetSpec]:
        return list(self._dataset_specs)

    @property
    def join_specs(self) -> List[JoinSpec]:
        return list(self._join_specs)

    @property
    def aggregation_specs(self) -> List[AggregationSpec]:
        return list(self._aggregation_specs)

    @property
    def computed_column_specs(self) -> List[ComputedColumnSpec]:
        return list(self._computed_columns_specs)

    @property
    def reshape_spec(self) -> TimeseriesReshapeSpec | None:
        return self._reshape_spec


@dataclass
class QueryPlan:
    sql: str
    params: List[object]
    requires_spatial: bool = False
