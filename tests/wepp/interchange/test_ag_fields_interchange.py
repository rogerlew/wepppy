from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.wepp.interchange import ag_fields_interchange as subject


pytestmark = pytest.mark.unit


def _write_mapping(path: Path, rows: list[tuple[int, int]]) -> None:
    pq.write_table(
        pa.table(
            {
                "field_id": pa.array([row[0] for row in rows], type=pa.int32()),
                "sub_field_id": pa.array([row[1] for row in rows], type=pa.int32()),
            }
        ),
        path,
    )


def _raw_inputs(output_dir: Path, sub_field_ids: list[int]) -> None:
    output_dir.mkdir(parents=True)
    for family, (_regex, glob_pattern, _target, _symbol, _schema) in subject._FAMILY_CONTRACTS.items():
        suffix = glob_pattern.removeprefix("H*")
        for sub_field_id in sub_field_ids:
            contents = (
                "EVENT OUTPUT\ncolumns\nunits\n1 1 1 scientific-row\n"
                if family == "ebe"
                else "raw\n"
            )
            (output_dir / f"H{sub_field_id}{suffix}").write_text(
                contents,
                encoding="ascii",
            )


def _default_value(data_type: pa.DataType):
    if pa.types.is_string(data_type):
        return "EVENT"
    if pa.types.is_integer(data_type):
        return 1
    if pa.types.is_floating(data_type):
        return 1.0
    raise AssertionError(f"Unhandled test data type: {data_type}")


def _install_fake_native(
    monkeypatch: pytest.MonkeyPatch,
    calls: list[tuple[str, list]],
    *,
    zero_row_sources: dict[str, set[int]] | None = None,
) -> None:
    monkeypatch.setattr(subject, "require_wepppyo3_interchange", lambda *_args: object())

    def _call(_operation, symbol, sources, output_path, _major, _minor, **_kwargs):
        calls.append((symbol, list(sources)))
        family, contract = next(
            (name, value)
            for name, value in subject._FAMILY_CONTRACTS.items()
            if value[3] == symbol
        )
        ordinary_schema = contract[4]
        fields = [
            pa.field("field_id", pa.int32(), nullable=False),
            pa.field("sub_field_id", pa.int32(), nullable=False),
            *list(ordinary_schema)[1:],
        ]
        metadata = dict(ordinary_schema.metadata or {})
        metadata[b"dataset_kind"] = subject.DATASET_KIND.encode()
        metadata[b"ag_fields_schema_version"] = str(
            subject.AG_FIELDS_SCHEMA_VERSION
        ).encode()
        schema = pa.schema(fields, metadata=metadata)
        with pq.ParquetWriter(output_path, schema, compression="snappy") as writer:
            for _source_path, field_id, sub_field_id in sources:
                if sub_field_id in (zero_row_sources or {}).get(family, set()):
                    continue
                values = [field_id, sub_field_id]
                values.extend(_default_value(field.type) for field in fields[2:])
                writer.write_table(
                    pa.Table.from_arrays(
                        [pa.array([value], type=field.type) for value, field in zip(values, fields)],
                        schema=schema,
                    )
                )

    monkeypatch.setattr(subject, "call_wepppyo3_interchange", _call)


def test_publishes_six_file_bundle_in_numeric_subfield_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "wepp" / "ag_fields" / "output"
    mapping_path = tmp_path / "fields.parquet"
    _write_mapping(mapping_path, [(20, 10), (10, 2)])
    _raw_inputs(output_dir, [10, 2])
    calls: list[tuple[str, list]] = []
    _install_fake_native(monkeypatch, calls)

    interchange_dir = subject.run_wepp_ag_fields_interchange(
        output_dir,
        mapping_path,
        start_year=2008,
    )

    assert interchange_dir == output_dir / "interchange"
    assert len(calls) == 6
    for _symbol, sources in calls:
        assert [(source[1], source[2]) for source in sources] == [(10, 2), (20, 10)]
    for _family, (_regex, _glob, target, _symbol, _schema) in subject._FAMILY_CONTRACTS.items():
        parquet_file = pq.ParquetFile(interchange_dir / target)
        assert parquet_file.metadata.num_row_groups == 2
        assert parquet_file.schema_arrow.names[:2] == ["field_id", "sub_field_id"]
        assert "wepp_id" not in parquet_file.schema_arrow.names
    manifest = json.loads((interchange_dir / "interchange_version.json").read_text())
    assert manifest["dataset_kind"] == subject.DATASET_KIND
    assert manifest["ag_fields_schema_version"] == 1
    assert set(manifest["files"]) == set(subject._FAMILY_CONTRACTS)
    assert not list(output_dir.glob(".interchange.stage-*"))
    assert not list(output_dir.glob(".interchange.backup-*"))


