import importlib.util
import math
import shutil
import sys
import types
from copy import deepcopy
from pathlib import Path
from typing import NamedTuple

import pytest

pytestmark = pytest.mark.integration

if "deprecated" not in sys.modules:
    deprecated_stub = types.ModuleType("deprecated")

    def _deprecated(*d_args, **d_kwargs):
        if d_args and callable(d_args[0]) and not d_kwargs:
            return d_args[0]

        def _decorator(func):
            return func

        return _decorator

    deprecated_stub.deprecated = _deprecated
    sys.modules["deprecated"] = deprecated_stub

REPO_ROOT = Path(__file__).resolve().parents[4]
WEPP_SOIL_UTIL_PATH = (
    REPO_ROOT / "wepppy" / "wepp" / "soils" / "utils" / "wepp_soil_util.py"
)


def _ensure_package(name: str, path: Path) -> bool:
    if name in sys.modules:
        return False
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module
    return True


def _build_all_your_base_stub() -> types.ModuleType:
    all_your_base_stub = types.ModuleType("wepppy.all_your_base")

    def _stub_try_parse(value):
        if isinstance(value, (int, float)):
            return value
        try:
            as_float = float(value)
        except Exception:
            return value
        try:
            as_int = int(value)
            return as_int
        except Exception:
            return as_float

    def _stub_try_parse_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    def _stub_isfloat(value):
        try:
            float(value)
            return True
        except Exception:
            return False

    def _stub_isint(value):
        try:
            return float(int(value)) == float(value)
        except Exception:
            return False

    def _stub_isnan(value):
        try:
            return math.isnan(float(value))
        except Exception:
            return False

    def _stub_isinf(value):
        try:
            return math.isinf(float(value))
        except Exception:
            return False

    all_your_base_stub.try_parse = _stub_try_parse
    all_your_base_stub.try_parse_float = _stub_try_parse_float
    all_your_base_stub.isfloat = _stub_isfloat
    all_your_base_stub.isint = _stub_isint
    all_your_base_stub.isnan = _stub_isnan
    all_your_base_stub.isinf = _stub_isinf
    all_your_base_stub.NCPU = 1

    class _StubRGBA(NamedTuple):
        red: int
        green: int
        blue: int
        alpha: int = 255

        def tohex(self) -> str:
            return "#" + "".join(f"{component:02X}" for component in self)

    all_your_base_stub.RGBA = _StubRGBA
    return all_your_base_stub


@pytest.fixture(scope="module")
def wepp_soil_util_module():
    created_packages = []
    if _ensure_package("wepppy", REPO_ROOT / "wepppy"):
        created_packages.append("wepppy")
    if _ensure_package("wepppy.wepp", REPO_ROOT / "wepppy" / "wepp"):
        created_packages.append("wepppy.wepp")
    if _ensure_package("wepppy.wepp.soils", REPO_ROOT / "wepppy" / "wepp" / "soils"):
        created_packages.append("wepppy.wepp.soils")
    if _ensure_package(
        "wepppy.wepp.soils.utils", REPO_ROOT / "wepppy" / "wepp" / "soils" / "utils"
    ):
        created_packages.append("wepppy.wepp.soils.utils")

    original_all_your_base = sys.modules.get("wepppy.all_your_base")
    sys.modules["wepppy.all_your_base"] = _build_all_your_base_stub()

    module_name = "wepppy.wepp.soils.utils.wepp_soil_util"
    original_module = sys.modules.get(module_name)
    module_spec = importlib.util.spec_from_file_location(module_name, WEPP_SOIL_UTIL_PATH)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)

    try:
        yield module
    finally:
        if original_all_your_base is not None:
            sys.modules["wepppy.all_your_base"] = original_all_your_base
        else:
            sys.modules.pop("wepppy.all_your_base", None)

        if original_module is not None:
            sys.modules[module_name] = original_module
        else:
            sys.modules.pop(module_name, None)

        for name in created_packages:
            sys.modules.pop(name, None)


