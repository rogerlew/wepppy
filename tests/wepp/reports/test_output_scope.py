from __future__ import annotations

import pytest

from wepppy.wepp.reports.output_scope import (
    DEFAULT_OUTPUT_SCOPE,
    normalize_output_scope,
    resolve_output_scope_paths,
    scoped_dataset_path,
)

pytestmark = pytest.mark.unit


def test_normalize_output_scope_defaults_to_baseline() -> None:
    assert DEFAULT_OUTPUT_SCOPE == "baseline"
    assert normalize_output_scope(None) == "baseline"
    assert normalize_output_scope("") == "baseline"
    assert normalize_output_scope("baseline") == "baseline"
    assert normalize_output_scope("ROADS") == "roads"


def test_normalize_output_scope_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="Invalid output_scope"):
        normalize_output_scope("foo")


def test_resolve_output_scope_paths() -> None:
    baseline = resolve_output_scope_paths("baseline")
    assert baseline.output_root.as_posix() == "wepp/output"
    assert baseline.interchange_root.as_posix() == "wepp/output/interchange"

    roads = resolve_output_scope_paths("roads")
    assert roads.output_root.as_posix() == "wepp/roads/output"
    assert roads.interchange_root.as_posix() == "wepp/roads/output/interchange"


def test_scoped_dataset_path_rewrites_only_wepp_output_prefix() -> None:
    assert scoped_dataset_path("wepp/output/interchange/loss_pw0.hill.parquet", "baseline") == (
        "wepp/output/interchange/loss_pw0.hill.parquet"
    )
    assert scoped_dataset_path("wepp/output/interchange/loss_pw0.hill.parquet", "roads") == (
        "wepp/roads/output/interchange/loss_pw0.hill.parquet"
    )
    assert scoped_dataset_path("watershed/hillslopes.parquet", "roads") == "watershed/hillslopes.parquet"
