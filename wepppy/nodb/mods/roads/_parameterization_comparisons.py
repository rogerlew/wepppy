"""Derived, source-verified Roads parameterization comparisons (not saved intent)."""
from __future__ import annotations

from wepppy.observability.safe_traceback import safe_text
from wepppy.observability.safe_logging import current_profile
from wepppy.observability.secret_profiles import WORKER

import hashlib
import json
import math
import os
import re
from pathlib import Path
import shlex
from uuid import uuid4

import pyarrow.parquet as pq

__all__ = ["write_comparison_snapshot", "query_comparisons"]

SNAPSHOT = Path("wepp/roads/output/roads.parameterization.comparison.json")
SUMMARY = Path("wepp/roads/output/interchange/roads_segment_loss_summary.parquet")
MANIFEST = Path("wepp/roads/segments/roads.segment.pass.manifest.json")
PASS = Path("wepp/roads/output/interchange/H.pass.parquet")
HISTORY = Path("wepp/roads/history")
RECEIPT = Path("wepp/roads/output/roads.current.json")
SCOPE = "modeled_profile_pass_event_exports_v1"
PARAMETERS = ("ksat_mm_h", "ki_kg_s_m4", "kr_s_m", "critical_shear_pa")
ROLES = ("road", "fill", "buffer")
# Native main.for/infile.for consume these controls in the hillslope process.
SIDECARS = ("wepp_ui.txt", "pmetpara.txt", "snow.txt", "gwcoeff.txt")


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _object_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def _source(root: Path, relative: str | Path) -> Path:
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Comparison source path escapes project")
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Comparison source alias escapes project")
    return path


def _number(value, name: str, *, positive=False) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"Invalid comparison {name}")
    result = float(value)
    if not math.isfinite(result) or (result <= 0 if positive else result < 0):
        raise ValueError(f"Invalid comparison {name}")
    return result


def _metrics(root: Path) -> tuple[dict, list[dict]]:
    records = pq.read_table(_source(root, SUMMARY)).to_pylist()
    if not records:
        raise ValueError("No executed Roads profiles available for comparison")
    ids, years, profiles = set(), set(), []
    for row in records:
        profile = row.get("segment_run_id")
        if type(profile) is not int or profile <= 0 or profile in ids:
            raise ValueError("Duplicate or invalid comparison profile")
        ids.add(profile)
        count = row.get("simulation_years")
        if type(count) is not int or count <= 0:
            raise ValueError("Invalid comparison simulation years")
        years.add(count)
        if row.get("summary_policy") != "roads_segment_pass_v1":
            raise ValueError("Unsupported comparison summary policy")
        profiles.append({"id": profile, "scope": row.get("profile_scope"),
                         "area_m2": _number(row.get("modeled_area_m2"), "area", positive=True),
                         "runoff_m3_yr": _number(row.get("runoff_volume_m3"), "runoff"),
                         "sediment_kg_yr": _number(row.get("sediment_yield_kg"), "sediment")})
        if profiles[-1]["scope"] not in {"road", "mixed_profile", "replacement_remainder"}:
            raise ValueError("Unsupported comparison profile scope")
    if len(years) != 1:
        raise ValueError("Unequal comparison simulation periods")
    area = math.fsum(row["area_m2"] for row in profiles)
    runoff = math.fsum(row["runoff_m3_yr"] for row in profiles)
    sediment = math.fsum(row["sediment_kg_yr"] for row in profiles)
    metrics = {"modeled_area_m2": area, "annual_runoff_m3": runoff,
               "annual_sediment_kg": sediment, "annual_runoff_mm": runoff / area * 1000,
               "annual_sediment_kg_m2": sediment / area, "simulation_years": years.pop()}
    for name, value in metrics.items():
        _number(value, name)
    return metrics, sorted(profiles, key=lambda row: row["id"])


