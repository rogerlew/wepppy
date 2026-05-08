from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.mods.disturbed.disturbed as disturbed_module
import wepppy.wepp.management as management_module
from wepppy.nodb.mods.disturbed import (
    TREATMENT_SUFFIXES,
    lookup_disturbed_class,
)
from wepppy.nodb.mods.disturbed.disturbed import (
    Disturbed,
    read_disturbed_land_soil_lookup,
    upgrade_disturbed_land_soil_lookup,
    write_disturbed_land_soil_lookup,
)

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


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


def test_canonical_disturbed_lookup_includes_bd_after_avke_with_blank_defaults() -> None:
    lookup_path = (
        Path(disturbed_module.__file__).resolve().parent
        / "data"
        / "disturbed_land_soil_lookup.csv"
    )

    with lookup_path.open() as fp:
        reader = csv.DictReader(fp)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    assert "avke" in fieldnames
    assert "bd" in fieldnames
    assert fieldnames.index("bd") == fieldnames.index("avke") + 1
    assert rows, "Canonical disturbed lookup should not be empty."
    assert all((row.get("bd") or "").strip() == "" for row in rows)


class TestLookupDisturbedClass:
    def test_strips_mulch_15_suffix(self) -> None:
        assert lookup_disturbed_class("forest moderate sev fire-mulch_15") == "forest moderate sev fire"

    def test_strips_mulch_30_suffix(self) -> None:
        assert lookup_disturbed_class("shrub high sev fire-mulch_30") == "shrub high sev fire"

    def test_strips_mulch_60_suffix(self) -> None:
        assert lookup_disturbed_class("grass low sev fire-mulch_60") == "grass low sev fire"

    def test_strips_thinning_suffix(self) -> None:
        assert lookup_disturbed_class("forest high sev fire-thinning") == "forest high sev fire"

    def test_strips_prescribed_fire_suffix(self) -> None:
        assert lookup_disturbed_class("forest-prescribed_fire") == "forest"

    def test_no_suffix_unchanged(self) -> None:
        assert lookup_disturbed_class("forest moderate sev fire") == "forest moderate sev fire"

    def test_none_returns_none(self) -> None:
        assert lookup_disturbed_class(None) is None

    def test_empty_string_unchanged(self) -> None:
        assert lookup_disturbed_class("") == ""

    def test_no_fire_class_unchanged(self) -> None:
        assert lookup_disturbed_class("forest") == "forest"

    def test_partial_suffix_not_stripped(self) -> None:
        assert lookup_disturbed_class("forest moderate sev fire-mulch") == "forest moderate sev fire-mulch"


class TestTreatmentSuffixes:
    def test_contains_all_mulch_levels(self) -> None:
        assert "-mulch_15" in TREATMENT_SUFFIXES
        assert "-mulch_30" in TREATMENT_SUFFIXES
        assert "-mulch_60" in TREATMENT_SUFFIXES

    def test_contains_thinning(self) -> None:
        assert "-thinning" in TREATMENT_SUFFIXES

    def test_contains_prescribed_fire(self) -> None:
        assert "-prescribed_fire" in TREATMENT_SUFFIXES


class TestSoilLookupKeyGeneration:
    def test_fire_lookup_key_for_mulch_scenario(self) -> None:
        disturbed_class = "forest moderate sev fire-mulch_15"
        texid = "sand loam"
        lookup_class = lookup_disturbed_class(disturbed_class)
        key = (texid, lookup_class)
        assert key == ("sand loam", "forest moderate sev fire")


@pytest.mark.unit
def test_extended_lookup_temp_file_is_run_scoped_and_writable(tmp_path: Path) -> None:
    disturbed = object.__new__(Disturbed)
    disturbed.wd = str(tmp_path)

    tmp_lookup = Path(disturbed._new_extended_land_soil_lookup_tmp_path())

    assert tmp_lookup.parent == (tmp_path / "disturbed")
    assert tmp_lookup.name.startswith("extended_disturbed_land_soil_lookup.")
    assert tmp_lookup.suffix == ".csv"
    assert "wepppy/nodb/mods/disturbed/data" not in str(tmp_lookup)
    assert tmp_lookup.exists()

    tmp_lookup.write_text("ok\n")
    tmp_lookup.unlink()


