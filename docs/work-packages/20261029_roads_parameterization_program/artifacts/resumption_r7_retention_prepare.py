"""Declare and prepare four paired Roads inputs; never fetch or invoke WEPP."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import sys

REPO = Path("/workdir/wepppy")
ART = REPO / "docs/work-packages/20261029_roads_parameterization_program/artifacts"
BASE = Path("/wc1/runs/ro/roads-parameterization-program-20261103")
SEEDS = BASE / "engine-seeds-v3/declaration.json"
PROTOCOL = ART / "resumption-r7-retention-preparation-protocol.md"
KEYS = {1718465, 1718494, 1718510, 1856573, 2711184, 2711250, 53949}
WITHHELD = {1718472, 53975, 1718476, 665770, 2711196, 658566}
CASES = {
    "B2": ("small_gravel_less_runon", "flagstaff", "1718494"),
    "B3": ("small_gravel_dry_legacy", "denver", "1718494"),
    "B4": ("passing_same_signature", "site", "1718465"),
    "B5": ("underprediction_less_supply", "site", "2711184"),
}
INPUTS = {
    "p1.slp", "p1.man", "p1.cli", "p1.sol", "p1.run", "pmetpara.txt",
    "gwcoeff.txt", "chntyp.txt", "tc.txt", "snow.txt", "wepp_ui.txt", "chan.inp",
}
DEFAULTS = dict(sandtotal_r=66.8, claytotal_r=7.0, om_r=7.0,
                cec7_r=11.3, sandvf_r=10.0, smr=55.5)
R7 = "4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def copy_exclusive(source, target, digest):
    data = Path(source).read_bytes()
    require(hashlib.sha256(data).hexdigest() == digest, f"Copy source drift: {source}")
    with Path(target).open("xb") as stream:
        stream.write(data)


def inventory(root):
    result = {}
    for path in sorted(Path(root).rglob("*")):
        require(not path.is_symlink(), f"Symlink is outside admission: {path}")
        if path.is_file():
            result[str(path.resolve())] = sha(path)
    return result


def verify(bindings):
    for name, digest in bindings.items():
        require(Path(name).is_file() and not Path(name).is_symlink()
                and sha(name) == digest, f"Bound file drift: {name}")


def apis():
    # Ordinary installed imports only: no import finders, worker overlays or hooks.
    import rosetta
    from wepppy.soils.ssurgo import ssurgo, retention
    from wepppy.nodb.mods.disturbed import disturbed
    from wepppy.nodb.core import wepp
    from wepppy.wepp.soils.utils import WeppSoilUtil, SoilMultipleOfeSynth
    return ssurgo, retention, disturbed, wepp, WeppSoilUtil, SoilMultipleOfeSynth, rosetta


def dependencies(api):
    files = {Path(__file__).resolve(), PROTOCOL, ART.parent / "acceptance.md",
             ART.parent / "autonomy.md",
             ART / "resumption-r7-retention-role-api-review.md",
             REPO / "docs/adrs/ADR-0132-optional-ssurgo-retention-builder.md",
             REPO / "docs/schemas/whole-soil-water-capacity-contract.md"}
    for directory in (REPO / "wepppy/soils/ssurgo", REPO / "wepppy/wepp/soils"):
        files.update(directory.rglob("*.py"))
    # Bind the actual imported implementation, including compiled numeric modules.
    for module in tuple(sys.modules.values()):
        name = getattr(module, "__name__", "")
        filename = getattr(module, "__file__", None)
        if filename and name.split(".")[0] in {
            "wepppy", "rosetta", "numpy", "scipy", "duckdb", "_duckdb", "pyarrow", "wepppyo3"
        }:
            path = Path(filename).resolve()
            if path.is_file() and path.suffix != ".pyc":
                files.add(path)
    # Include lazy numeric imports and their shipped shared libraries before any build.
    for package in ("numpy", "scipy", "duckdb", "pyarrow", "wepppyo3"):
        spec = importlib.util.find_spec(package)
        require(spec is not None and spec.origin is not None, f"Missing dependency: {package}")
        package_root = Path(spec.origin).resolve().parent
        for directory in (package_root, package_root.parent / f"{package}.libs"):
            if directory.is_dir():
                files.update(p for p in directory.rglob("*")
                             if p.is_file() and not {"tests", "__pycache__"} & set(p.parts)
                             and (p.suffix == ".py" or ".so" in p.name))
    rosetta_root = Path(api[-1].__file__).resolve().parent
    files.update(rosetta_root.glob("*.py"))
    for directory in ("db", "sqlite"):
        files.update(p for p in (rosetta_root / directory).rglob("*")
                     if p.is_file() and p.suffix in {".parquet", ".duckdb", ".sqlite"})
    return {str(p.resolve()): sha(p) for p in sorted(files)}


def environment():
    return dict(uid=os.getuid(), gid=os.getgid(), python=sys.version,
                executable=str(Path(sys.executable).resolve()),
                executable_sha256=sha(sys.executable))


def cohort_binding(root):
    root = Path(root).resolve()
    require(root.parent == BASE and re.fullmatch(r"retention-source-v[1-9][0-9]*", root.name),
            "Unexpected source cohort root")
    receipt_path = root / "acquisition.json"
    receipt = read(receipt_path)
    require(receipt.get("schema") == "roads-retention-acquisition-v1"
            and receipt.get("passed") is True and receipt.get("source_association_valid") is True,
            "Source acquisition/association gate did not pass")
    for field in ("requested_mukeys", "represented_mukeys"):
        values = list(map(int, receipt[field]))
        require(len(values) == len(KEYS) and set(values) == KEYS, f"Wrong {field}")
    require(not KEYS & WITHHELD and receipt["source_builds"] == receipt["native_calls"] == 0,
            "Source cohort scope changed")
    cache = root / "collection.sqlite"
    require(not any(Path(str(cache) + suffix).exists() for suffix in ("-wal", "-shm")),
            "Source cache is not finalized")
    require(sha(cache) == receipt["cache_sha256"], "Source cache identity mismatch")
    require(sha(root / "cache-association.json") == receipt["association_sha256"],
            "Association identity mismatch")
    require(sha(root / "declaration.json") == receipt["declaration_sha256"],
            "Acquisition declaration identity mismatch")
    association = read(root / "cache-association.json")
    require(association.get("passed") is True
            and association["cache"] == dict(path="collection.sqlite", sha256=sha(cache),
                                             integrity="ok", journal_mode="delete"),
            "Source cache association did not pass")
    require(set(map(int, association["represented_mukeys"])) == KEYS
            and set(association["tables"]) == {
                "component", "chorizon", "chfrags", "chtexturegrp", "corestrictions"},
            "Source association table/material scope changed")
    files = inventory(root)
    relative_files = {str(Path(name).relative_to(root)): digest for name, digest in files.items()
                      if Path(name) != receipt_path}
    require(relative_files == receipt["artifacts"], "Acquisition artifact inventory changed")
    return dict(root=str(root), receipt=str(receipt_path), receipt_sha256=sha(receipt_path),
                cache=str(cache), cache_sha256=sha(cache), files=files)


def semantic(path, parser):
    obj = deepcopy(parser(str(path), preserve_input_format=True).obj)
    obj.pop("header")
    if obj["datver"] == 9002:
        expected = {"theta_r", "theta_s", "alpha", "npar", "ks", "wp", "fc"}
        require(all(set(h.get("native_hydraulics", {})) == expected
                    for ofe in obj["ofes"] for h in ofe["horizons"]),
                f"Incomplete native hydraulic trailer: {path}")
    return obj


def differences(left, right, path=()):
    if isinstance(left, dict) and isinstance(right, dict):
        result = []
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                result.append(dict(path=list(path + (key,)),
                                   before=left.get(key), after=right.get(key)))
            else:
                result.extend(differences(left[key], right[key], path + (key,)))
        return result
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return [dict(path=list(path), before=left, after=right)]
        return [row for index, (a, b) in enumerate(zip(left, right, strict=True))
                for row in differences(a, b, path + (index,))]
    return [] if left == right else [dict(path=list(path), before=left, after=right)]


def retention_difference(row):
    path = row["path"]
    return (len(path) == 5 and path[0] == "ofes" and path[2] == "horizons"
            and path[4] in {"fc", "wp"})


def pair_readback(default, optional, parser):
    rows = differences(semantic(default, parser), semantic(optional, parser))
    require(all(retention_difference(row) for row in rows),
            f"Non-retention paired difference: {default}")
    return rows


def case_bindings(api):
    _, _, disturbed, _, parser, _, _ = api
    lookup_path = Path(disturbed.__file__).parent / "data/disturbed_land_soil_lookup.csv"
    lookup = disturbed.read_disturbed_land_soil_lookup(str(lookup_path))
    declared = read(SEEDS)
    result = {}
    for label, (stratum, climate, material) in CASES.items():
        matches = [r for r in declared["tasks"]
                   if r["stratum"] == stratum and r["lane"] == "modern" and r["version"] == "r7"]
        require(len(matches) == 1, f"Ambiguous seed case: {label}")
        row = matches[0]
        expected = dict(climate=climate, soil=material, design="outunrut", surface="gravel",
                        traffic="high", variant="erosion_road_cap", runtime="project")
        require(row["case"] == expected and set(row["inputs"]) == INPUTS, f"Seed scope: {label}")
        require(set(row["auxiliary_inputs"]) == {"reference.sol"}, "Unexpected auxiliary input")
        runs = Path(row["folder"]) / "runs"
        files = {str(runs / name): digest for name, digest in row["inputs"].items()}
        files.update({str(runs / name): digest for name, digest in row["auxiliary_inputs"].items()})
        legacy = Path(row["reference_record"]).parent / "runs/p1.sol"
        files[str(legacy)] = sha(legacy)
        verify(files)
        frozen = parser(str(runs / "p1.sol")).obj
        old = parser(str(legacy)).obj
        require(len(frozen["ofes"]) == len(old["ofes"]) == 3, "Unexpected OFE count")
        require([o["luse"] for o in frozen["ofes"]] == ["bare", "bare", "forest"],
                "Frozen role order changed")
        texture = frozen["ofes"][1]["stext"]
        bare, forest = dict(lookup[(texture, "bare")]), dict(lookup[(texture, "forest")])
        require(bare["bd"] in ("", None) and forest["bd"] in ("", None), "Density override")
        road = dict(bare, avke=str(min(float(bare["avke"]), float(old["ofes"][0]["avke"]))),
                    ksatadj="0")
        road.update({key: old["ofes"][0][key] for key in ("ki", "kr", "shcrit")})
        replacements = dict(road=road, fill=bare, buffer=forest)
        for actual, repl in zip(frozen["ofes"], replacements.values(), strict=True):
            for key in ("ki", "kr", "shcrit", "ksatfac", "ksatrec"):
                require(float(actual[key]) == float(repl[key]), f"Frozen role {key} drift")
            for key in ("luse", "stext", "ksatadj"):
                require(str(actual[key]) == str(repl[key]), f"Frozen role {key} drift")
            require(all(h["ksat"] == float(repl["avke"]) for h in actual["horizons"]
                        if h["solthk"] <= 200), "Frozen upper K drift")
        result[label] = dict(case=expected, stratum=stratum, source_seed_folder=row["folder"],
                             frozen_soil=str(runs / "p1.sol"), legacy_soil=str(legacy),
                             exact_inputs=row["inputs"], auxiliary_inputs=row["auxiliary_inputs"],
                             files=files, replacements=replacements, texture=texture,
                             role_order=["road", "fill", "buffer"], ksflag=frozen["ksflag"])
    return result, {str(lookup_path.resolve()): sha(lookup_path), str(SEEDS): sha(SEEDS)}


def declare(args):
    api = apis()
    root = args.root.resolve()
    require(root.parent == BASE and re.fullmatch(r"retention-preparation-v[1-9][0-9]*", root.name),
            "Unexpected preparation root")
    cohort = cohort_binding(args.cohort)
    cases, inputs = case_bindings(api)
    binary = BASE / "engine-seeds-v3/bin/r7"
    require(sha(binary) == R7, "Frozen r7 identity mismatch")
    inputs[str(binary)] = R7
    for case in cases.values():
        inputs.update(case["files"])
    deps = dependencies(api)
    root.mkdir(exist_ok=False)
    declaration = dict(schema="roads-retention-preparation-v1", root=str(root),
                       created_utc=datetime.now(timezone.utc).isoformat(), cohort=cohort,
                       cases=cases, input_files=inputs, dependencies=deps,
                       environment=environment(), requested_mukeys=sorted(KEYS),
                       defaults=DEFAULTS, source_initial_sat=0.75, source_ksflag=0,
                       source_workers=1, native_calls=0, network_requests=0,
                       limits="Preparation only; no native execution or scientific acceptance.")
    save(root / "declaration.json", declaration)
    copy_exclusive(__file__, root / "declared-helper.py", sha(__file__))
    copy_exclusive(PROTOCOL, root / "declared-protocol.md", sha(PROTOCOL))
    print(json.dumps(dict(root=str(root), declaration_sha256=sha(root / "declaration.json"))))


def build_sources(root, declaration, api):
    ss, retention, _, _, parser, _, _ = api
    cache = root / "source-cache.sqlite"
    source = declaration["cohort"]
    copy_exclusive(source["cache"], cache, source["cache_sha256"])
    view = ss.SurgoCollectionWorkerViewFactory(db_path=str(cache)).build(KEYS, "Surgo")
    # This owned worker consumes only the populated in-memory view, never acquisition helpers.
    profiles = {}
    for arm in ("default", "optional"):
        built = {}
        for key in sorted(KEYS):
            returned, soil, valid, _ = ss._build_soil_for_process(
                key, view, 0.75, declaration["defaults"], 0, False, None,
                retention.POLICY if arm == "optional" else None,
                source["receipt_sha256"] if arm == "optional" else None)
            require(returned == key and valid and soil is not None and soil.mukey == key,
                    f"Incomplete source build: {arm}/{key}")
            built[key] = soil
        require(set(built) == KEYS, "Incomplete requested source success set")
        profiles[arm] = built
    joins = []
    with sqlite3.connect(f"file:{cache}?mode=ro&immutable=1", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        for key in sorted(KEYS):
            baseline, candidate = (profiles[arm][key] for arm in ("default", "optional"))
            require(vars(baseline.majorComponent) == vars(candidate.majorComponent)
                    and baseline.horizons_mask == candidate.horizons_mask
                    and baseline.res_lyr_i == candidate.res_lyr_i, "Paired selection drift")
            for before, after, decision in zip(baseline.horizons, candidate.horizons,
                                              candidate.retention_decisions, strict=True):
                row = conn.execute("SELECT * FROM chorizon WHERE chkey=?", (after.chkey,)).fetchone()
                require(row is not None, "Missing original horizon")
                row = dict(row)
                require(before.retention_source == after.retention_source
                        and all(after.retention_source[f] == row.get(f) for f in retention.SOURCE_FIELDS),
                        "Original cache/source association mismatch")
                require(decision["before"] == dict(fc=before.field_cap, wp=before.wilt_pt),
                        "Default branch differs from optional decision before-values")
                joins.append(dict(mukey=key, cokey=candidate.majorComponent.cokey,
                                  chkey=after.chkey, source=after.retention_source,
                                  decision=decision))
    for arm in ("default", "optional"):
        directory = root / "source-builds" / arm
        directory.mkdir(parents=True, exist_ok=False)
        for key, soil in profiles[arm].items():
            soil.write(str(directory), overwrite=False)
    pairs = {}
    for key in sorted(KEYS):
        baseline = root / "source-builds/default" / f"{key}.sol"
        candidate = root / "source-builds/optional" / f"{key}.sol"
        proof = retention.load_source_companion(candidate)
        require(proof is not None and proof["source_receipt_sha256"] == source["receipt_sha256"],
                "Source companion receipt mismatch")
        pairs[str(key)] = pair_readback(baseline, candidate, parser)
    save(root / "source-readback.json", retention._json_safe(dict(joins=joins, paired_differences=pairs)))
    require(sha(cache) == source["cache_sha256"], "Read-only worker cache changed")


def build_cases(root, declaration, api):
    _, retention, disturbed, wepp, parser, stack_type, _ = api
    artifacts = {}
    for arm in ("default", "optional"):
        artifacts[arm] = {}
        for label, case in declaration["cases"].items():
            case_root = root / arm / label
            soils, runs = case_root / "soils", case_root / "runs"
            soils.mkdir(parents=True, exist_ok=False)
            runs.mkdir(exist_ok=False)
            material = case["case"]["soil"]
            source = soils / f"{material}.sol"
            original = root / "source-builds" / arm / source.name
            copy_exclusive(original, source, sha(original))
            if arm == "optional":
                original_companion = Path(str(original) + ".retention.json")
                copy_exclusive(original_companion, Path(str(source) + ".retention.json"),
                               sha(original_companion))
            require(parser(str(source)).simple_texture == case["texture"],
                    f"Fresh source texture changed; review before role preparation: {label}")
            role_paths = []
            for role in case["role_order"]:
                target = soils / f"{label}-{role}.sol"
                task = dict(source_soil_path=str(source), output_path=str(target),
                            disturbed_mukey=f"{material}-{label}-{role}",
                            replacements=case["replacements"][role], sol_ver=9002,
                            h0_max_om=None, recompute_wp_fc_using_rosetta_on_bd_override=False)
                disturbed._build_disturbed_mofe_soil(task)
                role_paths.append(str(target))
            stack = soils / f"{label}-stack.sol"
            stack_type(role_paths).write(str(stack), ksflag=case["ksflag"])
            final = runs / "p1.sol"
            wepp.prep_soil((label, str(stack), str(final), None, None, 0.75,
                            False, 700, False, None))
            proof = retention.load_source_companion(final, provenance_root=case_root)
            require((proof is not None) == (arm == "optional"), "Unexpected policy publication")
            final_rows = parser(str(final)).obj["ofes"]
            source_depth = parser(str(source)).obj["ofes"][0]["horizons"][-1]["solthk"]
            require(all(o["horizons"][-1]["solthk"] == source_depth for o in final_rows),
                    "Full source depth was not preserved")
            require(all(200 in [h["solthk"] for h in o["horizons"]] for o in final_rows),
                    "Missing 200 mm support")
            artifacts[arm][label] = dict(source=str(source), roles=role_paths,
                                        stack=str(stack), final=str(final),
                                        files=inventory(case_root), semantic=semantic(final, parser))
    results = {}
    for label, case in declaration["cases"].items():
        before, after = (artifacts[arm][label] for arm in ("default", "optional"))
        paired = {}
        for name in ("source", "stack", "final"):
            paired[name] = pair_readback(before[name], after[name], parser)
        for role, first, second in zip(case["role_order"], before["roles"], after["roles"], strict=True):
            paired[role] = pair_readback(first, second, parser)
        frozen = semantic(case["frozen_soil"], parser)
        drift = differences(frozen, before["semantic"])
        frozen_depths = [[h["solthk"] for h in o["horizons"]] for o in frozen["ofes"]]
        fresh_depths = [[h["solthk"] for h in o["horizons"]] for o in before["semantic"]["ofes"]]
        results[label] = dict(paired_differences=paired, fresh_default_vs_frozen_u12=drift,
                              source_vintage_or_builder_drift_present=bool(drift),
                              nonretention_drift_count=sum(not retention_difference(r) for r in drift),
                              geometry_matches_frozen=fresh_depths == frozen_depths,
                              frozen_horizon_depths_mm=frozen_depths,
                              fresh_horizon_depths_mm=fresh_depths,
                              full_depth_mm=[o["horizons"][-1]["solthk"]
                                             for o in after["semantic"]["ofes"]])
    save(root / "case-readback.json", dict(artifacts=artifacts, comparisons=results))
    require(all(value["geometry_matches_frozen"] for value in results.values()),
            "Fresh source changed frozen profile geometry; amendment required before native work")
    require(all(results[label]["full_depth_mm"] == [1600, 1600, 1600] for label in ("B2", "B3")),
            "B2/B3 causal geometry must retain exactly 1600 mm in each role")
    require(all(results[label]["paired_differences"]["final"] for label in ("B2", "B3")),
            "Fresh target source produced no final retention contrast; review before native study")
    return results


def prepare(args):
    api = apis()
    root = args.root.resolve()
    declaration_path = root / "declaration.json"
    require(sha(declaration_path) == args.declaration_sha256, "Unreviewed declaration digest")
    declaration = read(declaration_path)
    require(declaration["root"] == str(root) and declaration["environment"] == environment(),
            "Execution root/identity/interpreter changed")
    verify(declaration["dependencies"])
    verify(declaration["input_files"])
    require(cohort_binding(declaration["cohort"]["root"]) == declaration["cohort"], "Cohort changed")
    require(dependencies(api) == declaration["dependencies"], "Imported dependency set changed")
    save(root / "preparation-start.json", dict(declaration_sha256=args.declaration_sha256,
                                             environment=environment(), native_calls=0))
    try:
        # Deliberate experiment boundary: retain failures and re-raise; never retry or clean roots.
        build_sources(root, declaration, api)
        comparisons = build_cases(root, declaration, api)
        verify(declaration["dependencies"])
        verify(declaration["input_files"])
        verify(declaration["cohort"]["files"])
        require(sha(declaration_path) == args.declaration_sha256, "Declaration changed during build")
        save(root / "preparation-result.json", dict(
            passed=True, declaration_sha256=args.declaration_sha256,
            source_readback_sha256=sha(root / "source-readback.json"),
            case_readback_sha256=sha(root / "case-readback.json"),
            requested_source_profiles_per_arm=7, paired_cases=4,
            native_calls=0, network_requests=0,
            fresh_default_drift_cases=[label for label, value in comparisons.items()
                                      if value["source_vintage_or_builder_drift_present"]],
            gate="Paired preparation only; independent review required before any native run.",
            artifact_files=inventory(root)))
    except Exception as exc:
        save(root / "preparation-failure.json", dict(
            passed=False, exception_type=type(exc).__name__, message=str(exc),
            declaration_sha256=args.declaration_sha256, native_calls=0,
            retained_artifacts=inventory(root)))
        raise


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="action", required=True)
    declaration = sub.add_parser("declare")
    declaration.add_argument("--cohort", type=Path, default=BASE / "retention-source-v1")
    declaration.add_argument("--root", type=Path, default=BASE / "retention-preparation-v1")
    execution = sub.add_parser("prepare")
    execution.add_argument("--root", type=Path, default=BASE / "retention-preparation-v1")
    execution.add_argument("--declaration-sha256", required=True)
    args = cli.parse_args()
    (declare if args.action == "declare" else prepare)(args)


if __name__ == "__main__":
    main()
