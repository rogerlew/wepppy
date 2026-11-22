from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.nodb.mods.features_export import service
from wepppy.nodb.mods.features_export.cache_key import CacheKeyParts
from wepppy.nodb.mods.features_export.contracts import (
    NormalizedExportRequest,
    ResolvedExportPlan,
    ResolvedLayerPlan,
)
from wepppy.nodb.mods.features_export.dependency_tracker import DependencySnapshot

pytestmark = pytest.mark.unit


def _ag_fields_metric_plan() -> ResolvedExportPlan:
    request = NormalizedExportRequest(
        format="geopackage",
        units="si",
        layers=("ag_fields.metrics.subfields",),
        crs="wgs",
        output_scopes=("baseline",),
        swat_run_id="none",
    )
    return ResolvedExportPlan(
        catalog_version="test-catalog-v1",
        schema_version=1,
        request=request,
        layers=(
            ResolvedLayerPlan(
                layer_id="ag_fields.metrics.subfields",
                family="ag_fields_metrics",
                scope_class="scope_invariant",
                scope="shared",
                output_layer_id="shared__ag_fields.metrics.subfields",
            ),
        ),
        warnings=(),
    )


def test_prepare_export_submission_passes_nodb_ref_resolver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = NormalizedExportRequest(
        format="geopackage",
        units="si",
        layers=("watershed.subcatchments",),
        crs="wgs",
        output_scopes=("baseline",),
        swat_run_id="none",
    )
    plan = ResolvedExportPlan(
        catalog_version="test-catalog-v1",
        schema_version=1,
        request=request,
        layers=(
            ResolvedLayerPlan(
                layer_id="watershed.subcatchments",
                family="watershed",
                scope_class="scope_invariant",
                scope="shared",
                output_layer_id="shared__watershed.subcatchments",
            ),
        ),
        warnings=(),
    )
    fake_catalog = SimpleNamespace()
    captured: dict[str, object] = {}

    monkeypatch.setattr(service, "load_layer_catalog", lambda: fake_catalog)
    monkeypatch.setattr(service, "resolve_export_plan", lambda payload, catalog: plan)
    monkeypatch.setattr(service, "_resolve_plan_swat_run_id", lambda resolved_plan, wd_path: resolved_plan)

    def _fake_build_dependency_snapshot(plan_arg, catalog_arg, wd_path_arg, **kwargs):
        captured["plan"] = plan_arg
        captured["catalog"] = catalog_arg
        captured["wd_path"] = wd_path_arg
        captured["resolver"] = kwargs.get("nodb_ref_resolver")
        return DependencySnapshot(
            catalog_signature="catalog-signature",
            entries=(),
            fingerprint="dependency-fingerprint",
        )

    monkeypatch.setattr(service, "build_dependency_snapshot", _fake_build_dependency_snapshot)
    monkeypatch.setattr(
        service,
        "build_cache_key",
        lambda *args, **kwargs: CacheKeyParts(
            request_hash="request-hash",
            dependency_fingerprint="dependency-fingerprint",
            cache_key="request-hash+dependency-fingerprint",
        ),
    )
    monkeypatch.setattr(
        service,
        "Watershed",
        SimpleNamespace(
            getInstance=lambda wd: SimpleNamespace(subwta_shp="watershed/subwta.shp"),
        ),
    )

    submission = service.prepare_export_submission(tmp_path, {"format": "geopackage"})

    assert submission.plan is plan
    assert captured["plan"] is plan
    assert captured["catalog"] is fake_catalog
    resolver = captured["resolver"]
    assert callable(resolver)
    assert resolver(str(tmp_path), "watershed", "subwta_shp") == "watershed/subwta.shp"


