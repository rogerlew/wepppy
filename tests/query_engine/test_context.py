from __future__ import annotations

import json
from pathlib import Path

import pytest

from wepppy.query_engine.context import resolve_run_context

pytestmark = pytest.mark.unit


def _write_catalog(run_root: Path) -> None:
    catalog_dir = run_root / "_query_engine"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    catalog_payload = {
        "version": 1,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "root": str(run_root),
        "files": [],
    }
    (catalog_dir / "catalog.json").write_text(json.dumps(catalog_payload), encoding="utf-8")


def test_resolve_run_context_with_bare_omni_scenario_name(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    scenario_dir = run_dir / "_pups" / "omni" / "scenarios" / "burned"
    scenario_dir.mkdir(parents=True)
    _write_catalog(scenario_dir)

    context = resolve_run_context(str(run_dir), scenario="burned", auto_activate=False)

    assert context.base_dir == scenario_dir
    assert context.scenario == "burned"


def test_resolve_run_context_with_bare_rhessys_scenario_name(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    scenario_dir = run_dir / "rhessys" / "scenarios" / "S1"
    scenario_dir.mkdir(parents=True)
    _write_catalog(scenario_dir)

    context = resolve_run_context(str(run_dir), scenario="S1", auto_activate=False)

    assert context.base_dir == scenario_dir
    assert context.scenario == "S1"


def test_resolve_run_context_prefers_omni_for_ambiguous_bare_name(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    omni_dir = run_dir / "_pups" / "omni" / "scenarios" / "shared"
    rhessys_dir = run_dir / "rhessys" / "scenarios" / "shared"
    omni_dir.mkdir(parents=True)
    rhessys_dir.mkdir(parents=True)
    _write_catalog(omni_dir)
    _write_catalog(rhessys_dir)

    context = resolve_run_context(str(run_dir), scenario="shared", auto_activate=False)

    assert context.base_dir == omni_dir


def test_resolve_run_context_accepts_explicit_rhessys_path(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    scenario_dir = run_dir / "rhessys" / "scenarios" / "S2"
    scenario_dir.mkdir(parents=True)
    _write_catalog(scenario_dir)

    context = resolve_run_context(str(run_dir), scenario="rhessys/scenarios/S2", auto_activate=False)

    assert context.base_dir == scenario_dir
    assert context.scenario == "rhessys/scenarios/S2"


def test_resolve_run_context_accepts_omni_path_without_pups_prefix(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    scenario_dir = run_dir / "_pups" / "omni" / "scenarios" / "undisturbed"
    scenario_dir.mkdir(parents=True)
    _write_catalog(scenario_dir)

    context = resolve_run_context(str(run_dir), scenario="omni/scenarios/undisturbed", auto_activate=False)

    assert context.base_dir == scenario_dir


def test_resolve_run_context_rejects_traversal_scenarios(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)

    with pytest.raises(FileNotFoundError):
        resolve_run_context(str(run_dir), scenario="../outside", auto_activate=False)


def test_resolve_run_context_treats_blank_scenario_as_base(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)
    _write_catalog(run_dir)

    context = resolve_run_context(str(run_dir), scenario="  ", auto_activate=False)

    assert context.base_dir == run_dir


def test_resolve_run_context_does_not_treat_arbitrary_child_dir_as_bare_scenario(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    child_dir = run_dir / "dem"
    child_dir.mkdir(parents=True)
    _write_catalog(child_dir)

    with pytest.raises(FileNotFoundError):
        resolve_run_context(str(run_dir), scenario="dem", auto_activate=False)


def test_held_context_reloads_changed_schema_without_receipt(tmp_path: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    from wepppy.query_engine.context import refresh_run_context
    from wepppy.query_engine.core import run_query
    from wepppy.query_engine.payload import QueryRequest

    source = tmp_path / "data.parquet"
    pq.write_table(pa.table({"TopazID": [1]}), source)
    _write_catalog(tmp_path)
    context = resolve_run_context(str(tmp_path), auto_activate=False)
    refresh_run_context(context, ["data.parquet"])
    pq.write_table(pa.table({"topaz_id": [42]}), source)

    result = run_query(context, QueryRequest(datasets=["data.parquet"], columns=["TopazID"]))

    assert result.records == [{"TopazID": 42}]
    assert context.catalog.get("data.parquet").schema["fields"][0]["name"] == "topaz_id"


def test_report_context_refreshes_already_indexed_source(tmp_path: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    from wepppy.wepp.reports.helpers import ReportQueryContext

    source = tmp_path / "data.parquet"
    pq.write_table(pa.table({"before": [1]}), source)
    _write_catalog(tmp_path)
    report = ReportQueryContext(tmp_path)
    report.ensure_datasets("data.parquet")
    held = report.context
    pq.write_table(pa.table({"after": [2]}), source)

    report.ensure_datasets("data.parquet")

    assert report.context is held
    assert report.catalog.get("data.parquet").schema["fields"][0]["name"] == "after"


def test_readonly_required_source_change_does_not_publish(tmp_path: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    from wepppy.query_engine.context import refresh_run_context

    source = tmp_path / "data.parquet"
    pq.write_table(pa.table({"before": [1]}), source)
    _write_catalog(tmp_path)
    context = resolve_run_context(str(tmp_path), auto_activate=False)
    refresh_run_context(context, ["data.parquet"])
    catalog_path = tmp_path / "_query_engine/catalog.json"
    previous = catalog_path.read_bytes()
    (tmp_path / "READONLY").touch()
    refresh_run_context(context, ["data.parquet"])
    pq.write_table(pa.table({"after": [2]}), source)

    with pytest.raises(PermissionError):
        refresh_run_context(context, ["data.parquet"])

    assert catalog_path.read_bytes() == previous


def test_query_authorizes_refreshed_physical_selection(tmp_path: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    from wepppy.query_engine.context import refresh_run_context
    from wepppy.query_engine.core import run_query
    from wepppy.query_engine.payload import QueryRequest

    pq.write_table(pa.table({"value": [1]}), tmp_path / "old.parquet")
    pq.write_table(pa.table({"value": [2]}), tmp_path / "new.parquet")
    _write_catalog(tmp_path)
    context = resolve_run_context(str(tmp_path), auto_activate=False)
    refresh_run_context(context, ["old.parquet"])
    catalog_path = tmp_path / "_query_engine/catalog.json"
    data = json.loads(catalog_path.read_text())
    entry = data["files"][0]
    entry["path"] = "logical.parquet"
    entry["fs_path"] = "new.parquet"
    catalog_path.write_text(json.dumps(data))
    observed = []

    def deny_selected_source(fresh):
        observed.append(fresh.catalog.get("logical.parquet").fs_path)
        raise PermissionError("Selected source denied")

    with pytest.raises(PermissionError, match="Selected source denied"):
        run_query(context, QueryRequest(datasets=["logical.parquet"]), authorize=deny_selected_source)

    assert observed == ["new.parquet"]


@pytest.mark.parametrize("contents", ["{", '{"root": null, "files": []}'])
def test_reader_repairs_malformed_catalog_before_query(tmp_path: Path, contents: str) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    from wepppy.query_engine.core import run_query
    from wepppy.query_engine.payload import QueryRequest

    pq.write_table(pa.table({"value": [42]}), tmp_path / "data.parquet")
    _write_catalog(tmp_path)
    catalog_path = tmp_path / "_query_engine/catalog.json"
    catalog_path.write_text(contents)

    context = resolve_run_context(str(tmp_path), auto_activate=False)
    result = run_query(context, QueryRequest(datasets=["data.parquet"]))

    assert result.records == [{"value": 42}]
    assert context.catalog.has("data.parquet")
    assert json.loads(catalog_path.read_text())["root"] == str(tmp_path)
    attempts = list((tmp_path / "_query_engine/refresh/attempts").glob("malformed-*.json"))
    assert len(attempts) == 1
    assert json.loads(attempts[0].read_text())["state"] == "malformed_catalog"


def test_readonly_reader_does_not_repair_malformed_catalog(tmp_path: Path) -> None:
    _write_catalog(tmp_path)
    catalog_path = tmp_path / "_query_engine/catalog.json"
    catalog_path.write_text("{")
    (tmp_path / "READONLY").touch()

    with pytest.raises(PermissionError):
        resolve_run_context(str(tmp_path), auto_activate=False)

    assert catalog_path.read_text() == "{"
    assert not (tmp_path / "_query_engine/refresh").exists()
