from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.wepp.management.managements import ScenarioReference, read_management


REPO_ROOT = Path(__file__).resolve().parents[3]
AG_DIR = REPO_ROOT / "wepppy" / "wepp" / "management" / "data" / "Agriculture"


def _load_management():
    return read_management(str(AG_DIR / "corn,soybean-no till.man"))


@pytest.mark.unit
def test_setitem_preserves_integer_sensitive_fields_in_management_output(tmp_path: Path) -> None:
    management = _load_management()

    # These values come from disturbed extended lookup rows and must round-trip
    # through emitted .man files as integer tokens (not 1.0/2.0).
    management["plant.data.mfocod"] = "2"
    management["ini.data.daydis"] = "330"
    management["ini.data.dsharv"] = "1000"
    management["ini.data.iresd"] = "1"
    management["ini.data.imngmt"] = "2"
    management["ini.data.rtyp"] = "1"

    assert management.plants[0].data.mfocod == 2
    assert management.inis[0].data.daydis == 330
    assert management.inis[0].data.dsharv == 1000
    assert management.inis[0].data.imngmt == 2
    assert management.inis[0].data.rtyp == 1
    assert isinstance(management.inis[0].data.iresd, ScenarioReference)
    assert str(management.inis[0].data.iresd) == "1"

    out_man = tmp_path / "roundtrip.man"
    out_man.write_text(str(management), encoding="utf-8")

    roundtrip = read_management(str(out_man))
    assert roundtrip.plants[0].data.mfocod == 2
    assert roundtrip.inis[0].data.daydis == 330
    assert roundtrip.inis[0].data.dsharv == 1000
    assert roundtrip.inis[0].data.imngmt == 2
    assert roundtrip.inis[0].data.rtyp == 1
    assert str(roundtrip.inis[0].data.iresd) == "1"


@pytest.mark.unit
def test_setitem_preserves_integer_tokens_for_plant_spriod_and_rcc() -> None:
    management = _load_management()
    management["plant.data.spriod"] = "95.0"
    management["plant.data.rcc"] = "2"

    plant_text = str(management.plants[0].data).splitlines()
    assert len(plant_text) >= 6

    # Line 5 (0-indexed 4): ... rsr rtmmax spriod tmpmax
    spriod_token = plant_text[4].split()[8]
    # Line 6 (0-indexed 5): tmpmin xmxlai yld rcc
    rcc_token = plant_text[5].split()[-1]

    assert spriod_token == "95"
    assert rcc_token == "2"


@pytest.mark.unit
def test_setitem_rejects_non_integral_integer_field_values() -> None:
    management = _load_management()

    with pytest.raises(ValueError, match="expected integer"):
        management["ini.data.imngmt"] = "1.25"
    with pytest.raises(ValueError, match="expected integer"):
        management["plant.data.spriod"] = "95.25"
    with pytest.raises(ValueError, match="expected integer"):
        management["plant.data.rcc"] = "2.5"


@pytest.mark.unit
def test_setitem_rejects_unknown_data_attributes() -> None:
    management = _load_management()

    with pytest.raises(NotImplementedError, match="not implemented"):
        management["ini.data.not_a_real_field"] = "1"
