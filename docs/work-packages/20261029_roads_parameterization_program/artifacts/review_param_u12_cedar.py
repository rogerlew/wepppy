"""Independent source and raw water/soil parity checks for final U12 Cedar review."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(pair):
    path, expected = pair
    assert sha(path) == expected, path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--u11", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    roots = {"candidate": args.candidate, "u11": args.u11, "revision3": args.reference}
    result = dict(script_sha256=sha(Path(__file__)), roots={k: str(v) for k, v in roots.items()},
                  evidence_hashes={}, raw_parity={})
    inputs, outputs, tasks = {}, {}, []
    for label, root in roots.items():
        run = root / "candidate/off"
        ip, op = run / "inputs.json", run / "outputs.json"
        inputs[label], outputs[label] = json.loads(ip.read_text()), json.loads(op.read_text())
        result["evidence_hashes"].update({str(ip): sha(ip), str(op): sha(op)})
        tasks.extend((run / "runs" / name, digest) for name, digest in inputs[label].items())
        for suffix in (".wat.dat", ".soil.dat"):
            names = [name for name in outputs[label] if name.endswith(suffix)]
            assert len(names) == 864
            tasks.extend((run / "output" / name, outputs[label][name]) for name in names)
    assert inputs["candidate"] == inputs["u11"] == inputs["revision3"]
    result["input_files_per_run"] = len(inputs["candidate"])
    for label in ("u11", "revision3"):
        changed = [name for name, digest in outputs["candidate"].items()
                   if outputs[label].get(name) != digest]
        assert not any(name.endswith((".wat.dat", ".soil.dat")) for name in changed)
        result["raw_parity"][label] = dict(water_files_identical=864, soil_files_identical=864,
                                          changed_output_names=changed)
    semantic = args.candidate / "semantic-analysis"
    manifest = json.loads((semantic / "manifest.json").read_text())
    tasks.extend((Path(name), digest) for name, digest in manifest.items())
    result["evidence_hashes"][str(semantic / "manifest.json")] = sha(semantic / "manifest.json")
    summary = json.loads((semantic / "summary.json").read_text())
    u11_summary = json.loads((args.u11 / "semantic-analysis/summary.json").read_text())
    assert summary["candidate"] == u11_summary["candidate"]
    result["semantic_metrics_identical_to_u11"] = True
    result["revision3_changes"] = summary["changes"]
    result["event_screen_count"] = summary["event_screen_count"]
    result["event_screen_ranges"] = summary["event_screen_ranges"]
    optimized = args.candidate / "candidate/yield-optimized"
    conversion = json.loads((optimized / "summary.json").read_text())
    assert conversion["dates"] == 8766
    for kind, count in (("pass", 7573824), ("wat", 16690464)):
        row = conversion["conversion"][kind]
        assert row["rows_written"] == row["accepted_records"] == row["candidate_records"] == count
        assert row["rejected_records"] == 0 and row["row_groups"] == 864
    tasks.extend((optimized / name, digest) for name, digest in conversion["output_sha256"].items())
    water = json.loads((optimized / "water-audit.json").read_text())
    assert len(water) == 17 and all(row["negative"] == row["nonfinite"] == 0 for row in water.values())
    log = args.candidate / "audit_pass_sediment.log"
    particle = json.loads(next(line for line in log.read_text().splitlines() if line.startswith("{")))
    assert particle["passed"] and particle["rows"] == 7573824
    assert len(particle["fields"]) == 10
    assert all(row["negative"] == row["nonfinite"] == row["nulls"] == 0 for row in particle["fields"].values())
    tasks.append((Path(particle["source"]), particle["source_sha256"]))
    watershed_path = args.candidate / "candidate/off/watershed.json"
    watershed = json.loads(watershed_path.read_text())
    assert watershed["success"] and watershed["returncode"] == 0 and len(watershed["years"]) == 24
    build_path = args.candidate / "candidate/build.json"
    build = json.loads(build_path.read_text())
    tasks.extend((Path(row["source"]), row["sha256"]) for row in build.values())
    result.update(candidate_binaries={name: row["sha256"] for name, row in build.items()},
                  conversion=conversion, water_audit=water, particle_audit=particle,
                  watershed=watershed)
    for path in (optimized / "summary.json", log, watershed_path, build_path):
        result["evidence_hashes"][str(path)] = sha(path)
    # Rehash the historical and current bytes, not just equal manifest strings.
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(verify, tasks))
    result.update(rehashed_files=len(tasks), all_requested_hashes_verified=True,
                  limitations=["PASS concentration/fraction positivity is not an all-event class/bulk closure proof.",
                               "Discharge publication consistency is not a full physical water budget.",
                               "Converted Parquet hashes need not match; metadata-only differences are not assumed."])
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Cedar source, semantic evidence, and all 864 raw water/soil files verified against both references.")


if __name__ == "__main__":
    main()