def _soil_payload(luse="test use"):
    return {
        "header": ["initial header"],
        "datver": 7778.0,
        "solcom": "example solcom",
        "ntemp": 1,
        "ksflag": 1,
        "ofes": [
            {
                "slid": "SLID",
                "texid": "TEX",
                "nsl": 2,
                "salb": 0.1,
                "sat": 0.5,
                "ki": "1",
                "kr": "2",
                "shcrit": "3",
                "avke": "4",
                "horizons": [
                    {
                        "solthk": 50.0,
                        "bd": 1.2,
                        "ksat": 0.1,
                        "anisotropy": 1.0,
                        "fc": 0.3,
                        "wp": 0.1,
                        "sand": 60.0,
                        "clay": 20.0,
                        "om": 0.2,
                        "orgmat": 1.0,
                        "cec": 10.0,
                        "rfg": 0.0,
                    },
                    {
                        "solthk": 250.0,
                        "bd": 1.3,
                        "ksat": 0.2,
                        "anisotropy": 1.0,
                        "fc": 0.35,
                        "wp": 0.12,
                        "sand": 55.0,
                        "clay": 25.0,
                        "om": 0.1,
                        "orgmat": 1.2,
                        "cec": 11.0,
                        "rfg": 0.0,
                    },
                ],
                "ksatadj": "1",
                "luse": luse,
                "stext": "some text",
                "uksat": "-9999",
                "texid_enum": None,
                "lkeff": "-9999",
                "ksatfac": "1",
                "ksatrec": "1",
                "res_lyr": {"slflag": 1, "ui_bdrkth": 100.0, "kslast": 0.5},
            }
        ],
        "res_lyr": {"slflag": 1, "ui_bdrkth": 100.0, "kslast": 0.5},
    }


