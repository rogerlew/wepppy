"""Real source/parser and emitted-artifact contracts for Roads parameterization."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from wepppy.nodb.mods.roads import parameterization as model
from wepppy.nodb.mods.roads.roads import Roads

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


@pytest.fixture(scope="module")
def baseline_state():
    return model.new_state()


def _rehash(state, name):
    asset = state["baseline"]["assets"][name]
    asset["sha256"] = hashlib.sha256(asset["text"].encode()).hexdigest()
    state["baseline"]["id"] = model.baseline_identity(state["baseline"]["assets"])


def _state(baseline_state, role="road", key="ki_kg_s_m4", mode="multiply", value=2):
    state = copy.deepcopy(baseline_state)
    state["overrides"][role][key] = {"mode": mode, "value": value}
    return state


def _soil(tmp_path, state, order=(1, 2, 3), traffic="low"):
    retained = model.materialize_baseline(state, tmp_path)
    roads = Roads.__new__(Roads)
    path = tmp_path / "profile.sol"
    roads._build_routed_mofe_soil_file(
        template_path=retained / "soils/3gloam2.sol", output_path=path,
        ofe_order=order, surface="gravel", traffic=traffic, rfg_pct=20,
    )
    return path


def test_current_baseline_roundtrip_and_comment_adapter_preserve_source(baseline_state, tmp_path):
    restored = model.validate_state(json.loads(json.dumps(baseline_state)))
    assert restored == baseline_state
    assert len(restored["baseline"]["assets"]) == 18
    assert restored["baseline"]["id"] == "roads-legacy-v1-3293894ba3394c99836302c5e1bf669acb08c68a4316f1914f12ed60d7e92b63"
    materialized = model.materialize_baseline(restored, tmp_path)
    for name, asset in restored["baseline"]["assets"].items():
        actual = (materialized / name).read_bytes()
        assert actual == (model.TEMPLATE_ROOT / name).read_bytes()
        assert hashlib.sha256(actual).hexdigest() == asset["sha256"]
    # Parser-only comment normalization must never reach retained/native material.
    assert b"# `landuse'" in (materialized / "managements/3inslope.man").read_bytes()


@pytest.mark.parametrize("change", ["hash", "id", "path", "schema", "resolver", "bool_schema", "missing", "nul", "size"])
def test_invalid_retained_state_rejected(baseline_state, change):
    state = copy.deepcopy(baseline_state)
    name = "soils/3gloam2.sol"
    if change == "hash":
        state["baseline"]["assets"][name]["text"] += "\n"
    elif change == "id":
        state["baseline"]["id"] = "other"
    elif change == "path":
        state["baseline"]["assets"]["../outside.sol"] = state["baseline"]["assets"].pop(name)
    elif change == "schema":
        state["schema_version"] = 99
    elif change == "bool_schema":
        state["schema_version"] = True
    elif change == "resolver":
        state["baseline"]["resolver_version"] = 99
    elif change == "missing":
        del state["baseline"]["assets"][name]
    elif change == "nul":
        state["baseline"]["assets"][name]["text"] += "\x00"
        _rehash(state, name)
    elif change == "size":
        state["baseline"]["assets"][name]["text"] += "#" * (256 * 1024)
        _rehash(state, name)
    with pytest.raises(ValueError):
        model.validate_state(state)


@pytest.mark.parametrize("before,after", [("urr", "ufr"), ("0.5", "nan"), ("200     45      20", "200     95      20"), ("2e+006", "0")])
def test_self_consistent_hash_does_not_bypass_raw_soil_validation(baseline_state, before, after):
    state = copy.deepcopy(baseline_state)
    name = "soils/3gloam2.sol"
    state["baseline"]["assets"][name]["text"] = state["baseline"]["assets"][name]["text"].replace(before, after, 1)
    _rehash(state, name)
    with pytest.raises(ValueError):
        model.validate_state(state)


def test_self_consistent_nonfinite_management_rejected(baseline_state):
    state = copy.deepcopy(baseline_state)
    name = "managements/3inslope.man"
    state["baseline"]["assets"][name]["text"] = state["baseline"]["assets"][name]["text"].replace("0.85", "nan", 1)
    _rehash(state, name)
    with pytest.raises(ValueError, match="nonfinite management"):
        model.validate_state(state)


@pytest.mark.parametrize("value", [True, None, "2", 0, -1, float("nan"), float("inf"), 1e308, 1e-300])
def test_invalid_override_values_rejected(baseline_state, value):
    with pytest.raises(ValueError):
        model.validate_state(_state(baseline_state, value=value))


def test_all_templates_checked_even_for_absent_role(baseline_state):
    # Individually native-representable factor overflows source Ki in other rows.
    with pytest.raises(ValueError, match="native.*representation"):
        model.validate_state(_state(baseline_state, role="buffer", value=1e38))


def test_conductivity_underflow_cannot_activate_native_estimation(baseline_state):
    with pytest.raises(ValueError, match="native representation"):
        model.validate_state(_state(baseline_state, key="ksat_mm_h", mode="absolute", value=1e-40))


def test_traffic_adjustment_precedes_override(baseline_state):
    state = _state(baseline_state)
    groups = model.resolve_groups(state, "3gloam2.sol", "low")
    assert groups[0]["baseline"]["ki_kg_s_m4"] == 2000000
    assert groups[0]["adjusted"]["ki_kg_s_m4"] == 500000
    assert groups[0]["resolved"]["ki_kg_s_m4"] == 1000000
    assert groups[1]["resolved"]["ki_kg_s_m4"] == 2000000
    assert groups[2]["resolved"]["ki_kg_s_m4"] == 120000


@pytest.mark.parametrize("order", [(1,), (1, 3), (1, 2, 3), (3, 1, 2), (3, 1, 2, 3)])
def test_default_emitted_bytes_unchanged_and_split_horizons_read_back(baseline_state, tmp_path, order):
    path = _soil(tmp_path, baseline_state, order)
    before = path.read_bytes()
    receipt = model.apply_soil_overrides(path, baseline_state, order, template_name="3gloam2.sol", traffic="low")
    assert path.read_bytes() == before
    assert [entry["role"] for entry in receipt["ofes"]] == [model.ROLES[i - 1] for i in order]
    assert receipt["input_files"][0]["sha256"] == hashlib.sha256(before).hexdigest()


@pytest.mark.parametrize("role_index,parameter", [(role, key) for role in (1, 2, 3) for key in model.PARAMETERS])
def test_each_role_driver_reaches_native_header_only(baseline_state, tmp_path, role_index, parameter):
    order = (3, 1, 2, 3)
    state = _state(baseline_state, role=model.ROLES[role_index - 1], key=parameter)
    path = _soil(tmp_path, state, order)
    before = path.read_text().splitlines()
    receipt = model.apply_soil_overrides(path, state, order, template_name="3gloam2.sol", traffic="low")
    after = path.read_text().splitlines()
    differences = [(left, right) for left, right in zip(before, after) if left != right]
    assert len(differences) == order.count(role_index)
    assert all(left.lstrip().startswith("'") for left, _ in differences)
    for row in receipt["ofes"]:
        for key in model.PARAMETERS:
            factor = 2 if row["role"] == model.ROLES[role_index - 1] and key == parameter else 1
            assert row["emitted"][key] == pytest.approx(row["adjusted"][key] * factor)


def test_wrong_assembled_role_or_reapplied_override_rejected(baseline_state, tmp_path):
    state = _state(baseline_state)
    path = _soil(tmp_path, state)
    with pytest.raises(ValueError, match="source role"):
        model.apply_soil_overrides(path, state, (3, 2, 1), template_name="3gloam2.sol", traffic="low")
    model.apply_soil_overrides(path, state, (1, 2, 3), template_name="3gloam2.sol", traffic="low")
    with pytest.raises(ValueError, match="bound baseline adjustment"):
        model.apply_soil_overrides(path, state, (1, 2, 3), template_name="3gloam2.sol", traffic="low")


def test_new_save_preserves_custom_and_reset_preserves_bound_content(baseline_state):
    overrides = _state(baseline_state)["overrides"]
    first = model.apply_payload(model.UNBOUND, {"overrides": overrides})
    assert first["overrides"] == overrides
    reset = model.apply_payload(first, {"overrides": model.default_overrides()})
    assert reset["baseline"] == first["baseline"]
    assert model.configuration_hash(reset) != model.configuration_hash(first)
    assert first["overrides"]["road"]["ki_kg_s_m4"]["mode"] == "multiply"


@pytest.mark.parametrize("current", [model.UNBOUND, "valid"])
def test_repair_not_adoption(baseline_state, current):
    value = baseline_state if current == "valid" else current
    with pytest.raises(ValueError, match="repair|repaired"):
        model.apply_payload(value, {"overrides": model.default_overrides(), "repair": True})


def test_present_null_requires_explicit_repair():
    with pytest.raises(ValueError):
        model.apply_payload(None, {"overrides": model.default_overrides()})
    result = model.apply_payload(None, {"overrides": model.default_overrides(), "repair": True})
    assert result["schema_version"] == 1


@pytest.mark.parametrize("repair", [False, "true", 1, None])
def test_repair_requires_boolean_true(baseline_state, repair):
    with pytest.raises(ValueError):
        model.apply_payload(None, {"overrides": model.default_overrides(), "repair": repair})


def test_repair_rejects_custom_overrides(baseline_state):
    with pytest.raises(ValueError, match="default mode"):
        model.apply_payload(None, {"overrides": _state(baseline_state)["overrides"], "repair": True})


def test_materialization_refuses_symlink_parent_and_input(baseline_state, tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="nonsymlink"):
        model.materialize_baseline(baseline_state, link)
    soil = _soil(target, baseline_state)
    input_link = tmp_path / "input.sol"
    input_link.symlink_to(soil)
    with pytest.raises(ValueError, match="symlinked"):
        model.apply_soil_overrides(input_link, baseline_state, (1, 2, 3), template_name="3gloam2.sol", traffic="low")


def test_selection_uses_contents_not_suffix(baseline_state):
    assert model.soil_template_name("outslope_unrutted", "paved", "loam") == "3ploam1.sol"
    groups = model.resolve_groups(baseline_state, "3ploam1.sol", "low")
    assert groups[0]["resolved"]["critical_shear_pa"] == 2
    assert groups[0]["resolved"]["ki_kg_s_m4"] == 1.25
    assert model.management_template_name("none") == "3inslopen.man"


def test_retained_precision_is_not_rounded_for_default_copied_fields(baseline_state, tmp_path):
    state = copy.deepcopy(baseline_state)
    name = "soils/3gloam2.sol"
    state["baseline"]["assets"][name]["text"] = state["baseline"]["assets"][name]["text"].replace("8.1", "8.1234567").replace("2e+006", "2000000.123456")
    _rehash(state, name)
    model.validate_state(state)
    path = _soil(tmp_path, state)
    original = path.read_bytes()
    receipt = model.apply_soil_overrides(path, state, (1, 2, 3), template_name="3gloam2.sol", traffic="low")
    assert path.read_bytes() == original
    assert receipt["ofes"][0]["emitted"]["ksat_mm_h"] == 8.1234567
    assert receipt["ofes"][1]["emitted"]["ki_kg_s_m4"] == 2000000.123456


@pytest.mark.parametrize("kind", ["trailing", "negative_ref", "large_count", "native_overflow"])
def test_self_consistent_management_grammar_and_native_bounds(baseline_state, kind):
    state = copy.deepcopy(baseline_state)
    name = "managements/3inslope.man"
    text = state["baseline"]["assets"][name]["text"]
    if kind == "trailing":
        text += "999 999 999\n"
    elif kind == "negative_ref":
        import re
        text, count = re.subn(r"(?m)^\s*1(\s+# `Initial Conditions indx')", r"-1\1", text, count=1)
        assert count == 1
    elif kind == "large_count":
        text = text.replace("200\t# (total) years", "1000000\t# (total) years", 1)
    else:
        text = text.replace("0.85", "1e308", 1)
    state["baseline"]["assets"][name]["text"] = text
    _rehash(state, name)
    with pytest.raises(ValueError):
        model.validate_state(state)


@pytest.mark.parametrize("replacement", ["1e308     45      20", "200     45      20      0.01    1e308"])
def test_self_consistent_horizon_native_overflow_rejected(baseline_state, replacement):
    state = copy.deepcopy(baseline_state)
    name = "soils/3gloam2.sol"
    text = state["baseline"]["assets"][name]["text"]
    if replacement.startswith("1e308"):
        text = text.replace("200     45      20", replacement, 1)
    else:
        text = text.replace("200     45      20      0.01    16", replacement, 1)
    state["baseline"]["assets"][name]["text"] = text
    _rehash(state, name)
    with pytest.raises(ValueError, match="native numeric representation"):
        model.validate_state(state)


def test_strict_upload_version_is_not_widened(baseline_state, tmp_path):
    from wepppy.wepp.management.managements import Management
    path = tmp_path / "legacy.man"
    path.write_text(baseline_state["baseline"]["assets"]["managements/3inslope.man"]["text"].replace("# `landuse'", "#landuse"))
    with pytest.raises(ValueError, match="Only management version 98.4"):
        Management(Key=None, ManagementFile=path.name, ManagementDir=str(tmp_path),
                   Color=(0, 0, 0, 0), StrictUpload=True, InputMaxOfes=3)


def test_legacy_mode_cannot_widen_strict_upload():
    from wepppy.wepp.management.managements import Management
    with pytest.raises(ValueError, match="mutually exclusive"):
        Management(StrictUpload=True, StrictLegacyRoads=True)


def test_ordinary_management_does_not_gain_serialized_legacy_flag(baseline_state, tmp_path):
    from wepppy.wepp.management.managements import read_management
    path = tmp_path / "legacy.man"
    path.write_text(baseline_state["baseline"]["assets"]["managements/3inslope.man"]["text"].replace("# `landuse'", "#landuse"))
    parsed = read_management(str(path))
    assert "_strict_legacy_roads" not in vars(parsed)


@pytest.mark.parametrize("traffic", ["high", "low", "none"])
@pytest.mark.parametrize("asset_name", sorted(name for name in model.ASSET_NAMES if name.startswith("soils/")))
def test_every_retained_template_default_override_preserves_emitted_bytes(
    baseline_state, tmp_path, asset_name, traffic
):
    """Exercise every baseline against the implemented helper, including tiny paved Ki."""
    order = (3, 1, 2, 3)
    retained = model.materialize_baseline(baseline_state, tmp_path)
    filename = Path(asset_name).name
    surface = "paved" if filename.startswith("3p") else "gravel"
    path = tmp_path / "matrix.sol"
    roads = Roads.__new__(Roads)
    roads._build_routed_mofe_soil_file(
        template_path=retained / asset_name,
        output_path=path,
        ofe_order=order,
        surface=surface,
        traffic=traffic,
        rfg_pct=20,
    )
    before = path.read_bytes()
    receipt = model.apply_soil_overrides(
        path, baseline_state, order, template_name=filename, traffic=traffic
    )
    assert path.read_bytes() == before
    assert receipt["input_files"][0]["sha256"] == hashlib.sha256(before).hexdigest()
    assert [record["role"] for record in receipt["ofes"]] == ["buffer", "road", "fill", "buffer"]
    for record in receipt["ofes"]:
        assert record["emitted"] == record["adjusted"]
    road = receipt["ofes"][1]
    divisor = 1 if traffic == "high" else 4
    assert road["emitted"]["ki_kg_s_m4"] == float(f"{road['baseline']['ki_kg_s_m4'] / divisor:.6g}")
    assert road["emitted"]["kr_s_m"] == float(f"{road['baseline']['kr_s_m'] / divisor:.6g}")
