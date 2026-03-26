from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.nodb.mods.features_export.catalog_loader import parse_layer_catalog
from wepppy.nodb.mods.features_export.dependency_tracker import (
    DependencyResolutionError,
    build_catalog_signature,
    build_dependency_snapshot,
)
from wepppy.nodb.mods.features_export.planner import resolve_export_plan

pytestmark = pytest.mark.unit


def _resolver_contract() -> dict[str, object]:
    return {
        "allowed_locator_kinds": ["nodb_ref", "relpath", "path_template"],
        "path_template_vars": {
            "scope_root": {
                "values": {
                    "baseline": "output",
                    "roads": "roads/output",
                }
            }
        },
        "temporal_modes": ["annual_average", "yearly", "event"],
        "event_selectors": ["date", "return_period"],
    }


def _base_metadata() -> dict[str, object]:
    return {
        "catalog_version": "wp2-test",
        "schema_version": 2,
        "updated_at_utc": "2026-03-26T00:00:00Z",
        "owner": "tests",
        "status": "draft",
        "resolver_contract": _resolver_contract(),
    }


def _write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_build_dependency_snapshot_is_deterministic_and_tracks_project_unitizer_dependency(tmp_path: Path) -> None:
    catalog = parse_layer_catalog(
        {
            "metadata": _base_metadata(),
            "layers": [
                {
                    "layer_id": "test.scope.layer",
                    "family": "test",
                    "scope_class": "scope_aware",
                    "geometry": {
                        "type": "polygon",
                        "locator": {"kind": "nodb_ref", "value": "nodb:watershed.subwta_shp"},
                        "feature_id_keys": ["id"],
                    },
                    "join": {"primary_key": "id", "fallback_keys": []},
                    "sources": [
                        {
                            "source_id": "scope_metrics",
                            "kind": "parquet",
                            "locator": {
                                "kind": "path_template",
                                "value": "wepp/{scope_root}/interchange/loss.parquet",
                            },
                            "required": True,
                            "role": "metrics",
                        }
                    ],
                    "dependencies": [
                        {
                            "dep_id": "wepp_state",
                            "kind": "nodb",
                            "locator": {"kind": "relpath", "value": "wepp.nodb"},
                            "required": True,
                            "purpose": "controller state",
                        }
                    ],
                    "temporal": {
                        "supported_modes": [],
                        "grain": "none",
                        "time_columns": [],
                        "mode_rules": {},
                    },
                    "measures": {"required": ["id"], "optional": []},
                }
            ],
        },
        source_name="<memory>",
    )

    plan = resolve_export_plan(
        {
            "format": "geoparquet",
            "units": "project",
            "layers": ["test.scope.layer"],
            "output_scopes": ["roads", "baseline"],
            "swat_run_id": "run_2026032601",
        },
        catalog,
    )

    geometry_path = tmp_path / "geometry" / "subcatchments.WGS.geojson"
    _write(geometry_path, "geojson")
    _write(tmp_path / "wepp" / "output" / "interchange" / "loss.parquet", "baseline")
    _write(tmp_path / "wepp" / "roads" / "output" / "interchange" / "loss.parquet", "roads")
    _write(tmp_path / "wepp.nodb", "state")
    _write(tmp_path / "unitizer.nodb", "unitizer")

    def resolve_nodb_ref(wd: str, controller: str, attribute: str) -> str:
        assert wd == str(tmp_path.resolve())
        if controller == "watershed" and attribute == "subwta_shp":
            return str(geometry_path)
        raise AssertionError(f"Unexpected nodb_ref request: {controller}.{attribute}")

    snapshot_a = build_dependency_snapshot(
        plan,
        catalog,
        tmp_path,
        nodb_ref_resolver=resolve_nodb_ref,
        content_hash_mode="sha256",
    )
    snapshot_b = build_dependency_snapshot(
        plan,
        catalog,
        tmp_path,
        nodb_ref_resolver=resolve_nodb_ref,
        content_hash_mode="sha256",
    )

    assert snapshot_a.catalog_signature == build_catalog_signature(catalog)
    assert snapshot_a.fingerprint == snapshot_b.fingerprint
    assert len(snapshot_a.entries) == 7

    relpaths = {entry.relpath for entry in snapshot_a.entries}
    assert relpaths == {
        "geometry/subcatchments.WGS.geojson",
        "wepp/output/interchange/loss.parquet",
        "wepp/roads/output/interchange/loss.parquet",
        "wepp.nodb",
        "unitizer.nodb",
    }
    assert any(entry.dependency_role == "unitizer" for entry in snapshot_a.entries)
    assert all(
        entry.content_hash_marker == "sha256" and entry.content_hash_value
        for entry in snapshot_a.entries
        if entry.exists
    )

    _write(tmp_path / "wepp" / "roads" / "output" / "interchange" / "loss.parquet", "roads-updated")
    snapshot_c = build_dependency_snapshot(
        plan,
        catalog,
        tmp_path,
        nodb_ref_resolver=resolve_nodb_ref,
        content_hash_mode="sha256",
    )

    assert snapshot_c.fingerprint != snapshot_a.fingerprint