def test_land_soil_replacements_prefers_extended_lookup_when_present(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("extended-precedence")
    disturbed_dir = run_dir / "disturbed"

    base_lookup = disturbed_dir / "disturbed_land_soil_lookup.csv"
    _write_csv(
        base_lookup,
        ["luse", "stext", "rdmax", "xmxlai", "pmet_kcb", "pmet_rawp", "keffflag", "lkeff"],
        [
            {
                "luse": "forest",
                "stext": "loam",
                "rdmax": "1.0",
                "xmxlai": "2.0",
                "pmet_kcb": "0.95",
                "pmet_rawp": "0.80",
                "keffflag": "0",
                "lkeff": "-9999",
            }
        ],
    )

    extended_lookup = disturbed_dir / "disturbed_land_soil_lookup_extended.csv"
    _write_csv(
        extended_lookup,
        [
            "disturbed_class",
            "stext",
            "rdmax",
            "xmxlai",
            "pmet_kcb",
            "pmet_rawp",
            "keffflag",
            "lkeff",
            "ini.data.cancov",
        ],
        [
            {
                "disturbed_class": "forest",
                "stext": "loam",
                "rdmax": "9.0",
                "xmxlai": "8.0",
                "pmet_kcb": "0.33",
                "pmet_rawp": "0.22",
                "keffflag": "1",
                "lkeff": "2.5",
                "ini.data.cancov": "0.44",
            }
        ],
    )

    default_lookup = run_dir / "default_lookup.csv"
    _write_csv(
        default_lookup,
        ["luse", "stext", "rdmax", "xmxlai", "pmet_kcb", "pmet_rawp", "keffflag", "lkeff"],
        [
            {
                "luse": "forest",
                "stext": "loam",
                "rdmax": "3.0",
                "xmxlai": "4.0",
                "pmet_kcb": "0.90",
                "pmet_rawp": "0.70",
                "keffflag": "0",
                "lkeff": "-9999",
            }
        ],
    )

    disturbed.config_get_path = lambda *_args, **_kwargs: str(default_lookup)
    monkeypatch.setattr(Disturbed, "ensure_land_soil_lookup_schema", lambda self: None)

    replacements = disturbed.land_soil_replacements_d
    row = replacements[("loam", "forest")]

    assert row["rdmax"] == "9.0"
    assert row["xmxlai"] == "8.0"
    assert row["pmet_kcb"] == "0.33"
    assert row["pmet_rawp"] == "0.22"
    assert row["ini.data.cancov"] == "0.44"


def test_land_soil_replacements_honors_active_lookup_variant_base(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("active-lookup-base")
    disturbed_dir = run_dir / "disturbed"

    base_lookup = disturbed_dir / "disturbed_land_soil_lookup.csv"
    _write_csv(
        base_lookup,
        ["luse", "stext", "rdmax", "xmxlai", "pmet_kcb", "pmet_rawp", "keffflag", "lkeff"],
        [
            {
                "luse": "forest",
                "stext": "loam",
                "rdmax": "1.0",
                "xmxlai": "2.0",
                "pmet_kcb": "0.95",
                "pmet_rawp": "0.80",
                "keffflag": "0",
                "lkeff": "-9999",
            }
        ],
    )

    extended_lookup = disturbed_dir / "disturbed_land_soil_lookup_extended.csv"
    _write_csv(
        extended_lookup,
        [
            "disturbed_class",
            "stext",
            "rdmax",
            "xmxlai",
            "pmet_kcb",
            "pmet_rawp",
            "keffflag",
            "lkeff",
            "ini.data.cancov",
        ],
        [
            {
                "disturbed_class": "forest",
                "stext": "loam",
                "rdmax": "9.0",
                "xmxlai": "8.0",
                "pmet_kcb": "0.33",
                "pmet_rawp": "0.22",
                "keffflag": "1",
                "lkeff": "2.5",
                "ini.data.cancov": "0.44",
            }
        ],
    )

    default_lookup = run_dir / "default_lookup.csv"
    _write_csv(
        default_lookup,
        ["luse", "stext", "rdmax", "xmxlai", "pmet_kcb", "pmet_rawp", "keffflag", "lkeff"],
        [
            {
                "luse": "forest",
                "stext": "loam",
                "rdmax": "3.0",
                "xmxlai": "4.0",
                "pmet_kcb": "0.90",
                "pmet_rawp": "0.70",
                "keffflag": "0",
                "lkeff": "-9999",
            }
        ],
    )

    disturbed.config_get_path = lambda *_args, **_kwargs: str(default_lookup)
    monkeypatch.setattr(Disturbed, "ensure_land_soil_lookup_schema", lambda self: None)
    disturbed.active_lookup_variant = "base"

    replacements = disturbed.land_soil_replacements_d
    row = replacements[("loam", "forest")]

    assert row["rdmax"] == "1.0"
    assert row["xmxlai"] == "2.0"
    assert row["pmet_kcb"] == "0.95"
    assert row["pmet_rawp"] == "0.80"


def test_active_lookup_variant_rejects_invalid_value(disturbed_factory) -> None:
    disturbed, _ = disturbed_factory("active-lookup-invalid")

    with pytest.raises(ValueError, match="lookup_variant"):
        disturbed.active_lookup_variant = "invalid"


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


def test_upgrade_lookup_adds_bd_column_after_avke_with_blank_default(tmp_path: Path) -> None:
    default_path = tmp_path / "default_lookup.csv"
    target_path = tmp_path / "target_lookup.csv"

    default_fields = [
        "luse",
        "stext",
        "ki",
        "kr",
        "shcrit",
        "avke",
        "bd",
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
                "luse": "forest moderate sev fire",
                "stext": "loam",
                "ki": "110",
                "kr": "1",
                "shcrit": "0.5",
                "avke": "20",
                "bd": "",
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
        ["luse", "stext", "ki", "kr", "shcrit", "avke"],
        [
            {
                "luse": "forest moderate sev fire",
                "stext": "loam",
                "ki": "777",
                "kr": "2",
                "shcrit": "1.5",
                "avke": "13",
            }
        ],
    )

    changed = upgrade_disturbed_land_soil_lookup(str(target_path), str(default_path))
    assert changed is True

    fieldnames, rows = _read_csv(target_path)
    assert fieldnames.index("bd") == fieldnames.index("avke") + 1
    row = rows[0]
    assert row["ki"] == "777"
    assert row["bd"] == ""


def test_upgrade_legacy_disturbed_class_rows_remain_readable(tmp_path: Path) -> None:
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


def test_build_extended_lookup_writes_separate_extended_csv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
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
            "42": {
                "ManagementFile": "high-severity-forest.man",
                "DisturbedClass": "forest high sev fire",
            }
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
                ("loam", "forest high sev fire"): {
                    "luse": "",
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
    with extended_lookup.open() as fp:
        reader = csv.DictReader(fp)
        rows = list(reader)

    assert rows
    row = rows[0]
    assert row["disturbed_class"] == "forest high sev fire"
    assert row["luse"] == "forest high sev fire"
    assert row["landuse"] == "forest"
    assert row["sev_enum"] == "4"
