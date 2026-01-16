import importlib.util
import math
import shutil
import sys
import types
import uuid
from pathlib import Path
from typing import NamedTuple

import yaml as pyyaml
import yaml
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
def make_soil_yaml(workspace_tmp_dir):
    def _factory(luse="test use"):
        payload = _soil_payload(luse=luse)
        path = workspace_tmp_dir / f"soil_{uuid.uuid4().hex}.yaml"
        path.write_text(pyyaml.safe_dump(payload))
        return path

    return _factory


def test_replace_parameter_with_multiplier(wepp_soil_util_module):
    assert wepp_soil_util_module._replace_parameter("10", "*2") == "20.0"


def test_replace_parameter_with_none_like_string(wepp_soil_util_module):
    assert wepp_soil_util_module._replace_parameter("10", "None") == "10"
    assert wepp_soil_util_module._replace_parameter("10", " none ") == "10"


def test_pars_to_string_formats_values(wepp_soil_util_module):
    formatted = wepp_soil_util_module._pars_to_string({"a": "value", "b": 1.5})
    assert formatted == "(a='value', b=1.5)"


def test_modify_initial_sat_updates_all_ofes_and_header(make_soil_yaml, wepp_soil_util_module):
    path = make_soil_yaml()
    util = wepp_soil_util_module.WeppSoilUtil(str(path))

    util.modify_initial_sat(0.9)

    assert util.obj["ofes"][0]["sat"] == 0.9
    assert (
        util.obj["header"][-1]
        == "wepppy.wepp.soils.utils.WeppSoilUtil::modify_initial_sat(initial_sat=0.9)"
    )


def test_modify_kslast_skips_developed_soils(make_soil_yaml, wepp_soil_util_module):
    path = make_soil_yaml(luse="Highly Developed area")
    util = wepp_soil_util_module.WeppSoilUtil(str(path))
    original_header = list(util.obj["header"])
    original_kslast = util.obj["ofes"][0]["res_lyr"]["kslast"]

    util.modify_kslast(1.2)

    assert util.obj["header"] == original_header
    assert util.obj["ofes"][0]["res_lyr"]["kslast"] == original_kslast
    assert util.obj["res_lyr"]["kslast"] == original_kslast


def test_modify_kslast_updates_soil_and_header(make_soil_yaml, wepp_soil_util_module):
    path = make_soil_yaml()
    util = wepp_soil_util_module.WeppSoilUtil(str(path))

    util.modify_kslast(1.8, pars={"reason": "adjusted"})

    assert util.obj["ofes"][0]["res_lyr"]["kslast"] == 1.8
    assert util.obj["res_lyr"]["kslast"] == 1.8
    assert (
        util.obj["header"][-1]
        == "wepppy.wepp.soils.utils.WeppSoilUtil::modify_kslast(reason='adjusted')"
    )


def test_clip_soil_depth_truncates_horizons(make_soil_yaml, wepp_soil_util_module):
    path = make_soil_yaml()
    util = wepp_soil_util_module.WeppSoilUtil(str(path))

    util.clip_soil_depth(120)

    horizons = util.obj["ofes"][0]["horizons"]
    assert len(horizons) == 2
    assert horizons[-1]["solthk"] == 120
    assert util.obj["ofes"][0]["nsl"] == 2
    assert (
        util.obj["header"][-1]
        == "wepppy.wepp.soils.utils.WeppSoilUtil::clip_soil_depth(max_depth=120)"
    )


def test_dump_yaml_round_trip(workspace_tmp_dir, wepp_soil_util_module):
    payload = _soil_payload()
    src = workspace_tmp_dir / "source.yaml"
    src.write_text(yaml.dump(payload))
    util = wepp_soil_util_module.WeppSoilUtil(str(src))

    dst = workspace_tmp_dir / "round_trip.yaml"
    util.dump_yaml(str(dst))

    round_trip = yaml.safe_load(dst.read_text())
    assert round_trip == util.obj
