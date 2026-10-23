"""Opt-in, real-controller validation on fresh copies of the local source site."""
import argparse
from collections import Counter
import json
import hashlib
from pathlib import Path
import shutil

from tests.roads.extract_fixture import digest

SOURCE_UPLOAD_SHA256 = "8c25c4938f8142395df6be7703bc0ddf2a8ff3f28bf7cb3b2ffa71b5f4385405"
EXCLUDED_FEATURE_SHA256 = "b30f47d5562e899813769eb37c84be30f9a242d429c8aa6f87c534d791902b22"

DESIGNS = ("inslope_bd", "inslope_rd", "outslope_rutted", "outslope_unrutted")


def inventory(root, folders):
    return {str(p.relative_to(root)):digest(p) for folder in folders
            for p in sorted((root / folder).rglob("*")) if p.is_file()}


def inspect_outputs(root, design):
    """Independently reconcile area and daily water totals from persisted tables."""
    import numpy as np
    import pyarrow.parquet as pq
    from wepppy.wepp.interchange.roads_accounting import load

    folder = root / "wepp/roads/output/interchange"
    ledger = load(root)
    wat = pq.read_table(folder / "H.accounting.wat.parquet").to_pandas()
    total = pq.read_table(folder / "totalwatsed3.parquet").to_pandas().set_index("sim_day_index").sort_index()
    assert len(total) == 5844 and total.index.is_unique
    assert set(total["year"]) == set(range(2000, 2016))
    assert np.array_equal(total.index, np.arange(1, 5845))
    expected_area = sum(t["area_m2"] for t in ledger["targets"])
    assert np.allclose(total["Area"], expected_area, rtol=1e-10)
    assert np.allclose(wat.groupby("sim_day_index")["Area"].sum(), expected_area, rtol=1e-10)
    for source, published in (("P", "Precipitation"), ("Dp", "Percolation"),
                              ("latqcc", "Lateral Flow"),
                              ("Ep", "Transpiration"), ("Es", "Evaporation"), ("Er", "Interception")):
        weighted = (wat[source] * wat["Area"]).groupby(wat["sim_day_index"]).sum() / expected_area
        assert np.isfinite(weighted).all() and np.isfinite(total[published]).all()
        assert np.allclose(weighted, total[published], rtol=1e-9, atol=1e-9), published
    passes = pq.read_table(folder / "H.pass.parquet", columns=["wepp_id", "sim_day_index", "runvol"]).to_pandas()
    canonical = passes[passes["wepp_id"].isin([t["id"] for t in ledger["targets"]])]
    volumes = canonical.groupby("sim_day_index")["runvol"].sum()
    assert np.allclose(volumes, total["runvol"], rtol=1e-9, atol=1e-9)
    assert np.allclose(volumes / expected_area * 1000., total["Runoff"], rtol=1e-9, atol=1e-9)
    assert np.allclose(total["Streamflow"], total["Runoff"] + total["Lateral Flow"] + total["Baseflow"])
    modes = Counter(t["mode"] for t in ledger["targets"])
    expected_mode = "replacement" if design == "outslope_unrutted" else "additive"
    assert modes[expected_mode] > 0, modes
    columns = ("Precipitation", "Runoff", "Lateral Flow", "Baseflow", "Percolation", "ET")
    baseline = pq.read_table(root / "wepp/output/interchange/totalwatsed3.parquet").to_pandas()
    return dict(modeled_area_m2=expected_area, target_modes=dict(modes),
        mean_annual_mm={c:float(total[c].sum()/16) for c in columns},
        baseline_mean_annual_mm={c:float(baseline[c].sum()/16) for c in columns},
        baseline_area_m2=float(baseline["Area"].iloc[0]), daily_area_water_reconciliation=True)