@pytest.fixture
def workspace_tmp_dir(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("soil_utils")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def make_soil_util(wepp_soil_util_module):
    def _factory(luse="test use"):
        payload = _soil_payload(luse=luse)
        util = wepp_soil_util_module.WeppSoilUtil.__new__(
            wepp_soil_util_module.WeppSoilUtil
        )
        util.compute_erodibilities = False
        util.compute_conductivity = False
        util.obj = payload
        util.fn = "in-memory"
        return util

    return _factory


def test_replace_parameter_with_multiplier(wepp_soil_util_module):
    assert wepp_soil_util_module._replace_parameter("10", "*2") == "20.0"


def test_replace_parameter_with_none_like_string(wepp_soil_util_module):
    assert wepp_soil_util_module._replace_parameter("10", "None") == "10"
    assert wepp_soil_util_module._replace_parameter("10", " none ") == "10"


def test_pars_to_string_formats_values(wepp_soil_util_module):
    formatted = wepp_soil_util_module._pars_to_string({"a": "value", "b": 1.5})
    assert formatted == "(a='value', b=1.5)"


def test_modify_initial_sat_updates_all_ofes_and_header(make_soil_util):
    util = make_soil_util()

    util.modify_initial_sat(0.9)

    assert util.obj["ofes"][0]["sat"] == 0.9
    assert (
        util.obj["header"][-1]
        == "wepppy.wepp.soils.utils.WeppSoilUtil::modify_initial_sat(initial_sat=0.9)"
    )


def test_modify_kslast_skips_developed_soils(make_soil_util):
    util = make_soil_util(luse="Highly Developed area")
    original_header = list(util.obj["header"])
    original_kslast = util.obj["ofes"][0]["res_lyr"]["kslast"]

    util.modify_kslast(1.2)

    assert util.obj["header"] == original_header
    assert util.obj["ofes"][0]["res_lyr"]["kslast"] == original_kslast
    assert util.obj["res_lyr"]["kslast"] == original_kslast


def test_modify_kslast_updates_soil_and_header(make_soil_util):
    util = make_soil_util()

    util.modify_kslast(1.8, pars={"reason": "adjusted"})

    assert util.obj["ofes"][0]["res_lyr"]["kslast"] == 1.8
    assert util.obj["res_lyr"]["kslast"] == 1.8
    assert (
        util.obj["header"][-1]
        == "wepppy.wepp.soils.utils.WeppSoilUtil::modify_kslast(reason='adjusted')"
    )


def test_clip_soil_depth_truncates_horizons(make_soil_util):
    util = make_soil_util()

    util.clip_soil_depth(120)

    horizons = util.obj["ofes"][0]["horizons"]
    assert len(horizons) == 2
    assert horizons[-1]["solthk"] == 120
    assert util.obj["ofes"][0]["nsl"] == 2
    assert (
        util.obj["header"][-1]
        == "wepppy.wepp.soils.utils.WeppSoilUtil::clip_soil_depth(max_depth=120)"
    )


def test_ensure_minimum_soil_depth_extends_last_horizon(make_soil_util):
    util = make_soil_util()

    util.ensure_minimum_soil_depth(300)

    horizons = util.obj["ofes"][0]["horizons"]
    assert horizons[-1]["solthk"] == 300
    assert (
        util.obj["header"][-1]
        == "wepppy.wepp.soils.utils.WeppSoilUtil::ensure_minimum_soil_depth(min_depth=300)"
    )


def test_ensure_minimum_soil_depth_noop_when_depth_already_sufficient(make_soil_util):
    util = make_soil_util()
    original_depth = util.obj["ofes"][0]["horizons"][-1]["solthk"]

    util.ensure_minimum_soil_depth(200)

    horizons = util.obj["ofes"][0]["horizons"]
    assert horizons[-1]["solthk"] == original_depth


def test_yaml_input_raises_value_error(workspace_tmp_dir, wepp_soil_util_module):
    src = workspace_tmp_dir / "source.yaml"
    src.write_text("header: []\n")

    with pytest.raises(ValueError, match="YAML soil serialization is no longer supported"):
        wepp_soil_util_module.WeppSoilUtil(str(src))


def test_template_tokens_are_materialized_with_legacy_compute_flags(
    workspace_tmp_dir,
    wepp_soil_util_module,
):
    src = workspace_tmp_dir / "template_like.sol"
    src.write_text(
        "\n".join(
            [
                "7778",
                "Any comments:",
                "1 0",
                "'Template Soil' 'LOAM' 1 0.2300 sat ki kr tauc",
                "\t200.000000\t1.100000\tke\t1.000000\t0.300\t0.120\t40.000\t20.000\t2.000\t10.000\t5.000",
                "1 10000.0 0.01",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    util = wepp_soil_util_module.WeppSoilUtil(
        str(src),
        compute_erodibilities=True,
        compute_conductivity=True,
    )
    converted = util.to7778()

    ofe = converted.obj["ofes"][0]
    horizon = ofe["horizons"][0]

    assert isinstance(ofe["ki"], (int, float))
    assert isinstance(ofe["kr"], (int, float))
    assert isinstance(ofe["shcrit"], (int, float))
    assert isinstance(horizon["ksat"], (int, float))


def test_compute_conductivity_raises_when_estimate_unavailable(
    workspace_tmp_dir,
    wepp_soil_util_module,
):
    src = workspace_tmp_dir / "preserve_ksat_when_cec_zero.sol"
    src.write_text(
        "\n".join(
            [
                "7778",
                "Any comments:",
                "1 0",
                "'Template Soil' 'LOAM' 2 0.2300 0.75 400000 0.00008 2",
                "\t200.000000\t1.100000\t60.000000\t1.000000\t0.300\t0.120\t40.000\t20.000\t2.000\t0.000\t5.000",
                "\t400.000000\t1.200000\tke\t1.000000\t0.320\t0.140\t45.000\t18.000\t1.500\t0.000\t2.000",
                "1 10000.0 0.01",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="Unable to compute ksat"):
        wepp_soil_util_module.WeppSoilUtil(
            str(src),
            compute_conductivity=True,
        )


def test_to_7778disturbed_applies_replacements_and_metadata(make_soil_util):
    util = make_soil_util()

    disturbed = util.to_7778disturbed(
        replacements={
            "ki": "*2",
            "kr": "8.5",
            "shcrit": "*3",
            "avke": "0.75",
            "kslast": "*2",
            "luse": "forest high sev fire",
            "stext": "sandy loam",
        },
        h0_min_depth=120.0,
        hostname="dev.wepp.cloud",
    )

    ofe = disturbed.obj["ofes"][0]
    horizons = ofe["horizons"]

    assert ofe["ki"] == "2.0"
    assert ofe["kr"] == "8.5"
    assert ofe["shcrit"] == "9.0"
    assert ofe["luse"] == "forest high sev fire"
    assert ofe["stext"] == "sandy loam"
    assert float(horizons[0]["solthk"]) == 120.0
    assert horizons[0]["ksat"] == "0.75"
    assert float(horizons[1]["solthk"]) == 200.0
    assert horizons[1]["ksat"] == "0.75"
    assert horizons[2]["ksat"] == 0.2
    assert ofe["res_lyr"]["kslast"] == "1.0"
    assert ofe["nsl"] == len(horizons) == 3
    assert disturbed.obj["datver"] == 7778.0
    assert any(
        "WeppSoilUtil::7778disturbed_migration" in line
        for line in disturbed.obj["header"]
    )
    assert any("ki -> *2" in line for line in disturbed.obj["header"])
    assert any("h0_min_depth = 120.0" in line for line in disturbed.obj["header"])


def test_to_7778disturbed_none_replacements_preserves_values_and_records_source(
    make_soil_util,
):
    util = make_soil_util()
    original = util.obj["ofes"][0]

    disturbed = util.to_7778disturbed(
        replacements=None,
        hostname="unit.test",
    )
    ofe = disturbed.obj["ofes"][0]

    assert ofe["ki"] == original["ki"]
    assert ofe["kr"] == original["kr"]
    assert ofe["shcrit"] == original["shcrit"]
    assert any(
        "Source File: unit.test:in-memory" in line for line in disturbed.obj["header"]
    )


def test_to_7778disturbed_ignores_over9000_only_replacements(make_soil_util):
    util = make_soil_util()

    disturbed = util.to_7778disturbed(
        replacements={
            "ksflag": "9",
            "ksatadj": "2",
            "ksatfac": "3",
            "ksatrec": "4",
        }
    )

    ofe = disturbed.obj["ofes"][0]
    assert disturbed.obj["ksflag"] == 1
    assert ofe["ksatadj"] == "1"
    assert ofe["ksatfac"] == "1"
    assert ofe["ksatrec"] == "1"


def test_to_7778disturbed_falls_back_to_ksat_when_avke_is_none(make_soil_util):
    util = make_soil_util()

    disturbed = util.to_7778disturbed(
        replacements={"avke": None, "ksat": "6.2"},
    )

    assert disturbed.obj["ofes"][0]["horizons"][0]["ksat"] == "6.2"


@pytest.mark.parametrize(
    "avke,expected_ksat",
    [
        (None, "6.2"),
        (0, "0"),
        ("0", "0"),
    ],
)
def test_to_7778disturbed_avke_precedence(make_soil_util, avke, expected_ksat):
    util = make_soil_util()

    disturbed = util.to_7778disturbed(
        replacements={"avke": avke, "ksat": "6.2"},
    )

    assert disturbed.obj["ofes"][0]["horizons"][0]["ksat"] == expected_ksat


def test_to_7778disturbed_h0_max_om_filters_first_horizon(make_soil_util):
    util = make_soil_util()
    util.obj["ofes"][0]["horizons"][0].pop("om", None)
    util.obj["ofes"][0]["horizons"][1].pop("om", None)
    util.obj["ofes"][0]["horizons"][0]["orgmat"] = 0.5
    util.obj["ofes"][0]["horizons"][1]["orgmat"] = 0.1
    util.obj["ofes"][0]["horizons"][1]["solthk"] = 150.0

    disturbed = util.to_7778disturbed(replacements={}, h0_max_om=0.2)
    horizons = disturbed.obj["ofes"][0]["horizons"]

    assert len(horizons) == 1
    assert float(horizons[0]["solthk"]) == 150.0
    assert disturbed.obj["ofes"][0]["nsl"] == 1


def test_to_7778disturbed_h0_max_om_keeps_first_horizon_when_under_threshold(
    make_soil_util,
):
    util = make_soil_util()
    util.obj["ofes"][0]["horizons"][0].pop("om", None)
    util.obj["ofes"][0]["horizons"][0]["orgmat"] = 0.1

    disturbed = util.to_7778disturbed(replacements={}, h0_max_om=0.2)

    assert disturbed.obj["ofes"][0]["nsl"] == 3
    assert float(disturbed.obj["ofes"][0]["horizons"][0]["solthk"]) == 50.0


def test_to_7778disturbed_does_not_mutate_source_or_replacements(make_soil_util):
    util = make_soil_util()
    original_obj = deepcopy(util.obj)
    replacements = {"ksflag": "9", "ksatadj": "2", "ki": "4"}

    disturbed = util.to_7778disturbed(replacements=replacements)

    assert util.obj == original_obj
    assert replacements == {"ksflag": "9", "ksatadj": "2", "ki": "4"}
    assert disturbed.obj["ofes"][0]["ki"] == "4"


def test_to_7778disturbed_uses_to7778_when_source_not_7778(make_soil_util, monkeypatch):
    util = make_soil_util()
    util.obj["datver"] = 9002.0
    migrated_7778 = make_soil_util()
    called = {"count": 0, "hostname": None}

    def _fake_to7778(hostname=""):
        called["count"] += 1
        called["hostname"] = hostname
        return migrated_7778

    monkeypatch.setattr(util, "to7778", _fake_to7778)

    disturbed = util.to_7778disturbed(replacements={"ki": "4"}, hostname="unit.test")

    assert called["count"] == 1
    assert called["hostname"] == "unit.test"
    assert disturbed.obj["datver"] == 7778.0
    assert disturbed.obj["ofes"][0]["ki"] == "4"


def test_str_datver9002_requires_rosetta3(make_soil_util, monkeypatch):
    util = make_soil_util()
    util.obj["datver"] = 9002.0
    rosetta_stub = types.ModuleType("rosetta")
    monkeypatch.setitem(sys.modules, "rosetta", rosetta_stub)

    with pytest.raises(RuntimeError, match="Rosetta3 is required for datver>=9002"):
        str(util)


def test_str_datver9002_uses_rosetta_predictions(make_soil_util, monkeypatch):
    util = make_soil_util()
    util.obj["datver"] = 9002.0

    class _FakeRosetta3:
        def predict_kwargs(self, **_kwargs):
            return {
                "theta_r": 0.01,
                "theta_s": 0.43,
                "alpha": 0.02,
                "npar": 1.5,
                "ks": 0.77,
                "wp": 0.12,
                "fc": 0.34,
            }

    rosetta_stub = types.ModuleType("rosetta")
    rosetta_stub.Rosetta3 = _FakeRosetta3
    monkeypatch.setitem(sys.modules, "rosetta", rosetta_stub)

    serialized = str(util)
    assert "0.01\t 0.43\t 0.02\t 1.5\t 0.77\t 0.12\t 0.34" in serialized
    assert "0.0000\t 0.0000\t 0.0000\t 0.0000\t 0.0000\t 0.0000\t 0.0000" not in serialized


def test_to_over9000_applies_replacements_and_sets_datver(make_soil_util):
    util = make_soil_util()

    disturbed = util.to_over9000(
        replacements={
            "ki": "*2",
            "kr": "5.5",
            "shcrit": "4.5",
            "ksflag": "9",
            "ksatadj": "2",
            "ksatfac": "*3",
            "ksatrec": "*4",
            "avke": "0.8",
            "kslast": "*3",
            "luse": "forest high sev fire",
            "stext": "silt loam",
        },
        h0_min_depth=120.0,
        version=9002,
        hostname="dev.wepp.cloud",
    )

    ofe = disturbed.obj["ofes"][0]
    horizons = ofe["horizons"]

    assert disturbed.obj["datver"] == 9002
    assert disturbed.obj["ksflag"] == "9"
    assert ofe["ki"] == "2.0"
    assert ofe["kr"] == "5.5"
    assert ofe["shcrit"] == "4.5"
    assert ofe["ksatadj"] == "2"
    assert ofe["ksatfac"] == "3.0"
    assert ofe["ksatrec"] == "4.0"
    assert ofe["luse"] == "forest high sev fire"
    assert ofe["stext"] == "silt loam"
    assert float(horizons[0]["solthk"]) == 120.0
    assert horizons[0]["ksat"] == "0.8"
    assert float(horizons[1]["solthk"]) == 200.0
    assert horizons[1]["ksat"] == "0.8"
    assert horizons[2]["ksat"] == 0.2
    assert ofe["res_lyr"]["kslast"] == "1.5"
    assert ofe["nsl"] == len(horizons) == 3
    assert any("WeppSoilUtil::9002migration" in line for line in disturbed.obj["header"])


def test_to_over9000_prefers_ksat_when_avke_is_falsey(make_soil_util):
    util = make_soil_util()

    disturbed = util.to_over9000(
        replacements={"avke": 0, "ksat": "7.5"},
        version=9002,
    )

    assert disturbed.obj["ofes"][0]["horizons"][0]["ksat"] == "7.5"


def test_to_over9000_applies_bd_override_only_to_top_horizon(make_soil_util):
    util = make_soil_util()

    disturbed = util.to_over9000(
        replacements={"bd": "1.65"},
        version=9002,
    )

    horizons = disturbed.obj["ofes"][0]["horizons"]
    assert horizons[0]["bd"] == pytest.approx(1.65)
    assert horizons[1]["bd"] == 1.3


def test_to_over9000_blank_bd_override_is_noop_even_when_recompute_enabled(make_soil_util):
    util = make_soil_util()

    disturbed = util.to_over9000(
        replacements={"bd": ""},
        recompute_wp_fc_using_rosetta_on_bd_override=True,
        version=9002,
    )

    top_horizon = disturbed.obj["ofes"][0]["horizons"][0]
    assert top_horizon["bd"] == 1.2
    assert top_horizon["wp"] == 0.1
    assert top_horizon["fc"] == 0.3


def test_to_over9000_rejects_non_numeric_bd_override(make_soil_util):
    util = make_soil_util()

    with pytest.raises(ValueError, match="Invalid disturbed bd override"):
        util.to_over9000(replacements={"bd": "10.0.0"}, version=9002)


def test_to_over9000_rejects_out_of_bounds_bd_override(make_soil_util):
    util = make_soil_util()

    with pytest.raises(ValueError, match="Disturbed bd override out of bounds"):
        util.to_over9000(replacements={"bd": "2.3"}, version=9002)


@pytest.mark.parametrize("bd_value", ["0.6", "2.2"])
def test_to_over9000_accepts_boundary_bd_override_values(make_soil_util, bd_value):
    util = make_soil_util()

    disturbed = util.to_over9000(replacements={"bd": bd_value}, version=9002)

    assert disturbed.obj["ofes"][0]["horizons"][0]["bd"] == pytest.approx(float(bd_value))


def test_to_7778disturbed_rejects_non_numeric_bd_override(make_soil_util):
    util = make_soil_util()

    with pytest.raises(ValueError, match="Invalid disturbed bd override"):
        util.to_7778disturbed(replacements={"bd": "10.0.0"})


def test_to_over9000_recomputes_wp_fc_with_rosetta_for_top_horizon_only(
    make_soil_util,
    monkeypatch,
):
    util = make_soil_util()
    rosetta_calls = []

    class _FakeRosetta3:
        def predict_kwargs(self, **kwargs):
            rosetta_calls.append(kwargs)
            return {"wp": 0.21987, "fc": 0.41234}

    rosetta_stub = types.ModuleType("rosetta")
    rosetta_stub.Rosetta3 = _FakeRosetta3
    monkeypatch.setitem(sys.modules, "rosetta", rosetta_stub)

    disturbed = util.to_over9000(
        replacements={"bd": "1.6"},
        recompute_wp_fc_using_rosetta_on_bd_override=True,
        version=9002,
    )

    horizons = disturbed.obj["ofes"][0]["horizons"]
    assert horizons[0]["bd"] == pytest.approx(1.6)
    assert horizons[0]["wp"] == pytest.approx(0.2199)
    assert horizons[0]["fc"] == pytest.approx(0.4123)
    assert horizons[1]["wp"] == 0.12
    assert horizons[1]["fc"] == 0.35
    assert len(rosetta_calls) == 1
    assert rosetta_calls[0]["bd"] == pytest.approx(1.6)


@pytest.mark.parametrize("version", [9001, 9002])
def test_to_over9000_versions_9001_9002_update_ksatfac_ksatrec(
    make_soil_util,
    version,
):
    util = make_soil_util()

    disturbed = util.to_over9000(
        replacements={"ksatfac": "*5", "ksatrec": "*6"},
        version=version,
    )

    ofe = disturbed.obj["ofes"][0]
    assert ofe["ksatfac"] == "5.0"
    assert ofe["ksatrec"] == "6.0"
    assert disturbed.obj["datver"] == version


def test_to_over9000_version_9003_uses_lkeff_not_ksatfac_ksatrec(make_soil_util):
    util = make_soil_util()

    disturbed = util.to_over9000(
        replacements={"lkeff": "0.42", "ksatfac": "7", "ksatrec": "8"},
        version=9003,
    )

    ofe = disturbed.obj["ofes"][0]
    assert ofe["lkeff"] == "0.42"
    assert ofe["ksatfac"] == "1"
    assert ofe["ksatrec"] == "1"
    assert disturbed.obj["datver"] == 9003


def test_to_over9000_version_9005_sets_lkeff_and_uksat(make_soil_util):
    util = make_soil_util()

    disturbed = util.to_over9000(
        replacements={"lkeff": "0.77", "uksat": "123"},
        version=9005,
    )

    ofe = disturbed.obj["ofes"][0]
    assert ofe["lkeff"] == "0.77"
    assert ofe["uksat"] == "123"
    assert disturbed.obj["datver"] == 9005


def test_to_over9000_version_9005_defaults_lkeff_and_uksat(make_soil_util):
    util = make_soil_util()

    disturbed = util.to_over9000(replacements={}, version=9005)

    ofe = disturbed.obj["ofes"][0]
    assert ofe["lkeff"] == "-9999"
    assert ofe["uksat"] == "-9999"


def test_to_over9000_records_source_and_h0_metadata_in_header(make_soil_util):
    util = make_soil_util()

    disturbed = util.to_over9000(
        replacements={"ki": "3"},
        h0_min_depth=90.0,
        h0_max_om=0.2,
        hostname="unit.test",
        version=9002,
    )

    header = disturbed.obj["header"]
    assert any("Source File: unit.test:in-memory" in line for line in header)
    assert any("h0_min_depth = 90.0" in line for line in header)
    assert any("h0_max_om = 0.2" in line for line in header)


def test_to_over9000_h0_max_om_filters_first_horizon(make_soil_util):
    util = make_soil_util()
    util.obj["ofes"][0]["horizons"][0].pop("om", None)
    util.obj["ofes"][0]["horizons"][1].pop("om", None)
    util.obj["ofes"][0]["horizons"][0]["orgmat"] = 0.5
    util.obj["ofes"][0]["horizons"][1]["orgmat"] = 0.1
    util.obj["ofes"][0]["horizons"][1]["solthk"] = 150.0

    disturbed = util.to_over9000(replacements={}, h0_max_om=0.2, version=9002)
    horizons = disturbed.obj["ofes"][0]["horizons"]

    assert len(horizons) == 1
    assert float(horizons[0]["solthk"]) == 150.0
    assert disturbed.obj["ofes"][0]["nsl"] == 1


def test_to_over9000_h0_max_om_keeps_first_horizon_when_under_threshold(make_soil_util):
    util = make_soil_util()
    util.obj["ofes"][0]["horizons"][0].pop("om", None)
    util.obj["ofes"][0]["horizons"][0]["orgmat"] = 0.1

    disturbed = util.to_over9000(replacements={}, h0_max_om=0.2, version=9002)

    assert disturbed.obj["ofes"][0]["nsl"] == 3
    assert float(disturbed.obj["ofes"][0]["horizons"][0]["solthk"]) == 50.0


def test_to_over9000_first_horizon_above_200_splits_once_and_skips_secondary_split(
    make_soil_util,
):
    util = make_soil_util()

    disturbed = util.to_over9000(
        replacements={"avke": "0.8"},
        h0_min_depth=250.0,
        version=9002,
    )

    horizons = disturbed.obj["ofes"][0]["horizons"]
    assert len(horizons) == 3
    assert float(horizons[0]["solthk"]) == 200.0
    assert horizons[0]["ksat"] == "0.8"
    assert float(horizons[1]["solthk"]) == 250.0
    assert horizons[1]["ksat"] == 0.1
    assert horizons[2]["ksat"] == 0.2


def test_to_over9000_rejects_unsupported_version(make_soil_util):
    util = make_soil_util()

    with pytest.raises(ValueError, match="Unsupported WEPP soil version"):
        util.to_over9000(replacements={}, version=9004)


def test_to_over9000_does_not_mutate_source_or_replacements(make_soil_util):
    util = make_soil_util()
    original_obj = deepcopy(util.obj)
    replacements = {"ki": "4", "ksflag": "9"}

    disturbed = util.to_over9000(replacements=replacements, version=9002)

    assert util.obj == original_obj
    assert replacements == {"ki": "4", "ksflag": "9"}
    assert disturbed.obj["ofes"][0]["ki"] == "4"


def test_to_over9000_uses_to7778_when_source_not_7778(make_soil_util, monkeypatch):
    util = make_soil_util()
    util.obj["datver"] = 9002.0
    migrated_7778 = make_soil_util()
    called = {"count": 0, "hostname": None}

    def _fake_to7778(hostname=""):
        called["count"] += 1
        called["hostname"] = hostname
        return migrated_7778

    monkeypatch.setattr(util, "to7778", _fake_to7778)

    disturbed = util.to_over9000(
        replacements={"ki": "4"},
        version=9001,
        hostname="unit.test",
    )

    assert called["count"] == 1
    assert called["hostname"] == "unit.test"
    assert disturbed.obj["ofes"][0]["ki"] == "4"
    assert disturbed.obj["datver"] == 9001


@pytest.mark.parametrize(
    "wrapper_name,expected_version",
    [
        ("to9001", 9001),
        ("to9002", 9002),
        ("to9003", 9003),
        ("to9005", 9005),
    ],
)
def test_over9000_wrappers_forward_expected_version(
    make_soil_util,
    monkeypatch,
    wrapper_name,
    expected_version,
):
    util = make_soil_util()
    captured = {}

    def _fake_to_over9000(
        replacements,
        h0_min_depth=None,
        h0_max_om=None,
        hostname="",
        version=9002,
    ):
        captured.update(
            replacements=replacements,
            h0_min_depth=h0_min_depth,
            h0_max_om=h0_max_om,
            hostname=hostname,
            version=version,
        )
        return "sentinel"

    monkeypatch.setattr(util, "to_over9000", _fake_to_over9000)

    wrapper = getattr(util, wrapper_name)
    result = wrapper(
        {"ki": 1.0},
        h0_min_depth=60.0,
        h0_max_om=0.15,
        hostname="dev.wepp.cloud",
    )

    assert result == "sentinel"
    assert captured["replacements"] == {"ki": 1.0}
    assert captured["h0_min_depth"] == 60.0
    assert captured["h0_max_om"] == 0.15
    assert captured["hostname"] == "dev.wepp.cloud"
    assert captured["version"] == expected_version
