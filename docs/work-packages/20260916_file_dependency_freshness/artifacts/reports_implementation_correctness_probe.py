"""Actual report generation/compatibility on disposable projects only."""
import ast
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pyarrow.parquet as pq
from wepppy.nodb.core import Watershed
from wepppy.wepp.reports.average_annuals_by_landuse import AverageAnnualsByLanduseReport
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport
from wepppy.wepp.reports import _cache_freshness as freshness

# Reuse retained fixture writers without executing the earlier stale assertions.
fixture_path = Path(__file__).with_name("reports_freshness_baseline_probe.py")
tree = ast.parse(fixture_path.read_text())
namespace = {}
exec(compile(ast.Module(body=[node for node in tree.body if isinstance(
    node, (ast.Import, ast.ImportFrom, ast.FunctionDef))], type_ignores=[]), str(fixture_path), "exec"), namespace)
results = {}


def observe(label, callback):
    try:
        report = callback()
        results[label] = {"cache_status": report.cache_status}
    except Exception as exc:  # Deliberate probe capture; retain actual failure.
        results[label] = {"error_type": type(exc).__name__, "error": str(exc)}


with TemporaryDirectory(prefix="reports-implementation-correctness-") as temporary:
    base = Path(temporary)
    run = base / "translator"
    namespace["write_watershed"](run)
    namespace["write_wat"](run)
    with patch.object(Watershed, "getInstance", side_effect=namespace["watershed_for_run"]):
        HillslopeWatbalReport(run)
        (run / "watershed/hillslopes.parquet").unlink()
        try:
            namespace["watershed_for_run"](run).translator_factory()
        except RuntimeError as exc:
            results["actual_translator_absence"] = {
                "error": str(exc),
                "initial_implementation_expected": "No sub_ids/chns_ids available for translator (no summaries or parquet files)",
                "initial_error_literal_matched": str(exc) == "No sub_ids/chns_ids available for translator (no summaries or parquet files)",
            }
        observe("current_missing_translator", lambda: HillslopeWatbalReport(run))

    run = base / "original"
    namespace["write_landuse_sources"](run)
    AverageAnnualsByLanduseReport(run)
    (run / "landuse/landuse.parquet").unlink()
    relocated = base / "relocated"
    shutil.copytree(run, relocated)
    shutil.rmtree(run)
    observe("relocated_partial_archive", lambda: AverageAnnualsByLanduseReport(relocated))
    catalog_path = relocated / "_query_engine/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    catalog["root"] = str(relocated)
    catalog_path.write_text(json.dumps(catalog))
    observe("relocated_rebased_catalog_control", lambda: AverageAnnualsByLanduseReport(relocated))

    run = base / "complete_original"
    namespace["write_landuse_sources"](run)
    AverageAnnualsByLanduseReport(run)
    relocated = base / "complete_relocated"
    shutil.copytree(run, relocated)
    namespace["rewrite_table"](relocated / "wepp/output/interchange/loss_pw0.hill.parquet",
                               lambda frame: frame.__setitem__("Runoff Volume", [900.0, 30.0]))
    result = AverageAnnualsByLanduseReport(relocated)
    results["complete_relocation_current_local_runoff"] = {
        "cache_status": result.cache_status,
        "local_input_runoff_m3": 900.0,
        "returned_runoff_mm": [dict(row.row)["Avg Runoff Depth (mm/yr)"] for row in result
                               if dict(row.row)["Landuse ID"] == 100][0],
    }

    run = base / "malformed_alias"
    namespace["write_landuse_sources"](run)
    AverageAnnualsByLanduseReport(run)
    cache = run / "wepp/reports/cache/average_annuals_by_landuse.parquet"
    table = pq.read_table(cache)
    metadata = dict(table.schema.metadata)
    proof = json.loads(metadata[freshness._METADATA_KEY])
    proof["dependencies"]["landuse/landuse.parquet:aliases"] = None
    metadata[freshness._METADATA_KEY] = json.dumps(proof).encode()
    pq.write_table(table.replace_schema_metadata(metadata), cache)
    (run / "landuse/landuse.parquet").unlink()
    catalog_path = run / "_query_engine/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    catalog["files"] = [entry for entry in catalog["files"] if entry["path"] != "landuse/landuse.parquet"]
    catalog_path.write_text(json.dumps(catalog))
    observe("malformed_alias_proof_with_missing_source", lambda: AverageAnnualsByLanduseReport(run))

    run = base / "legacy_partial_corrupt"
    namespace["write_landuse_sources"](run)
    AverageAnnualsByLanduseReport(run)
    cache = run / "wepp/reports/cache/average_annuals_by_landuse.parquet"
    table = pq.read_table(cache)
    metadata = dict(table.schema.metadata)
    metadata.pop(freshness._METADATA_KEY)
    pq.write_table(table.replace_schema_metadata(metadata), cache)
    (run / "landuse/landuse.parquet").unlink()
    (run / "watershed/hillslopes.parquet").write_bytes(b"not a parquet file")
    observe("legacy_partial_archive_with_malformed_remaining_input", lambda: AverageAnnualsByLanduseReport(run))

    run = base / "redirected_history"
    namespace["write_landuse_sources"](run)
    AverageAnnualsByLanduseReport(run)
    logical = "wepp/output/interchange/loss_pw0.hill.parquet"
    selected = run / "wepp/output/interchange/selected-loss.parquet"
    shutil.copyfile(run / logical, selected)
    catalog_path = run / "_query_engine/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    for entry in catalog["files"]:
        if entry["path"] == logical:
            entry["fs_path"] = str(selected.relative_to(run))
    catalog_path.write_text(json.dumps(catalog))
    AverageAnnualsByLanduseReport(run)
    for relative in (logical, "watershed/hillslopes.parquet", "landuse/landuse.parquet"):
        (run / relative).unlink()
    selected.unlink()
    shutil.rmtree(catalog_path.parent)
    observe("missing_catalog_with_redirected_historical_source", lambda: AverageAnnualsByLanduseReport(run))
    catalog_path.parent.mkdir(exist_ok=True)
    catalog_path.write_text(json.dumps(catalog))
    observe("redirected_historical_catalog_control", lambda: AverageAnnualsByLanduseReport(run))

print(json.dumps(results, indent=2))
output = Path(__file__).with_name(sys.argv[1] + ".json") if len(sys.argv) > 1 else Path(__file__).with_suffix(".json")
output.write_text(json.dumps(results, indent=2) + "\n")