def validate_project(source, root, design, *, exclude_infeasible_unrutted=False):
    from wepppy.nodb.mods.roads import Roads
    from wepppy.wepp.interchange import _roads_lifecycle as lifecycle

    source, root = source.resolve(strict=True), root.resolve()
    if design not in DESIGNS or root == source or root.is_relative_to(source) or root.exists():
        raise ValueError("Require a supported design and a fresh independent destination")
    original = inventory(source, ("wepp", "roads", "climate"))
    original.update({p.name:digest(p) for p in source.glob("*.nodb")})
    shutil.copytree(source, root, ignore=shutil.ignore_patterns("*.log", "_logs", "_query_engine", "export"))
    # Rebase serialized clone paths BEFORE deserialization. Roads __setstate__
    # initializes its log before NoDb load corrects wd; stale wd would touch source.
    def rebase(value):
        if isinstance(value, dict):
            return {k:rebase(v) for k,v in value.items()}
        if isinstance(value, list):
            return [rebase(v) for v in value]
        if isinstance(value, str) and (value == str(source) or value.startswith(str(source) + "/")):
            return str(root) + value[len(str(source)):]
        return value
    for path in root.glob("*.nodb"):
        path.write_text(json.dumps(rebase(json.loads(path.read_text()))))
    protected = inventory(root, ("wepp/runs", "wepp/output"))
    (root / "validation-source-before.json").write_text(json.dumps(original, indent=2))
    (root / "validation-baseline-before.json").write_text(json.dumps(protected, indent=2))
    controller = Roads.getInstance(str(root))
    upload_rel = json.loads((root / "roads.nodb").read_text())["py/state"]["_uploaded_geojson_relpath"]
    assert digest(root / upload_rel) == SOURCE_UPLOAD_SHA256
    payload = json.loads((root / upload_rel).read_text())
    selection = dict(source_upload_sha256=SOURCE_UPLOAD_SHA256, source_features=len(payload["features"]), excluded=[])
    if exclude_infeasible_unrutted:
        if design != "outslope_unrutted":
            raise ValueError("Reviewed exclusion applies only to the unrutted positive control")
        excluded = [f for f in payload["features"] if str(f["properties"].get("OSUNUM")) == "6"]
        assert len(excluded) == 1
        identity = hashlib.sha256(json.dumps(excluded[0],sort_keys=True,separators=(",",":")).encode()).hexdigest()
        assert identity == EXCLUDED_FEATURE_SHA256
        payload["features"] = [f for f in payload["features"] if str(f["properties"].get("OSUNUM")) != "6"]
        selection["excluded"] = [dict(OSUNUM="6", sha256=identity, reason="reviewed_non_positive_upstream_ofe_control")]
    selection["input_features"] = len(payload["features"])
    (root / "validation-selection.json").write_text(json.dumps(selection, indent=2))
    # Mapped feature attributes take precedence over controller defaults.
    for feature in payload["features"]:
        feature["properties"]["DESIGN"] = design
        if design == "outslope_unrutted":
            # Required per-feature inputs, absent from the original rutted upload.
            feature["properties"].update(FILL_LENGTH_M=30., FILL_SLOPE_PCT=10.,
                                          BUFFER_LENGTH_M=30., BUFFER_SLOPE_PCT=10.)
    upload = root / "validation-input.geojson"
    upload.write_text(json.dumps(payload))
    controller.set_uploaded_geojson(str(upload))
    controller.prepare_segments()
    assert not lifecycle.available(root)
    result = controller.run_roads_wepp()
    assert result["status"] == "completed"
    return collect_evidence(source, root, design)


