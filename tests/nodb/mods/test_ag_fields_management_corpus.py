from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.nodb.mods.ag_fields.management_corpus import (
    ALGORITHM,
    SCHEMA_VERSION,
    run_management_corpus,
)
from wepppy.wepp.management import read_management


pytestmark = [pytest.mark.unit, pytest.mark.nodb]

FIXTURE_RUNS = (
    Path(__file__).resolve().parents[2] / "disturbed" / "disturbed_matrix0" / "runs"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_management_corpus_materializes_reparsed_inventory(tmp_path: Path) -> None:
    parent_runs = tmp_path / "parent_runs"
    subfield_runs = tmp_path / "subfield_runs"
    parent_runs.mkdir()
    subfield_runs.mkdir()
    shutil.copyfile(FIXTURE_RUNS / "p1.man", parent_runs / "p7.man")
    shutil.copyfile(FIXTURE_RUNS / "p2.man", subfield_runs / "p31.man")

    plan_path = tmp_path / "ofe_plan.parquet"
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "parent_wepp_id": 7,
                    "ofe_id": 2,
                    "normalized_start": 0.25,
                    "normalized_end": 1.0,
                    "source_kind": "background",
                    "sub_field_id": None,
                },
                {
                    "parent_wepp_id": 7,
                    "ofe_id": 1,
                    "normalized_start": 0.0,
                    "normalized_end": 0.25,
                    "source_kind": "field",
                    "sub_field_id": 31,
                },
            ]
        ),
        plan_path,
    )

    output_dir = tmp_path / "corpus"
    result = run_management_corpus(
        ofe_plan_path=plan_path,
        parent_runs_dir=parent_runs,
        subfield_runs_dir=subfield_runs,
        output_dir=output_dir,
        workers=1,
    )

    generated_path = output_dir / "managements" / "p7.man"
    generated = read_management(str(generated_path))
    assert generated.nofe == generated.man.nofes == 2
    assert result["schema_version"] == SCHEMA_VERSION
    assert result["algorithm"] == ALGORITHM
    assert result["counts"] == {
        "parents": 1,
        "plan_rows": 2,
        "unique_source_managements": 2,
        "serialized_and_reparsed": 1,
    }
    assert result["maxima"]["ofe_count"] == {
        "value": 2,
        "parent_count": 1,
        "parent_wepp_ids": [7],
        "parent_wepp_ids_truncated": False,
    }

    corpus = pq.read_table(output_dir / "management_corpus.parquet")
    assert corpus.schema.metadata == {
        b"schema_version": SCHEMA_VERSION.encode("ascii"),
        b"algorithm": ALGORITHM.encode("ascii"),
    }
    corpus_row = corpus.to_pylist()[0]
    assert corpus_row["parent_wepp_id"] == 7
    assert corpus_row["ofe_count"] == 2
    assert corpus_row["serialization_reparsed"] is True
    assert corpus_row["generated_sha256"] == _sha256(generated_path)

    sources = pq.read_table(output_dir / "management_sources.parquet").to_pylist()
    assert [(row["ofe_id"], row["source_kind"], row["sub_field_id"]) for row in sources] == [
        (1, "field", 31),
        (2, "background", None),
    ]
    assert all(Path(row["source_path"]).is_absolute() for row in sources)
    assert all(len(row["source_sha256"]) == 64 for row in sources)

    summary = json.loads(
        (output_dir / "management_corpus_summary.json").read_text()
    )
    assert summary["inputs"]["ofe_plan"]["sha256"] == _sha256(plan_path)
    assert summary["artifacts"]["managements"] == "managements/"
