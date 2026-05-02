from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "ablation_protocol.py"
SPEC = importlib.util.spec_from_file_location("ablation_protocol", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load ablation_protocol module")
ablation_protocol = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ablation_protocol
SPEC.loader.exec_module(ablation_protocol)


def seed_templates(ablation_root: Path) -> None:
    ablation_root.mkdir(parents=True, exist_ok=True)
    for src, dst in ablation_protocol.TEMPLATE_MAP.items():
        (ablation_root / src).write_text(f"template::{dst}\n", encoding="utf-8")


def write_matrix(path: Path, header: list[str], row: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerow(row)


def write_contract_observations(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(ablation_protocol.CONTRACT_OBSERVATION_COLUMNS)
        writer.writerows(rows)


def build_observation_row(
    *,
    case_id: str = "C110",
    contract_id: str = "SC-WATBAL-001",
    invariant_id: str = "INV-WATBAL-002",
    status: str = "satisfied",
    observed_value: str = "ratio=0.1",
    disposition: str = "valid_extreme",
    evidence_path: str = "artifacts/logs/C110.stdout.txt",
    notes: str = "pytest synthetic observation row",
) -> list[str]:
    return [
        case_id,
        contract_id,
        invariant_id,
        f"{contract_id}#{invariant_id}",
        status,
        observed_value,
        disposition,
        evidence_path,
        notes,
    ]


def test_init_incident_package_creates_layout(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)

    incident_dir = ablation_protocol.init_incident_package(ablation_root, "20260419_demo", force=False)

    assert incident_dir == (ablation_root / "20260419_demo").resolve()
    assert (incident_dir / "incident.md").is_file()
    assert (incident_dir / "notes.md").is_file()
    assert (incident_dir / "matrix.csv").is_file()
    assert (incident_dir / "artifacts" / "README.md").is_file()

    for subdir in ("logs", "diffs", "repro", "env"):
        assert (incident_dir / "artifacts" / subdir).is_dir()

    manifest_path = incident_dir / "artifacts" / "manifest.csv"
    checksums_path = incident_dir / "artifacts" / "checksums.sha256"

    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows == [ablation_protocol.MANIFEST_HEADER]
    assert checksums_path.read_text(encoding="utf-8") == ""


def test_finalize_incident_package_generates_manifest_and_checksums(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260419_demo"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)

    (incident_dir / "artifacts" / "logs" / "C001.stderr.txt").write_text("stderr\n", encoding="utf-8")
    (incident_dir / "artifacts" / "logs" / "C001.stdout.txt").write_text("stdout\n", encoding="utf-8")
    (incident_dir / "artifacts" / "logs" / "C001.stderr.tail.txt").write_text("tail\n", encoding="utf-8")
    (incident_dir / "artifacts" / "diffs" / "C001.diff.txt").write_text("diff\n", encoding="utf-8")
    repro_file = incident_dir / "artifacts" / "repro" / "C001" / "wepp" / "runs" / "pw0.run"
    repro_file.parent.mkdir(parents=True, exist_ok=True)
    repro_file.write_text("runfile\n", encoding="utf-8")
    (incident_dir / "artifacts" / "env" / "host.txt").write_text("forest\n", encoding="utf-8")

    row_count, checksum_count, resolved_incident_dir = ablation_protocol.finalize_incident_package(
        ablation_root,
        incident_id,
        produced_by="pytest",
    )

    assert resolved_incident_dir == incident_dir
    assert row_count == 6
    assert checksum_count >= row_count

    manifest_path = incident_dir / "artifacts" / "manifest.csv"
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert {row["case_id"] for row in rows} == {"C001", "GLOBAL"}
    artifact_types = {row["artifact_type"] for row in rows}
    assert {"stderr", "stdout", "tail", "diff", "repro_input", "env_capture"} <= artifact_types
    assert all(row["produced_by"] == "pytest" for row in rows)

    checksums_path = incident_dir / "artifacts" / "checksums.sha256"
    checksums_lines = [line.strip() for line in checksums_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(line.endswith("artifacts/manifest.csv") for line in checksums_lines)
    assert any(line.endswith("artifacts/logs/C001.stderr.txt") for line in checksums_lines)


def test_finalize_rejects_policy_era_upstream_lane_without_contract_columns(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260430_demo_hillslope_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    write_matrix(
        incident_dir / "matrix.csv",
        header=["timestamp_utc", "incident_id", "lane_id", "pass_fail", "notes"],
        row=["2026-04-30T00:00:00Z", incident_id, "U1", "FAIL", "missing contract columns"],
    )

    with pytest.raises(ValueError, match="upstream mutation contract columns are required"):
        ablation_protocol.finalize_incident_package(ablation_root, incident_id, produced_by="pytest")


def test_finalize_rejects_upstream_lane_without_contract_ref_or_gap_disposition(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260430_demo_hillslope_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    write_matrix(
        incident_dir / "matrix.csv",
        header=[
            "timestamp_utc",
            "incident_id",
            "lane_id",
            "contract_refs",
            "boundary_disposition",
            "pass_fail",
            "notes",
        ],
        row=[
            "2026-04-30T00:00:00Z",
            incident_id,
            "U1",
            "none",
            "valid_extreme",
            "FAIL",
            "U lane needs contract ref or explicit gap disposition",
        ],
    )

    with pytest.raises(ValueError, match="requires contract_refs or boundary_disposition"):
        ablation_protocol.finalize_incident_package(ablation_root, incident_id, produced_by="pytest")


def test_finalize_rejects_upstream_lane_with_malformed_contract_ref(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260430_demo_hillslope_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    write_matrix(
        incident_dir / "matrix.csv",
        header=[
            "timestamp_utc",
            "incident_id",
            "lane_id",
            "contract_refs",
            "boundary_disposition",
            "pass_fail",
            "notes",
        ],
        row=[
            "2026-04-30T00:00:00Z",
            incident_id,
            "U1",
            "SC-WATBAL-1#INV-WB-001",
            "valid_extreme",
            "FAIL",
            "malformed contract ref",
        ],
    )

    with pytest.raises(ValueError, match="invalid contract_ref"):
        ablation_protocol.finalize_incident_package(ablation_root, incident_id, produced_by="pytest")


def test_finalize_rejects_policy_era_upstream_lane_without_contract_observation_artifact(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260430_demo_hillslope_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    write_matrix(
        incident_dir / "matrix.csv",
        header=[
            "timestamp_utc",
            "incident_id",
            "lane_id",
            "contract_refs",
            "boundary_disposition",
            "pass_fail",
            "notes",
        ],
        row=[
            "2026-04-30T00:00:00Z",
            incident_id,
            "U1",
            "SC-WATBAL-001#INV-WATBAL-002",
            "valid_extreme",
            "PASS",
            "policy-era U lane requires contract observations artifact",
        ],
    )

    with pytest.raises(FileNotFoundError, match="Missing required contract observations artifact"):
        ablation_protocol.finalize_incident_package(ablation_root, incident_id, produced_by="pytest")


def test_finalize_rejects_contract_observation_with_missing_columns(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260430_demo_hillslope_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    write_matrix(
        incident_dir / "matrix.csv",
        header=[
            "timestamp_utc",
            "incident_id",
            "lane_id",
            "contract_refs",
            "boundary_disposition",
            "pass_fail",
            "notes",
        ],
        row=[
            "2026-04-30T00:00:00Z",
            incident_id,
            "U1",
            "SC-WATBAL-001#INV-WATBAL-002",
            "valid_extreme",
            "PASS",
            "observation schema must include required columns",
        ],
    )
    observation_path = incident_dir / "artifacts" / "logs" / "contract_observations.csv"
    with observation_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case_id", "contract_id", "status"])
        writer.writerow(["C110", "SC-WATBAL-001", "satisfied"])

    with pytest.raises(ValueError, match="missing contract observation columns"):
        ablation_protocol.finalize_incident_package(ablation_root, incident_id, produced_by="pytest")


def test_finalize_rejects_contract_observation_with_invalid_status(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260430_demo_hillslope_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    write_matrix(
        incident_dir / "matrix.csv",
        header=[
            "timestamp_utc",
            "incident_id",
            "lane_id",
            "contract_refs",
            "boundary_disposition",
            "pass_fail",
            "notes",
        ],
        row=[
            "2026-04-30T00:00:00Z",
            incident_id,
            "U1",
            "SC-WATBAL-001#INV-WATBAL-002",
            "valid_extreme",
            "PASS",
            "invalid status should fail finalize",
        ],
    )
    write_contract_observations(
        incident_dir / "artifacts" / "logs" / "contract_observations.csv",
        [build_observation_row(status="invalid_status_token")],
    )

    with pytest.raises(ValueError, match="invalid status"):
        ablation_protocol.finalize_incident_package(ablation_root, incident_id, produced_by="pytest")


def test_finalize_rejects_contract_observation_with_invalid_disposition(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260430_demo_hillslope_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    write_matrix(
        incident_dir / "matrix.csv",
        header=[
            "timestamp_utc",
            "incident_id",
            "lane_id",
            "contract_refs",
            "boundary_disposition",
            "pass_fail",
            "notes",
        ],
        row=[
            "2026-04-30T00:00:00Z",
            incident_id,
            "U1",
            "SC-WATBAL-001#INV-WATBAL-002",
            "valid_extreme",
            "PASS",
            "invalid disposition should fail finalize",
        ],
    )
    write_contract_observations(
        incident_dir / "artifacts" / "logs" / "contract_observations.csv",
        [build_observation_row(disposition="not_a_boundary_disposition")],
    )

    with pytest.raises(ValueError, match="invalid disposition"):
        ablation_protocol.finalize_incident_package(ablation_root, incident_id, produced_by="pytest")


def test_finalize_allows_upstream_lane_with_requires_scientific_review(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260430_demo_hillslope_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    write_matrix(
        incident_dir / "matrix.csv",
        header=[
            "timestamp_utc",
            "incident_id",
            "lane_id",
            "contract_refs",
            "boundary_disposition",
            "pass_fail",
            "notes",
        ],
        row=[
            "2026-04-30T00:00:00Z",
            incident_id,
            "U1",
            "none",
            "requires_scientific_review",
            "FAIL",
            "no active contract yet",
        ],
    )
    write_contract_observations(
        incident_dir / "artifacts" / "logs" / "contract_observations.csv",
        [
            build_observation_row(
                status="not_observed",
                disposition="requires_scientific_review",
                notes="upstream gap remains unresolved",
            )
        ],
    )
    (incident_dir / "artifacts" / "logs" / "C001.stdout.txt").write_text("review\n", encoding="utf-8")

    row_count, checksum_count, _ = ablation_protocol.finalize_incident_package(
        ablation_root,
        incident_id,
        produced_by="pytest",
    )

    assert row_count >= 2
    assert checksum_count >= 2


def test_finalize_allows_policy_era_upstream_lane_with_valid_contract_observations(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260430_demo_hillslope_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    write_matrix(
        incident_dir / "matrix.csv",
        header=[
            "timestamp_utc",
            "incident_id",
            "lane_id",
            "contract_refs",
            "boundary_disposition",
            "pass_fail",
            "notes",
        ],
        row=[
            "2026-04-30T00:00:00Z",
            incident_id,
            "U1",
            "SC-WATBAL-001#INV-WATBAL-002",
            "valid_extreme",
            "PASS",
            "contract-backed U lane",
        ],
    )
    write_contract_observations(
        incident_dir / "artifacts" / "logs" / "contract_observations.csv",
        [build_observation_row()],
    )
    (incident_dir / "artifacts" / "logs" / "C001.stdout.txt").write_text("ok\n", encoding="utf-8")

    row_count, checksum_count, _ = ablation_protocol.finalize_incident_package(
        ablation_root,
        incident_id,
        produced_by="pytest",
    )

    assert row_count >= 2
    assert checksum_count >= 2


def test_finalize_ignores_non_upstream_lane_without_contract_columns(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260430_demo_hillslope_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    write_matrix(
        incident_dir / "matrix.csv",
        header=["timestamp_utc", "incident_id", "lane_id", "pass_fail", "notes"],
        row=["2026-04-30T00:00:00Z", incident_id, "G1", "PASS", "guard lane"],
    )
    (incident_dir / "artifacts" / "logs" / "C001.stdout.txt").write_text("ok\n", encoding="utf-8")

    row_count, checksum_count, _ = ablation_protocol.finalize_incident_package(
        ablation_root,
        incident_id,
        produced_by="pytest",
    )

    assert row_count == 1
    assert checksum_count >= 1


def test_finalize_watershed_requires_durability_columns(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260430_demo_pw0_watershed_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    (incident_dir / "incident.md").write_text(
        "\n".join(
            [
                "# Incident",
                "- `status`: `active`",
                "- `scope`: `watershed`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_matrix(
        incident_dir / "matrix.csv",
        header=["timestamp_utc", "incident_id", "pass_fail", "notes"],
        row=["2026-04-30T00:00:00Z", incident_id, "FAIL", "missing durability metadata"],
    )

    with pytest.raises(ValueError, match="watershed durability metadata columns are required"):
        ablation_protocol.finalize_incident_package(ablation_root, incident_id, produced_by="pytest")


def test_finalize_legacy_watershed_allows_missing_durability_columns(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260420_demo_pw0_watershed_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    (incident_dir / "incident.md").write_text(
        "\n".join(
            [
                "# Incident",
                "- `status`: `active`",
                "- `scope`: `watershed`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_matrix(
        incident_dir / "matrix.csv",
        header=["timestamp_utc", "incident_id", "pass_fail", "notes"],
        row=["2026-04-20T00:00:00Z", incident_id, "FAIL", "legacy schema"],
    )
    (incident_dir / "artifacts" / "logs" / "C001.stdout.txt").write_text("legacy\n", encoding="utf-8")

    row_count, checksum_count, _ = ablation_protocol.finalize_incident_package(
        ablation_root,
        incident_id,
        produced_by="pytest",
    )

    assert row_count == 1
    assert checksum_count >= 1


def test_finalize_watershed_resolved_requires_decisive_full_period_pass(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260430_demo_pw0_watershed_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    (incident_dir / "incident.md").write_text(
        "\n".join(
            [
                "# Incident",
                "- `status`: `resolved`",
                "- `scope`: `watershed`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_matrix(
        incident_dir / "matrix.csv",
        header=[
            "timestamp_utc",
            "incident_id",
            "pass_fail",
            "durability_lane",
            "configured_simulation_years",
            "simulated_years_completed",
            "notes",
        ],
        row=[
            "2026-04-30T00:00:00Z",
            incident_id,
            "PASS",
            "decisive",
            "100",
            "55",
            "truncated pass cannot close resolved watershed incident",
        ],
    )

    with pytest.raises(ValueError, match="decisive PASS lane requires full period completion"):
        ablation_protocol.finalize_incident_package(ablation_root, incident_id, produced_by="pytest")


def test_finalize_watershed_allows_resolved_when_decisive_pass_is_full_period(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260430_demo_pw0_watershed_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    (incident_dir / "incident.md").write_text(
        "\n".join(
            [
                "# Incident",
                "- `status`: `resolved`",
                "- `scope`: `watershed`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_matrix(
        incident_dir / "matrix.csv",
        header=[
            "timestamp_utc",
            "incident_id",
            "pass_fail",
            "durability_lane",
            "configured_simulation_years",
            "simulated_years_completed",
            "notes",
        ],
        row=[
            "2026-04-30T00:00:00Z",
            incident_id,
            "PASS",
            "decisive",
            "100",
            "100",
            "full-period decisive pass",
        ],
    )
    (incident_dir / "artifacts" / "logs" / "C100.stdout.txt").write_text("ok\n", encoding="utf-8")

    row_count, checksum_count, _ = ablation_protocol.finalize_incident_package(
        ablation_root,
        incident_id,
        produced_by="pytest",
    )

    assert row_count == 1
    assert checksum_count >= 1


def test_finalize_watershed_resolved_rejects_without_decisive_pass(tmp_path: Path) -> None:
    ablation_root = tmp_path / "docs" / "ablation"
    seed_templates(ablation_root)
    incident_id = "20260430_demo_pw0_watershed_sigfpe"
    incident_dir = ablation_protocol.init_incident_package(ablation_root, incident_id)
    (incident_dir / "incident.md").write_text(
        "\n".join(
            [
                "# Incident",
                "- `status`: `resolved`",
                "- `scope`: `watershed`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_matrix(
        incident_dir / "matrix.csv",
        header=[
            "timestamp_utc",
            "incident_id",
            "pass_fail",
            "durability_lane",
            "configured_simulation_years",
            "simulated_years_completed",
            "notes",
        ],
        row=[
            "2026-04-30T00:00:00Z",
            incident_id,
            "PASS",
            "exploratory",
            "100",
            "100",
            "exploratory pass is not enough for resolved status",
        ],
    )

    with pytest.raises(ValueError, match="requires at least one decisive PASS"):
        ablation_protocol.finalize_incident_package(ablation_root, incident_id, produced_by="pytest")