def collect_evidence(source, root, design):
    """Recheck completed fresh artifacts without rerunning the model."""
    import pyarrow.parquet as pq
    from wepppy.wepp.interchange import _roads_lifecycle as lifecycle
    from wepppy.wepp.interchange.roads_accounting import accounting_source, load

    saved_path = root / "validation.json"
    saved = json.loads(saved_path.read_text()) if saved_path.exists() else None
    protected = json.loads((root / "validation-baseline-before.json").read_text())
    original = json.loads((root / "validation-source-before.json").read_text())
    result = json.loads((root / "roads.nodb").read_text())["py/state"]["_last_run_summary"]
    assert result["status"] == "completed"
    receipt = lifecycle.require_current(root)
    records = json.loads((root / "wepp/roads/segments/roads.segment.pass.manifest.json").read_text())
    completed = [r for r in records if r.get("status") == "completed" and r.get("design") == design]
    assert completed, f"No executed {design} profiles"
    key = "replacement_targeted_hillslope_wepp_ids" if design == "outslope_unrutted" else "additive_targeted_hillslope_wepp_ids"
    assert result[key], f"No expected {key}"
    summary_path = root / "wepp/roads/output/interchange/roads_segment_loss_summary.parquet"
    summary = pq.read_table(summary_path).to_pylist()
    ids = {r["segment_run_id"] for r in summary}
    assert {r["segment_run_id"] for r in completed} <= ids
    assert all(r["simulation_years"] == 16 and r["modeled_area_m2"] > 0 for r in summary)
    ledger = load(root)
    accounting = accounting_source(root)
    assert accounting.is_file() and ledger["state"] == "ready"
    total = root / "wepp/roads/output/interchange/totalwatsed3.parquet"
    assert total.is_file()
    table = pq.read_table(total)
    assert table.num_rows > 0
    for r in completed:
        run_id = r["segment_run_id"]
        for extension in ("slp", "sol", "man", "cli", "run"):
            assert (root / f"wepp/roads/runs/p{run_id}.{extension}").stat().st_size > 0
    assert inventory(root, ("wepp/runs", "wepp/output")) == protected
    assert all(digest(source / name) == value for name,value in original.items())
    upload_path = root / "validation-input.geojson"
    upload = json.loads(upload_path.read_text())
    selection_path = root / "validation-selection.json"
    if selection_path.exists():
        selection = json.loads(selection_path.read_text())
    else:
        # Early additive checks predate explicit selection metadata; prove the
        # retained full upload against the source identity recorded before execution.
        assert design != "outslope_unrutted"
        assert original["roads/roads.uploaded.geojson"] == SOURCE_UPLOAD_SHA256
        assert len(upload["features"]) == 55
        selection = dict(source_upload_sha256=SOURCE_UPLOAD_SHA256, source_features=55, input_features=55, excluded=[])
    assert digest(source / "roads/roads.uploaded.geojson") == SOURCE_UPLOAD_SHA256
    expected_upload = json.loads((source / "roads/roads.uploaded.geojson").read_text())
    if selection["excluded"]:
        assert design == "outslope_unrutted"
        assert selection["excluded"] == [dict(OSUNUM="6", sha256=EXCLUDED_FEATURE_SHA256,
                                              reason="reviewed_non_positive_upstream_ofe_control")]
        expected_upload["features"] = [f for f in expected_upload["features"] if str(f["properties"].get("OSUNUM")) != "6"]
    for feature in expected_upload["features"]:
        feature["properties"]["DESIGN"] = design
        if design == "outslope_unrutted":
            feature["properties"].update(FILL_LENGTH_M=30., FILL_SLOPE_PCT=10., BUFFER_LENGTH_M=30., BUFFER_SLOPE_PCT=10.)
    assert upload == expected_upload
    assert len(upload["features"]) == selection["input_features"]
    assert all(f["properties"]["DESIGN"] == design for f in upload["features"])
    from tests.roads.roads_matrix import read_management
    template_dir = Path(__file__).resolve().parents[2] / "wepppy/nodb/mods/roads/legacy_templates/managements"
    management_readback = {}
    for record in completed:
        run_id = record["segment_run_id"]
        slope = root / f"wepp/roads/runs/p{run_id}.slp"
        count = int(slope.read_text().splitlines()[1])
        order = ((1,) if count == 1 else (1,3)) if design.startswith("inslope") else (
            (1,2,3) if design == "outslope_rutted" else ((3,1,2) if count == 3 else (3,1,2,3)))
        template = template_dir / ("3inslopen.man" if record["traffic"] == "none" else "3inslope.man")
        management_readback[str(run_id)] = read_management(root / f"wepp/roads/runs/p{run_id}.man", template, order)
    prepared_count = len(json.loads((root / "wepp/roads/segments/roads.inslope.monotonic.geojson").read_text())["features"])
    evidence = dict(design=design, management_readback=management_readback, selection=selection, prepared_features=prepared_count, input_sha256=digest(upload_path), root=str(root), completed_at=result["completed_at"],
        completed_profiles=len(completed), summary_profiles=len(summary),
        execution_counts={k:v for k,v in result.items() if k.endswith("_count")},
        skipped_reasons=dict(Counter(str(r.get("reason") or r.get("skip_reason")) for r in records if r.get("status") == "skipped")),
        routing_mode_counts=dict(Counter(r.get("routing_mode") for r in completed)),
        target_ids=result[key], receipt=receipt, accounting_state=ledger["state"],
        accounting_sha256=digest(accounting), totalwatsed_sha256=digest(total),
        totalwatsed_rows=table.num_rows, summary_sha256=digest(summary_path),
        experiment_unrutted_fill_buffer="30 m at 10% each",
        protected_baseline_files=len(protected), unchanged_source_files=len(original),
        reconciliation=inspect_outputs(root, design),
        params=json.loads((root / "roads.nodb").read_text())["py/state"]["_roads_params"],
        prepared_inputs=inventory(root, ("wepp/roads/runs",)))
    if saved is not None:
        for field in ("prepared_inputs", "summary_sha256", "accounting_sha256", "totalwatsed_sha256", "input_sha256"):
            assert evidence[field] == saved[field], f"Changed project execution artifact: {field}"
        if "selection" in saved:
            assert evidence["selection"] == saved["selection"]
    (root / "validation.json").write_text(json.dumps(evidence, indent=2, allow_nan=False)+"\n")
    return evidence


