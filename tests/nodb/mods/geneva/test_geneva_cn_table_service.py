from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
from wepppy.nodb.mods.geneva.collaborators.cn_table_service import GenevaCnTableService
from wepppy.nodb.mods.geneva.errors import GenevaValidationError


pytestmark = pytest.mark.unit


@pytest.fixture()
def geneva_stub(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        wd=str(tmp_path),
        artifact_io=GenevaArtifactIO(),
    )


def test_cn_table_meta_initializes_and_recreates_missing_file(geneva_stub: SimpleNamespace) -> None:
    service = GenevaCnTableService()

    meta = service.meta(geneva_stub)
    assert meta["exists"] is True
    assert meta["path"] == "geneva/data/cn_table.csv"
    assert meta["schema_version"] == 1
    assert meta["rows"] > 0
    assert meta["columns"] == 9
    assert meta["sha256"]

    table_path = geneva_stub.artifact_io.resolve_path(geneva_stub.wd, "data/cn_table.csv")
    table_path.unlink()

    recreated = service.meta(geneva_stub)
    assert recreated["exists"] is True
    assert recreated["sha256"]


def test_cn_table_reset_is_deterministic_after_edit(geneva_stub: SimpleNamespace) -> None:
    service = GenevaCnTableService()

    baseline_snapshot = service.snapshot(geneva_stub)
    baseline_sha = baseline_snapshot["meta"]["sha256"]

    rows = list(baseline_snapshot["rows"])
    rows[0] = dict(rows[0])
    rows[0]["cn_arc_ii"] = "88"
    rows[0]["antecedent_condition_source"] = "user_override"

    modified = service.modify(
        geneva_stub,
        rows,
        if_match_sha256=baseline_sha,
    )
    assert modified["sha256"]
    assert modified["sha256"] != baseline_sha

    reset_meta = service.reset(geneva_stub, reason="test")
    assert reset_meta["sha256"] == baseline_sha


def test_cn_table_modify_requires_if_match_and_rejects_stale_token(geneva_stub: SimpleNamespace) -> None:
    service = GenevaCnTableService()
    snapshot = service.snapshot(geneva_stub)
    rows = list(snapshot["rows"])

    with pytest.raises(GenevaValidationError) as missing_token_error:
        service.modify(geneva_stub, rows, if_match_sha256=None)

    assert missing_token_error.value.code == "PRECONDITION_REQUIRED"
    assert missing_token_error.value.status_code == 428

    with pytest.raises(GenevaValidationError) as stale_token_error:
        service.modify(geneva_stub, rows, if_match_sha256="stale-token")

    assert stale_token_error.value.code == "STALE_LOOKUP"
    assert stale_token_error.value.status_code == 409


def test_cn_table_snapshot_is_deterministic_without_mutation(geneva_stub: SimpleNamespace) -> None:
    service = GenevaCnTableService()

    first_snapshot = service.snapshot(geneva_stub)
    second_snapshot = service.snapshot(geneva_stub)

    assert first_snapshot["meta"] == second_snapshot["meta"]
    assert first_snapshot["rows"] == second_snapshot["rows"]
    assert first_snapshot["csv_text"] == second_snapshot["csv_text"]


def test_cn_table_meta_migrates_legacy_missing_antecedent_column(
    geneva_stub: SimpleNamespace,
) -> None:
    service = GenevaCnTableService()

    legacy_header = [
        "nlcd_class",
        "nlcd_label",
        "hsg",
        "burn_severity",
        "hydrophobic",
        "cn_arc_ii",
        "source",
        "notes",
    ]

    table_path = geneva_stub.artifact_io.resolve_path(geneva_stub.wd, "data/cn_table.csv")
    table_path.parent.mkdir(parents=True, exist_ok=True)
    with open(table_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=legacy_header, lineterminator="\n")
        writer.writeheader()
        writer.writerow(
            {
                "nlcd_class": "41",
                "nlcd_label": "Deciduous Forest",
                "hsg": "B",
                "burn_severity": "unburned",
                "hydrophobic": "false",
                "cn_arc_ii": "55",
                "source": "legacy_seed",
                "notes": "",
            }
        )

    meta = service.meta(geneva_stub)
    assert meta["columns"] == 9

    migrated_snapshot = service.snapshot(geneva_stub)
    assert migrated_snapshot["rows"][0]["antecedent_condition_source"] == "arc_ii_seed"
