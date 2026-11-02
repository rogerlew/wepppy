"""Capture actual management-writer observations without changing production inputs.

Run with the WEPPpy virtualenv from the repository root. The output directory
must not exist; existing evidence is never overwritten. No native model runs.
"""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(repo))

    from wepppy.wepp.management import read_management
    from wepppy.wepp.management.managements import get_plant_loop_names
    from wepppy.wepp.management.pmetpara import pmetpara_prep
    from wepppy.wepp.management.utils import ManagementMultipleOfeSynth

    source_files = [
        "wepppy/wepp/management/managements.py",
        "wepppy/wepp/management/pmetpara.py",
        "wepppy/wepp/management/utils/multi_ofe.py",
        "wepppy/nodb/mods/disturbed/disturbed.py",
        "wepppy/nodb/core/wepp_prep_service.py",
        "wepppy/nodb/core/landuse.py",
        "tests/wepp/management/test_multiple_ofe.py",
        "tests/wepp/management/fixtures/ag_fields_rotation_synth/oats_spring_conventional.man",
        "wepppy/wepp/management/data/Agriculture/corn,soybean-no till.man",
    ]
    source_hashes = {name: sha256(repo / name) for name in source_files}

    fixture_tree = ast.parse((repo / source_files[6]).read_text())
    fire_text = next(
        ast.literal_eval(node.value)
        for node in fixture_tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "HIGH_SEVERITY_FIRE_MAN"
                for target in node.targets)
    )
    sources = output / "sources"
    sources.mkdir()
    fire_path = sources / "fire.man"
    fire_path.write_text(fire_text)
    oats_path = sources / "oats.man"
    oats_path.write_bytes((repo / source_files[7]).read_bytes())
    corn_path = sources / "corn_soybean.man"
    corn_path.write_bytes((repo / source_files[8]).read_bytes())

    pmet_dir = output / "pmet"
    pmet_dir.mkdir()
    ManagementMultipleOfeSynth([read_management(str(fire_path)), read_management(str(fire_path))]).write(
        str(pmet_dir / "p1.man")
    )
    pmetpara_prep(str(pmet_dir), kcb=0.95, rawp=0.8)
    pmet_readback = read_management(str(pmet_dir / "p1.man"))
    pmet_observation = {
        "serialized_plants": [plant.name for plant in pmet_readback.plants],
        "collector_result": get_plant_loop_names(str(pmet_dir)),
        "pmetpara": (pmet_dir / "pmetpara.txt").read_text(),
    }

    first, second = read_management(str(oats_path)), read_management(str(oats_path))
    second.plants[-1].data.hmax = 0.123
    residue_path = output / "residue.man"
    ManagementMultipleOfeSynth([first, second]).write(str(residue_path))
    residue = read_management(str(residue_path))
    residue_observation = {
        "ofe2_last_plant_hmax_mutation": 0.123,
        "plants": [{"index": i + 1, "name": plant.name, "hmax": plant.data.hmax}
                   for i, plant in enumerate(residue.plants)],
        "residue_operations": [
            {"name": operation.name, "plant_name": operation.data.iresad.loop_name,
             "plant_index": str(operation.data.iresad)}
            for operation in residue.ops if operation.data.pcode == 10
        ],
    }

    base, other = read_management(str(oats_path)), read_management(str(corn_path))
    mixed = ManagementMultipleOfeSynth([base, other]).build()
    rotation_path = output / "rotation.man"
    rotation_path.write_text(str(mixed))
    expanded_path = output / "rotation_expanded.man"
    expanded = mixed.build_multiple_year_man(4)
    expanded_path.write_text(str(expanded))

    def yearly_names(management, ofe):
        return [[[reference.loop_name for reference in year[ofe].manindx]
                 for year in rotation.years] for rotation in management.man.loops]

    # Capture a parser failure as explicit audit evidence, not a passing check.
    try:
        expanded_readback = read_management(str(expanded_path))
    except (IndexError, ValueError, AssertionError) as error:
        expanded_parse = {"status": "failed", "error_type": type(error).__name__, "error": str(error)}
    else:
        expanded_parse = {"status": "passed", "ofe2_refs": yearly_names(expanded_readback, 1)}
    rotation_observation = {
        "source_rotation_lengths": [[len(rotation.years) for rotation in management.man.loops]
                                    for management in (base, other)],
        "second_source_yearly_refs": yearly_names(other, 0),
        "combined_ofe2_refs": yearly_names(read_management(str(rotation_path)), 1),
        "expanded_in_memory_ofe2_refs": yearly_names(expanded, 1),
        "expanded_serialized_readback": expanded_parse,
    }
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv,
        "repo": str(repo),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "script_sha256": sha256(Path(__file__).resolve()),
        "source_sha256": source_hashes,
        "pmet": pmet_observation,
        "residue": residue_observation,
        "rotation": rotation_observation,
        "scope": "Actual Python writers and serialized/reparsed artifacts; no native execution or broad tests.",
    }
    changed = [name for name, digest in source_hashes.items() if sha256(repo / name) != digest]
    if changed:
        raise RuntimeError(f"Source changed during reproduction: {changed}")
    (output / "observations.json").write_text(json.dumps(result, indent=2) + "\n")
    artifacts = {str(path.relative_to(output)): sha256(path)
                 for path in sorted(output.rglob("*")) if path.is_file()}
    (output / "manifest.json").write_text(json.dumps(artifacts, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