def _nonparameter_soil_hash(path: Path) -> str:
    # Native input headers are explicitly quoted; horizon records are numeric.
    # Compare everything except the four contractually adjustable header values.
    rows = []
    for line in path.read_text().splitlines():
        if line.lstrip().startswith(("'", '"')):
            fields = shlex.split(line)
            if len(fields) != 9:
                raise ValueError("Unsupported soil header in comparison")
            fields[5:9] = ["<parameter>"] * 4
            rows.append(fields)
        else:
            rows.append(line)
    return _object_hash(rows)


def _engine_identity(wepp_bin) -> dict:
    from wepp_runner.wepp_runner import get_linux_wepp_bin_role_paths
    watershed, hillslope = get_linux_wepp_bin_role_paths(wepp_bin)
    return {"watershed_sha256": _digest(Path(watershed)), "hillslope_sha256": _digest(Path(hillslope))}


def _default(overrides: dict) -> bool:
    if not isinstance(overrides, dict) or set(overrides) != set(ROLES):
        raise ValueError("Comparison lacks complete override snapshot")
    modes = []
    for role in ROLES:
        if not isinstance(overrides[role], dict) or set(overrides[role]) != set(PARAMETERS):
            raise ValueError("Comparison lacks complete override snapshot")
        for entry in overrides[role].values():
            if not isinstance(entry, dict) or entry.get("mode") not in {"default", "multiply", "absolute"}:
                raise ValueError("Invalid comparison override mode")
            if entry["mode"] == "default":
                if set(entry) != {"mode"}:
                    raise ValueError("Invalid default comparison override")
            else:
                if set(entry) != {"mode", "value"}:
                    raise ValueError("Invalid comparison override value")
                _number(entry["value"], "override value", positive=True)
            modes.append(entry["mode"])
    return all(mode == "default" for mode in modes)


def _input_signature(root: Path, profiles: list[dict]) -> tuple[list[dict], dict]:
    sources, signatures = {}, []
    for profile in profiles:
        identifier = profile["id"]
        signature = {"scope": profile["scope"], "area_m2": profile["area_m2"]}
        for suffix in ("cli", "slp", "man", "sol"):
            relative = f"wepp/roads/runs/p{identifier}.{suffix}"
            path = _source(root, relative)
            sources[relative] = _digest(path)
            signature[suffix] = _nonparameter_soil_hash(path) if suffix == "sol" else sources[relative]
        relative = f"wepp/roads/runs/p{identifier}.run"
        run_path = _source(root, relative)
        sources[relative] = _digest(run_path)
        signature["run"] = _object_hash(re.sub(
            rf"(?<![A-Za-z0-9])[pH]{identifier}(?=\.|/|\s|$)", "<profile>", run_path.read_text()))
        signatures.append(signature)
    # IDs are preparation-local; compatibility is a multiset of actual inputs.
    return sorted(signatures, key=lambda row: json.dumps(row, sort_keys=True)), sources


def _sidecar_signature(root: Path) -> tuple[dict, dict]:
    signature, sources = {}, {}
    for name in SIDECARS:
        relative = f"wepp/roads/runs/{name}"
        path = _source(root, relative)
        signature[name] = _digest(path) if path.is_file() else None
        if signature[name] is not None:
            sources[relative] = signature[name]
    return signature, sources


