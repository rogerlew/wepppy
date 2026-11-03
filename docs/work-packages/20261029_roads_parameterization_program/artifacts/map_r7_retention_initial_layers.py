"""Read-only, case-bound native initialization geometry; never runs the model.

This maps source horizon support, not native floating-point water coefficients.
The native initialization sequence and assumptions are reviewed separately in
resumption-r7-retention-initial-layer-review.md. Output is additive/exclusive.
"""

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import shlex
import subprocess


SOURCE_COMMIT = "e0abe0581f77c6f66917e90daf8f8f429e9315c8"
PREP_DECLARATION = "5be61161a62c428867735328cd9b085da64473e13d26d92f8b8aae88bb87da7b"
MANAGEMENT = "6ed3319bd1bce803b0cd2efbf631765b6d6e1f00bd2534f59358df11f9ecb31c"
SOURCE_FILES = (
    "contin.for", "infile.for", "input.for", "tilage.for", "scon.for",
    "soil.for", "watbal.for", "watbal_hourly.for", "wepp_observe.for",
    "inidat.for", "pmxnsl.inc",
)
TAGS = ("WBH_HK_FCUL", "WBH_HK_RATIO")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def records(path):
    return [tokens for line in path.read_text().splitlines()
            if (tokens := shlex.split(line, comments=True))]


def soil_rows(path):
    rows = records(path)
    require(rows[:3] == [["9002"], ["Any", "comments:"], ["3", "0"]],
            f"Unexpected reviewed soil format: {path}")
    cursor = 3
    ofes = []
    for _ in range(3):
        header, profile = rows[cursor:cursor + 2]
        require(len(header) == 5 and len(profile) == 8,
                f"Unexpected soil headers: {path}")
        count = int(profile[2])
        require(0 < count <= 10, f"Source layer count exceeds reviewed native support: {path}")
        horizons = rows[cursor + 2:cursor + 2 + count]
        require(len(horizons) == count and all(len(row) == 18 for row in horizons),
                f"Unexpected 9002 horizon fields: {path}")
        cursor += count + 2
        require(len(rows[cursor]) == 3, f"Missing restrictive record: {path}")
        cursor += 1
        ofes.append(horizons)
    require(cursor == len(rows), f"Trailing soil records: {path}")
    return ofes


def geometry(horizons):
    depths = [Decimal(row[0]) for row in horizons]
    require(depths == sorted(set(depths)) and depths[0] > 0,
            "Non-increasing source boundaries")
    require(sum(depths) >= 200 and depths[-1] in (400, 1600),
            "Profile outside reviewed depth cases")
    native_depths = depths[:-1] + [min(depths[-1] + 200, Decimal(1800))]
    require(native_depths[-1] % 200 == 0, "Non-grid native bottom")
    bounds = [Decimal(0), Decimal(100)] + [Decimal(v) for v in range(200, int(native_depths[-1]) + 1, 200)]
    layers = []
    for index, (top, bottom) in enumerate(zip(bounds, bounds[1:]), 1):
        # tilage duplicates the full first-200-mm property average into both
        # 100-mm tillage layers; do not assign each half its original horizons.
        average_top, average_bottom = (Decimal(0), Decimal(200)) if index <= 2 else (top, bottom)
        support = []
        previous = Decimal(0)
        for horizon, native_bottom in enumerate(native_depths, 1):
            overlap = max(Decimal(0), min(native_bottom, average_bottom) - max(previous, average_top))
            if overlap:
                support.append({
                    "source_horizon": horizon,
                    "source_interval_mm": [int(previous), int(depths[horizon - 1])],
                    "native_interval_mm": [int(previous), int(native_bottom)],
                    "overlap_mm": str(overlap),
                    "property_weight": str(overlap / (average_bottom - average_top)),
                })
            previous = native_bottom
        require(sum(Decimal(item["overlap_mm"]) for item in support) == average_bottom - average_top,
                "Incomplete source support")
        layers.append({
            "s": index, "depth_bounds_mm": [int(top), int(bottom)],
            "property_average_interval_mm": [int(average_top), int(average_bottom)],
            "native_extension_overlap_mm": int(max(Decimal(0), bottom - max(top, depths[-1]))),
            "source_support": support,
        })
    require(len(layers) <= 10, "Internal layer count exceeds mxnsl=10")
    return layers


