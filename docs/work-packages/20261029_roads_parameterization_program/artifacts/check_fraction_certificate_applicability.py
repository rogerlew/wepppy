"""Check the retained two-case certificate against an explicit later candidate."""
import argparse
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--observer-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("audit", Path(__file__).with_name("audit_particle_closure.py"))
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    cases = {
        "denver_fraction": "downstream-buffer_cap/denver-1718465-outunrut-gravel-none-erosion_road_cap-project",
        "site_fraction": "roads/site-2711250-outunrut-paved-low-erosion_road_cap-project",
    }
    result = dict(script_sha256=audit.digest(Path(__file__)),
                  audit_script_sha256=audit.digest(Path(audit.__file__)), cases={})
    for label, relative in cases.items():
        old_path = args.baseline_root / relative / "record.json"
        new_path = args.candidate_root / relative / "record.json"
        old, new = (json.loads(path.read_text()) for path in (old_path, new_path))
        for path, record in ((old_path, old), (new_path, new)):
            for name, digest in record["outputs"].items():
                assert audit.digest(path.parent / "output" / name) == digest
        assert old["inputs"] == new["inputs"]
        before, after = audit.audit(old_path), audit.audit(new_path)
        assert before["flags"] == after["flags"] and len(after["flags"]) == 1
        item = dict(candidate_record=str(new_path), candidate_record_sha256=audit.digest(new_path),
                    candidate_binary_sha256=new["binary_sha256"], inputs_identical=True,
                    strict_flag_identical=True, flag=after["flags"][0],
                    baseline_output_hashes=old["outputs"], candidate_output_hashes=new["outputs"],
                    all_ordinary_outputs_identical=old["outputs"] == new["outputs"])
        if label == "denver_fraction":
            assert item["all_ordinary_outputs_identical"]
            item["basis"] = "All ordinary output hashes identical across the complete simulation."
        else:
            observer = args.observer_root / "u12-applicability"
            folder = observer / "runs" / label
            receipt_path = folder / "receipt.json"
            receipt = json.loads(receipt_path.read_text())
            assert receipt["exact_output_parity"] and receipt["outputs"] == new["outputs"]
            assert receipt["source_record_sha256"] == audit.digest(new_path)
            assert receipt["trace_sha256"] == audit.digest(folder / "trace.txt")
            assert receipt["binary_sha256"] == audit.digest(observer / "wepp")
            for name, digest in receipt["outputs"].items():
                assert audit.digest(folder / "output" / name) == digest
            def event_lines(path):
                return [line.split() for line in path.read_text().splitlines()
                        if line.startswith("PM_") and line.split()[1:3] == ["2003", "29"]]
            original_trace = args.observer_root / "class_normalization" / "runs" / label / "trace.txt"
            old_lines, new_lines = event_lines(original_trace), event_lines(folder / "trace.txt")
            assert old_lines == new_lines and any(line[0] == "PM_CLASS" for line in new_lines)
            item.update(basis="Full-period observer matches U12 outputs exactly; all target-day PM observations match U11.",
                        observer_receipt_sha256=audit.digest(receipt_path),
                        observer_trace_sha256=receipt["trace_sha256"],
                        identical_event_observations=new_lines)
        result["cases"][label] = item
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Both retained numerical certificates apply to the exact candidate flagged events.")


if __name__ == "__main__":
    main()
