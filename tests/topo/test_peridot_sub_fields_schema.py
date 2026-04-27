from pathlib import Path

import pandas as pd
import pytest

from wepppy.topo.peridot import peridot_runner


class _DummyTranslator:
    @staticmethod
    def wepp(top: int) -> int:
        return top + 1000


class _DummyWatershedState:
    @staticmethod
    def translator_factory() -> _DummyTranslator:
        return _DummyTranslator()


class _DummyWatershed:
    @staticmethod
    def getInstance(_wd: str) -> _DummyWatershedState:
        return _DummyWatershedState()


def _patch_watershed(monkeypatch: pytest.MonkeyPatch) -> None:
    import wepppy.nodb.core as nodb_core

    monkeypatch.setattr(nodb_core, "Watershed", _DummyWatershed)
    monkeypatch.setattr(peridot_runner, "_update_catalog_entry", None)


def _write_fields_csv(sub_fields_dir: Path) -> None:
    pd.DataFrame(
        {
            "field_id": [7],
            "topaz_id": [11],
            "sub_field_id": [9001],
            "area": [25.0],
        }
    ).to_csv(sub_fields_dir / "fields.csv", index=False)


def _field_flowpaths_columns() -> dict[str, list[object]]:
    return {
        "field_id": [7],
        "topaz_id": [11],
        "sub_field_id": [9001],
        "flowpath_topaz_id": [11],
        "fp_id": [1],
        "area": [2.5],
    }


@pytest.mark.unit
def test_post_abstract_sub_fields_accepts_flowpath_topaz_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_watershed(monkeypatch)
    sub_fields_dir = tmp_path / "ag_fields" / "sub_fields"
    sub_fields_dir.mkdir(parents=True)
    _write_fields_csv(sub_fields_dir)
    pd.DataFrame(_field_flowpaths_columns()).to_csv(
        sub_fields_dir / "field_flowpaths.csv",
        index=False,
    )

    field_count, flowpath_count = peridot_runner.post_abstract_sub_fields(str(tmp_path), verbose=False)

    assert (field_count, flowpath_count) == (1, 1)
    flowpaths_df = pd.read_parquet(sub_fields_dir / "field_flowpaths.parquet")
    fields_df = pd.read_parquet(sub_fields_dir / "fields.parquet")
    assert "flowpath_topaz_id" in flowpaths_df.columns
    assert "topaz_id.1" not in flowpaths_df.columns
    for column in ("field_id", "topaz_id", "sub_field_id", "flowpath_topaz_id", "fp_id"):
        assert str(flowpaths_df[column].dtype) == "Int32"
    assert str(fields_df["topaz_id"].dtype) == "Int32"
    assert str(fields_df["wepp_id"].dtype) == "Int32"
    assert not (sub_fields_dir / "field_flowpaths.csv").exists()
    assert not (sub_fields_dir / "fields.csv").exists()


@pytest.mark.unit
def test_post_abstract_sub_fields_normalizes_historical_topaz_id_mangle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_watershed(monkeypatch)
    sub_fields_dir = tmp_path / "ag_fields" / "sub_fields"
    sub_fields_dir.mkdir(parents=True)
    _write_fields_csv(sub_fields_dir)
    (sub_fields_dir / "field_flowpaths.csv").write_text(
        "field_id,topaz_id,sub_field_id,topaz_id,fp_id,area\n"
        "7,11,9001,11,1,2.5\n",
        encoding="utf-8",
    )

    peridot_runner.post_abstract_sub_fields(str(tmp_path), verbose=False)

    flowpaths_df = pd.read_parquet(sub_fields_dir / "field_flowpaths.parquet")
    assert "flowpath_topaz_id" in flowpaths_df.columns
    assert "topaz_id.1" not in flowpaths_df.columns
    assert flowpaths_df["topaz_id"].tolist() == [11]
    assert flowpaths_df["flowpath_topaz_id"].tolist() == [11]
    assert str(flowpaths_df["flowpath_topaz_id"].dtype) == "Int32"


@pytest.mark.unit
def test_field_flowpaths_normalization_rejects_ambiguous_mixed_schema() -> None:
    fps_df = pd.DataFrame(
        {
            "field_id": [7],
            "topaz_id": [11],
            "sub_field_id": [9001],
            "flowpath_topaz_id": [11],
            "topaz_id.1": [12],
            "fp_id": [1],
        }
    )

    with pytest.raises(ValueError, match="Ambiguous field_flowpaths schema"):
        peridot_runner._normalize_field_flowpaths_dataframe(fps_df)


@pytest.mark.unit
def test_field_flowpaths_normalization_requires_flowpath_topaz_id() -> None:
    fps_df = pd.DataFrame(
        {
            "field_id": [7],
            "topaz_id": [11],
            "sub_field_id": [9001],
            "fp_id": [1],
        }
    )

    with pytest.raises(KeyError, match="flowpath_topaz_id"):
        peridot_runner._normalize_field_flowpaths_dataframe(fps_df)