def test_missing_family_source_fails_before_native_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "output"
    mapping_path = tmp_path / "fields.parquet"
    _write_mapping(mapping_path, [(10, 2), (20, 10)])
    _raw_inputs(output_dir, [2, 10])
    (output_dir / "H10.wat.dat").unlink()
    calls: list[tuple[str, list]] = []
    _install_fake_native(monkeypatch, calls)

    with pytest.raises(FileNotFoundError, match="wat source ids"):
        subject.run_wepp_ag_fields_interchange(output_dir, mapping_path)

    assert calls == []
    assert not (output_dir / "interchange").exists()


@pytest.mark.parametrize(
    "failing_symbol",
    [contract[3] for contract in subject._FAMILY_CONTRACTS.values()],
)
def test_native_family_failure_preserves_previous_bundle_and_raw_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing_symbol: str,
) -> None:
    output_dir = tmp_path / "output"
    mapping_path = tmp_path / "fields.parquet"
    _write_mapping(mapping_path, [(10, 2), (20, 10)])
    _raw_inputs(output_dir, [2, 10])
    prior_dir = output_dir / "interchange"
    prior_dir.mkdir()
    marker = prior_dir / "prior.txt"
    marker.write_text("preserve", encoding="utf-8")
    raw_paths = sorted(output_dir.glob("H*.dat"))
    raw_contents = {path: path.read_bytes() for path in raw_paths}
    calls: list[tuple[str, list]] = []
    _install_fake_native(monkeypatch, calls)
    original_call = subject.call_wepppyo3_interchange

    def _fail_family(operation, symbol, *args, **kwargs):
        if symbol == failing_symbol:
            raise RuntimeError(f"injected failure for {symbol}")
        return original_call(operation, symbol, *args, **kwargs)

    monkeypatch.setattr(subject, "call_wepppyo3_interchange", _fail_family)

    with pytest.raises(RuntimeError, match="injected failure"):
        subject.run_wepp_ag_fields_interchange(output_dir, mapping_path)

    assert marker.read_text(encoding="utf-8") == "preserve"
    assert {path: path.read_bytes() for path in raw_paths} == raw_contents
    assert not list(output_dir.glob(".interchange.stage-*"))
    assert not list(output_dir.glob(".interchange.backup-*"))


