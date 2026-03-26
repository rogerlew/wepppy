from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.mods.disturbed.disturbed as disturbed_module
import wepppy.wepp.management as management_module
from wepppy.nodb.mods.disturbed.disturbed import (
    Disturbed,
    read_disturbed_land_soil_lookup,
    upgrade_disturbed_land_soil_lookup,
    write_disturbed_land_soil_lookup,
)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open() as fp:
        reader = csv.DictReader(fp)
        return list(reader.fieldnames or []), list(reader)


def _read_audit_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


@pytest.mark.unit
def test_write_lookup_replaces_table_when_payload_is_complete(tmp_path: Path) -> None:
    lookup_path = tmp_path / "lookup.csv"
    fieldnames = ["luse", "stext", "ki", "kr"]
    _write_csv(
        lookup_path,
        fieldnames,
        [
            {"luse": "forest", "stext": "loam", "ki": "100", "kr": "1"},
            {"luse": "shrub", "stext": "loam", "ki": "200", "kr": "2"},
        ],
    )

    write_disturbed_land_soil_lookup(
        str(lookup_path),
        [
            ["forest", "loam", "999", "9"],
            ["shrub", "loam", "222", "2"],
            ["grass", "loam", "333", "3"],
        ],
    )

    header, rows = _read_csv(lookup_path)
    assert header == fieldnames
    assert rows == [
        {"luse": "forest", "stext": "loam", "ki": "999", "kr": "9"},
        {"luse": "shrub", "stext": "loam", "ki": "222", "kr": "2"},
        {"luse": "grass", "stext": "loam", "ki": "333", "kr": "3"},
    ]
    audit_lines = _read_audit_lines(tmp_path / "disturbed_lookup_audit.jsonl")
    assert any('"event":"lookup.write"' in line for line in audit_lines)


