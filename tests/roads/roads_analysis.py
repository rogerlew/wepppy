"""Fail-closed native Roads matrix analysis and report generation."""
import argparse
import json
import math
from dataclasses import asdict
from pathlib import Path

from tests.roads.extract_fixture import digest
from tests.roads.roads_matrix import CASES, site

REPO = Path(__file__).resolve().parents[2]
SUITE = REPO / "tests/roads"


def source_hashes():
    paths = list(SUITE.glob("*.py")) + [SUITE / "analysis_context.md"] + list((SUITE / "data").rglob("*"))
    paths += list((REPO / "wepppy/nodb/mods/roads").glob("*.py"))
    paths += list((REPO / "wepppy/nodb/mods/roads/legacy_templates").rglob("*"))
    paths += list((REPO / "wepp_runner").glob("*.py"))
    paths += list((REPO / "wepp_runner/templates").rglob("*"))
    paths += list((REPO / "wepppy/wepp/interchange").glob("*.py"))
    paths += [REPO / "wepp_runner/bin" / (site()["binary"] + suffix) for suffix in ("", "_hill")]
    return {str(p.relative_to(REPO)):digest(p) for p in sorted(set(paths)) if p.is_file()}


def records(root, expected=CASES):
    paths = list(root.glob("case-*.json"))
    result = sorted((json.loads(p.read_text()) for p in paths), key=lambda r:r["segment_run_id"])
    if len(result) != len(expected) or [r["name"] for r in result] != [c.name for c in expected]:
        raise ValueError("Matrix missing, duplicate, or unexpected case identities")
    if [r["segment_run_id"] for r in result] != list(range(1,len(expected)+1)):
        raise ValueError("Matrix run identifiers differ")
    for record, case in zip(result, expected):
        if record["case"] != asdict(case):
            raise ValueError("Matrix case metadata differs from definition")
        if record["status"] != "completed":
            raise ValueError("Matrix contains incomplete case")
        identifier = record["segment_run_id"]
        required_inputs = {f"wepp/roads/runs/p{identifier}.{ext}" for ext in ("run","slp","sol","man","cli")}
        required_outputs = {f"wepp/roads/output/H{identifier}.{ext}.dat" for ext in ("pass","wat")}
        if not required_inputs <= record["input_sha256"].keys() or not required_outputs <= record["output_sha256"].keys():
            raise ValueError("Missing mandatory artifact identities")
        for key in ("input_sha256", "output_sha256", "template_sha256"):
            if not record[key]:
                raise ValueError("Missing source identity")
            for name, expected_hash in record[key].items():
                path = (REPO if key == "template_sha256" else root) / name
                if digest(path) != expected_hash:
                    raise ValueError(f"Changed matrix artifact: {name}")
    return result


def analyze(root):
    import pyarrow.parquet as pq
    from wepppy.wepp.interchange.hill_pass_interchange import run_wepp_hillslope_pass_interchange
    from wepppy.wepp.interchange.hill_wat_interchange import run_wepp_hillslope_wat_interchange
    from wepppy.nodb.mods.roads._segment_loss_summary import build_segment_loss_summary

    from tests.roads.roads_matrix import execution_identity
    if json.loads((root / "execution-identity.json").read_text()) != execution_identity():
        raise ValueError("Execution sources changed; rerun matrix")
    staged = json.loads((root / "staged-inputs.json").read_text())
    from tests.roads.extract_fixture import DATA
    expected_staged = {"climate/site.cli": digest(DATA / "site.cli"),
                      **{f"wepp/roads/runs/{p.name}":digest(p) for p in (DATA / "shared").iterdir()}}
    if staged != expected_staged or any(digest(root / p) != h for p,h in staged.items()):
        raise ValueError("Staged shared scientific inputs changed")
    evidence = records(root)
    output = root / "wepp/roads/output"
    run_wepp_hillslope_pass_interchange(output, expected_hillslopes=len(CASES))
    run_wepp_hillslope_wat_interchange(output, expected_hillslopes=len(CASES))
    (root / "wepp/roads/segments/roads.segment.pass.manifest.json").write_text(json.dumps(evidence, indent=2))
    relative = build_segment_loss_summary(root, output / "interchange", expected_years=site()["simulation_years"], start_year=2000)
    rows = pq.read_table(root / relative).to_pylist()
    by_id = {r["segment_run_id"]:r for r in rows}
    for record in evidence:
        summary = by_id[record["segment_run_id"]]
        area = record["emitted"]["width_m"] * sum(record["emitted"]["lengths_m"])
        # WAT prints limited precision; preserve WAT area as the metric denominator.
        if not math.isclose(summary["modeled_area_m2"], area, rel_tol=1e-6, abs_tol=.0051 * len(record["ofe_order"])):
            raise ValueError(f"WAT/prepared slope area mismatch: {record['name']}")
        record["summary"] = summary
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    rows = analyze(args.root)
    (args.root / "analysis.json").write_text(json.dumps(rows, indent=2, allow_nan=False)+"\n")
    print(f"Validated {len(rows)} complete native profile summaries")


if __name__ == "__main__":
    main()