def write_comparison_snapshot(wd, *, parameterization: dict, configuration_hash: str,
                              completed_at: int, wepp_bin=None) -> dict:
    """Record actual regenerated continuous-run reports before result publication."""
    root = Path(wd).resolve()
    destination = _source(root, SNAPSHOT)
    if destination.resolve() != root / SNAPSHOT:
        raise ValueError("Comparison output must not alias another project artifact")
    snapshot = {"schema_version": 1, "scope": SCOPE, "run_id": uuid4().hex,
                "completed_at": completed_at, "configuration_hash": configuration_hash,
                "baseline_id": parameterization["baseline"]["id"],
                "overrides": parameterization["overrides"]}
    snapshot["is_default"] = _default(snapshot["overrides"])
    # Scalar comparison can be unavailable for single storms, but the published
    # snapshot still binds emitted per-profile provenance in the manifest.
    snapshot["sources"] = {str(MANIFEST): _digest(_source(root, MANIFEST))}
    if not _source(root, SUMMARY).is_file():
        snapshot.update(status="unavailable", reason="Continuous-run profile summary unavailable; no comparison generated.")
    else:
        metrics, profiles = _metrics(root)
        manifest = json.loads(_source(root, MANIFEST).read_text())
        if not isinstance(manifest, list):
            raise ValueError("Invalid Roads comparison manifest")
        completed = [row for row in manifest if row.get("status", "completed") == "completed"]
        if len(completed) != len(profiles) or {row.get("segment_run_id") for row in completed} != {row["id"] for row in profiles}:
            raise ValueError("Comparison summary does not match executed profile set")
        if any(row.get("parameterization", {}).get("configuration_hash") != configuration_hash for row in completed):
            raise ValueError("Comparison profiles do not match saved parameterization")
        calendar = pq.read_table(_source(root, PASS), columns=["year", "wepp_id"],
                                 filters=[("wepp_id", "in", [row["id"] for row in profiles])])
        years = sorted(set(calendar.column("year").to_pylist()))
        if not years or len(years) != metrics["simulation_years"] or years != list(range(years[0], years[-1] + 1)):
            raise ValueError("Comparison calendar does not match profile summary")
        signatures, sources = _input_signature(root, profiles)
        sidecars, sidecar_sources = _sidecar_signature(root)
        sources.update(sidecar_sources)
        sources.update({str(relative): _digest(_source(root, relative)) for relative in (SUMMARY, MANIFEST, PASS)})
        compatibility = {"scope": SCOPE, "baseline_id": snapshot["baseline_id"],
                         "engine": _engine_identity(wepp_bin), "years": years, "profiles": signatures,
                         "hillslope_runtime_controls": sidecars}
        snapshot.update(status="completed", metrics=metrics, calendar_years=years,
                        compatibility=compatibility, compatibility_hash=_object_hash(compatibility),
                        sources=sources, profile_count=len(profiles))
    destination.parent.mkdir(parents=True, exist_ok=True)
    candidate = destination.with_name(f"{destination.name}.pending-{uuid4().hex}")
    try:
        with candidate.open("x") as stream:
            json.dump(snapshot, stream, sort_keys=True, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(candidate, destination)
    finally:
        candidate.unlink(missing_ok=True)
    return snapshot


def _read_snapshot(root: Path, project: Path) -> dict:
    path = _source(root, SNAPSHOT)
    snapshot = json.loads(path.read_text())
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1 or snapshot.get("scope") != SCOPE:
        raise ValueError("Unsupported comparison snapshot")
    if snapshot.get("status") != "completed":
        raise ValueError(str(snapshot.get("reason") or "Comparison did not complete"))
    if (not isinstance(snapshot.get("run_id"), str) or not snapshot["run_id"]
            or type(snapshot.get("completed_at")) is not int or snapshot["completed_at"] <= 0
            or type(snapshot.get("is_default")) is not bool):
        raise ValueError("Invalid comparison run identity")
    receipt = json.loads(_source(root, RECEIPT).read_text())
    if (not isinstance(receipt, dict) or receipt.get("policy") != "roads_current_v1"
            or receipt.get("parameterization_hash") != snapshot.get("configuration_hash")
            or receipt.get("parameterization_snapshot_sha256") != _digest(path)
            or str(SNAPSHOT) not in receipt.get("required_relpaths", [])):
        raise ValueError("Comparison run has no matching completed publication receipt")
    from wepppy.wepp.interchange import _roads_lifecycle as lifecycle
    required = receipt.get("required_relpaths")
    if (type(receipt.get("is_single_storm")) is not bool or receipt["is_single_storm"]
            or not isinstance(required, list)
            or not lifecycle.mandatory_paths(False).issubset(required)):
        raise ValueError("Comparison publication receipt is incomplete")
    for relative in required:
        if not isinstance(relative, str) or not _source(root, relative).is_file():
            raise ValueError("Comparison publication resource is missing")
    if root == project:
        lifecycle.require_current(root)
    if _default(snapshot["overrides"]) != snapshot.get("is_default"):
        raise ValueError("Comparison override classification changed")
    sources = snapshot.get("sources")
    if not isinstance(sources, dict) or not all(str(p) in sources for p in (SUMMARY, MANIFEST, PASS)):
        raise ValueError("Comparison source bindings missing")
    for relative, digest in sources.items():
        if not isinstance(relative, str) or _digest(_source(root, relative)) != digest:
            raise ValueError("Comparison source bytes changed")
    metrics, profiles = _metrics(root)
    signatures, required = _input_signature(root, profiles)
    if not set(required).issubset(sources) or metrics != snapshot.get("metrics"):
        raise ValueError("Comparison metrics or input bindings changed")
    sidecars, required_sidecars = _sidecar_signature(root)
    if not set(required_sidecars).issubset(sources):
        raise ValueError("Comparison runtime control bindings missing")
    calendar = pq.read_table(_source(root, PASS), columns=["year", "wepp_id"],
                             filters=[("wepp_id", "in", [row["id"] for row in profiles])])
    years = sorted(set(calendar.column("year").to_pylist()))
    if snapshot.get("calendar_years") != years or snapshot.get("profile_count") != len(profiles):
        raise ValueError("Comparison calendar or profile count changed")
    compatibility = snapshot.get("compatibility")
    if (not isinstance(compatibility, dict) or compatibility.get("profiles") != signatures
            or compatibility.get("hillslope_runtime_controls") != sidecars
            or compatibility.get("years") != years or compatibility.get("scope") != SCOPE
            or compatibility.get("baseline_id") != snapshot.get("baseline_id")
            or _object_hash(compatibility) != snapshot.get("compatibility_hash")):
        raise ValueError("Comparison compatibility binding changed")
    return {key: snapshot[key] for key in ("run_id", "completed_at", "configuration_hash", "baseline_id",
            "overrides", "is_default", "metrics", "calendar_years", "profile_count", "compatibility_hash")} | {
                "snapshot_relpath": str(path.relative_to(project)), "historical": root != project}


def query_comparisons(wd) -> dict:
    """Read actual retained pairs; never label historical values as edited results."""
    from wepppy.wepp.interchange._roads_lifecycle import RoadsResultsUnavailable
    root = Path(wd).resolve()
    candidates = [root]
    try:
        history = _source(root, HISTORY)
    except ValueError as exc:
        return {"status": "unavailable", "scope": SCOPE, "reason": safe_text(str(exc), source_profile=current_profile(WORKER)), "runs": [], "diagnostics": []}
    if history.is_dir():
        candidates.extend(path for path in sorted(history.iterdir()) if path.is_dir() and not path.is_symlink())
    runs, diagnostics = [], []
    for candidate in candidates:
        try:
            if not _source(candidate, SNAPSHOT).is_file():
                continue
            runs.append(_read_snapshot(candidate, root))
        except (OSError, ValueError, TypeError, KeyError, OverflowError, RoadsResultsUnavailable) as exc:
            diagnostics.append({"snapshot_relpath": str((candidate / SNAPSHOT).relative_to(root)), "reason": safe_text(str(exc), source_profile=current_profile(WORKER))})
    runs.sort(key=lambda run: (run["completed_at"], run["run_id"]), reverse=True)
    for custom in (run for run in runs if not run["is_default"]):
        baseline = next((run for run in runs if run["is_default"] and
                         run["compatibility_hash"] == custom["compatibility_hash"]), None)
        if baseline is not None:
            differences = {key: custom["metrics"][key] - baseline["metrics"][key]
                           for key in ("annual_runoff_m3", "annual_sediment_kg", "annual_runoff_mm", "annual_sediment_kg_m2")}
            return {"status": "available", "scope": SCOPE, "baseline": baseline, "custom": custom,
                    "difference": differences, "diagnostics": diagnostics}
    reason = ("No compatible retained default/custom runs with matching climate, geometry, management and report scope."
              if runs else "Run a default and custom configuration to generate comparable results.")
    return {"status": "unavailable", "scope": SCOPE, "reason": reason, "runs": runs, "diagnostics": diagnostics}
