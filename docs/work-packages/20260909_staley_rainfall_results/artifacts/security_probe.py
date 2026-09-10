"""Direct local-file security review evidence; run with wctl run-python."""
from pathlib import Path
import copy
import json
import os
import stat
from tempfile import TemporaryDirectory

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.nodb.mods.postfire_debris_flow import rainfall_io as io
from wepppy.nodb.mods.postfire_debris_flow.results import (
    RainfallInputs, build_m1_results, get_event, list_events, open_results,
)


def main():
    checks = []

    def rejects(label, code, operation):
        try:
            operation()
        except io.RainfallError as exc:
            assert exc.code == code, (label, exc.code)
        else:
            raise AssertionError(f"{label} was accepted")
        checks.append(label)

    with TemporaryDirectory(prefix="rainfall-security-") as temporary:
        root = Path(temporary)
        text = root / "value.json"
        text.write_text('{"value": 1}')
        assert io.read_json(text) == {"value": 1}
        checks.append("valid regular JSON")
        link = root / "symlink.json"
        link.symlink_to(text)
        rejects("leaf symlink", "invalid_input", lambda: io.regular(link))
        parent = root / "parent-link"
        parent.symlink_to(root, target_is_directory=True)
        rejects("parent symlink", "invalid_input", lambda: io.regular(parent / text.name))
        rejects("parent traversal", "invalid_input", lambda: io.regular(root / "x/../value.json"))
        fifo = root / "pipe"
        os.mkfifo(fifo)
        rejects("FIFO before open", "invalid_input", lambda: io.regular(fifo))
        rejects("file byte limit", "resource_limit", lambda: io.regular(text, limit=1))
        rejects("missing expected digest", "missing_provenance", lambda: io.pinned(text, {}, {}))
        rejects("incorrect digest", "provenance_mismatch", lambda: io.pinned(text, {str(text): "0" * 64}, {}))
        consumed = {}
        io.pinned(text, {str(text): io.digest(text)}, consumed)
        text.write_text('{"value": 2}')
        rejects("source mutation recheck", "source_changed", lambda: io.recheck(consumed))
        for label, content in (("duplicate JSON keys", '{"a":1,"a":2}'),
                               ("nonfinite JSON", '{"a":NaN}'),
                               ("overflow JSON exponent", '{"a":1e309}')):
            text.write_text(content)
            rejects(label, "invalid_input", lambda: io.read_json(text))

        parquet = root / "table.parquet"
        table = pa.table({"prcp": [1.0], "year": [1], "peak_intensity_15": [12.0]})
        pq.write_table(table, parquet)
        assert io.read_table(parquet, max_rows=1, numeric=True).equals(table)
        checks.append("valid numeric parquet")
        rejects("parquet row limit", "resource_limit", lambda: io.read_table(parquet, max_rows=0))
        pq.write_table(pa.table({"nested": [[1]]}), parquet)
        rejects("nested input column", "invalid_input", lambda: io.read_table(parquet, max_rows=1, numeric=True))
        pq.write_table(pa.table({"text": ["x"]}), parquet)
        rejects("string input column", "invalid_input", lambda: io.read_table(parquet, max_rows=1, numeric=True))
        pq.write_table(pa.Table.from_arrays([pa.array([1]), pa.array([2])], names=["a", "a"]), parquet)
        rejects("duplicate parquet columns", "invalid_input", lambda: io.read_table(parquet, max_rows=1))
        pq.write_table(table, parquet)
        metadata = pq.read_metadata(parquet)
        metadata.set_file_path("/unopened-security-sentinel.parquet")
        metadata.write_metadata_file(root / "external.parquet")
        rejects("external parquet chunk", "invalid_input", lambda: io.read_table(root / "external.parquet", max_rows=1))

        repo = Path(__file__).resolve().parents[4]
        predictors = repo / "docs/work-packages/20260909_staley_m1_predictors/artifacts/generated/wallow-rebuilt-final/bundle/manifest.json"
        inputs = RainfallInputs(
            predictor_manifest=predictors, cli_parquet=parquet,
            expected_sha256={str(predictors): io.digest(predictors), str(parquet): io.digest(parquet)},
            project_id="direct-security-fixture", climate_mode="controlled",
            date_semantics="simulation_labels", assessment_id="pinned-wallow-fixture",
        )
        output = root / "bundle"
        options = dict(frequency_source="noaa", return_intervals=[1], durations=[15], target_probabilities=[.5])
        build_m1_results(inputs, output, **options)
        assert stat.S_IMODE(output.stat().st_mode) == 0o700
        catalog = open_results(output, expected_manifest_sha256=io.digest(output / "manifest.json"))
        rows = list_events(catalog, duration_minutes=15)["rows"]
        assert len(rows) == 1 and len(get_event(catalog, rows[0]["event_id"])["rows"]) == 1
        checks.append("fresh private output and valid round-trip query")
        rejects("query page bound", "invalid_input", lambda: list_events(catalog, duration_minutes=15, limit=1001))
        rejects("query sort injection", "invalid_input", lambda: list_events(catalog, duration_minutes=15, sort="__import__('os')"))
        rejects("malformed event ID", "invalid_input", lambda: get_event(catalog, "../../manifest.json"))
        old_digest = io.digest(output / "manifest.json")
        rejects("existing output preservation", "output_exists", lambda: build_m1_results(inputs, output, **options))
        assert io.digest(output / "manifest.json") == old_digest
        rejects("output parent symlink", "invalid_input", lambda: build_m1_results(inputs, parent / "other-bundle", **options))
        (root / "incomplete").mkdir()
        rejects("incomplete bundle rejection", "incomplete_output", lambda: open_results(root / "incomplete", expected_manifest_sha256="0" * 64))
        rejects("result manifest hash mismatch", "provenance_mismatch", lambda: open_results(output, expected_manifest_sha256="0" * 64))
        manifest_path = output / "manifest.json"
        original_manifest = io.read_json(manifest_path)
        changed_manifest = copy.deepcopy(original_manifest)
        changed_manifest["tables"]["../../outside-events"] = changed_manifest["tables"].pop("events")
        manifest_path.write_text(json.dumps(changed_manifest))
        rejects("manifest-controlled table traversal", "invalid_input", lambda: open_results(output, expected_manifest_sha256=io.digest(manifest_path)))
        changed_manifest = copy.deepcopy(original_manifest)
        changed_manifest["sources_sha256"]["/unopened-security-sentinel/provenance"] = "0" * 64
        changed_manifest["predictor_snapshot"]["sources_sha256"]["/unopened-security-sentinel/predictor"] = "0" * 64
        manifest_path.write_text(json.dumps(changed_manifest))
        open_results(output, expected_manifest_sha256=io.digest(manifest_path))
        checks.append("embedded provenance paths are not reopened")
        manifest_path.write_text(json.dumps(original_manifest))
        old_digest = io.digest(manifest_path)
        with (output / "events.parquet").open("ab") as stream:
            stream.write(b"changed")
        rejects("result table mutation", "provenance_mismatch", lambda: open_results(output, expected_manifest_sha256=old_digest))
    print(json.dumps({"passed": len(checks), "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