@pytest.mark.parametrize(
    "rows, message",
    [
        ([(1, 1), (2, 1)], "Duplicate sub_field_id"),
        ([(0, 1)], "field_id must be"),
        ([(1, 0)], "sub_field_id must be"),
    ],
)
def test_mapping_identity_rejections(
    tmp_path: Path,
    rows: list[tuple[int, int]],
    message: str,
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    mapping_path = tmp_path / "fields.parquet"
    _write_mapping(mapping_path, rows)

    with pytest.raises(ValueError, match=message):
        subject.run_wepp_ag_fields_interchange(output_dir, mapping_path)


def test_manifest_mapping_hash_detects_stale_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "output"
    mapping_path = tmp_path / "fields.parquet"
    _write_mapping(mapping_path, [(10, 2)])
    _raw_inputs(output_dir, [2])
    _install_fake_native(monkeypatch, [])
    subject.run_wepp_ag_fields_interchange(output_dir, mapping_path)

    assert subject._is_wepp_ag_fields_interchange_complete(output_dir, mapping_path)
    _write_mapping(mapping_path, [(11, 2)])
    assert not subject._is_wepp_ag_fields_interchange_complete(output_dir, mapping_path)


def test_completion_rejects_corrupt_parquet_and_wrong_major(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "output"
    mapping_path = tmp_path / "fields.parquet"
    _write_mapping(mapping_path, [(10, 2)])
    _raw_inputs(output_dir, [2])
    _install_fake_native(monkeypatch, [])
    interchange_dir = subject.run_wepp_ag_fields_interchange(output_dir, mapping_path)
    manifest_path = interchange_dir / "interchange_version.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["major"] = subject.INTERCHANGE_VERSION.major + 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert not subject._is_wepp_ag_fields_interchange_complete(
        output_dir,
        mapping_path,
    )

    manifest["major"] = subject.INTERCHANGE_VERSION.major
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (interchange_dir / "H.wat.parquet").write_bytes(b"not parquet")
    assert not subject._is_wepp_ag_fields_interchange_complete(
        output_dir,
        mapping_path,
    )


def test_zero_row_source_is_recorded_without_inventing_scientific_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "output"
    mapping_path = tmp_path / "fields.parquet"
    _write_mapping(mapping_path, [(10, 2), (20, 10)])
    _raw_inputs(output_dir, [2, 10])
    (output_dir / "H10.ebe.dat").write_text(
        "EVENT OUTPUT\ncolumns\nunits\n",
        encoding="ascii",
    )
    _install_fake_native(monkeypatch, [], zero_row_sources={"ebe": {10}})

    interchange_dir = subject.run_wepp_ag_fields_interchange(output_dir, mapping_path)

    manifest = json.loads((interchange_dir / "interchange_version.json").read_text())
    assert manifest["files"]["ebe"] == {
        "identity_count": 1,
        "row_groups": 1,
        "rows": 1,
        "size_bytes": (interchange_dir / "H.ebe.parquet").stat().st_size,
        "source_count": 2,
        "zero_row_source_count": 1,
        "zero_row_sub_field_ids": [10],
    }
    table = pq.read_table(interchange_dir / "H.ebe.parquet", columns=["sub_field_id"])
    assert table.column("sub_field_id").to_pylist() == [2]


def test_missing_non_ebe_identity_is_not_misclassified_as_zero_row_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "output"
    mapping_path = tmp_path / "fields.parquet"
    _write_mapping(mapping_path, [(10, 2), (20, 10)])
    _raw_inputs(output_dir, [2, 10])
    _install_fake_native(monkeypatch, [], zero_row_sources={"wat": {10}})

    with pytest.raises(ValueError, match="unexplained missing identity pairs"):
        subject.run_wepp_ag_fields_interchange(output_dir, mapping_path)

    assert not (output_dir / "interchange").exists()
    assert not list(output_dir.glob(".interchange.stage-*"))


def test_mapping_change_during_conversion_preserves_prior_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "output"
    mapping_path = tmp_path / "fields.parquet"
    _write_mapping(mapping_path, [(10, 2)])
    _raw_inputs(output_dir, [2])
    prior_dir = output_dir / "interchange"
    prior_dir.mkdir()
    prior_marker = prior_dir / "prior-generation.txt"
    prior_marker.write_text("preserve me", encoding="utf-8")
    _install_fake_native(monkeypatch, [])
    native_call = subject.call_wepppyo3_interchange

    def _replace_mapping_after_wat(operation, symbol, *args, **kwargs):
        result = native_call(operation, symbol, *args, **kwargs)
        if symbol == "ag_fields_hillslope_wat_files_to_parquet":
            _write_mapping(mapping_path, [(11, 2)])
        return result

    monkeypatch.setattr(
        subject,
        "call_wepppyo3_interchange",
        _replace_mapping_after_wat,
    )

    with pytest.raises(RuntimeError, match="mapping changed during"):
        subject.run_wepp_ag_fields_interchange(output_dir, mapping_path)

    assert prior_marker.read_text(encoding="utf-8") == "preserve me"
    assert not list(output_dir.glob(".interchange.stage-*"))


def test_successful_rerun_replaces_the_complete_prior_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "output"
    mapping_path = tmp_path / "fields.parquet"
    _write_mapping(mapping_path, [(10, 2)])
    _raw_inputs(output_dir, [2])
    _install_fake_native(monkeypatch, [])

    interchange_dir = subject.run_wepp_ag_fields_interchange(output_dir, mapping_path)
    stale_marker = interchange_dir / "prior-generation.txt"
    stale_marker.write_text("replace me", encoding="utf-8")

    rerun_dir = subject.run_wepp_ag_fields_interchange(output_dir, mapping_path)

    assert rerun_dir == interchange_dir
    assert not stale_marker.exists()
    assert subject._is_wepp_ag_fields_interchange_complete(output_dir, mapping_path)
    assert not list(output_dir.glob(".interchange.stage-*"))
    assert not list(output_dir.glob(".interchange.backup-*"))


def test_final_publication_validation_failure_restores_prior_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    final_dir = output_dir / "interchange"
    final_dir.mkdir()
    prior_marker = final_dir / "prior-generation.txt"
    prior_marker.write_text("preserve me", encoding="utf-8")
    stage_dir = output_dir / ".interchange.stage-test"
    stage_dir.mkdir()
    (stage_dir / "new-generation.txt").write_text("reject me", encoding="utf-8")
    monkeypatch.setattr(
        subject,
        "_manifest_is_current",
        lambda candidate: (candidate / "prior-generation.txt").is_file(),
    )

    with pytest.raises(RuntimeError, match="failed validation"):
        subject._publish_stage(stage_dir, final_dir)

    assert prior_marker.read_text(encoding="utf-8") == "preserve me"
    assert not (final_dir / "new-generation.txt").exists()
    assert not list(output_dir.glob(".interchange.backup-*"))


@pytest.mark.parametrize("invalid_start_year", [True, "not-a-year", object()])
def test_invalid_start_year_is_not_silently_ignored(
    tmp_path: Path,
    invalid_start_year: object,
) -> None:
    output_dir = tmp_path / "output"
    mapping_path = tmp_path / "fields.parquet"
    _write_mapping(mapping_path, [(10, 2)])
    _raw_inputs(output_dir, [2])

    with pytest.raises((TypeError, ValueError)):
        subject.run_wepp_ag_fields_interchange(
            output_dir,
            mapping_path,
            start_year=invalid_start_year,  # type: ignore[arg-type]
        )
