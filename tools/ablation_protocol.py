#!/usr/bin/env python3
"""Initialize and finalize WEPP ablation incident packages."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

TEMPLATE_MAP = {
    "TEMPLATE_incident.md": "incident.md",
    "TEMPLATE_notes.md": "notes.md",
    "TEMPLATE_matrix.csv": "matrix.csv",
    "TEMPLATE_artifacts.md": "artifacts/README.md",
}

MANIFEST_HEADER = [
    "artifact_id",
    "case_id",
    "artifact_type",
    "relative_path",
    "description",
    "produced_by",
    "created_utc",
]

CASE_ID_RE = re.compile(r"(C\d{3,})")
CONTRACT_ID_RE = re.compile(r"^SC-[A-Z]+-\d{3}$")
INVARIANT_ID_RE = re.compile(r"^INV-[A-Z]+-\d{3}$")
CONTRACT_REF_RE = re.compile(r"^SC-[A-Z]+-\d{3}#INV-[A-Z]+-\d{3}$")
INCIDENT_STATUS_RE = re.compile(r"^-\s*`status`:\s*`([^`]+)`\s*$", re.MULTILINE)
INCIDENT_SCOPE_RE = re.compile(r"^-\s*`scope`:\s*`([^`]+)`\s*$", re.MULTILINE)
UPSTREAM_CONTRACT_COLUMNS = [
    "contract_refs",
    "boundary_disposition",
]
SCIENCE_BOUNDARY_DISPOSITIONS = {
    "invalid_input",
    "inactive_process",
    "valid_extreme",
    "neutral_branch",
    "bounded_transition",
    "model_gap",
    "requires_scientific_review",
}
UPSTREAM_GAP_DISPOSITIONS = {
    "model_gap",
    "requires_scientific_review",
}
EMPTY_CONTRACT_VALUES = {
    "",
    "none",
    "na",
    "n/a",
}
UPSTREAM_CONTRACT_ENFORCEMENT_DATE = 20260428
WATERSHED_DURABILITY_COLUMNS = [
    "durability_lane",
    "configured_simulation_years",
    "simulated_years_completed",
]
WATERSHED_RESOLVED_STATUSES = {"resolved", "resolved-and-hardened", "closed"}
WATERSHED_DURABILITY_ENFORCEMENT_DATE = 20260428
CONTRACT_OBSERVATION_COLUMNS = [
    "case_id",
    "contract_id",
    "invariant_id",
    "contract_ref",
    "status",
    "observed_value",
    "disposition",
    "evidence_path",
    "notes",
]
CONTRACT_OBSERVATION_STATUSES = {
    "satisfied",
    "violated_expected",
    "violated_unexpected",
    "not_applicable",
    "not_observed",
}
CONTRACT_OBSERVATION_RELATIVE_PATH = Path("artifacts/logs/contract_observations.csv")
CONTRACT_OBSERVATION_ENFORCEMENT_DATE = 20260428


@dataclass(frozen=True)
class ManifestRow:
    artifact_id: str
    case_id: str
    artifact_type: str
    relative_path: str
    description: str
    produced_by: str
    created_utc: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default="docs/ablation",
        help="Ablation docs root (default: docs/ablation).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create an incident package from templates.")
    init_parser.add_argument("--incident-id", required=True, help="Incident directory name.")
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Allow writing into an existing incident directory.",
    )

    finalize_parser = subparsers.add_parser(
        "finalize",
        help="Regenerate artifacts manifest and checksums for an incident package.",
    )
    finalize_parser.add_argument("--incident-id", required=True, help="Incident directory name.")
    finalize_parser.add_argument(
        "--produced-by",
        default="tools/ablation_protocol.py finalize",
        help="Value written to manifest produced_by column.",
    )

    return parser.parse_args()


def resolve_ablation_root(root_arg: str) -> Path:
    root = Path(root_arg).expanduser()
    if root.is_absolute():
        return root.resolve()
    return (Path.cwd() / root).resolve()


def ensure_templates_exist(ablation_root: Path) -> None:
    missing = [name for name in TEMPLATE_MAP if not (ablation_root / name).is_file()]
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise FileNotFoundError(f"Missing template files in {ablation_root}: {missing_text}")


def init_incident_package(ablation_root: Path, incident_id: str, force: bool = False) -> Path:
    ensure_templates_exist(ablation_root)

    incident_dir = (ablation_root / incident_id).resolve()
    artifacts_dir = incident_dir / "artifacts"
    manifest_path = artifacts_dir / "manifest.csv"
    checksums_path = artifacts_dir / "checksums.sha256"

    if incident_dir.exists() and any(incident_dir.iterdir()) and not force:
        raise FileExistsError(
            f"Incident directory already exists and is not empty: {incident_dir} (use --force to overwrite files)"
        )

    for subdir in ("logs", "diffs", "repro", "env"):
        (artifacts_dir / subdir).mkdir(parents=True, exist_ok=True)

    for template_name, relative_destination in TEMPLATE_MAP.items():
        src = ablation_root / template_name
        dst = incident_dir / relative_destination
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and not force:
            continue
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    if force or not manifest_path.exists():
        with manifest_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(MANIFEST_HEADER)

    if force or not checksums_path.exists():
        checksums_path.write_text("", encoding="utf-8")

    return incident_dir


def detect_case_id(relative_path: str) -> str:
    match = CASE_ID_RE.search(relative_path)
    if match:
        return match.group(1)
    return "GLOBAL"


def classify_artifact_type(relative_path: str) -> str:
    normalized = relative_path.lower()

    if normalized.startswith("artifacts/logs/"):
        if ".tail" in normalized:
            return "tail"
        if "stderr" in normalized or normalized.endswith(".err"):
            return "stderr"
        if "stdout" in normalized or normalized.endswith(".out"):
            return "stdout"
        if "command" in normalized:
            return "command_log"
        return "other"

    if normalized.startswith("artifacts/diffs/"):
        return "diff"
    if normalized.startswith("artifacts/repro/"):
        return "repro_input"
    if normalized.startswith("artifacts/env/"):
        return "env_capture"
    return "other"


def gather_artifact_files(artifacts_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for subdir_name in ("logs", "diffs", "repro", "env"):
        subdir = artifacts_dir / subdir_name
        if not subdir.is_dir():
            continue
        for path in subdir.rglob("*"):
            if path.is_file():
                paths.append(path)
    return sorted(paths)


def build_manifest_rows(
    *,
    incident_dir: Path,
    artifact_files: list[Path],
    produced_by: str,
) -> list[ManifestRow]:
    rows: list[ManifestRow] = []
    for index, artifact_path in enumerate(artifact_files, start=1):
        relative_path = artifact_path.relative_to(incident_dir).as_posix()
        created_utc = datetime.fromtimestamp(
            artifact_path.stat().st_mtime,
            tz=timezone.utc,
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows.append(
            ManifestRow(
                artifact_id=f"A{index:04d}",
                case_id=detect_case_id(relative_path),
                artifact_type=classify_artifact_type(relative_path),
                relative_path=relative_path,
                description=f"Auto-indexed artifact: {relative_path}",
                produced_by=produced_by,
                created_utc=created_utc,
            )
        )
    return rows


def write_manifest(manifest_path: Path, rows: list[ManifestRow]) -> None:
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(MANIFEST_HEADER)
        for row in rows:
            writer.writerow(
                [
                    row.artifact_id,
                    row.case_id,
                    row.artifact_type,
                    row.relative_path,
                    row.description,
                    row.produced_by,
                    row.created_utc,
                ]
            )


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksums(incident_dir: Path, checksums_path: Path) -> int:
    targets = sorted(
        path
        for path in incident_dir.rglob("*")
        if path.is_file() and path != checksums_path
    )
    with checksums_path.open("w", encoding="utf-8") as handle:
        for target in targets:
            checksum = compute_sha256(target)
            relative = target.relative_to(incident_dir).as_posix()
            handle.write(f"{checksum}  {relative}\n")
    return len(targets)


def read_incident_metadata(incident_md_path: Path) -> tuple[str | None, str | None]:
    if not incident_md_path.is_file():
        return None, None
    text = incident_md_path.read_text(encoding="utf-8", errors="replace")
    status_match = INCIDENT_STATUS_RE.search(text)
    scope_match = INCIDENT_SCOPE_RE.search(text)
    status = status_match.group(1).strip().lower() if status_match else None
    scope = scope_match.group(1).strip().lower() if scope_match else None
    return status, scope


def is_watershed_incident(incident_id: str, scope: str | None) -> bool:
    if scope in {"watershed", "mixed"}:
        return True
    return "_watershed_" in incident_id.lower()


def parse_incident_date_token(incident_id: str) -> int | None:
    token = incident_id[:8]
    if len(token) != 8 or not token.isdigit():
        return None
    return int(token)


def is_policy_era_incident(incident_id: str, enforcement_date: int) -> bool:
    incident_date = parse_incident_date_token(incident_id)
    return incident_date is None or incident_date >= enforcement_date


def parse_matrix_year_value(value: str, *, field: str, row_label: str) -> int:
    text = value.strip()
    if not text:
        raise ValueError(f"{row_label}: missing {field}")
    if not text.isdigit():
        raise ValueError(f"{row_label}: non-integer {field} value={text!r}")
    parsed = int(text)
    if parsed < 0:
        raise ValueError(f"{row_label}: negative {field} value={text!r}")
    return parsed


def parse_contract_refs(value: str, *, row_label: str) -> list[str]:
    raw_value = value.strip()
    if raw_value.lower() in EMPTY_CONTRACT_VALUES:
        return []

    refs = [part.strip() for part in raw_value.split(";") if part.strip()]
    for contract_ref in refs:
        if not CONTRACT_REF_RE.fullmatch(contract_ref):
            raise ValueError(
                f"{row_label}: invalid contract_ref={contract_ref!r} "
                "(expected SC-<DOMAIN>-<NNN>#INV-<DOMAIN>-<NNN>)"
            )
    return refs


def validate_upstream_contract_matrix(incident_dir: Path, incident_id: str) -> None:
    matrix_path = incident_dir / "matrix.csv"
    if not matrix_path.is_file():
        return

    with matrix_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        if "lane_id" not in fieldnames:
            return
        rows = list(reader)

    upstream_rows = [
        (row_index, row)
        for row_index, row in enumerate(rows, start=2)
        if row.get("lane_id", "").strip().upper().startswith("U")
    ]
    if not upstream_rows:
        return

    missing = [name for name in UPSTREAM_CONTRACT_COLUMNS if name not in fieldnames]
    if missing and is_policy_era_incident(incident_id, UPSTREAM_CONTRACT_ENFORCEMENT_DATE):
        missing_text = ", ".join(missing)
        raise ValueError(
            f"{matrix_path}: upstream mutation contract columns are required for U* lanes: {missing_text}"
        )
    if missing:
        return

    for row_index, row in upstream_rows:
        row_label = f"{matrix_path}:{row_index}"
        disposition = row["boundary_disposition"].strip().lower()
        if disposition in EMPTY_CONTRACT_VALUES:
            raise ValueError(f"{row_label}: U* lane requires boundary_disposition")
        if disposition not in SCIENCE_BOUNDARY_DISPOSITIONS:
            allowed = "|".join(sorted(SCIENCE_BOUNDARY_DISPOSITIONS))
            raise ValueError(
                f"{row_label}: invalid boundary_disposition={disposition!r} "
                f"(expected one of {allowed})"
            )

        contract_refs = parse_contract_refs(row["contract_refs"], row_label=row_label)
        if contract_refs:
            continue
        if disposition in UPSTREAM_GAP_DISPOSITIONS:
            continue

        raise ValueError(
            f"{row_label}: U* lane requires contract_refs or "
            "boundary_disposition=model_gap|requires_scientific_review"
        )


def validate_watershed_durability_matrix(incident_dir: Path, incident_id: str) -> None:
    matrix_path = incident_dir / "matrix.csv"
    status, scope = read_incident_metadata(incident_dir / "incident.md")
    if not is_watershed_incident(incident_id, scope):
        return
    if not matrix_path.is_file():
        raise FileNotFoundError(f"Missing matrix.csv: {matrix_path}")

    with matrix_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [name for name in WATERSHED_DURABILITY_COLUMNS if name not in fieldnames]
        requires_strict_columns = is_policy_era_incident(incident_id, WATERSHED_DURABILITY_ENFORCEMENT_DATE)
        if missing and requires_strict_columns:
            missing_text = ", ".join(missing)
            raise ValueError(
                f"{matrix_path}: watershed durability metadata columns are required: {missing_text}"
            )
        if missing:
            return
        rows = list(reader)

    decisive_pass_rows = 0
    for row_index, row in enumerate(rows, start=2):
        row_label = f"{matrix_path}:{row_index}"
        durability_lane = row["durability_lane"].strip().lower()
        pass_fail = row.get("pass_fail", "").strip().upper()

        if durability_lane in {"", "na", "n/a"}:
            continue
        if durability_lane not in {"decisive", "exploratory"}:
            raise ValueError(
                f"{row_label}: invalid durability_lane={durability_lane!r} "
                "(expected decisive|exploratory|na)"
            )

        configured_years = parse_matrix_year_value(
            row["configured_simulation_years"],
            field="configured_simulation_years",
            row_label=row_label,
        )
        if configured_years <= 0:
            raise ValueError(f"{row_label}: configured_simulation_years must be > 0")
        simulated_years = parse_matrix_year_value(
            row["simulated_years_completed"],
            field="simulated_years_completed",
            row_label=row_label,
        )

        if pass_fail == "PASS" and durability_lane == "decisive" and simulated_years < configured_years:
            raise ValueError(
                f"{row_label}: decisive PASS lane requires full period completion "
                f"(simulated={simulated_years}, configured={configured_years})"
            )
        if pass_fail == "PASS" and durability_lane == "decisive" and simulated_years >= configured_years:
            decisive_pass_rows += 1

    if status in WATERSHED_RESOLVED_STATUSES and decisive_pass_rows == 0:
        raise ValueError(
            f"{matrix_path}: status={status!r} requires at least one decisive PASS row "
            "with full configured-period completion"
        )


def requires_contract_observations(incident_dir: Path, incident_id: str) -> bool:
    if not is_policy_era_incident(incident_id, CONTRACT_OBSERVATION_ENFORCEMENT_DATE):
        return False

    matrix_path = incident_dir / "matrix.csv"
    if not matrix_path.is_file():
        return False

    with matrix_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        if "lane_id" not in fieldnames:
            return False
        return any(
            row.get("lane_id", "").strip().upper().startswith("U")
            for row in reader
        )


def validate_contract_observations_artifact(incident_dir: Path, incident_id: str) -> None:
    observations_path = incident_dir / CONTRACT_OBSERVATION_RELATIVE_PATH
    observations_required = requires_contract_observations(incident_dir, incident_id)
    strict_policy = is_policy_era_incident(incident_id, CONTRACT_OBSERVATION_ENFORCEMENT_DATE)

    if observations_required and not observations_path.is_file():
        raise FileNotFoundError(
            "Missing required contract observations artifact for policy-era U* lanes: "
            f"{observations_path}"
        )
    if not observations_path.is_file() or not strict_policy:
        return

    with observations_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [name for name in CONTRACT_OBSERVATION_COLUMNS if name not in fieldnames]
        if missing:
            missing_text = ", ".join(missing)
            raise ValueError(
                f"{observations_path}: missing contract observation columns: {missing_text}"
            )
        rows = list(reader)

    if observations_required and not rows:
        raise ValueError(
            f"{observations_path}: policy-era U* lane requires at least one observation row"
        )

    for row_index, row in enumerate(rows, start=2):
        row_label = f"{observations_path}:{row_index}"

        case_id = row["case_id"].strip()
        if not case_id:
            raise ValueError(f"{row_label}: missing case_id")

        contract_id = row["contract_id"].strip()
        if not CONTRACT_ID_RE.fullmatch(contract_id):
            raise ValueError(
                f"{row_label}: invalid contract_id={contract_id!r} "
                "(expected SC-<DOMAIN>-<NNN>)"
            )

        invariant_id = row["invariant_id"].strip()
        if not INVARIANT_ID_RE.fullmatch(invariant_id):
            raise ValueError(
                f"{row_label}: invalid invariant_id={invariant_id!r} "
                "(expected INV-<DOMAIN>-<NNN>)"
            )

        contract_ref = row["contract_ref"].strip()
        if not CONTRACT_REF_RE.fullmatch(contract_ref):
            raise ValueError(
                f"{row_label}: invalid contract_ref={contract_ref!r} "
                "(expected SC-<DOMAIN>-<NNN>#INV-<DOMAIN>-<NNN>)"
            )

        expected_contract_ref = f"{contract_id}#{invariant_id}"
        if contract_ref != expected_contract_ref:
            raise ValueError(
                f"{row_label}: contract_ref mismatch "
                f"(expected {expected_contract_ref!r}, got {contract_ref!r})"
            )

        status = row["status"].strip().lower()
        if status not in CONTRACT_OBSERVATION_STATUSES:
            allowed_statuses = "|".join(sorted(CONTRACT_OBSERVATION_STATUSES))
            raise ValueError(
                f"{row_label}: invalid status={status!r} "
                f"(expected one of {allowed_statuses})"
            )

        disposition = row["disposition"].strip().lower()
        if not disposition:
            raise ValueError(f"{row_label}: missing disposition")
        if disposition not in SCIENCE_BOUNDARY_DISPOSITIONS:
            allowed_dispositions = "|".join(sorted(SCIENCE_BOUNDARY_DISPOSITIONS))
            raise ValueError(
                f"{row_label}: invalid disposition={disposition!r} "
                f"(expected one of {allowed_dispositions})"
            )

        evidence_path = row["evidence_path"].strip()
        if not evidence_path:
            raise ValueError(f"{row_label}: missing evidence_path")


def finalize_incident_package(ablation_root: Path, incident_id: str, produced_by: str) -> tuple[int, int, Path]:
    incident_dir = (ablation_root / incident_id).resolve()
    artifacts_dir = incident_dir / "artifacts"
    manifest_path = artifacts_dir / "manifest.csv"
    checksums_path = artifacts_dir / "checksums.sha256"

    if not incident_dir.is_dir():
        raise FileNotFoundError(f"Incident directory not found: {incident_dir}")
    if not artifacts_dir.is_dir():
        raise FileNotFoundError(f"Missing artifacts directory: {artifacts_dir}")

    validate_watershed_durability_matrix(incident_dir, incident_id)
    validate_upstream_contract_matrix(incident_dir, incident_id)
    validate_contract_observations_artifact(incident_dir, incident_id)

    artifact_files = gather_artifact_files(artifacts_dir)
    rows = build_manifest_rows(
        incident_dir=incident_dir,
        artifact_files=artifact_files,
        produced_by=produced_by,
    )
    write_manifest(manifest_path, rows)
    checksum_count = write_checksums(incident_dir, checksums_path)

    return len(rows), checksum_count, incident_dir


def main() -> int:
    args = parse_args()
    ablation_root = resolve_ablation_root(args.root)

    if args.command == "init":
        incident_dir = init_incident_package(
            ablation_root=ablation_root,
            incident_id=args.incident_id,
            force=bool(args.force),
        )
        print(f"Initialized incident package: {incident_dir}")
        return 0

    if args.command == "finalize":
        row_count, checksum_count, incident_dir = finalize_incident_package(
            ablation_root=ablation_root,
            incident_id=args.incident_id,
            produced_by=args.produced_by,
        )
        print(
            f"Finalized incident package: {incident_dir} "
            f"(manifest_rows={row_count}, checksummed_files={checksum_count})"
        )
        return 0

    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
