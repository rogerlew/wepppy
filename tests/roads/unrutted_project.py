"""Current-policy full-upload controls; historical Roads report readers stay separate."""
from collections import defaultdict
import json
import math
from pathlib import Path
import shutil

from tests.roads.roads_matrix import read_management
from tests.roads.roads_project import digest, inspect_outputs, inventory

SOURCE_UPLOAD_SHA256 = "fa32c9ad8d43789acaca5b19f324c89871510913c10fae0fd29a939c6e4eec1f"
FAILED_PROFILE_IDS = {
    "roads-seg-000005::7d9376e34ba1::h43",
    "roads-seg-000005::effc04073fe3::h62",
    "roads-seg-000005::137156d35d01::h63",
    "roads-seg-000007::0c3c0abdfade::h143",
    "roads-seg-000007::75d0e71f09aa::h143",
}


def _source_inventory(root):
    result = inventory(root, ("wepp", "roads", "climate"))
    result.update({p.name: digest(p) for pattern in ("*.nodb", "*.cfg") for p in root.glob(pattern)})
    return result


def _rebase(value, source, destination):
    if isinstance(value, dict):
        return {key: _rebase(item, source, destination) for key, item in value.items()}
    if isinstance(value, list):
        return [_rebase(item, source, destination) for item in value]
    if isinstance(value, str) and (value == str(source) or value.startswith(str(source) + "/")):
        return str(destination) + value[len(str(source)):]
    return value


def _positive_readback(root, result):
    from wepppy.nodb.mods.roads import _unrutted
    from wepppy.wepp.interchange import _roads_lifecycle as lifecycle
    from wepppy.wepp.soils.utils import WeppSoilUtil

    lifecycle.require_current(root)
    assert result["status"] == "completed" and result["executed_segment_count"] == 24
    records = json.loads((root / "wepp/roads/segments/roads.segment.pass.manifest.json").read_text())
    prepared = json.loads((root / "wepp/roads/segments/roads.inslope.monotonic.geojson").read_text())
    source_ids = {f["properties"]["segment_id"] for f in prepared["features"]}
    areas = defaultdict(list)
    profiles = {}
    template_dir = Path(__file__).resolve().parents[2] / "wepppy/nodb/mods/roads/legacy_templates/managements"
    for record in records:
        if record.get("status") != "completed":
            continue
        identifier = record["segment_run_id"]
        slope = root / f"wepp/roads/runs/p{identifier}.slp"
        areas[record["target_hillslope_topaz_id"]].append(_unrutted.slope_area(slope))
        if record["design"] == "outslope_unrutted_remainder":
            roles = ["buffer"]
        else:
            assert record["placement_policy"] == _unrutted.PLACEMENT_POLICY
            assert set(record["source_segment_ids"]) <= source_ids
            roles = (["buffer"] if record["top_landuse_length_m"] > 0 else []) + ["road", "fill"]
            if record["bottom_landuse_length_m"] > 0:
                roles.append("buffer")
        parameterization = record["parameterization"]
        assert [ofe["role"] for ofe in parameterization["ofes"]] == roles
        for file in parameterization["input_files"]:
            assert digest(root / file["relpath"]) == file["sha256"]
        soil = WeppSoilUtil(str(root / f"wepp/roads/runs/p{identifier}.sol")).obj["ofes"]
        assert [ofe["slid"] for ofe in soil] == [{"road": "Road", "fill": "Fill", "buffer": "Forest"}[role] for role in roles]
        assert int(slope.read_text().splitlines()[1]) == len(roles)
        order = tuple({"road": 1, "fill": 2, "buffer": 3}[role] for role in roles)
        template = template_dir / ("3inslopen.man" if record.get("traffic") == "none" else "3inslope.man")
        profiles[str(identifier)] = read_management(root / f"wepp/roads/runs/p{identifier}.man", template, order)
    assert len(profiles) == 24
    for hill in result["outslope_unrutted_hillslope_records"]:
        emitted = areas[hill["topaz_id_hill"]]
        if hill["reference_area_m2"] is None:
            assert not emitted
            continue
        assert abs(math.fsum(emitted) - hill["reference_area_m2"]) <= 1e-6
    return {"management_readback": profiles, "reconciliation": inspect_outputs(root, "outslope_unrutted")}


