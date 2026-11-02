"""Exercise actual native slope writers in a fresh, explicitly named directory."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from wepppyo3 import wepp_interchange as api
from wepppyo3.wepp_interchange import wepp_interchange_rust as native


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-root", type=Path, default=Path("/workdir/wepppyo3"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.output / "source.slp"
    source.write_text("97.5\n1\n100 10\n2 100\n0, 0.1 1, 0.1\n")
    cases = [
        ("tiny", "explicit", {"breakpoints": [0, 0.00001, 1]}),
        ("zero_buffer", "automatic", {"apply_buffer": True, "buffer_length": 0}),
        ("negative_buffer", "automatic", {"apply_buffer": True, "buffer_length": -10}),
        ("min_length", "automatic", {"target_length": 1, "min_length": 10, "max_ofes": 200}),
    ]
    results = []
    for name, kind, kwargs in cases:
        output = args.output / f"{name}.slp"
        writer = (api.segment_single_ofe_slope_at_breakpoints if kind == "explicit"
                  else api.segment_single_ofe_slope)
        count = writer(str(source), dst_fn=str(output), **kwargs)
        results.append({"case": name, "arguments": kwargs, "returned_ofes": count,
                        "output": output.name,
                        "sha256": hashlib.sha256(output.read_bytes()).hexdigest()})
    extension = Path(native.__file__).resolve()
    record = {
        "executable": sys.executable,
        "argv": sys.argv,
        "pythonpath": os.environ.get("PYTHONPATH"),
        "extension": str(extension),
        "extension_sha256": hashlib.sha256(extension.read_bytes()).hexdigest(),
        "source_root": str(args.source_root.resolve()),
        "source_head": subprocess.check_output(
            ["git", "-C", str(args.source_root), "rev-parse", "HEAD"], text=True).strip(),
        "source_status": subprocess.check_output(
            ["git", "-C", str(args.source_root), "status", "--short"], text=True),
        "source_input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "results": results,
        "claim": "Native writer readback only; no native WEPP execution or build provenance claim.",
    }
    (args.output / "readback.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