def _write_shallow_ag_fields_bundle(wd: Path) -> tuple[Path, Path]:
    from wepppy.wepp.interchange import ag_fields_interchange as interchange

    mapping_path = wd / "ag_fields" / "sub_fields" / "fields.parquet"
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.table(
            {
                "field_id": pa.array([7], type=pa.int32()),
                "sub_field_id": pa.array([2], type=pa.int32()),
            }
        ),
        mapping_path,
    )
    interchange_dir = wd / "wepp" / "ag_fields" / "output" / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    summaries: dict[str, dict[str, object]] = {}
    for family, contract in interchange._FAMILY_CONTRACTS.items():
        target_path = interchange_dir / contract[2]
        target_path.write_bytes(f"bundle-{family}".encode("ascii"))
        zero_row_source_count = 1 if family == "ebe" else 0
        identity_count = 1 - zero_row_source_count
        summaries[family] = {
            "rows": identity_count,
            "row_groups": identity_count,
            "size_bytes": target_path.stat().st_size,
            "identity_count": identity_count,
            "source_count": 1,
            "zero_row_source_count": zero_row_source_count,
            "zero_row_sub_field_ids": [2] if zero_row_source_count else [],
        }
    manifest_path = interchange_dir / "interchange_version.json"
    manifest_path.write_text(
        json.dumps(
            {
                "dataset_kind": interchange.DATASET_KIND,
                "ag_fields_schema_version": interchange.AG_FIELDS_SCHEMA_VERSION,
                "major": interchange.INTERCHANGE_VERSION.major,
                "source_mapping_sha256": hashlib.sha256(
                    mapping_path.read_bytes()
                ).hexdigest(),
                "files": summaries,
            }
        ),
        encoding="utf-8",
    )
    return mapping_path, manifest_path


def _files_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize(
    "stale_reason",
    ("cleared_completion_marker", "mapping_hash_mismatch", "wrong_major"),
)
def test_prepare_export_submission_rejects_stale_ag_fields_interchange_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stale_reason: str,
) -> None:
    from wepppy.wepp.interchange import ag_fields_interchange as interchange

    mapping_path, manifest_path = _write_shallow_ag_fields_bundle(tmp_path)
    completion_marker_current = stale_reason != "cleared_completion_marker"
    if stale_reason == "mapping_hash_mismatch":
        pq.write_table(
            pa.table(
                {
                    "field_id": pa.array([8], type=pa.int32()),
                    "sub_field_id": pa.array([2], type=pa.int32()),
                }
            ),
            mapping_path,
        )
    elif stale_reason == "wrong_major":
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["major"] = interchange.INTERCHANGE_VERSION.major + 1
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    controller = SimpleNamespace(
        has_current_wepp_ag_fields_interchange=lambda: (
            completion_marker_current
            and interchange._is_wepp_ag_fields_interchange_complete(
                tmp_path / "wepp" / "ag_fields" / "output",
                mapping_path,
            )
        )
    )
    monkeypatch.setattr(
        service.AgFields,
        "load_detached",
        classmethod(lambda _cls, _wd, allow_nonexistent=True: controller),
    )
    plan = _ag_fields_metric_plan()
    monkeypatch.setattr(service, "load_layer_catalog", lambda: SimpleNamespace())
    monkeypatch.setattr(service, "resolve_export_plan", lambda _payload, _catalog: plan)
    monkeypatch.setattr(service, "_resolve_plan_swat_run_id", lambda value, _wd: value)
    monkeypatch.setattr(
        service,
        "build_dependency_snapshot",
        lambda *_args, **_kwargs: pytest.fail(
            "stale AgFields readiness must fail before dependency planning"
        ),
    )
    before = _files_snapshot(tmp_path)

    with pytest.raises(service.FeaturesExportServiceError) as exc_info:
        service.prepare_export_submission(tmp_path, {"format": "geopackage"})

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "ag_fields_interchange_not_current"
    assert _files_snapshot(tmp_path) == before


def test_ag_fields_interchange_readiness_gate_accepts_current_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wepppy.wepp.interchange import ag_fields_interchange as interchange

    mapping_path, _manifest_path = _write_shallow_ag_fields_bundle(tmp_path)
    controller = SimpleNamespace(
        has_current_wepp_ag_fields_interchange=lambda: (
            interchange._is_wepp_ag_fields_interchange_complete(
                tmp_path / "wepp" / "ag_fields" / "output",
                mapping_path,
            )
        )
    )
    monkeypatch.setattr(
        service.AgFields,
        "load_detached",
        classmethod(lambda _cls, _wd, allow_nonexistent=True: controller),
    )
    before = _files_snapshot(tmp_path)

    service._require_current_ag_fields_interchange(
        tmp_path,
        _ag_fields_metric_plan(),
    )

    assert _files_snapshot(tmp_path) == before


def test_nodb_ref_resolver_rejects_unsupported_controller(tmp_path: Path) -> None:
    with pytest.raises(service.FeaturesExportServiceError, match="Unsupported nodb_ref controller"):
        service._resolve_nodb_ref_relpath(str(tmp_path), "landuse", "landuse_shp")
