"""Deterministic manifest-driven trial planning."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from .common import content_hash, sha256_file
from .manifest import StudyManifest
from .mutations import expected_mutation


@dataclass(frozen=True)
class PlannedTrial:
    site: str
    scenario: str
    hillslope_id: int
    family: str
    direction: str
    requested_change: float
    eligibility: str
    exclusion_reason: str | None
    relative_input: str
    input_sha256: str
    parameter: str | None
    source_value: Any
    expected_value: Any
    lines: tuple[int, ...]
    tokens: tuple[int, ...]
    trial_id: str
    evidence_locator: str

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["lines"] = list(self.lines)
        value["tokens"] = list(self.tokens)
        return value


@dataclass(frozen=True)
class TrialPlan:
    schema_version: str
    study_id: str
    plan_id: str
    site: str
    manifest_sha256: str
    input_authorities: tuple[dict[str, str], ...]
    executable: dict[str, str]
    evidence_root: str
    trials: tuple[PlannedTrial, ...]
    totals: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "study_id": self.study_id,
                "plan_id": self.plan_id, "site": self.site,
                "manifest_sha256": self.manifest_sha256,
                "input_authorities": list(self.input_authorities), "executable": self.executable,
                "evidence_root": self.evidence_root, "trials": [trial.as_dict() for trial in self.trials],
                "totals": self.totals}


def _discover(study: StudyManifest) -> dict[str, tuple[int, ...]]:
    populations: dict[str, tuple[int, ...]] = {}
    pattern = re.compile(rf"^{re.escape(study.file_prefix)}(\d+){re.escape(study.run_suffix)}$")
    for scenario in study.scenarios:
        run_root = scenario.authority / study.run_dir
        identifiers = tuple(sorted(int(match.group(1)) for path in run_root.iterdir()
                                   if (match := pattern.fullmatch(path.name))))
        if not identifiers:
            raise ValueError(f"no hillslope run decks discovered for {scenario.name}")
        populations[scenario.name] = identifiers
    distinct = {values for values in populations.values()}
    if len(distinct) != 1 and not study.population_exception:
        raise ValueError(f"scenario hillslope populations differ: {populations}")
    return populations


def _totals(trials: tuple[PlannedTrial, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {"requested": len(trials),
                              "eligible": sum(t.eligibility == "eligible" for t in trials),
                              "excluded": sum(t.eligibility == "excluded" for t in trials),
                              "by_scenario": {}, "by_family": {}, "exclusion_reasons": {}}
    for trial in trials:
        for key, label in (("by_scenario", trial.scenario), ("by_family", trial.family)):
            bucket = result[key].setdefault(label, {"requested": 0, "eligible": 0, "excluded": 0})
            bucket["requested"] += 1
            bucket[trial.eligibility] += 1
        if trial.exclusion_reason:
            result["exclusion_reasons"][trial.exclusion_reason] = result["exclusion_reasons"].get(trial.exclusion_reason, 0) + 1
    return result


def plan_trials(study: StudyManifest) -> TrialPlan:
    populations = _discover(study)
    records: list[PlannedTrial] = []
    for scenario in study.scenarios:
        identifiers = populations[scenario.name]
        if study.selected_hillslopes is not None:
            missing = sorted(set(study.selected_hillslopes) - set(identifiers))
            if missing:
                raise ValueError(f"selected hillslopes absent from {scenario.name}: {missing}")
            identifiers = study.selected_hillslopes
        root = scenario.authority / study.run_dir
        for hillslope_id in identifiers:
            for family in study.mutation_families:
                suffix = ".sol" if family.name == "ksat" else ".man"
                relative = f"{study.file_prefix}{hillslope_id}{suffix}"
                source_path = root / relative
                source_hash = sha256_file(source_path)
                directions = [("minus", family.minus), ("plus", family.plus)]
                expected_by_direction = {direction: expected_mutation(source_path, family.name, direction, change)
                                         for direction, change in directions}
                cover_invalid = family.name == "cover" and any(
                    any(not 0 <= value <= 1 for value in item["expected_value"].values())
                    for item in expected_by_direction.values())
                for direction, change in directions:
                    expected = expected_by_direction[direction]
                    records.append(PlannedTrial(
                        study.site, scenario.name, hillslope_id, family.name, direction, change,
                        "excluded" if cover_invalid else "eligible",
                        "paired_cover_direction_would_clip" if cover_invalid else None,
                        relative, source_hash, expected["parameter"], expected["source_value"],
                        expected["expected_value"], tuple(expected["lines"]), tuple(expected["tokens"]), "", ""))
    authority_records = tuple({"scenario": item.name, "authority": str(item.authority),
                               "input_tree_sha256": item.input_tree_sha256} for item in study.scenarios)
    identity_records = [{key: value for key, value in record.as_dict().items()
                         if key not in {"trial_id", "evidence_locator"}} for record in records]
    plan_id = content_hash({"study_id": study.study_id, "input_authorities": authority_records,
                            "trials": identity_records})
    bound = tuple(replace(record,
                          trial_id=f"{record.site}-{record.scenario}-h{record.hillslope_id}-{record.family}-{record.direction}-{plan_id[:12]}",
                          evidence_locator=f"{plan_id}/{record.scenario}/h{record.hillslope_id}/{record.family}-{record.direction}")
                  for record in records)
    totals = _totals(bound)
    if "projections" in study.raw:
        per_trial = study.raw["projections"]
        totals["projections"] = {
            "method": per_trial["method"],
            "eligible_trials": totals["eligible"],
            "expected_runtime_s": totals["eligible"] * float(per_trial["runtime_s_per_eligible_trial"]),
            "expected_retained_bytes": round(totals["eligible"] * float(per_trial["retained_bytes_per_eligible_trial"])),
            "external_evidence_locator": str(study.evidence_root / plan_id),
        }
    return TrialPlan("1.0.0", study.study_id, plan_id, study.site,
                     content_hash(study.raw), authority_records,
                     {"path": str(study.executable), "sha256": study.executable_sha256},
                     str(study.evidence_root), bound, totals)


def trial_plan_from_dict(raw: dict[str, Any]) -> TrialPlan:
    trials = tuple(PlannedTrial(**{**item, "lines": tuple(item["lines"]), "tokens": tuple(item["tokens"])})
                   for item in raw["trials"])
    return TrialPlan(raw["schema_version"], raw["study_id"], raw["plan_id"], raw["site"],
                     raw["manifest_sha256"], tuple(raw["input_authorities"]), raw["executable"],
                     raw["evidence_root"], trials, raw["totals"])