def test_build_dependency_snapshot_requires_nodb_ref_resolver_for_nodb_locator(tmp_path: Path) -> None:
    catalog = parse_layer_catalog(
        {
            "metadata": _base_metadata(),
            "layers": [
                {
                    "layer_id": "test.nodb.layer",
                    "family": "test",
                    "scope_class": "scope_invariant",
                    "geometry": {
                        "type": "polygon",
                        "locator": {"kind": "nodb_ref", "value": "nodb:watershed.subwta_shp"},
                        "feature_id_keys": ["id"],
                    },
                    "join": {"primary_key": "id", "fallback_keys": []},
                    "sources": [
                        {
                            "source_id": "attrs",
                            "kind": "parquet",
                            "locator": {"kind": "relpath", "value": "attrs.parquet"},
                            "required": True,
                            "role": "attributes",
                        }
                    ],
                    "dependencies": [],
                    "temporal": {
                        "supported_modes": [],
                        "grain": "none",
                        "time_columns": [],
                        "mode_rules": {},
                    },
                    "measures": {"required": ["id"], "optional": []},
                }
            ],
        },
        source_name="<memory>",
    )

    plan = resolve_export_plan(
        {
            "format": "geojson",
            "units": "si",
            "layers": ["test.nodb.layer"],
            "swat_run_id": "run_2026032601",
        },
        catalog,
    )

    with pytest.raises(DependencyResolutionError, match="nodb_ref locator requires"):
        build_dependency_snapshot(plan, catalog, tmp_path)


def test_build_dependency_snapshot_requires_table_name_resolution_for_path_templates(tmp_path: Path) -> None:
    catalog = parse_layer_catalog(
        {
            "metadata": _base_metadata(),
            "layers": [
                {
                    "layer_id": "test.swat.layer",
                    "family": "swat_interchange",
                    "scope_class": "scope_invariant",
                    "geometry": {
                        "type": "polygon",
                        "locator": {"kind": "relpath", "value": "watershed/subcatchments.geojson"},
                        "feature_id_keys": ["subbasin"],
                    },
                    "join": {"primary_key": "subbasin", "fallback_keys": []},
                    "sources": [
                        {
                            "source_id": "swat_table",
                            "kind": "parquet",
                            "locator": {
                                "kind": "path_template",
                                "value": "swat/outputs/run_{swat_run_id}/interchange/{table_name}.parquet",
                            },
                            "required": True,
                            "role": "metrics",
                        }
                    ],
                    "dependencies": [
                        {
                            "dep_id": "swat_state",
                            "kind": "nodb",
                            "locator": {"kind": "relpath", "value": "swat.nodb"},
                            "required": True,
                            "purpose": "state",
                        }
                    ],
                    "temporal": {
                        "supported_modes": [],
                        "grain": "none",
                        "time_columns": [],
                        "mode_rules": {},
                    },
                    "measures": {"required": [], "optional": []},
                }
            ],
        },
        source_name="<memory>",
    )

    plan = resolve_export_plan(
        {
            "format": "geoparquet",
            "units": "english",
            "layers": ["test.swat.layer"],
            "swat_run_id": "run_424242",
        },
        catalog,
    )

    _write(tmp_path / "watershed" / "subcatchments.geojson", "geom")
    _write(tmp_path / "swat.nodb", "swat")

    with pytest.raises(DependencyResolutionError, match="requires table_name selector resolution"):
        build_dependency_snapshot(plan, catalog, tmp_path)

    _write(tmp_path / "swat" / "outputs" / "run_run_424242" / "interchange" / "basin_wb.parquet", "b")
    _write(tmp_path / "swat" / "outputs" / "run_run_424242" / "interchange" / "hru_wb.parquet", "h")

    snapshot = build_dependency_snapshot(
        plan,
        catalog,
        tmp_path,
        table_names_by_output_layer_id={"shared__test.swat.layer": ["hru_wb", "basin_wb"]},
    )

    source_relpaths = sorted(
        entry.relpath
        for entry in snapshot.entries
        if entry.dependency_role == "source"
    )
    assert source_relpaths == [
        "swat/outputs/run_run_424242/interchange/basin_wb.parquet",
        "swat/outputs/run_run_424242/interchange/hru_wb.parquet",
    ]