def _negative_readback(root, result):
    from wepppy.wepp.interchange import _roads_lifecycle as lifecycle

    assert result["status"] == "failed" and result["failed_segment_count"] == 5
    assert result["executed_segment_count"] == 15
    assert not lifecycle.available(root) and not (root / lifecycle.RECEIPT).exists()
    failed = [row for row in result["segment_execution_records"] if row.get("status") == "failed"]
    assert {row["segment_hillslope_id"] for row in failed} == FAILED_PROFILE_IDS
    for row in failed:
        assert row["reason"] == "failed_road_fill_exceeds_hillslope"
        # Unrutted simulation road length is the physical road width.
        dimensions = [row[key] for key in ("hillslope_length_m", "road_width_m", "fill_length_m")]
        assert all(math.isfinite(value) and value > 0 for value in dimensions)
        assert row["road_width_m"] + row["fill_length_m"] > row["hillslope_length_m"]
    return {"failed_records": failed, "current_receipt_absent": True}


def validate_unrutted_project(source, root, *, fill_length_m):
    """Run one pinned 5 m-positive or 30 m-negative synthetic geometry control."""
    from wepp_runner.wepp_runner import get_linux_wepp_bin_role_paths
    from wepppy.nodb.mods.roads import Roads, _unrutted
    from wepppy.wepp.interchange import _roads_lifecycle as lifecycle

    source, root = Path(source).resolve(strict=True), Path(root).resolve()
    if fill_length_m not in (5.0, 30.0) or root.exists() or root.is_relative_to(source):
        raise ValueError("Require a declared 5 m/30 m control and fresh independent destination")
    assert digest(source / "roads/roads.uploaded.geojson") == SOURCE_UPLOAD_SHA256
    before = _source_inventory(source)
    shutil.copytree(source, root, ignore=shutil.ignore_patterns("*.log", "_logs", "_query_engine", "export"))
    for path in root.glob("*.nodb"):
        path.write_text(json.dumps(_rebase(json.loads(path.read_text()), source, root)))
    protected = inventory(root, ("wepp/runs", "wepp/output"))
    (root / "validation-source-before.json").write_text(json.dumps(before, indent=2))
    (root / "validation-baseline-before.json").write_text(json.dumps(protected, indent=2))
    values = dict(FILL_LENGTH_M=fill_length_m, FILL_SLOPE_PCT=10., BUFFER_LENGTH_M=30., BUFFER_SLOPE_PCT=10.)
    payload = json.loads((root / "roads/roads.uploaded.geojson").read_text())
    assert len(payload["features"]) == 55
    for feature in payload["features"]:
        feature["properties"].update(DESIGN="outslope_unrutted", **values)
    upload = root / "validation-input.geojson"
    upload.write_text(json.dumps(payload))
    declaration = dict(source=str(source), source_upload_sha256=SOURCE_UPLOAD_SHA256,
                       synthetic_inputs=values, input_sha256=digest(upload), input_features=55,
                       excluded_features=[], purpose="geometry acceptance, not site prediction")
    try:
        roads = Roads.getInstance(str(root))
        binary = roads.wepp_instance.wepp_bin
        assert binary == "wepp_260803"
        declaration["native_binaries"] = {path: digest(Path(path)) for path in get_linux_wepp_bin_role_paths(binary)}
        (root / "validation-declaration.json").write_text(json.dumps(declaration, indent=2))
        roads.set_uploaded_geojson(str(upload))
        prepared = roads.prepare_segments()
        (root / "validation-prepared.json").write_text(json.dumps(prepared, indent=2))
        assert not lifecycle.available(root)
        try:
            roads.run_roads_wepp()
        except RuntimeError as exc:
            if fill_length_m != 30.0:
                raise
            assert "segment execution failed for 5 segment(s)" in str(exc)
            (root / "validation-expected-error.txt").write_text(str(exc))
        else:
            assert fill_length_m == 5.0, "Oversized geometry unexpectedly succeeded"
        result = json.loads((root / "roads.nodb").read_text())["py/state"]["_last_run_summary"]
        (root / "validation-result.json").write_text(json.dumps(result, indent=2))
        assert result["unrutted_placement_policy"] == _unrutted.PLACEMENT_POLICY
        readback = _positive_readback(root, result) if fill_length_m == 5.0 else _negative_readback(root, result)
        evidence = dict(declaration=declaration, status=result["status"], readback=readback,
                        executed_segment_count=result["executed_segment_count"],
                        artifacts=inventory(root, ("wepp/roads/runs", "wepp/roads/output", "wepp/roads/segments")))
        (root / "validation-current-unrutted.json").write_text(json.dumps(evidence, indent=2))
        return evidence
    finally:
        assert before == _source_inventory(source), "Original project changed"
        assert protected == inventory(root, ("wepp/runs", "wepp/output")), "Copied baseline changed"