def verify_negative(source, root):
    """Retain the exact full-upload rejection; never turn model failures into passes."""
    from wepppy.wepp.interchange import _roads_lifecycle as lifecycle

    assert not lifecycle.available(root)
    assert not (root / lifecycle.RECEIPT).exists()
    original = json.loads((root / "validation-source-before.json").read_text())
    baseline = json.loads((root / "validation-baseline-before.json").read_text())
    assert all(digest(source / name) == value for name,value in original.items())
    assert inventory(root, ("wepp/runs", "wepp/output")) == baseline
    assert original["roads/roads.uploaded.geojson"] == SOURCE_UPLOAD_SHA256
    manifests = []
    for path in (root / "wepp/roads/history").glob("*/wepp/roads/segments/roads.segment.pass.manifest.json"):
        rows = json.loads(path.read_text())
        failed = [r for r in rows if r.get("status") == "failed"]
        if failed:
            manifests.append((path, failed))
    assert len(manifests) == 1
    path, failed = manifests[0]
    assert len(failed) == 2
    assert {r["target_hillslope_topaz_id"] for r in failed} == {271, 272}
    assert all(r["reason"] == "failed_non_positive_top_ofe" and r["segment_id"] == "roads-seg-000001" for r in failed)
    upload = json.loads((root / "validation-input.geojson").read_text())
    assert len(upload["features"]) == 55
    assert all(f["properties"]["DESIGN"] == "outslope_unrutted" and
               all(f["properties"][k] == v for k,v in dict(FILL_LENGTH_M=30., FILL_SLOPE_PCT=10.,
                   BUFFER_LENGTH_M=30., BUFFER_SLOPE_PCT=10.).items()) for f in upload["features"])
    assert not (root / lifecycle.RECEIPT).exists()
    evidence = dict(root=str(root), source_upload_sha256=SOURCE_UPLOAD_SHA256,
        input_features=55, excluded_features=0, failed_records=failed,
        manifest_relpath=str(path.relative_to(root)), manifest_sha256=digest(path),
        current_receipt_absent=True, unchanged_source_files=len(original),
        unchanged_baseline_files=len(baseline))
    (root / "validation-negative.json").write_text(json.dumps(evidence, indent=2))
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("design", choices=DESIGNS)
    parser.add_argument("--verify-negative", action="store_true")
    parser.add_argument("--exclude-infeasible-unrutted", action="store_true", help="Reviewed positive control only: exclude exact source OSUNUM6")
    parser.add_argument("--verify-existing", action="store_true", help="Recheck saved receipt and before/after hashes; do not rerun WEPP")
    args = parser.parse_args()
    if args.verify_negative:
        result = verify_negative(args.source, args.destination)
    elif args.verify_existing:
        result = collect_evidence(args.source, args.destination, args.design)
    else:
        result = validate_project(args.source, args.destination, args.design,
                                  exclude_infeasible_unrutted=args.exclude_infeasible_unrutted)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
