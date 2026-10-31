"""Replay either retained fraction case; require exact ordinary-output parity."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

CASES = {
    "denver_fraction": "downstream-buffer_cap/denver-1718465-outunrut-gravel-none-erosion_road_cap-project",
    "site_fraction": "roads/site-2711250-outunrut-paved-low-erosion_road_cap-project",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--case", action="append", choices=CASES)
    args = parser.parse_args()
    results = []
    for label in args.case or CASES:
        source = args.candidate_root / CASES[label]
        record_path = source / "record.json"
        record = json.loads(record_path.read_text())
        folder = args.output_root / label
        runs = folder / "runs"
        runs.mkdir(parents=True, exist_ok=False)
        output = folder / "output"
        output.mkdir()
        for name, digest in record["inputs"].items():
            assert sha(source / "runs" / name) == digest
            shutil.copy2(source / "runs" / name, runs / name)
        with (runs / "p1.run").open() as inp, (runs / "stdout").open("w") as out, (runs / "stderr").open("w") as err:
            proc = subprocess.run([str(args.binary.resolve())], cwd=runs, stdin=inp,
                                  stdout=out, stderr=err, timeout=300)
        outputs = {path.name: sha(path) for path in output.iterdir() if path.is_file()}
        assert proc.returncode == 0 and outputs == record["outputs"], label
        for name, digest in record["inputs"].items():
            assert sha(runs / name) == digest
        trace = folder / "trace.txt"
        trace.write_text("\n".join(line.strip() for line in (runs / "stdout").read_text().splitlines()
                                   if line.strip().startswith(("PM_", "NC_"))) + "\n")
        receipt = dict(label=label, source=str(source), source_record_sha256=sha(record_path),
                       inputs=record["inputs"], outputs=outputs, trace_sha256=sha(trace),
                       exact_output_parity=True, returncode=proc.returncode,
                       binary_sha256=sha(args.binary))
        (folder / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        results.append(receipt)
        print(label, "exact output parity", flush=True)
    (args.output_root / "results.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
