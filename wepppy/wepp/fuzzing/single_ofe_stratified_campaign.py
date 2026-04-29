"""Milestone 3 single-OFE stratified fuzzing campaign orchestration."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import shutil
import subprocess
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from wepppy.climates.cligen.cligen import ClimateFile
from wepppy.topo.watershed_abstraction import SlopeFile
from wepppy.wepp.fuzzing.seeded_soil_landuse_generators import (
    DEFAULT_GENERATOR_SEED,
    DEFAULT_MUTATION_PROFILE,
    MUTATION_PROFILES,
    SeedTuple,
    SeededSoilLanduseGenerator,
    discover_seed_tuples,
)
from wepppy.wepp.management.managements import read_management
from wepppy.wepp.soils.utils import WeppSoilUtil

CLIMATE_BINS: tuple[str, str, str] = ("dry", "mesic", "wet")
SLOPE_BINS: tuple[str, str, str] = ("gradual", "moderate", "steep")
REQUIRED_BIN_KEYS: tuple[tuple[str, str], ...] = tuple(
    (climate_bin, slope_bin)
    for climate_bin in CLIMATE_BINS
    for slope_bin in SLOPE_BINS
)
KNOWN_FAIL_CLASSIFICATIONS: set[str] = {
    "TRAP_SIGFPE",
    "TRAP_SIGNAL",
    "RUNTIME_ERROR",
    "UNKNOWN",
}
POSITIVE_CONTROL_CASE_PREFIX = "positive-control::"
ORACLE_TOKEN_PATTERN = re.compile(r"\b(nan|inf|infinity|overflow)\b", re.IGNORECASE)
ORACLE_NONNEGATIVE_HINTS: tuple[str, ...] = (
    "runoff",
    "rain",
    "precip",
    "infil",
    "soil loss",
    "sediment",
    "detachment",
)
NUMBER_PATTERN = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    seed_id: str
    run_id: str
    stem: str
    reason_codes: tuple[str, ...]
    details: tuple[str, ...]
    soil_ofe_count: int | None
    seed_lineage: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PreflightContractMapping:
    obligation_id: str
    contract_ref: str
    channel_class: str
    boundary_disposition: str
    strict_policy_required: bool
    rationale_token: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


PREFLIGHT_CHANNEL_CLASSES: set[str] = {"NUM", "CONF_PARSE", "MIXED"}
PREFLIGHT_BOUNDARY_DISPOSITIONS: set[str] = {
    "invalid_input",
    "inactive_process",
    "valid_extreme",
    "neutral_branch",
    "bounded_transition",
    "model_gap",
    "requires_scientific_review",
}
PREFLIGHT_REASON_CODE_CONTRACT_MAP: dict[str, PreflightContractMapping] = {
    "MISSING_REQUIRED_INPUT": PreflightContractMapping(
        obligation_id="PO-PASS-001",
        contract_ref="SC-PASS-001#INV-PASS-002",
        channel_class="CONF_PARSE",
        boundary_disposition="invalid_input",
        strict_policy_required=False,
        rationale_token="producer_input_path_missing",
    ),
    "MISSING_RUN_FILE": PreflightContractMapping(
        obligation_id="PO-PASS-001",
        contract_ref="SC-PASS-001#INV-PASS-002",
        channel_class="CONF_PARSE",
        boundary_disposition="invalid_input",
        strict_policy_required=False,
        rationale_token="producer_run_context_missing",
    ),
    "SOIL_PARSE_ERROR": PreflightContractMapping(
        obligation_id="PO-SOIL-001",
        contract_ref="SC-SOIL-001#INV-SOIL-001",
        channel_class="CONF_PARSE",
        boundary_disposition="invalid_input",
        strict_policy_required=False,
        rationale_token="soil_parse_boundary",
    ),
    "SOIL_MULTI_OFE": PreflightContractMapping(
        obligation_id="PO-SOIL-001",
        contract_ref="SC-SOIL-001#INV-SOIL-002",
        channel_class="MIXED",
        boundary_disposition="neutral_branch",
        strict_policy_required=False,
        rationale_token="single_ofe_campaign_scope_boundary",
    ),
    "MAN_PARSE_ERROR": PreflightContractMapping(
        obligation_id="PO-WATBAL-001",
        contract_ref="SC-WATBAL-001#INV-WATBAL-002",
        channel_class="CONF_PARSE",
        boundary_disposition="requires_scientific_review",
        strict_policy_required=False,
        rationale_token="management_parse_boundary",
    ),
    "SLP_PARSE_ERROR": PreflightContractMapping(
        obligation_id="PO-PERC-001",
        contract_ref="SC-PERC-001#INV-PERC-001",
        channel_class="CONF_PARSE",
        boundary_disposition="requires_scientific_review",
        strict_policy_required=False,
        rationale_token="slope_parse_boundary",
    ),
    "SLP_MULTI_OFE": PreflightContractMapping(
        obligation_id="PO-PERC-001",
        contract_ref="SC-PERC-001#INV-PERC-002",
        channel_class="MIXED",
        boundary_disposition="model_gap",
        strict_policy_required=False,
        rationale_token="single_ofe_slope_structure_boundary",
    ),
    "CLI_PARSE_ERROR": PreflightContractMapping(
        obligation_id="PO-EVAP-001",
        contract_ref="SC-EVAP-001#INV-EVAP-002",
        channel_class="CONF_PARSE",
        boundary_disposition="requires_scientific_review",
        strict_policy_required=False,
        rationale_token="climate_parse_boundary",
    ),
    "ROSETTA3_UNAVAILABLE": PreflightContractMapping(
        obligation_id="PO-WATBAL-001",
        contract_ref="SC-WATBAL-001#INV-WATBAL-002",
        channel_class="MIXED",
        boundary_disposition="requires_scientific_review",
        strict_policy_required=True,
        rationale_token="producer_dependency_unavailable",
    ),
}
UNMAPPED_REASON_CODE_MAPPING = PreflightContractMapping(
    obligation_id="PO-UNMAPPED-001",
    contract_ref="",
    channel_class="MIXED",
    boundary_disposition="requires_scientific_review",
    strict_policy_required=True,
    rationale_token="unmapped_reason_code",
)


def _validate_preflight_contract_map() -> None:
    for reason_code, mapping in PREFLIGHT_REASON_CODE_CONTRACT_MAP.items():
        if mapping.channel_class not in PREFLIGHT_CHANNEL_CLASSES:
            raise ValueError(
                f"Invalid channel_class={mapping.channel_class!r} for reason_code={reason_code}"
            )
        if mapping.boundary_disposition not in PREFLIGHT_BOUNDARY_DISPOSITIONS:
            raise ValueError(
                "Invalid boundary_disposition="
                f"{mapping.boundary_disposition!r} for reason_code={reason_code}"
            )
    if UNMAPPED_REASON_CODE_MAPPING.channel_class not in PREFLIGHT_CHANNEL_CLASSES:
        raise ValueError("Invalid channel_class in UNMAPPED_REASON_CODE_MAPPING")
    if (
        UNMAPPED_REASON_CODE_MAPPING.boundary_disposition
        not in PREFLIGHT_BOUNDARY_DISPOSITIONS
    ):
        raise ValueError("Invalid boundary_disposition in UNMAPPED_REASON_CODE_MAPPING")


def _build_preflight_producer_obligation_rows(
    quarantined: Sequence[QuarantineRecord],
    *,
    strict_policy: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for quarantined_row in quarantined:
        details = " | ".join(quarantined_row.details)
        for reason_code in quarantined_row.reason_codes:
            mapping = PREFLIGHT_REASON_CODE_CONTRACT_MAP.get(reason_code)
            mapping_status = "mapped"
            if mapping is None:
                if strict_policy:
                    raise ValueError(
                        "Unmapped preflight reason code under strict policy mode: "
                        f"{reason_code}"
                    )
                mapping = UNMAPPED_REASON_CODE_MAPPING
                mapping_status = "unmapped_reason_code"
            rows.append(
                {
                    "seed_id": quarantined_row.seed_id,
                    "run_id": quarantined_row.run_id,
                    "stem": quarantined_row.stem,
                    "reason_code": reason_code,
                    "obligation_id": mapping.obligation_id,
                    "contract_ref": mapping.contract_ref,
                    "channel_class": mapping.channel_class,
                    "boundary_disposition": mapping.boundary_disposition,
                    "strict_policy_required": mapping.strict_policy_required,
                    "mapping_status": mapping_status,
                    "rationale_token": mapping.rationale_token,
                    "details": details,
                }
            )
    return rows


_validate_preflight_contract_map()


def _summarize_preflight_producer_obligation_rows(
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "row_count": len(rows),
        "reason_code_counts": dict(sorted(Counter(row["reason_code"] for row in rows).items())),
        "contract_ref_counts": dict(
            sorted(Counter((row["contract_ref"] or "UNMAPPED") for row in rows).items())
        ),
        "channel_class_counts": dict(
            sorted(Counter(row["channel_class"] for row in rows).items())
        ),
        "disposition_counts": dict(
            sorted(Counter(row["boundary_disposition"] for row in rows).items())
        ),
        "unmapped_reason_code_count": sum(
            1 for row in rows if row["mapping_status"] != "mapped"
        ),
    }


@dataclass(frozen=True, slots=True)
class EligibleRecord:
    seed: SeedTuple
    soil_ofe_count: int
    climate_annual_precip_mm: float
    slope_scalar: float
    climate_bin: str
    slope_bin: str

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["seed"] = self.seed.as_dict()
        return payload


@dataclass(frozen=True, slots=True)
class StratificationThresholds:
    climate_dry_upper: float
    climate_mesic_upper: float
    slope_gradual_upper: float
    slope_moderate_upper: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OversamplingWeights:
    warning_density: float
    non_pass_signature: float
    novel_signature: float
    dry_wet_corner: float
    gradual_steep_corner: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SeedSignal:
    soft_warning_density: float
    non_pass_hits: int
    novel_non_pass_hits: int

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PositiveControlRecord:
    case_id: str
    stderr_path: str
    observe_path: str
    expected_signal_class: str
    expected_top_frame: str
    expected_last_marker_tag: str
    expected_classification: str
    expected_routine_chain_hash: str
    expected_signature_key: str
    expected_last_simulation_year: str
    notes: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _linear_quantile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("Cannot compute quantile from empty values.")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be in [0, 1].")
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    frac = pos - lower
    return ordered[lower] * (1.0 - frac) + ordered[upper] * frac


def _assign_three_bin(
    value: float,
    *,
    low_upper: float,
    middle_upper: float,
    labels: tuple[str, str, str],
) -> str:
    if value <= low_upper:
        return labels[0]
    if value <= middle_upper:
        return labels[1]
    return labels[2]


def _estimate_cli_annual_precip_mm(cli: ClimateFile) -> float:
    for idx, line in enumerate(cli.lines[:-1]):
        if "monthly ave precipitation" not in line.lower():
            continue
        values_line = cli.lines[idx + 1]
        try:
            values = [float(item) for item in values_line.replace(",", " ").split()]
        except ValueError:
            continue
        if len(values) == 12:
            return float(sum(values))

    colnames = cli.colnames
    dtypes = cli.dtypes
    data0line = cli.data0line
    breakpoint = cli.breakpoint
    prcp_index = colnames.index("prcp") if "prcp" in colnames else None
    year_totals: dict[int, float] = defaultdict(float)

    for offset, line in enumerate(cli.lines[data0line:]):
        row = [item.strip() for item in line.split()]
        if line.strip() == "":
            break
        if breakpoint and len(row) == 2 and len(row) != len(colnames):
            continue
        if len(row) != len(colnames):
            continue

        parsed = [dtype(value) for dtype, value in zip(dtypes, row)]
        year = int(parsed[2])
        if breakpoint:
            nbreak = int(parsed[3])
            if nbreak > 0:
                breakpoint_row = cli.lines[data0line + offset + nbreak].split()
                year_totals[year] += float(breakpoint_row[1])
        else:
            assert prcp_index is not None
            year_totals[year] += float(parsed[prcp_index])

    if not year_totals:
        raise ValueError(f"Unable to derive climate precipitation metric from {cli.cli_fn}")
    return float(sum(year_totals.values()) / len(year_totals))


def _preflight_seed(seed: SeedTuple) -> EligibleRecord | QuarantineRecord:
    reason_codes: list[str] = []
    details: list[str] = []
    soil_ofe_count: int | None = None

    for path in (seed.sol_path, seed.man_path, seed.slp_path, seed.cli_path):
        if not Path(path).exists():
            reason_codes.append("MISSING_REQUIRED_INPUT")
            details.append(f"missing={path}")

    if seed.run_path is None or not Path(seed.run_path).exists():
        reason_codes.append("MISSING_RUN_FILE")
        details.append(f"missing_run={seed.run_path}")

    if reason_codes:
        return QuarantineRecord(
            seed_id=seed.seed_id,
            run_id=seed.run_id,
            stem=seed.stem,
            reason_codes=tuple(reason_codes),
            details=tuple(details),
            soil_ofe_count=soil_ofe_count,
            seed_lineage=seed.as_dict(),
        )

    try:
        soil = WeppSoilUtil(seed.sol_path)
        soil_ofe_count = int(soil.obj.get("ntemp", 1))
    except Exception as exc:  # Deliberate parser boundary.
        reason_codes.append("SOIL_PARSE_ERROR")
        details.append(str(exc))
        return QuarantineRecord(
            seed_id=seed.seed_id,
            run_id=seed.run_id,
            stem=seed.stem,
            reason_codes=tuple(reason_codes),
            details=tuple(details),
            soil_ofe_count=soil_ofe_count,
            seed_lineage=seed.as_dict(),
        )

    if soil_ofe_count != 1:
        reason_codes.append("SOIL_MULTI_OFE")
        details.append(f"soil_ntemp={soil_ofe_count}")
        return QuarantineRecord(
            seed_id=seed.seed_id,
            run_id=seed.run_id,
            stem=seed.stem,
            reason_codes=tuple(reason_codes),
            details=tuple(details),
            soil_ofe_count=soil_ofe_count,
            seed_lineage=seed.as_dict(),
        )

    try:
        read_management(seed.man_path)
    except Exception as exc:  # Deliberate parser boundary.
        reason_codes.append("MAN_PARSE_ERROR")
        details.append(str(exc))

    slope_scalar = 0.0
    try:
        slope = SlopeFile(seed.slp_path)
        slope_scalar = abs(float(slope.slope_scalar))
    except AssertionError as exc:
        msg = str(exc)
        if "expecting 1 ofe" in msg.lower():
            reason_codes.append("SLP_MULTI_OFE")
        else:
            reason_codes.append("SLP_PARSE_ERROR")
        details.append(msg)
    except Exception as exc:  # Deliberate parser boundary.
        reason_codes.append("SLP_PARSE_ERROR")
        details.append(str(exc))

    climate_annual_precip_mm = 0.0
    try:
        cli = ClimateFile(seed.cli_path)
        climate_annual_precip_mm = _estimate_cli_annual_precip_mm(cli)
    except Exception as exc:  # Deliberate parser boundary.
        reason_codes.append("CLI_PARSE_ERROR")
        details.append(str(exc))

    if reason_codes:
        return QuarantineRecord(
            seed_id=seed.seed_id,
            run_id=seed.run_id,
            stem=seed.stem,
            reason_codes=tuple(reason_codes),
            details=tuple(details),
            soil_ofe_count=soil_ofe_count,
            seed_lineage=seed.as_dict(),
        )

    return EligibleRecord(
        seed=seed,
        soil_ofe_count=soil_ofe_count,
        climate_annual_precip_mm=climate_annual_precip_mm,
        slope_scalar=slope_scalar,
        climate_bin="",
        slope_bin="",
    )


def preflight_single_ofe_seeds(
    seed_tuples: Sequence[SeedTuple],
) -> tuple[list[EligibleRecord], list[QuarantineRecord]]:
    eligible: list[EligibleRecord] = []
    quarantined: list[QuarantineRecord] = []

    ordered = sorted(seed_tuples, key=lambda row: (row.run_id, row.stem))
    for seed in ordered:
        record = _preflight_seed(seed)
        if isinstance(record, EligibleRecord):
            eligible.append(record)
        else:
            quarantined.append(record)

    return eligible, quarantined


def stratify_eligible_seeds(
    eligible: Sequence[EligibleRecord],
) -> tuple[list[EligibleRecord], StratificationThresholds]:
    if not eligible:
        raise RuntimeError("No eligible single-OFE seeds available after preflight.")

    climate_values = [record.climate_annual_precip_mm for record in eligible]
    slope_values = [record.slope_scalar for record in eligible]

    thresholds = StratificationThresholds(
        climate_dry_upper=_linear_quantile(climate_values, 1.0 / 3.0),
        climate_mesic_upper=_linear_quantile(climate_values, 2.0 / 3.0),
        slope_gradual_upper=_linear_quantile(slope_values, 1.0 / 3.0),
        slope_moderate_upper=_linear_quantile(slope_values, 2.0 / 3.0),
    )

    stratified: list[EligibleRecord] = []
    for record in eligible:
        climate_bin = _assign_three_bin(
            record.climate_annual_precip_mm,
            low_upper=thresholds.climate_dry_upper,
            middle_upper=thresholds.climate_mesic_upper,
            labels=CLIMATE_BINS,
        )
        slope_bin = _assign_three_bin(
            record.slope_scalar,
            low_upper=thresholds.slope_gradual_upper,
            middle_upper=thresholds.slope_moderate_upper,
            labels=SLOPE_BINS,
        )
        stratified.append(
            EligibleRecord(
                seed=record.seed,
                soil_ofe_count=record.soil_ofe_count,
                climate_annual_precip_mm=record.climate_annual_precip_mm,
                slope_scalar=record.slope_scalar,
                climate_bin=climate_bin,
                slope_bin=slope_bin,
            )
        )

    return stratified, thresholds


def select_stratified_seeds(
    stratified: Sequence[EligibleRecord],
    *,
    per_bin_quota: int,
    random_seed: int,
) -> tuple[list[EligibleRecord], dict[tuple[str, str], int]]:
    if per_bin_quota <= 0:
        raise ValueError("per_bin_quota must be > 0.")

    by_bin: dict[tuple[str, str], list[EligibleRecord]] = defaultdict(list)
    for record in stratified:
        by_bin[(record.climate_bin, record.slope_bin)].append(record)

    missing = [key for key in REQUIRED_BIN_KEYS if len(by_bin.get(key, [])) == 0]
    if missing:
        missing_str = ", ".join(f"{climate}/{slope}" for climate, slope in missing)
        raise RuntimeError(f"Mandatory stratification bins missing eligible seeds: {missing_str}")

    rng = random.Random(random_seed)
    selected: list[EligibleRecord] = []
    availability: dict[tuple[str, str], int] = {}

    for key in REQUIRED_BIN_KEYS:
        candidates = sorted(by_bin[key], key=lambda row: row.seed.seed_id)
        rng.shuffle(candidates)
        availability[key] = len(candidates)
        selected.extend(candidates[: min(per_bin_quota, len(candidates))])

    selected.sort(key=lambda row: row.seed.seed_id)
    return selected, availability


def _load_known_failure_signature_keys(path: str | None) -> set[str]:
    if not path:
        return set()
    manifest_path = Path(path)
    if not manifest_path.exists():
        return set()

    keys: set[str] = set()
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row.get("expected_signature_key") or "").strip()
            if key:
                keys.add(key)
    return keys


def _resolve_artifact_path(path_value: str, *, base_dir: Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _load_positive_controls(
    manifest_path: str | None,
) -> list[PositiveControlRecord]:
    if not manifest_path:
        return []
    manifest = Path(manifest_path)
    if not manifest.exists():
        return []

    base_dir = manifest.parent.parent.parent
    controls: list[PositiveControlRecord] = []
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            case_id = (row.get("case_id") or "").strip()
            stderr_raw = (row.get("stderr_path") or "").strip()
            if not case_id or not stderr_raw:
                continue

            stderr_path = _resolve_artifact_path(stderr_raw, base_dir=base_dir)
            observe_raw = (row.get("observe_path") or "").strip()
            observe_path = ""
            if observe_raw:
                observe_path = str(_resolve_artifact_path(observe_raw, base_dir=base_dir))

            controls.append(
                PositiveControlRecord(
                    case_id=f"{POSITIVE_CONTROL_CASE_PREFIX}{case_id}",
                    stderr_path=str(stderr_path),
                    observe_path=observe_path,
                    expected_signal_class=(row.get("expected_signal_class") or "").strip(),
                    expected_top_frame=(row.get("expected_top_frame") or "").strip(),
                    expected_last_marker_tag=(row.get("expected_last_marker_tag") or "").strip(),
                    expected_classification=(row.get("expected_classification") or "").strip(),
                    expected_routine_chain_hash=(row.get("expected_routine_chain_hash") or "").strip(),
                    expected_signature_key=(row.get("expected_signature_key") or "").strip(),
                    expected_last_simulation_year=(row.get("expected_last_simulation_year") or "").strip(),
                    notes=(row.get("notes") or "").strip(),
                )
            )

    return controls


def _evaluate_secondary_oracle(
    *,
    case_dir: Path,
    execution_status: str,
) -> tuple[str, list[str], list[str]]:
    flags: list[str] = []
    evidence: list[str] = []

    if execution_status != "executed":
        flags.append("ORACLE_PARSE_INTEGRITY_EXECUTION_NOT_EXECUTED")
        evidence.append(f"execution_status={execution_status}")
        return "indeterminate", flags, evidence

    combined_log = case_dir / "execution" / "combined.log"
    if not combined_log.exists():
        flags.append("ORACLE_PARSE_INTEGRITY_MISSING_LOG")
        evidence.append("missing=execution/combined.log")
        return "indeterminate", flags, evidence

    output_dir = case_dir / "execution" / "workspace" / "output"
    required_globs = ("*.loss.dat", "*.wat.dat")
    required_outputs: dict[str, list[Path]] = {
        pattern: sorted(output_dir.glob(pattern)) for pattern in required_globs
    }
    missing_required = [pattern for pattern, matches in required_outputs.items() if not matches]
    if missing_required:
        flags.append("ORACLE_PARSE_INTEGRITY_MISSING_OUTPUT")
        evidence.append(f"missing_outputs={','.join(missing_required)}")
        return "indeterminate", flags, evidence

    candidate_paths: list[Path] = [combined_log]
    candidate_paths.extend(sorted(output_dir.glob("*.dat")))

    negative_flagged = False
    token_flagged = False
    for path in candidate_paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        match = ORACLE_TOKEN_PATTERN.search(text)
        if match:
            token = match.group(1).lower()
            flags.append("ORACLE_TOKEN_ANOMALY")
            evidence.append(f"{path.name}:token={token}")
            token_flagged = True

        if path.suffixes[-2:] not in ([".loss", ".dat"], [".wat", ".dat"]):
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            line_lower = line.lower()
            if not any(hint in line_lower for hint in ORACLE_NONNEGATIVE_HINTS):
                continue
            for value_raw in NUMBER_PATTERN.findall(line):
                try:
                    value = float(value_raw)
                except ValueError:
                    continue
                if value < -1.0e-9:
                    flags.append("ORACLE_IMPOSSIBLE_NEGATIVE_VALUE")
                    evidence.append(f"{path.name}:L{line_no}:value={value_raw}")
                    negative_flagged = True
                    break
            if negative_flagged:
                break
        if negative_flagged:
            break

    deduped_flags = sorted(set(flags))
    deduped_evidence = sorted(set(evidence))
    if token_flagged or negative_flagged:
        return "flag", deduped_flags, deduped_evidence
    return "pass", deduped_flags, deduped_evidence


def _upper_bound(alpha: float, trials: int) -> float | None:
    if trials <= 0:
        return None
    return 1.0 - math.pow(alpha, 1.0 / float(trials))


def _ensure_rosetta3_available() -> None:
    try:
        from rosetta import Rosetta3
    except (ModuleNotFoundError, ImportError) as exc:
        raise RuntimeError(
            "Rosetta3 dependency unavailable. "
            "Install vendored rosetta in host .venv before running campaign generation."
        ) from exc
    _ = Rosetta3


def load_seed_signals_from_prior_campaign(
    *,
    prior_campaign_root: str | None,
    known_failures_manifest: str | None,
) -> dict[str, SeedSignal]:
    if not prior_campaign_root:
        return {}

    root = Path(prior_campaign_root)
    if not root.exists():
        return {}

    execution_manifest = root / "execution_manifest.csv"
    classifier_results = root / "classifier_results.csv"
    if not execution_manifest.exists():
        return {}

    with execution_manifest.open("r", encoding="utf-8", newline="") as handle:
        execution_rows = list(csv.DictReader(handle))

    classifier_by_case: dict[str, dict[str, str]] = {}
    if classifier_results.exists():
        with classifier_results.open("r", encoding="utf-8", newline="") as handle:
            classifier_by_case = {row["case_id"]: row for row in csv.DictReader(handle)}

    known_failures = _load_known_failure_signature_keys(known_failures_manifest)
    warning_by_case: dict[str, int] = {}

    for row in execution_rows:
        case_id = row["case_id"]
        case_metadata_path = Path(row["case_dir"]) / "case_metadata.json"
        if case_metadata_path.exists():
            payload = json.loads(case_metadata_path.read_text(encoding="utf-8"))
            warning_by_case[case_id] = int(payload.get("soft_warning_count", 0))
        else:
            warning_by_case[case_id] = 0

    aggregates: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"total_cases": 0, "warning_total": 0.0, "non_pass_hits": 0, "novel_non_pass_hits": 0}
    )
    for row in execution_rows:
        seed_id = row["seed_id"]
        case_id = row["case_id"]
        agg = aggregates[seed_id]
        agg["total_cases"] = int(agg["total_cases"]) + 1
        agg["warning_total"] = float(agg["warning_total"]) + float(warning_by_case.get(case_id, 0))

        classification = (classifier_by_case.get(case_id, {}).get("classification") or "").strip()
        signature_key = (classifier_by_case.get(case_id, {}).get("signature_key") or "").strip()
        if classification and classification != "PASS":
            agg["non_pass_hits"] = int(agg["non_pass_hits"]) + 1
            if signature_key and signature_key not in known_failures:
                agg["novel_non_pass_hits"] = int(agg["novel_non_pass_hits"]) + 1

    signals: dict[str, SeedSignal] = {}
    for seed_id, agg in aggregates.items():
        total_cases = max(1, int(agg["total_cases"]))
        signals[seed_id] = SeedSignal(
            soft_warning_density=round(float(agg["warning_total"]) / float(total_cases), 6),
            non_pass_hits=int(agg["non_pass_hits"]),
            novel_non_pass_hits=int(agg["novel_non_pass_hits"]),
        )
    return signals


def _weighted_without_replacement(
    candidates: Sequence[EligibleRecord],
    *,
    target_count: int,
    random_seed: int,
    weights: dict[str, float],
) -> list[EligibleRecord]:
    if target_count <= 0 or not candidates:
        return []
    rng = random.Random(random_seed)
    remaining = list(candidates)
    selected: list[EligibleRecord] = []
    while remaining and len(selected) < target_count:
        choices = [max(weights.get(row.seed.seed_id, 1.0), 1.0e-9) for row in remaining]
        idx = rng.choices(range(len(remaining)), weights=choices, k=1)[0]
        selected.append(remaining.pop(idx))
    return selected


def _parse_target_slice(target_slice: str) -> tuple[str, str, str]:
    parts = [part.strip() for part in target_slice.split(":")]
    if len(parts) != 3:
        raise ValueError(
            "target_slice must be formatted as climate_bin:slope_bin:mutation_profile_id"
        )
    climate_bin, slope_bin, mutation_profile_id = parts
    if climate_bin not in CLIMATE_BINS:
        raise ValueError(f"Unknown target climate_bin={climate_bin}")
    if slope_bin not in SLOPE_BINS:
        raise ValueError(f"Unknown target slope_bin={slope_bin}")
    if mutation_profile_id not in MUTATION_PROFILES:
        raise ValueError(f"Unknown target mutation_profile_id={mutation_profile_id}")
    if mutation_profile_id == DEFAULT_MUTATION_PROFILE:
        raise ValueError("target_slice mutation_profile_id must be a non-baseline profile.")
    return climate_bin, slope_bin, mutation_profile_id


def build_targeted_slice_selection_plan(
    stratified: Sequence[EligibleRecord],
    *,
    target_slice: str,
    target_case_count: int,
    random_seed: int,
) -> tuple[list[EligibleRecord], dict[tuple[str, str], int], dict[str, dict[str, Any]]]:
    if target_case_count <= 0:
        raise ValueError("target_case_count must be > 0.")
    climate_bin, slope_bin, mutation_profile_id = _parse_target_slice(target_slice)

    by_bin: dict[tuple[str, str], list[EligibleRecord]] = defaultdict(list)
    for record in stratified:
        by_bin[(record.climate_bin, record.slope_bin)].append(record)

    availability: dict[tuple[str, str], int] = {
        key: len(by_bin.get(key, [])) for key in REQUIRED_BIN_KEYS
    }
    candidates = sorted(
        by_bin.get((climate_bin, slope_bin), []), key=lambda row: row.seed.seed_id
    )
    if len(candidates) < target_case_count:
        raise RuntimeError(
            "Insufficient eligible seeds for targeted slice "
            f"{climate_bin}:{slope_bin}. available={len(candidates)} "
            f"required={target_case_count}"
        )

    rng = random.Random(random_seed)
    rng.shuffle(candidates)
    selected = sorted(candidates[:target_case_count], key=lambda row: row.seed.seed_id)

    selection_meta: dict[str, dict[str, Any]] = {}
    for row in selected:
        selection_meta[row.seed.seed_id] = {
            "adaptive_score": 1.0,
            "adaptive_components": {},
            "mutation_profile_id": mutation_profile_id,
            "climate_bin": row.climate_bin,
            "slope_bin": row.slope_bin,
            "target_slice": target_slice,
        }

    return selected, availability, selection_meta


def build_adaptive_selection_plan(
    stratified: Sequence[EligibleRecord],
    *,
    per_bin_quota: int,
    target_case_count: int,
    base_seed: int,
    oversampling_weights: OversamplingWeights,
    prior_signals: dict[str, SeedSignal],
    profile_weights: dict[str, float],
    profile_floor: int,
) -> tuple[list[EligibleRecord], dict[tuple[str, str], int], dict[str, dict[str, Any]]]:
    base_selected, availability = select_stratified_seeds(
        stratified, per_bin_quota=per_bin_quota, random_seed=base_seed
    )
    seed_lookup = {row.seed.seed_id: row for row in stratified}
    selected_ids = {row.seed.seed_id for row in base_selected}
    remaining = [row for row in stratified if row.seed.seed_id not in selected_ids]

    target_count = max(len(base_selected), target_case_count)
    extra_needed = max(0, target_count - len(base_selected))

    score_by_seed: dict[str, float] = {}
    component_by_seed: dict[str, dict[str, float | int]] = {}
    for row in stratified:
        signal = prior_signals.get(
            row.seed.seed_id,
            SeedSignal(soft_warning_density=0.0, non_pass_hits=0, novel_non_pass_hits=0),
        )
        score = 1.0
        score += signal.soft_warning_density * oversampling_weights.warning_density
        score += float(signal.non_pass_hits) * oversampling_weights.non_pass_signature
        score += float(signal.novel_non_pass_hits) * oversampling_weights.novel_signature

        if row.climate_bin in {"dry", "wet"}:
            score += oversampling_weights.dry_wet_corner
        if row.slope_bin in {"gradual", "steep"}:
            score += oversampling_weights.gradual_steep_corner

        score_by_seed[row.seed.seed_id] = round(max(score, 1.0e-6), 6)
        component_by_seed[row.seed.seed_id] = {
            "soft_warning_density": signal.soft_warning_density,
            "non_pass_hits": signal.non_pass_hits,
            "novel_non_pass_hits": signal.novel_non_pass_hits,
            "final_score": score_by_seed[row.seed.seed_id],
        }

    oversampled = _weighted_without_replacement(
        remaining,
        target_count=extra_needed,
        random_seed=base_seed + 991,
        weights=score_by_seed,
    )
    selected = sorted(
        list(base_selected) + oversampled, key=lambda record: record.seed.seed_id
    )

    ordered_profiles = [
        profile
        for profile in MUTATION_PROFILES
        if profile != DEFAULT_MUTATION_PROFILE and profile in profile_weights
    ]
    if not ordered_profiles:
        raise RuntimeError("No mutation profiles configured for adaptive planning.")

    per_seed_profile: dict[str, str] = {}
    floor_pool = [row.seed.seed_id for row in selected]
    rng_floor = random.Random(base_seed + 401)
    rng_floor.shuffle(floor_pool)
    floor_index = 0
    for profile in ordered_profiles:
        for _ in range(profile_floor):
            if floor_index >= len(floor_pool):
                break
            seed_id = floor_pool[floor_index]
            floor_index += 1
            if seed_id not in per_seed_profile:
                per_seed_profile[seed_id] = profile

    rng_profiles = random.Random(base_seed + 577)
    profile_names = [profile for profile in ordered_profiles]
    profile_weight_values = [max(profile_weights.get(profile, 0.0), 0.0) for profile in profile_names]
    if not any(profile_weight_values):
        raise RuntimeError("At least one positive profile weight is required.")
    for row in selected:
        seed_id = row.seed.seed_id
        if seed_id in per_seed_profile:
            continue
        adjusted_weights = list(profile_weight_values)
        if row.slope_bin in {"moderate", "steep"} and "P5_SLOPE_RESPONSE_AMPLIFICATION" in profile_names:
            idx = profile_names.index("P5_SLOPE_RESPONSE_AMPLIFICATION")
            adjusted_weights[idx] *= 1.75
        per_seed_profile[seed_id] = rng_profiles.choices(
            profile_names, weights=adjusted_weights, k=1
        )[0]

    selection_meta: dict[str, dict[str, Any]] = {}
    for row in selected:
        seed_id = row.seed.seed_id
        selection_meta[seed_id] = {
            "adaptive_score": score_by_seed.get(seed_id, 1.0),
            "adaptive_components": component_by_seed.get(seed_id, {}),
            "mutation_profile_id": per_seed_profile[seed_id],
            "climate_bin": row.climate_bin,
            "slope_bin": row.slope_bin,
        }

    return selected, availability, selection_meta


def shard_selected_seeds(
    selected: Sequence[EligibleRecord],
    *,
    shard_count: int,
    random_seed: int,
) -> list[list[EligibleRecord]]:
    if shard_count <= 0:
        raise ValueError("shard_count must be > 0.")
    if not selected:
        raise RuntimeError("No selected seeds available for sharding.")

    rng = random.Random(random_seed)
    ordered = sorted(selected, key=lambda row: row.seed.seed_id)
    rng.shuffle(ordered)

    shards: list[list[EligibleRecord]] = [[] for _ in range(shard_count)]
    for idx, record in enumerate(ordered):
        shards[idx % shard_count].append(record)
    return shards


def _prepare_execution_workspace(
    *,
    case_dir: Path,
    generated_paths: dict[str, str | None],
) -> tuple[Path, Path]:
    execution_root = case_dir / "execution"
    runs_dir = execution_root / "workspace" / "runs"
    output_dir = execution_root / "workspace" / "output"
    if execution_root.exists():
        shutil.rmtree(execution_root)
    runs_dir.mkdir(parents=True, exist_ok=False)
    output_dir.mkdir(parents=True, exist_ok=False)

    for ext in ("sol", "man", "slp", "cli", "run"):
        src = generated_paths.get(ext)
        if not src:
            continue
        src_path = Path(src)
        if src_path.exists():
            shutil.copy2(src_path, runs_dir / src_path.name)

    run_src = generated_paths.get("run")
    if not run_src:
        raise FileNotFoundError("Generated case is missing run file path.")
    run_name = Path(run_src).name
    run_path = runs_dir / run_name
    if not run_path.exists():
        raise FileNotFoundError(f"Execution run file missing from workspace: {run_path}")

    return runs_dir, run_path


def _execute_case(
    *,
    case_dir: Path,
    generated_paths: dict[str, str | None],
    wepp_binary: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    if not wepp_binary.exists():
        raise FileNotFoundError(f"WEPP binary does not exist: {wepp_binary}")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be > 0.")

    log_path = case_dir / "execution" / "combined.log"
    started = time.perf_counter()
    try:
        runs_dir, run_path = _prepare_execution_workspace(
            case_dir=case_dir, generated_paths=generated_paths
        )
    except Exception as exc:  # Deliberate setup boundary.
        return {
            "execution_status": "workspace_error",
            "execution_exit_code": None,
            "execution_duration_seconds": round(time.perf_counter() - started, 6),
            "stderr_path": None,
            "execution_error": str(exc),
        }

    try:
        with run_path.open("rb") as run_handle, log_path.open("w", encoding="utf-8") as log_handle:
            proc = subprocess.run(
                [str(wepp_binary)],
                stdin=run_handle,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                cwd=str(runs_dir),
                timeout=timeout_seconds,
                check=False,
            )
        status = "executed"
        exit_code: int | None = int(proc.returncode)
        error: str | None = None
    except subprocess.TimeoutExpired:
        status = "timeout"
        exit_code = None
        error = f"execution timeout after {timeout_seconds} seconds"
    except Exception as exc:  # Deliberate subprocess boundary.
        status = "execution_error"
        exit_code = None
        error = str(exc)

    return {
        "execution_status": status,
        "execution_exit_code": exit_code,
        "execution_duration_seconds": round(time.perf_counter() - started, 6),
        "stderr_path": str(log_path) if log_path.exists() else None,
        "execution_error": error,
    }


def _write_csv(path: Path, *, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _seed_tuple_from_dict(payload: dict[str, Any]) -> SeedTuple:
    run_path_raw = payload.get("run_path")
    run_path = (
        str(run_path_raw)
        if run_path_raw not in (None, "")
        else None
    )
    return SeedTuple(
        seed_id=str(payload["seed_id"]),
        run_id=str(payload["run_id"]),
        runs_dir=str(payload["runs_dir"]),
        stem=str(payload["stem"]),
        sol_path=str(payload["sol_path"]),
        man_path=str(payload["man_path"]),
        slp_path=str(payload["slp_path"]),
        cli_path=str(payload["cli_path"]),
        run_path=run_path,
    )


def _eligible_record_from_dict(payload: dict[str, Any]) -> EligibleRecord:
    return EligibleRecord(
        seed=_seed_tuple_from_dict(dict(payload["seed"])),
        soil_ofe_count=int(payload["soil_ofe_count"]),
        climate_annual_precip_mm=float(payload["climate_annual_precip_mm"]),
        slope_scalar=float(payload["slope_scalar"]),
        climate_bin=str(payload["climate_bin"]),
        slope_bin=str(payload["slope_bin"]),
    )


def _quarantine_record_from_dict(payload: dict[str, Any]) -> QuarantineRecord:
    return QuarantineRecord(
        seed_id=str(payload["seed_id"]),
        run_id=str(payload["run_id"]),
        stem=str(payload["stem"]),
        reason_codes=tuple(str(item) for item in payload.get("reason_codes", [])),
        details=tuple(str(item) for item in payload.get("details", [])),
        soil_ofe_count=(
            int(payload["soil_ofe_count"])
            if payload.get("soil_ofe_count") not in (None, "")
            else None
        ),
        seed_lineage=dict(payload.get("seed_lineage", {})),
    )


def run_campaign(args: argparse.Namespace) -> dict[str, Any]:
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    _ensure_rosetta3_available()
    targeted_slice_mode = bool((args.target_slice or "").strip())
    minimum_required = args.per_bin_quota * len(REQUIRED_BIN_KEYS)
    if not targeted_slice_mode and args.target_case_count < minimum_required:
        raise ValueError(
            "target_case_count must be >= per_bin_quota * 9 to preserve mandatory 3x3 bins."
        )
    if args.profile_floor_count < 0:
        raise ValueError("profile_floor_count must be >= 0.")

    cached_preflight_path = (
        Path(args.preflight_cache_json).resolve()
        if (args.preflight_cache_json or "").strip()
        else None
    )
    if cached_preflight_path is not None:
        if not cached_preflight_path.exists():
            raise FileNotFoundError(f"Missing preflight cache json: {cached_preflight_path}")
        cached_preflight = json.loads(cached_preflight_path.read_text(encoding="utf-8"))
        stratified = [
            _eligible_record_from_dict(dict(row))
            for row in cached_preflight.get("eligible_records", [])
        ]
        quarantined = [
            _quarantine_record_from_dict(dict(row))
            for row in cached_preflight.get("quarantined_records", [])
        ]
        if not stratified:
            raise RuntimeError("Cached preflight contains no eligible_records.")
        discovered_total = int(
            cached_preflight.get("total_discovered", len(stratified) + len(quarantined))
        )
        climate_values = [record.climate_annual_precip_mm for record in stratified]
        slope_values = [record.slope_scalar for record in stratified]
        thresholds = StratificationThresholds(
            climate_dry_upper=_linear_quantile(climate_values, 1.0 / 3.0),
            climate_mesic_upper=_linear_quantile(climate_values, 2.0 / 3.0),
            slope_gradual_upper=_linear_quantile(slope_values, 1.0 / 3.0),
            slope_moderate_upper=_linear_quantile(slope_values, 2.0 / 3.0),
        )
    else:
        discovered = discover_seed_tuples(args.run_root, max_run_dirs=args.max_run_dirs)
        if not discovered:
            raise RuntimeError("No seed tuples discovered from run root.")

        eligible, quarantined = preflight_single_ofe_seeds(discovered)
        stratified, thresholds = stratify_eligible_seeds(eligible)
        discovered_total = len(discovered)

    eligible = stratified
    prior_signals = load_seed_signals_from_prior_campaign(
        prior_campaign_root=args.prior_campaign_root,
        known_failures_manifest=args.known_failures_manifest,
    )
    oversampling_config = OversamplingWeights(
        warning_density=args.oversample_warning_weight,
        non_pass_signature=args.oversample_non_pass_weight,
        novel_signature=args.oversample_novel_weight,
        dry_wet_corner=args.oversample_dry_wet_corner_weight,
        gradual_steep_corner=args.oversample_gradual_steep_corner_weight,
    )
    profile_weights = {
        "P1_DENOMINATOR_EDGE": args.profile_weight_p1,
        "P2_EVENT_EDGE": args.profile_weight_p2,
        "P3_CONDUCTIVITY_SATURATION_CONTRAST": args.profile_weight_p3,
        "P4_TEXTURE_DENSITY_DISCONTINUITY": args.profile_weight_p4,
        "P5_SLOPE_RESPONSE_AMPLIFICATION": args.profile_weight_p5,
    }
    if targeted_slice_mode:
        selected, availability, selection_meta = build_targeted_slice_selection_plan(
            stratified,
            target_slice=str(args.target_slice).strip(),
            target_case_count=args.target_case_count,
            random_seed=args.stratification_seed,
        )
    else:
        selected, availability, selection_meta = build_adaptive_selection_plan(
            stratified,
            per_bin_quota=args.per_bin_quota,
            target_case_count=args.target_case_count,
            base_seed=args.stratification_seed,
            oversampling_weights=oversampling_config,
            prior_signals=prior_signals,
            profile_weights=profile_weights,
            profile_floor=args.profile_floor_count,
        )
    shards = shard_selected_seeds(
        selected,
        shard_count=args.shard_count,
        random_seed=args.shard_seed,
    )

    selected_by_seed_id = {record.seed.seed_id: record for record in selected}
    selected_by_bin_counter = Counter((r.climate_bin, r.slope_bin) for r in selected)
    seed_by_bin_counter = Counter((r.climate_bin, r.slope_bin) for r in stratified)
    producer_obligation_rows = _build_preflight_producer_obligation_rows(
        quarantined,
        strict_policy=bool(args.policy_era_producer_obligation_strict),
    )
    producer_obligation_summary = _summarize_preflight_producer_obligation_rows(
        producer_obligation_rows
    )

    preflight_payload = {
        "total_discovered": discovered_total,
        "eligible_single_ofe": len(eligible),
        "quarantined": len(quarantined),
        "policy_era_producer_obligation_strict": bool(
            args.policy_era_producer_obligation_strict
        ),
        "preflight_cache_json": str(cached_preflight_path) if cached_preflight_path else "",
        "quarantine_reason_counts": dict(
            sorted(
                Counter(reason for row in quarantined for reason in row.reason_codes).items()
            )
        ),
        "producer_obligation_summary": producer_obligation_summary,
        "producer_obligation_records": producer_obligation_rows,
        "quarantined_records": [row.as_dict() for row in quarantined],
        "eligible_records": [row.as_dict() for row in stratified],
    }
    _write_json(output_root / "preflight_manifest.json", preflight_payload)

    quarantine_rows = [
        {
            "seed_id": row.seed_id,
            "run_id": row.run_id,
            "stem": row.stem,
            "reason_codes": "|".join(row.reason_codes),
            "details": " | ".join(row.details),
            "soil_ofe_count": row.soil_ofe_count if row.soil_ofe_count is not None else "",
        }
        for row in quarantined
    ]
    _write_csv(
        output_root / "quarantine_manifest.csv",
        rows=quarantine_rows,
        fieldnames=[
            "seed_id",
            "run_id",
            "stem",
            "reason_codes",
            "details",
            "soil_ofe_count",
        ],
    )
    _write_csv(
        output_root / "preflight_contract_obligations.csv",
        rows=producer_obligation_rows,
        fieldnames=[
            "seed_id",
            "run_id",
            "stem",
            "reason_code",
            "obligation_id",
            "contract_ref",
            "channel_class",
            "boundary_disposition",
            "strict_policy_required",
            "mapping_status",
            "rationale_token",
            "details",
        ],
    )

    selected_rows = [
        {
            "seed_id": row.seed.seed_id,
            "run_id": row.seed.run_id,
            "stem": row.seed.stem,
            "climate_annual_precip_mm": round(row.climate_annual_precip_mm, 6),
            "slope_scalar": round(row.slope_scalar, 6),
            "climate_bin": row.climate_bin,
            "slope_bin": row.slope_bin,
            "run_path": row.seed.run_path or "",
            "adaptive_score": selection_meta[row.seed.seed_id]["adaptive_score"],
            "mutation_profile_id": selection_meta[row.seed.seed_id]["mutation_profile_id"],
        }
        for row in selected
    ]
    _write_csv(
        output_root / "selected_seeds.csv",
        rows=selected_rows,
        fieldnames=[
            "seed_id",
            "run_id",
            "stem",
            "climate_annual_precip_mm",
            "slope_scalar",
            "climate_bin",
            "slope_bin",
            "run_path",
            "adaptive_score",
            "mutation_profile_id",
        ],
    )

    stratification_payload = {
        "thresholds": thresholds.as_dict(),
        "per_bin_quota": args.per_bin_quota,
        "target_case_count": args.target_case_count,
        "target_slice": str(args.target_slice).strip(),
        "targeted_slice_mode": targeted_slice_mode,
        "seed_count_by_bin": {
            f"{climate}:{slope}": seed_by_bin_counter.get((climate, slope), 0)
            for climate, slope in REQUIRED_BIN_KEYS
        },
        "selected_count_by_bin": {
            f"{climate}:{slope}": selected_by_bin_counter.get((climate, slope), 0)
            for climate, slope in REQUIRED_BIN_KEYS
        },
        "availability_by_bin": {
            f"{climate}:{slope}": availability.get((climate, slope), 0)
            for climate, slope in REQUIRED_BIN_KEYS
        },
        "adaptive_oversampling_weights": oversampling_config.as_dict(),
        "profile_weights": profile_weights,
        "profile_floor_count": args.profile_floor_count,
    }
    _write_json(output_root / "stratification_manifest.json", stratification_payload)
    _write_json(output_root / "selection_metadata.json", selection_meta)

    positive_controls = _load_positive_controls(args.positive_controls_manifest)
    _write_json(
        output_root / "positive_control_manifest.json",
        {
            "source_manifest": args.positive_controls_manifest,
            "controls_expected": len(positive_controls),
            "controls": [row.as_dict() for row in positive_controls],
        },
    )

    execution_records: list[dict[str, Any]] = []
    classifier_rows: list[dict[str, str]] = []
    shard_rows: list[dict[str, Any]] = []

    for shard_idx, shard_records in enumerate(shards, start=1):
        shard_name = f"shard-{shard_idx:03d}"
        shard_dir = output_root / "shards" / shard_name
        generated_dir = shard_dir / "generated"
        shard_seed = args.generator_seed + shard_idx

        shard_generator = SeededSoilLanduseGenerator(
            run_root=args.run_root,
            random_seed=shard_seed,
            catalog_map=args.catalog_map,
        )
        shard_case_configs = [
            {
                "mutation_profile_id": selection_meta[row.seed.seed_id]["mutation_profile_id"],
                "mutation_profile_attribution": selection_meta[row.seed.seed_id],
            }
            for row in shard_records
        ]
        shard_manifest = shard_generator.generate_batch(
            seeds=[row.seed for row in shard_records],
            output_root=generated_dir,
            case_configs=shard_case_configs,
        )

        shard_rows.append(
            {
                "shard_id": shard_name,
                "generator_seed": shard_seed,
                "selected_seed_count": len(shard_records),
                "ok_cases": shard_manifest.get("ok_cases", 0),
                "hard_fail_cases": shard_manifest.get("hard_fail_cases", 0),
                "manifest_json": shard_manifest.get("manifest_json"),
                "manifest_csv": shard_manifest.get("manifest_csv"),
            }
        )

        for case in shard_manifest.get("cases", []):
            seed_id = case["seed_id"]
            selected_meta = selected_by_seed_id.get(seed_id)
            if selected_meta is None:
                raise KeyError(f"Selected metadata not found for seed_id={seed_id}")
            climate_bin = selected_meta.climate_bin
            slope_bin = selected_meta.slope_bin
            case_dir = generated_dir / case["case_id"]

            record: dict[str, Any] = {
                "case_id": case["case_id"],
                "seed_id": seed_id,
                "run_id": selected_meta.seed.run_id,
                "stem": selected_meta.seed.stem,
                "shard_id": shard_name,
                "climate_bin": climate_bin,
                "slope_bin": slope_bin,
                "generation_status": case.get("status"),
                "mutation_seed": case.get("mutation_seed"),
                "mutation_profile_id": case.get("mutation_profile_id"),
                "adaptive_score": selection_meta[seed_id]["adaptive_score"],
                "case_dir": str(case_dir),
            }

            if case.get("status") != "ok":
                oracle_status, oracle_flags, oracle_evidence = _evaluate_secondary_oracle(
                    case_dir=case_dir,
                    execution_status="generation_hard_fail",
                )
                record.update(
                    {
                        "execution_status": "generation_hard_fail",
                        "execution_exit_code": None,
                        "execution_duration_seconds": 0.0,
                        "stderr_path": None,
                        "execution_error": "; ".join(case.get("hard_failures", [])),
                        "oracle_status": oracle_status,
                        "oracle_flags": "|".join(oracle_flags),
                        "oracle_evidence": " | ".join(oracle_evidence),
                    }
                )
                execution_records.append(record)
                continue

            execution = _execute_case(
                case_dir=case_dir,
                generated_paths=case.get("generated_paths", {}),
                wepp_binary=Path(args.wepp_binary),
                timeout_seconds=args.execution_timeout_seconds,
            )
            oracle_status, oracle_flags, oracle_evidence = _evaluate_secondary_oracle(
                case_dir=case_dir,
                execution_status=execution["execution_status"],
            )
            record.update(execution)
            record["oracle_status"] = oracle_status
            record["oracle_flags"] = "|".join(oracle_flags)
            record["oracle_evidence"] = " | ".join(oracle_evidence)
            execution_records.append(record)

            stderr_path = execution.get("stderr_path")
            if stderr_path:
                classifier_rows.append(
                    {
                        "case_id": case["case_id"],
                        "stderr_path": str(Path(stderr_path).relative_to(output_root)),
                        "observe_path": "",
                        "lineage_kind": "generated",
                        "expected_signal_class": "",
                        "expected_top_frame": "",
                        "expected_last_marker_tag": "",
                        "expected_classification": "",
                        "expected_routine_chain_hash": "",
                        "expected_signature_key": "",
                        "expected_last_simulation_year": "",
                        "control_notes": "",
                    }
                )

    for control in positive_controls:
        classifier_rows.append(
            {
                "case_id": control.case_id,
                "stderr_path": control.stderr_path,
                "observe_path": control.observe_path,
                "lineage_kind": "positive_control",
                "expected_signal_class": control.expected_signal_class,
                "expected_top_frame": control.expected_top_frame,
                "expected_last_marker_tag": control.expected_last_marker_tag,
                "expected_classification": control.expected_classification,
                "expected_routine_chain_hash": control.expected_routine_chain_hash,
                "expected_signature_key": control.expected_signature_key,
                "expected_last_simulation_year": control.expected_last_simulation_year,
                "control_notes": control.notes,
            }
        )

    _write_csv(
        output_root / "shard_manifest.csv",
        rows=shard_rows,
        fieldnames=[
            "shard_id",
            "generator_seed",
            "selected_seed_count",
            "ok_cases",
            "hard_fail_cases",
            "manifest_json",
            "manifest_csv",
        ],
    )
    _write_csv(
        output_root / "execution_manifest.csv",
        rows=execution_records,
        fieldnames=[
            "case_id",
            "seed_id",
            "run_id",
            "stem",
            "shard_id",
            "climate_bin",
            "slope_bin",
            "generation_status",
            "mutation_seed",
            "mutation_profile_id",
            "adaptive_score",
            "case_dir",
            "execution_status",
            "execution_exit_code",
            "execution_duration_seconds",
            "stderr_path",
            "execution_error",
            "oracle_status",
            "oracle_flags",
            "oracle_evidence",
        ],
    )
    _write_csv(
        output_root / "classifier_manifest.csv",
        rows=classifier_rows,
        fieldnames=[
            "case_id",
            "stderr_path",
            "observe_path",
            "lineage_kind",
            "expected_signal_class",
            "expected_top_frame",
            "expected_last_marker_tag",
            "expected_classification",
            "expected_routine_chain_hash",
            "expected_signature_key",
            "expected_last_simulation_year",
            "control_notes",
        ],
    )

    coverage_rows = []
    for climate_bin, slope_bin in REQUIRED_BIN_KEYS:
        coverage_rows.append(
            {
                "climate_bin": climate_bin,
                "slope_bin": slope_bin,
                "seed_count": seed_by_bin_counter.get((climate_bin, slope_bin), 0),
                "selected_count": selected_by_bin_counter.get((climate_bin, slope_bin), 0),
                "executed_count": sum(
                    1
                    for row in execution_records
                    if row["climate_bin"] == climate_bin
                    and row["slope_bin"] == slope_bin
                    and row["execution_status"] == "executed"
                ),
                "hard_fail_count": sum(
                    1
                    for row in execution_records
                    if row["climate_bin"] == climate_bin
                    and row["slope_bin"] == slope_bin
                    and row["execution_status"] != "executed"
                ),
                "signature_count": 0,
            }
        )
    _write_csv(
        output_root / "coverage_matrix.csv",
        rows=coverage_rows,
        fieldnames=[
            "climate_bin",
            "slope_bin",
            "seed_count",
            "selected_count",
            "executed_count",
            "hard_fail_count",
            "signature_count",
        ],
    )

    payload = {
        "campaign_root": str(output_root),
        "run_root": args.run_root,
        "generator_seed": args.generator_seed,
        "stratification_seed": args.stratification_seed,
        "shard_seed": args.shard_seed,
        "per_bin_quota": args.per_bin_quota,
        "target_case_count": args.target_case_count,
        "shard_count": args.shard_count,
        "wepp_binary": args.wepp_binary,
        "execution_timeout_seconds": args.execution_timeout_seconds,
        "prior_campaign_root": args.prior_campaign_root,
        "known_failures_manifest": args.known_failures_manifest,
        "positive_controls_manifest": args.positive_controls_manifest,
        "preflight": {
            "total_discovered": discovered_total,
            "eligible_single_ofe": len(eligible),
            "quarantined": len(quarantined),
            "quarantine_reason_counts": preflight_payload["quarantine_reason_counts"],
            "policy_era_producer_obligation_strict": bool(
                args.policy_era_producer_obligation_strict
            ),
            "producer_obligation_row_count": producer_obligation_summary["row_count"],
            "producer_obligation_unmapped_count": producer_obligation_summary[
                "unmapped_reason_code_count"
            ],
            "producer_obligation_channel_counts": producer_obligation_summary[
                "channel_class_counts"
            ],
            "producer_obligation_contract_counts": producer_obligation_summary[
                "contract_ref_counts"
            ],
            "producer_obligation_manifest_csv": str(
                output_root / "preflight_contract_obligations.csv"
            ),
        },
        "positive_controls": {
            "controls_expected": len(positive_controls),
            "controls_manifest_json": str(output_root / "positive_control_manifest.json"),
        },
        "stratification": {
            "thresholds": thresholds.as_dict(),
            "seed_count_by_bin": stratification_payload["seed_count_by_bin"],
            "selected_count_by_bin": stratification_payload["selected_count_by_bin"],
            "availability_by_bin": stratification_payload["availability_by_bin"],
            "adaptive_oversampling_weights": stratification_payload[
                "adaptive_oversampling_weights"
            ],
            "profile_weights": stratification_payload["profile_weights"],
            "profile_floor_count": stratification_payload["profile_floor_count"],
        },
        "shard_manifest_csv": str(output_root / "shard_manifest.csv"),
        "execution_manifest_csv": str(output_root / "execution_manifest.csv"),
        "classifier_manifest_csv": str(output_root / "classifier_manifest.csv"),
        "coverage_matrix_csv": str(output_root / "coverage_matrix.csv"),
        "selection_metadata_json": str(output_root / "selection_metadata.json"),
    }
    _write_json(output_root / "campaign_manifest.json", payload)
    return payload


def summarize_classifier_outputs(args: argparse.Namespace) -> dict[str, Any]:
    campaign_root = Path(args.campaign_root)
    campaign_manifest_path = campaign_root / "campaign_manifest.json"
    if not campaign_manifest_path.exists():
        raise FileNotFoundError(f"Missing campaign manifest: {campaign_manifest_path}")

    campaign_manifest = json.loads(campaign_manifest_path.read_text(encoding="utf-8"))
    execution_manifest_path = Path(campaign_manifest["execution_manifest_csv"])
    if not execution_manifest_path.exists():
        raise FileNotFoundError(f"Missing execution manifest: {execution_manifest_path}")

    classifier_csv = Path(args.classifier_csv)
    if not classifier_csv.exists():
        raise FileNotFoundError(f"Missing classifier csv: {classifier_csv}")

    with execution_manifest_path.open("r", encoding="utf-8", newline="") as handle:
        execution_rows = list(csv.DictReader(handle))
    with classifier_csv.open("r", encoding="utf-8", newline="") as handle:
        classifier_rows = list(csv.DictReader(handle))

    known_signature_keys: set[str] = set()
    if args.known_failures_manifest:
        known_manifest_path = Path(args.known_failures_manifest)
        if known_manifest_path.exists():
            with known_manifest_path.open("r", encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    value = (row.get("expected_signature_key") or "").strip()
                    if value:
                        known_signature_keys.add(value)

    execution_by_case = {row["case_id"]: row for row in execution_rows}
    generated_classifier_rows = [
        row for row in classifier_rows if not row["case_id"].startswith(POSITIVE_CONTROL_CASE_PREFIX)
    ]
    control_classifier_rows = [
        row for row in classifier_rows if row["case_id"].startswith(POSITIVE_CONTROL_CASE_PREFIX)
    ]
    classified_by_case = {row["case_id"]: row for row in generated_classifier_rows}

    expected_controls_by_case: dict[str, dict[str, str]] = {}
    positive_control_manifest_path = campaign_root / "positive_control_manifest.json"
    if positive_control_manifest_path.exists():
        positive_control_manifest = json.loads(
            positive_control_manifest_path.read_text(encoding="utf-8")
        )
        for row in positive_control_manifest.get("controls", []):
            case_id = (row.get("case_id") or "").strip()
            if case_id:
                expected_controls_by_case[case_id] = row

    matched_controls: list[dict[str, Any]] = []
    missing_controls: list[str] = []
    misclassified_controls: list[dict[str, str]] = []
    for case_id, expected in sorted(expected_controls_by_case.items()):
        observed = next((row for row in control_classifier_rows if row["case_id"] == case_id), None)
        if observed is None:
            missing_controls.append(case_id)
            continue

        expected_classification = expected.get("expected_classification", "")
        expected_signature_key = expected.get("expected_signature_key", "")
        classification_match = not expected_classification or (
            observed.get("classification", "") == expected_classification
        )
        signature_match = not expected_signature_key or (
            observed.get("signature_key", "") == expected_signature_key
        )
        non_pass_detected = observed.get("classification", "") != "PASS"

        matched_controls.append(
            {
                "case_id": case_id,
                "expected_classification": expected_classification,
                "observed_classification": observed.get("classification", ""),
                "expected_signature_key": expected_signature_key,
                "observed_signature_key": observed.get("signature_key", ""),
                "non_pass_detected": non_pass_detected,
                "classification_match": classification_match,
                "signature_match": signature_match,
            }
        )
        if not classification_match or not signature_match or not non_pass_detected:
            misclassified_controls.append(
                {
                    "case_id": case_id,
                    "expected_classification": expected_classification,
                    "observed_classification": observed.get("classification", ""),
                    "expected_signature_key": expected_signature_key,
                    "observed_signature_key": observed.get("signature_key", ""),
                }
            )

    controls_expected = len(expected_controls_by_case)
    controls_detected = len(matched_controls)
    control_recall = (
        round(controls_detected / controls_expected, 6) if controls_expected else 1.0
    )
    sensitivity_gate_pass = not missing_controls and not misclassified_controls
    sensitivity_summary = {
        "controls_expected": controls_expected,
        "controls_detected": controls_detected,
        "control_recall": control_recall,
        "missing_controls": missing_controls,
        "misclassified_controls": misclassified_controls,
        "sensitivity_gate_pass": sensitivity_gate_pass,
    }
    _write_json(campaign_root / "positive_control_sensitivity.json", sensitivity_summary)

    composite_by_case: dict[str, dict[str, Any]] = {}
    for row in execution_rows:
        case_id = row["case_id"]
        classifier = classified_by_case.get(case_id)
        classification = (classifier or {}).get("classification", "")
        signature_key = (classifier or {}).get("signature_key", "")
        classifier_non_pass = bool(classification and classification != "PASS")
        oracle_status = (row.get("oracle_status") or "").strip().lower()
        oracle_flags = [flag for flag in (row.get("oracle_flags") or "").split("|") if flag]
        oracle_non_pass = oracle_status == "flag"
        composite_non_pass = classifier_non_pass or oracle_non_pass
        reason_codes: list[str] = []
        if classifier_non_pass:
            reason_codes.append("signature_non_pass")
        if oracle_non_pass:
            reason_codes.append("oracle_flag")
        composite_by_case[case_id] = {
            "classification": classification,
            "signature_key": signature_key,
            "oracle_status": oracle_status,
            "oracle_flags": oracle_flags,
            "composite_non_pass": composite_non_pass,
            "composite_reason_codes": reason_codes,
        }

    composite_rows: list[dict[str, Any]] = []
    for row in execution_rows:
        composite = composite_by_case[row["case_id"]]
        composite_rows.append(
            {
                "case_id": row["case_id"],
                "seed_id": row["seed_id"],
                "run_id": row["run_id"],
                "climate_bin": row["climate_bin"],
                "slope_bin": row["slope_bin"],
                "mutation_profile_id": row.get("mutation_profile_id", ""),
                "adaptive_score": row.get("adaptive_score", ""),
                "classification": composite["classification"],
                "signature_key": composite["signature_key"],
                "oracle_status": composite["oracle_status"],
                "oracle_flags": "|".join(composite["oracle_flags"]),
                "composite_non_pass": "1" if composite["composite_non_pass"] else "0",
                "composite_reason_codes": "|".join(composite["composite_reason_codes"]),
            }
        )
    _write_csv(
        campaign_root / "composite_case_disposition.csv",
        rows=composite_rows,
        fieldnames=[
            "case_id",
            "seed_id",
            "run_id",
            "climate_bin",
            "slope_bin",
            "mutation_profile_id",
            "adaptive_score",
            "classification",
            "signature_key",
            "oracle_status",
            "oracle_flags",
            "composite_non_pass",
            "composite_reason_codes",
        ],
    )

    cluster_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in generated_classifier_rows:
        cluster_groups[row["signature_key"]].append(row)

    clusters: list[dict[str, Any]] = []
    for signature_key, rows in cluster_groups.items():
        sample = rows[0]
        case_ids = sorted(row["case_id"] for row in rows)
        bin_pairs = sorted(
            {
                (
                    execution_by_case[row["case_id"]]["climate_bin"],
                    execution_by_case[row["case_id"]]["slope_bin"],
                )
                for row in rows
                if row["case_id"] in execution_by_case
            }
        )
        clusters.append(
            {
                "signature_key": signature_key,
                "classification": sample["classification"],
                "signal_class": sample["signal_class"],
                "top_frame": sample["top_frame"],
                "last_marker_tag": sample["last_marker_tag"],
                "frequency": len(rows),
                "novel_signature": signature_key not in known_signature_keys,
                "case_ids": case_ids,
                "bin_pairs": [f"{climate}:{slope}" for climate, slope in bin_pairs],
            }
        )

    clusters.sort(
        key=lambda row: (
            int(row["novel_signature"]),
            row["frequency"],
            row["classification"],
            row["signature_key"],
        ),
        reverse=True,
    )

    boundary_queue: list[dict[str, Any]] = []
    for cluster in clusters:
        if cluster["classification"] == "PASS":
            continue
        case_id = cluster["case_ids"][0]
        execution = execution_by_case.get(case_id)
        if execution is None:
            continue
        case_dir = Path(execution["case_dir"])
        repro_cmd = (
            f"cd {case_dir}/execution/workspace/runs && "
            f"{campaign_manifest['wepp_binary']} < {execution['stem']}.run > rerun.log 2>&1"
        )
        boundary_queue.append(
            {
                "priority_rank": len(boundary_queue) + 1,
                "signature_key": cluster["signature_key"],
                "classification": cluster["classification"],
                "frequency": cluster["frequency"],
                "novel_signature": cluster["novel_signature"],
                "top_frame": cluster["top_frame"],
                "example_case_id": case_id,
                "example_seed_id": execution["seed_id"],
                "example_run_id": execution["run_id"],
                "example_climate_bin": execution["climate_bin"],
                "example_slope_bin": execution["slope_bin"],
                "mutation_profile_id": execution.get("mutation_profile_id", ""),
                "adaptive_score": execution.get("adaptive_score", ""),
                "example_case_dir": execution["case_dir"],
                "repro_command": repro_cmd,
                "no_action_reason": "",
                "oracle_flags": [],
            }
        )

    oracle_only_cases = [
        row for row in execution_rows if composite_by_case[row["case_id"]]["oracle_status"] == "flag"
    ]
    oracle_only_cases.sort(key=lambda row: row["case_id"])
    for oracle_case in oracle_only_cases:
        if any(item["example_case_id"] == oracle_case["case_id"] for item in boundary_queue):
            continue
        boundary_queue.append(
            {
                "priority_rank": len(boundary_queue) + 1,
                "signature_key": composite_by_case[oracle_case["case_id"]]["signature_key"] or "ORACLE_ONLY",
                "classification": composite_by_case[oracle_case["case_id"]]["classification"] or "PASS",
                "frequency": 1,
                "novel_signature": False,
                "top_frame": "ORACLE_ONLY",
                "example_case_id": oracle_case["case_id"],
                "example_seed_id": oracle_case["seed_id"],
                "example_run_id": oracle_case["run_id"],
                "example_climate_bin": oracle_case["climate_bin"],
                "example_slope_bin": oracle_case["slope_bin"],
                "mutation_profile_id": oracle_case.get("mutation_profile_id", ""),
                "adaptive_score": oracle_case.get("adaptive_score", ""),
                "example_case_dir": oracle_case["case_dir"],
                "repro_command": (
                    f"cd {oracle_case['case_dir']}/execution/workspace/runs && "
                    f"{campaign_manifest['wepp_binary']} < {oracle_case['stem']}.run > rerun.log 2>&1"
                ),
                "no_action_reason": "",
                "oracle_flags": composite_by_case[oracle_case["case_id"]]["oracle_flags"],
            }
        )

    if not boundary_queue and clusters:
        top_cluster = clusters[0]
        top_case_id = top_cluster["case_ids"][0] if top_cluster["case_ids"] else ""
        top_execution = execution_by_case.get(top_case_id) if top_case_id else None
        if top_execution is not None:
            boundary_queue.append(
                {
                    "priority_rank": 1,
                    "signature_key": top_cluster["signature_key"],
                    "classification": top_cluster["classification"],
                    "frequency": top_cluster["frequency"],
                    "novel_signature": top_cluster["novel_signature"],
                    "top_frame": top_cluster["top_frame"],
                    "example_case_id": top_case_id,
                    "example_seed_id": top_execution["seed_id"],
                    "example_run_id": top_execution["run_id"],
                    "example_climate_bin": top_execution["climate_bin"],
                    "example_slope_bin": top_execution["slope_bin"],
                    "mutation_profile_id": top_execution.get("mutation_profile_id", ""),
                    "adaptive_score": top_execution.get("adaptive_score", ""),
                    "example_case_dir": top_execution["case_dir"],
                    "repro_command": (
                        f"cd {top_execution['case_dir']}/execution/workspace/runs && "
                        f"{campaign_manifest['wepp_binary']} < {top_execution['stem']}.run > rerun.log 2>&1"
                    ),
                    "no_action_reason": "No non-pass signatures observed in this campaign.",
                    "oracle_flags": [],
                }
            )

    for idx, item in enumerate(boundary_queue, start=1):
        item["priority_rank"] = idx

    coverage_rows = []
    confidence_bins: dict[str, dict[str, Any]] = {}
    composite_non_pass_total = 0
    oracle_flag_total = 0
    oracle_indeterminate_total = 0
    for climate_bin, slope_bin in REQUIRED_BIN_KEYS:
        bin_execution_rows = [
            row
            for row in execution_rows
            if row["climate_bin"] == climate_bin and row["slope_bin"] == slope_bin
        ]
        seed_count = int(
            campaign_manifest["stratification"]["seed_count_by_bin"][f"{climate_bin}:{slope_bin}"]
        )
        selected_count = int(
            campaign_manifest["stratification"]["selected_count_by_bin"][
                f"{climate_bin}:{slope_bin}"
            ]
        )
        executed_count = sum(1 for row in bin_execution_rows if row["execution_status"] == "executed")
        hard_fail_count = sum(1 for row in bin_execution_rows if row["execution_status"] != "executed")

        signature_keys = {
            classified_by_case[row["case_id"]]["signature_key"]
            for row in bin_execution_rows
            if row["case_id"] in classified_by_case
        }

        composite_non_pass_count = sum(
            1 for row in bin_execution_rows if composite_by_case[row["case_id"]]["composite_non_pass"]
        )
        oracle_flag_count = sum(
            1 for row in bin_execution_rows if composite_by_case[row["case_id"]]["oracle_status"] == "flag"
        )
        oracle_indeterminate_count = sum(
            1
            for row in bin_execution_rows
            if composite_by_case[row["case_id"]]["oracle_status"] == "indeterminate"
        )

        composite_non_pass_total += composite_non_pass_count
        oracle_flag_total += oracle_flag_count
        oracle_indeterminate_total += oracle_indeterminate_count

        coverage_rows.append(
            {
                "climate_bin": climate_bin,
                "slope_bin": slope_bin,
                "seed_count": seed_count,
                "selected_count": selected_count,
                "executed_count": executed_count,
                "hard_fail_count": hard_fail_count,
                "signature_count": len(signature_keys),
                "composite_non_pass_count": composite_non_pass_count,
                "oracle_flag_count": oracle_flag_count,
                "oracle_indeterminate_count": oracle_indeterminate_count,
            }
        )
        confidence_bins[f"{climate_bin}:{slope_bin}"] = {
            "executed_count": executed_count,
            "composite_non_pass_count": composite_non_pass_count,
            "upper_bound_95": (
                _upper_bound(0.05, executed_count)
                if composite_non_pass_count == 0
                else None
            ),
            "upper_bound_99": (
                _upper_bound(0.01, executed_count)
                if composite_non_pass_count == 0
                else None
            ),
        }

    overall_executed = sum(1 for row in execution_rows if row["execution_status"] == "executed")
    coverage_target_met = all(
        int(
            campaign_manifest["stratification"]["selected_count_by_bin"][f"{climate}:{slope}"]
        )
        >= int(campaign_manifest["per_bin_quota"])
        for climate, slope in REQUIRED_BIN_KEYS
    )
    minimum_case_target_met = len(execution_rows) >= int(args.minimum_case_count)
    oracle_indeterminate_rate = (
        oracle_indeterminate_total / len(execution_rows) if execution_rows else 1.0
    )
    overall_upper_95 = (
        _upper_bound(0.05, overall_executed) if composite_non_pass_total == 0 else None
    )
    overall_upper_99 = (
        _upper_bound(0.01, overall_executed) if composite_non_pass_total == 0 else None
    )

    if not sensitivity_gate_pass or not minimum_case_target_met or not coverage_target_met:
        disposition = "Inconclusive"
    elif oracle_indeterminate_rate > args.oracle_indeterminate_rate_limit:
        disposition = "Inconclusive"
    elif composite_non_pass_total > 0:
        disposition = "Boundary Yield Achieved"
    elif overall_upper_95 is not None and overall_upper_95 <= 0.005:
        disposition = "Calibrated Stable (provisional)"
    else:
        disposition = "Inconclusive"

    confidence_summary = {
        "overall": {
            "executed_count": overall_executed,
            "composite_non_pass_count": composite_non_pass_total,
            "oracle_flag_count": oracle_flag_total,
            "oracle_indeterminate_count": oracle_indeterminate_total,
            "oracle_indeterminate_rate": round(oracle_indeterminate_rate, 6),
            "upper_bound_95": overall_upper_95,
            "upper_bound_99": overall_upper_99,
        },
        "per_bin": confidence_bins,
        "inputs": {
            "minimum_case_count": int(args.minimum_case_count),
            "coverage_target_met": coverage_target_met,
            "minimum_case_target_met": minimum_case_target_met,
            "sensitivity_gate_pass": sensitivity_gate_pass,
            "oracle_indeterminate_rate_limit": args.oracle_indeterminate_rate_limit,
            "formula": "1 - alpha^(1/N)",
        },
        "disposition": disposition,
    }
    _write_json(campaign_root / "confidence_summary.json", confidence_summary)

    _write_json(campaign_root / "signature_clusters.json", clusters)
    _write_json(campaign_root / "boundary_queue.json", boundary_queue)
    _write_csv(
        campaign_root / "boundary_queue.csv",
        rows=boundary_queue,
        fieldnames=[
            "priority_rank",
            "signature_key",
            "classification",
            "frequency",
            "novel_signature",
            "top_frame",
            "example_case_id",
            "example_seed_id",
            "example_run_id",
            "example_climate_bin",
            "example_slope_bin",
            "mutation_profile_id",
            "adaptive_score",
            "example_case_dir",
            "repro_command",
            "no_action_reason",
            "oracle_flags",
        ],
    )
    _write_csv(
        campaign_root / "coverage_matrix.csv",
        rows=coverage_rows,
        fieldnames=[
            "climate_bin",
            "slope_bin",
            "seed_count",
            "selected_count",
            "executed_count",
            "hard_fail_count",
            "signature_count",
            "composite_non_pass_count",
            "oracle_flag_count",
            "oracle_indeterminate_count",
        ],
    )

    summary = {
        "campaign_root": str(campaign_root),
        "cluster_count": len(clusters),
        "non_pass_cluster_count": sum(1 for row in clusters if row["classification"] != "PASS"),
        "boundary_queue_count": len(boundary_queue),
        "composite_non_pass_count": composite_non_pass_total,
        "sensitivity_gate_pass": sensitivity_gate_pass,
        "controls_expected": controls_expected,
        "controls_detected": controls_detected,
        "misclassified_controls": len(misclassified_controls),
        "missing_controls": len(missing_controls),
        "oracle_flag_count": oracle_flag_total,
        "oracle_indeterminate_count": oracle_indeterminate_total,
        "confidence_disposition": disposition,
        "coverage_matrix_csv": str(campaign_root / "coverage_matrix.csv"),
        "signature_clusters_json": str(campaign_root / "signature_clusters.json"),
        "boundary_queue_json": str(campaign_root / "boundary_queue.json"),
        "boundary_queue_csv": str(campaign_root / "boundary_queue.csv"),
        "positive_control_sensitivity_json": str(campaign_root / "positive_control_sensitivity.json"),
        "confidence_summary_json": str(campaign_root / "confidence_summary.json"),
        "composite_case_disposition_csv": str(campaign_root / "composite_case_disposition.csv"),
    }
    _write_json(campaign_root / "campaign_summary.json", summary)
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Milestone 3 single-OFE stratified campaign tooling."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run preflight + stratified sharded campaign.")
    run_parser.add_argument("--run-root", default="/wc1/runs")
    run_parser.add_argument("--output-root", required=True)
    run_parser.add_argument("--catalog-map", default=None)
    run_parser.add_argument("--max-run-dirs", type=int, default=None)
    run_parser.add_argument(
        "--preflight-cache-json",
        default="",
        help=(
            "Optional path to a preflight_manifest.json from a prior run. "
            "When provided, skips /wc1/runs discovery and reuses eligible/quarantine inventory."
        ),
    )
    run_parser.add_argument("--per-bin-quota", type=int, default=12)
    run_parser.add_argument("--target-case-count", type=int, default=216)
    run_parser.add_argument(
        "--target-slice",
        default="",
        help=(
            "Optional targeted mode selector formatted as "
            "climate_bin:slope_bin:mutation_profile_id."
        ),
    )
    run_parser.add_argument("--shard-count", type=int, default=6)
    run_parser.add_argument("--generator-seed", type=int, default=DEFAULT_GENERATOR_SEED)
    run_parser.add_argument("--stratification-seed", type=int, default=20260422)
    run_parser.add_argument("--shard-seed", type=int, default=20260423)
    run_parser.add_argument(
        "--prior-campaign-root",
        default="/home/workdir/wepp-forest/generative-inputs-fuzzing/results/milestone3_single_ofe_campaign",
    )
    run_parser.add_argument(
        "--known-failures-manifest",
        default="/home/workdir/wepp-forest/generative-inputs-fuzzing/seeds/milestone0_known_failures.csv",
    )
    run_parser.add_argument(
        "--positive-controls-manifest",
        default="/home/workdir/wepp-forest/generative-inputs-fuzzing/seeds/milestone0_known_failures.csv",
    )
    run_parser.add_argument("--oversample-warning-weight", type=float, default=0.55)
    run_parser.add_argument("--oversample-non-pass-weight", type=float, default=1.5)
    run_parser.add_argument("--oversample-novel-weight", type=float, default=1.75)
    run_parser.add_argument("--oversample-dry-wet-corner-weight", type=float, default=0.6)
    run_parser.add_argument(
        "--oversample-gradual-steep-corner-weight", type=float, default=0.6
    )
    run_parser.add_argument("--profile-weight-p1", type=float, default=1.0)
    run_parser.add_argument("--profile-weight-p2", type=float, default=1.0)
    run_parser.add_argument("--profile-weight-p3", type=float, default=1.2)
    run_parser.add_argument("--profile-weight-p4", type=float, default=1.0)
    run_parser.add_argument("--profile-weight-p5", type=float, default=1.15)
    run_parser.add_argument("--profile-floor-count", type=int, default=6)
    run_parser.add_argument(
        "--policy-era-producer-obligation-strict",
        action="store_true",
        help=(
            "Fail preflight manifest generation when quarantine reason codes cannot be "
            "mapped to deterministic producer-obligation contract rows."
        ),
    )
    run_parser.add_argument("--wepp-binary", default="/workdir/wepppy/wepp_runner/bin/latest")
    run_parser.add_argument("--execution-timeout-seconds", type=int, default=180)

    summarize_parser = subparsers.add_parser(
        "summarize", help="Summarize classifier outputs into clusters/queue/coverage."
    )
    summarize_parser.add_argument("--campaign-root", required=True)
    summarize_parser.add_argument("--classifier-csv", required=True)
    summarize_parser.add_argument("--known-failures-manifest", default=None)
    summarize_parser.add_argument("--minimum-case-count", type=int, default=1000)
    summarize_parser.add_argument("--oracle-indeterminate-rate-limit", type=float, default=0.05)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "run":
        payload = run_campaign(args)
    else:
        payload = summarize_classifier_outputs(args)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