def build_mapping(preparation_root, native_root):
    declaration_path = preparation_root / "declaration.json"
    readback_path = preparation_root / "case-readback.json"
    result_path = preparation_root / "preparation-result.json"
    require(sha(declaration_path) == PREP_DECLARATION, "Different preparation declaration")
    declaration = json.loads(declaration_path.read_text())
    readback = json.loads(readback_path.read_text())
    result = json.loads(result_path.read_text())
    require(result["passed"] is True and result["native_calls"] == 0, "Preparation did not pass without native calls")
    require(result["declaration_sha256"] == sha(declaration_path)
            and result["case_readback_sha256"] == sha(readback_path), "Unbound preparation readback")
    source_hashes = {}
    for name in SOURCE_FILES:
        path = native_root / "src" / name
        selected = subprocess.check_output(["git", "-C", str(native_root), "show", f"{SOURCE_COMMIT}:src/{name}"])
        require(path.read_bytes() == selected, f"Selected source drift: {name}")
        source_hashes[str(path)] = sha(path)
    cases = {}
    for case_id in ("B2", "B3", "B4", "B5"):
        case = declaration["cases"][case_id]
        require(case["role_order"] == ["road", "fill", "buffer"], "Different OFE role order")
        seed_runs = Path(case["source_seed_folder"]) / "runs"
        seed_hashes = {}
        for name in ("p1.man", "p1.slp", "p1.run", "wepp_ui.txt"):
            path = seed_runs / name
            require(sha(path) == case["exact_inputs"][name], f"Seed input drift: {path}")
            seed_hashes[str(path)] = sha(path)
        require(sha(seed_runs / "p1.man") == MANAGEMENT, "Management differs from reviewed management")
        require(records(seed_runs / "p1.man")[:3] == [["97.3"], ["3"], ["200"]], "Unexpected management size")
        require(records(seed_runs / "p1.slp")[1] == ["3"], "Unexpected slope OFE count")
        arm_rows, soil_hashes = {}, {}
        for arm in ("default", "optional"):
            path = preparation_root / arm / case_id / "runs" / "p1.sol"
            require(sha(path) == readback["artifacts"][arm][case_id]["files"][str(path)], "Prepared soil drift")
            soil_hashes[arm] = {"path": str(path), "sha256": sha(path)}
            arm_rows[arm] = soil_rows(path)
        ofes, keys = [], []
        for ofe, (role, normal, optional) in enumerate(zip(case["role_order"], arm_rows["default"], arm_rows["optional"]), 1):
            require(len(normal) == len(optional), "Policy changed horizon count")
            changed = []
            for horizon, (left, right) in enumerate(zip(normal, optional), 1):
                differences = [i for i, (a, b) in enumerate(zip(left, right)) if Decimal(a) != Decimal(b)]
                require(set(differences) <= {4, 5}, "Policy changed fields outside FC/WP")
                if differences:
                    changed.append({"source_horizon": horizon, "default_fc_wp_tokens": left[4:6],
                                    "optional_fc_wp_tokens": right[4:6]})
            layers = geometry(normal)
            require(layers == geometry(optional), "Policy changed initialization geometry")
            changed_indices = {row["source_horizon"] for row in changed}
            for layer in layers:
                layer["has_changed_fc_wp_input_support"] = any(
                    row["source_horizon"] in changed_indices for row in layer["source_support"])
                keys.extend({"tag": tag, "e": ofe, "c": 0, "s": layer["s"]} for tag in TAGS)
            ofes.append({"e": ofe, "role": role, "layers": layers, "changed_source_horizons": changed})
        cases[case_id] = {"seed_inputs": seed_hashes, "soil_inputs": soil_hashes, "ofes": ofes,
                          "expected_initialization_keys_per_observed_arm": keys,
                          "expected_selected_trace_rows_per_observed_arm": len(keys)}
    return {"schema": "roads-retention-initial-layer-map-v1", "native_calls": 0,
            "native_source_commit": SOURCE_COMMIT, "native_source_sha256": source_hashes,
            "helper_sha256": sha(Path(__file__)),
            "preparation_bindings": {str(path): sha(path) for path in (declaration_path, readback_path, result_path)},
            "depth_status": "source-derived initialization coordinates; observer does not emit DG/depth",
            "coefficient_status": "no native numeric prediction; scon corrections and trace rounding remain in effect",
            "cases": cases,
            "expected_selected_trace_rows_all_eight_observed_arms": sum(2 * case["expected_selected_trace_rows_per_observed_arm"] for case in cases.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparation-root", type=Path, required=True)
    parser.add_argument("--native-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mapping = build_mapping(args.preparation_root, args.native_root)
    with args.output.open("x") as stream:
        json.dump(mapping, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "sha256": sha(args.output),
                      "selected_trace_rows_all_eight": mapping["expected_selected_trace_rows_all_eight_observed_arms"]}))


if __name__ == "__main__":
    main()
