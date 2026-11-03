"""Read completed retained traces after all eight ordinary-output parity gates."""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

ART = Path(__file__).resolve().parent
ROOT = Path("/wc1/runs/ro/roads-parameterization-program-20261103/retention-native-v1")
MAP = ART / "resumption-r7-retention-initial-layer-map.json"
MAP_REVIEW = ART / "resumption-r7-retention-initial-layer-review.md"
CONTRACT = ART.parents[2] / "schemas/whole-soil-water-capacity-contract.md"
WINTER = Path("/workdir/wepp-forest-release-20261009/src/winter.for")
WINTER_SHA = "6dca46e762611ddd93e030d7fcc619af92922d614a4ddc1c44576b90ee9d86ff"
DECL_SHA = "631e70e5ddbe6573bd694c18c900b798d621b4c138fd93ed31f591511425e814"
MAP_SHA = "5dcc0c68d3dd4213c1ae1cbc5bf7b18393318f962b2dde80f1d3b6f329c653c7"
MAP_REVIEW_SHA = "05908301a7110aadf5450906ca3880b8d9a7a408927463896088f210220dbebc"
BINARY_SHA = "4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825"
OUTPUTS = {f"H1.{name}.dat" for name in ("loss", "soil", "pass", "plot", "wat", "element", "ebe")}
SELECTED = {"WBH_HK_FCUL", "WBH_HK_RATIO"}
LINE = re.compile(
    r"^\s*(?P<tag>\S+)\s+y=\s*(?P<y>-?\d+)\s+d=\s*(?P<d>-?\d+)"
    r"\s+e=\s*(?P<e>-?\d+)\s+c=\s*(?P<c>-?\d+)\s+s=\s*(?P<s>-?\d+)"
    r"\s+v1=\s*(?P<v1>\S+)\s+v2=\s*(?P<v2>\S+)\s*$"
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def verify(files):
    for name, digest in files.items():
        require(sha(name) == digest, f"Bound input changed: {name}")


def interval(token):
    value = Decimal(token.replace("D", "E").replace("d", "e"))
    require(value.is_finite(), f"Nonfinite required value: {token}")
    half_quantum = Decimal(10) ** value.as_tuple().exponent / 2
    return value, value - half_quantum, value + half_quantum


def preflight():
    require(sha(ROOT / "declaration.json") == DECL_SHA, "Wrong native declaration")
    require(sha(MAP) == MAP_SHA and sha(MAP_REVIEW) == MAP_REVIEW_SHA, "Layer map changed")
    require(sha(WINTER) == WINTER_SHA, "Guard interpretation source changed")
    declaration, results = read(ROOT / "declaration.json"), read(ROOT / "results.json")
    mapping = read(MAP)
    verify(mapping["native_source_sha256"])
    verify(mapping["preparation_bindings"])
    verify(declaration["reference_files"])
    verify(declaration["preparation_files"])
    require(declaration["binary_sha256"] == BINARY_SHA, "Wrong executable")
    require(read(ROOT / "execution-start.json")["declaration_sha256"] == DECL_SHA,
            "Execution-start binding mismatch")
    review = read(ROOT / "execution-review.json")
    require(review["passed"] is True and review["declaration_sha256"] == DECL_SHA,
            "Missing accepted execution review")
    verify(review["files"])
    require(not (ROOT / "failure.json").exists(), "Campaign retained a failure")
    require(len(results) == len(declaration["tasks"]) == 16, "Incomplete campaign")
    tasks = {(t["label"], t["arm"], t["mode"]): t for t in declaration["tasks"]}
    require(len(tasks) == 16, "Duplicate declared tasks")
    rows, files = {}, {}
    for row in results:
        key = row["label"], row["arm"], row["mode"]
        require(key in tasks and key not in rows, "Wrong or duplicate result identity")
        task = tasks[key]
        for field in ("case", "inputs", "auxiliary_inputs", "staged_files", "version"):
            require(row[field] == task[field], f"Result task drift: {key}/{field}")
        folder = Path(row["retained_folder"])
        require(folder == ROOT / "cases" / row["mode"] / row["arm"] / row["label"],
                "Unexpected archival root")
        require(read(folder / "retention-receipt.json") == row, "Archive receipt differs")
        require(row["completed"] and row["returncode"] == 0 and set(row["outputs"]) == OUTPUTS,
                "Native completion/output failure")
        for path in folder.rglob("*"):
            require(not path.is_symlink(), f"Unexpected archival alias: {path}")
        for relative, digest in task["staged_files"].items():
            require(sha(folder / relative) == digest, "Archived staged input changed")
        for name, digest in row["execution_logs"].items():
            require(sha(folder / "runs" / name) == digest, "Execution log changed")
        output_files = {str(folder / "output" / name): digest for name, digest in row["outputs"].items()}
        verify(output_files)
        files.update(output_files)
        files[str(folder / "retention-receipt.json")] = sha(folder / "retention-receipt.json")
        map_case = mapping["cases"][row["label"]]
        source = map_case["soil_inputs"][row["arm"]]
        require(sha(source["path"]) == source["sha256"] == row["inputs"]["p1.sol"],
                "Layer map soil differs from execution")
        verify(map_case["seed_inputs"])
        for source_name, digest in map_case["seed_inputs"].items():
            require(row["inputs"][Path(source_name).name] == digest, "Layer map runtime input drift")
        if row["mode"] == "ordinary":
            require(all(row.get(k) for k in ("physical_pass", "particle_pass", "pass_completeness")),
                    "Ordinary scientific artifact gate failed")
            require(row["binary_sha256"] == BINARY_SHA, "Ordinary executable mismatch")
        else:
            require(row["ordinary_outputs_identical"] and row["working_directory_expected"],
                    "Observer retained gate failed")
        rows[key] = row
    parity = []
    for label in ("B2", "B3", "B4", "B5"):
        for arm in ("default", "optional"):
            normal, observed = (rows[(label, arm, mode)] for mode in ("ordinary", "observed"))
            require(normal["outputs"] == observed["outputs"], "Observer changes ordinary outputs")
            require(normal["staged_files"] == {
                k: v for k, v in observed["staged_files"].items() if k != "runs/wepp_observe.on"
            }, "Observer pair has non-marker input changes")
            marker = Path(observed["retained_folder"]) / "runs/wepp_observe.on"
            require(marker.read_bytes() == b"", "Observer marker is not empty")
            for row in (normal, observed):
                require(not (Path(row["retained_folder"]) / "runs/wepp_observe_frost.on").exists(),
                        "Frost-only filter is outside the design")
            parity.append(dict(label=label, arm=arm, exact_outputs=sorted(OUTPUTS)))
    # No trace is read before all 56 output comparisons and input pair gates pass.
    require(len(parity) == 8 and len(files) == 128, "Incomplete retained parity inventory")
    return declaration, mapping, rows, parity, files


def parse_trace(path, expected_keys):
    tags, dates, keys, guards = Counter(), Counter(), Counter(), {}
    winter_counters = {}
    selected, malformed = [], []
    digest = hashlib.sha256()
    byte_count = line_count = malformed_count = 0
    with Path(path).open("rb") as stream:
        for line_count, raw in enumerate(stream, 1):
            digest.update(raw)
            byte_count += len(raw)
            text = raw.decode("ascii").rstrip("\r\n")
            match = LINE.fullmatch(text)
            if not match:
                malformed_count += 1
                if len(malformed) < 20:
                    malformed.append(dict(line=line_count, raw=text))
                continue
            fields = match.groupdict()
            record = dict(tag=fields["tag"],
                          **{key: int(fields[key]) for key in ("y", "d", "e", "c", "s")},
                          v1=fields["v1"], v2=fields["v2"], line=line_count, raw=text)
            tag = record["tag"]
            tags[tag] += 1
            if tag in SELECTED:
                key = tag, record["e"], record["c"], record["s"]
                keys[key] += 1
                dates[(record["y"], record["d"])] += 1
                selected.append(record)
            if "_G_" in tag or "GUAR" in tag or "BAD" in tag or "WARN" in tag:
                entry = guards.setdefault(tag, dict(count=0, first_records=[], last_record=None))
                entry["count"] += 1
                if len(entry["first_records"]) < 3:
                    entry["first_records"].append(record)
                entry["last_record"] = record
            if tag in ("WFR_SUM_CALL", "WFR_SUM_GUAR", "WFR_SUM_WARN"):
                entry = winter_counters.setdefault(tag, dict(
                    rows=0, nonzero_rows=0, sum_v1=Decimal(0), sum_v2=Decimal(0),
                    max_v1=Decimal(0), max_v2=Decimal(0)))
                v1, _, _ = interval(record["v1"])
                v2, _, _ = interval(record["v2"])
                require(v1 >= 0 and v2 >= 0, "Negative winter counter")
                entry["rows"] += 1
                entry["nonzero_rows"] += int(v1 != 0 or v2 != 0)
                entry["sum_v1"] += v1
                entry["sum_v2"] += v2
                entry["max_v1"] = max(entry["max_v1"], v1)
                entry["max_v2"] = max(entry["max_v2"], v2)
    expected = Counter({(r["tag"], r["e"], r["c"], r["s"]): 1 for r in expected_keys})
    inventory_pass = keys == expected and malformed_count == 0
    inventory_issues = [dict(key=list(key), expected=expected[key], observed=keys[key])
                        for key in sorted(set(keys) | set(expected)) if keys[key] != expected[key]]
    return dict(path=str(path), sha256=digest.hexdigest(), bytes=byte_count, lines=line_count,
                tag_counts=dict(sorted(tags.items())), selected_rows=selected,
                initialization_dates=[dict(y=y, d=d, rows=n) for (y, d), n in sorted(dates.items())],
                inventory_pass=inventory_pass, inventory_issues=inventory_issues,
                malformed_count=malformed_count, malformed_examples=malformed, guards=guards,
                winter_counters={tag: {key: str(value) if isinstance(value, Decimal) else value
                                       for key, value in counts.items()}
                                 for tag, counts in winter_counters.items()})


def layer_values(trace, case_map):
    selected = {(r["tag"], r["e"], r["c"], r["s"]): r for r in trace["selected_rows"]}
    result = []
    for ofe in case_map["ofes"]:
        for layer in ofe["layers"]:
            key = ofe["e"], 0, layer["s"]
            fcrow, rrow = (selected[(tag,) + key] for tag in ("WBH_HK_FCUL", "WBH_HK_RATIO"))
            require((fcrow["y"], fcrow["d"]) == (rrow["y"], rrow["d"]), "Initialization dates disagree")
            fc, flo, fhi = interval(fcrow["v1"])
            ul, ulo, uhi = interval(fcrow["v2"])
            ratio, rlo, rhi = interval(rrow["v1"])
            ratio_v2, _, _ = interval(rrow["v2"])
            require(ratio_v2 == 0, "Unexpected ratio payload second value")
            result.append(dict(
                e=ofe["e"], c=0, s=layer["s"], role=ofe["role"],
                y=fcrow["y"], d=fcrow["d"],
                depth_bounds_mm=layer["depth_bounds_mm"],
                property_average_interval_mm=layer["property_average_interval_mm"],
                native_extension_overlap_mm=layer["native_extension_overlap_mm"],
                has_changed_fc_wp_input_support=layer["has_changed_fc_wp_input_support"],
                tokens=dict(fc_m=fcrow["v1"], ul_m=fcrow["v2"], ratio=rrow["v1"]),
                printed_intervals=dict(fc_m=[str(flo), str(fhi)], ul_m=[str(ulo), str(uhi)],
                                       ratio=[str(rlo), str(rhi)]),
                positive_fc_ul=fc > 0 and ul > 0,
                positive_ratio=ratio > 0,
                ratio_one_within_print_interval=rlo <= 1 <= rhi,
                initialized_arithmetic_domain_pass=fc > 0 and ul > 0 and ratio > 0 and not rlo <= 1 <= rhi,
                strict_ordered_ratio_screen=0 < fc < ul and 0 < ratio < 1,
            ))
    return result


def comparisons(arms, mapping):
    cases = {}
    for label in ("B2", "B3", "B4", "B5"):
        before = arms[f"{label}/default"]["layers"]
        after = arms[f"{label}/optional"]["layers"]
        require(len(before) == len(after), "Different paired layer inventory")
        rows = []
        for a, b in zip(before, after, strict=True):
            for key in ("e", "c", "s", "y", "d", "depth_bounds_mm", "property_average_interval_mm"):
                require(a[key] == b[key], f"Paired initialization identity differs: {label}/{key}")
            fields = {}
            for field in ("fc_m", "ul_m", "ratio"):
                first, alo, ahi = interval(a["tokens"][field])
                second, blo, bhi = interval(b["tokens"][field])
                fields[field] = dict(default_token=a["tokens"][field], optional_token=b["tokens"][field],
                                     changed=first != second, printed_delta=str(second-first),
                                     disjoint_print_intervals=ahi < blo or bhi < alo)
            rows.append(dict(e=a["e"], c=0, s=a["s"], role=a["role"],
                             depth_bounds_mm=a["depth_bounds_mm"],
                             property_average_interval_mm=a["property_average_interval_mm"],
                             native_extension_overlap_mm=a["native_extension_overlap_mm"],
                             has_changed_fc_wp_input_support=a["has_changed_fc_wp_input_support"],
                             changed=any(value["changed"] for value in fields.values()), fields=fields))
        cases[label] = dict(
            layers=rows,
            changed_layers=sum(r["changed"] for r in rows),
            changed_supported_nonextension_layers=sum(
                r["changed"] and r["has_changed_fc_wp_input_support"]
                and r["native_extension_overlap_mm"] == 0 for r in rows),
            changed_native_extension_layers=sum(r["changed"] and r["native_extension_overlap_mm"] > 0
                                                for r in rows),
            unexpected_changed_without_input_support=[r for r in rows if r["changed"]
                                                       and not r["has_changed_fc_wp_input_support"]],
            primary_b2_b3_deeper_witness=[r for r in rows if label in ("B2", "B3") and r["s"] in (7, 8, 9)],
        )
    return cases


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path,
                     default=ART / "resumption-r7-retention-observer-outcome.json")
    args = cli.parse_args()
    require(not args.output.exists(), "Readback output must be fresh")
    metadata = {str(path): sha(path) for path in (
        Path(__file__), ROOT / "results.json", ROOT / "declaration.json", MAP, MAP_REVIEW, CONTRACT, WINTER)}
    declaration, mapping, rows, parity, files = preflight()
    arms = {}
    for label in ("B2", "B3", "B4", "B5"):
        for arm in ("default", "optional"):
            row = rows[(label, arm, "observed")]
            trace_path = Path(row["retained_folder"]) / "runs/wepp_observe.log"
            trace = parse_trace(trace_path, mapping["cases"][label]["expected_initialization_keys_per_observed_arm"])
            require(trace["sha256"] == row["trace"]["sha256"] and trace["bytes"] == row["trace"]["bytes"],
                    "Retained trace identity mismatch")
            require(trace["inventory_pass"], f"Initialization inventory failed: {label}/{arm}")
            require(len(trace["initialization_dates"]) == 1, "Unexplained initialization dates")
            layers = layer_values(trace, mapping["cases"][label])
            arms[f"{label}/{arm}"] = dict(trace=trace, layers=layers)
            files[str(trace_path)] = trace["sha256"]
    selected_count = sum(len(a["trace"]["selected_rows"]) for a in arms.values())
    require(selected_count == mapping["expected_selected_trace_rows_all_eight_observed_arms"] == 408,
            "Wrong total initialization inventory")
    pairs = comparisons(arms, mapping)
    domains_pass = all(layer["initialized_arithmetic_domain_pass"]
                       for arm in arms.values() for layer in arm["layers"])
    strict_screen = all(layer["strict_ordered_ratio_screen"]
                        for arm in arms.values() for layer in arm["layers"])
    verify(metadata)
    verify(files)
    result = dict(
        schema="roads-retention-observer-readback-v1", reviewer="mipa_contract_scope",
        passed=domains_pass, ordinary_artifact_gates_pass=True,
        ordinary_observer_parity_pairs=len(parity), exact_output_comparisons=56,
        actual_native_output_file_count=112, parity=parity,
        selected_rows=selected_count, initialization_pairs=selected_count // 2,
        initialized_arithmetic_domain_pass=domains_pass, strict_ordered_ratio_screen_pass=strict_screen,
        arms=arms, paired_comparisons=pairs, metadata_bindings=metadata, retained_artifact_bindings=files,
        native_calls_by_reader=0, raw_traces_retained=True,
        precision="Original 1pe12.4 tokens: five significant digits. Deltas are differences of printed values, not exact binary32 state. Half-quantum intervals describe printing precision, not fitted acceptance tolerances.",
        guard_policy="Every _G_, GUAR, BAD or WARN tag is counted with raw examples; presence alone is not classified as fatal. WFR_SUM_GUAR is an unconditional daily summary, not itself a failure event. Full tag counters and original traces remain retained.",
        winter_counter_semantics="At winter.for hour24, WFR_SUM_CALL gives frost-condition opportunities and KSFLAG skips; WFR_SUM_GUAR gives near-zero qoutdm and frost/thaw boundary counts following frostN; WFR_SUM_WARN occurs only when their sum exceeds50. Daily counters reset before the hourly loop. Zero summaries do not prove exercised frostN domains.",
        domain_scope="Finite positive initialized FC/UL and positive ratio with the log singularity excluded at printed precision. The stricter ordered-ratio screen is reported separately and is not claimed to be native guard enforcement. Dynamic UL-DRFC and frozen/unfrozen consumer coverage are not established here.",
        limits="Depths come from the bound source map, not trace DG. Both top layers use the 0–200 mm property average; native-added bottom support is separate. No observed stored HK, dynamic PERC operand, unique drainage/ET causality, pore-capacity validation or whole-system water closure claim.",
    )
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=domains_pass, selected_rows=selected_count,
                          exact_output_comparisons=56, output=str(args.output),
                          sha256=sha(args.output),
                          changed_layers={k:v["changed_layers"] for k,v in pairs.items()})))


if __name__ == "__main__":
    main()
