"""Isolate MAN-03 with real parsers; write only into a new evidence directory."""

from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path

from wepppy.wepp.management import read_management
from wepppy.wepp.management.managements import Loops
from wepppy.wepp.management.utils import ManagementMultipleOfeSynth


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = Path("tests/wepp/management/fixtures/ag_fields_rotation_synth/oats_spring_conventional.man")
    oats = read_management(str(source))
    observations = []

    def capture(name, management):
        path = args.output / f"{name}.man"
        path.write_text(str(management))
        record = {
            "case": name,
            "declared_sim_years": management.sim_years,
            "rotation_lengths": [len(rotation.years) for rotation in management.man.loops],
            "total_emitted_years": sum(len(rotation.years) for rotation in management.man.loops),
            "intended_references": [[[ref.loop_name for ref in ofe.manindx]
                                     for year in rotation.years for ofe in year]
                                    for rotation in management.man.loops],
        }
        try:
            reloaded = read_management(str(path))
        except (IndexError, ValueError, AssertionError) as exc:
            record["readback"] = {"status": "failed", "type": type(exc).__name__, "error": str(exc)}
        else:
            record["readback"] = {
                "status": "parsed",
                "references": [[[ref.loop_name for ref in ofe.manindx]
                                for year in rotation.years for ofe in year]
                               for rotation in reloaded.man.loops],
            }
        observations.append(record)

    capture("source_roundtrip", oats)
    capture("source_expanded_4", oats.build_multiple_year_man(4))

    # Experimental in-memory normalization, not a production patch or native proof.
    normalized = deepcopy(oats)
    rotation = deepcopy(normalized.man.loops[0])
    rotation.years = Loops()
    for item in normalized.man.loops:
        rotation.years.extend(deepcopy(item.years))
    normalized.man.loops = Loops()
    normalized.man.loops.append(rotation)
    normalized.setroot()
    capture("normalized_source", normalized)
    capture("normalized_expanded_4", normalized.build_multiple_year_man(4))

    combined = ManagementMultipleOfeSynth([oats, oats]).build()
    records = [year[1] for rotation in combined.man.loops for year in rotation.years]
    observations.append({"case": "combined_downstream_year_objects", "distinct_objects": len({id(x) for x in records}), "year_count": len(records)})
    result = {
        "scope": "Actual writer/parser boundary; normalization is an isolated experiment, no native execution",
        "source": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "producer_sha256": hashlib.sha256(Path("wepppy/wepp/management/managements.py").read_bytes()).hexdigest(),
        "observations": observations,
    }
    (args.output / "observations.json").write_text(json.dumps(result, indent=2) + "\n")
    manifest = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(args.output.iterdir()) if path.is_file()}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