@pytest.mark.unit
def test_reset_lookup_emits_audit_record(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    disturbed_dir = run_dir / "disturbed"
    disturbed_dir.mkdir(parents=True)
    default_lookup = tmp_path / "default_lookup.csv"
    _write_csv(
        default_lookup,
        ["luse", "stext", "ki", "kr"],
        [{"luse": "forest", "stext": "loam", "ki": "101", "kr": "1"}],
    )
    target_lookup = disturbed_dir / "disturbed_land_soil_lookup.csv"
    target_lookup.write_text("luse,stext,ki,kr\nforest,loam,999,9\n")

    disturbed = object.__new__(Disturbed)
    disturbed.wd = str(run_dir)
    disturbed.config_get_path = lambda *_args, **_kwargs: str(default_lookup)

    disturbed.reset_land_soil_lookup(reason="test")

    assert target_lookup.read_text() == default_lookup.read_text()
    audit_lines = _read_audit_lines(disturbed_dir / "disturbed_lookup_audit.jsonl")
    assert any('"event":"lookup.reset"' in line for line in audit_lines)
    assert any('"reason":"test"' in line for line in audit_lines)


@pytest.mark.unit
def test_write_lookup_rejects_payload_missing_existing_rows(tmp_path: Path) -> None:
    lookup_path = tmp_path / "lookup.csv"
    _write_csv(
        lookup_path,
        ["luse", "stext", "ki", "kr"],
        [
            {"luse": "forest", "stext": "loam", "ki": "100", "kr": "1"},
            {"luse": "shrub", "stext": "loam", "ki": "200", "kr": "2"},
        ],
    )
    before = lookup_path.read_text()

    with pytest.raises(ValueError, match="missing existing lookup rows"):
        write_disturbed_land_soil_lookup(
            str(lookup_path),
            [["forest", "loam", "999", "9"]],
        )

    assert lookup_path.read_text() == before


@pytest.mark.unit
def test_write_lookup_rejects_same_row_count_when_existing_key_missing(tmp_path: Path) -> None:
    lookup_path = tmp_path / "lookup.csv"
    _write_csv(
        lookup_path,
        ["luse", "stext", "ki", "kr"],
        [
            {"luse": "forest", "stext": "loam", "ki": "100", "kr": "1"},
            {"luse": "shrub", "stext": "loam", "ki": "200", "kr": "2"},
        ],
    )
    before = lookup_path.read_text()

    with pytest.raises(ValueError, match="missing existing lookup rows"):
        write_disturbed_land_soil_lookup(
            str(lookup_path),
            [
                ["forest", "loam", "999", "9"],
                ["grass", "loam", "222", "2"],
            ],
        )

    assert lookup_path.read_text() == before


@pytest.mark.unit
def test_write_lookup_rejects_width_mismatch_without_overwriting_file(tmp_path: Path) -> None:
    lookup_path = tmp_path / "lookup.csv"
    _write_csv(
        lookup_path,
        ["luse", "stext", "ki", "kr"],
        [{"luse": "forest", "stext": "loam", "ki": "100", "kr": "1"}],
    )
    before = lookup_path.read_text()

    with pytest.raises(ValueError, match="expected 4"):
        write_disturbed_land_soil_lookup(
            str(lookup_path),
            [["forest", "loam"]],
        )

    assert lookup_path.read_text() == before


@pytest.mark.unit
def test_write_lookup_rejects_duplicate_keys(tmp_path: Path) -> None:
    lookup_path = tmp_path / "lookup.csv"
    _write_csv(
        lookup_path,
        ["luse", "stext", "ki", "kr"],
        [{"luse": "forest", "stext": "loam", "ki": "100", "kr": "1"}],
    )
    before = lookup_path.read_text()

    with pytest.raises(ValueError, match="duplicates key values"):
        write_disturbed_land_soil_lookup(
            str(lookup_path),
            [
                ["forest", "loam", "999", "9"],
                ["forest", "loam", "888", "8"],
            ],
        )

    assert lookup_path.read_text() == before


@pytest.mark.unit
def test_write_lookup_rejects_partial_mapping_rows(tmp_path: Path) -> None:
    lookup_path = tmp_path / "lookup.csv"
    _write_csv(
        lookup_path,
        ["luse", "stext", "ki", "kr"],
        [{"luse": "forest", "stext": "loam", "ki": "100", "kr": "1"}],
    )
    before = lookup_path.read_text()

    with pytest.raises(ValueError, match="missing columns"):
        write_disturbed_land_soil_lookup(
            str(lookup_path),
            [{"luse": "forest", "stext": "loam", "ki": "999"}],
        )

    assert lookup_path.read_text() == before


@pytest.mark.unit
def test_upgrade_lookup_is_additive_and_preserves_user_modified_values(tmp_path: Path) -> None:
    default_path = tmp_path / "default_lookup.csv"
    target_path = tmp_path / "target_lookup.csv"

    default_fields = [
        "luse",
        "stext",
        "ki",
        "kr",
        "pmet_kcb",
        "pmet_rawp",
        "rdmax",
        "xmxlai",
        "keffflag",
        "lkeff",
    ]
    _write_csv(
        default_path,
        default_fields,
        [
            {
                "luse": "forest",
                "stext": "loam",
                "ki": "100",
                "kr": "1",
                "pmet_kcb": "0.95",
                "pmet_rawp": "0.8",
                "rdmax": "2",
                "xmxlai": "14",
                "keffflag": "0",
                "lkeff": "-9999",
            },
            {
                "luse": "forest moderate sev fire",
                "stext": "loam",
                "ki": "110",
                "kr": "1",
                "pmet_kcb": "0.95",
                "pmet_rawp": "0.8",
                "rdmax": "0.3",
                "xmxlai": "4",
                "keffflag": "1",
                "lkeff": "1",
            },
            {
                "luse": "shrub",
                "stext": "loam",
                "ki": "300",
                "kr": "3",
                "pmet_kcb": "0.9",
                "pmet_rawp": "0.7",
                "rdmax": "1",
                "xmxlai": "9",
                "keffflag": "0",
                "lkeff": "-9999",
            },
        ],
    )

    _write_csv(
        target_path,
        ["luse", "stext", "ki", "kr"],
        [
            {"luse": "forest", "stext": "loam", "ki": "999", "kr": "1"},
            {"luse": "forest moderate sev fire", "stext": "loam", "ki": "888", "kr": "2"},
        ],
    )

    changed = upgrade_disturbed_land_soil_lookup(str(target_path), str(default_path))
    assert changed is True

    fieldnames, rows = _read_csv(target_path)
    assert fieldnames == default_fields

    by_key = {(row["luse"], row["stext"]): row for row in rows}
    assert by_key[("forest", "loam")]["ki"] == "999"
    assert by_key[("forest", "loam")]["pmet_kcb"] == "0.95"
    assert by_key[("shrub", "loam")]["ki"] == "300"

    changed_again = upgrade_disturbed_land_soil_lookup(str(target_path), str(default_path))
    assert changed_again is False
    audit_lines = _read_audit_lines(tmp_path / "disturbed_lookup_audit.jsonl")
    assert any('"event":"lookup.schema_upgrade"' in line for line in audit_lines)


@pytest.mark.unit
def test_upgrade_legacy_disturbed_class_rows_remain_readable(tmp_path: Path) -> None:
    default_path = tmp_path / "default_lookup.csv"
    target_path = tmp_path / "target_lookup.csv"
    default_fields = ["luse", "stext", "ki", "kr", "pmet_kcb", "pmet_rawp", "rdmax", "xmxlai", "keffflag", "lkeff"]
    _write_csv(
        default_path,
        default_fields,
        [
            {
                "luse": "forest moderate sev fire",
                "stext": "loam",
                "ki": "100",
                "kr": "1",
                "pmet_kcb": "0.95",
                "pmet_rawp": "0.8",
                "rdmax": "0.3",
                "xmxlai": "4",
                "keffflag": "1",
                "lkeff": "1",
            }
        ],
    )

    _write_csv(
        target_path,
        ["luse", "stext", "disturbed_class", "texid", "ki", "kr"],
        [
            {
                "luse": "",
                "stext": "",
                "disturbed_class": "forest moderate sev fire",
                "texid": "loam",
                "ki": "777",
                "kr": "2",
            }
        ],
    )

    assert upgrade_disturbed_land_soil_lookup(str(target_path), str(default_path)) is True

    lookup = read_disturbed_land_soil_lookup(str(target_path))
    assert ("loam", "forest moderate sev fire") in lookup
    assert lookup[("loam", "forest moderate sev fire")]["ki"] == "777"

    _, rows = _read_csv(target_path)
    assert rows[0]["luse"] == "forest moderate sev fire"
    assert rows[0]["stext"] == "loam"


class _AnyAttr:
    def __getattr__(self, _name: str) -> "_AnyAttr":
        return self

    def __str__(self) -> str:
        return "0"


class _IniLoopCroplandStub:
    def __getattr__(self, _name: str) -> int:
        return 0


@pytest.mark.unit
def test_build_extended_lookup_writes_separate_extended_csv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    disturbed_dir = run_dir / "disturbed"
    disturbed_dir.mkdir(parents=True)
    editable_lookup = disturbed_dir / "disturbed_land_soil_lookup.csv"
    editable_lookup.write_text("user,edited\n")

    class _LanduseStub:
        mapping = "fake.mapping"

        @classmethod
        def getInstance(cls, _wd: str):
            return cls()

    management = SimpleNamespace(
        desc="Stub Management",
        inis=[SimpleNamespace(landuse=1, data=_IniLoopCroplandStub())],
        plants=[_AnyAttr()],
    )

    monkeypatch.setattr(disturbed_module, "Landuse", _LanduseStub)
    monkeypatch.setattr(management_module, "IniLoopCropland", _IniLoopCroplandStub)
    monkeypatch.setattr(
        management_module,
        "load_map",
        lambda _mapping: {
            "42": {"ManagementFile": "forest.man", "DisturbedClass": "forest"}
        },
    )
    monkeypatch.setattr(
        management_module,
        "get_management",
        lambda _key, _map=None: management,
    )
    monkeypatch.setattr(Disturbed, "ensure_land_soil_lookup_schema", lambda self: None)
    monkeypatch.setattr(
        Disturbed,
        "land_soil_replacements_d",
        property(
            lambda self: {
                ("loam", "forest"): {
                    "luse": "forest",
                    "stext": "loam",
                    "rdmax": "0.6",
                    "xmxlai": "3.2",
                }
            }
        ),
    )

    disturbed = object.__new__(Disturbed)
    disturbed.wd = str(run_dir)
    disturbed.logger = SimpleNamespace(info=lambda *_args, **_kwargs: None)

    disturbed.build_extended_land_soil_lookup()

    assert editable_lookup.read_text() == "user,edited\n"
    extended_lookup = Path(disturbed.extended_lookup_fn)
    assert extended_lookup.exists()
    extended_text = extended_lookup.read_text()
    assert "disturbed_class" in extended_text
    assert "forest" in extended_text
